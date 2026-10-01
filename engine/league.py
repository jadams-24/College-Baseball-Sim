"""Fictional D1 league: conferences and tiers mirror 2025 D1, names are invented,
players carry true per-PA rates on the logit scale.

  logit rate = logit L + c_rate + mu_group + T_tier + U_team + e_player

L is the league outcome table; T, U and e come from the Phase 2 estimates in config;
c_rate is the location (intercept) solved by scripts/solve_phase2_location.py so that
simulated PA-weighted league rates equal the league table.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config.phase2 import (N_BENCH, N_MIDWEEK_SP, N_REGULARS, N_RELIEVERS, N_WEEKEND_SP, PA_RATES, RATES, TIERS,
                           Phase2Config)
from engine.matchup import matchup_probs

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
    z: np.ndarray      # logit offsets for RATES (relative to league, before location)
    order: int = 0     # role order on the team (lineup rank, rotation slot, bullpen rank)


@dataclass
class Team:
    tid: int
    name: str
    conference: int
    tier: str
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


def build_league(cfg: Phase2Config, rng: np.random.Generator) -> League:
    tal, fx = cfg.talent, cfg.tier_effects
    cb = np.array(cfg.correlation["batter"]["matrix"])
    cp = np.array(cfg.correlation["pitcher"]["matrix"])  # K, BB, HBP, HR, BABIP
    # conferences: real sizes and tiers, invented names
    confs: dict = {}
    by_conf: dict = {}
    for _, conf, tier in cfg.teams:
        by_conf.setdefault(conf, []).append(tier)
    used = set()
    for i, (conf, tiers) in enumerate(sorted(by_conf.items(), key=lambda x: (-len(x[1]), x[0]))):
        if conf == "DI Independent":
            name = "Independents"
        else:
            while True:
                name = f"{rng.choice(_CONF_WORDS)} {rng.choice(['Conference', 'Athletic Conference', 'League', 'Collegiate Conference'])}"
                if name not in used:
                    used.add(name); break
        confs[i] = [name, [], tiers[0], conf == "DI Independent"]
    conf_index = {conf: i for i, (conf, _) in enumerate(sorted(by_conf.items(), key=lambda x: (-len(x[1]), x[0])))}
    teams, players = [], []
    team_names = set()
    sd_team_b = np.array([tal["batter"][r]["sd_team_logit"] for r in RATES])
    sd_team_p = np.array([tal["pitcher"][r]["sd_team_logit"] for r in RATES[:5]])
    for tid, (_, conf, tier) in enumerate(cfg.teams):
        while True:
            nm = f"{_word(rng, int(rng.integers(1, 3)))} {rng.choice(_MASCOTS)}"
            if nm not in team_names:
                team_names.add(nm); break
        t = Team(tid, nm, conf_index[conf], tier)
        confs[t.conference][1].append(tid)
        u_b = _mvn(rng, sd_team_b, cb, 1)[0]
        u_p = _mvn(rng, sd_team_p, cp, 1)[0]
        tb = np.array([fx[r]["bat"][tier] for r in RATES])
        tp = np.array([fx[r]["pit"][tier] for r in RATES[:5]])

        def make(side, group, n):
            if side == "bat":
                g = {r: tal["batter"][r]["groups"][group] for r in RATES}
                mu = np.array([g[r]["mu_logit"] for r in RATES]); sd = np.array([g[r]["sd_ind_logit"] for r in RATES])
                e = _mvn(rng, sd, cb, n)
                zs = mu + tb + u_b + e
            else:
                g = {r: tal["pitcher"][r]["groups"][group] for r in RATES[:5]}
                mu = np.array([g[r]["mu_logit"] for r in RATES[:5]]); sd = np.array([g[r]["sd_ind_logit"] for r in RATES[:5]])
                e = _mvn(rng, sd, cp, n)
                zs = np.hstack([mu + tp + u_p + e, np.zeros((n, 1))])  # XBH allowed: league (attributed to batter)
            out = []
            for z in zs:
                p = Player(len(players), f"{rng.choice(_ON).upper()}. {_word(rng, int(rng.integers(1, 3)))}", tid, side, group, z)
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
