"""Phase 2 metrics per simulated season, aggregation across seasons, and the realism report."""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from engine.status import Status
from config.phase2 import (SEASON_GAMES, DEFERRED_TO_PHASE6, WATCH_ITEMS, GATE_SE_MULTIPLE, LEADERBOARD_MIN_IP, LEADERBOARD_PI, QUAL_GAMES_SHARE, QUAL_IP_PER_TEAM_GAME,
                           QUAL_PA_PER_TEAM_GAME)
from engine.game2 import (B_2B, B_3B, B_AB, B_BB, B_G, B_GPA, B_H, B_HBP, B_HR, B_K, B_PA, B_SF, P_BF, P_ER, P_K, P_OUTS, P_WGS)

ROOT = Path(__file__).resolve().parents[1]
TIERS = ("p4", "mid", "low")
QS = (10, 25, 50, 75, 90)
LEADER_TOP = 5          # home-run leaders whose HR per game is gated (benchmarks individual_leaders_2023_2026)


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
    m["home_run_diff"] = float(np.mean([g[2] - g[3] for g in games]))
    cell = {(a, b): [] for a in TIERS for b in TIERS}
    for g in games:
        cell[(tier[g[0]], tier[g[1]])].append(g[2]); cell[(tier[g[1]], tier[g[0]])].append(g[3])
    m["tier_matrix"] = {a: {b: float(np.mean(cell[(a, b)])) for b in TIERS} for a in TIERS}
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
    # games counted as the benchmark counts them (scripts/build_phase2_gate.py): games with a plate appearance,
    # not substitute appearances without one (pinch runners, defensive substitutes; Phase 6)
    q = (b[:, B_PA] >= QUAL_PA_PER_TEAM_GAME * bt) & (b[:, B_GPA] >= QUAL_GAMES_SHARE * bt)
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
    # 56-game equivalents, as the benchmarks scale real seasons: a player's totals x 56 / his team's games
    # (Phase 7 cancels games, so teams play fewer than 56)
    s56 = SEASON_GAMES / bt
    p50 = ip * s56 >= LEADERBOARD_MIN_IP
    era50 = 9 * p[p50, P_ER] / ip[p50]
    # team leaders on full seasons, postseason included, as the NCAA.com team pages count them (Phase 7 world):
    # regular-season team rows plus the postseason lines (engine.season._postseason)
    tv = list(team.values())
    if "post" in res:
        pl_ = res["post"]["post_lines"]
        T = len(lg.teams)
        sm = lambda col_r, col_p: np.bincount(tids, tg[:, col_r], T) + np.bincount(pl_[:, 0].astype(int), pl_[:, col_p], T)
        gf = np.bincount(tids, minlength=T) + np.bincount(pl_[:, 0].astype(int), minlength=T)
        hf, abf, hrf, erf, outf = sm(3, 4), sm(4, 5), sm(5, 6), sm(6, 1), sm(7, 2)
        tv = [{"ba": hf[t] / abf[t], "hr_g": hrf[t] / gf[t], "era": 27 * erf[t] / outf[t]} for t in range(T) if gf[t] > 0]
    m["leaderboards"] = {"pitchers_50ip": int(p50.sum()), "pitchers_50ip_era_under_2": int((era50 < 2).sum()), "pitchers_50ip_era_under_3": int((era50 < 3).sum()),
                         "teams_era_under_4": int(sum(x["era"] < 4 for x in tv)), "best_team_era": min(x["era"] for x in tv),
                         "team_ba_max": max(x["ba"] for x in tv), "team_hr_per_game_max": max(x["hr_g"] for x in tv),
                         "individual_ba_top": float(np.nanmax(BA)), "individual_hr_top": int(b[:, B_HR].max())}
    # individual leaders (gate block individual_leaders_2023_2026): the five home-run leaders' HR per game played
    top = np.argsort(-b[:, B_HR], kind="stable")[:LEADER_TOP]
    hr56 = b[:, B_HR] * s56
    m["leaders"] = {"hr_leader_56g": float(hr56.max()), "hr_30plus_56g": int((hr56 >= 30).sum()), "ba_leader": float(np.nanmax(BA)),
                    "hr_top5_per_game": float(np.mean(b[top, B_HR] / np.maximum(b[top, B_G], 1))), "hr_max": int(b[:, B_HR].max())}
    # rotation: share of a team's weekend starts made by its three most frequent weekend starters
    tid_p = np.array([x.team for x in pl]); wgs = p[:, P_WGS]
    top3, nstart, iprank = [], [], []
    for t in range(len(lg.teams)):
        w = np.sort(wgs[tid_p == t])[::-1]
        if w.sum():
            top3.append(w[:3].sum() / w.sum()); nstart.append(int((w > 0).sum()))
        iprank.append(np.sort(ip[tid_p == t])[::-1][:3])
    m["usage"] = {"pitchers_per_team_game": float(p[:, 0].sum() / ntg), "weekend_top3_share": float(np.mean(top3)),
                  "weekend_starters_per_team": float(np.mean(nstart)), "ip_top3": [float(x) for x in np.mean(iprank, axis=0)]}
    return m


def aggregate(ms: list) -> dict:
    """Mean over seasons of every metric; out["se"] holds each mean's standard error
    (season-to-season SD / sqrt(n)), keyed by the metric's path."""
    n = len(ms)
    se: dict = {}

    def avg(path):
        vals = []
        for m in ms:
            v = m
            for k in path:
                v = v[k]
            vals.append(v)
        arr = np.array(vals, float)
        s_ = arr.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.zeros_like(arr[0])
        se["/".join(path)] = s_.tolist() if arr.ndim > 1 else float(s_)
        return arr.mean(axis=0) if arr.ndim > 1 else float(arr.mean())
    out = {"n_seasons": n, "se": se}
    out["league"] = {k: avg(["league", k]) for k in ms[0]["league"]}
    for k in ("run_histogram", "half_inning_run_dist"):
        out[k] = [float(x) for x in avg([k])]
    for k in ("extra_innings_freq", "run_rule_freq", "margin_10plus", "runs_sd", "home_win_pct", "home_run_diff", "big_inning_freq", "pa_per_half_inning"):
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
    out["leaders"] = {k: {"mean": avg(["leaders", k]), "min": float(min(m["leaders"][k] for m in ms)), "max": float(max(m["leaders"][k] for m in ms))}
                      for k in ms[0]["leaders"]}
    out["tier_matrix"] = {a: {b: avg(["tier_matrix", a, b]) for b in TIERS} for a in TIERS}
    out["usage"] = {k: (avg(["usage", k]) if k != "ip_top3" else [float(x) for x in avg(["usage", k])]) for k in ms[0]["usage"]}
    return out


def _t_quantile(p: float, df: int) -> float:
    """Student-t quantile by bisection on the numerically integrated density."""
    c = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))

    def cdf(x):
        g = np.linspace(0, x, 4001)
        return 1 / 2 + float(np.trapezoid(c * (1 + g ** 2 / df) ** (-(df + 1) / 2), g))
    lo, hi = 0, 1000
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


def build_report(agg: dict, seeds: list, bench: dict | None = None) -> tuple[str, dict]:
    b = bench or json.loads((ROOT / "benchmarks.json").read_text())
    st, rows = Status(), []
    se = agg["se"]
    n = agg["n_seasons"]
    k_se = GATE_SE_MULTIPLE

    def comb(tol, s):
        return None if tol is None else float(math.sqrt(tol ** 2 + (k_se * s) ** 2))

    def row(section, label, got, val, tol, conf, key, path, gate=True, nd=4):
        tol_c = comb(tol, se["/".join(path)])
        ok = None if (val is None or tol_c is None) else bool(abs(got - val) <= tol_c)
        deferred = key in DEFERRED_TO_PHASE6
        watch = key in WATCH_ITEMS
        if gate and not deferred and not watch:
            st[key] = ok
            st.record(key, got, se["/".join(path)])
        gcol = "Phase 6" if deferred else ("watch item: " + WATCH_ITEMS[key] if watch else ("yes" if gate else ""))
        status = "pass" if ok else ("FAIL" if ok is False else "n/a")
        rows.append((section, f"| {label} | {got:.{nd}f} | {'—' if val is None else f'{val:.{nd}f}'} | {'—' if tol_c is None else f'±{tol_c:.{max(nd, 3)}f}'} | {conf} | {gcol} | {status} |"))
    lt = b["league_totals_2025"]
    for key, label in (("runs_per_team_game", "Runs per team-game"), ("ba", "Batting average"), ("obp", "On-base pct"), ("slg", "Slugging pct"),
                       ("hr_per_team_game", "HR per team-game"), ("bb_pct", "BB per PA"), ("k_pct", "K per PA"), ("hbp_pct", "HBP per PA")):
        row("league", label, agg["league"][key], lt[key]["value"], lt[key]["tol"], lt[key]["conf"], f"league_{key}", ["league", key],
            gate=key in ("runs_per_team_game", "ba", "obp", "slg"))
    for key, label in (("errors_per_team_game", "Errors per team-game"), ("pa_per_team_game", "PA per team-game"), ("era", "ERA")):
        row("league", label, agg["league"][key], lt[key]["value"], lt[key]["tol"], lt[key]["conf"], f"league_{key}", ["league", key], gate=False)
    hb = b["half_inning_2025"]
    row("league", "Big-inning frequency (3+ runs)", agg["big_inning_freq"], hb["big_inning_freq"]["value"], hb["big_inning_freq"]["tol"], "A", "big_inning", ["big_inning_freq"])
    row("league", "PA per half-inning", agg["pa_per_half_inning"], hb["pa_per_half_inning"]["value"], hb["pa_per_half_inning"]["tol"], "A", "pa_half", ["pa_per_half_inning"], nd=3)
    half_tol = [comb(t, s_) for t, s_ in zip(hb["bin_tol"], se["half_inning_run_dist"])]
    half_ok = bool(all(abs(g - v) <= t for g, v, t in zip(agg["half_inning_run_dist"], hb["bins"], half_tol)))
    st["half_inning_run_dist"] = half_ok
    for i, (g, s_) in enumerate(zip(agg["half_inning_run_dist"], se["half_inning_run_dist"])):
        st.record(f"half_inning_run_dist_{i}", g, s_)
    gs = b["game_structure"]
    row("game", "Extra-innings frequency", agg["extra_innings_freq"], gs["extra_innings_freq"]["value"], gs["extra_innings_freq"]["tol"], gs["extra_innings_freq"]["conf"], "extra_innings", ["extra_innings_freq"])
    row("game", "Run-rule frequency", agg["run_rule_freq"], gs["run_rule_freq"]["value"], gs["run_rule_freq"].get("tol"), gs["run_rule_freq"]["conf"], "run_rule", ["run_rule_freq"])
    row("game", "Games decided by 10+ runs", agg["margin_10plus"], gs["run_distribution_per_team_game"]["share_games_margin_10plus"], None, "A", "margin10", ["margin_10plus"], gate=False)
    row("game", "Runs per team-game SD", agg["runs_sd"], gs["run_distribution_per_team_game"]["sd_runs_per_team_game"], None, "A", "runs_sd", ["runs_sd"], gate=False, nd=3)
    rb = gs["run_distribution_per_team_game"]
    hist_se = se["run_histogram"]
    bin_tol = [comb(rb["tol_per_bin"], s_) for s_ in hist_se]
    tvd = sum(abs(g - v) for g, v in zip(agg["run_histogram"], rb["bins"])) / 2
    tvd_tol = comb(rb["tol_total_variation"], math.sqrt(sum(s_ ** 2 for s_ in hist_se)) / 2)
    last = len(rb["bins"]) - 1  # the 15+ bin is gated in Phase 6
    bins_ok = [abs(g - v) <= t for g, v, t in zip(agg["run_histogram"], rb["bins"], bin_tol)]
    st["run_histogram"] = bool(all(bins_ok[:last]) and tvd <= tvd_tol)
    for i in range(last):
        st.record(f"run_histogram_{i}", agg["run_histogram"][i], hist_se[i])
    hm = b["home_2025"]
    row("game", "Home win pct", agg["home_win_pct"], hm["home_win_pct"]["value"], hm["home_win_pct"]["tol"], hm["conf"], "home_win_pct", ["home_win_pct"])
    row("game", "Home run differential per game", agg["home_run_diff"], hm["home_run_diff"]["value"], hm["home_run_diff"]["tol"], hm["conf"], "home_run_diff", ["home_run_diff"], nd=3)
    tm = b["tier_matrix_2025"]
    for bt in TIERS:
        for pt in TIERS:
            c = tm["matrix"][bt][pt]
            row("tiers", f"{bt} batting vs {pt} pitching", agg["tier_matrix"][bt][pt], c["r_per_game"], c["tol"], tm["conf"], f"tier_{bt}_{pt}", ["tier_matrix", bt, pt], nd=3)
    ts = b["team_strength_2025"]
    for scope, sim, real in [("all", agg["team_strength"]["all"], ts["all"])] + [(t, agg["team_strength"]["by_tier"][t], ts["by_tier"][t]) for t in TIERS]:
        base = ["team_strength", "all"] if scope == "all" else ["team_strength", "by_tier", scope]
        for s, lab in (("r_per_game", "R/G"), ("ra_per_game", "RA/G")):
            row("team", f"Team {lab} mean ({scope})", sim[s]["mean"], real[s]["mean"], real[s]["mean_tol"], "A", f"team_{scope}_{s}_mean", base + [s, "mean"], nd=3)
            row("team", f"Team {lab} SD across teams ({scope})", sim[s]["sd"], real[s]["sd"], real[s]["sd_tol"], "A", f"team_{scope}_{s}_sd", base + [s, "sd"], nd=3)
    qp = b["qualified_players_2025"]
    for side, cols in (("batters", ("BA", "OBP", "ISO", "K_pct", "BB_pct")), ("pitchers", ("ERA", "K9"))):
        for c in cols:
            for pq in ("p10", "p50", "p90"):
                nd = 2 if c in ("ERA", "K9") else 4
                row("qualified", f"{c} {pq}", agg["qualified"][side][c][pq], qp[side][c][pq], qp[side][c]["tol"][pq], qp["conf"], f"q_{c}_{pq}", ["qualified", side, c, pq], nd=nd)
    lbb = b["leaderboards_2025"]
    tq = _t_quantile((1 + LEADERBOARD_PI) / 2, n - 1) if n > 1 else float("inf")
    for k, lab in (("pitchers_50ip", "Pitchers with 50+ IP"), ("pitchers_50ip_era_under_2", "50+ IP pitchers with ERA < 2.00"), ("pitchers_50ip_era_under_3", "50+ IP pitchers with ERA < 3.00")):
        # counts of 50+ IP pitchers at a 56-game equivalent where the benchmark carries one (the sim plays 56 games)
        s, real = agg["leaderboards"][k], lbb[k].get("value_56g", lbb[k]["value"])
        half = tq * s["sd"] * np.sqrt(1 + 1 / n)
        ok = None if real is None else bool(abs(real - s["mean"]) <= half)
        deferred = f"lb_{k}" in DEFERRED_TO_PHASE6
        if real is not None and not deferred:
            st[f"lb_{k}"] = ok
            st.record(f"lb_{k}", s["mean"], s["sd"] / np.sqrt(n))
        nd = 3 if s["mean"] < 10 else 1
        gcol = "Phase 6" if deferred else ("yes" if real is not None else "")
        rows.append(("leaders", f"| {lab} | {s['mean']:.{nd}f} (season range {s['min']:.{nd}f}–{s['max']:.{nd}f}) | {'—' if real is None else real}{' (56-game eq. of ' + str(lbb[k]['value']) + ')' if 'value_56g' in lbb[k] else ''} | ±{half:.{nd}f} | {lbb[k]['conf']} | {gcol} | "
                                f"{'pass' if ok else ('FAIL' if ok is False else 'n/a (no full-population source)')} |"))
    # team leaders: the 2024-2026 band (team_leaders_2024_2026), as the individual leaders
    tl = b["team_leaders_2024_2026"]
    for k, lab, nd in (("teams_era_under_4", "Teams with ERA < 4.00", 1), ("best_team_era", "Best team ERA", 3), ("team_ba_max", "Best team BA", 3),
                       ("team_hr_per_game_max", "Most team HR per game", 3)):
        s, real = agg["leaderboards"][k], tl[k]
        pad = k_se * s["sd"] / np.sqrt(n)
        ok = bool(real["lo"] - pad <= s["mean"] <= real["hi"] + pad)
        watch = f"lb_{k}" in WATCH_ITEMS
        st[f"lb_{k}"] = None if watch else ok
        if not watch:
            st.record(f"lb_{k}", s["mean"], s["sd"] / np.sqrt(n))
        seasons = ", ".join(f"{y} {v:.{nd}f}" for y, v in real["by_season"].items())
        gcol = "watch item: " + WATCH_ITEMS[f"lb_{k}"] if watch else "yes"
        rows.append(("teamleaders", f"| {lab} | {s['mean']:.{nd}f} (season range {s['min']:.{nd}f}–{s['max']:.{nd}f}) | {real['lo']:.{nd}f}–{real['hi']:.{nd}f} ({seasons}) | "
                                    f"±{pad:.{nd}f} | {tl['conf']} | {gcol} | {'pass' if ok else 'FAIL'} |"))
    il = b["individual_leaders_2023_2026"]
    for k, lab, nd in (("hr_leader_56g", "HR leader (56-game equivalent)", 1), ("hr_30plus_56g", "Hitters with 30+ HR (56-game equivalent)", 2),
                       ("ba_leader", "BA leader (qualified)", 3), ("hr_top5_per_game", "Top-5 HR hitters, HR per game", 3)):
        s, real = agg["leaders"][k], il[k]
        pad = k_se * se[f"leaders/{k}"]
        ok = bool(real["lo"] - pad <= s["mean"] <= real["hi"] + pad)
        st[f"lb_ind_{k}"] = ok
        st.record(f"lb_ind_{k}", s["mean"], se[f"leaders/{k}"])
        seasons = ", ".join(f"{y} {v:.{nd}f}" for y, v in real["by_season"].items())
        rows.append(("individual", f"| {lab} | {s['mean']:.{nd}f} (season range {s['min']:.{nd}f}–{s['max']:.{nd}f}) | {real['lo']:.{nd}f}–{real['hi']:.{nd}f} ({seasons}) | "
                                   f"±{pad:.{nd}f} | {il['conf']} | yes | {'pass' if ok else 'FAIL'} |"))
    rec = il["hr_season_record"]["value"]
    hr_max = agg["leaders"]["hr_max"]["max"]
    st["lb_ind_hr_record_ceiling"] = bool(hr_max <= rec)
    rows.append(("individual", f"| Most HR by any player, all {n} seasons (hard ceiling) | {hr_max:.0f} | ≤ {rec} (D1 record) | — | A | yes | {'pass' if hr_max <= rec else 'FAIL'} |"))
    gate_ok = all(v for v in st.values() if v is not None)
    hdr = "| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |\n|---|---|---|---|---|---|---|"
    sec = lambda name: "\n".join(r for s, r in rows if s == name)
    md = [f"# Phase 2 realism report", "",
          f"Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), {n} simulated 56-game seasons, a new league per season, seeds {seeds[0]}–{seeds[-1]}. Generated {dt.date.today().isoformat()}.",
          f"Tolerances combine the benchmark's (3 SE of the real statistic) with {k_se} SE of the simulated mean at {n} seasons. "
          f"Leaderboard rows pass if the real value lies inside the {LEADERBOARD_PI:.0%} Student-t prediction interval of the simulated seasons. "
          "Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.", "",
          f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
          "## Phase 1 league totals (must be unchanged)", "", hdr, sec("league"), "",
          f"Runs per half-inning: {'pass' if half_ok else 'FAIL'}. Sim {', '.join(f'{x:.4f}' for x in agg['half_inning_run_dist'])} vs {', '.join(str(x) for x in hb['bins'])}.", "",
          "## Game structure", "", hdr, sec("game"), "",
          f"### Runs per team-game histogram (±{rb['tol_per_bin']} per bin and TVD ≤ {rb['tol_total_variation']}, each combined with the sim's SE; 15+ bin in Phase 6): "
          f"TVD {tvd:.4f} (limit {tvd_tol:.4f}) → **{'pass' if st['run_histogram'] else 'FAIL'}**", "",
          "| Runs | Sim | Benchmark | Diff | Tol | Status |", "|---|---|---|---|---|---|"]
    for i, (g, v) in enumerate(zip(agg["run_histogram"], rb["bins"])):
        ok = abs(g - v) <= bin_tol[i]
        md.append(f"| {i if i < last else f'{last}+'} | {g:.4f} | {v:.4f} | {g - v:+.4f} | ±{bin_tol[i]:.4f} | {('pass' if ok else 'FAIL') + (' (Phase 6)' if i == last else '')} |")
    md += ["", "## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)", "", hdr, sec("tiers"), "",
           "## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)", "", hdr, sec("team"), "",
           "## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)", "",
           f"Qualified per team: batters sim {agg['qualified']['batters']['per_team']:.2f} vs data {qp['batters']['per_team']}; pitchers sim {agg['qualified']['pitchers']['per_team']:.2f} vs data {qp['pitchers']['per_team']}.", "",
           hdr, sec("qualified"), "", "## Leaderboards (full-population extremes)", "", hdr, sec("leaders"), "",
           "## National team leaders (NCAA.com team pages, 2024–2026)", "",
           "Rates and counts of teams on full seasons: real seasons include conference tournaments, the NCAA tournament and non-D1 games; the sim's "
           "its regular season plus its postseason when the Phase 7 world is on (the rest of this report is the regular season). A row passes if the simulated mean lies in the band from the "
           f"lowest to the highest real season, widened by {k_se} SE of the simulated mean. Benchmark column: the band, then each season.", "",
           "| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |\n|---|---|---|---|---|---|---|", sec("teamleaders"), "",
           "## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)", "",
           f"Counting stats at a {il['season_games']}-game equivalent (each real player's HR × {il['season_games']} / his games; real leaders' teams played 57–72 games, "
           "the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by "
           f"{k_se} SE of the simulated mean. Benchmark column: the band, then each season.", "",
           "| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |\n|---|---|---|---|---|---|---|", sec("individual"), "",
           "## Diagnostics", "",
           f"- Earned share of runs {agg['league']['earned_share']:.4f} (data {b['usage_2025']['earned_run_share']}); pitchers per team-game {agg['usage']['pitchers_per_team_game']:.2f} (data {b['usage_2025']['pitchers_per_team_game']})",
           f"- Weekend starts by a team's top three starters {agg['usage']['weekend_top3_share']:.3f} (data {sum(b['usage_2025']['weekend_start_share_by_rank'][str(k)] for k in (1, 2, 3)):.3f}); weekend starters per team {agg['usage']['weekend_starters_per_team']:.2f} (data {b['usage_2025']['weekend_starters_per_team']})",
           f"- Innings of a team's three busiest pitchers {', '.join(f'{x:.1f}' for x in agg['usage']['ip_top3'])} (data, full-season teams averaging {b['usage_2025']['games_per_full_season_team']} games: {', '.join(str(b['usage_2025']['pitcher_ip_by_team_rank'][str(k)]) for k in (1, 2, 3))})", ""]
    return "\n".join(md), st
