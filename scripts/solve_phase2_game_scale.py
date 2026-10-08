"""Solve the engine's game-level run scale and home edge.

Team strength (o, d) and the home effect h come from a quasi-Poisson fit of runs per
team-game on the 2025 scoreboard (build_phase2_teams.py). Runs per game include the
run rule and the skipped or walk-off bottom of the ninth, which compress lopsided games,
while the half-inning scale (build_phase2_run_scale.py) has no truncation. So the same
fit is run on simulated seasons and three numbers are found by fixed-point iteration:
  map_o, map_d  one monotone map per side from the scoreboard rating x to engine units,
             g(x) = k x + q x^2, the same for every team. The fitted o (d) of simulated
             teams is regressed on their true rating, pooled over seasons:
             fitted = a + b x + c x^2. The target is b = 1, c = 0 (the fit recovers the
             rating). Composition update g <- g o (b x + c x^2)^-1:
             k <- k / b,  q <- q / b^2 - k c / b^3.
             (A single linear k left the response convex: within-P4 slope 1.10, low 0.99,
             because run-rule truncation compresses lopsided games, not close ones.)
  eta        home talent edge, so the simulated fitted home effect equals the
             scoreboard's: eta <- eta + (h_scoreboard - h_sim)
Nothing else is matched: runs, spreads and gate rows are not used. Calibration seeds
(910000+) are disjoint from the location solve and the report.
--warm starts from the current solved scale (a re-solve after the engine changed: owner rule 2026-10-08, scripts/check_drift.py).
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
ITERS = 4
WORKERS = 4


def _season(args) -> dict:
    scale, seed = args
    phase2.GAME_SCALE_OVERRIDE = dict(scale)
    res = simulate_season(phase2.load(), seed)
    g = pd.DataFrame(res["games"], columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    names = sorted(set(g.home) | set(g.away))
    f = fit(g, names)
    to = [res["league"].teams[t].o for t in names]; td = [res["league"].teams[t].d for t in names]
    return {"true_o": to, "fit_o": f["o"].tolist(), "true_d": td, "fit_d": f["d"].tolist(), "h": f["h"], "phi": f["phi"]}


def _quad(x, y) -> tuple:
    """fitted = a + b x + c x^2 (least squares); returns (b, c)."""
    x, y = np.asarray(x), np.asarray(y)
    X = np.column_stack([np.ones_like(x), x, x ** 2])
    a, b, c = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(b), float(c)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm", action="store_true", help="start from the current solved scale (a drift re-solve, scripts/check_drift.py)")
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--seasons", type=int, default=len(SEEDS), help="calibration seasons per iteration (910001 on)")
    args = ap.parse_args()
    seeds = tuple(range(SEEDS[0], SEEDS[0] + args.seasons))
    cfg = phase2.load()
    h_real = cfg.team_talent["home_log_ratio"]
    rs = json.loads(phase2.RUN_SCALE.read_text())
    scale = {"k_o": 1.0, "q_o": 0.0, "k_d": 1.0, "q_d": 0.0, "eta": h_real - rs["home_structural"]["h0_log_ratio"]}
    prior = json.loads(OUT.read_text()) if OUT.exists() else None
    if args.warm and prior:
        scale = dict(prior["scale"])
    history = (prior.get("history", []) if args.warm and prior else [])
    for it in range(args.iters):
        with ProcessPoolExecutor(WORKERS) as ex:
            out = list(ex.map(_season, [(scale, s) for s in seeds]))
        m = {"h": float(np.mean([x["h"] for x in out])), "phi": float(np.mean([x["phi"] for x in out]))}
        new = dict(scale)
        for side in ("o", "d"):
            b, c = _quad(sum((x[f"true_{side}"] for x in out), []), sum((x[f"fit_{side}"] for x in out), []))
            m[f"b_{side}"], m[f"c_{side}"] = b, c
            k, q = scale[f"k_{side}"], scale[f"q_{side}"]
            new[f"k_{side}"], new[f"q_{side}"] = k / b, q / b ** 2 - k * c / b ** 3
        new["eta"] = scale["eta"] + (h_real - m["h"])
        history.append({"iteration": it, "scale": dict(scale), "fitted": m, **({"warm_start": dt.date.today().isoformat()} if args.warm else {})})
        print(it, {k: round(v, 4) for k, v in scale.items()}, {k: round(v, 4) for k, v in m.items()})
        scale = new
    OUT.write_text(json.dumps({"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": seeds, "h_scoreboard": h_real,
                               "scale": scale, "history": history}, indent=1) + "\n")
    print("scale:", {k: round(v, 4) for k, v in scale.items()})


if __name__ == "__main__":
    main()
