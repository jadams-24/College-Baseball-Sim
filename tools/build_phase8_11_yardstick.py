"""Build the Phase 8-11 yardstick tables and benchmarks_phase8_11.json (data-prep session, 2026-10-10).

    python tools/build_phase8_11_yardstick.py

Reads only committed data: the 2025 roster aggregates (data/ncaa_2025/roster_aggregates/), the school
locations (IPEDS), the 2025 D1 scoreboard, the WMT player-season aggregates (data/wmt_player_seasons/,
when present) and the hand-researched entries in data/phase8_11/manual_entries.json (every entry with
its source URL, fetch date, sample size and grade). Writes data/phase8_11/*.csv and
benchmarks_phase8_11.json. No player rows anywhere.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AGG = ROOT / "data/ncaa_2025/roster_aggregates"
OUT = ROOT / "data/phase8_11"
WMT = ROOT / "data/wmt_player_seasons"
TIERS = ["p4", "mid", "low"]
TALENT_STATES = ["TX", "FL", "CA", "GA", "NC", "AZ", "TN", "SC", "VA", "IL", "OH", "NY", "NJ", "PA", "LA", "AL", "OK", "MS", "WA", "OR"]
ROSTER_SRC = {"source": "2025 roster pages of 283 WMT-sample teams (233 parsed), data/ncaa_2025/roster_aggregates/ (tools/fetch_rosters.py, tools/aggregate_rosters.py)",
              "fetched": "2026-10-09", "season": 2025}


def share_table(counts: pd.Series) -> dict:
    tot = float(counts.sum())
    return {str(k): {"count": int(v), "share": round(float(v) / tot, 4) if tot else None} for k, v in counts.items()}


def se_share(p: float, n: int) -> float:
    return round(float(np.sqrt(max(p * (1 - p), 0) / max(n, 1))), 4)


def tier_block(df: pd.DataFrame, key: str, levels: list[str], by_school: bool = True) -> dict:
    """Shares of `key` by tier: pooled over players, with the SD across schools of the school's share."""
    out = {}
    for tier, gdf in list(df.groupby("tier")) + [("all", df)]:
        if tier not in TIERS + ["all"]:
            continue
        c = gdf.groupby(key)["count"].sum().reindex(levels, fill_value=0)
        n = int(c.sum())
        block = {"players": n, "schools": int(gdf["team_ncaa_id"].nunique())}
        for lv in levels:
            p = float(c[lv]) / n if n else None
            block[lv] = {"count": int(c[lv]), "share": round(p, 4) if p is not None else None, "se": se_share(p, n) if p is not None else None}
        if by_school:
            per = gdf.pivot_table(index="team_ncaa_id", columns=key, values="count", aggfunc="sum", fill_value=0)
            per = per.reindex(columns=levels, fill_value=0)
            sh = per.div(per.sum(axis=1), axis=0)
            for lv in levels:
                block[lv]["school_sd"] = round(float(sh[lv].std(ddof=1)), 4) if len(sh) > 1 else None
        out[tier] = block
    return out


def roster_composition() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    o = pd.read_csv(AGG / "origins_by_school.csv")
    o = o[o.tier.isin(TIERS)]
    classes = ["Fr", "So", "Jr", "Sr", "Gr", "unknown"]
    cls = tier_block(o, "class", classes)
    origins = tier_block(o, "origin", ["high_school_only", "d1_transfer", "juco", "other_four_year", "unknown"])
    # class x origin, by tier (shares within class)
    co = o.groupby(["tier", "class", "origin"])["count"].sum().reset_index()
    co["share_within_class"] = co["count"] / co.groupby(["tier", "class"])["count"].transform("sum")
    # roster size: players parsed per school
    size = o.groupby(["tier", "team_ncaa_id"])["count"].sum().reset_index()
    sizes = {}
    for tier, gdf in list(size.groupby("tier")) + [("all", size)]:
        sizes[tier] = {"schools": int(len(gdf)), "mean": round(float(gdf["count"].mean()), 2), "sd": round(float(gdf["count"].std(ddof=1)), 2),
                       "p10": float(gdf["count"].quantile(.1)), "p50": float(gdf["count"].median()), "p90": float(gdf["count"].quantile(.9)),
                       "min": int(gdf["count"].min()), "max": int(gdf["count"].max()),
                       "share_over_34": round(float((gdf["count"] > 34).mean()), 3)}
    # pitchers vs position players (handedness_by_position: tier scope)
    h = pd.read_csv(AGG / "handedness_by_position.csv")
    h = h[h.scope.isin(["tier", "all"])]
    pos = {}
    for val, gdf in h.groupby("scope_value"):
        c = gdf.groupby("position_group")["count"].sum()
        n = int(c.sum())
        p = int(c.get("P", 0))
        tw = int(c.get("two-way", 0))
        pos[val] = {"players": n, "pitchers": p, "two_way": tw, "position_players": n - p - tw,
                    "pitcher_share": round(p / n, 4), "pitcher_or_two_way_share": round((p + tw) / n, 4),
                    "by_group": {k: int(v) for k, v in c.items()}}
    return ({"class_by_tier": cls, "origin_by_tier": origins, "roster_size_by_tier": sizes, "position_mix_by_tier": pos},
            co.round(4), size.rename(columns={"count": "players_listed"}))


def roster_detail() -> dict:
    """Redshirt flag, class x position group and the D1 transfer flow by tier, from the roster run of
    2026-10-10 (class_detail_by_tier.csv, d1_transfer_flow.csv, age_by_class.csv); absent before that run."""
    out = {}
    cd = AGG / "class_detail_by_tier.csv"
    if cd.exists():
        c = pd.read_csv(cd)
        t = c[(c.scope == "tier") & c.scope_value.isin(TIERS) & c["class"].isin(["Fr", "So", "Jr", "Sr", "Gr"])]
        rs = {}
        for (tier, cls), g in t.groupby(["scope_value", "class"]):
            rs.setdefault(tier, {})[cls] = {"players": int(g["count"].sum()), "redshirt_share": round(float(g.loc[g.redshirt == True, "count"].sum() / g["count"].sum()), 4)}
        for tier, g in t.groupby("scope_value"):
            rs[tier]["all"] = {"players": int(g["count"].sum()), "redshirt_share": round(float(g.loc[g.redshirt == True, "count"].sum() / g["count"].sum()), 4)}
        out["redshirt_by_class"] = rs
        pos = t.groupby(["scope_value", "class", "pos_group"])["count"].sum().reset_index()
        out["class_by_position"] = {}
        for (tier, cls), g in pos.groupby(["scope_value", "class"]):
            n = g["count"].sum()
            out["class_by_position"].setdefault(tier, {})[cls] = {r.pos_group: round(float(r["count"] / n), 4) for _, r in g.iterrows()}
    fl = AGG / "d1_transfer_flow.csv"
    if fl.exists():
        f = pd.read_csv(fl)
        out["d1_transfer_flow"] = {}
        for sc, g in f.groupby("scope_value"):
            out["d1_transfer_flow"][sc] = {"d1_transfers": int(g["count"].sum()), "from_prev_tier": {r.prev_tier: {"count": int(r["count"]), "share": float(r.share)} for _, r in g.iterrows()}}
        out["d1_transfer_flow"]["note"] = "Tier of the previous D1 school named first on the roster page for players classified d1_transfer; unknown = only an alias matched. Current tier = the roster's school."
    ag = AGG / "age_by_class.csv"
    if ag.exists():
        a = pd.read_csv(ag)
        out["age_by_class"] = {"rows": int(len(a)), "note": "no roster page in the 2025 fetch lists a birthdate or age (coverage.csv share_birthdate_or_age_filled = 0)"} if len(a) == 0 else a.to_dict("records")
    return out


def geography() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    ht = pd.read_csv(AGG / "hometown_by_school.csv")
    loc = pd.read_csv(ROOT / "data/ncaa_2025/school_locations_2025.csv")[["ncaa_team_id", "state"]].rename(columns={"ncaa_team_id": "team_ncaa_id", "state": "school_state"})
    ht = ht.merge(loc, on="team_ncaa_id", how="left")
    ht = ht[ht.tier.isin(TIERS)]
    ht["in_state"] = (ht.area_type == "us_state") & (ht.hometown_area == ht.school_state)
    # (a) where the players of each home state go, by tier (the "export" view)
    us = ht[ht.area_type == "us_state"]
    by_state = us.groupby(["hometown_area", "tier"])["count"].sum().unstack(fill_value=0).reindex(columns=TIERS, fill_value=0)
    by_state["total"] = by_state.sum(axis=1)
    by_state["in_state_players"] = us[us.in_state].groupby("hometown_area")["count"].sum().reindex(by_state.index).fillna(0).astype(int)
    by_state["in_state_share_of_states_players"] = (by_state["in_state_players"] / by_state["total"]).round(4)
    for t in TIERS:
        by_state[f"share_{t}"] = (by_state[t] / by_state["total"]).round(4)
    by_state = by_state.sort_values("total", ascending=False).reset_index().rename(columns={"hometown_area": "home_state"})
    # (b) schools in each state: share of their rosters that is in-state, by tier
    sch = ht.groupby(["school_state", "tier", "team_ncaa_id"]).apply(lambda g: pd.Series({"players": g["count"].sum(), "in_state": g.loc[g.in_state, "count"].sum()})).reset_index()
    sch["in_state_share"] = sch.in_state / sch.players
    rows = []
    for (st, tier), gdf in list(sch.groupby(["school_state", "tier"])) + [((st, "all"), gdf2) for st, gdf2 in sch.groupby("school_state")]:
        rows.append({"school_state": st, "tier": tier, "schools": int(len(gdf)), "players": int(gdf.players.sum()),
                     "in_state_share_pooled": round(float(gdf.in_state.sum() / gdf.players.sum()), 4),
                     "in_state_share_school_mean": round(float(gdf.in_state_share.mean()), 4),
                     "in_state_share_school_sd": round(float(gdf.in_state_share.std(ddof=1)), 4) if len(gdf) > 1 else None})
    schools_by_state = pd.DataFrame(rows).sort_values(["school_state", "tier"])
    # (c) foreign share by tier and top countries
    intl = ht[ht.area_type == "international"].groupby(["tier", "hometown_area"])["count"].sum().reset_index()
    allp = ht.groupby("tier")["count"].sum()
    block = {"talent_states": {}, "foreign": {}}
    for st in TALENT_STATES:
        r = by_state[by_state.home_state == st]
        s = schools_by_state[(schools_by_state.school_state == st)]
        if len(r):
            r = r.iloc[0]
            block["talent_states"][st] = {"players_from_state": int(r.total), "share_of_all_located_players": round(float(r.total / us["count"].sum()), 4),
                                          "stay_in_state_share": float(r.in_state_share_of_states_players),
                                          "to_tier": {t: float(r[f"share_{t}"]) for t in TIERS},
                                          "schools_in_state": {row.tier: {"schools": int(row.schools), "in_state_share_pooled": float(row.in_state_share_pooled),
                                                                          "school_sd": row.in_state_share_school_sd} for row in s.itertuples()}}
    for tier in TIERS:
        n = int(allp.get(tier, 0))
        f = int(intl[intl.tier == tier]["count"].sum())
        top = intl[intl.tier == tier].sort_values("count", ascending=False).head(6)
        block["foreign"][tier] = {"players": n, "foreign": f, "share": round(f / n, 4), "top": {r.hometown_area: int(r["count"]) for _, r in top.iterrows()}}
    block["in_state_by_tier"] = {t: {"players": int(allp[t]), "in_state_share": round(float(ht[(ht.tier == t) & ht.in_state]["count"].sum() / allp[t]), 4)} for t in TIERS}
    return block, by_state, schools_by_state


def d1_vs_non_d1() -> tuple[dict, pd.DataFrame]:
    g = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    d1 = set(t.team) | {"New Orleans", "LSU New Orleans"}
    g = g[g.state == "final"].drop_duplicates("gameID").copy()
    for s in ("home_score", "away_score"):
        g[s] = pd.to_numeric(g[s], errors="coerce")
    g = g.dropna(subset=["home_score", "away_score"])
    g = g[(g.home != "TBA") & (g.away != "TBA")]
    g["home_d1"], g["away_d1"] = g.home.isin(d1), g.away.isin(d1)
    x = g[g.home_d1 != g.away_d1].copy()
    x["d1_score"] = np.where(x.home_d1, x.home_score, x.away_score)
    x["nd_score"] = np.where(x.home_d1, x.away_score, x.home_score)
    x["d1_team"] = np.where(x.home_d1, x.home, x.away)
    x["nd_team"] = np.where(x.home_d1, x.away, x.home)
    x["nd_conf"] = np.where(x.home_d1, x.away_conf, x.home_conf)
    x["d1_home"] = x.home_d1
    x = x.merge(t[["team", "tier"]], left_on="d1_team", right_on="team", how="left")
    x["d1_win"] = x.d1_score > x.nd_score
    x["margin"] = x.d1_score - x.nd_score
    rows = []
    for tier, gdf in list(x.groupby("tier")) + [("all", x)]:
        rows.append({"d1_tier": tier, "games": int(len(gdf)), "d1_win_pct": round(float(gdf.d1_win.mean()), 4),
                     "d1_runs_per_game": round(float(gdf.d1_score.mean()), 3), "non_d1_runs_per_game": round(float(gdf.nd_score.mean()), 3),
                     "margin_mean": round(float(gdf.margin.mean()), 3), "margin_sd": round(float(gdf.margin.std(ddof=1)), 3),
                     "log_run_ratio": round(float(np.log(gdf.d1_score.mean() / gdf.nd_score.mean())), 4),
                     "d1_home_share": round(float(gdf.d1_home.mean()), 3), "distinct_non_d1_opponents": int(gdf.nd_team.nunique())})
    tab = pd.DataFrame(rows)
    confs = x.nd_conf.fillna("").value_counts().head(12).to_dict()
    return ({"games_table": tab.to_dict("records"), "non_d1_conferences_top": {k: int(v) for k, v in confs.items()},
             "note": "2025 D1 scoreboard finals with exactly one D1 team (non-D1 are D2, D3, NAIA and others; the feed tags most as IND, so the level mix is unknown). D1 teams host most of these games. A scoreboard strength fit on D2's own feed would place D2 properly; this is the raw crossover margin."},
            tab)


def money_eada() -> tuple[dict, pd.DataFrame]:
    """Baseball operating expenses, total expenses and revenue by tier from the committed EADA 2024-25
    extract (304 institutions; the service academies do not file). EADA reports coaching salaries only
    per institution across all men's teams, not by sport, so baseball coaching pay is not here."""
    e = pd.read_csv(ROOT / "data/eada/baseball_eada_2024_25.csv")
    sch = pd.read_csv(ROOT / "data/schools/schools.csv")[["unitid", "tier", "conference"]]
    e = e.merge(sch, on="unitid", how="inner")
    e = e[e.tier.isin(TIERS)]
    e["expenses_per_participant"] = e.baseball_total_expenses / e.participants
    e["revenue_minus_expenses"] = e.baseball_total_revenue - e.baseball_total_expenses
    cols = ["baseball_operating_expenses", "baseball_total_expenses", "baseball_total_revenue", "participants", "assistant_coaches", "expenses_per_participant", "revenue_minus_expenses"]
    rows, block = [], {}
    for tier, gdf in list(e.groupby("tier")) + [("all", e)]:
        b = {"schools": int(len(gdf))}
        for c in cols:
            q = gdf[c].quantile([.1, .25, .5, .75, .9])
            b[c] = {"mean": round(float(gdf[c].mean()), 1), "p10": round(float(q[.1]), 1), "p25": round(float(q[.25]), 1), "median": round(float(q[.5]), 1),
                    "p75": round(float(q[.75]), 1), "p90": round(float(q[.9]), 1), "min": round(float(gdf[c].min()), 1), "max": round(float(gdf[c].max()), 1)}
            rows.append({"tier": tier, "measure": c, **{k: v for k, v in b[c].items()}, "schools": len(gdf)})
        b["share_revenue_equals_expenses"] = round(float((gdf.baseball_total_revenue == gdf.baseball_total_expenses).mean()), 3)
        block[tier] = b
    conf = e.groupby("conference").agg(schools=("unitid", "size"), median_total_expenses=("baseball_total_expenses", "median"),
                                       median_operating=("baseball_operating_expenses", "median"), median_revenue=("baseball_total_revenue", "median")).round(0).reset_index()
    conf = conf.merge(sch.drop_duplicates("conference")[["conference", "tier"]], on="conference").sort_values("median_total_expenses", ascending=False)
    block["by_conference"] = conf.to_dict("records")
    block["note"] = ("EADA 2024-25 (reporting year July 2024 - June 2025, the last season before revenue sharing). Total expenses include "
                     "aid, salaries, recruiting, travel, equipment and facilities charges; operating (game-day) expenses are the subset. "
                     "Revenue equals expenses at many schools by convention (institutional support fills the gap), so revenue is not profit.")
    return block, pd.DataFrame(rows)


def wmt_blocks() -> dict:
    if not (WMT / "aging_curves.csv").exists():
        return {"status": "not built yet"}
    cov = pd.read_csv(WMT / "coverage.csv")
    ac = pd.read_csv(WMT / "aging_curves.csv")
    ret = pd.read_csv(WMT / "retention_by_class.csv")
    size = pd.read_csv(WMT / "roster_size.csv")
    out = {"coverage": cov.to_dict("records"), "aging_by_class": {}, "retention_by_class": {}, "stat_roster_size": size.to_dict("records")}
    for (role, cls, rate), gdf in ac[ac.scope == "class"].groupby(["role", "class", "rate"]):
        r = gdf.iloc[0]
        out["aging_by_class"].setdefault(role, {}).setdefault(cls, {})[rate] = {
            "players": int(r.players), "level_t": round(float(r.level_t), 4), "level_t1": round(float(r.level_t1), 4),
            "delta_mean": round(float(r.delta_mean), 4), "delta_se": round(float(r.delta_se), 4), "scale": r.scale}
    sv_p = WMT / "survivor_selection.csv"
    if sv_p.exists():
        sv = pd.read_csv(sv_p)
        out["survivor_bias"] = {}
        for (role, cls), gdf in sv.groupby(["role", "class"]):
            out["survivor_bias"].setdefault(role, {})[cls] = {r.rate: {"survivor_share": r.survivor_share, "selection_gap_sd": r.selection_gap_sd,
                                                                  "yoy_corr": r.yoy_corr_survivors, "rtm_bias_logit": r.rtm_bias_logit, "rtm_bias_raw": r.rtm_bias_raw}
                                                         for r in gdf.itertuples()}
    rc = ret[ret.scope == "class"].groupby("class")[["players", "same_team", "other_client_team", "absent"]].sum()
    for cls, r in rc.iterrows():
        out["retention_by_class"][cls] = {"players": int(r.players), "same_team": round(float(r.same_team / r.players), 4),
                                          "other_client_team": round(float(r.other_client_team / r.players), 4), "absent": round(float(r.absent / r.players), 4)}
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    comp, class_origin, sizes = roster_composition()
    geo, by_state, schools_by_state = geography()
    xd, xtab = d1_vs_non_d1()
    money, money_tab = money_eada()
    money_tab.to_csv(OUT / "eada_baseball_by_tier_2024_25.csv", index=False)
    class_origin.to_csv(OUT / "class_by_origin_2025.csv", index=False)
    sizes.to_csv(OUT / "roster_size_by_school_2025.csv", index=False)
    by_state.to_csv(OUT / "players_by_home_state_2025.csv", index=False)
    schools_by_state.to_csv(OUT / "in_state_share_by_school_state_2025.csv", index=False)
    xtab.to_csv(OUT / "d1_vs_non_d1_2025.csv", index=False)
    manual_p = OUT / "manual_entries.json"
    manual = json.loads(manual_p.read_text()) if manual_p.exists() else {}
    bench = {
        "_meta": {"purpose": "Phase 8-11 yardstick (roster rules, recruiting, development, program). Every entry carries its source, fetch date, sample size and confidence grade. Built by tools/build_phase8_11_yardstick.py from committed aggregates plus data/phase8_11/manual_entries.json; never edit values by hand without a note in PHASE8_NOTES.md.",
                  "built": dt.date.today().isoformat(), "confidence_key": {"A": "official or primary source, directly usable", "B": "public, usable after processing", "C": "partial or a proxy", "D": "no data; a GUESS until data is found"}},
        "roster_composition_2025": {**ROSTER_SRC, "conf": "B", "note": "Spring 2025 rosters (before the 34-man limit, effective 7/1/25). Classes as listed, redshirt markers dropped (R-Fr = Fr); Gr = graduate, 5th/6th year. Pitcher share from the listed position; two-way players counted separately. Redshirt, class x position and the transfer flow from the roster run of 2026-10-10 (run 38066352243).", **comp, **roster_detail()},
        "geography_2025": {**ROSTER_SRC, "conf": "B", "note": "Hometown state as listed on the roster page; school state from IPEDS. State-level only.", **geo},
        "d1_vs_non_d1_2025": {"source": "data.ncaa.com 2025 D1 scoreboard (data/ncaa_2025/scoreboard/games_2025.csv)", "fetched": "2026-09-30", "conf": "C", **xd},
        "development_2022_2026_wmt": {"source": "api.wmt.games player season statistics (data/wmt_player_seasons/)", "conf": "B", **wmt_blocks()},
        "program_money_eada_2024_25": {"source": "U.S. Department of Education EADA 2024-25 (data/eada/baseball_eada_2024_25.csv, fetched 2026-10-08), tiers from data/schools/schools.csv", "conf": "A", **money},
    }
    bench.update(manual)
    (ROOT / "benchmarks_phase8_11.json").write_text(json.dumps(bench, indent=1))
    print("wrote", ROOT / "benchmarks_phase8_11.json", "and", OUT)


if __name__ == "__main__":
    main()
