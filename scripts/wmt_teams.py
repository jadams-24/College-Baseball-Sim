"""Build data/ncaa_2025/pbp/teams_2025.csv: every D1 team's conference and Phase 0 tier.

Conference comes from the NCAA scoreboard feed already in
data/ncaa_2025/scoreboard/games_2025.csv (each game tags both teams' conference;
306 of 307 NCAA team names match exactly). The WMT team endpoint is used only as
a fallback; it answers for WMT client schools and 404s for everyone else.
Tier (p4 / mid / low) is the Phase 0 grouping from data/phase0/conf2025.csv.
No network access is needed unless the fallback fires (one request per second).
"""
from __future__ import annotations

import csv
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

API = "https://api.wmt.games/api/statistics"
HEADERS = {"Accept": "application/json", "Origin": "https://wmt.games",
           "User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}
TEAMS = Path("data/ncaa_2025/ncaa_d1_teams_2025.csv")
SCOREBOARD = Path("data/ncaa_2025/scoreboard/games_2025.csv")
OUT = Path("data/ncaa_2025/pbp/teams_2025.csv")
# scoreboard / WMT conference labels -> Phase 0 conference names (conf2025.csv)
ALIAS = {"The American": "American", "CUSA": "C-USA", "CAA": "Colonial", "ASUN": "Atlantic Sun", "MVC": "Missouri Valley",
         "OVC": "Ohio Valley", "NEC": "Northeast", "Patriot": "Patriot League", "Summit League": "Summit",
         "DI Independent": "Independent", "IND": "Independent"}
NAME_ALIAS = {"LSU New Orleans": "New Orleans"}


def main() -> None:
    tiers = {r["league"]: r["tier"] for r in csv.DictReader(open("data/phase0/conf2025.csv"))}
    votes: dict[str, Counter] = defaultdict(Counter)
    for r in csv.DictReader(SCOREBOARD.open()):
        for side in ("home", "away"):
            if r[f"{side}_conf"]:
                votes[r[side]][r[f"{side}_conf"]] += 1
    sb_conf = {k: v.most_common(1)[0][0] for k, v in votes.items()}
    rows = []
    for t in csv.DictReader(TEAMS.open()):
        tid, name = t["ncaa_team_id"], t["team"]
        conf = sb_conf.get(name) or sb_conf.get(NAME_ALIAS.get(name, ""), "")
        source = "ncaa scoreboard" if conf else ""
        if not conf:
            time.sleep(1.0)
            try:
                r = requests.get(f"{API}/teams/{tid}", headers=HEADERS, timeout=60)
                if r.status_code == 200:
                    conf = r.json().get("data", {}).get("conference_name_tabular") or ""
                    source = "wmt" if conf else ""
            except requests.RequestException:
                pass
        rows.append({"ncaa_team_id": tid, "team": name, "conference": conf, "tier": tiers.get(ALIAS.get(conf, conf), ""), "conference_source": source})
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ncaa_team_id", "team", "conference", "tier", "conference_source"]); w.writeheader(); w.writerows(rows)
    print(len(rows), "teams;", Counter(r["tier"] or "none" for r in rows), "| conferences without a tier:", sorted({r["conference"] for r in rows if not r["tier"]}))


if __name__ == "__main__":
    main()
