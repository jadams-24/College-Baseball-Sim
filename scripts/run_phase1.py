"""Run the Phase 1 engine and write the realism report.
    python3 scripts/run_phase1.py --games 10000 --seed 20250101
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.report import build_report  # noqa: E402
from engine.sim import simulate_league_average_games  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=20250101)
    ap.add_argument("--out", default="reports/phase1.md")
    a = ap.parse_args()
    t0 = time.time()
    sim = simulate_league_average_games(a.games, a.seed)
    md, status = build_report(sim, a.seed)
    Path(a.out).write_text(md)
    Path(a.out).with_suffix(".json").write_text(json.dumps(sim, indent=1, default=float) + "\n")
    print(md)
    print(f"({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
