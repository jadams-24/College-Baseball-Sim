"""Phase 2 constants. Rates and distributions come from benchmarks.json and
data/ncaa_2025/derived/phase2_inputs_2025.json (built by
scripts/build_phase2_benchmarks.py and scripts/build_phase2_gate.py). Roster shape
and schedule length follow the project owner's Phase 2 spec and game_structure in
benchmarks.json. Anything else is marked # GUESS and listed in GUESSES.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config import phase1

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data/ncaa_2025/derived/phase2_inputs_2025.json"
RUN_SCALE = ROOT / "data/ncaa_2025/derived/phase2_run_scale_2025.json"
GAME_SCALE = ROOT / "data/ncaa_2025/derived/phase2_game_scale_2025.json"
GAME_SCALE_OVERRIDE = None  # set by scripts/solve_phase2_game_scale.py while it iterates
TEAMS = ROOT / "data/ncaa_2025/pbp/teams_2025.csv"
TIERS = ("p4", "mid", "low")
RATES = ("K", "BB", "HBP", "HR", "BABIP", "XBH")
PA_RATES = ("K", "BB", "HBP", "HR")

# Roster shape: owner's Phase 2 spec ("about 9 regulars plus bench, a weekend rotation
# of 3 starters, midweek starters, about 8 relievers").
N_REGULARS = 9
N_BENCH = 5
N_WEEKEND_SP = 3
N_MIDWEEK_SP = 2
N_RELIEVERS = 13   # Phase 6: 2025 full-season teams use 18.3 pitchers (median 18; scripts/build_phase6_usage.py), so 3 + 2 + 13

# Season: 56 games (benchmarks game_structure.regular_season_game_limit) as 14 weeks of a
# Fri-Sun series plus one midweek game; conference weekends from the scoreboard share of
# conference games (schedule_mix.conference_games_share x 56 / 3).
WEEKS = 14
GAMES_PER_WEEKEND = 3
SEASON_GAMES = 56

# Qualification for the percentile and leaderboard gates: NCAA statistics rules
# (batting: 2.0 PA per team game and 75% of team games; pitching: 1 IP per team game)
# and the FanGraphs 50-IP cut used for pitching_distribution_2025.
QUAL_PA_PER_TEAM_GAME = 2.0
QUAL_GAMES_SHARE = 0.75
QUAL_IP_PER_TEAM_GAME = 1.0
LEADERBOARD_MIN_IP = 50

# Weekend starts: the team's k-th most frequent weekend starter (usage weekend_start_share_by_rank)
# is played by this staff slot. Ranks 1-3 are the weekend rotation; who makes the occasional
# 4th-8th-ranked starts (here the two midweek starters, then the top relievers) is not in the data.
ROTATION_STAFF = (("weekend_sp", 0), ("weekend_sp", 1), ("weekend_sp", 2), ("midweek_sp", 0), ("midweek_sp", 1),
                  ("relievers", 0), ("relievers", 1), ("relievers", 2))  # GUESS (slots for ranks 4-8)
# Weekend starter pull hazards are tabulated for rotation ranks 1, 2, 3 and 4+ (spot starters),
# matching usage.weekend_starter_pull_by_rank in phase2_inputs_2025.json.
SPOT_STARTER_RANK = 4

# Gate tolerances. Benchmark tolerances are 3 standard errors of the real statistic; the
# simulated value has its own standard error at the number of seasons run (season-to-season
# SD / sqrt(n)). A gate row's tolerance combines both: sqrt(tol_bench^2 + (3 * se_sim)^2).
# Leaderboard rows compare one real season with the simulated seasons: Student-t
# prediction interval at the central 95% stated in leaderboards_2025.
GATE_SE_MULTIPLE = 3
LEADERBOARD_PI = 0.95

# Gate rows moved to the Phase 6 gate by the project owner (PR #4 review): their causes are
# built in Phase 6. Reported every run, not gated here. See CLAUDE.md, Phase 6 deferred rows.
DEFERRED_TO_PHASE6 = {
    "run_rule": "game-to-game variance: parks/weather, bullpen availability, lineup changes, blowout substitutions",
    "run_histogram_15plus": "game-to-game variance: parks/weather, bullpen availability, lineup changes, blowout substitutions",
    "lb_pitchers_50ip": "swingman relief and Thursday openers (need rest days and fatigue)",
    "q_K9_p50": "swingman relief and Thursday openers (need rest days and fatigue)",
    "q_K9_p90": "swingman relief and Thursday openers (need rest days and fatigue)",
    "tier_p4_low": "reserves in mismatches and blowouts (manager AI)",
}

# Shape of the individual true-talent distributions (scripts/build_talent_shapes.py). A rate is drawn
# from its fitted sinh-arcsinh shape when the likelihood-ratio statistic against the Gaussian
# (2 degrees of freedom) exceeds the chi-square(2) critical value at p = .001 (13.82; strict, as
# 17 side-rate shapes are tested); otherwise Gaussian. Grids are numerical settings.
TALENT_SHAPES = ROOT / "data/ncaa_2025/derived/talent_shapes_2025.json"
SHAPE_LRT_CRIT = 13.82  # GUESS (statistical threshold)
TALENT_SHAPES_OVERRIDE = None              # set by scripts that compare shapes (e.g. {} for all-Gaussian)
SHAPE_NPMLE_GRID = (-8.0, 8.0, 321)        # NPMLE support: standardized offsets, 0.05 apart
SHAPE_NPMLE_ITERS = 20000                  # EM steps (stops earlier when the log-likelihood gains < 1e-8)
SHAPE_Z_GRID = (8.0, 401)                  # quadrature over Z ~ N(0, 1) for the sinh-arcsinh likelihood
SHAPE_QUANTILE_POINTS = (-6.0, 6.0, 241)   # stored quantile table of each standardized shape (normal scores)

# Starter/reliever choice weights and lineup start rates come from usage tables; when a
# hazard cell has fewer than this many batters faced it backs off to the coarser table.
MIN_HAZARD_N = 30  # GUESS (statistical threshold)


@dataclass(frozen=True)
class Phase2Config:
    base: phase1.Phase1Config
    league_rates: dict          # per-rate league values implied by the outcome table
    roe_share_of_bip: float     # reached on error as a share of balls in play (league)
    triple_share_of_xbh: float  # 3B / (2B + 3B) (league)
    tier_effects: dict          # logit tier effects from the play-by-play (define the quality directions)
    team_talent: dict           # scoreboard decomposition: tier means, team and conference covariances, home, hosting
    v_bat: tuple                # logit offsets per unit of engine offense (one log run per half-inning)
    v_pit: tuple                # logit offsets per unit of engine run prevention given up (same scale)
    map_o: tuple                # (k, q): engine offense = k * o + q * o^2, o the scoreboard rating (log runs per game)
    map_d: tuple                # (k, q): engine run prevention = k * d + q * d^2
    team_draw: dict             # tier -> {"mean", "team_cov", "conf_cov"} of (o, d), individual share removed
    style_cov: dict             # "bat"/"pit" -> 6x6 covariance of team rate offsets with zero run value
    home_eta: float             # home talent edge in log runs (matchup-controlled home effect minus batting-last effect)
    talent: dict                # mu / sd by side, rate and role group; team SDs
    correlation: dict           # batter and pitcher correlation matrices
    usage: dict                 # pull hazards, pitches per PA, start shares, reliever shares
    schedule_mix: dict          # nonconference opponent-tier mix by own tier and day type
    conference_weekends: int
    teams: list                 # (ncaa_team_id, conference, tier) for the real D1 structure
    talent_shape: dict = None   # "bat_HR" etc. -> (normal scores, standardized shape values) for rates drawn non-Gaussian


def load() -> Phase2Config:
    import csv
    base = phase1.load()
    inp = json.loads(INPUTS.read_text())
    t = base.outcome_probs
    hits = t["1B"] + t["2B"] + t["3B"]
    out_class = t["IP_OUT"] + t["SF"] + t["SH"] + t["FC"]
    bip_total = 1 - t["K"] - t["BB"] - t["HBP"] - t["HR"]
    league_rates = {"K": t["K"], "BB": t["BB"], "HBP": t["HBP"], "HR": t["HR"],
                    "BABIP": hits / (hits + out_class), "XBH": (t["2B"] + t["3B"]) / hits}
    teams = [(int(r["ncaa_team_id"]), r["conference"], r["tier"]) for r in csv.DictReader(TEAMS.open()) if r["tier"]]
    mix = inp["schedule_mix"]
    rs = json.loads(RUN_SCALE.read_text())
    tt = inp["team_talent"]
    draw, style = _team_draws(inp, rs)
    # game-level scale (scripts/solve_phase2_game_scale.py): the scoreboard fits runs per game, which
    # include run-rule and walk-off truncation, and truncation compresses lopsided games more, so the
    # engine's per-game response to a team's rating is not linear. One monotone map per side, the same
    # for every team, takes the scoreboard rating to engine units (k * x + q * x^2), solved so the same
    # fit on simulated seasons recovers each team's (o, d) with slope 1 and no curvature; eta is the
    # home edge that makes the simulated matchup-controlled home effect equal the scoreboard's
    gs = {"q_o": 0.0, "q_d": 0.0, **(GAME_SCALE_OVERRIDE or (json.loads(GAME_SCALE.read_text())["scale"] if GAME_SCALE.exists() else
                                    {"k_o": 1.0, "k_d": 1.0, "eta": tt["home_log_ratio"] - rs["home_structural"]["h0_log_ratio"]}))}
    return Phase2Config(
        base=base, league_rates=league_rates, roe_share_of_bip=t["ROE"] / bip_total,
        triple_share_of_xbh=t["3B"] / (t["2B"] + t["3B"]),
        tier_effects=inp["tier_effects_logit"], team_talent=tt, v_bat=tuple(rs["v_bat_unit"]),
        v_pit=tuple(rs["v_pit_unit"]), map_o=(gs["k_o"], gs["q_o"]), map_d=(gs["k_d"], gs["q_d"]), team_draw=draw, style_cov=style, home_eta=gs["eta"], talent=inp["talent"], correlation=inp["correlation"],
        usage=inp["usage"], schedule_mix=mix,
        conference_weekends=round(mix["conference_games_share"] * SEASON_GAMES / GAMES_PER_WEEKEND),
        teams=teams, talent_shape=load_talent_shapes(),
    )


def load_talent_shapes() -> dict:
    """Quantile tables (normal score -> offset in method-of-moments SD units: location + scale x
    standardized shape) of the fitted individual true-talent distributions that differ
    meaningfully from Gaussian (scripts/build_talent_shapes.py); rates not listed are Gaussian."""
    import numpy as np
    if TALENT_SHAPES_OVERRIDE is not None:
        return TALENT_SHAPES_OVERRIDE
    if not TALENT_SHAPES.exists():
        return {}
    out = {}
    for key, e in json.loads(TALENT_SHAPES.read_text())["rates"].items():
        if e.get("shape") == "shash":
            st = e["standard"]
            out[key] = (np.array(st["normal_scores"]), st["loc"] + st["scale"] * np.array(st["values"]))
    return out


def _team_draws(inp: dict, rs: dict) -> tuple[dict, dict]:
    """Team-level draw covariances on the log-runs scale.

    The scoreboard's true team covariance of (o, d) includes the team mean of its players'
    individual deviations; with usage shares s_k that part has variance
    sum s_k^2 * w' Sigma_e w (w: the engine's log-runs gradient). It is removed so the
    league generator's team effect plus its drawn players reproduce the scoreboard spread.
    Style: the play-by-play team covariance of rate offsets with its run-value direction
    projected out (P = I - v w' / w'v), so style moves rate mix but not runs.
    """
    import numpy as np
    w = np.array(rs["w_gradient_logR"])
    tal, cor, u = inp["talent"], inp["correlation"], inp["usage"]
    cb = np.array(cor["batter"]["matrix"])
    cp = np.zeros((6, 6)); cp[:5, :5] = np.array(cor["pitcher"]["matrix"]); cp[5, 5] = 1.0

    def cov(sd, c):
        sd = np.asarray(sd)
        return np.outer(sd, sd) * c
    # individual SDs on the logit scale: fitted distributions where a shape is fitted (talent_shapes)
    shp = load_talent_shapes()
    def sd_ind(side, r, g):
        tab = shp.get(f"{side}_{r}")
        return tal["batter" if side == "bat" else "pitcher"][r]["groups"][g]["sd_ind_logit"] * (float(np.std(_shape_draws(tab))) if tab else 1.0)
    se_bat = cov([sd_ind("bat", r, "regular") for r in RATES], cb)
    wk_games = WEEKS * GAMES_PER_WEEKEND / SEASON_GAMES
    sh = {"sp_weekend": u["starter_bf_share"]["weekend"] * wk_games, "sp_midweek": u["starter_bf_share"]["midweek"] * (1 - wk_games)}
    sh["rp"] = 1 - sum(sh.values())
    se_pit = sum(v * cov([sd_ind("pit", r, g) for r in RATES[:5]] + [0.0], cp) for g, v in sh.items())
    ind_o = u["batter_share_hhi"] * float(w @ se_bat @ w)
    ind_d = u["pitcher_share_hhi"] * float(w @ se_pit @ w)

    def psd(m):
        vals, vecs = np.linalg.eigh((m + m.T) / 2)
        return vecs @ np.diag(np.clip(vals, 0, None)) @ vecs.T
    draw = {}
    for t, e in inp["team_talent"]["tiers"].items():
        draw[t] = {"mean": (e["mean_o"], e["mean_d"]), "team_cov": psd(np.array(e["team_cov"]) - np.diag([ind_o, ind_d])),
                   "conf_cov": psd(np.array(e["conf_cov"])), "individual_var": (ind_o, ind_d)}
    style = {}
    for side, v, sds, c in (("bat", rs["v_bat_unit"], [tal["batter"][r]["sd_team_logit"] for r in RATES], cb),
                            ("pit", rs["v_pit_unit"], [tal["pitcher"][r]["sd_team_logit"] for r in RATES[:5]] + [0.0], cp)):
        v = np.array(v)
        P = np.eye(6) - np.outer(v, w) / float(w @ v)
        style[side] = psd(P @ cov(sds, c) @ P.T)
    return draw, style


def _shape_draws(tab) -> "np.ndarray":
    """The fitted distribution's values at the normal quantiles of a fixed fine grid (for its SD)."""
    import numpy as np
    from math import erf, sqrt
    p = (np.arange(20000) + 0.5) / 20000
    # normal scores of p by bisection-free inversion: interpolate the CDF on a fine grid
    xs = np.linspace(-6, 6, 24001)
    cdf = np.array([0.5 * (1 + erf(x / sqrt(2))) for x in xs])
    u = np.interp(p, cdf, xs)
    return np.interp(u, tab[0], tab[1])
