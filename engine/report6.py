"""Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI.

Gate rows:
  - errors per team-game; stolen bases per team-game and steal success (league_totals_2025);
  - pitcher usage at a 56-game equivalent (usage_phase6_2025): appearances of a team's busiest, 5th
    and 10th busiest pitchers, relief-only pitchers (3 or fewer starts) with 40+ and 60+ IP, the top
    three pitchers' innings; distinct batters per team-game;
  - the rows deferred from Phases 2 and 5 (CLAUDE.md): run-rule frequency, runs per team-game 15+,
    pitchers with 50+ IP, qualified K/9 p50 and p90, midweek starter pitch count p10, P4 batting vs
    low pitching;
  - every Phase 1, 2, 4 and 5 gate on the same run.
Tolerances as in those phases: the benchmark's combined with 3 SE of the simulated mean at the
number of seasons run (leaderboard counts: the Student-t prediction interval of the seasons).
Reported with their diagnosis (CLAUDE.md watch items): the within-game residual correlation and
dispersion of runs around the team-strength fit, the strikeout leader, ERA ranks 2-5, the elite
run-prevention rows, errors by tier, the top three pitchers' innings split.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

from config.phase2 import GATE_SE_MULTIPLE, LEADERBOARD_PI, TIERS
from engine.game2 import P_ER, P_G, P_GS, P_K, P_OUTS

ROOT = Path(__file__).resolve().parents[1]
FRI_SUN = (4, 5, 6)


def season_extract6(res: dict) -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    from build_phase2_teams import fit
    lg, p, tg, games = res["league"], res["pstats"], res["team_game_rows"], res["games"]
    tier = {t.tid: t.tier for t in lg.teams}
    out = {"errors_per_team_game": float(tg[:, 8].mean()), "batters_per_team_game": float(tg[:, 10].mean())}
    for t in TIERS:
        sel = np.array([tier[int(x)] == t for x in tg[:, 0]])
        out[f"errors_{t}"] = float(tg[sel, 8].mean())
    att, ok = res["sb"]
    out["sb_per_team_game"], out["sb_attempts_per_team_game"], out["sb_success_rate"] = ok / len(tg), att / len(tg), ok / max(att, 1)
    o = res["outings"]
    fs_outs, os_outs, rl_outs = {}, {}, {}
    for pid, started, outs, wd in o:
        d = (fs_outs if wd in FRI_SUN else os_outs) if started else rl_outs
        d[pid] = d.get(pid, 0) + outs
    usage = []
    for tm in lg.teams:
        ids = [x.pid for x in tm.weekend_sp + tm.midweek_sp + tm.relievers]
        g = np.sort(p[ids, P_G])[::-1]
        ipx = p[ids, P_OUTS] / 3
        rel = p[ids, P_GS] <= 3
        top = [ids[i] for i in np.argsort(-ipx)[:3]]
        row = [g[0], g[4], g[9], float((rel & (ipx >= 40)).sum()), float((rel & (ipx >= 60)).sum())]
        row += [p[i, P_OUTS] / 3 for i in top]
        for i in top:
            row += [fs_outs.get(i, 0) / 3, os_outs.get(i, 0) / 3, rl_outs.get(i, 0) / 3]
        usage.append(row)
    u = np.mean(usage, axis=0)
    names = ["app_max", "app_5th", "app_10th", "relief_only_40ip", "relief_only_60ip", "ip_rank1", "ip_rank2", "ip_rank3"]
    for k in range(3):
        names += [f"ip_rank{k + 1}_fri_sun_starts", f"ip_rank{k + 1}_other_starts", f"ip_rank{k + 1}_relief"]
    out.update(dict(zip(names, map(float, u))))
    gd = pd.DataFrame(games, columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    nm = sorted(set(gd.home) | set(gd.away))
    f0, f1 = fit(gd, nm, parks=False), fit(gd, nm)
    out.update({"resid_corr": f0["residual_corr"], "dispersion": f0["phi"], "resid_corr_parks": f1["residual_corr"], "dispersion_parks": f1["phi"]})
    team_g = res["team_games"]
    ipp = p[:, P_OUTS] / 3
    qual = [x.pid for x in lg.players if x.side == "pit" and p[x.pid, P_OUTS] >= 3 * team_g[x.team]]
    era = np.sort([9 * p[i, P_ER] / ipp[i] for i in qual])
    out.update({"k_leader": float(p[:, P_K].max()), "era_rank2": float(era[1]), "era_rank5": float(era[4]), "era_rank1": float(era[0])})
    # reliever workloads, national (the leaders audit's watch item; raw 56-game counts)
    pit = np.array([x.pid for x in lg.players if x.side == "pit"])
    gp, gs, ip = p[pit, P_G], p[pit, P_GS], p[pit, P_OUTS] / 3
    by_app = np.argsort(-gp, kind="stable")
    rel = gs <= 3
    out.update({"app_max_national": float(gp[by_app[0]]), "app_50th_national": float(gp[by_app[49]]),
                "top50_app_with_60ip": float((ip[by_app[:50]] >= 60).sum()), "relief_ip_max": float(ip[rel].max()),
                "relievers_60ip": float((rel & (ip >= 60)).sum()), "ip_leader_is_reliever": float(rel[np.argmax(ip)])})
    return out


def aggregate6(ex: list) -> dict:
    n = len(ex)
    keys = ex[0].keys()
    mean = {k: float(np.mean([e[k] for e in ex])) for k in keys}
    se = {k: float(np.std([e[k] for e in ex], ddof=1) / np.sqrt(n)) if n > 1 else 0.0 for k in keys}
    lo = {k: float(np.min([e[k] for e in ex])) for k in keys}
    hi = {k: float(np.max([e[k] for e in ex])) for k in keys}
    return {"n_seasons": n, "mean": mean, "se": se, "min": lo, "max": hi}


def _t_quantile(p: float, df: int) -> float:
    from engine.report2 import _t_quantile as tq
    return tq(p, df)


def build_report6(agg: dict, agg2: dict, agg5: dict, seeds: list, st2: dict, st4: dict, st5: dict) -> tuple[str, dict]:
    b = json.loads((ROOT / "benchmarks.json").read_text())
    m, se = agg["mean"], agg["se"]
    n = agg["n_seasons"]
    k = GATE_SE_MULTIPLE
    st, rows = {}, []

    def comb(tol, s):
        return float(math.sqrt(tol ** 2 + (k * s) ** 2))

    def row(section, key, label, got, s_, val, tol, nd=3, note=""):
        t = comb(tol, s_)
        ok = bool(abs(got - val) <= t)
        st[key] = ok
        rows.append((section, f"| {label} | {got:.{nd}f} | {val:.{nd}f} | ±{t:.{nd}f} | {'pass' if ok else 'FAIL'} | {note} |"))
    lt = b["league_totals_2025"]
    row("field", "p6_errors_per_team_game", "Errors per team-game", m["errors_per_team_game"], se["errors_per_team_game"],
        lt["errors_per_team_game"]["value"], lt["errors_per_team_game"]["tol"])
    row("field", "p6_sb_per_team_game", "Stolen bases per team-game", m["sb_per_team_game"], se["sb_per_team_game"], lt["sb_per_team_game"]["value"], lt["sb_per_team_game"]["tol"])
    row("field", "p6_sb_success_rate", "Steal success rate", m["sb_success_rate"], se["sb_success_rate"], lt["sb_success_rate"]["value"], lt["sb_success_rate"]["tol"])
    u6 = b["usage_phase6_2025"]
    row("field", "p6_earned_share", "Earned share of runs", agg2["league"]["earned_share"], agg2["se"]["league/earned_share"], u6["earned_run_share"]["value"],
        u6["earned_run_share"]["tol"], 4, "gated here, not against the Phase 4 run (Phase 6 fielding moves it)")
    for key, label in (("app_max", "Appearances, team's busiest pitcher"), ("app_5th", "Appearances, 5th busiest"), ("app_10th", "Appearances, 10th busiest"),
                       ("relief_only_40ip", "Relief-only pitchers (≤3 GS) with 40+ IP, per team"), ("relief_only_60ip", "Relief-only pitchers with 60+ IP, per team"),
                       ("ip_rank1", "IP, team's top pitcher"), ("ip_rank2", "IP, 2nd"), ("ip_rank3", "IP, 3rd")):
        row("usage", f"p6_{key}", label, m[key], se[key], u6[key]["value"], u6[key]["tol"], 2)
    row("usage", "p6_batters_per_team_game", "Distinct batters per team-game", m["batters_per_team_game"], se["batters_per_team_game"],
        u6["batters_per_team_game"]["value"], u6["batters_per_team_game"]["tol"], 3)
    # rows deferred from Phases 2 and 5
    s2 = agg2["se"]
    gs = b["game_structure"]
    row("deferred", "p6_run_rule", "Run-rule frequency", agg2["run_rule_freq"], s2["run_rule_freq"], gs["run_rule_freq"]["value"], gs["run_rule_freq"]["tol"], 4)
    rb = gs["run_distribution_per_team_game"]
    row("deferred", "p6_run_histogram_15plus", "Runs per team-game, 15+ bin", agg2["run_histogram"][15], s2["run_histogram"][15], rb["bins"][15], rb["tol_per_bin"], 4)
    qp = b["qualified_players_2025"]["pitchers"]["K9"]
    for q in ("p50", "p90"):
        row("deferred", f"p6_q_K9_{q}", f"Qualified K/9 {q}", agg2["qualified"]["pitchers"]["K9"][q], s2[f"qualified/pitchers/K9/{q}"], qp[q], qp["tol"][q], 2)
    c = b["tier_matrix_2025"]["matrix"]["p4"]["low"]
    row("deferred", "p6_tier_p4_low", "P4 batting vs low pitching (R/G)", agg2["tier_matrix"]["p4"]["low"], s2["tier_matrix/p4/low"], c["r_per_game"], c["tol"], 2)
    pl = b["pitch_level_2025"]["pitches_per_start_midweek_p10"]
    row("deferred", "p6_midweek_p10", "Midweek starter pitch count p10 (Mon-Wed)", agg5["mean"]["pitches_per_start_midweek_p10"],
        agg5["se"]["pitches_per_start_midweek_p10"], pl["value"], pl["tol"], 1)
    lb = agg2["leaderboards"]["pitchers_50ip"]
    tq = _t_quantile((1 + LEADERBOARD_PI) / 2, n - 1) if n > 1 else float("inf")
    half = tq * lb["sd"] * math.sqrt(1 + 1 / n)
    pb = b["leaderboards_2025"]["pitchers_50ip"]
    real = pb["value_56g"]
    ok = bool(abs(real - lb["mean"]) <= half)
    st["p6_pitchers_50ip"] = ok
    rows.append(("deferred", f"| Pitchers with 50+ IP | {lb['mean']:.1f} (seasons {lb['min']:.0f}–{lb['max']:.0f}) | {real} | ±{half:.1f} (95% PI) | {'pass' if ok else 'FAIL'} | "
                             f"56-game equivalent of the raw {pb['value']} (ratio {pb['ratio_56g']['value']} ± {pb['ratio_56g']['se']}, WMT full-season teams) |"))
    for name, s_ in (("phase2_gate", st2), ("phase4_gate", st4), ("phase5_gate", st5)):
        st[name] = bool(all(v for kk, v in s_.items() if v is not None))
    gate_ok = all(v for v in st.values() if v is not None)
    tt = b["team_talent_2025"]
    hdr = "| Metric | Sim | Benchmark | Tol | Status | Note |\n|---|---|---|---|---|---|"
    sec = lambda name: "\n".join(r for s_, r in rows if s_ == name)  # noqa: E731
    lbs = agg2["leaderboards"]
    md = ["# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI", "",
          f"{n} simulated 56-game seasons, seeds {seeds[0]}–{seeds[-1]}, all mechanisms on (config.phase6.FEATURES). Generated {dt.date.today().isoformat()}. "
          f"Tolerances combine the benchmark's with {k} SE of the simulated mean at {n} seasons.", "",
          f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
          f"Every Phase 1 and 2 row (reports/phase2.md): **{'pass' if st['phase2_gate'] else 'FAIL'}**; Phase 4 forward ratings test (reports/phase4.md): "
          f"**{'pass' if st['phase4_gate'] else 'FAIL'}**; Phase 5 pitch-by-pitch (reports/phase5.md): **{'pass' if st['phase5_gate'] else 'FAIL'}**.", "",
          "## Fielding and base running", "", hdr, sec("field"), "",
          f"Errors per team-game by tier: P4 {m['errors_p4']:.3f}, mid {m['errors_mid']:.3f}, low {m['errors_low']:.3f} "
          f"(2025 sample, raw: {lt['errors_per_team_game']['by_tier_in_sample']}). Steal attempts per team-game {m['sb_attempts_per_team_game']:.3f} "
          f"(real {lt['sb_attempts_per_team_game']['value']}).", "",
          "## Pitcher usage (56-game equivalent)", "", hdr, sec("usage"), "",
          "Top three pitchers' innings, split (sim / real): " + "; ".join(
              f"#{r}: Fri-Sun starts {m[f'ip_rank{r}_fri_sun_starts']:.1f} / {u6[f'ip_rank{r}_fri_sun_starts']['value']:.1f}, "
              f"other starts {m[f'ip_rank{r}_other_starts']:.1f} / {u6[f'ip_rank{r}_other_starts']['value']:.1f}, "
              f"relief {m[f'ip_rank{r}_relief']:.1f} / {u6[f'ip_rank{r}_relief']['value']:.1f}" for r in (1, 2, 3)) + ".", "",
          "## Rows deferred from Phases 2 and 5", "", hdr, sec("deferred"), "",
          "## Diagnostics (CLAUDE.md watch items)", "",
          f"- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation "
          f"{m['resid_corr']:.4f} (real {tt['residual_corr_within_game']}), dispersion {m['dispersion']:.3f} (real {tt.get('dispersion_without_parks', '—')}); "
          f"with the park term: {m['resid_corr_parks']:.4f} (real {tt.get('residual_corr_within_game_with_parks', '—')}), {m['dispersion_parks']:.3f} (real {tt['dispersion']}).",
          f"- Strikeout leader {m['k_leader']:.1f} (seasons {agg['min']['k_leader']:.0f}–{agg['max']['k_leader']:.0f}); real 2024-2026 leaders 191 / 180 / 169 "
          "in 57-72 team games.",
          f"- Qualified ERA: leader {m['era_rank1']:.2f}, #2 {m['era_rank2']:.2f}, #5 {m['era_rank5']:.2f} (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).",
          f"- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances "
          f"{m['app_max_national']:.1f} (real 38 / 37 / 39); 50th-most-used pitcher {m['app_50th_national']:.1f} (29 / 28 / 28); of the top 50 by "
          f"appearances {m['top50_app_with_60ip']:.1f} have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts {m['relief_ip_max']:.1f} "
          f"(the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP {m['relievers_60ip']:.1f}; the IP leader is a reliever "
          f"in {m['ip_leader_is_reliever'] * n:.0f} of {n} seasons.",
          f"- Elite run prevention (Phase 2 rows): best team ERA {lbs['best_team_era']['mean']:.2f} (real 3.20), 50+ IP pitchers with ERA < 2.00 "
          f"{lbs['pitchers_50ip_era_under_2']['mean']:.1f} (5), < 3.00 {lbs['pitchers_50ip_era_under_3']['mean']:.1f} (57), teams with ERA < 4.00 "
          f"{lbs['teams_era_under_4']['mean']:.1f} (12).", ""]
    return "\n".join(md), st
