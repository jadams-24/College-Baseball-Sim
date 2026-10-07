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

from config.phase2 import GATE_SE_MULTIPLE, LEADERBOARD_PI, SEASON_GAMES, TIERS

# owner decision (2026-10-03): named watch items, reported with their diagnosis and not gated (PHASE0_NOTES, Phase 6)
WATCH6 = {"p6_run_rule": "offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES)",
          "p6_run_histogram_15plus": "offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES)",
          # owner decision 2026-10-04: re-checked in Phase 7, once conference tournaments and the postseason change rotation usage
          "p6_ip_rank2": "top starters' innings (re-check in Phase 7)",
          "p6_pitchers_50ip": "top starters' innings (re-check in Phase 7)"}
from engine.status import Status
from engine.game2 import P_ER, P_G, P_GS, P_K, P_OUTS

ROOT = Path(__file__).resolve().parents[1]
FRI_SUN = (4, 5, 6)
PATH_COUNTS = tuple(f"{b}-{s}" for b in range(4) for s in range(3) if (b, s) != (0, 0))   # 0-0: 48 plate appearances in the data


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
    dc = res.get("decisions")
    if dc is not None:
        # PR B: decisions (per team-game, regular season) and the steal paths
        for k in ("bunts", "SH", "bunt_hits", "ibb"):
            out[f"dec_{k}_per_team_game"] = dc[k] / len(tg)
        # the steal paths: gated on every plate appearance that began with a lead runner able to steal (path_all_*),
        # the first-event sample (path_*) as a diagnostic; prefix "path" for the gated, "fe" for the diagnostic
        for pre, kl, kf in (("path", "path_all_by_len", "path_all_by_fc"), ("fe", "path_by_len", "path_by_fc")):
            tot = np.sum([v for v in dc[kl].values()], axis=0)
            out[f"{pre}_attempt_per_pa"] = tot[1] / max(tot[0], 1)
            out[f"{pre}_success"] = tot[2] / max(tot[1], 1)
            for L in range(2, 9):
                n_, a_, k_ = dc[kl].get(L, (0, 0, 0))
                out[f"{pre}_len{L}_attempt"] = a_ / max(n_, 1)
                out[f"{pre}_len{L}_success"] = k_ / a_ if a_ else float("nan")
            for fc in PATH_COUNTS:
                n_, a_, _ = dc[kf].get(fc, (0, 0, 0))
                out[f"{pre}_fc{fc}_attempt"] = a_ / max(n_, 1)
    o = res["outings"]
    fs_outs, os_outs, rl_outs = {}, {}, {}
    for pid, started, outs, wd in o:
        d = (fs_outs if wd in FRI_SUN else os_outs) if started else rl_outs
        d[pid] = d.get(pid, 0) + outs
    usage = []
    for tm in lg.teams:
        # 56-game equivalent, as the benchmark scales real teams: x 56 / the team's games (Phase 7 cancellations)
        s56 = SEASON_GAMES / res["team_games"][tm.tid]
        ids = [x.pid for x in tm.weekend_sp + tm.midweek_sp + tm.relievers]
        g = np.sort(p[ids, P_G])[::-1] * s56
        ipx = p[ids, P_OUTS] / 3 * s56
        rel = p[ids, P_GS] <= 3
        top = [ids[i] for i in np.argsort(-ipx)[:3]]
        row = [g[0], g[4], g[9], float((rel & (ipx >= 40)).sum()), float((rel & (ipx >= 60)).sum())]
        row += [p[i, P_OUTS] / 3 * s56 for i in top]
        for i in top:
            row += [fs_outs.get(i, 0) / 3 * s56, os_outs.get(i, 0) / 3 * s56, rl_outs.get(i, 0) / 3 * s56]
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
    # tier-mean recovery: the park fit's tier means of (o, d) against the drawn net ratings (both centred over teams),
    # and the fit without parks against the real scoreboard's (diagnostic)
    T = {t.tid: t for t in lg.teams}
    tn = np.array([T[x].tier for x in nm])
    xo, xd = np.array([T[x].o for x in nm]), np.array([T[x].d for x in nm])
    xo, xd = xo - xo.mean(), xd - xd.mean()
    for tr in TIERS:
        k = tn == tr
        out[f"rec_o_minus_drawn_{tr}"] = float(f1["o"][k].mean() - xo[k].mean())
        out[f"rec_d_minus_drawn_{tr}"] = float(f1["d"][k].mean() - xd[k].mean())
        out[f"nopark_o_{tr}"], out[f"nopark_d_{tr}"] = float(f0["o"][k].mean()), float(f0["d"][k].mean())
    # schedule selection (scripts/build_phase6_schedule.py), measured as on the real scoreboard: the mean within-tier
    # deviation of fitted strength (fit without parks) of the teams in each directed nonconference tier pairing, and
    # the covariance of opponents' deviations in cross-tier games
    s0 = f0["o"] + f0["d"]
    dv = {x: float(s0[i] - s0[tn == T[x].tier].mean()) for i, x in enumerate(nm)}
    ind = {cid for cid, c in lg.conferences.items() if c[3]}
    sel, xs = {}, []
    for h, a in zip(gd.home, gd.away):
        if T[h].conference != T[a].conference or T[h].conference in ind:
            for p_, q_ in ((h, a), (a, h)):
                sel.setdefault(f"{T[p_].tier}|{T[q_].tier}", []).append(dv[p_])
                if T[p_].tier != T[q_].tier:
                    xs.append((dv[p_], dv[q_]))
    out.update({f"sel_{k_}": float(np.mean(v_)) for k_, v_ in sel.items()})
    xs = np.array(xs)
    out["sel_cross_cov"] = float(np.cov(xs[:, 0], xs[:, 1])[0, 1])
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
    mean = {k: float(np.nanmean([e[k] for e in ex])) for k in keys}
    se = {k: float(np.nanstd([e[k] for e in ex], ddof=1) / np.sqrt(n)) if n > 1 else 0.0 for k in keys}
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
    st, rows = Status(), []

    def comb(tol, s):
        return float(math.sqrt(tol ** 2 + (k * s) ** 2))

    def row(section, key, label, got, s_, val, tol, nd=3, note=""):
        t = comb(tol, s_)
        ok = bool(abs(got - val) <= t)
        watch = key in WATCH6
        st[key] = None if watch else ok
        if not watch:
            st.record(key, got, s_)
        note = (f"watch item: {WATCH6[key]}. " if watch else "") + note
        rows.append((section, f"| {label} | {got:.{nd}f} | {val:.{nd}f} | ±{t:.{nd}f} | {'pass' if ok else 'FAIL'} | {note} |"))
    lt = b["league_totals_2025"]
    row("field", "p6_errors_per_team_game", "Errors per team-game", m["errors_per_team_game"], se["errors_per_team_game"],
        lt["errors_per_team_game"]["value"], lt["errors_per_team_game"]["tol"])
    row("field", "p6_sb_per_team_game", "Stolen bases per team-game", m["sb_per_team_game"], se["sb_per_team_game"], lt["sb_per_team_game"]["value"], lt["sb_per_team_game"]["tol"])
    row("field", "p6_sb_success_rate", "Steal success rate", m["sb_success_rate"], se["sb_success_rate"], lt["sb_success_rate"]["value"], lt["sb_success_rate"]["tol"])
    u6 = b["usage_phase6_2025"]
    # PA per team-game: the per-opportunity base running (scripts/build_engine_tables.py) moves it on purpose,
    # so it is gated against real data here, not against the Phase 4 run (reports/phase5.md)
    row("field", "p6_pa_per_team_game", "PA per team-game", agg2["league"]["pa_per_team_game"], agg2["se"]["league/pa_per_team_game"],
        lt["pa_per_team_game"]["value"], lt["pa_per_team_game"]["tol"], 2, "gated here, not against the Phase 4 run (base running per opportunity moves it)")
    row("field", "p6_era", "ERA", agg2["league"]["era"], agg2["se"]["league/era"], lt["era"]["value"], lt["era"]["tol"], 3,
        "gated here, not against the Phase 4 run (PR B decisions move it; owner decision 2026-10-07)")
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
    watch = "p6_pitchers_50ip" in WATCH6
    st["p6_pitchers_50ip"] = None if watch else ok
    if not watch:
        st.record("p6_pitchers_50ip", lb["mean"], lb["sd"] / math.sqrt(n))
    rows.append(("deferred", f"| Pitchers with 50+ IP | {lb['mean']:.1f} (seasons {lb['min']:.0f}–{lb['max']:.0f}) | {real} | ±{half:.1f} (95% PI) | {'pass' if ok else 'FAIL'} | "
                             f"{'watch item: ' + WATCH6['p6_pitchers_50ip'] + '. ' if watch else ''}56-game equivalent of the raw {pb['value']} (ratio {pb['ratio_56g']['value']} ± {pb['ratio_56g']['se']}, WMT full-season teams) |"))
    # PR B: decisions that change outcomes, with the AI deciding (benchmarks decisions_2025: the play-by-play's games)
    if "dec_bunts_per_team_game" in m:
        sa = lt["sb_attempts_per_team_game"]
        row("dec", "pb_sb_attempts", "Steal attempts per team-game", m["sb_attempts_per_team_game"], se["sb_attempts_per_team_game"], sa["value"], sa["tol"], 3,
            "box-score count: every runner in a double steal, a runner picked off while breaking charged a caught stealing")
        dz = b["decisions_2025"]
        for key, label in (("bunts", "Bunts per team-game"), ("SH", "Sacrifice hits per team-game"), ("bunt_hits", "Bunt hits per team-game"),
                           ("ibb", "Intentional walks per team-game")):
            bz = dz[f"{key}_per_team_game"]
            row("dec", f"pb_{key}", label, m[f"dec_{key}_per_team_game"], se[f"dec_{key}_per_team_game"], bz["value"], bz["tol"], 3)
        pz, fe = dz["steal_paths"], dz["steal_paths_first_event"]
        row("dec", "pb_path_attempt", "Steal attempts per eligible PA", m["path_attempt_per_pa"], se["path_attempt_per_pa"],
            pz["attempt_per_pa"]["value"], pz["attempt_per_pa"]["tol"], 4)
        row("dec", "pb_path_success", "Steal success on eligible PAs", m["path_success"], se["path_success"], pz["success"]["value"], pz["success"]["tol"], 3)
        for L in range(2, 9):
            c_ = pz["by_length"][str(L)]
            row("path", f"pb_len{L}_attempt", f"Attempt per PA, {L}{'+' if L == 8 else ''} pitches", m[f"path_len{L}_attempt"], se[f"path_len{L}_attempt"],
                c_["attempt"], c_["tol_attempt"], 4)
        for L in range(2, 9):
            c_ = pz["by_length"][str(L)]
            row("path", f"pb_len{L}_success", f"Success, {L}{'+' if L == 8 else ''} pitches", m[f"path_len{L}_success"], se[f"path_len{L}_success"],
                c_["success"], c_["tol_success"], 3)
        for fc in PATH_COUNTS:
            c_ = pz["by_final_count"][fc]
            row("path", f"pb_fc{fc}_attempt", f"Attempt per PA, final count {fc}", m[f"path_fc{fc}_attempt"], se[f"path_fc{fc}_attempt"],
                c_["attempt"], c_["tol_attempt"], 4)
    for tr in TIERS:
        for s_k, lab in (("o", "offense"), ("d", "run prevention")):
            key = f"rec_{s_k}_minus_drawn_{tr}"
            row("recovery", f"p6_{key}", f"{tr.upper() if tr == 'p4' else tr} {lab}: recovered minus drawn (park fit, tier mean)", m[key], se[key], 0.0, 0.0, 3)
    for name, s_ in (("phase2_gate", st2), ("phase4_gate", st4), ("phase5_gate", st5)):
        st[name] = bool(all(v for kk, v in s_.items() if v is not None))
    gate_ok = all(v for v in st.values() if v is not None)
    tt = b["team_talent_2025"]
    from config import phase6
    sel6 = phase6.load().get("schedule6", {}).get("targets", {"mean_dev": {}, "cross_cov_fitted": float("nan")})
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
          *(["## Decisions (PR B: steals before each pitch, called bunts, intentional walks)", "",
             "The AI manager decides; its attempt, bunt and intentional-walk rates are the play-by-play's, by game state "
             "(data/ncaa_2025/derived/prb_steals.json, prb_inputs.json). Benchmarks: the 2025 play-by-play's games, except steal attempts "
             "(box scores, league_totals_2025).", "", hdr, sec("dec"), "",
             "Steal attempts and success by observed pitch path (owner decision 2026-10-07: the sample free of selection): every plate "
             "appearance that began with a lead runner able to steal and has a ball or strike, whatever base running came first; an attempt "
             "is any steal or caught stealing during it, counted in the plate appearance it happened in, success that of the first. Computed "
             "the same way on the play-by-play (scripts/build_prb_decisions.py selection_free()) and on the simulated plate appearances. "
             "Tolerance: 3 SE of the real share combined with 3 SE of the simulated mean.", "", hdr, sec("path"), "",
             "Diagnostic, not gated: the first-event sample (plate appearances whose first base-running event is a steal or none; it leaves "
             "out those in which a wild pitch, passed ball, pickoff or balk came first, more often long ones, and the engine draws those "
             "events before the pitches, so it has no such selection). Sim / real attempt per PA: all " +
             f"{m['fe_attempt_per_pa']:.4f} / {fe['attempt_per_pa']['value']:.4f}; " + "; ".join(
                 f"{L}{'+' if L == 8 else ''} pitches {m[f'fe_len{L}_attempt']:.4f} / {fe['by_length'][str(L)]['attempt']:.4f}" for L in range(2, 9)) +
             "; final count " + ", ".join(f"{fc} {m[f'fe_fc{fc}_attempt']:.4f} / {fe['by_final_count'][fc]['attempt']:.4f}" for fc in PATH_COUNTS) + ".", ""]
            if "dec_bunts_per_team_game" in m else []),
          "## Pitcher usage (56-game equivalent)", "", hdr, sec("usage"), "",
          "Top three pitchers' innings, split (sim / real): " + "; ".join(
              f"#{r}: Fri-Sun starts {m[f'ip_rank{r}_fri_sun_starts']:.1f} / {u6[f'ip_rank{r}_fri_sun_starts']['value']:.1f}, "
              f"other starts {m[f'ip_rank{r}_other_starts']:.1f} / {u6[f'ip_rank{r}_other_starts']['value']:.1f}, "
              f"relief {m[f'ip_rank{r}_relief']:.1f} / {u6[f'ip_rank{r}_relief']['value']:.1f}" for r in (1, 2, 3)) + ".", "",
          "## Rows deferred from Phases 2 and 5", "", hdr, sec("deferred"), "",
          "## Team-strength recovery by tier", "",
          "The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn "
          "(tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.", "", hdr, sec("recovery"), "",
          "Fit without parks, simulated against real tier means (diagnostic): " + "; ".join(
              f"{tr} offense {m[f'nopark_o_{tr}']:+.3f} / {tt['tiers_total'][tr]['mean_o']:+.3f}, run prevention {m[f'nopark_d_{tr}']:+.3f} / {tt['tiers_total'][tr]['mean_d']:+.3f}"
              for tr in TIERS) + ".", "",
          "## Schedule selection (diagnostic)", "",
          "Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the "
          "fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: " + "; ".join(
              f"{k_} {m.get(f'sel_{k_}', float('nan')):+.3f} / {sel6['mean_dev'][k_]:+.3f}" for k_ in sorted(sel6["mean_dev"])) +
          f". Cross-tier covariance of opponents' deviations {m['sel_cross_cov']:.4f} / {sel6['cross_cov_fitted']:.4f}. Same-tier pairings are not matched: "
          "in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.", "",
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
          f"- Elite run prevention (Phase 2 rows): best team ERA {lbs['best_team_era']['mean']:.2f} (real 2024-2026 {b['team_leaders_2024_2026']['best_team_era']['lo']:.2f}–{b['team_leaders_2024_2026']['best_team_era']['hi']:.2f}), 50+ IP pitchers with ERA < 2.00 "
          f"{lbs['pitchers_50ip_era_under_2']['mean']:.1f} (5), < 3.00 {lbs['pitchers_50ip_era_under_3']['mean']:.1f} (57), teams with ERA < 4.00 "
          f"{lbs['teams_era_under_4']['mean']:.1f} (2024-2026: 6 / 12 / 12).", ""]
    return "\n".join(md), st
