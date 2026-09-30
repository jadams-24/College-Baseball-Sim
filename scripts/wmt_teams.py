"""Fetch each D1 team's 2025 record from the WMT stats API to get its conference,
and attach the Phase 0 tier (p4 / mid / low) from data/phase0/conf2025.csv.

Output: data/ncaa_2025/pbp/teams_2025.csv
  ncaa_team_id, team, conference, tier, wins, losses
Used by build_pbp_benchmarks.py to report per-tier rates and to reweight the
WMT sample (which over-represents P4 programs) to the D1 tier mix.
One request per second; teams already in the output file are not re-fetched.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

import requests

API = "https://api.wmt.games/api/statistics"
HEADERS = {"Accept": "application/json", "Origin": "https://wmt.games",
           "User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}
TEAMS = Path("data/ncaa_2025/ncaa_d1_teams_2025.csv")
OUT = Path("data/ncaa_2025/pbp/teams_2025.csv")
# WMT conference labels -> Phase 0 conference names (conf2025.csv)
ALIAS = {"The American": "American", "CUSA": "C-USA", "CAA": "Colonial", "ASUN": "Atlantic Sun", "MVC": "Missouri Valley",
         "OVC": "Ohio Valley", "NEC": "Northeast", "Patriot": "Patriot League", "Summit League": "Summit",
         "DI Independent": "Independent", "Independent": "Independent"}


def main() -> None:
    tiers = {r["league"]: r["tier"] for r in csv.DictReader(open("data/phase0/conf2025.csv"))}
    done = {}
    if OUT.exists():
        done = {r["ncaa_team_id"]: r for r in csv.DictReader(OUT.open())}
    rows = []
    for t in csv.DictReader(TEAMS.open()):
        tid = t["ncaa_team_id"]
        if tid in done:
            rows.append(done[tid]); continue
        conf = ""
        wins = losses = ""
        for attempt in range(3):
            time.sleep(1.0)
            try:
                r = requests.get(f"{API}/teams/{tid}", headers=HEADERS, timeout=60)
            except requests.RequestException:
                time.sleep(5); continue
            if r.status_code == 200:
                d = r.json().get("data", {})
                conf = d.get("conference_name_tabular") or ""
                wins, losses = d.get("wins", ""), d.get("losses", "")
            break
        league = ALIAS.get(conf, conf)
        rows.append({"ncaa_team_id": tid, "team": t["team"], "conference": conf, "tier": tiers.get(league, ""), "wins": wins, "losses": losses})
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ncaa_team_id", "team", "conference", "tier", "wins", "losses"]); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(len(rows), "teams;", Counter(r["tier"] for r in rows), "unmapped conferences:", sorted({r["conference"] for r in rows if not r["tier"]}))


if __name__ == "__main__":
    main()
