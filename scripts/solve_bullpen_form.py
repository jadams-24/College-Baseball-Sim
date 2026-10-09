"""Solve the bullpen form scale in the engine (variance stage, owner decision 2026-10-09, option A).

The relief choice's recent-form coefficients (scripts/build_bullpen_form.py) are fitted on real staffs, whose observed
form also carries each pitcher's quality; the engine's roles already sort by quality. So the form terms (last outing and
prior three; the no-outing-yet terms stay as fitted) are multiplied by one scale, solved so the engine's within-pitcher
slope of the next entry's blowout share on the runs allowed last outing (P4 staffs, engine/bullpen_metrics.py) equals the
real P4 value. Secant on the scale over simulated seasons (seeds 770001+, not the report seeds); writes solved_scale into
data/ncaa_2025/derived/bullpen_form_2025.json and prints every gate metric at each step.
    python3 scripts/solve_bullpen_form.py [--seasons 4] [--start 1.0 2.0] [--iters 4] [--eval 1.0]
"""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SEED0 = 770001


def season_metrics(args) -> dict:
    scale, seed = args
    from config import phase2, phase6
    from engine import bullpen_metrics as bm
    from engine.season import simulate_season
    base = phase6.load_bullpen_form()
    phase6.load_bullpen_form = lambda: {**base, "solved_scale": scale}       # this process only
    res = simulate_season(phase2.load(), seed)
    o = bm.frame(res["bullpen_rows"].tolist())
    tier = {t.tid: t.tier for t in res["league"].teams}
    out = {}
    for name, keep in (("p4", lambda t: tier[t] == "p4"), ("all", lambda t: True)):
        sub = o[o.team.map(keep)]
        out[name] = {**bm.feedback_slopes(sub), **{f"terc_{k}": v for k, v in bm.workload_terciles(sub).items()}}
    return out


def evaluate(scale: float, n: int) -> dict:
    with Pool(min(4, n)) as pool:
        per = pool.map(season_metrics, [(scale, SEED0 + i) for i in range(n)])
    out = {}
    for name in ("p4", "all"):
        for k in ("blow", "absm", "terc_low", "terc_mid", "terc_high", "terc_low_minus_high"):
            v = np.array([p[name][k] for p in per])
            out[f"{name}_{k}"] = (float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else float("nan"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=4)
    ap.add_argument("--start", type=float, nargs=2, default=(1.0, 2.0))
    ap.add_argument("--iters", type=int, default=4)
    ap.add_argument("--eval", type=float, default=None, help="evaluate one scale and stop")
    a = ap.parse_args()
    from config.phase6 import BULLPEN_FORM
    bf = json.loads(BULLPEN_FORM.read_text())
    target = bf["gate"]["p4"]["blow"]["value"]
    show = lambda s, r: print(f"scale {s:.3f}: " + ", ".join(f"{k} {v[0]:+.4f}±{v[1]:.4f}" for k, v in r.items()), flush=True)  # noqa: E731
    if a.eval is not None:
        show(a.eval, evaluate(a.eval, a.seasons))
        return
    xs, ys = list(a.start), []
    for x in xs:
        r = evaluate(x, a.seasons); show(x, r); ys.append(r["p4_blow"][0] - target)
    for _ in range(a.iters):
        x0, x1, y0, y1 = xs[-2], xs[-1], ys[-2], ys[-1]
        if abs(y1 - y0) < 1e-12:
            break
        x2 = float(np.clip(x1 - y1 * (x1 - x0) / (y1 - y0), 0.0, 10.0))
        r = evaluate(x2, a.seasons); show(x2, r)
        xs.append(x2); ys.append(r["p4_blow"][0] - target)
        if abs(ys[-1]) < r["p4_blow"][1]:
            break
    best = xs[int(np.argmin(np.abs(ys)))]
    bf["solved_scale"] = round(best, 4)
    bf["solve"] = {"target_p4_blow": target, "steps": [{"scale": x, "p4_blow_minus_target": y} for x, y in zip(xs, ys)],
                   "seasons_per_step": a.seasons, "seeds_from": SEED0}
    BULLPEN_FORM.write_text(json.dumps(bf, indent=1, default=float) + "\n")
    print("solved_scale", best)


if __name__ == "__main__":
    main()
