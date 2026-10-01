"""Diagnostic: the top tail of team run prevention, simulated vs real.

Fits the scoreboard decomposition (build_phase2_teams.fit) to the real 2025 games and to
simulated seasons, and compares the recovered run-prevention ratings d (and offense o):
tier means, within-tier SD, and the top 5% / top 1% overall and within P4. Recovered
ratings include estimation noise in both, so like is compared with like.
    python3 scripts/diag_phase2_defense_tail.py --seasons 8 --seed 20251000
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_phase2_teams import TIERS, fit, load  # noqa: E402
from config import phase2  # noqa: E402
from engine.season import simulate_season  # noqa: E402


def summarize(o, d, tiers) -> dict:
    out = {}
    for name, v in (("o", np.asarray(o)), ("d", np.asarray(d))):
        tiers = np.asarray(tiers)
        r = {"top5_all": float(np.mean(np.sort(v)[-max(1, round(0.05 * len(v))):])), "top1_all": float(np.mean(np.sort(v)[-max(1, round(0.01 * len(v))):])),
             "max_all": float(v.max())}
        p4 = np.sort(v[tiers == "p4"])
        r["top5_p4"] = float(np.mean(p4[-max(1, round(0.05 * len(p4))):])); r["top1_p4"] = float(p4[-1])
        for t in TIERS:
            r[f"mean_{t}"] = float(v[tiers == t].mean()); r[f"sd_{t}"] = float(v[tiers == t].std(ddof=1))
        out[name] = r
    return out


def _season(seed: int) -> dict:
    res = simulate_season(phase2.load(), seed)
    g = pd.DataFrame(res["games"], columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    names = sorted(set(g.home) | set(g.away))
    f = fit(g, names)
    teams = res["league"].teams
    tiers = [teams[t].tier for t in names]
    return {"fitted": summarize(f["o"], f["d"], tiers), "true": summarize([teams[t].o for t in names], [teams[t].d for t in names], tiers)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20251000)
    a = ap.parse_args()
    sb, names, tier, conf = load()
    f = fit(sb, names)
    real = summarize(f["o"], f["d"], [tier[t] for t in names])
    with ProcessPoolExecutor(4) as ex:
        sims = list(ex.map(_season, [a.seed + i for i in range(a.seasons)]))
    keys = list(real["d"])
    print(f"{'stat':10} {'real d':>8} {'sim d':>8} {'sim SE':>7} {'true d':>8} | {'real o':>8} {'sim o':>8} {'sim SE':>7}")
    out = {"real": real, "sim_fitted_mean": {}, "sim_true_mean": {}}
    for k in keys:
        row = []
        for side in ("d", "o"):
            v = np.array([s["fitted"][side][k] for s in sims]); tv = np.array([s["true"][side][k] for s in sims])
            out["sim_fitted_mean"].setdefault(side, {})[k] = float(v.mean()); out["sim_true_mean"].setdefault(side, {})[k] = float(tv.mean())
            row.append((real[side][k], v.mean(), v.std(ddof=1) / np.sqrt(len(v)), tv.mean()))
        (rd, sd, sed, td), (ro, so, seo, _) = row
        print(f"{k:10} {rd:8.3f} {sd:8.3f} {sed:7.3f} {td:8.3f} | {ro:8.3f} {so:8.3f} {seo:7.3f}")
    print(json.dumps({"n_seasons": a.seasons}))


if __name__ == "__main__":
    main()
