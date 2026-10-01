"""Phase 2 metrics per simulated season, aggregation across seasons, and the realism report."""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path

import numpy as np

from config.phase2 import LEADERBOARD_MIN_IP, QUAL_GAMES_SHARE, QUAL_IP_PER_TEAM_GAME, QUAL_PA_PER_TEAM_GAME
from engine.game2 import (B_2B, B_3B, B_AB, B_BB, B_G, B_H, B_HBP, B_HR, B_K, B_PA, B_SF, P_BF, P_ER, P_K, P_OUTS)

ROOT = Path(__file__).resolve().parents[1]
TIERS = ("p4", "mid", "low")
QS = (10, 25, 50, 75, 90)


def season_metrics(res: dict) -> dict:
    lg, b, p, tg, games = res["league"], res["bstats"], res["pstats"], res["team_game_rows"], res["games"]
    tier = {t.tid: t.tier for t in lg.teams}
    m = {}
    pa, ab, h, d2, d3, hr, bb, hbp, k, sf = (b[:, i].sum() for i in (B_PA, B_AB, B_H, B_2B, B_3B, B_HR, B_BB, B_HBP, B_K, B_SF))
    ntg = len(tg)
    tb = h + d2 + 2 * d3 + 3 * hr
    m["league"] = {"runs_per_team_game": tg[:, 1].mean(), "ba": h / ab, "obp": (h + bb + hbp) / (ab + bb + hbp + sf), "slg": tb / ab,
                   "hr_per_team_game": hr / ntg, "bb_pct": bb / pa, "k_pct": k / pa, "hbp_pct": hbp / pa, "pa_per_team_game": pa / ntg,
                   "errors_per_team_game": tg[:, 8].mean(), "era": 27 * p[:, P_ER].sum() / p[:, P_OUTS].sum(), "earned_share": p[:, P_ER].sum() / max(1, p[:, 9].sum())}
    runs = tg[:, 1].astype(int)
    hist = Counter(np.minimum(runs, 15))
    m["run_histogram"] = [hist[i] / ntg for i in range(16)]
    m["extra_innings_freq"] = float(np.mean([g[4] > 9 for g in games]))
    m["run_rule_freq"] = float(np.mean([g[5] for g in games]))
    m["margin_10plus"] = float(np.mean([abs(g[2] - g[3]) >= 10 for g in games]))
    m["runs_sd"] = float(runs.std())
    m["home_win_pct"] = float(np.mean([g[2] > g[3] for g in games]))
    hv = res["half_innings"]
    hh = Counter(min(x[2], 5) for x in hv)
    m["half_inning_run_dist"] = [hh[i] / len(hv) for i in range(6)]
    m["big_inning_freq"] = float(np.mean([x[2] >= 3 for x in hv]))
    m["pa_per_half_inning"] = float(np.mean([x[3] for x in hv]))
    # team season lines
    tids = tg[:, 0].astype(int)
    team = {}
    for t in np.unique(tids):
        r = tg[tids == t]
        team[t] = {"g": len(r), "rg": r[:, 1].mean(), "rag": r[:, 2].mean(), "ba": r[:, 3].sum() / r[:, 4].sum(), "hr_g": r[:, 5].mean(),
                   "era": 27 * r[:, 6].sum() / r[:, 7].sum(), "tier": tier[t]}
    def spread(rows):
        rg = np.array([x["rg"] for x in rows]); ra = np.array([x["rag"] for x in rows])
        return {"r_per_game": {"mean": rg.mean(), "sd": rg.std(ddof=1)}, "ra_per_game": {"mean": ra.mean(), "sd": ra.std(ddof=1)}}
    m["team_strength"] = {"all": spread(list(team.values())), "by_tier": {tr: spread([x for x in team.values() if x["tier"] == tr]) for tr in TIERS}}
    # qualified players
    team_g = res["team_games"]
    pl = lg.players
    bt = np.array([team_g[x.team] for x in pl])
    q = (b[:, B_PA] >= QUAL_PA_PER_TEAM_GAME * bt) & (b[:, B_G] >= QUAL_GAMES_SHARE * bt)
    qb = b[q]
    with np.errstate(divide="ignore", invalid="ignore"):
        BA = qb[:, B_H] / qb[:, B_AB]
        OBP = (qb[:, B_H] + qb[:, B_BB] + qb[:, B_HBP]) / (qb[:, B_AB] + qb[:, B_BB] + qb[:, B_HBP] + qb[:, B_SF])
        ISO = (qb[:, B_2B] + 2 * qb[:, B_3B] + 3 * qb[:, B_HR]) / qb[:, B_AB]
        Kp, BBp = qb[:, B_K] / qb[:, B_PA], qb[:, B_BB] / qb[:, B_PA]
        ip = p[:, P_OUTS] / 3
        qp = ip >= QUAL_IP_PER_TEAM_GAME * bt
        ERA, K9 = 9 * p[qp, P_ER] / ip[qp], 9 * p[qp, P_K] / ip[qp]
    pct = lambda v: {f"p{qq}": float(np.percentile(v, qq)) for qq in QS}
    m["qualified"] = {"batters": {"n": int(q.sum()), "per_team": q.sum() / len(lg.teams), "BA": pct(BA), "OBP": pct(OBP), "ISO": pct(ISO), "K_pct": pct(Kp), "BB_pct": pct(BBp)},
                      "pitchers": {"n": int(qp.sum()), "per_team": qp.sum() / len(lg.teams), "ERA": pct(ERA), "K9": pct(K9)}}
    p50 = ip >= LEADERBOARD_MIN_IP
    era50 = 9 * p[p50, P_ER] / ip[p50]
    tv = list(team.values())
    m["leaderboards"] = {"pitchers_50ip": int(p50.sum()), "pitchers_50ip_era_under_2": int((era50 < 2).sum()), "pitchers_50ip_era_under_3": int((era50 < 3).sum()),
                         "teams_era_under_4": int(sum(x["era"] < 4 for x in tv)), "best_team_era": min(x["era"] for x in tv),
                         "team_ba_max": max(x["ba"] for x in tv), "team_hr_per_game_max": max(x["hr_g"] for x in tv),
                         "individual_ba_top": float(np.nanmax(BA)), "individual_hr_top": int(b[:, B_HR].max())}
    m["usage"] = {"pitchers_per_team_game": float(p[:, 0].sum() / ntg)}
    return m


def aggregate(ms: list) -> dict:
    def avg(path):
        vals = []
        for m in ms:
            v = m
            for k in path:
                v = v[k]
            vals.append(v)
        return np.mean(vals, axis=0) if not isinstance(vals[0], (int, float, np.floating, np.integer)) else float(np.mean(vals))
    out = {"n_seasons": len(ms)}
    out["league"] = {k: avg(["league", k]) for k in ms[0]["league"]}
    for k in ("run_histogram", "half_inning_run_dist"):
        out[k] = [float(x) for x in avg([k])]
    for k in ("extra_innings_freq", "run_rule_freq", "margin_10plus", "runs_sd", "home_win_pct", "big_inning_freq", "pa_per_half_inning"):
        out[k] = avg([k])
    out["team_strength"] = {"all": {s: {q: avg(["team_strength", "all", s, q]) for q in ("mean", "sd")} for s in ("r_per_game", "ra_per_game")},
                            "by_tier": {t: {s: {q: avg(["team_strength", "by_tier", t, s, q]) for q in ("mean", "sd")} for s in ("r_per_game", "ra_per_game")} for t in TIERS}}
    out["qualified"] = {side: {k: (avg(["qualified", side, k]) if k in ("n", "per_team") else {pq: avg(["qualified", side, k, pq]) for pq in ms[0]["qualified"][side][k]})
                               for k in ms[0]["qualified"][side]} for side in ("batters", "pitchers")}
    lb = {}
    for k in ms[0]["leaderboards"]:
        v = np.array([m["leaderboards"][k] for m in ms], float)
        lb[k] = {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0, "min": float(v.min()), "max": float(v.max())}
    out["leaderboards"] = lb
    out["usage"] = {"pitchers_per_team_game": avg(["usage", "pitchers_per_team_game"])}
    return out


def build_report(agg: dict, seeds: list, bench: dict | None = None) -> tuple[str, dict]:
    b = bench or json.loads((ROOT / "benchmarks.json").read_text())
    st, rows = {}, []

    def row(section, label, got, val, tol, conf, key, gate=True, nd=4):
        ok = None if (val is None or tol is None) else bool(abs(got - val) <= tol)
        if gate:
            st[key] = ok
        rows.append((section, f"| {label} | {got:.{nd}f} | {'—' if val is None else f'{val:.{nd}f}'} | {'—' if tol is None else f'±{tol}'} | {conf} | {'yes' if gate else ''} | "
                              f"{'pass' if ok else ('FAIL' if ok is False else 'n/a')} |"))
    lt = b["league_totals_2025"]
    for key, label in (("runs_per_team_game", "Runs per team-game"), ("ba", "Batting average"), ("obp", "On-base pct"), ("slg", "Slugging pct"),
                       ("hr_per_team_game", "HR per team-game"), ("bb_pct", "BB per PA"), ("k_pct", "K per PA"), ("hbp_pct", "HBP per PA")):
        row("league", label, agg["league"][key], lt[key]["value"], lt[key]["tol"], lt[key]["conf"], f"league_{key}", gate=key in ("runs_per_team_game", "ba", "obp", "slg"))
    for key, label in (("errors_per_team_game", "Errors per team-game"), ("pa_per_team_game", "PA per team-game"), ("era", "ERA")):
        row("league", label, agg["league"][key], lt[key]["value"], lt[key]["tol"], lt[key]["conf"], f"league_{key}", gate=False)
    hb = b["half_inning_2025"]
    row("league", "Big-inning frequency (3+ runs)", agg["big_inning_freq"], hb["big_inning_freq"]["value"], hb["big_inning_freq"]["tol"], "A", "big_inning")
    row("league", "PA per half-inning", agg["pa_per_half_inning"], hb["pa_per_half_inning"]["value"], hb["pa_per_half_inning"]["tol"], "A", "pa_half", nd=3)
    half_ok = bool(all(abs(g - v) <= t for g, v, t in zip(agg["half_inning_run_dist"], hb["bins"], hb["bin_tol"])))
    st["half_inning_run_dist"] = half_ok
    gs = b["game_structure"]
    row("game", "Extra-innings frequency", agg["extra_innings_freq"], gs["extra_innings_freq"]["value"], gs["extra_innings_freq"]["tol"], gs["extra_innings_freq"]["conf"], "extra_innings")
    row("game", "Run-rule frequency", agg["run_rule_freq"], gs["run_rule_freq"]["value"], gs["run_rule_freq"].get("tol"), gs["run_rule_freq"]["conf"], "run_rule")
    row("game", "Games decided by 10+ runs", agg["margin_10plus"], gs["run_distribution_per_team_game"]["share_games_margin_10plus"], None, "A", "margin10", gate=False)
    row("game", "Runs per team-game SD", agg["runs_sd"], gs["run_distribution_per_team_game"]["sd_runs_per_team_game"], None, "A", "runs_sd", gate=False, nd=3)
    rb = gs["run_distribution_per_team_game"]
    tvd = sum(abs(g - v) for g, v in zip(agg["run_histogram"], rb["bins"])) / 2
    st["run_histogram"] = bool(all(abs(g - v) <= rb["tol_per_bin"] for g, v in zip(agg["run_histogram"], rb["bins"])) and tvd <= rb["tol_total_variation"])
    ts = b["team_strength_2025"]
    for scope, sim, real in [("all", agg["team_strength"]["all"], ts["all"])] + [(t, agg["team_strength"]["by_tier"][t], ts["by_tier"][t]) for t in TIERS]:
        for s, lab in (("r_per_game", "R/G"), ("ra_per_game", "RA/G")):
            row("team", f"Team {lab} mean ({scope})", sim[s]["mean"], real[s]["mean"], real[s]["mean_tol"], "A", f"team_{scope}_{s}_mean", nd=3)
            row("team", f"Team {lab} SD across teams ({scope})", sim[s]["sd"], real[s]["sd"], real[s]["sd_tol"], "A", f"team_{scope}_{s}_sd", nd=3)
    qp = b["qualified_players_2025"]
    for side, cols in (("batters", ("BA", "OBP", "ISO", "K_pct", "BB_pct")), ("pitchers", ("ERA", "K9"))):
        for c in cols:
            for pq in ("p10", "p50", "p90"):
                nd = 2 if c in ("ERA", "K9") else 4
                row("qualified", f"{c} {pq}", agg["qualified"][side][c][pq], qp[side][c][pq], qp[side][c]["tol"][pq], qp["conf"], f"q_{c}_{pq}", nd=nd)
    lbb = b["leaderboards_2025"]
    n = agg["n_seasons"]
    for k, lab in (("pitchers_50ip", "Pitchers with 50+ IP"), ("pitchers_50ip_era_under_2", "50+ IP pitchers with ERA < 2.00"), ("pitchers_50ip_era_under_3", "50+ IP pitchers with ERA < 3.00"),
                   ("teams_era_under_4", "Teams with ERA < 4.00"), ("best_team_era", "Best team ERA"), ("team_ba_max", "Best team BA"),
                   ("team_hr_per_game_max", "Most team HR per game"), ("individual_ba_top", "Top qualified BA"), ("individual_hr_top", "Most HR, individual")):
        s, real = agg["leaderboards"][k], lbb[k]["value"]
        half = 2 * s["sd"] * np.sqrt(1 + 1 / n)
        ok = None if real is None else bool(abs(real - s["mean"]) <= half)
        if real is not None:
            st[f"lb_{k}"] = ok
        nd = 3 if s["mean"] < 10 else 1
        rows.append(("leaders", f"| {lab} | {s['mean']:.{nd}f} (season range {s['min']:.{nd}f}–{s['max']:.{nd}f}) | {'—' if real is None else real} | ±{half:.{nd}f} | {lbb[k]['conf']} | {'yes' if real is not None else ''} | "
                                f"{'pass' if ok else ('FAIL' if ok is False else 'n/a (no full-population source)')} |"))
    gate_ok = all(v for v in st.values() if v is not None)
    hdr = "| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |\n|---|---|---|---|---|---|---|"
    sec = lambda name: "\n".join(r for s, r in rows if s == name)
    md = [f"# Phase 2 realism report", "",
          f"Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), {n} simulated 56-game seasons, a new league per season, seeds {seeds[0]}–{seeds[-1]}. Generated {dt.date.today().isoformat()}.",
          "Leaderboard rows pass if the real value lies within ±2 SD (prediction interval) of the simulated seasons.", "",
          f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
          "## Phase 1 league totals (must be unchanged)", "", hdr, sec("league"), "",
          f"Runs per half-inning: {'pass' if half_ok else 'FAIL'}. Sim {', '.join(f'{x:.4f}' for x in agg['half_inning_run_dist'])} vs {', '.join(str(x) for x in hb['bins'])}.", "",
          "## Game structure", "", hdr, sec("game"), "",
          f"### Runs per team-game histogram (±{rb['tol_per_bin']} per bin, TVD ≤ {rb['tol_total_variation']}): TVD {tvd:.4f} → **{'pass' if st['run_histogram'] else 'FAIL'}**", "",
          "| Runs | Sim | Benchmark | Diff | Status |", "|---|---|---|---|---|"]
    for i, (g, v) in enumerate(zip(agg["run_histogram"], rb["bins"])):
        md.append(f"| {i if i < 15 else '15+'} | {g:.4f} | {v:.4f} | {g - v:+.4f} | {'pass' if abs(g - v) <= rb['tol_per_bin'] else 'FAIL'} |")
    md += ["", "## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)", "", hdr, sec("team"), "",
           "## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)", "",
           f"Qualified per team: batters sim {agg['qualified']['batters']['per_team']:.2f} vs data {qp['batters']['per_team']}; pitchers sim {agg['qualified']['pitchers']['per_team']:.2f} vs data {qp['pitchers']['per_team']}.", "",
           hdr, sec("qualified"), "", "## Leaderboards (full-population extremes)", "", hdr, sec("leaders"), "",
           "## Diagnostics", "", f"- Home win pct {agg['home_win_pct']:.4f} (real {b['team_strength_2025'].get('home_win_pct', 0.5876)}; no home advantage is modeled)",
           f"- Pitchers per team-game {agg['usage']['pitchers_per_team_game']:.2f} (data {b['usage_2025']['pitchers_per_team_game']}); earned share of runs {agg['league']['earned_share']:.3f} (data {b['usage_2025']['earned_run_share']})", ""]
    return "\n".join(md), st
