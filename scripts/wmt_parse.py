"""Parse WMT game payloads (data/ncaa_2025/pbp/raw/*.jsonl.gz) into flat tables.

Each plate appearance in the raw actions is a group: a `play/start` record
(text, pre-play outs and score), `runner/onbase` records (which bases are
occupied before the play), a `batter/<outcome>` record (outcome flags, pitch
sequence), `runner/advances|out|...` records (from base -> to base) and
`fielder`/`pitcher` credit records. Groups with no batter outcome are base
running events (stolen base, caught stealing, pickoff, wild pitch, passed ball).

Outputs under data/ncaa_2025/pbp/parsed/:
  pa_events_2025.csv.gz      one row per plate appearance; r1_to/r2_to/r3_to are the
                             destination of the runner who started on that base
                             (0 = out, 1-3 = base, 4 = scored, same base = held)
  runner_events_2025.csv.gz  one row per non-PA base running event
  games_2025.csv             one row per game with both teams' box totals
"""
from __future__ import annotations

import csv
import glob
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

RAW = Path("data/ncaa_2025/pbp/raw")
OUT = Path("data/ncaa_2025/pbp/parsed")

RESULT = {  # batter sub_type -> result code
    "single": "1B", "double": "2B", "triple": "3B", "home run": "HR",
    "walk": "BB", "intentional walk": "IBB", "hit by pitch": "HBP",
    "strikeout": "K", "strikeout looking": "K",
    "flyout": "FO", "ground out": "GO", "sacrifice fly": "SF", "sacrifice hit": "SH",
    "grounded into double play": "GIDP", "double play": "DP",
    "reached on error": "ROE", "reached on fielders choice": "FC",
    "reached on catchers interference": "CI",
}
RUNNER_EVENT = {"stolen base": "SB", "caught stealing": "CS", "picked off": "PO"}

# Box stat keys from competitors[].teamStats period 0 that we keep, with short names.
BOX = {
    "sAtBats": "ab", "sRuns": "r", "sHits": "h", "sDoubles": "2b", "sTriples": "3b", "sHomeRuns": "hr",
    "sRunsBattedIn": "rbi", "sWalks": "bb", "sHitByPitch": "hbp", "sStrikeoutsHitting": "k",
    "sSacrificeFlies": "sf", "sSacrificeBunts": "sh", "sStolenBases": "sb", "sCaughtStealing": "cs",
    "sGroundOuts": "go", "sFlyOuts": "fo", "sLeftOnBase": "lob", "cPlateAppearances": "pa",
    "sErrors": "e", "sPutouts": "po", "sAssists": "a", "sDoublePlays": "dp", "sPassedBalls": "pb",
    "sInningsPitched": "ip", "sBattersFaced": "bf", "sHitsAllowed": "h_allowed", "sRunsAllowed": "r_allowed",
    "sEarnedRuns": "er", "sBasesOnBallsAllowed": "bb_allowed", "sStrikeouts": "k_pitched",
    "sHitBatters": "hbp_pitched", "sWildPitches": "wp", "sHomeRunsAllowed": "hr_allowed",
    "sStolenBasesAgainst": "sb_against", "sCaughtStealingBy": "cs_by", "sBalks": "bk",
    "sSacrificeFliesAllowed": "sf_allowed", "sSacrificeBuntsAllowed": "sh_allowed",
    "sNumberOfGroundOuts": "go_pitched", "sNumberOfFlyOuts": "fo_pitched", "sIntentionalWalks10494": "ibb",
}


def bb_type(text: str, sub: str) -> tuple[str, int]:
    """Batted-ball trajectory of an out/in-play from the play text."""
    t = text.lower()
    bunt = 1 if "bunt" in t else 0
    if "popped up" in t or "popped out" in t or "fouled out" in t or "foul pop" in t:
        return "PU", bunt
    if "lined" in t:
        return "LD", bunt
    if "flied" in t or "fly" in t:
        return "FB", bunt
    if "grounded" in t or "out at first" in t or "ground" in t:
        return "GB", bunt
    if sub in ("ground out", "grounded into double play", "sacrifice hit"):
        return "GB", bunt
    if sub in ("flyout", "sacrifice fly"):
        return "FB", bunt
    return "", bunt


def parse_game(g: dict) -> tuple[dict, list[dict], list[dict]]:
    comps = g["competitors"]
    home = next(c for c in comps if c.get("homeTeam"))
    away = next(c for c in comps if not c.get("homeTeam"))
    by_comp = {c["id"]: c for c in comps}
    hs, as_ = home.get("score"), away.get("score")
    game = {
        "game_id": g["id"], "game_date": (g.get("game_date") or "")[:10],
        "home_team_id": home["teamId"], "home_team": home.get("nameTabular"), "home_score": hs,
        "away_team_id": away["teamId"], "away_team": away.get("nameTabular"), "away_score": as_,
        "innings": g.get("periods_played"), "neutral_site": int(bool(g.get("neutral_site"))),
        "conference_game": int(bool(g.get("conference_contest"))), "attendance": g.get("attendance"),
        "duration_s": g.get("duration"),
    }
    if hs is not None and as_ is not None and game["innings"]:
        margin = abs(hs - as_)
        game["extra_innings"] = int(game["innings"] > 9)
        game["run_rule"] = int(game["innings"] < 9 and margin >= 10)
        game["short_not_run_rule"] = int(game["innings"] < 9 and margin < 10)
    for side, c in (("home", home), ("away", away)):
        st = next((s["statistic"] for s in c.get("teamStats", []) if s.get("period") == 0), {})
        for k, short in BOX.items():
            game[f"{side}_{short}"] = st.get(k, 0)

    acts = [a["action"] for a in (g.get("actions") or {}).get("data", [])]
    acts.sort(key=lambda a: a["id"])
    groups: dict[int, list[dict]] = defaultdict(list)
    order: list[int] = []
    for a in acts:
        if a.get("play_action_type") == "play" and a.get("play_action_sub_type") == "start":
            groups[a["id"]].append(a); order.append(a["id"])
        elif a.get("play_by_play_id") in groups:
            groups[a["play_by_play_id"]].append(a)
    pas, runs_ev = [], []
    for gid in order:
        rows = groups[gid]
        start = rows[0]
        text = start.get("play_by_play_text", "") or ""
        text = text.replace("3a", "; ") if "3a " in text else text
        bat_comp = start.get("competitor_id")
        bat_team = by_comp.get(bat_comp, {}).get("teamId")
        pit_team = away["teamId"] if bat_team == home["teamId"] else home["teamId"]
        half = "B" if bat_team == home["teamId"] else "T"
        onbase = {r["on_base"]: r for r in rows if r.get("play_action_type") == "runner" and r.get("play_action_sub_type") == "onbase" and r.get("on_base")}
        base = {"game_id": g["id"], "group_id": gid, "inning": start.get("period_number"), "half": half,
                "bat_team_id": bat_team, "pit_team_id": pit_team, "outs": start.get("outs", 0),
                "on1": int(1 in onbase), "on2": int(2 in onbase), "on3": int(3 in onbase),
                "away_score": start.get("visitor_score"), "home_score": start.get("home_score")}
        outcome = [r for r in rows if r.get("play_action_type") == "batter" and r.get("play_action_sub_type") not in ("atbat", None)]
        movers = [r for r in rows if r.get("play_action_type") == "runner" and r.get("play_action_sub_type") not in ("onbase", None)]
        # A runner with no movement record held his base.
        dest = {b: b for b in onbase}
        for r in movers:
            frm = r.get("on_base")
            if not frm:
                continue
            if r.get("play_action_sub_type") in ("out", "caught stealing", "picked off") or r.get("outs"):
                dest[frm] = 0  # out
            else:
                dest[frm] = r.get("to_base") or (4 if r.get("runs") else frm)
        if outcome:
            o = outcome[0]
            sub = o.get("play_action_sub_type")
            res = RESULT.get(sub, "OTHER")
            atbat = next((r for r in rows if r.get("play_action_type") == "batter" and r.get("play_action_sub_type") == "atbat"), {})
            pitcher = next((r for r in rows if r.get("play_action_type") == "pitcher" and r.get("play_action_sub_type") == "onmound"), {})
            bbt, bunt = bb_type(text, sub) if res in ("FO", "GO", "SF", "SH", "GIDP", "DP", "FC", "ROE", "1B", "2B", "3B", "HR") else ("", 0)
            b_to = o.get("to_base")
            if res in ("K", "FO", "GO", "SF", "SH", "GIDP", "DP") and not b_to:
                b_to = 0
            if res == "HR":
                b_to = 4
            outs_play = (o.get("outs") or 0) + sum(1 for r in movers if r.get("play_action_sub_type") == "out" or (r.get("outs") and r.get("play_action_sub_type") not in ("advances", "stolen base")))
            if res in ("GIDP", "DP") and outs_play < 2:
                outs_play = 2
            runs_play = sum(1 for v in dest.values() if v == 4) + (1 if b_to == 4 else 0)
            pas.append({**base, "batter": atbat.get("checkname"), "batter_id": atbat.get("game_player_id"),
                        "pitcher": pitcher.get("checkname"), "pitcher_id": pitcher.get("game_player_id"),
                        "result": res, "sub_type": sub, "k_looking": int(sub == "strikeout looking"),
                        "bb_type": bbt, "bunt": bunt, "hit_to": o.get("hit_to_position"),
                        "pitches": o.get("pitches"), "balls": o.get("balls"), "strikes": o.get("strikes"),
                        "pitch_seq": o.get("pitch_sequence"), "batter_to": b_to,
                        "r1_to": dest.get(1, "") if 1 in onbase else "", "r2_to": dest.get(2, "") if 2 in onbase else "",
                        "r3_to": dest.get(3, "") if 3 in onbase else "",
                        "outs_on_play": outs_play, "runs_on_play": runs_play, "rbi": o.get("rbi") or 0, "text": text})
        elif movers:
            subs = {r.get("play_action_sub_type") for r in movers}
            ev = next((RUNNER_EVENT[s] for s in ("stolen base", "caught stealing", "picked off") if s in subs), None)
            if ev is None:
                tl = text.lower()
                ev = "WP" if "wild pitch" in tl else "PB" if "passed ball" in tl else "BK" if "balk" in tl else "OTHER"
            for r in movers:
                frm = r.get("on_base")
                if not frm:
                    continue
                runs_ev.append({**base, "event": ev, "runner": r.get("checkname"), "from_base": frm,
                                "to_base": dest.get(frm), "text": text})
    game["n_pa_parsed"] = len(pas)
    return game, pas, runs_ev


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games, pas, revs, text_only = [], [], [], []
    for fn in sorted(glob.glob(str(RAW / "*.jsonl.gz"))):
        try:
            with gzip.open(fn, "rt") as fh:
                for line in fh:
                    g = json.loads(line)
                    if not (g.get("actions") or {}).get("data"):
                        continue
                    gm, p, r = parse_game(g)
                    if not p:  # play text present but no structured outcome records; a few tournament games
                        text_only.append(g["id"]); continue
                    games.append(gm); pas.extend(p); revs.extend(r)
        except (EOFError, json.JSONDecodeError) as exc:
            print(f"WARNING {fn}: stopped at a truncated record ({exc.__class__.__name__}); file still being written?")
    for name, rows, gz in (("games_2025.csv", games, False), ("pa_events_2025.csv.gz", pas, True), ("runner_events_2025.csv.gz", revs, True)):
        fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in rows[0], k)) if rows else []
        fields = list(rows[0].keys()) + [f for f in fields if f not in rows[0]] if rows else []
        fh = gzip.open(OUT / name, "wt", newline="") if gz else (OUT / name).open("w", newline="")
        with fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    (OUT / "excluded_games.json").write_text(json.dumps({"text_only_no_structured_actions": text_only}, indent=1) + "\n")
    print(f"games {len(games)}  PA {len(pas)}  runner events {len(revs)}  excluded (text only) {len(text_only)}")


if __name__ == "__main__":
    main()
