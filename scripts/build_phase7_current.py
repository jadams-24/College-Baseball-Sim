"""Phase 7 benchmarks that depend on the conference map, on the seasons played under the current one
(owner decision 2026-10-05): 2025 and 2026, reported separately and together. The sim builds the 2025 map
and was fitted to 2025 data, so 2026 is the independent check.

Results: WarrenNolan team schedules (data/ncaa_<season>/warrennolan/games_<season>.csv: Division I flags,
neutral sites, complete conference tournaments). Field: published brackets (data/ncaa_brackets). Tiers: the
2025 tier of each conference (data/ncaa_2025/pbp/teams_2025.csv), applied to the team's conference of that
season (2026: the NCAA RPI page's conference column).
Rows per season:
  rpi_at_rank      RPI of the teams ranked 1, 16, 32 and 64 (engine.rpi, Division I games before selection)
  mean_rpi_by_tier mean RPI by tier
  at_large_by_tier, conferences_multi_bid, worst_rpi_rank_at_large, best_rpi_rank_left_out
  win_pct_sd_by_tier  win% SD across teams with 30+ decided Division I regular-season games (conference
                   tournaments and later excluded)
  p4_vs_mid        P4 against mid-tier nonconference regular-season games: P4 win%, run margin and its SD
Season-to-season variation: the year-to-year swings of the same rows in 2022-2025 (scoreboard feed, the
seasons whose results are complete), as the successive-difference SD sqrt(mean(diff^2) / 2) (the von Neumann
estimator: a level shift such as realignment moves it less than the plain SD). GUESS, config.phase7.

Writes the "current" block of data/ncaa_2025/derived/phase7_benchmarks.json.

    python3 scripts/build_phase7_current.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from build_phase7_benchmarks import SELECTION  # noqa: E402
from engine.rpi import rpi  # noqa: E402
from lib.brackets import brackets, feed_counts, feed_games, feed_name, name_map  # noqa: E402

BENCH = ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json"
CURRENT = ("2025", "2026")
SWING = ("2022", "2023", "2024", "2025")
SEL = dict(SELECTION, **{"2026": "2026-05-25"})
TIERS = ("p4", "mid", "low")
RANKS = (1, 16, 32, 64)


def norm(x: str) -> str:
    return str(x).lower().replace(".", "").replace("state", "st").replace("–", "-").replace("'", "").replace(" ", "")


def conf_tier() -> tuple[dict, dict]:
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    ct = t.groupby("conference").tier.agg(lambda s: s.mode().iloc[0]).to_dict()
    return ct, {norm(a): (c, ti) for a, c, ti in zip(t.team, t.conference, t.tier)}


def season_rows(y: str, rpis: dict, tier: dict, conf: dict, field: dict, games_reg: pd.DataFrame) -> dict:
    v = sorted(rpis.values(), reverse=True)
    out = {"rpi_at_rank": {str(k): v[k - 1] for k in RANKS}}
    out["mean_rpi_by_tier"] = {t: float(np.mean([r for x, r in rpis.items() if tier.get(x) == t])) for t in TIERS}
    rank = {x: i + 1 for i, x in enumerate(sorted(rpis, key=lambda x: -rpis[x]))}
    atl, auto = field["at_large"], field["auto"]
    out["at_large_by_tier"] = {t: sum(tier.get(x) == t for x in atl) for t in TIERS}
    out["conferences_multi_bid"] = int((pd.Series(field["conference"]).value_counts() > 1).sum())
    out["worst_rpi_rank_at_large"] = max(rank[x] for x in atl if x in rank)
    out["best_rpi_rank_left_out"] = min(r for x, r in rank.items() if x not in atl and x not in auto)
    g = games_reg[games_reg.home_score != games_reg.away_score]
    w = pd.concat([g.home[g.home_score > g.away_score], g.away[g.away_score > g.home_score]]).value_counts()
    l = pd.concat([g.home[g.home_score < g.away_score], g.away[g.away_score < g.home_score]]).value_counts()
    rec = pd.DataFrame({"w": w, "l": l}).fillna(0)
    rec = rec[rec.w + rec.l >= 30]
    pct = rec.w / (rec.w + rec.l)
    out["win_pct_sd_by_tier"] = {t: float(pct[[tier.get(x) == t for x in pct.index]].std(ddof=1)) for t in TIERS}
    nc = g[[conf.get(h) != conf.get(a) for h, a in zip(g.home, g.away)]]
    pm = nc[[{tier.get(h), tier.get(a)} == {"p4", "mid"} for h, a in zip(nc.home, nc.away)]]
    marg = np.where([tier.get(h) == "p4" for h in pm.home], pm.home_score - pm.away_score, pm.away_score - pm.home_score)
    out["p4_vs_mid"] = {"n": int(len(pm)), "p4_win": float((marg > 0).mean()), "margin": float(marg.mean()), "margin_sd": float(marg.std(ddof=1))}
    return out


def wn_season(y: str, ct: dict, team25: dict, b: dict) -> dict:
    g = pd.read_csv(ROOT / f"data/ncaa_{y}/warrennolan/games_{y}.csv")
    g = g[(g.status == "final") & g.home_d1.astype(bool) & g.away_d1.astype(bool) & (g.date < SEL[y])].copy()
    nm = pd.read_csv(ROOT / "data/ncaa_2026/team_name_map.csv")
    to_ncaa = dict(zip(nm.warrennolan_name, nm.ncaa_name))
    conf26 = dict(zip(pd.read_csv(ROOT / "data/ncaa_2026/rpi/ncaa_rpi_through_2026-05-24.csv").school,
                      pd.read_csv(ROOT / "data/ncaa_2026/rpi/ncaa_rpi_through_2026-05-24.csv").conference))
    names = sorted(set(g.home) | set(g.away))
    conf, tier = {}, {}
    for x in names:
        n = to_ncaa.get(x, x)
        c = conf26.get(n) if y == "2026" else team25.get(norm(n), (None, None))[0]
        if c is None:
            c = team25.get(norm(n), (None, None))[0] or conf26.get(n)
        conf[x], tier[x] = c, ct.get(c)
    dec = g[g.home_score != g.away_score]
    r = rpi(zip(dec.home, dec.away, dec.home_score > dec.away_score, dec.neutral.astype(bool)))
    rp = {x: v["rpi"] for x, v in r.items()}
    # field: bracket names -> WarrenNolan names
    by_norm = {norm(x): x for x in names} | {norm(to_ncaa.get(x, x)): x for x in names}
    m = name_map()
    s = b[y]
    alias = {"Saint Mary's": "Saint Mary's College", "Saint Mary's (CA)": "Saint Mary's College"}   # WarrenNolan spelling
    pick = lambda t: (by_norm.get(norm(t)) or by_norm.get(norm(m.get(t, t))) or by_norm.get(norm(t.replace(" State", " St.")))
                      or by_norm.get(norm(alias.get(t, ""))))
    field = {"auto": [pick(t["team"]) for t in s["teams"] if t["bid"] == "auto"],
             "at_large": [pick(t["team"]) for t in s["teams"] if t["bid"] != "auto"],
             "conference": [t["conference"] for t in s["teams"] if t["conference"] not in ("Independent",)]}
    missing = [t["team"] for t in s["teams"] if pick(t["team"]) is None]
    post = g.event.astype(str).str.contains("Tournament|Championship|Regional|Super|World Series", case=False, na=False) & (pd.to_datetime(g.date).dt.month >= 5)
    out = season_rows(y, rp, tier, conf, field, g[~post])
    out["unmatched_field_teams"] = missing
    return out


def feed_season(y: str, ct: dict, team25: dict, b: dict) -> dict:
    """The same rows from the scoreboard feed (no neutral flags), for the 2022-2025 swings."""
    d = feed_games(y); fc = feed_counts(d)
    f = d[(d.state == "final") & d.home_score.notna() & (d.date < SEL[y])].drop_duplicates("url")
    known = {x for x in set(f.home) | set(f.away) if norm(x) in team25}
    f = f[f.home.isin(known) & f.away.isin(known)]
    conf = {x: team25[norm(x)][0] for x in known}
    tier = {x: team25[norm(x)][1] for x in known}
    dec = f[f.home_score != f.away_score]
    r = rpi(zip(dec.home, dec.away, dec.home_score > dec.away_score, [False] * len(dec)))
    rp = {x: v["rpi"] for x, v in r.items()}
    m = name_map(); s = b[y]
    field = {"auto": [feed_name(t["team"], fc, m) for t in s["teams"] if t["bid"] == "auto"],
             "at_large": [feed_name(t["team"], fc, m) for t in s["teams"] if t["bid"] != "auto"],
             "conference": [t["conference"] for t in s["teams"] if t["conference"] not in ("Independent",)]}
    end = pd.Timestamp(SEL[y]) - pd.Timedelta(days=6)
    return season_rows(y, rp, tier, conf, field, f[f.date < end])


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, f"{prefix}{k}/"))
        elif isinstance(v, (int, float)):
            out[prefix + k] = float(v)
    return out


def main() -> None:
    ct, team25 = conf_tier()
    b = brackets()
    cur = {y: wn_season(y, ct, team25, b) for y in CURRENT}
    swing = {y: feed_season(y, ct, team25, b) for y in SWING}
    fc = {y: flat({k: v for k, v in cur[y].items() if k != "unmatched_field_teams"}) for y in CURRENT}
    fs = {y: flat(swing[y]) for y in SWING}
    rows = {}
    for key in fc[CURRENT[0]]:
        vals = [fc[y][key] for y in CURRENT]
        sw = np.array([fs[y][key] for y in SWING if key in fs[y]])
        sigma = float(np.sqrt(np.mean(np.diff(sw) ** 2) / 2)) if len(sw) > 1 else None
        rows[key] = {"by_season": {y: round(v, 4) for y, v in zip(CURRENT, vals)}, "value": round(float(np.mean(vals)), 4),
                     "season_sd": round(sigma, 4) if sigma is not None else None,
                     "se": round(sigma / np.sqrt(len(CURRENT)), 4) if sigma is not None else None,
                     "swing_2022_2025": {y: round(fs[y][key], 4) for y in SWING if key in fs[y]}}
    block = {"_note": __doc__, "built": dt.date.today().isoformat(), "seasons": list(CURRENT), "conf": "B",
             "conf_note": "WarrenNolan results match the NCAA's published 2026 records for every team; brackets from Wikipedia (validated); "
                          "two seasons, so season-to-season variation dominates the tolerance",
             "unmatched_field_teams": {y: cur[y]["unmatched_field_teams"] for y in CURRENT}, "rows": rows}
    bench = json.loads(BENCH.read_text())
    bench["current"] = block
    BENCH.write_text(json.dumps(bench, indent=1) + "\n")
    for k, r in rows.items():
        print(f"{k:38s} 2025 {r['by_season']['2025']:>8} 2026 {r['by_season']['2026']:>8} | mean {r['value']:>8} | season SD {r['season_sd']} | swings {list(r['swing_2022_2025'].values())}")
    print("unmatched:", block["unmatched_field_teams"])


if __name__ == "__main__":
    main()
