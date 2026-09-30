"""Extract team season totals from saved Sidearm Sports stats pages.

A Sidearm stats page (/sports/baseball/stats/2025) embeds the full cumulative
season table as a Nuxt payload, including a "Totals" and an "Opponents" footer
row for hitting, pitching and fielding. Pages were fetched 2026-09-30 for the
13 programs whose sites answered plainly (most Sidearm sites sit behind Imperva
Incapsula and refuse automated clients). Raw pages: data/ncaa_2025/sidearm/raw/.
Output: data/ncaa_2025/sidearm/team_totals_2025.csv (one row per team x side).
"""
from __future__ import annotations

import csv
import glob
import gzip
import json
import re
from pathlib import Path

RAW = Path("data/ncaa_2025/sidearm/raw")
OUT = Path("data/ncaa_2025/sidearm/team_totals_2025.csv")
TAGS = ("ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef")
KEEP_H = ["gamesPlayed", "atBats", "runs", "hits", "doubles", "triples", "homeRuns", "runsBattedIn", "walks", "hitByPitch",
          "strikeouts", "sacrificeFlies", "sacrificeHits", "stolenBases", "stolenBasesAttemps", "totalPlateAppearances",
          "groundedIntoDoublePlay", "intentionalWalks"]
KEEP_F = ["putouts", "assists", "errors", "fieldingPercentage", "doublePlays", "passedBalls", "stolenBasesAgainst", "caughtStealingBy"]
KEEP_P = ["inningsPitched", "hitsAllowed", "runsAllowed", "earnedRunsAllowed", "walksAllowed", "strikeouts", "hitBatters", "wildPitches", "homeRunsAllowed", "earnedRunAverage"]


def hydrate(raw):
    memo = {}

    def hy(i):
        if not isinstance(i, int) or i < 0:
            return None
        if i in memo:
            return memo[i]
        v = raw[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and len(v) == 2 and isinstance(v[1], int) and v[0] in TAGS:
                out = hy(v[1])
            elif v and isinstance(v[0], str) and v[0] in ("Date", "BigInt", "RegExp"):
                out = v[1]
            elif v and isinstance(v[0], str) and v[0] in ("Set", "Map"):
                out = [hy(x) for x in v[1:] if isinstance(x, int)]
            else:
                out = [hy(x) for x in v]
        elif isinstance(v, dict):
            out = {k: hy(x) for k, x in v.items()}
        else:
            out = v
        memo[i] = out
        return out
    return hy(0)


def walk(o, path=""):
    if isinstance(o, dict):
        if o.get("playerName") in ("Totals", "Opponents") and o.get("isAFooterStat") is not None:
            yield path, o
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + f"[{i}]")


def main() -> None:
    rows = []
    for fn in sorted(glob.glob(str(RAW / "*.html.gz"))):
        domain = Path(fn).name[:-8]
        with gzip.open(fn, "rt") as fh:
            html = fh.read()
        m = re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S)
        title = re.search(r"<title>([^<]*)</title>", html)
        root = hydrate(json.loads(m.group(1)))
        rec = {}
        for path, o in walk(root):
            if "individualStatsConference" in path or "Conference" in path.split("/")[-2:][0]:
                continue  # overall season only, not conference-only splits
            side = o["playerName"]
            kind = "hitting" if "Hitting" in path else "fielding" if "Fielding" in path else "pitching" if "Pitching" in path else None
            if not kind:
                continue
            r = rec.setdefault(side, {"domain": domain, "page_title": (title.group(1).strip() if title else ""), "side": side})
            keys = {"hitting": KEEP_H, "fielding": KEEP_F, "pitching": KEEP_P}[kind]
            for k in keys:
                col = f"{kind[0]}_{k}"
                if col not in r or r[col] in ("", None):
                    r[col] = o.get(k)
        rows.extend(rec.values())
    fields = ["domain", "page_title", "side"] + [f"h_{k}" for k in KEEP_H] + [f"f_{k}" for k in KEEP_F] + [f"p_{k}" for k in KEEP_P]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(len(rows), "rows ->", OUT)
    for r in rows[:4]:
        print({k: r.get(k) for k in ["domain", "side", "h_gamesPlayed", "h_atBats", "h_hits", "h_hitByPitch", "h_sacrificeFlies", "h_sacrificeHits", "h_stolenBases", "h_stolenBasesAttemps", "h_totalPlateAppearances", "f_errors", "f_fieldingPercentage", "p_inningsPitched", "p_hitBatters"]})


if __name__ == "__main__":
    main()
