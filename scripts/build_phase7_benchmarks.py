"""Phase 7 benchmarks from the scoreboard feed 2015-2025 and the published brackets.

Writes data/ncaa_2025/derived/phase7_benchmarks.json:
  seeds          hosts winning their regional, top-8 national seeds reaching Omaha, top-16 national
                 seeds among the CWS teams (2018 on), CWS slots by tier, champion's tier (report row);
                 published brackets 2015-2025 without 2020 (data/ncaa_brackets), 2025 tiers
  field          the 64-team field by tier, at-large bids by tier, conferences with more than one bid
  home_field     postseason games: the regional or super regional host at its own park, and the listed
                 home team at neutral sites (CWS; regional games without the host)
  standings      Division I games of the regular season: SD of team win% within each tier (mean over
                 seasons) and the best record (win%, and wins-losses); regular season = games before the
                 Tuesday of conference tournament week (selection Monday - 6 days)
Each block carries per-season values, the pooled value with its standard error, and a confidence grade.

    python3 scripts/build_phase7_benchmarks.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.brackets import SEASONS, brackets, feed_games, feed_name, name_map, tier_of, tiers  # noqa: E402
sys.path.insert(0, str(ROOT))
from config.phase7 import MAX_UNRESOLVED  # noqa: E402

OUT = ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json"
SELECTION = {"2015": "2015-05-25", "2016": "2016-05-30", "2017": "2017-05-29", "2018": "2018-05-28", "2019": "2019-05-27",
             "2021": "2021-05-31", "2022": "2022-05-30", "2023": "2023-05-29", "2024": "2024-05-27", "2025": "2025-05-26"}
TIERS = ("p4", "mid", "low")


def binom(w: int, n: int) -> dict:
    p = w / n
    return {"value": round(p, 4), "se": round(float(np.sqrt(p * (1 - p) / n)), 4), "n": n}


def seeds_and_field(b, tier, m) -> dict:
    host_won = n_reg = 0
    top8, top16, cws, champ, atl, fld, multi = {}, {}, {t: 0 for t in TIERS}, {}, {}, {}, {}
    for y in SEASONS:
        s = b[y]
        for r in s["regionals"]:
            n_reg += 1; host_won += r["winner"] == r["host"]
        ns = {t["team"]: t["national_seed"] for t in s["teams"] if t["national_seed"]}
        top8[y] = sum(t in s["cws"] for t, k in ns.items() if k <= 8)
        if len(ns) == 16:
            top16[y] = sum(t in s["cws"] for t in ns)
        for t in s["cws"]:
            cws[tier_of(t, tier, m)] += 1
        champ[y] = tier_of(s["champion"], tier, m)
        atl[y] = {k: sum(1 for t in s["teams"] if t["bid"] != "auto" and tier_of(t["team"], tier, m) == k) for k in TIERS}
        fld[y] = {k: sum(1 for t in s["teams"] if tier_of(t["team"], tier, m) == k) for k in TIERS}
        conf = pd.Series([t["conference"] for t in s["teams"]]).value_counts()
        multi[y] = int((conf > 1).sum())
    v8, v16 = np.array(list(top8.values()), float), np.array(list(top16.values()), float)
    ncws = sum(cws.values())
    per = lambda d, k: np.array([d[y][k] for y in SEASONS], float)
    return {
        "seeds": {"_note": "published brackets 2015-2025 without 2020 (Wikipedia, data/ncaa_brackets; confidence B: hosts 2015-2018 are the regional 1 seeds, as the 2018 page states for national seeds); tiers by the program's 2025 conference",
                  "conf": "B",
                  "host_wins_regional": binom(host_won, n_reg),
                  "top8_national_seeds_in_cws": {"value": round(float(v8.mean()), 3), "se": round(float(v8.std(ddof=1) / np.sqrt(len(v8))), 3), "by_season": top8},
                  "top16_national_seeds_in_cws": {"value": round(float(v16.mean()), 3), "se": round(float(v16.std(ddof=1) / np.sqrt(len(v16))), 3), "by_season": top16},
                  "cws_share_by_tier": {k: binom(cws[k], ncws) for k in TIERS},
                  "champion_tier_by_season": champ},
        "field": {"_note": "the 64-team field by the program's 2025 tier; at-large = not the conference's automatic bid (for 2015-2018, 2022 and 2023 the page lists only automatic bids, every other team is at-large)",
                  "conf": "B",
                  "field_by_tier": {k: {"mean": round(float(per(fld, k).mean()), 2), "sd": round(float(per(fld, k).std(ddof=1)), 2),
                                        "range": [int(per(fld, k).min()), int(per(fld, k).max())]} for k in TIERS},
                  "at_large_by_tier": {k: {"mean": round(float(per(atl, k).mean()), 2), "sd": round(float(per(atl, k).std(ddof=1)), 2),
                                           "range": [int(per(atl, k).min()), int(per(atl, k).max())]} for k in TIERS},
                  "conferences_multi_bid": {"mean": round(float(np.mean(list(multi.values()))), 2), "sd": round(float(np.std(list(multi.values()), ddof=1)), 2),
                                            "range": [min(multi.values()), max(multi.values())]},
                  "by_season": {"field": fld, "at_large": atl, "conferences_multi_bid": multi}},
    }


def home_field(b, m) -> dict:
    tot = {"regional_host": [0, 0], "regional_no_host_listed_home": [0, 0], "super_host": [0, 0], "cws_listed_home": [0, 0]}
    for y in SEASONS:
        s = b[y]
        d = feed_games(y)
        d = d[(d.state == "final") & d.home_score.notna()].drop_duplicates("url")
        feed = set(d.home) | set(d.away)
        fn = lambda t: feed_name(t, feed, m)
        field = {fn(t["team"]) for t in s["teams"]} - {None}
        pg = d[d.home.isin(field) & d.away.isin(field) & (d.date > SELECTION[y])]
        cws = {fn(t) for t in s["cws"]}
        reg_end = pd.Timestamp(SELECTION[y]) + pd.Timedelta(days=8)          # regionals: Friday-Monday after selection
        for r in s["regionals"]:
            host, tm = fn(r["host"]), {fn(t["team"]) for t in r["teams"]}
            g = pg[pg.home.isin(tm) & pg.away.isin(tm) & (pg.date <= reg_end)]
            for h, a, hs, as_ in zip(g.home, g.away, g.home_score, g.away_score):
                hw = hs > as_
                if host in (h, a):
                    tot["regional_host"][0] += (h == host) == hw; tot["regional_host"][1] += 1
                else:
                    tot["regional_no_host_listed_home"][0] += hw; tot["regional_no_host_listed_home"][1] += 1
        sup_end = reg_end + pd.Timedelta(days=8)
        for sp in s["supers"]:
            if not sp["host"]:
                continue
            a_, c_ = (fn(t) for t in sp["teams"]); host = fn(sp["host"])
            g = pg[(((pg.home == a_) & (pg.away == c_)) | ((pg.home == c_) & (pg.away == a_))) & (pg.date > reg_end) & (pg.date <= sup_end)]
            for h, hs, as_ in zip(g.home, g.home_score, g.away_score):
                tot["super_host"][0] += (h == host) == (hs > as_); tot["super_host"][1] += 1
        g = pg[pg.home.isin(cws) & pg.away.isin(cws) & (pg.date > sup_end)]
        tot["cws_listed_home"][0] += int((g.home_score > g.away_score).sum()); tot["cws_listed_home"][1] += len(g)
    out = {k: binom(w, n) for k, (w, n) in tot.items()}
    out["_note"] = ("postseason games from the scoreboard feed 2015-2025 (no 2020), sites from the published brackets: a host's games "
                    "at its own park are won by the host; at neutral sites the feed's listed home team. Regionals: Friday-Monday "
                    "after selection Monday; super regionals: the next eight days; CWS: after that.")
    out["conf"] = "B"
    return out


def standings(tier: dict) -> dict:
    sd = {t: {} for t in TIERS}
    best = {}
    for y in SEASONS:
        d = feed_games(y)
        end = pd.Timestamp(SELECTION[y]) - pd.Timedelta(days=6)
        reg = d[(d.date < end) & (d.home != "TBA") & (d.away != "TBA")]
        if (reg.state != "final").mean() > MAX_UNRESOLVED:      # 2015 and 2016: results missing in the feed
            continue
        d = d[(d.state == "final") & d.home_score.notna() & (d.home_score != d.away_score)].drop_duplicates("url")
        d = d[(d.date < end) & d.home.isin(tier) & d.away.isin(tier)]
        w = pd.concat([d.home[d.home_score > d.away_score], d.away[d.away_score > d.home_score]]).value_counts()
        l = pd.concat([d.home[d.home_score < d.away_score], d.away[d.away_score < d.home_score]]).value_counts()
        rec = pd.DataFrame({"w": w, "l": l}).fillna(0)
        rec = rec[rec.w + rec.l >= 30]
        rec["pct"] = rec.w / (rec.w + rec.l)
        for t in TIERS:
            x = rec[rec.index.map(lambda n: tier.get(n) == t)]
            sd[t][y] = round(float(x.pct.std(ddof=1)), 4)
        top = rec.sort_values("pct", ascending=False).iloc[0]
        best[y] = {"team": top.name, "w": int(top.w), "l": int(top.l), "pct": round(float(top.pct), 4)}
    used = sorted(best)
    bp = np.array([best[y]["pct"] for y in used])
    return {"_note": "Division I games before the Tuesday of conference tournament week (selection Monday - 6 days), teams with 30+ "
                     "decided games, tiers by the program's 2025 conference; seasons whose feed leaves more than 5% of regular-season entries "
                     "without a result are left out (2015, 2016 and 2021, the last also a shortened season)",
            "conf": "B", "seasons": used,
            "win_pct_sd_by_tier": {t: {"value": round(float(np.mean(list(sd[t].values()))), 4),
                                       "se": round(float(np.std(list(sd[t].values()), ddof=1) / np.sqrt(len(sd[t]))), 4),
                                       "by_season": sd[t]} for t in TIERS},
            "best_win_pct": {"value": round(float(bp.mean()), 4), "range": [round(float(bp.min()), 4), round(float(bp.max()), 4)], "by_season": best}}


def main() -> None:
    b, m, tier = brackets(), name_map(), tiers()
    out = {"built": dt.date.today().isoformat()}
    out.update(seeds_and_field(b, tier, m))
    out["home_field"] = home_field(b, m)
    out["standings"] = standings(tier)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    main()
