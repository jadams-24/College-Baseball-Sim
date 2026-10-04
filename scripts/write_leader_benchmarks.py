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

Team leaders (team_leaders_2024_2026, NCAA.com team pages, 2024-2026; owner decision 2026-10-04,
after the single-season rows were found to rest on one season and, for best team BA and most team
HR per game, on the wrong one):

  team_ba_max            the season's best team batting average
  best_team_era          the season's best team ERA
  team_hr_per_game_max   the season's most team home runs per game
  teams_era_under_4      teams with ERA under 4.00

All four are rates or counts of teams, so none is normalized to 56 games. They replace the
single-season leaderboards_2025 rows of the same names. The Phase 0 source entries for 2025
(batting_distribution_2025.team_ba_range_2025 and team_hr_max_2025, pitching_distribution_2025.
best_team_era_2025) carried 2026 values (Georgia Tech .356; Georgia 179 HR in 67 games) and
2025's second-best ERA (Coastal Carolina 3.20 behind Northeastern 3.06); they are corrected
to NCAA.com's 2025 table.

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


TEAM_ROWS = ("team_ba_max", "best_team_era", "team_hr_per_game_max", "teams_era_under_4")
TEAM_SRC = "https://www.ncaa.com/stats/baseball/d1/2024/team/{210,211,323} (2025 season; fetched 2026-10-04)"


def team_block(seasons: dict) -> dict:
    rows = {}
    for k in TEAM_ROWS:
        vals = {y: s[k]["value"] for y, s in sorted(seasons.items())}
        who = {y: s[k].get("team") for y, s in sorted(seasons.items()) if s[k].get("team")}
        rows[k] = {"by_season": vals, "lo": min(vals.values()), "hi": max(vals.values()), **({"teams": who} if who else {})}
    return {"_note": ("Phase 2 gate. National team leaders, 2024-2026 seasons: NCAA.com team pages (top 50; data/ncaa_leaders/). "
                      "Rates and counts of teams, not normalized to 56 games. Real seasons include the postseason and games "
                      "against non-D1 opponents. A row passes if the simulated mean over the seasons run lies in the band from "
                      "the lowest to the highest real season, widened by 3 SE of the simulated mean (as individual_leaders_2023_2026)."),
            "conf": "A", "src": "https://www.ncaa.com/stats/baseball/d1/{2023,2024,2025}/team/{210,211,323} (fetched 2026-10-04)", **rows}


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
    team = team_block(json.loads(SRC.read_text())["team_seasons"])
    if json.loads(json.dumps(b.get("team_leaders_2024_2026"))) != json.loads(json.dumps(team)):
        changes.append({"path": "team_leaders_2024_2026", "old": b.get("team_leaders_2024_2026"), "new": team})
    b["team_leaders_2024_2026"] = team
    lb = b["leaderboards_2025"]
    for k in TEAM_ROWS:
        if k in lb:
            changes.append({"path": f"leaderboards_2025.{k}", "old": lb[k], "new": None, "why": "superseded by team_leaders_2024_2026"})
            del lb[k]
    # the Phase 0 single-season source entries, corrected to NCAA.com's 2025 table
    t25 = json.loads(SRC.read_text())["team_seasons"]["2025"]
    fixes = ((["batting_distribution_2025", "team_ba_range_2025"], {"max": t25["team_ba_max"]["value"], "max_team": t25["team_ba_max"]["team"], "conf": "A", "src": TEAM_SRC}),
             (["batting_distribution_2025", "team_hr_max_2025"], {"value": t25["team_hr_per_game_max"]["HR"], "team": t25["team_hr_per_game_max"]["team"],
                                                                  "games": t25["team_hr_per_game_max"]["G"], "conf": "A", "src": TEAM_SRC}),
             (["pitching_distribution_2025", "best_team_era_2025"], {"value": t25["best_team_era"]["value"], "team": t25["best_team_era"]["team"], "conf": "A", "src": TEAM_SRC}))
    for path, val in fixes:
        cur = b[path[0]].get(path[1])
        if cur != val:
            changes.append({"path": ".".join(path), "old": cur, "new": val,
                            "why": "Phase 0 entry carried the 2026 season's value (or 2025's second-best ERA); NCAA.com 2025 team table"})
            b[path[0]][path[1]] = val
    # the Phase 2 placeholders without a full-population source are superseded by this block
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
