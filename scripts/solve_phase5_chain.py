"""Solve the league base chain of the pitch model so that the simulated league's pitch events by
count equal the data's.

The data's per-count event shares (data/ncaa_2025/derived/phase5_pitch_2025.json, chain.by_count)
are pooled over every pitcher and batter, weighted by who reaches each count. The engine tilts the
base chain for each matchup along the measured player directions (engine/pitch.py), and the
pooled result of those tilted chains is not the base chain: deep-count pitches come
disproportionately from wild pitchers and patient batters, and tilting the pooled shares a second
time skews the aggregate (fewer pitches per PA than the data). So the base chain is found by
fixed-point iteration on simulated seasons, every count and event at once:
    q0(c, e) <- q0(c, e) * data(c, e) / sim(c, e), renormalised per count.
Nothing else is matched: pitches per PA, count reach, outcomes by count and starter pitch counts are
the gate, not targets. PA outcomes are untouched (each PA's outcome is drawn first). Calibration
seeds (950000+) are disjoint from gate and other calibration seeds.
Output: data/ncaa_2025/derived/phase5_chain_solved_2025.json
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
from config.phase5 import EVENTS, SOLVED  # noqa: E402
from config.phase5 import load as load_pitch  # noqa: E402
from engine.pitch import COUNTS  # noqa: E402
from engine.season import simulate_season  # noqa: E402

SEEDS = tuple(range(950001, 950005))
ITERS = 4
WORKERS = 4


def season_events(seed: int) -> np.ndarray:
    return simulate_season(phase2.load(), seed)["pitch_rec"]["ev"]


def main() -> None:
    data = load_pitch()["chain"]["by_count"]
    target = np.array([data[f"{b}-{s}"] for b, s in COUNTS], float)
    q0 = target.copy()
    log = []
    for it in range(ITERS):
        SOLVED.write_text(json.dumps({"by_count": {f"{b}-{s}": q0[i].tolist() for i, (b, s) in enumerate(COUNTS)}}) + "\n")
        with ProcessPoolExecutor(WORKERS) as ex:
            ev = sum(ex.map(season_events, SEEDS))
        sim = ev / ev.sum(axis=1, keepdims=True)
        gap = float(np.max(np.abs(sim - target)))
        log.append({"iter": it, "max_abs_gap": round(gap, 5), "pitches": int(ev.sum())})
        print(log[-1], flush=True)
        ratio = np.where(sim > 0, target / np.maximum(sim, 1e-12), 1.0)
        q0 = q0 * ratio
        q0 /= q0.sum(axis=1, keepdims=True)
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": list(SEEDS), "iterations": log, "events": list(EVENTS),
           "by_count": {f"{b}-{s}": [round(float(x), 6) for x in q0[i]] for i, (b, s) in enumerate(COUNTS)}}
    SOLVED.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
