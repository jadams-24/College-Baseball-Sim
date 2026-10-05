"""Write the Phase 7 benchmark block (season and world) into benchmarks.json.

Sources: data/ncaa_2025/derived/phase7_benchmarks.json (scripts/build_phase7_benchmarks.py,
build_phase7_selection.py, build_phase7_cancel.py) and the RPI formula check against the NCAA's published
2026 pre-selection RPI (data/ncaa_2026/rpi/rpi_check_2026.json, scripts/check_rpi_2026.py). Each entry keeps
its confidence grade ("conf") and source note. New entries only: no existing benchmark value changes.
The change is logged in data/ncaa_2025/derived/benchmark_changes_phase7.json.

    python3 scripts/write_phase7_benchmarks.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

B = ROOT / "benchmarks.json"
LOG = ROOT / "data/ncaa_2025/derived/benchmark_changes_phase7.json"


def main() -> None:
    b = json.loads(B.read_text())
    p7 = json.loads((ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json").read_text())
    chk = json.loads((ROOT / "data/ncaa_2026/rpi/rpi_check_2026.json").read_text())
    block = {"_note": "Phase 7 (season and world): scoreboard feed 2015-2025, published brackets 2015-2025 (no 2020), WarrenNolan "
                      "schedules 2025-2026, the NCAA's published RPI through May 24, 2026. See PHASE0_NOTES, Phase 7.",
             "built": p7["built"],
             "rpi_formula_check_2026": {"spearman": round(chk["weighted"]["spearman"], 5), "exact_rank": chk["weighted"]["exact_rank"],
                                        "within_3": chk["weighted"]["within_3"], "teams": chk["weighted"]["teams"],
                                        "spearman_unweighted": round(chk["unweighted"]["spearman"], 5), "conf": "A",
                                        "src": "engine.rpi on WarrenNolan 2026 results through May 24 against https://www.ncaa.com/rankings/baseball/d1/rpi "
                                               "('Through Games May. 24 2026', the final RPI before the field was selected)"}}
    for k in ("games", "standings", "rpi", "field", "seeds", "home_field", "conference_tournaments"):
        block[k] = p7[k]
    old = b.get("season_world_2015_2026")
    b["season_world_2015_2026"] = block
    B.write_text(dumps_compact(b) + "\n")
    log = LOG
    entries = json.loads(log.read_text()) if log.exists() else []
    entries.append({"date": dt.date.today().isoformat(), "block": "season_world_2015_2026", "action": "replaced" if old else "added",
                    "keys": sorted(block)})
    log.write_text(json.dumps(entries, indent=1) + "\n")
    print("wrote season_world_2015_2026:", sorted(block))


if __name__ == "__main__":
    main()
