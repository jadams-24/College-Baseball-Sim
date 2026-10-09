"""Engine speed benchmark (speed pass, 2026-10-09): wall time per game on a fixed world, and optionally one full season.
    python3 scripts/bench_engine.py [--games 600] [--season] [--lean]
--lean: the report-only accumulators off (config.diagnostics), as for dynasty play.
Prints ms per game (median of 3 repeats of the same games, each on a fresh engine) and the season's wall time."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def games(n: int) -> float:
    from config import phase2
    from engine import game2
    from engine.league import build_league
    from engine.manager import Manager
    from engine.schedule import make_schedule
    cfg = phase2.load()
    sa, sb, sc = np.random.SeedSequence(20261009).spawn(3)
    gen = lambda s: np.random.Generator(np.random.PCG64(s))  # noqa: E731
    lg = build_league(cfg, gen(sa))
    sch = make_schedule(cfg, lg, gen(sb))
    seeds = sc.spawn(n)
    times = []
    for _ in range(3):
        nn = len(lg.players)
        eng = game2.PlayerGameEngine(cfg, lg, [[0] * game2.B_NCOL for _ in range(nn)], [[0] * game2.P_NCOL for _ in range(nn)])
        mgr = Manager(cfg)
        t = time.perf_counter()
        for g, gs in zip(sch[:n], seeds):
            eng.play(gen(gs), lg.teams[g.home], lg.teams[g.away], g.weekend, mgr, week=g.week, day=g.day, date=g.date)
        times.append((time.perf_counter() - t) / n * 1000)
    return statistics.median(times)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=600)
    ap.add_argument("--season", action="store_true")
    ap.add_argument("--lean", action="store_true")
    a = ap.parse_args()
    if a.lean:
        from config import diagnostics
        diagnostics.RECORD = False
    print(f"{games(a.games):.2f} ms per game ({a.games} games, median of 3)", flush=True)
    if a.season:
        from config import phase2
        from engine.season import simulate_season
        t = time.perf_counter()
        res = simulate_season(phase2.load(), 20251000)
        print(f"season: {time.perf_counter() - t:.1f} s ({len(res['games'])} regular-season games plus the postseason)")


if __name__ == "__main__":
    main()
