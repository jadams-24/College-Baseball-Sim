"""Pull 2025 D1 play-by-play from the WMT stats API (api.wmt.games).

WMT hosts the live-stats platform behind many athletics sites. Its public API
(robots.txt: allow all) is keyed by NCAA team id and serves, per game, every
scoring action of the NCAA game XML: one group of records per plate appearance
with the pre-state (outs, occupied bases), the batter's outcome flags, each
runner's from/to base, and the pitch sequence.

Sampling: candidates in data/ncaa_2025/pbp/programs_candidates.csv are taken in
order per tier until the per-tier quota is met; a program is used only if it has
at least MIN_GAMES[tier] finalized games with an XML file, and at most
MAX_PER_CONF programs per conference are taken so the sample stays spread.

Output (all under data/ncaa_2025/pbp/):
  programs_selected.csv                 the sample actually used
  games_index.csv                       one row per game pulled (ids, teams, score, innings)
  raw/<ncaa_team_id>.jsonl.gz           one line per game: the API game object with its
                                        actions. The only transformation is that null
                                        fields and the ingestion timestamps
                                        (created_at/updated_at) are dropped.
  manifest.json                         source URLs, fetch date, counts, skipped programs

One request per second. Resumable: games already in raw/ are not re-fetched.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

API = "https://api.wmt.games/api/statistics"
HEADERS = {"Accept": "application/json", "Origin": "https://wmt.games",
           "User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}
QUOTA = {"p4": 14, "mid": 26, "low": 20}
MAX_PER_CONF = {"p4": 3, "mid": 3, "low": 3}
# WMT coverage thins out below the P4: most mid/low programs only appear in games
# against WMT client schools, so partial seasons are accepted there.
MIN_GAMES = {"p4": 20, "mid": 8, "low": 5}
DELAY = 1.0
OUT = Path("data/ncaa_2025/pbp")
SEASON = 2025

_last = [0.0]


def get(url: str, params: dict | None = None, tries: int = 4):
    for attempt in range(tries):
        wait = DELAY - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=120)
        except requests.RequestException as exc:
            print("  network error", exc, "retrying", flush=True)
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(10 * (attempt + 1))
            continue
        raise RuntimeError(f"{url} -> {r.status_code} {r.text[:200]}")
    raise RuntimeError(f"gave up on {url}")


def strip(o):
    """Drop null/empty fields and ingestion timestamps, recursively."""
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items()
                if v not in (None, "", [], {}) and k not in ("created_at", "updated_at", "createdAt", "updatedAt")}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


SCHED = OUT / "schedules"


def team_games(team_id: str) -> list[dict]:
    """Schedule for one team, from the cache written by scripts/wmt_schedules.py when present."""
    fn = SCHED / f"{team_id}.json.gz"
    if fn.exists():
        with gzip.open(fn, "rt") as fh:
            games = json.load(fh)
    else:
        d = get(f"{API}/teams/{team_id}/games", {"per_page": 100})
        games = strip(d.get("data", []))
        SCHED.mkdir(parents=True, exist_ok=True)
        with gzip.open(fn, "wt") as fh:
            json.dump(games, fh, separators=(",", ":"))
    return [g for g in games if g.get("season_academic_year") == SEASON]


def usable(g: dict) -> bool:
    return bool(g.get("xml_file_exists")) and bool(g.get("stats_finalized")) and not g.get("canceled") \
        and not g.get("is_exhibition") and g.get("sport_code") == "MBA"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-team", help="pull a single NCAA team id (validation run)")
    ap.add_argument("--quota", type=int, help="override every tier quota (smoke test)")
    ap.add_argument("--all-covered", action="store_true",
                    help="after the program sample, also pull every other usable D1-vs-D1 game present in the cached schedules")
    a = ap.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    cands = list(csv.DictReader((OUT / "programs_candidates.csv").open()))
    if a.only_team:
        cands = [c for c in cands if c["ncaa_team_id"] == a.only_team]
    quota = {k: (a.quota or v) for k, v in QUOTA.items()}

    selected, skipped, per_conf = [], [], Counter()
    schedules: dict[str, list[dict]] = {}
    for tier in ("p4", "mid", "low"):
        need = quota[tier]
        for c in [c for c in cands if c["tier"] == tier]:
            if need <= 0:
                break
            if per_conf[(tier, c["conference"])] >= MAX_PER_CONF[tier]:
                continue
            try:
                games = team_games(c["ncaa_team_id"])
            except Exception as exc:
                skipped.append({**c, "reason": f"schedule error: {exc}"[:160]}); continue
            ok = [g for g in games if usable(g)]
            print(f"{tier:4} {c['team']:28} games={len(games)} usable={len(ok)}", flush=True)
            if len(ok) < MIN_GAMES[tier]:
                skipped.append({**c, "reason": f"only {len(ok)} usable games"}); continue
            selected.append({**c, "games_listed": len(games), "games_usable": len(ok)})
            schedules[c["ncaa_team_id"]] = ok
            per_conf[(tier, c["conference"])] += 1
            need -= 1
    with (OUT / "programs_selected.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(selected[0].keys())); w.writeheader(); w.writerows(selected)
    print("selected", Counter(s["tier"] for s in selected), "skipped", len(skipped), flush=True)

    # Games are attributed to the first selected team that lists them; each game is pulled once.
    owner: dict[int, str] = {}
    for tid, games in schedules.items():
        for g in games:
            owner.setdefault(g["id"], tid)
    if a.all_covered:
        # Every other usable game between two D1 teams that any cached schedule lists,
        # attributed to the pseudo-team "other" so the stratified sample stays identifiable.
        d1 = {int(r["ncaa_team_id"]) for r in csv.DictReader(Path("data/ncaa_2025/ncaa_d1_teams_2025.csv").open())}
        extra = []
        for fn in sorted(SCHED.glob("*.json.gz")):
            with gzip.open(fn, "rt") as fh:
                for g in json.load(fh):
                    if g.get("season_academic_year") != SEASON or not usable(g) or g["id"] in owner:
                        continue
                    tids = {c.get("teamId") for c in g.get("competitors", [])}
                    if len(tids) == 2 and tids <= d1:
                        owner[g["id"]] = "other"; extra.append(g)
        schedules["other"] = extra
        print(f"--all-covered: {len(extra)} additional D1-vs-D1 games", flush=True)
    index_rows, done = [], set()
    idx_path = OUT / "games_index.csv"
    if idx_path.exists():
        for r in csv.DictReader(idx_path.open()):
            done.add(int(r["game_id"])); index_rows.append(r)
    fields = ["game_id", "pulled_via_team_id", "game_date", "home_team_id", "home_team", "home_score",
              "away_team_id", "away_team", "away_score", "innings", "attendance", "duration_s",
              "neutral_site", "conference_game", "n_actions"]
    total = sum(1 for gid in owner if gid not in done)
    print(f"{len(owner)} distinct games, {total} to fetch (~{total*DELAY/60:.0f} min)", flush=True)
    n = 0
    for tid, games in schedules.items():
        mine = [g for g in games if owner[g["id"]] == tid and g["id"] not in done]
        if not mine:
            continue
        with gzip.open(OUT / "raw" / f"{tid}.jsonl.gz", "at") as raw, idx_path.open("a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            if fh.tell() == 0:
                w.writeheader()
            for g in mine:
                try:
                    full = get(f"{API}/games/{g['id']}", {"with[]": ["actions"]})["data"]
                except Exception as exc:
                    print("  game error", g["id"], exc, flush=True); continue
                acts = (full.get("actions") or {}).get("data") or []
                raw.write(json.dumps(strip(full), separators=(",", ":")) + "\n")
                home = next((c for c in full["competitors"] if c.get("homeTeam")), full["competitors"][0])
                away = next((c for c in full["competitors"] if not c.get("homeTeam")), full["competitors"][-1])
                row = {"game_id": g["id"], "pulled_via_team_id": tid, "game_date": (g.get("game_date") or "")[:10],
                       "home_team_id": home.get("teamId"), "home_team": home.get("nameTabular"), "home_score": home.get("score"),
                       "away_team_id": away.get("teamId"), "away_team": away.get("nameTabular"), "away_score": away.get("score"),
                       "innings": full.get("periods_played"), "attendance": full.get("attendance"), "duration_s": full.get("duration"),
                       "neutral_site": full.get("neutral_site"), "conference_game": full.get("conference_contest"), "n_actions": len(acts)}
                w.writerow(row); fh.flush(); index_rows.append(row); done.add(g["id"]); n += 1
                if n % 25 == 0:
                    print(f"  fetched {n}/{total}", flush=True)
    manifest = {
        "source": {"schedule": f"{API}/teams/{{ncaa_team_id}}/games?per_page=100",
                   "game": f"{API}/games/{{game_id}}?with[]=actions",
                   "robots": "https://api.wmt.games/robots.txt allows all user agents"},
        "fetched_on": dt.date.today().isoformat(), "season": SEASON, "rate_limit_s": DELAY,
        "raw_transformation": "null/empty fields and created_at/updated_at removed; nothing else",
        "programs_selected": len(selected), "programs_skipped": skipped,
        "games_indexed": len(index_rows), "quota": quota, "min_games": MIN_GAMES, "max_per_conf": MAX_PER_CONF,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("done:", len(index_rows), "games indexed", flush=True)


if __name__ == "__main__":
    main()
