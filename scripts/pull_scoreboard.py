"""Pull every D1 baseball scoreboard day for a season from data.ncaa.com.

Source: https://data.ncaa.com/casablanca/scoreboard/baseball/d1/YYYY/MM/DD/scoreboard.json
(the JSON feed behind ncaa.com's scoreboard pages). Each day's raw JSON is
stored gzipped under <out>/raw/, days with no games (HTTP 404) are listed in
the manifest, and every game entry is flattened into <out>/games_<season>.csv.

Run from the repo root:
    python3 scripts/pull_scoreboard.py --season 2025 --start 2025-02-13 --end 2025-06-23
Existing raw files are not re-fetched.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import time
from pathlib import Path

import requests

URL = "https://data.ncaa.com/casablanca/scoreboard/baseball/d1/{y}/{m:02d}/{d:02d}/scoreboard.json"
FIELDS = [
    "date", "gameID", "url", "state", "period", "finalMessage", "title",
    "away", "away_seo", "away_score", "away_conf",
    "home", "home_seo", "home_score", "home_conf",
]


def flatten(date: str, entry: dict) -> dict:
    g = entry["game"]

    def side(s: dict, prefix: str) -> dict:
        confs = s.get("conferences") or [{}]
        return {
            prefix: s["names"]["short"],
            f"{prefix}_seo": s["names"]["seo"],
            f"{prefix}_score": s.get("score", ""),
            f"{prefix}_conf": confs[0].get("conferenceName", ""),
        }

    row = {
        "date": date, "gameID": g.get("gameID", ""), "url": g.get("url", ""),
        "state": g.get("gameState", ""), "period": g.get("currentPeriod", ""),
        "finalMessage": g.get("finalMessage", ""), "title": g.get("title", ""),
    }
    row.update(side(g["away"], "away"))
    row.update(side(g["home"], "home"))
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--delay", type=float, default=0.3)
    a = ap.parse_args()
    out = Path(a.out or f"data/ncaa_{a.season}/scoreboard")
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    day = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end)
    fetched, no_games, errors = [], [], []
    while day <= end:
        fn = raw / f"{day.isoformat()}.json.gz"
        if not fn.exists():
            r = requests.get(URL.format(y=day.year, m=day.month, d=day.day), timeout=60)
            if r.status_code == 200:
                with gzip.open(fn, "wt") as fh:
                    fh.write(r.text)
                fetched.append(day.isoformat())
            elif r.status_code == 404:
                no_games.append(day.isoformat())
            else:
                errors.append((day.isoformat(), r.status_code))
            time.sleep(a.delay)
        day += dt.timedelta(days=1)

    rows = []
    for fn in sorted(raw.glob("*.json.gz")):
        with gzip.open(fn, "rt") as fh:
            data = json.load(fh)
        for entry in data.get("games", []):
            rows.append(flatten(fn.name[:10], entry))
    csv_path = out / f"games_{a.season}.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    manifest = {
        "source": URL,
        "season": a.season,
        "date_range": [a.start, a.end],
        "fetched_on": dt.date.today().isoformat(),
        "days_with_games": len(list(raw.glob("*.json.gz"))),
        "days_without_games_404": no_games,
        "errors": errors,
        "game_entries": len(rows),
        "unique_game_urls": len({r["url"] for r in rows}),
        "note": "gameID is the NCAA contest id; url is the ncaa.com game page id. Per-game box score / play-by-play JSON is not served by this host for these games.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "days_without_games_404"}, indent=1))
    print("days without games:", no_games)


if __name__ == "__main__":
    main()
