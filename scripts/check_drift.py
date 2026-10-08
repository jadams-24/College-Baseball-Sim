"""Drift check on the calibrated maps (owner rule 2026-10-08: every PR that changes engine behavior runs it; a check beyond
2 SE is re-solved in the same PR, so no map drifts silently across PRs).

A short run of the current engine (DRIFT_SEEDS, disjoint from the report's and every solver's seeds) measures, as its solver
does, whether each calibrated map still recovers its target:
  strength map   the scoreboard fit (scripts/build_phase2_teams.fit) on each simulated season, fitted o (d) regressed on the
                 drawn rating: fitted = a + b x + c x^2, targets b = 1, c = 0 (scripts/solve_phase2_game_scale.py); also the
                 tier means of recovered minus drawn (both centred over teams), the Phase 6 recovery rows
  home edge      the fitted home log ratio against the scoreboard's (its SE included)
  pitch chain    pitch events by count against the data's (scripts/solve_phase5_chain.py): chi-square over the counts x events
                 with the data's and the simulation's sampling error, and the largest per-cell z
SEs are between seasons (each season is one independent sample). A row is flagged when |z| > 2 (chain: chi-square p < .05).
Writes reports/drift_check.md and reports/drift_check.json.
    python3 scripts/check_drift.py [--seasons 8] [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_phase2_teams import fit  # noqa: E402
from config import phase2  # noqa: E402
from config.phase5 import load as load_pitch  # noqa: E402
from engine.pitch import COUNTS  # noqa: E402
from engine.season import simulate_season  # noqa: E402

DRIFT_SEEDS = tuple(range(970001, 970041))     # disjoint from the report (20251000+) and the solvers (910000+, 950000+)
Z_FLAG = 2.0


def _quad(x, y) -> tuple:
    X = np.column_stack([np.ones_like(x), x, x ** 2])
    a, b, c = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(b), float(c)


def season(seed: int) -> dict:
    res = simulate_season(phase2.load(), seed)
    lg = res["league"]
    g = pd.DataFrame(res["games"], columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    names = sorted(set(g.home) | set(g.away))
    f = fit(g, names)
    out = {"h": float(f["h"]), "ev": res["pitch_rec"]["ev"].astype(float)}
    tier = np.array([lg.teams[t].tier for t in names])
    for side in ("o", "d"):
        x = np.array([getattr(lg.teams[t], side) for t in names], float)
        y = np.asarray(f[side], float)
        out[f"b_{side}"], out[f"c_{side}"] = _quad(x, y)
        xc = x - x.mean()        # the fit's ratings are centred over teams: the drawn ones too (engine/report6.py, recovery rows)
        for tr in ("p4", "mid", "low"):
            k = tier == tr
            out[f"rec_{side}_{tr}"] = float(y[k].mean() - xc[k].mean())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    seeds = DRIFT_SEEDS[: a.seasons]
    with ProcessPoolExecutor(a.workers) as ex:
        runs = list(ex.map(season, seeds))
    summarize(runs, seeds)


def summarize(runs: list, seeds: tuple) -> None:
    n = len(runs)
    cfg = phase2.load()
    rows = []

    def row(name, label, vals, target, target_se=0.0):
        v = np.array(vals, float)
        m, se = float(v.mean()), float(v.std(ddof=1) / math.sqrt(n))
        z = (m - target) / math.sqrt(se ** 2 + target_se ** 2)
        rows.append({"key": name, "label": label, "value": m, "se": se, "target": target, "target_se": target_se, "z": z,
                     "flag": abs(z) > Z_FLAG})
    for side, lab in (("o", "offense"), ("d", "run prevention")):
        row(f"b_{side}", f"Strength map, {lab}: slope of recovered on drawn", [r[f"b_{side}"] for r in runs], 1.0)
        row(f"c_{side}", f"Strength map, {lab}: curvature", [r[f"c_{side}"] for r in runs], 0.0)
        for tr in ("p4", "mid", "low"):
            row(f"rec_{side}_{tr}", f"Recovered minus drawn, {lab}, {tr} (tier mean)", [r[f"rec_{side}_{tr}"] for r in runs], 0.0)
    row("home", "Home edge: fitted home log ratio", [r["h"] for r in runs], cfg.team_talent["home_log_ratio"],
        cfg.team_talent["home_log_ratio_se"])
    # pitch chain: shares by count and event, the data's sampling error from its pitch counts
    chain = load_pitch()["chain"]
    data = np.array([chain["by_count"][f"{b}-{s}"] for b, s in COUNTS], float)
    n_data = np.array([chain["n_pitches_by_count"][f"{b}-{s}"] for b, s in COUNTS], float)
    shares = np.array([r["ev"] / r["ev"].sum(axis=1, keepdims=True) for r in runs])
    sim, sim_se = shares.mean(axis=0), shares.std(axis=0, ddof=1) / math.sqrt(n)
    data_se = np.sqrt(data * (1 - data) / n_data[:, None])
    keep = data > 0
    zc = (sim - data)[keep] / np.sqrt(sim_se[keep] ** 2 + data_se[keep] ** 2)
    chi2, df = float((zc ** 2).sum()), int(keep.sum() - len(COUNTS))      # each count's shares sum to 1
    # Wilson-Hilferty normal approximation of the chi-square upper tail
    zwh = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    p = 0.5 * math.erfc(zwh / math.sqrt(2))
    rows.append({"key": "chain", "label": "Pitch chain: events by count against the data (chi-square / df, p)", "value": chi2 / df,
                 "se": None, "target": 1.0, "target_se": None, "z": float(np.max(np.abs(zc))), "p": p, "df": df, "flag": p < 0.05})
    out = {"seasons": n, "seeds": [seeds[0], seeds[-1]], "rows": rows,
           "flagged": [r["key"] for r in rows if r["flag"]]}
    (ROOT / "reports/drift_check.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    md = ["# Drift check on the calibrated maps", "",
          f"{n} seasons of the current engine (seeds {seeds[0]}-{seeds[-1]}). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in "
          "the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).", "",
          "| Check | Value | Target | z | Flag |", "|---|---|---|---|---|"]
    for r in rows:
        if r["key"] == "chain":
            md.append(f"| {r['label']} | {r['value']:.2f} (df {r['df']}) | 1 | max cell z {r['z']:.1f}, p {r['p']:.3f} | {'RE-SOLVE' if r['flag'] else 'ok'} |")
        else:
            md.append(f"| {r['label']} | {r['value']:+.4f} ± {r['se']:.4f} | {r['target']:+.4f} | {r['z']:+.2f} | {'RE-SOLVE' if r['flag'] else 'ok'} |")
    (ROOT / "reports/drift_check.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
