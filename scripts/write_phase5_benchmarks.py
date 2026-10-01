"""Write the Phase 5 block of benchmarks.json from data/ncaa_2025/derived/phase5_pitch_2025.json
(scripts/build_phase5_benchmarks.py): pitch_level_2025, the gate values of the pitch-by-pitch
engine with tolerance 3 SE (bootstrap over games). The Phase 0 block pitch_level_2023_2025
(Trackman first-pitch strike rate and older count data) is kept as it is and is not gated: its
first-pitch strike rate counts pitches in a different way from the play-by-play the engine is
built on (see PHASE0_NOTES.md, Phase 5). Every write is recorded in
data/ncaa_2025/derived/benchmark_changes_phase5.json.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.phase5 import DEFERRED_TO_PHASE6  # noqa: E402

D = Path("data/ncaa_2025/derived")
BENCH = Path("benchmarks.json")


def main() -> None:
    src = json.loads((D / "phase5_pitch_2025.json").read_text())
    b = json.loads(BENCH.read_text())
    new = {"_note": ("Phase 5 gate. Pitch sequences of the 2025 WMT play-by-play (B ball, K called strike, S swinging strike, F foul, P in play, "
                     "H hit by pitch; no pitch type, velocity or location in the data), reweighted by batting-tier x pitching-tier cell to the "
                     "full-season D1 matchup mix. Tolerance 3 SE, bootstrap over games. Cleaning, definitions and the per-count chain tables: "
                     "data/ncaa_2025/derived/phase5_pitch_2025.json. Intentional walks excluded."),
           "conf": "B", "src": src["src"], "n_games": src["n_games"], "n_pa": src["cleaning"]["pa_used"], "n_starts": src["n_starts"],
           **{k: {"value": v["value"], "tol": round(3 * v["se"], 5), **({"gate": "phase6"} if k in DEFERRED_TO_PHASE6 else {})}
              for k, v in src["benchmarks"].items()},
           "percentile_pooling": {"floor": src["percentile_pooling"]["floor"], "pooled_groups": src["percentile_pooling"]["pooled_groups"],
                                  "note": "Starter pitch-count percentiles: tier-pair cells with fewer starts than the floor are pooled with their nearest cells before reweighting (scripts/lib/pooling.py)."}}
    changes = []
    if json.loads(json.dumps(b.get("pitch_level_2025"))) != json.loads(json.dumps(new)):
        changes.append({"path": "pitch_level_2025", "old": b.get("pitch_level_2025"), "new": new})
    b["pitch_level_2025"] = new
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:
        log = D / "benchmark_changes_phase5.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        log.write_text(json.dumps(prior + [{**c, "date": datetime.date.today().isoformat()} for c in changes], indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
