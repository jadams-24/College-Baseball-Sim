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

    # ---- PA outcome table -------------------------------------------------
    res = pa.result.replace({"IBB": "BB", "CI": "HBP"})  # fold rarities into the nearest bucket
    counts = Counter(res)
    ip_out = sum(counts[k] for k in IN_PLAY_OUT)
    reach_other = counts["ROE"] + counts["FC"]
    table = {
        "K": counts["K"], "BB": counts["BB"], "HBP": counts["HBP"], "1B": counts["1B"], "2B": counts["2B"],
        "3B": counts["3B"], "HR": counts["HR"], "SF": counts["SF"], "SH": counts["SH"],
        "IP_OUT": counts["FO"] + counts["GO"] + counts["GIDP"] + counts["DP"], "ROE_FC": reach_other,
    }
    tot = sum(table.values())
    probs = {k: round(v / tot, 4) for k, v in table.items()}
    ab = tot - table["BB"] - table["HBP"] - table["SF"] - table["SH"]
    h = sum(table[k] for k in HIT)
    tb = table["1B"] + 2 * table["2B"] + 3 * table["3B"] + 4 * table["HR"]
    outs = pa[pa.result.isin(IN_PLAY_OUT)]
    split = Counter(outs.bb_type.fillna(""))
    split_tot = sum(v for k, v in split.items() if k)
    out_split = {k: round(split[k] / split_tot, 4) for k in ("GB", "FB", "LD", "PU")}
    hits_bb = Counter(pa[pa.result.isin(HIT)].bb_type.fillna(""))
    derived = {
        "ab_share_of_pa": round(ab / tot, 4), "h_per_pa": round(h / tot, 4),
        "ba": round(h / ab, 4), "obp": round((h + table["BB"] + table["HBP"]) / (ab + table["BB"] + table["HBP"] + table["SF"]), 4),
        "slg": round(tb / ab, 4), "babip": round((h - table["HR"]) / (ab - table["K"] - table["HR"] + table["SF"]), 4),
        "hit_mix": {k: round(table[k] / h, 4) for k in HIT},
        "in_play_out_split": {**out_split, "n": split_tot, "conf": "A", "note": "GB/FB/LD/PU among batter outs on balls in play incl. SF/SH/GIDP/DP; from play text"},
        "k_looking_share": round(pa[pa.result == "K"].k_looking.mean(), 4),
        "gidp_share_of_gb_outs": round(counts["GIDP"] / max(1, split["GB"]), 4),
        "bunt_share_of_in_play": round(pa[pa.result.isin(IN_PLAY_OUT + HIT + ["ROE", "FC"])].bunt.mean(), 4),
    }
    outcome_block = {"_note": f"Per plate appearance, {src}. ROE_FC = reached on error or fielder's choice (batter safe, not a hit). conf A for the sample; league-wide composition is the 40-program tier sample plus every opponent, see PHASE0_NOTES.md.",
                     **probs, "_derived": derived, "_n_pa": tot, "conf": "A"}

    # ---- pitches per PA ----------------------------------------------------
    pp = pa.pitches.dropna()
    fps = pa.pitch_seq.dropna().astype(str)
    first_strike = (~fps.str.startswith("B")).mean()
    pitch_block = {"pitches_per_pa": {"value": round(pp.mean(), 3), "tol": 0.10, "conf": "A", "src": src, "n_pa": int(len(pp)),
                                      "dist": {str(k): round(v / len(pp), 4) for k, v in sorted(Counter(pp.astype(int).clip(upper=10)).items())}},
                   "first_pitch_strike_pct_pbp": {"value": round(first_strike, 4), "n_pa": int(len(fps)), "conf": "A", "note": "cross-check of the Trackman value; first pitch not a called ball"}}

    # ---- team-level rates from box totals ----------------------------------
    # League-wide when the full-season schedule table exists (every D1 vs D1 game
    # with both box lines), else the PBP sample.
    if sched is not None:
        box = sched[(sched.home_is_d1 == 1) & (sched.away_is_d1 == 1) & (sched.home_has_box == 1) & (sched.away_has_box == 1)
                    & (sched.canceled == 0) & (sched.exhibition == 0) & sched.home_score.notna() & sched.away_score.notna()].copy()
        box_src = f"WMT stats API box totals for every 2025 D1-vs-D1 game with both box lines ({len(box)} games), team-weighted; data/ncaa_2025/pbp/schedules (fetched {TODAY})"
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
    team_rates = {
        "hbp_pct": {"value": round(HBP_box / PA_box, 4), "tol": 0.004, "conf": "A", "src": box_src},
        "sf_per_team_game": {"value": round(SF_box / tg, 3), "tol": 0.08, "conf": "A", "src": box_src},
        "sh_per_team_game": {"value": round(SH_box / tg, 3), "tol": 0.05, "conf": "A", "src": box_src},
        "sb_success_rate": {"value": round(SB / (SB + CS), 3), "tol": 0.03, "conf": "A", "src": box_src + f"; {int(SB)} SB / {int(CS)} CS"},
        "era": {"value": round(9 * ER / IP, 2), "tol": 0.3, "conf": "A", "src": box_src},
        "fielding_pct": {"value": round((PO + A) / (PO + A + E), 4), "tol": 0.004, "conf": "A", "src": box_src},
        "errors_per_team_game": {"value": round(E / tg, 3), "tol": 0.15, "conf": "A", "src": box_src},
        "pa_per_team_game": {"value": round(PA_box / tg, 2), "tol": 1.0, "conf": "A", "src": box_src},
        "k_per_9": {"value": round(9 * K_p / IP, 2), "tol": 0.4, "conf": "A", "src": box_src},
        "sb_attempts_per_team_game": {"value": round((SB + CS) / tg, 3), "conf": "A", "src": box_src},
    }
    # Team-weighted season line from the same box totals: a cross-check of the conf B
    # FanGraphs conference means. Written as its own block; conf B values are not touched.
    TB = (H - D2 - D3 - HR) + 2 * D2 + 3 * D3 + 4 * HR
    cross = {
        "_note": box_src + ". Cross-check of league_totals_2025 conf B values, which are unweighted conference means; these are team-game weighted.",
        "conf": "A", "n_games": int(len(box)), "n_team_games": int(tg),
        "ba": round(H / AB, 4), "obp": round((H + BB + HBP_box) / (AB + BB + HBP_box + SF_box), 4), "slg": round(TB / AB, 4),
        "bb_pct": round(BB / PA_box, 4), "k_pct": round(K_h / PA_box, 4), "hbp_pct": round(HBP_box / PA_box, 4),
        "runs_per_team_game": round(R / tg, 3), "hr_per_team_game": round(HR / tg, 3), "sb_per_team_game": round(SB / tg, 3),
        "sh_per_team_game": round(SH_box / tg, 3), "sf_per_team_game": round(SF_box / tg, 3), "pa_per_team_game": round(PA_box / tg, 2),
        "babip": round((H - HR) / (AB - K_h - HR + SF_box), 4),
        "go_fo_ratio_batting": round(both("go") / max(1, both("fo")), 3),
    }

    # ---- game structure ------------------------------------------------------
    gs = sched if sched is not None else gm
    fin = gs[gs.innings.notna() & (gs.innings > 0)]
    margin = (fin.home_score - fin.away_score).abs()
    game_block = {
        "extra_innings_freq": {"value": round((fin.innings > 9).mean(), 4), "n_games": int(len(fin)), "conf": "A",
                               "src": ("WMT schedules for all screened programs" if sched is not None else src)},
        "run_rule_freq": {"value": round(((fin.innings < 9) & (margin >= 10)).mean(), 4), "conf": "A",
                          "note": "games ending before the 9th with a margin of 10+; scheduled 7-inning doubleheaders that also reach 10+ are counted",
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
        "_note": f"{src}. Runner destinations by batter result and starting base, pooled over outs; the full table by outs and base state is data/ncaa_2025/derived/runner_advancement_2025.json.",
        "conf": "A",
        "advancement_by_result": pooled,
        "sb_attempt_rate_per_runner_on_1b_or_2b_pa": round(len(sb_att) / max(1, len(opp)), 4),
        "sb_success_rate_pbp": round((sb_att.event == "SB").mean(), 3),
        "sb_target_base_share": {k: round(v / len(sb_att), 3) for k, v in Counter(sb_att.to_base.fillna(0).astype(int)).items()},
        "wp_pb_per_game": round(len(rev[rev.event.isin(["WP", "PB"])]) / n_games, 3),
        "pickoffs_per_game": round(len(rev[rev.event == "PO"]) / n_games, 3),
    }
    json.dump({"by_result_outs_base": runner_adv, "by_result_state": {res_: {s: dict(c.most_common(12)) for s, c in d.items()} for res_, d in adv_state.items()},
               "n_pa": n_pa, "n_games": n_games, "src": src}, (D / "runner_advancement_2025.json").open("w"), indent=1)

    # per-tier composition and per-tier rates for the notes
    sel = pd.read_csv("data/ncaa_2025/pbp/programs_selected.csv")
    tier_of = dict(zip(sel.ncaa_team_id, sel.tier))
    pa["bat_tier"] = pa.bat_team_id.map(tier_of).fillna("opponent")
    comp = pa.bat_tier.value_counts(normalize=True).round(3).to_dict()
    summary = {"n_games": n_games, "n_pa": n_pa, "pa_by_batting_team_tier": comp, "outcome_table": outcome_block, "team_weighted_cross_check": cross,
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
        cur[path[-1]] = new
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
    BENCH.write_text(dumps_compact(b) + "\n")
    json.dump(changes, (D / "benchmark_changes.json").open("w"), indent=1, default=str)
    print(json.dumps({"n_games": n_games, "n_pa": n_pa, "composition": comp}, indent=1))
    for c in changes:
        print(f"- {c['path']}: {json.dumps(c['old'], default=str)[:120]}  ->  {json.dumps(c['new'], default=str)[:160]}")


if __name__ == "__main__":
    main()
