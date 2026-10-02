"""Write the individual-leaders block of benchmarks.json (individual_leaders_2023_2026) from
the NCAA.com national leader pages and the record book (data/ncaa_leaders/ncaa_leaders.json,
scripts/parse_ncaa_leaders.py). Phase 2 gate rows (engine/report2.py):

  hr_leader_56g          the season's most home runs at a 56-game equivalent: each listed
                         player's HR x 56 / his games (real leaders' teams played 57-72 games,
                         postseason included; the sim plays 56)
  hr_30plus_56g          hitters with 30+ HR at the 56-game equivalent (from each season's
                         top 50, which reaches down to 19-21 HR)
  ba_leader              the qualified batting-average leader (a rate: no normalization)
  hr_top5_per_game       the five home-run leaders' mean HR per game played (the pages give
                         games, not plate appearances, so this is the per-PA comparison on the
                         nearest scale both sides share)
  hr_season_record       48 (Pete Incaviglia, Oklahoma State, 1985): a hard ceiling on every
                         simulated player-season

Tolerance: the band from the lowest to the highest real season of 2023-2026 (the season-to-
season range of the real leaders), widened only by the sim mean's own sampling error (engine/
report2.py). 2023 enters the rows its record-book lines support (leader HR, BA leader).
Every write is recorded in data/ncaa_2025/derived/benchmark_changes_leaders.json.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

sys.path.insert(0, str(ROOT))
from config.phase2 import SEASON_GAMES  # noqa: E402

SRC = ROOT / "data/ncaa_leaders/ncaa_leaders.json"
BENCH = ROOT / "benchmarks.json"
LOG = ROOT / "data/ncaa_2025/derived/benchmark_changes_leaders.json"
HR_RECORD = 48     # NCAA D1 single-season record (record book): Pete Incaviglia, Oklahoma State, 1985
TOP = 5


def main() -> None:
    src = json.loads(SRC.read_text())["seasons"]
    per = {}
    for season, s in sorted(src.items()):
        if "hr_top5" in s:     # NCAA.com top 50
            rows = [(float(r["HR"]), float(r["G"])) for r in s["hr"]["rows"]]
            ba_leader = s["ba_top5"][0]
        else:                  # record book: the top lines only
            rows = [(float(r["HR"]), float(r["G"])) for r in s["hr"]]
            ba_leader = s["ba"][0]["BA"]
        eq = [hr * SEASON_GAMES / g for hr, g in rows]
        e = {"hr_leader_56g": round(max(eq), 2), "ba_leader": round(ba_leader, 3)}
        if "hr_top5" in s:
            top = sorted(rows, key=lambda x: -x[0])[:TOP]
            e["hr_30plus_56g"] = int(sum(v >= 30 for v in eq))
            e["hr_top5_per_game"] = round(sum(hr / g for hr, g in top) / TOP, 4)
        per[season] = e
    rows = {}
    for key in ("hr_leader_56g", "hr_30plus_56g", "ba_leader", "hr_top5_per_game"):
        vals = {y: e[key] for y, e in per.items() if key in e}
        rows[key] = {"by_season": vals, "lo": min(vals.values()), "hi": max(vals.values())}
    new = {"_note": ("Phase 2 gate. National individual leaders, 2023-2026 seasons: NCAA.com national leader pages (top 50) for 2024-2026 "
                     "and the NCAA record book for 2023 (data/ncaa_leaders/). Counting stats at a 56-game equivalent (each player's "
                     "HR x 56 / his games), rates as they are. A row passes if the simulated mean over the seasons run lies in the "
                     "band from the lowest to the highest real season, widened by 3 SE of the simulated mean; the single-season record "
                     "is a hard ceiling on every simulated player-season."),
           "conf": "A", "src": "https://www.ncaa.com/stats/baseball/d1/{2023,2024,2025}/individual/{470,200} (fetched 2026-10-01); "
                               "http://fs.ncaa.org/Docs/stats/baseball_RB/2024/D1.pdf",
           "season_games": SEASON_GAMES, **rows,
           "hr_season_record": {"value": HR_RECORD, "note": "Pete Incaviglia, Oklahoma State, 1985 (NCAA record book)"}}
    b = json.loads(BENCH.read_text())
    old = b.get("individual_leaders_2023_2026")
    changes = []
    if json.loads(json.dumps(old)) != json.loads(json.dumps(new)):
        changes.append({"path": "individual_leaders_2023_2026", "old": old, "new": new})
    # the Phase 2 placeholders without a full-population source are superseded by this block
    lb = b["leaderboards_2025"]
    for k in ("individual_ba_top", "individual_hr_top"):
        if lb.get(k, {}).get("value", 0) is None:
            changes.append({"path": f"leaderboards_2025.{k}", "old": lb[k], "new": None})
            del lb[k]
    b["individual_leaders_2023_2026"] = new
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:
        prior = json.loads(LOG.read_text()) if LOG.exists() else []
        LOG.write_text(json.dumps(prior + [{**c, "date": datetime.date.today().isoformat()} for c in changes], indent=1, default=str) + "\n")
    print(json.dumps(per, indent=1))
    print(json.dumps(rows, indent=1))
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
