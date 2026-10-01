"""Simulate seasons once and write both reports: Phase 2 (every Phase 1 and Phase 2 gate
row, on the Phase 4 engine) and Phase 4 (the ratings round trip).
    python3 scripts/run_phase4.py            # the report's run: 20 seasons, seed 20251000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import phase2  # noqa: E402
from engine.report2 import aggregate, build_report, season_metrics  # noqa: E402
from engine.report4 import aggregate4, build_report4, season_extract4  # noqa: E402
from engine.season import simulate_season  # noqa: E402
from run_phase2 import REPORT_SEASONS, REPORT_SEED  # noqa: E402


def one(seed: int) -> tuple:
    res = simulate_season(phase2.load(), seed)
    return season_metrics(res), season_extract4(res)


def run(seasons: int, seed: int, workers: int) -> tuple:
    seeds = [seed + i for i in range(seasons)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(one, seeds))
    return aggregate([o[0] for o in out]), aggregate4([o[1] for o in out]), seeds


def write(agg2, agg4, seeds, root: Path) -> tuple[dict, dict]:
    md2, st2 = build_report(agg2, seeds)
    (root / "reports/phase2.md").write_text(md2)
    (root / "reports/phase2.json").write_text(json.dumps({"aggregate": agg2, "status": st2}, indent=1, default=float) + "\n")
    md4, st4 = build_report4(agg4, seeds, st2)
    (root / "reports/phase4.md").write_text(md4)
    (root / "reports/phase4.json").write_text(json.dumps({"aggregate": agg4, "status": st4}, indent=1, default=float) + "\n")
    return st2, st4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=REPORT_SEASONS)
    ap.add_argument("--seed", type=int, default=REPORT_SEED)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    agg2, agg4, seeds = run(a.seasons, a.seed, a.workers)
    st2, st4 = write(agg2, agg4, seeds, Path(__file__).resolve().parents[1])
    print((Path(__file__).resolve().parents[1] / "reports/phase4.md").read_text())
    print("phase2 gate", all(v for v in st2.values() if v is not None), "| phase4 gate", all(v for v in st4.values() if v is not None), f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
