"""Derive Phase 1 benchmarks from the parsed WMT play-by-play and write them
into benchmarks.json, replacing only conf C / D entries.

Reads data/ncaa_2025/pbp/parsed/*, writes data/ncaa_2025/derived/*.json and
updates these benchmarks.json entries (old values are printed for the PR):
  league_totals_2025: hbp_pct, sf_per_team_game, sh_per_team_game, sb_success_rate,
                      era, fielding_pct, errors_per_team_game, pa_per_team_game, k_per_9
  pa_outcome_table_league_avg (whole block, incl. in-play out split)
  pitch_level_2023_2025.pitches_per_pa
  game_structure.extra_innings_freq, game_structure.run_rule_freq (new)
  base_running_2025 (new block): runner advancement by result and base-out state, SB attempt rate
Run: python3 scripts/build_pbp_benchmarks.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

P = Path("data/ncaa_2025/pbp/parsed")
D = Path("data/ncaa_2025/derived")
BENCH = Path("benchmarks.json")
TODAY = dt.date.today().isoformat()

HIT = ["1B", "2B", "3B", "HR"]
IN_PLAY_OUT = ["FO", "GO", "GIDP", "DP", "SF", "SH"]


def plain(o):
    """Normalize numpy scalars, NaN and non-string keys so the output is strict JSON."""
    import math
    if isinstance(o, dict):
        return {str(k): plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    if hasattr(o, "item"):
        o = o.item()
    if isinstance(o, float) and math.isnan(o):
        return None
    return o


def dumps_compact(obj, indent=2, level=0) -> str:
    """JSON with leaf dicts (all scalar values) and scalar lists on one line, like the Phase 0 file."""
    if level == 0:
        obj = plain(obj)
    pad = " " * (indent * level)
    pad_in = " " * (indent * (level + 1))
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        if all(not isinstance(v, (dict, list)) for v in obj.values()):
            return "{" + ", ".join(f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in obj.items()) + "}"
        items = [f"{pad_in}{json.dumps(k, ensure_ascii=False)}: {dumps_compact(v, indent, level + 1)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list):
        if all(not isinstance(v, (dict, list)) for v in obj):
            return json.dumps(obj, ensure_ascii=False)
        return "[\n" + ",\n".join(pad_in + dumps_compact(v, indent, level + 1) for v in obj) + "\n" + pad + "]"
    return json.dumps(obj, ensure_ascii=False)


def r(x, n=4):
    return None if x is None or pd.isna(x) else round(float(x), n)


def main() -> None:
    D.mkdir(parents=True, exist_ok=True)
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False)
    rev = pd.read_csv(P / "runner_events_2025.csv.gz", low_memory=False)
    gm = pd.read_csv(P / "games_2025.csv", low_memory=False)
    sched = pd.read_csv(P / "schedule_games_2025.csv") if (P / "schedule_games_2025.csv").exists() else None
    n_games, n_pa = len(gm), len(pa)
    tg = 2 * n_games  # team-games
    src = f"WMT stats API play-by-play, {n_games} D1 games / {n_pa} PA, 2025; data/ncaa_2025/pbp (fetched {TODAY})"

    # ---- tiers: WMT covers about a quarter of the D1 season and over-represents P4
    # programs, so sample rates are reweighted to the D1 tier mix (team counts per tier).
    teams = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv") if Path("data/ncaa_2025/pbp/teams_2025.csv").exists() else None
    if teams is not None:
        teams["tier"] = teams.tier.fillna("")
        tier_of = dict(zip(teams.ncaa_team_id, teams.tier))
        d1_share = teams[teams.tier != ""].tier.value_counts(normalize=True).to_dict()
    else:
        tier_of, d1_share = {}, {}
    TIERS = ("p4", "mid", "low")
    CELLS = [(t, o) for t in TIERS for o in TIERS]

    # True matchup mix of 2025 D1-vs-D1 team-games from the full-season scoreboard.
    # Low- and mid-tier teams enter the WMT sample mostly through games against P4
    # clients, so a per-tier rate from WMT is really "that tier facing P4 pitching";
    # weighting per (tier, opponent tier) cell by the true mix removes that bias.
    mix = {}
    if teams is not None and Path("data/ncaa_2025/scoreboard/games_2025.csv").exists():
        sb = pd.read_csv("data/ncaa_2025/scoreboard/games_2025.csv")
        sb = sb[(sb.state == "final") & sb.home_score.notna() & sb.away_score.notna()].drop_duplicates("url")
        tier_of_name = dict(zip(teams.team, teams.tier))
        cnt = Counter()
        for side, opp in (("home", "away"), ("away", "home")):
            for t, o in zip(sb[side].map(tier_of_name), sb[opp].map(tier_of_name)):
                if t and o and isinstance(t, str) and isinstance(o, str):
                    cnt[(t, o)] += 1
        tot_tg = sum(cnt.values())
        mix = {c: cnt[c] / tot_tg for c in CELLS}

    def reweight(by_cell: dict) -> float | None:
        """Matchup-mix-weighted mean of per-cell rates; None if a cell is missing."""
        if not mix or any(c not in by_cell or by_cell[c] is None for c in CELLS):
            return None
        return sum(mix[c] * by_cell[c] for c in CELLS)

    pa["bat_tier"] = pa.bat_team_id.map(tier_of).fillna("")
    pa["pit_tier"] = pa.pit_team_id.map(tier_of).fillna("")

    # ---- PA outcome table -------------------------------------------------
    res = pa.result.replace({"IBB": "BB", "CI": "HBP"})  # fold rarities into the nearest bucket
    counts = Counter(res)
    ip_out = sum(counts[k] for k in IN_PLAY_OUT)
    table = {
        "K": counts["K"], "BB": counts["BB"], "HBP": counts["HBP"], "1B": counts["1B"], "2B": counts["2B"],
        "3B": counts["3B"], "HR": counts["HR"], "SF": counts["SF"], "SH": counts["SH"],
        "IP_OUT": counts["FO"] + counts["GO"] + counts["GIDP"] + counts["DP"], "ROE": counts["ROE"], "FC": counts["FC"],
    }
    tot = sum(table.values())
    probs_raw = {k: round(v / tot, 4) for k, v in table.items()}
    # reweight: P(outcome) = sum_tier share_tier * P(outcome | batting team in tier)
    by_cell_tables = {}
    for cell in CELLS:
        sub = res[(pa.bat_tier == cell[0]) & (pa.pit_tier == cell[1])]
        if len(sub):
            c = Counter(sub)
            tt = {"K": c["K"], "BB": c["BB"], "HBP": c["HBP"], "1B": c["1B"], "2B": c["2B"], "3B": c["3B"], "HR": c["HR"], "SF": c["SF"], "SH": c["SH"],
                  "IP_OUT": c["FO"] + c["GO"] + c["GIDP"] + c["DP"], "ROE": c["ROE"], "FC": c["FC"]}
            n_c = sum(tt.values())
            by_cell_tables[cell] = {k: v / n_c for k, v in tt.items()}
            by_cell_tables[cell]["_n_pa"] = n_c
    if mix and all(c in by_cell_tables for c in CELLS):
        probs = {k: sum(mix[c] * by_cell_tables[c][k] for c in CELLS) for k in table}
        norm = sum(probs.values()); probs = {k: round(v / norm, 4) for k, v in probs.items()}
        table = {k: probs[k] * tot for k in table}  # matchup-weighted pseudo-counts for the derived line
        weighting = "reweighted by batting-tier x pitching-tier cell to the full-season D1 matchup mix"
    else:
        probs, weighting = probs_raw, "raw sample"
    ab = tot - table["BB"] - table["HBP"] - table["SF"] - table["SH"]
    h = sum(table[k] for k in HIT)
    tb = table["1B"] + 2 * table["2B"] + 3 * table["3B"] + 4 * table["HR"]
    outs = pa[pa.result.isin(IN_PLAY_OUT)]
    # state dependence the single table cannot carry: SF needs a runner on 3rd with <2 outs,
    # SH and FC need runners on; the engine subtypes the in-play class by state using these
    runners_on = (pa.on1 + pa.on2 + pa.on3) > 0
    state_dep = {
        "fc_rate_runners_on": round((pa.result[runners_on] == "FC").mean(), 4), "fc_rate_bases_empty": round((pa.result[~runners_on] == "FC").mean(), 4),
        "roe_rate_runners_on": round((pa.result[runners_on] == "ROE").mean(), 4), "roe_rate_bases_empty": round((pa.result[~runners_on] == "ROE").mean(), 4),
        "sf_rate_on3_lt2": round((pa.result[(pa.on3 == 1) & (pa.outs < 2)] == "SF").mean(), 4),
        "sh_rate_runners_on_lt2": round((pa.result[runners_on & (pa.outs < 2)] == "SH").mean(), 4),
        "share_pa_runners_on": round(runners_on.mean(), 4),
    }
    split = Counter(outs.bb_type.fillna(""))
    split_tot = sum(v for k, v in split.items() if k)
    out_split = {k: round(split[k] / split_tot, 4) for k in ("GB", "FB", "LD", "PU")}
    hits_bb = Counter(pa[pa.result.isin(HIT)].bb_type.fillna(""))
    derived = {
        "ab_share_of_pa": round(ab / tot, 4), "h_per_pa": round(h / tot, 4),
        "ba": round(h / ab, 4), "obp": round((h + table["BB"] + table["HBP"]) / (ab + table["BB"] + table["HBP"] + table["SF"]), 4),
        "slg": round(tb / ab, 4), "babip": round((h - table["HR"]) / (ab - table["K"] - table["HR"] + table["SF"]), 4),
        "hit_mix": {k: round(table[k] / h, 4) for k in HIT},
        "in_play_out_split": {**out_split, "n": split_tot, "conf": "B", "note": "GB/FB/LD/PU among batter outs on balls in play incl. SF/SH/GIDP/DP; from play text"},
        "k_looking_share": round(pa[pa.result == "K"].k_looking.mean(), 4),
        "gidp_share_of_gb_outs": round(counts["GIDP"] / max(1, split["GB"]), 4),
        "bunt_share_of_in_play": round(pa[pa.result.isin(IN_PLAY_OUT + HIT + ["ROE", "FC"])].bunt.mean(), 4),
        "state_dependence": state_dep,
    }
    derived["by_matchup_cell"] = {f"{t}_vs_{o}": {k: round(v, 4) for k, v in d.items()} for (t, o), d in by_cell_tables.items()}
    derived["matchup_mix_weights"] = {f"{t}_vs_{o}": round(w, 4) for (t, o), w in mix.items()}
    derived["raw_sample_probs"] = probs_raw
    outcome_block = {"_note": f"Per plate appearance, {src}, {weighting}. ROE = reached on error, FC = reached on fielder's choice (batter safe, not a hit); FC, SF and SH depend on the base-out state, see _derived.state_dependence. WMT covers about a quarter of the 2025 D1 season and over-represents P4 programs; see PHASE0_NOTES.md.",
                     **probs, "_derived": derived, "_n_pa": tot, "conf": "B"}

    # ---- pitches per PA ----------------------------------------------------
    pp = pa.pitches.dropna()
    fps = pa.pitch_seq.dropna().astype(str)
    first_strike = (~fps.str.startswith("B")).mean()
    pitch_block = {"pitches_per_pa": {"value": round(pp.mean(), 3), "tol": 0.10, "conf": "B", "src": src, "n_pa": int(len(pp)),
                                      "dist": {str(k): round(v / len(pp), 4) for k, v in sorted(Counter(pp.astype(int).clip(upper=10)).items())}},
                   "first_pitch_strike_pct_pbp": {"value": round(first_strike, 4), "n_pa": int(len(fps)), "conf": "B", "note": "cross-check of the Trackman value; first pitch not a called ball"}}

    # ---- team-level rates from box totals ----------------------------------
    # League-wide when the full-season schedule table exists (every D1 vs D1 game
    # with both box lines), else the PBP sample.
    if sched is not None:
        box = sched[(sched.home_is_d1 == 1) & (sched.away_is_d1 == 1) & (sched.home_has_box == 1) & (sched.away_has_box == 1)
                    & (sched.canceled == 0) & (sched.exhibition == 0) & sched.home_score.notna() & sched.away_score.notna()].copy()
        box_src = f"WMT stats API box totals, {len(box)} 2025 D1-vs-D1 games (about a quarter of the season), reweighted by tier x opponent-tier cell to the full-season matchup mix; data/ncaa_2025/pbp/schedules (fetched {TODAY})"
    else:
        box, box_src = gm, src + "; box totals"
    tg = 2 * len(box)

    def both(col):
        return box[f"home_{col}"].fillna(0).sum() + box[f"away_{col}"].fillna(0).sum()
    PA_box, HBP_box = both("pa"), both("hbp")
    SF_box, SH_box, SB, CS = both("sf"), both("sh"), both("sb"), both("cs")
    E, PO, A = both("e"), both("po"), both("a")
    ER, IP_raw, K_p = both("er"), gm[["home_ip", "away_ip"]].fillna(0), both("k_pitched")
    # innings pitched come as x.1 / x.2 thirds
    def ip_to_innings(s):
        whole = s.astype(float).apply(lambda v: int(v))
        frac = (s.astype(float) - whole).round(1)
        return (whole + frac * 10 / 3).sum()
    IP = ip_to_innings(box.home_ip.fillna(0)) + ip_to_innings(box.away_ip.fillna(0))
    sb_att = rev[rev.event.isin(["SB", "CS"])]
    AB, H, D2, D3, HR, BB, K_h, R = both("ab"), both("h"), both("2b"), both("3b"), both("hr"), both("bb"), both("k"), both("r")

    # one long table of team-games so rates can be computed per tier and reweighted
    cols = ["pa", "hbp", "sf", "sh", "sb", "cs", "e", "po", "a", "er", "ip", "k_pitched", "ab", "h", "2b", "3b", "hr", "bb", "k", "r", "go", "fo"]
    parts = []
    for side, opp in (("home", "away"), ("away", "home")):
        d = box[[f"{side}_{c}" for c in cols]].rename(columns=lambda c: c.split("_", 1)[1])
        d["tier"] = box[f"{side}_team_id"].map(tier_of).fillna("").values
        d["opp"] = box[f"{opp}_team_id"].map(tier_of).fillna("").values
        parts.append(d)
    long = pd.concat(parts, ignore_index=True)
    long["ip_inn"] = long.ip.fillna(0).astype(float).apply(lambda v: int(v) + round(v - int(v), 1) * 10 / 3)

    def rates(df):
        n = len(df); S = df.sum(numeric_only=True)
        if n == 0 or S.pa == 0:
            return None
        return {"hbp_pct": S.hbp / S.pa, "sf_per_team_game": S.sf / n, "sh_per_team_game": S.sh / n,
                "sb_success_rate": S.sb / max(1, S.sb + S.cs), "era": 9 * S.er / S.ip_inn, "fielding_pct": (S.po + S.a) / (S.po + S.a + S.e),
                "errors_per_team_game": S.e / n, "pa_per_team_game": S.pa / n, "k_per_9": 9 * S.k_pitched / S.ip_inn,
                "sb_attempts_per_team_game": (S.sb + S.cs) / n, "runs_per_team_game": S.r / n, "hr_per_team_game": S.hr / n,
                "sb_per_team_game": S.sb / n, "ba": S.h / S.ab, "obp": (S.h + S.bb + S.hbp) / (S.ab + S.bb + S.hbp + S.sf),
                "slg": ((S.h - S["2b"] - S["3b"] - S.hr) + 2 * S["2b"] + 3 * S["3b"] + 4 * S.hr) / S.ab, "bb_pct": S.bb / S.pa, "k_pct": S.k / S.pa,
                "go_fo_ratio_batting": S.go / max(1, S.fo), "n_team_games": n}
    raw_rates = rates(long)
    tier_rates = {t: rates(long[long.tier == t]) for t in TIERS}
    cell_rates = {c: rates(long[(long.tier == c[0]) & (long.opp == c[1])]) for c in CELLS}
    rw = {k: reweight({c: (cell_rates[c] or {}).get(k) for c in CELLS}) for k in raw_rates if k != "n_team_games"}
    use = {k: (rw[k] if rw[k] is not None else raw_rates[k]) for k in rw}
    TOL = {"hbp_pct": 0.004, "sf_per_team_game": 0.08, "sh_per_team_game": 0.05, "sb_success_rate": 0.03, "era": 0.3,
           "fielding_pct": 0.004, "errors_per_team_game": 0.15, "pa_per_team_game": 1.0, "k_per_9": 0.4}
    ND = {"hbp_pct": 4, "fielding_pct": 4, "era": 2, "k_per_9": 2, "pa_per_team_game": 2}
    team_rates = {k: {"value": round(use[k], ND.get(k, 3)), **({"tol": TOL[k]} if k in TOL else {}), "conf": "B", "src": box_src,
                      "raw_sample": round(raw_rates[k], ND.get(k, 3)), "by_tier_in_sample": {t: round(tier_rates[t][k], ND.get(k, 3)) for t in TIERS if tier_rates[t]}}
                  for k in ("hbp_pct", "sf_per_team_game", "sh_per_team_game", "sb_success_rate", "era", "fielding_pct",
                            "errors_per_team_game", "pa_per_team_game", "k_per_9", "sb_attempts_per_team_game")}
    team_rates["sb_success_rate"]["src"] += f"; {int(SB)} SB / {int(CS)} CS in the sample"
    # Team-weighted season line from the same box totals: a cross-check of the conf B
    # FanGraphs conference means. Written as its own block; conf B values are not touched.
    keys_x = ["ba", "obp", "slg", "bb_pct", "k_pct", "hbp_pct", "runs_per_team_game", "hr_per_team_game", "sb_per_team_game", "sh_per_team_game", "sf_per_team_game", "pa_per_team_game", "go_fo_ratio_batting"]
    cross = {
        "_note": box_src + ". Cross-check of league_totals_2025 conf B values (unweighted conference means) and of the scoreboard R/G; not used to change any conf A/B value. 'raw' is the WMT sample as is; 'reweighted' weights each tier x opponent-tier cell by its share of all 2025 D1-vs-D1 team-games (scoreboard). Validation: reweighted R/G should sit near the scoreboard's 6.78 for D1-vs-D1 games.",
        "conf": "B", "n_games": int(len(box)), "n_team_games": int(tg), "matchup_mix_weights": {f"{t}_vs_{o}": round(w, 4) for (t, o), w in mix.items()},
        "reweighted": {k: round(use[k], 4) for k in keys_x}, "raw": {k: round(raw_rates[k], 4) for k in keys_x},
        "by_tier_in_sample": {t: {k: round(tier_rates[t][k], 4) for k in keys_x + ["n_team_games"]} for t in TIERS if tier_rates[t]},
        "by_cell": {f"{t}_vs_{o}": {k: round(cell_rates[(t, o)][k], 4) for k in keys_x + ["n_team_games"]} for (t, o) in CELLS if cell_rates[(t, o)]},
        "reweighted_r_g_by_tier": {t: round(sum(mix[(t, o)] * cell_rates[(t, o)]["runs_per_team_game"] for o in TIERS) / sum(mix[(t, o)] for o in TIERS), 3) for t in TIERS} if mix else {},
    }

    # ---- game structure ------------------------------------------------------
    gs = sched if sched is not None else gm
    fin = gs[gs.innings.notna() & (gs.innings > 0)]
    margin = (fin.home_score - fin.away_score).abs()
    big = fin[margin >= 10]
    p_early_given_big = ((big.innings < 9)).mean() if len(big) else None
    # full-season share of 10+ margin games from the scoreboard histogram block written by build_run_histogram.py
    b0 = json.loads(BENCH.read_text())
    p_big_season = b0["game_structure"]["run_distribution_per_team_game"].get("share_games_margin_10plus")
    game_block = {
        "extra_innings_freq": {"value": round((fin.innings > 9).mean(), 4), "tol": 0.015, "n_games": int(len(fin)), "conf": "B",
                               "src": f"WMT schedules, {len(fin)} 2025 D1 games with innings recorded (about a quarter of the season); data/ncaa_2025/pbp/schedules"},
        "run_rule_freq": {"value": round(p_big_season * p_early_given_big, 4) if p_big_season and p_early_given_big is not None else round(((fin.innings < 9) & (margin >= 10)).mean(), 4),
                          "conf": "B",
                          "note": "P(run rule) = P(final margin >= 10, all 8,079 scoreboard games) x P(game ended before the 9th | margin >= 10, WMT sample). Scheduled 7-inning doubleheaders that also reach a 10-run margin are counted.",
                          "p_margin_10plus_season": p_big_season, "p_ended_early_given_margin_10plus_wmt": round(p_early_given_big, 4) if p_early_given_big is not None else None,
                          "wmt_sample_run_rule_freq": round(((fin.innings < 9) & (margin >= 10)).mean(), 4),
                          "short_game_not_run_rule_freq": round(((fin.innings < 9) & (margin < 10)).mean(), 4),
                          "innings_dist": {str(int(k)): round(v / len(fin), 4) for k, v in sorted(Counter(fin.innings.astype(int)).items())}},
    }

    # ---- runner advancement -------------------------------------------------
    adv = defaultdict(lambda: defaultdict(Counter))  # result -> (outs, from_base) -> to
    adv_state = defaultdict(lambda: defaultdict(Counter))  # result -> (outs, on1on2on3) -> tuple of destinations
    for row in pa.itertuples(index=False):
        res_ = row.result if row.result not in ("IBB",) else "BB"
        state = f"{row.outs}_{row.on1}{row.on2}{row.on3}"
        dests = []
        for b, v in ((1, row.r1_to), (2, row.r2_to), (3, row.r3_to)):
            if v == "" or pd.isna(v):
                continue
            to = int(float(v)); adv[res_][(row.outs, b)][to] += 1; dests.append(f"{b}>{to}")
        bt = row.batter_to
        if not pd.isna(bt):
            dests.append(f"B>{int(float(bt))}")
        adv_state[res_][state][";".join(dests)] += 1
    runner_adv = {}
    for res_, d in adv.items():
        runner_adv[res_] = {}
        for (o, b), c in sorted(d.items()):
            n = sum(c.values())
            runner_adv[res_][f"outs{o}_from{b}"] = {"n": n, **{("out" if k == 0 else f"to{k}"): round(v / n, 3) for k, v in sorted(c.items())}}
    # compact benchmark view: by result and from-base, pooled over outs
    pooled = {}
    for res_, d in adv.items():
        pooled[res_] = {}
        for b in (1, 2, 3):
            c = Counter()
            for (o, bb), cc in d.items():
                if bb == b:
                    c.update(cc)
            n = sum(c.values())
            if n:
                pooled[res_][f"from{b}"] = {"n": n, "out": round(c[0] / n, 3), "scored": round(c[4] / n, 3),
                                           **{f"to{k}": round(c[k] / n, 3) for k in (1, 2, 3) if c[k]}}
    # steal attempts: per opportunity (PA with runner on 1st and 2nd base open, etc.) -- simple version: attempts per PA with a runner on
    opp = pa[(pa.on1 == 1) | (pa.on2 == 1)]
    base_running = {
        "_note": f"{src}. Runner destinations by batter result and starting base, pooled over outs; the full table by outs and base state is data/ncaa_2025/derived/runner_advancement_2025.json. Advancement rates vary little by tier, so these are raw sample values.",
        "conf": "B",
        "advancement_by_result": pooled,
        "sb_attempt_rate_per_runner_on_1b_or_2b_pa": round(len(sb_att) / max(1, len(opp)), 4),
        "sb_success_rate_pbp": round((sb_att.event == "SB").mean(), 3),
        "sb_target_base_share": {k: round(v / len(sb_att), 3) for k, v in Counter(sb_att.to_base.fillna(0).astype(int)).items()},
        "wp_pb_per_game": round(len(rev[rev.event.isin(["WP", "PB"])]) / n_games, 3),
        "pickoffs_per_game": round(len(rev[rev.event == "PO"]) / n_games, 3),
    }
    json.dump({"by_result_outs_base": runner_adv, "by_result_state": {res_: {s: dict(c.most_common(12)) for s, c in d.items()} for res_, d in adv_state.items()},
               "n_pa": n_pa, "n_games": n_games, "src": src}, (D / "runner_advancement_2025.json").open("w"), indent=1)

    # ---- Phase 1 gate: runs per half-inning, big innings, PA per half-inning ---------
    # Half-innings from the play-by-play, reweighted by batting-tier x pitching-tier cell.
    # Tolerances are 3 standard errors using the effective sample size after reweighting.
    key = ["game_id", "inning", "half"]
    hi = pa.groupby(key).agg(runs_pa=("runs_on_play", "sum"), n_pa=("result", "size"), bt=("bat_tier", "first"), pt=("pit_tier", "first")).reset_index()
    rr = rev[rev.to_base == 4].groupby(key).size().rename("runs_ev").reset_index()
    hi = hi.merge(rr, on=key, how="left"); hi["runs_ev"] = hi.runs_ev.fillna(0); hi["runs"] = hi.runs_pa + hi.runs_ev
    hi["cell"] = list(zip(hi.bt, hi.pt))
    ok_hi = hi[hi.cell.isin(mix)] if mix else hi
    n_hi = len(hi)
    import numpy as np
    def hbins(r):
        return np.bincount(np.clip(r, 0, 5).astype(int), minlength=6) / len(r)
    raw_bins = hbins(hi.runs.values)
    if mix:
        w_rows = ok_hi.cell.map({c: mix[c] / (len(ok_hi[ok_hi.cell == c]) / len(ok_hi)) for c in mix if len(ok_hi[ok_hi.cell == c])})
        n_eff = float(w_rows.sum() ** 2 / (w_rows ** 2).sum())
        rw_bins = np.zeros(6); rw_pa = 0.0
        for c, w in mix.items():
            sub = ok_hi[ok_hi.cell == c]
            if len(sub):
                rw_bins += w * hbins(sub.runs.values); rw_pa += w * sub.n_pa.mean()
        rw_bins = rw_bins / rw_bins.sum()
    else:
        n_eff, rw_bins, rw_pa = float(n_hi), raw_bins, hi.n_pa.mean()
    se = np.sqrt(rw_bins * (1 - rw_bins) / n_eff)
    big = float(rw_bins[3:].sum()); se_big = float(np.sqrt(big * (1 - big) / n_eff))
    se_pa = float(hi.n_pa.std() / np.sqrt(n_eff))
    half_inning = {
        "_note": f"Phase 1 gate. Runs per half-inning P(0)..P(4), P(5+), big-inning frequency (3+ runs) and PA per half-inning from {src}, reweighted by batting-tier x pitching-tier cell to the full-season matchup mix. Tolerances are 3 SE at the effective sample size after reweighting ({int(n_eff)} of {n_hi} half-innings). Partial half-innings (walk-offs, run-rule endings) are included as played, as the engine counts them.",
        "conf": "A", "src": src, "n_half_innings": int(n_hi), "n_effective": int(n_eff), "half_innings_per_game": round(n_hi / n_games, 3),
        "bins": [round(float(x), 4) for x in rw_bins], "bin_tol": [round(float(max(3 * x, 0.002)), 4) for x in se],
        "bins_raw_sample": [round(float(x), 4) for x in raw_bins],
        "big_inning_freq": {"value": round(big, 4), "tol": round(max(3 * se_big, 0.002), 4), "conf": "A", "note": "P(3+ runs in a half-inning)"},
        "pa_per_half_inning": {"value": round(float(rw_pa), 3), "tol": round(max(3 * se_pa, 0.01), 3), "conf": "A"},
        "mean_runs_per_half_inning": round(float(sum(i * b for i, b in enumerate(rw_bins[:5])) + 5 * rw_bins[5]), 4),
    }

    # ---- walk-rate resolution (user decision 2026-10-01) -----------------------------
    # WMT box totals agree with FanGraphs conference by conference; the league gap is
    # weighting. The team-weighted all-D1 estimate is the matchup-reweighted WMT value.
    bb_res = {"value": round(use["bb_pct"], 4), "tol": 0.005, "conf": "B",
              "src": box_src + "; team-weighted, matchup-reweighted. Replaces the FanGraphs unweighted conference mean (.1137): WMT and FanGraphs agree conference by conference (SEC .121/.121, ACC .116/.121, Big Ten .114/.117, Big 12 .114/.113, Mountain West .095/.095), so the difference is that P4 conferences walk the most and are a fifth of D1 teams.",
              "raw_sample": round(raw_rates["bb_pct"], 4), "by_tier_in_sample": {t: round(tier_rates[t]["bb_pct"], 4) for t in TIERS if tier_rates[t]},
              "fangraphs_conf_mean": 0.1137, "sidearm_13_team_full_season": {"totals": 0.1153, "opponents": 0.1062, "both": 0.1108}}

    # ---- OBP resolution (project owner decision on PR #4, 2026-10-01) ---------------------
    # Same weighting error as the walk rate: the FanGraphs .385 is an unweighted mean of
    # conference values. Team-weighted, matchup-reweighted WMT box value, same method as BB/PA.
    obp_res = {"value": round(use["obp"], 4), "tol": 0.005, "conf": "B",
               "src": box_src + "; team-weighted, matchup-reweighted, same method as bb_pct. Replaces the FanGraphs unweighted conference mean (.385), which weights each conference "
                                "equally and so over-weights the P4 conferences that walk and reach base most.",
               "raw_sample": round(raw_rates["obp"], 4), "by_tier_in_sample": {t: round(tier_rates[t]["obp"], 4) for t in TIERS if tier_rates[t]},
               "fangraphs_conf_mean": 0.385}

    # per-tier composition and per-tier rates for the notes
    comp = pa.bat_tier.replace("", "unknown").value_counts(normalize=True).round(3).to_dict()
    summary = {"n_games": n_games, "n_pa": n_pa, "pa_by_batting_team_tier": comp, "outcome_table": outcome_block, "team_weighted_cross_check": cross, "half_inning": half_inning, "bb_pct_resolution": bb_res, "obp_resolution": obp_res,
               "team_rates": team_rates, "pitches": pitch_block, "game_structure": game_block, "base_running": base_running}
    json.dump(summary, (D / "pbp_benchmarks_2025.json").open("w"), indent=1)

    # ---- write into benchmarks.json (targeted edits, old values recorded) -------
    b = json.loads(BENCH.read_text())
    changes = []
    def setv(path, new):
        cur = b
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        old = cur.get(path[-1])
        if isinstance(old, dict) and isinstance(new, dict):  # keep fields added later (e.g. the Phase 2 run-rule tolerance)
            new = {**{k: v for k, v in old.items() if k not in new and k in ("tol", "tol_note", "gate")}, **new}
        cur[path[-1]] = new
        if json.loads(json.dumps(old, default=str)) != json.loads(json.dumps(new, default=str)):
            changes.append({"path": ".".join(path), "old": old, "new": new})
    for k, v in team_rates.items():
        if k in b["league_totals_2025"] and b["league_totals_2025"][k].get("conf") in ("C", "D"):
            setv(["league_totals_2025", k], v)
        elif k not in b["league_totals_2025"]:
            setv(["league_totals_2025", k], v)
    setv(["pa_outcome_table_league_avg"], outcome_block)
    setv(["pitch_level_2023_2025", "pitches_per_pa"], pitch_block["pitches_per_pa"])
    setv(["pitch_level_2023_2025", "first_pitch_strike_pct_pbp"], pitch_block["first_pitch_strike_pct_pbp"])
    setv(["game_structure", "extra_innings_freq"], game_block["extra_innings_freq"])
    setv(["game_structure", "run_rule_freq"], game_block["run_rule_freq"])
    setv(["base_running_2025"], base_running)
    setv(["league_totals_2025_team_weighted_wmt"], cross)
    setv(["half_inning_2025"], half_inning)
    if b["league_totals_2025"]["bb_pct"].get("value") != bb_res["value"]:
        setv(["league_totals_2025", "bb_pct"], bb_res)
    if b["league_totals_2025"]["obp"].get("value") != obp_res["value"]:
        setv(["league_totals_2025", "obp"], obp_res)
    for path in (["game_structure", "run_distribution_per_team_game"], ["game_structure", "extra_innings_freq"], ["game_structure", "run_rule_freq"]):
        cur = b
        for k in path:
            cur = cur[k]
        cur.setdefault("gate", "phase2")  # later phases may move a row (see CLAUDE.md)
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:  # append to the change record; a rerun with nothing new leaves it as is
        log = D / "benchmark_changes.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        log.write_text(json.dumps(prior + [{**c, "date": dt.date.today().isoformat()} for c in changes], indent=1, default=str))
    print(json.dumps({"n_games": n_games, "n_pa": n_pa, "composition": comp}, indent=1))
    for c in changes:
        print(f"- {c['path']}: {json.dumps(c['old'], default=str)[:120]}  ->  {json.dumps(c['new'], default=str)[:160]}")


if __name__ == "__main__":
    main()
