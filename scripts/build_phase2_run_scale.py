"""The engine's run scale: how log runs respond to talent offsets.

Team strength is estimated from the scoreboard on the log-runs scale (see
build_phase2_teams.py). To put it into the engine, a team's offense o (log runs above
an average team) becomes a logit offset o * v_bat on its batters' rates, and its run
prevention d becomes -d * v_pit on its pitchers' rates. This script measures the
engine's response so that one unit of o or d is one unit of log runs:

  w        gradient of log(runs per half-inning) with respect to each rate's logit
           offset at league average (finite differences, common random numbers)
  v_bat    direction of the 2025 batting tier contrast (P4 minus low, from the additive
           play-by-play fit), scaled so d log R / d s = 1 along it
  v_pit    the same for the pitching tier contrast (low minus P4: worse run prevention)
  linearity  log R on a grid of s in [-0.6, 0.6] along each direction, and a joint
           batting + pitching point (additivity)
  h0       log(E home runs / E away runs) between identical teams over full games:
           the structural home effect of batting last (no bottom of the 9th when ahead,
           walk-offs end the game). Home talent advantage is the scoreboard's
           matchup-controlled home effect minus h0.

Output: data/ncaa_2025/derived/phase2_run_scale_2025.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import phase2  # noqa: E402
from engine.decider import Decision, LeagueAverageDecider  # noqa: E402
from engine.game2 import GameState2, PlayerGameEngine  # noqa: E402
from engine.league import Player, Team  # noqa: E402

RATES = phase2.RATES
OUT = Path("data/ncaa_2025/derived/phase2_run_scale_2025.json")
INPUTS = Path("data/ncaa_2025/derived/phase2_inputs_2025.json")
N_HALF = 300_000      # half-innings per gradient / grid point
N_GAMES = 100_000     # games for the home effect
STEP = 0.25           # finite-difference step (logit)
GRID = (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6)
SEED = 7101


class _League:
    def __init__(self):
        self.location = {r: 0.0 for r in RATES}


def _engine():
    cfg = phase2.load()
    bs = [[0] * 13 for _ in range(16)]
    ps = [[0] * 13 for _ in range(16)]
    eng = PlayerGameEngine(cfg, _League(), bs, ps)
    eng.home_bat = eng.home_bat * 0.0  # measure the engine with no home talent edge
    eng.home_pit = eng.home_pit * 0.0
    return eng


def half_runs(args) -> float:
    """Mean runs per half-inning: nine identical batters (offset zb) against one pitcher (zp)."""
    zb, zp, n, seed = args
    eng = _engine()
    bat = [Player(i, "b", 0, "bat", "regular", np.array(zb, float)) for i in range(9)]
    pit = Player(9, "p", 1, "pit", "rp", np.array(zp, float))
    t = Team(0, "t", 0, "mid")
    st = GameState2(np.random.default_rng(seed), t, t, True)
    st.lineup = {"away": bat}
    st.pitcher = {"home": pit}
    st.outing = {"home": {"starter": True, "pitches": 0, "runs": 0}}
    st.half, tot = "T", 0
    dec = LeagueAverageDecider()
    for _ in range(n):
        st.score["away"], st.inning = 0, 1
        eng._half(st, dec)
        tot += st.score["away"]
    return tot / n


class _Fixed(LeagueAverageDecider):
    def lineup(self, state, team):
        return state.team_obj[team].batters

    def starting_pitcher(self, state, team):
        return state.team_obj[team].weekend_sp[0]

    def pitching_change(self, state):
        return Decision.NO


def home_games(args) -> tuple:
    n, seed = args
    eng = _engine()
    teams = []
    for k in range(2):
        t = Team(k, str(k), 0, "mid")
        t.batters = [Player(10 * k + i, "b", k, "bat", "regular", np.zeros(6)) for i in range(9)]
        t.weekend_sp = [Player(10 * k + 9, "p", k, "pit", "sp_weekend", np.zeros(6))]
        teams.append(t)
    eng.bstats = [[0] * 13 for _ in range(32)]
    eng.pstats = [[0] * 13 for _ in range(32)]
    rng = np.random.default_rng(seed)
    dec = _Fixed()
    h = a = hw = 0
    for _ in range(n):
        st = eng.play(rng, teams[0], teams[1], True, dec)
        h += st.score["home"]; a += st.score["away"]; hw += st.score["home"] > st.score["away"]
    return h, a, hw, n


def main() -> None:
    inp = json.loads(INPUTS.read_text())
    fx = inp["tier_effects_logit"]
    vb = np.array([fx[r]["bat"]["p4"] - fx[r]["bat"]["low"] for r in RATES])
    vp = np.array([fx[r]["pit"]["low"] - fx[r]["pit"]["p4"] for r in RATES])
    zero = np.zeros(6)
    jobs = [(zero, zero, N_HALF, SEED)]
    for i in range(6):
        e = np.zeros(6); e[i] = STEP
        jobs += [(e, zero, N_HALF, SEED), (-e, zero, N_HALF, SEED)]
    for s in GRID:
        jobs.append((s * vb, zero, N_HALF, SEED))
    for s in GRID:
        jobs.append((zero, s * vp, N_HALF, SEED))
    with ProcessPoolExecutor(4) as ex:
        out = list(ex.map(half_runs, jobs))
        hg = list(ex.map(home_games, [(N_GAMES // 4, SEED + k) for k in range(4)]))
    base = out[0]
    w = [(np.log(out[1 + 2 * i]) - np.log(out[2 + 2 * i])) / (2 * STEP) for i in range(6)]
    gb = np.log(out[13:13 + len(GRID)])
    gp = np.log(out[13 + len(GRID):])
    sb = float(np.polyfit(GRID, gb, 1)[0])
    sp = float(np.polyfit(GRID, gp, 1)[0])
    curv_b = float(np.polyfit(GRID, gb, 2)[0])
    curv_p = float(np.polyfit(GRID, gp, 2)[0])
    vb_u, vp_u = vb / sb, vp / sp
    # additivity: +0.4 log runs from batting and +0.4 from pitching together
    with ProcessPoolExecutor(4) as ex:
        joint = list(ex.map(half_runs, [(0.4 * vb_u, 0.4 * vp_u, N_HALF, SEED), (-0.4 * vb_u, -0.4 * vp_u, N_HALF, SEED),
                                        (0.4 * vb_u, -0.4 * vp_u, N_HALF, SEED)]))
    H = sum(x[0] for x in hg); A = sum(x[1] for x in hg); HW = sum(x[2] for x in hg); NG = sum(x[3] for x in hg)
    h0 = float(np.log(H / A))
    res = {
        "_note": __doc__, "built": dt.date.today().isoformat(), "rates": list(RATES), "seed": SEED, "n_half_innings": N_HALF, "n_games": NG,
        "runs_per_half_inning_league": round(base, 5),
        "w_gradient_logR": [round(float(x), 4) for x in w],
        "v_bat_unit": [round(float(x), 5) for x in vb_u], "v_pit_unit": [round(float(x), 5) for x in vp_u],
        "slope_raw": {"bat": round(sb, 4), "pit": round(sp, 4)},
        "linearity": {"grid": list(GRID), "logR_bat": [round(float(x), 4) for x in gb], "logR_pit": [round(float(x), 4) for x in gp],
                      "quadratic_coef": {"bat": round(curv_b, 4), "pit": round(curv_p, 4)}},
        "additivity": {"base_logR": round(float(np.log(base)), 4),
                       "both_plus_0.4": round(float(np.log(joint[0]) - np.log(base)), 4),
                       "both_minus_0.4": round(float(np.log(joint[1]) - np.log(base)), 4),
                       "bat_plus_pit_minus_0.4": round(float(np.log(joint[2]) - np.log(base)), 4),
                       "expected": [0.8, -0.8, 0.0]},
        "home_structural": {"h0_log_ratio": round(h0, 4), "home_runs_per_game": round(H / NG, 4), "away_runs_per_game": round(A / NG, 4),
                            "home_win_pct": round(HW / NG, 4)},
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "_note"}, indent=1))


if __name__ == "__main__":
    main()
