"""Pull every D1 team's 2025 schedule from the WMT stats API and flatten it.

For each NCAA team id in data/ncaa_2025/ncaa_d1_teams_2025.csv (307 teams) the
schedule endpoint returns every game with both teams' final box totals and the
number of innings played. Deduplicated by game id this is (close to) the whole
2025 D1 season, so league totals derived from it are team-weighted over all of
Division I rather than a sample.

Outputs:
  data/ncaa_2025/pbp/schedules/<ncaa_team_id>.json.gz   raw response (nulls and ingestion timestamps dropped)
  data/ncaa_2025/pbp/parsed/schedule_games_2025.csv      one row per distinct game with both box lines
One request per second; cached schedules are not re-fetched.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wmt_parse import BOX  # noqa: E402

API = "https://api.wmt.games/api/statistics"
HEADERS = {"Accept": "application/json", "Origin": "https://wmt.games",
           "User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}
SCHED = Path("data/ncaa_2025/pbp/schedules")
OUT = Path("data/ncaa_2025/pbp/parsed/schedule_games_2025.csv")
TEAMS = Path("data/ncaa_2025/ncaa_d1_teams_2025.csv")
DELAY = 1.0


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if v not in (None, "", [], {}) and k not in ("created_at", "updated_at", "createdAt", "updatedAt")}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def fetch(team_id: str) -> list[dict]:
    fn = SCHED / f"{team_id}.json.gz"
    if fn.exists():
        with gzip.open(fn, "rt") as fh:
            return json.load(fh)
    for attempt in range(4):
        time.sleep(DELAY)
        try:
            r = requests.get(f"{API}/teams/{team_id}/games", params={"per_page": 100}, headers=HEADERS, timeout=120)
        except requests.RequestException:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 200:
            games = strip(r.json().get("data", []))
            with gzip.open(fn, "wt") as fh:
                json.dump(games, fh, separators=(",", ":"))
            return games
        if r.status_code == 404:
            with gzip.open(fn, "wt") as fh:
                json.dump([], fh)
            return []
        time.sleep(10 * (attempt + 1))
    print("  failed", team_id, flush=True)
    return []


def main() -> None:
    SCHED.mkdir(parents=True, exist_ok=True)
    teams = list(csv.DictReader(TEAMS.open()))
    d1 = {int(t["ncaa_team_id"]): t["team"] for t in teams}
    games: dict[int, dict] = {}
    per_team = {}
    for i, t in enumerate(teams):
        tid = t["ncaa_team_id"]
        gs = fetch(tid)
        per_team[tid] = len(gs)
        for g in gs:
            if g.get("season_academic_year") != 2025 or g.get("sport_code") != "MBA":
                continue
            games.setdefault(g["id"], g)
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(teams)} teams, {len(games)} distinct games", flush=True)
    rows = []
    for g in games.values():
        comps = g.get("competitors") or []
        home = next((c for c in comps if c.get("homeTeam")), None)
        away = next((c for c in comps if not c.get("homeTeam")), None)
        if not home or not away:
            continue
        row = {"game_id": g["id"], "game_date": (g.get("game_date") or "")[:10], "innings": g.get("periods_played"),
               "home_team_id": home.get("teamId"), "home_team": home.get("nameTabular"), "home_score": home.get("score"),
               "away_team_id": away.get("teamId"), "away_team": away.get("nameTabular"), "away_score": away.get("score"),
               "home_is_d1": int(home.get("teamId") in d1), "away_is_d1": int(away.get("teamId") in d1),
               "stats_finalized": int(bool(g.get("stats_finalized"))), "xml_file_exists": int(bool(g.get("xml_file_exists"))),
               "canceled": int(bool(g.get("canceled"))), "exhibition": int(bool(g.get("is_exhibition"))),
               "neutral_site": int(bool(g.get("neutral_site"))), "conference_game": int(bool(g.get("conference_contest"))),
               "attendance": g.get("attendance"), "duration_s": g.get("duration")}
        for side, c in (("home", home), ("away", away)):
            st = next((s["statistic"] for s in c.get("teamStats", []) if s.get("period") == 0), {})
            row[f"{side}_has_box"] = int(bool(st))
            for k, short in BOX.items():
                row[f"{side}_{short}"] = st.get(k, 0)
        rows.append(row)
    rows.sort(key=lambda r: (r["game_date"], r["game_id"]))
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    manifest = {"source": f"{API}/teams/{{ncaa_team_id}}/games?per_page=100", "fetched_on": dt.date.today().isoformat(),
                "teams_requested": len(teams), "teams_with_games": sum(1 for v in per_team.values() if v),
                "distinct_games": len(rows), "games_both_d1": sum(1 for r in rows if r["home_is_d1"] and r["away_is_d1"]),
                "games_with_both_box": sum(1 for r in rows if r["home_has_box"] and r["away_has_box"]),
                "raw_transformation": "null/empty fields and created_at/updated_at removed; nothing else"}
    (SCHED.parent / "schedules_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
