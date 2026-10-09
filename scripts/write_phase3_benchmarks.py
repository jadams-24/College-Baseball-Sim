"""Write the Phase 3 block of benchmarks.json (handedness_platoon_2025) from the roster aggregates
(data/ncaa_2025/roster_aggregates/, fetch of 2026-10-07/08; counts only) and data/ncaa_2025/derived/phase3_inputs_2025.json.

Rows (plan approved 2026-10-08 with the owner's adjustments):
  lhp_share                 left-handers among the pitchers who appeared, by role (a starter: half or more of his appearances
                            are starts), D1: the tiers weighted by their number of teams (the play-by-play over-represents P4);
                            tolerance 1.96 SE (each tier's conference-clustered SE, combined)
  lhp_by_tier               the same by tier and role: the tier-gradient check (not fitted: no code path reads tier to set a
                            hand). Tolerance: the conference-clustered 95% interval (owner, 2026-10-08), point estimate alongside
  bats_by_group, throws_L_by_group
                            position players' bats (L / R / S) and throwing hand by position group (C, 1B, IF, OF, UT/DH), every
                            parsed roster (coverage approved as representative without weighting, 2026-10-08); clustered 95% interval
  bats_L_by_tier            batters' L share by tier, the groups above (check of the talent-conditional draw), with each tier's
                            roster mix of the groups (group_mix_by_tier) so the engine's share can be standardized to it
  platoon                   plate appearances with both hands known: the split (rate against left-handed pitchers minus against
                            right-handed) of K, BB, HR per PA, BABIP (hits in play over balls in play less ROE, the engine's
                            definition) and on base per PA, for batters hitting left, hitting right (switch hitters on the side
                            used) and switch hitters; within each batting tier, then the tiers weighted by their hand-known
                            plate appearances (one engine shift serves every tier; the levels are reported: see platoon_rows); the share of plate appearances by batters hitting left
                            (batting tiers) and against left-handers (pitching tiers) and the platoon advantage above random
                            pairing are reported (their binomial tolerance on plate appearances is too small: plate appearances
                            cluster by player). Tolerance of the splits: 1.96 binomial SE
  usage                     on the pooled tables (the usage model's sample): ratios of pitching-change rates between the batters
                            due up, the left-handers' share of relief entries (difference by the batter due up), the pinch-hit
                            rate's ratio (batter due up of the pitcher's hand over the other), the pinch hitters' platoon-advantage
                            share. 1.96 SE (binomial, delta method)
Every write is recorded in data/ncaa_2025/derived/benchmark_changes_phase3.json. The block is inserted as text (the rest of
the file is not reformatted).
    python3 scripts/write_phase3_benchmarks.py
"""
from __future__ import annotations

import datetime
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_pbp_benchmarks import dumps_compact  # noqa: E402
from config.phase3 import BATTER_GROUPS  # noqa: E402
from scripts.build_phase3_hands import TIERS, _conf_tier, real_lhp, tier_weights  # noqa: E402
from scripts.roster_representativeness import clustered  # noqa: E402

AGG = ROOT / "data/ncaa_2025/roster_aggregates"
D = ROOT / "data/ncaa_2025/derived"
BENCH = ROOT / "benchmarks.json"
KEY = "handedness_platoon_2025"
Z = 1.959964
SRC = ("roster aggregates 2025 (data/ncaa_2025/roster_aggregates/, fetch rosters workflow 2026-10-07/08, 232 of 277 D1 teams; "
       "counts only) and the 2025 WMT play-by-play (data/ncaa_2025/pbp)")


def r4(x):
    return round(float(x), 4)


def clustered_row(xs, ns) -> dict:
    p, lo, hi = clustered(xs, ns)
    return {"value": r4(p), "lo": r4(lo), "hi": r4(hi), "tol": r4((hi - lo) / 2)}


def weighted(cells: dict, tw: dict) -> dict:
    """Tier-weighted rate: cells {tier: (x, n)}; value and 1.96 binomial SE."""
    W = sum(tw[t] for t in cells if cells[t][1] > 0)
    v = sum(tw[t] * cells[t][0] / cells[t][1] for t in cells if cells[t][1] > 0) / W
    se = math.sqrt(sum((tw[t] / W) ** 2 * (cells[t][0] / cells[t][1]) * (1 - cells[t][0] / cells[t][1]) / cells[t][1]
                       for t in cells if cells[t][1] > 0))
    return {"value": r4(v), "tol": r4(Z * se)}


def roster_rows() -> dict:
    h = pd.read_csv(AGG / "handedness_by_position.csv")
    conf = h[(h.scope == "conference") & h.position_group.isin(BATTER_GROUPS)]
    out = {"bats_by_group": {}, "throws_L_by_group": {}}
    for g in BATTER_GROUPS:
        d = conf[(conf.position_group == g) & conf.bats.isin(["L", "R", "S"])]
        n = d.groupby("scope_value")["count"].sum()
        out["bats_by_group"][g] = {}
        for hand in ("L", "R", "S"):
            x = d[d.bats == hand].groupby("scope_value")["count"].sum().reindex(n.index, fill_value=0)
            out["bats_by_group"][g][hand] = clustered_row(list(x), list(n))
        d = conf[(conf.position_group == g) & conf.throws.isin(["L", "R"])]
        n = d.groupby("scope_value")["count"].sum()
        x = d[d.throws == "L"].groupby("scope_value")["count"].sum().reindex(n.index, fill_value=0)
        out["throws_L_by_group"][g] = clustered_row(list(x), list(n))
    tiers = _conf_tier()
    out["bats_L_by_tier"], out["group_mix_by_tier"] = {}, {}
    for t in TIERS:
        d = conf[(conf.scope_value.map(tiers) == t) & conf.bats.isin(["L", "R", "S"])]
        n = d.groupby("scope_value")["count"].sum()
        x = d[d.bats == "L"].groupby("scope_value")["count"].sum().reindex(n.index, fill_value=0)
        out["bats_L_by_tier"][t] = clustered_row(list(x), list(n))
        mix = d.groupby("position_group")["count"].sum()
        out["group_mix_by_tier"][t] = {g: r4(mix.get(g, 0) / mix.sum()) for g in BATTER_GROUPS}
    return out


def _cell_counts(x) -> dict:
    hits = x["1B"] + x["2B"] + x["3B"]
    bip = x["pa"] - x["K"] - x["BB"] - x["HBP"] - x["HR"] - x["ROE"]
    return {"K": (x["K"], x["pa"]), "BB": (x["BB"], x["pa"]), "HR": (x["HR"], x["pa"]), "BABIP": (hits, bip),
            "OB": (x["BB"] + x["HBP"] + hits + x["HR"], x["pa"])}


def platoon_rows(tw: dict) -> dict:
    """Splits, not levels: the hand-known plate appearances of a tier are not a sample of that tier's (low-tier batters in
    the play-by-play face mostly P4 pitching, its teams' schedules), so a tier's level carries its opponents. Within a
    tier the split (rate against left-handers minus against right-handers) compares the same batters, so the gate rows are
    splits, tier-weighted; the levels are reported."""
    pl = pd.read_csv(AGG / "platoon_league.csv")
    s = pl[pl.scope == "bat_tier"]
    cell = {}
    for basis, hands in (("side_used", ("L", "R")), ("listed", ("S",))):
        for bh in hands:
            for ph in ("L", "R"):
                d = s[(s.basis == basis) & (s.bat_hand == bh) & (s.pit_throws == ph)].set_index("scope_value")
                for t in TIERS:
                    cell[(bh, ph, t)] = _cell_counts(d.loc[t])
    splits, levels = {}, {}
    for bh in ("L", "R", "S"):
        # the engine's shift is one number for every tier, so the tiers are weighted by precision: their hand-known plate
        # appearances (both hands); the simulated split uses the same weights (split_weights)
        sw = {t: int(cell[(bh, "L", t)]["K"][1] + cell[(bh, "R", t)]["K"][1]) for t in TIERS}
        for r in ("K", "BB", "HR", "BABIP", "OB"):
            W, v, var = 0.0, 0.0, 0.0
            for t in TIERS:
                (xl, nl), (xr, nr) = cell[(bh, "L", t)][r], cell[(bh, "R", t)][r]
                if nl == 0 or nr == 0:
                    continue
                pl_, pr_ = xl / nl, xr / nr
                W += sw[t]; v += sw[t] * (pl_ - pr_); var += sw[t] ** 2 * (pl_ * (1 - pl_) / nl + pr_ * (1 - pr_) / nr)
            splits[f"{bh}|{r}"] = {"value": r4(v / W), "tol": r4(Z * math.sqrt(var) / W)}
            for ph in ("L", "R"):
                levels[f"{bh}|{ph}|{r}"] = {**weighted({t: cell[(bh, ph, t)][r] for t in TIERS}, tw), "gate": "report"}
        splits[f"{bh}|weights"] = sw
    u = s[s.basis == "side_used"]
    p = pl[(pl.scope == "pit_tier") & (pl.basis == "side_used")]
    side_l = {t: (u[(u.scope_value == t) & (u.bat_hand == "L")].pa.sum(), u[u.scope_value == t].pa.sum()) for t in TIERS}
    vs_lhp = {t: (p[(p.scope_value == t) & (p.pit_throws == "L")].pa.sum(), p[p.scope_value == t].pa.sum()) for t in TIERS}
    # the platoon advantage above random pairing, within each batting tier's own cells: observed share with the advantage
    # minus the share the tier's own marginals would give (bullpen and pinch-hit choices, and lineups, make the excess)
    W, v, var = 0.0, 0.0, 0.0
    raw = {}
    for t in TIERS:
        d = u[u.scope_value == t].set_index(["bat_hand", "pit_throws"]).pa
        n = d.sum()
        adv = (d[("L", "R")] + d[("R", "L")]) / n
        sl, hl = (d[("L", "L")] + d[("L", "R")]) / n, (d[("L", "L")] + d[("R", "L")]) / n
        ind = sl * (1 - hl) + (1 - sl) * hl
        raw[t] = (d[("L", "R")] + d[("R", "L")], n)
        W += tw[t]; v += tw[t] * (adv - ind); var += tw[t] ** 2 * adv * (1 - adv) / n
    # the plate-appearance mix is reported: its tolerance here is binomial on plate appearances, several times too small
    # (a player's plate appearances share his hand; the tables have no clustering unit for it)
    mix_note = "binomial tolerance on plate appearances, too small: plate appearances cluster by player (reported until a by-conference table)"
    return {"splits": splits, "levels": levels,
            "side_L_share": {**weighted(side_l, tw), "gate": "report", "_note": mix_note},
            "pa_share_vs_lhp": {**weighted(vs_lhp, tw), "gate": "report", "_note": mix_note},
            "advantage_excess": {"value": r4(v / W), "tol": r4(Z * math.sqrt(var) / W), "gate": "report", "_note": mix_note},
            "advantage_share": {**weighted(raw, tw), "gate": "report"}}


def _ratio(x1, n1, x2, n2) -> dict:
    """(x1 / n1) / (x2 / n2) and 1.96 SE (delta method, binomial counts)."""
    r = (x1 / n1) / (x2 / n2)
    return {"value": r4(r), "tol": r4(Z * r * math.sqrt(1 / x1 - 1 / n1 + 1 / x2 - 1 / n2))}


def usage_rows() -> dict:
    """Relative rows on the pooled tables, the sample the usage model is fitted on (scope all; usage by hand is one model for
    every tier, GUESSES.md): a change rate's ratio between the batters due up, the left-handers' share of relief entries by
    the batter due up (difference), the pinch-hit rate's ratio between a batter due up of the pitcher's hand and one of the
    other, and the pinch hitters' platoon-advantage share."""
    r = pd.read_csv(AGG / "relief_by_hand.csv")
    r = r[(r.scope == "all") & r.cur_throws.isin(["L", "R"]) & r.batter_bats.isin(["L", "R"])].groupby(["cur_throws", "batter_bats"])[
        ["pas", "changes", "changes_to_L", "changes_to_R"]].sum()
    out = {"change_ratio": {
        "L": {**_ratio(r.loc[("L", "R")].changes, r.loc[("L", "R")].pas, r.loc[("L", "L")].changes, r.loc[("L", "L")].pas),
              "_note": "left-hander pitching: changes per PA with a right-handed batter due up over a left-handed one"},
        "R": {**_ratio(r.loc[("R", "L")].changes, r.loc[("R", "L")].pas, r.loc[("R", "R")].changes, r.loc[("R", "R")].pas),
              "_note": "right-hander pitching: changes per PA with a left-handed batter due up over a right-handed one"}}}
    sh = {}
    for bats in ("L", "R"):
        x = r.xs(bats, level="batter_bats")[["changes_to_L", "changes_to_R"]].sum()
        sh[bats] = (x.changes_to_L, x.changes_to_L + x.changes_to_R)
    d = sh["L"][0] / sh["L"][1] - sh["R"][0] / sh["R"][1]
    se = math.sqrt(sum((x / n) * (1 - x / n) / n for x, n in sh.values()))
    out["lhp_entry_diff"] = {"value": r4(d), "tol": r4(Z * se),
                             "_note": "left-handers' share of relief entries, left-handed batter due up minus right-handed"}
    p = pd.read_csv(AGG / "pinch_hit_by_hand.csv")
    p = p[(p.scope == "all") & p.pitcher_throws.isin(["L", "R"]) & p.replaced_bats.isin(["L", "R"])]
    same = p.pitcher_throws == p.replaced_bats
    cnt = {}
    for name, m in (("same", same), ("other", ~same)):
        q = p[m]
        cnt[name] = (q[q.ph_bats != "opportunity"].n.sum(), q[q.ph_bats == "opportunity"].n.sum())
    out["ph_ratio"] = {**_ratio(cnt["same"][0], cnt["same"][1], cnt["other"][0], cnt["other"][1]),
                       "_note": "pinch hitters per opportunity, batter due up of the pitcher's hand over the other hand"}
    p = pd.read_csv(AGG / "pinch_hit_by_hand.csv")
    k = p[(p.scope == "all") & p.pitcher_throws.isin(["L", "R"]) & p.ph_bats.isin(["L", "R", "S"])]
    a = k[(k.ph_bats == "S") | (k.ph_bats != k.pitcher_throws)].n.sum()
    out["ph_advantage_share"] = {"value": r4(a / k.n.sum()), "tol": r4(Z * math.sqrt((a / k.n.sum()) * (1 - a / k.n.sum()) / k.n.sum()))}
    return out


def main() -> None:
    tw = tier_weights()
    lhp = real_lhp(tw)
    block = {"_note": ("Phase 3 gate (handedness and platoon splits; plan approved 2026-10-08, plans/phase3_plan_2026-10-08.md). "
                       "Shares from rosters are unweighted (coverage approved as representative); rates from the play-by-play weight "
                       "the tiers by their number of teams (tier_weights_teams), the play-by-play sample being P4-heavy. lhp_by_tier and "
                       "bats_L_by_tier are the tier-gradient check: hands are drawn from talent and role or position only, so a failure "
                       "measures handedness valued beyond talent (owner rule: no tier term; a failing row becomes a watch item and a "
                       "Phase 9 requirement)."),
             "conf": "B", "src": SRC, "tier_weights_teams": tw,
             "lhp_share": {role: {"value": lhp[role]["d1"]["share"], "tol": r4(Z * lhp[role]["d1"]["se"])} for role in ("starter", "reliever")},
             "lhp_by_tier": {f"{t}|{role}": {"value": lhp[role]["by_tier"][t]["share"], "lo": lhp[role]["by_tier"][t]["lo"],
                                            "hi": lhp[role]["by_tier"][t]["hi"],
                                            "tol": r4((lhp[role]["by_tier"][t]["hi"] - lhp[role]["by_tier"][t]["lo"]) / 2),
                                            "pitchers": lhp[role]["by_tier"][t]["pitchers"]}
                             for t in TIERS for role in ("starter", "reliever")},
             **roster_rows(), "platoon": platoon_rows(tw), "usage": usage_rows()}
    text = BENCH.read_text()
    b = json.loads(text)
    old = b.get(KEY)
    if old is not None:
        raise SystemExit(f"{KEY} already in benchmarks.json: remove it by hand (recorded in benchmark_changes_phase3.json) before rewriting")
    body = dumps_compact(block, indent=2, level=1)
    i = text.rstrip().rfind("}")
    new_text = text[:i].rstrip() + f',\n  "{KEY}": {body}\n}}\n'
    json.loads(new_text)
    BENCH.write_text(new_text)
    log = D / "benchmark_changes_phase3.json"
    prior = json.loads(log.read_text()) if log.exists() else []
    log.write_text(json.dumps(prior + [{"path": KEY, "old": None, "new": block, "date": datetime.date.today().isoformat()}], indent=1, default=str) + "\n")
    print(json.dumps(block, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
