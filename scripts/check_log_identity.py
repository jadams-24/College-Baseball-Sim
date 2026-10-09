"""Hash the event logs of 300 games (owner, 2026-10-09: bookkeeping and speed changes must leave every game bit-identical).

Plays the first 300 games of a fixed world (seed 20261009) with full event logs and prints one sha256 over all of them,
plus the per-game hashes to a file when asked. Run it on two commits on the same machine: equal hashes mean every pitch,
decision and runner movement is identical (across machines floating point differs; CLAUDE.md).
    python3 scripts/check_log_identity.py [--games 300] [--out hashes.txt] [--lean]
--lean plays with the report-only accumulators off (config.diagnostics); the log hash must not change. A second hash
covers the season stat lines (batting and pitching, box-score columns included) after the games.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=300)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--lean", action="store_true")
    a = ap.parse_args()
    if a.lean:
        from config import diagnostics
        diagnostics.RECORD = False
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
    n = len(lg.players)
    eng = game2.PlayerGameEngine(cfg, lg, [[0] * game2.B_NCOL for _ in range(n)], [[0] * game2.P_NCOL for _ in range(n)])
    mgr = Manager(cfg)
    total, lines = hashlib.sha256(), []
    for g, gs in zip(sch[:a.games], sc.spawn(a.games)):
        s = game2.GameSession(eng, gen(gs), lg.teams[g.home], lg.teams[g.away], g.weekend, mgr, week=g.week, day=g.day,
                              date=g.date, log=True)
        s.run()
        h = hashlib.sha256(repr(s.log).encode()).hexdigest()
        total.update(h.encode()); lines.append(h)
    if a.out:
        a.out.write_text("\n".join(lines) + "\n")
    print(f"{a.games} games: {total.hexdigest()}")
    print(f"stat lines: {hashlib.sha256(np.asarray(eng.bstats).tobytes() + np.asarray(eng.pstats).tobytes()).hexdigest()}")


if __name__ == "__main__":
    main()
