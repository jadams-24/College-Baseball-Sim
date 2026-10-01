"""Solve the engine's game-level run scale and home edge.

Team strength (o, d) and the home effect h come from a quasi-Poisson fit of runs per
team-game on the 2025 scoreboard (build_phase2_teams.py). Runs per game include the
run rule and the skipped or walk-off bottom of the ninth, which compress lopsided games,
while the half-inning scale (build_phase2_run_scale.py) has no truncation. So the same
fit is run on simulated seasons and three numbers are found by fixed-point iteration:
  k_o, k_d   multipliers on the batting / pitching quality directions, so the fitted
             o (d) of simulated teams regresses on their true o (d) with slope 1:
             k <- k / slope
  eta        home talent edge, so the simulated fitted home effect equals the
             scoreboard's: eta <- eta + (h_scoreboard - h_sim)
Nothing else is matched: runs, spreads and gate rows are not used. Calibration seeds
(910000+) are disjoint from the location solve and the report.
Output: data/ncaa_2025/derived/phase2_game_scale_2025.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_phase2_teams import fit  # noqa: E402
from config import phase2  # noqa: E402
from engine.season import simulate_season  # noqa: E402

OUT = Path("data/ncaa_2025/derived/phase2_game_scale_2025.json")
SEEDS = tuple(range(910001, 910009))
ITERS = 3
WORKERS = 4


def _season(args) -> dict:
    scale, seed = args
    phase2.GAME_SCALE_OVERRIDE = dict(scale)
    res = simulate_season(phase2.load(), seed)
    g = pd.DataFrame(res["games"], columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    names = sorted(set(g.home) | set(g.away))
    f = fit(g, names)
    to = np.array([res["league"].teams[t].o for t in names]); td = np.array([res["league"].teams[t].d for t in names])
    so = float(np.cov(f["o"], to)[0, 1] / np.var(to, ddof=1)); sd = float(np.cov(f["d"], td)[0, 1] / np.var(td, ddof=1))
    return {"slope_o": so, "slope_d": sd, "h": f["h"], "phi": f["phi"]}


def main() -> None:
    cfg = phase2.load()
    h_real = cfg.team_talent["home_log_ratio"]
    rs = json.loads(phase2.RUN_SCALE.read_text())
    scale = {"k_o": 1.0, "k_d": 1.0, "eta": h_real - rs["home_structural"]["h0_log_ratio"]}
    history = []
    for it in range(ITERS):
        with ProcessPoolExecutor(WORKERS) as ex:
            out = list(ex.map(_season, [(scale, s) for s in SEEDS]))
        m = {k: float(np.mean([x[k] for x in out])) for k in out[0]}
        history.append({"iteration": it, "scale": dict(scale), "fitted": m})
        print(it, {k: round(v, 4) for k, v in scale.items()}, {k: round(v, 4) for k, v in m.items()})
        scale = {"k_o": scale["k_o"] / m["slope_o"], "k_d": scale["k_d"] / m["slope_d"], "eta": scale["eta"] + (h_real - m["h"])}
    OUT.write_text(json.dumps({"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": SEEDS, "h_scoreboard": h_real,
                               "scale": scale, "history": history}, indent=1) + "\n")
    print("scale:", {k: round(v, 4) for k, v in scale.items()})


if __name__ == "__main__":
    main()
