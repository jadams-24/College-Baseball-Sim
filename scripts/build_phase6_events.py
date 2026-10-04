"""Phase 6 event tables from the raw WMT play-by-play (data/ncaa_2025/pbp/raw).

The Phase 1-5 parse (scripts/wmt_parse.py) kept plate appearances. Phase 6 needs what happens
around them, so this reads the same raw game payloads again and writes, to
data/ncaa_2025/pbp/parsed/:

  games_meta_2025.csv     one row per game: local date and start hour, venue (id, name, city,
                          state, latitude, longitude), home and away team, neutral site,
                          doubleheader game number
  subs_2025.csv           every substitution action (in and out): team, inning, play number,
                          score, outs, lineup spot, position (p, ph, pr, c, 1b, ..., dh)
  fielding_2025.csv       every fielder credit on a play: fielding team, player, position,
                          putouts, assists, errors, passed balls; linked to the plate appearance by
                          play_by_play_id (= group_id in pa_events_2025)
  runners_2025.csv        every runner action: on base, advances, stolen base, caught stealing,
                          picked off, out; from and to base, the scorer's code (xml_action)

Player identity inside a game is game_player_id; across games, the name key of
scripts/lib/players.py (team + canonical name). Games without actions (2 payloads) are skipped.

    python3 scripts/build_phase6_events.py
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/ncaa_2025/pbp/raw"
OUT = ROOT / "data/ncaa_2025/pbp/parsed"
sys.path.insert(0, str(ROOT / "scripts"))

GAME_COLS = ["game_id", "local_date", "local_hour", "time_tba", "venue_id", "venue", "city", "state", "lat", "lon",
             "home_team_id", "away_team_id", "neutral_site", "dbl_header_game_no"]
SUB_COLS = ["game_id", "team_id", "play_number", "play_by_play_id", "inning", "visitor_score", "home_score", "outs",
            "kind", "game_player_id", "name", "position", "lineup_spot"]
FLD_COLS = ["game_id", "team_id", "play_number", "play_by_play_id", "inning", "game_player_id", "name", "position",
            "put_outs", "assists", "errors", "pass_ball", "double_play"]
RUN_COLS = ["game_id", "team_id", "play_number", "play_by_play_id", "inning", "outs", "game_player_id", "name",
            "kind", "on_base", "to_base", "bases_advanced", "code", "unearned"]


def local_time(d: dict) -> tuple[str, int]:
    """Local date and hour of the first pitch, from the UTC time and the venue's time zone offset
    implied by game_date (local wall time written with a Z suffix) against game_date_utc."""
    loc = datetime.fromisoformat(d["game_date"].replace("Z", "+00:00"))
    return loc.date().isoformat(), loc.hour


def main() -> None:
    games, subs, flds, runs = [], [], [], []
    seen = set()
    for f in sorted(RAW.glob("*.jsonl.gz")):
        for line in gzip.open(f, "rt"):
            d = json.loads(line)
            gid = d["id"]
            if gid in seen or "actions" not in d:
                continue
            seen.add(gid)
            comp = {c["id"]: c["teamId"] for c in d["competitors"]}
            home = next(c["teamId"] for c in d["competitors"] if c["homeTeam"])
            away = next(c["teamId"] for c in d["competitors"] if not c["homeTeam"])
            v = d.get("venue") or {}
            date, hour = local_time(d)
            games.append([gid, date, hour, int(bool(d.get("is_game_time_tba"))), v.get("id"), v.get("name"), v.get("city"), v.get("state"),
                          v.get("latitude"), v.get("longitude"), home, away, int(bool(d.get("neutral_site"))), d.get("dbl_header_game_no")])
            for a in d["actions"]["data"]:
                ac = a["action"]
                t, s = ac.get("play_action_type"), ac.get("play_action_sub_type")
                team = comp.get(ac.get("competitor_id"))
                base = [gid, team, ac.get("play_number"), ac.get("play_by_play_id"), ac.get("period_number")]
                if t == "sub":
                    subs.append(base + [ac.get("visitor_score"), ac.get("home_score"), ac.get("outs"), s, ac.get("game_player_id"),
                                        ac.get("checkname"), ac.get("position"), ac.get("lineup_spot")])
                elif t == "fielder":
                    flds.append(base + [ac.get("game_player_id"), ac.get("checkname"), ac.get("position"), ac.get("put_outs", 0),
                                        ac.get("assists", 0), ac.get("errors_committed", 0), ac.get("pass_ball", 0), ac.get("double_play", 0)])
                elif t == "runner":
                    runs.append(base[:5] + [ac.get("outs"), ac.get("game_player_id"), ac.get("checkname"), s, ac.get("on_base"),
                                            ac.get("to_base"), ac.get("bases_advanced"), (ac.get("xml_action") or "").strip(),
                                            int(bool(ac.get("unearned_run")))])
    for name, cols, rows in (("games_meta_2025.csv", GAME_COLS, games), ("subs_2025.csv.gz", SUB_COLS, subs),
                             ("fielding_2025.csv.gz", FLD_COLS, flds), ("runners_2025.csv.gz", RUN_COLS, runs)):
        op = gzip.open if name.endswith(".gz") else open
        with op(OUT / name, "wt", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            w.writerows(rows)
        print(name, len(rows))


if __name__ == "__main__":
    main()
