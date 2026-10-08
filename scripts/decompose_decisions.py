"""Decompose the change in runs per team-game between the PR A engine and PR B (owner request 2026-10-07).

One season per call, printed as one JSON line:
    python3 scripts/decompose_decisions.py <variant> <seed> [--old-chain FILE]
Variants (config.decisions.FEATURES):
    B  decisions off, the Phase 5 chain solved before PR B (--old-chain: git show 1af753a:data/ncaa_2025/derived/phase5_chain_solved_2025.json)
    C  decisions off
    D  steals before each pitch only
    E  called bunts only
    F  intentional walks only
    G  all decisions (the engine as committed)
Variant A is the PR A engine itself: run this script from a checkout of 1af753a (main after PR A) with variant C
(its config has no decision switches). Pair the variants by seed; PHASE0_NOTES, "Where the runs went", has the
8-season result (seeds 20251000-20251007).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

FLAGS = {"B": set(), "C": set(), "D": {"steals"}, "E": {"bunts"}, "F": {"ibb"}, "G": {"steals", "bunts", "ibb"}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", choices=sorted(FLAGS))
    ap.add_argument("seed", type=int)
    ap.add_argument("--old-chain")
    a = ap.parse_args()
    try:
        import config.decisions as cd
        f = FLAGS[a.variant]
        cd.FEATURES.update({"decisions": bool(f), "steals": "steals" in f, "bunts": "bunts" in f, "ibb": "ibb" in f})
    except ImportError:
        pass                                    # the PR A checkout (variant A)
    if a.variant == "B":
        import engine.game2 as g2
        old = json.loads(Path(a.old_chain).read_text())
        g2.load_solved = lambda: old
    from config import phase2
    from engine.game2 import P_BF, P_PITCH
    from engine.season import simulate_season
    res = simulate_season(phase2.load(), a.seed)
    tg, p = res["team_game_rows"], res["pstats"]
    print(json.dumps({"variant": a.variant, "seed": a.seed, "rg": float(tg[:, 1].mean()), "pa": float(tg[:, 9].mean()), "tg": int(len(tg)),
                      "sb": list(map(int, res["sb"])), "pitches_per_bf": float(p[:, P_PITCH].sum() / p[:, P_BF].sum())}))


if __name__ == "__main__":
    main()
