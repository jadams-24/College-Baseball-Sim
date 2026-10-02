"""Fictional D1 league: conferences and tiers mirror 2025 D1, names are invented,
players carry true per-PA rates on the logit scale. All teams sit on one talent scale.

Team strength is a pair (o, d) in log runs (offense, run prevention) relative to an
average D1 team, drawn as tier mean + conference effect + team effect from the
scoreboard decomposition (config.phase2.team_draw). It becomes rate offsets along the
engine's quality directions, plus a style term that changes the rate mix but not runs:

  batter  logit rate = logit L + c_rate + mu_group + g_o(o) * v_bat + style_bat + e_player
  pitcher logit rate = logit L + c_rate + mu_group - g_d(d) * v_pit + style_pit + e_player

g_o, g_d (config map_o, map_d) take the scoreboard's per-game log-run rating to engine
units; one monotone map for every team, so tiers stay on one scale.

e_player is drawn from the correlated normal (play-by-play correlations) and, through a
Gaussian copula, given each rate's fitted true-talent shape (scripts/build_talent_shapes.py):
the normal score of each component is mapped to the rate's standardized shape and rescaled by
its method-of-moments SD, so variances and rank correlations are kept and only the shape changes.

Tiers and conferences are only distributions of (o, d); nothing in a matchup knows a
team's tier. L is the league outcome table, mu_group and e come from the play-by-play
talent estimates, and c_rate is the location solved by scripts/solve_phase2_location.py
so that simulated PA-weighted league rates equal the league table.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config.phase2 import N_BENCH, N_MIDWEEK_SP, N_REGULARS, N_RELIEVERS, N_WEEKEND_SP, RATES, Phase2Config
from engine.matchup import matchup_probs
from engine.ratings import RatingScale

_ON = ["br", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "st", "t", "v", "w", "z", "sh", "th", "gr", "cl", "tr"]
_NU = ["a", "e", "i", "o", "u", "ai", "ea", "ou", "y"]
_CO = ["n", "r", "l", "s", "t", "ck", "rd", "ns", "lt", "ng", "x", "m", "son", "ford", "ton", "ley", "well", "berg", "wood", "field"]
_MASCOTS = ["Hawks", "Owls", "Rams", "Foxes", "Bison", "Herons", "Otters", "Comets", "Pilots", "Miners", "Rangers", "Mariners", "Badgers", "Coyotes",
            "Falcons", "Pioneers", "Monarchs", "Ospreys", "Cardinals", "Lynx", "Stags", "Thunder", "Raptors", "Mustangs", "Wolves", "Gulls", "Hornets",
            "Bluejays", "Sentinels", "Highlanders", "Voyagers", "Bobcats", "Kestrels", "Lancers", "Rapids", "Quakers", "Ironmen", "Sailors", "Clippers"]
_CONF_WORDS = ["Coastal", "Prairie", "Summit", "Great Lakes", "Bluegrass", "Gulf", "Pacific", "Atlantic", "Heartland", "Piedmont", "Frontier", "Canyon",
               "Delta", "Ridge", "Tidewater", "Northern", "Southern", "Valley", "Plains", "Cascade", "Bayou", "Keystone", "Granite", "Mesa", "Harbor",
               "Pine", "Lakeshore", "River", "Desert", "Highland"]


def _word(rng: np.random.Generator, parts: int) -> str:
    w = "".join(rng.choice(_ON) + rng.choice(_NU) for _ in range(parts)) + rng.choice(_CO)
    return w.capitalize()


@dataclass
class Player:
    pid: int
    name: str
    team: int
    side: str          # "bat" or "pit"
    group: str         # regular / bench / sp_weekend / sp_midweek / rp
    z: np.ndarray      # logit offsets for RATES (relative to league, before location), built from ratings
    order: int = 0     # role order on the team (lineup rank, rotation slot, bullpen rank)
    ratings: dict = field(default_factory=dict)   # 20-80 true ratings (continuous; engine.ratings)
    hidden: dict = field(default_factory=dict)    # true components without a rating (HBP; pitcher BABIP/XBH)
    log_theta: float = 0.0                        # pitcher leash multiplier on the pull hazard (Stamina)


@dataclass
class Team:
    tid: int
    name: str
    conference: int
    tier: str
    o: float = 0.0     # true offense, log runs above an average team (team level, before players)
    d: float = 0.0     # true run prevention, log runs
    batters: list = field(default_factory=list)
    weekend_sp: list = field(default_factory=list)
    midweek_sp: list = field(default_factory=list)
    relievers: list = field(default_factory=list)


@dataclass
class League:
    teams: list
    conferences: dict           # conf id -> (name, [team ids], tier)
    players: list
    location: dict              # rate -> c (added to every matchup)


def _mvn(rng, sd: np.ndarray, corr: np.ndarray, n: int) -> np.ndarray:
    cov = np.outer(sd, sd) * corr
    return rng.multivariate_normal(np.zeros(len(sd)), cov, size=n, method="eigh")


def _shaped(e: np.ndarray, sd: np.ndarray, shapes: list) -> np.ndarray:
    """Gaussian copula: each column of the correlated normal draw e (SDs sd) is a normal score
    u = e / sd, mapped to the rate's fitted standardized shape (quantile table at normal scores,
    linear beyond its ends) and scaled back by sd. Ranks, hence rank correlations, are unchanged;
    a rate without a fitted shape stays Gaussian (identity)."""
    out = e.copy()
    for j, sh in enumerate(shapes):
        if sh is None or sd[j] <= 0:
            continue
        x, y = sh
        u = e[:, j] / sd[j]
        v = np.interp(u, x, y)
        lo, hi = u < x[0], u > x[-1]
        v[lo] = y[0] + (u[lo] - x[0]) * (y[1] - y[0]) / (x[1] - x[0])
        v[hi] = y[-1] + (u[hi] - x[-1]) * (y[-1] - y[-2]) / (x[-1] - x[-2])
        out[:, j] = sd[j] * v
    return out


def build_league(cfg: Phase2Config, rng: np.random.Generator) -> League:
    tal = cfg.talent
    cb = np.array(cfg.correlation["batter"]["matrix"])
    cp = np.array(cfg.correlation["pitcher"]["matrix"])  # K, BB, HBP, HR, BABIP
    v_bat, v_pit = np.array(cfg.v_bat), np.array(cfg.v_pit)
    # conferences: real sizes and tiers, invented names, one conference effect each
    confs: dict = {}
    by_conf: dict = {}
    for _, conf, tier in cfg.teams:
        by_conf.setdefault(conf, []).append(tier)
    used = set()
    order = sorted(by_conf.items(), key=lambda x: (-len(x[1]), x[0]))
    conf_fx = {}
    for i, (conf, tiers) in enumerate(order):
        if conf == "DI Independent":
            name = "Independents"
        else:
            while True:
                name = f"{rng.choice(_CONF_WORDS)} {rng.choice(['Conference', 'Athletic Conference', 'League', 'Collegiate Conference'])}"
                if name not in used:
                    used.add(name); break
        confs[i] = [name, [], tiers[0], conf == "DI Independent"]
        conf_fx[i] = rng.multivariate_normal(np.zeros(2), cfg.team_draw[tiers[0]]["conf_cov"], method="eigh")
    conf_index = {conf: i for i, (conf, _) in enumerate(order)}
    scale = RatingScale()
    shapes_bat = [cfg.talent_shape.get(f"bat_{r}") for r in RATES]
    shapes_pit = [cfg.talent_shape.get(f"pit_{r}") for r in RATES[:5]]
    # stamina draws use their own stream so the Phase 2 talent draws are unchanged for a given seed
    rng_stamina = np.random.Generator(np.random.PCG64(rng.bit_generator.seed_seq.spawn(1)[0]))
    teams, players = [], []
    team_names = set()
    for tid, (_, conf, tier) in enumerate(cfg.teams):
        while True:
            nm = f"{_word(rng, int(rng.integers(1, 3)))} {rng.choice(_MASCOTS)}"
            if nm not in team_names:
                team_names.add(nm); break
        t = Team(tid, nm, conf_index[conf], tier)
        confs[t.conference][1].append(tid)
        td = cfg.team_draw[tier]
        # an independent has no conference: it draws its own effect from its tier's conference distribution
        c = conf_fx[t.conference] if not confs[t.conference][3] else rng.multivariate_normal(np.zeros(2), td["conf_cov"], method="eigh")
        t.o, t.d = np.array(td["mean"]) + c + rng.multivariate_normal(np.zeros(2), td["team_cov"], method="eigh")
        g_o = cfg.map_o[0] * t.o + cfg.map_o[1] * t.o ** 2
        g_d = cfg.map_d[0] * t.d + cfg.map_d[1] * t.d ** 2
        tb = g_o * v_bat + rng.multivariate_normal(np.zeros(6), cfg.style_cov["bat"], method="eigh")
        tp = -g_d * v_pit + rng.multivariate_normal(np.zeros(6), cfg.style_cov["pit"], method="eigh")

        def make(side, group, n):
            if side == "bat":
                g = {r: tal["batter"][r]["groups"][group] for r in RATES}
                mu = np.array([g[r]["mu_logit"] for r in RATES]); sd = np.array([g[r]["sd_ind_logit"] for r in RATES])
                zs = mu + tb + _shaped(_mvn(rng, sd, cb, n), sd, shapes_bat)
            else:
                g = {r: tal["pitcher"][r]["groups"][group] for r in RATES[:5]}
                mu = np.array([g[r]["mu_logit"] for r in RATES[:5]]); sd = np.array([g[r]["sd_ind_logit"] for r in RATES[:5]])
                # individual hit-type mix allowed is not modeled (attributed to the batter); team quality moves it
                zs = np.hstack([mu + _shaped(_mvn(rng, sd, cp, n), sd, shapes_pit), np.zeros((n, 1))]) + tp
            out = []
            # players are generated from ratings: the drawn true rates are expressed on the 20-80 scale and
            # the engine's rates are rebuilt from those ratings (plus unrated components)
            lt = scale.draw_log_theta(group, rng_stamina, n) if side == "pit" else None
            for k, z in enumerate(zs):
                ratings, hidden = scale.split(side, z)
                p = Player(len(players), f"{rng.choice(_ON).upper()}. {_word(rng, int(rng.integers(1, 3)))}", tid, side, group,
                           scale.compose(side, ratings, hidden), ratings=ratings, hidden=hidden)
                if side == "pit":
                    p.ratings["stamina"] = scale.stamina_rating(group, lt[k])
                    p.log_theta = scale.log_theta(group, p.ratings["stamina"])
                players.append(p); out.append(p)
            return out
        regs = make("bat", "regular", N_REGULARS)
        bench = make("bat", "bench", N_BENCH)
        # lineup rank by expected on-base plus slugging against a league-average pitcher
        def bat_value(p):
            pr = matchup_probs(cfg, p.z, np.zeros(6), {r: 0.0 for r in RATES})
            ob = pr["BB"] + pr["HBP"] + pr["1B"] + pr["2B"] + pr["3B"] + pr["HR"]
            return ob + (pr["1B"] + 2 * pr["2B"] + 3 * pr["3B"] + 4 * pr["HR"])
        for grp, base in ((regs, 0), (bench, N_REGULARS)):
            for k, p in enumerate(sorted(grp, key=bat_value, reverse=True)):
                p.order = base + k
        t.batters = sorted(regs + bench, key=lambda p: p.order)
        # pitchers ordered by K - BB - HR (logit offsets): best gets Friday / most relief work
        quality = lambda p: p.z[0] - p.z[1] - p.z[3]
        for lst, group, n in ((t.weekend_sp, "sp_weekend", N_WEEKEND_SP), (t.midweek_sp, "sp_midweek", N_MIDWEEK_SP), (t.relievers, "rp", N_RELIEVERS)):
            for k, p in enumerate(sorted(make("pit", group, n), key=quality, reverse=True)):
                p.order = k; lst.append(p)
        teams.append(t)
    league = League(teams, confs, players, {r: 0.0 for r in RATES})
    league.location = dict(FIXED_LOCATION) if FIXED_LOCATION is not None else load_location()
    return league


FIXED_LOCATION = None  # set by scripts/solve_phase2_location.py while it iterates


def load_location() -> dict:
    """Intercepts solved by scripts/solve_phase2_location.py (see that script)."""
    import json
    from config.phase2 import ROOT
    return json.loads((ROOT / "data/ncaa_2025/derived/phase2_location_2025.json").read_text())["location"]


def _expit(x):
    return 1.0 / (1.0 + np.exp(-x))
