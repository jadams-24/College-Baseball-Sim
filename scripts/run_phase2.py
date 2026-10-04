"""Simulate Phase 2 seasons and write reports/phase2.md (+ .json).
    python3 scripts/run_phase2.py --seasons 20 --seed 20251000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import phase2  # noqa: E402
from engine.report2 import aggregate, build_report, season_metrics  # noqa: E402
from engine.season import simulate_season  # noqa: E402


REPORT_SEASONS = 40     # the report's run, and CI's own gate run (tests/conftest.py); 40 since 2026-10-04 (owner decision)
REPORT_SEED = 20251000


def one(seed: int) -> dict:
    return season_metrics(simulate_season(phase2.load(), seed))


def run(seasons: int, seed: int, workers: int) -> tuple[dict, list]:
    seeds = [seed + i for i in range(seasons)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        ms = list(ex.map(one, seeds))
    return aggregate(ms), seeds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=REPORT_SEASONS)
    ap.add_argument("--seed", type=int, default=REPORT_SEED)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="reports/phase2.md")
    a = ap.parse_args()
    t0 = time.time()
    agg, seeds = run(a.seasons, a.seed, a.workers)
    md, status = build_report(agg, seeds)
    Path(a.out).write_text(md)
    Path(a.out).with_suffix(".json").write_text(json.dumps({"aggregate": agg, "status": status}, indent=1, default=float) + "\n")
    print(md)
    print(f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
