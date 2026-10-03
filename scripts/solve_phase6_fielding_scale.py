"""The engine's run response to a team's error log-odds, for the fielding / pitching split of run
prevention (Phase 6).

A team's scoreboard run prevention d already includes its fielding. The engine draws the team's
error log-odds e from the play-by-play error model (team term tied to d, plus its fielders), so the
pitching staff gets d minus the fielding part: pitching = g(d) + phi * e in engine log runs, with phi
the engine's log-runs response to e. phi is measured by shifting every team's error log-odds by
-STEP and +STEP on the same calibration seeds: phi = (log R/G at +STEP - log R/G at -STEP) / (2 STEP).
For comparison the play-by-play gives 0.80 runs per error play (state-matched run expectancy: a
reached-on-error against a batted-ball out, an error on any other play against the same result
without one) and 1.07 errors per team-game per unit of e, so phi_data = 0.80 x 1.07 / R/G.
Output: the "fielding_scale" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/solve_phase6_fielding_scale.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase2  # noqa: E402
from config.phase6 import INPUTS6  # noqa: E402

SEEDS = (930001, 930002)   # calibration seeds, disjoint from the report's and the other solves'
STEP = 0.5


def _season(args) -> float:
    seed, shift = args
    import engine.game2 as g2
    orig = g2.PlayerGameEngine.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        self.delta["err"] += shift
    g2.PlayerGameEngine.__init__ = init
    from engine.season import simulate_season
    res = simulate_season(phase2.load(), seed)
    tg = res["team_game_rows"]
    return float(tg[:, 1].mean()), float(tg[:, 8].mean())


def main() -> None:
    jobs = [(s, x) for s in SEEDS for x in (-STEP, STEP)]
    with ProcessPoolExecutor(4) as ex:
        out = dict(zip(jobs, ex.map(_season, jobs)))
    phis = [(np.log(out[(s, STEP)][0]) - np.log(out[(s, -STEP)][0])) / (2 * STEP) for s in SEEDS]
    errs = [(out[(s, STEP)][1] - out[(s, -STEP)][1]) / (2 * STEP) for s in SEEDS]
    blk = {"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": list(SEEDS), "step": STEP,
           "phi_engine": round(float(np.mean(phis)), 4), "phi_by_seed": [round(float(v), 4) for v in phis],
           "errors_per_unit_engine": round(float(np.mean(errs)), 3),
           "data": {"runs_per_error_play": 0.803, "errors_per_unit": 1.068, "phi_data": round(0.803 * 1.068 / 6.75, 4)}}
    cur = json.loads(INPUTS6.read_text())
    cur["fielding_scale"] = blk
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in blk.items() if k != "_note"}, indent=1))


if __name__ == "__main__":
    main()
