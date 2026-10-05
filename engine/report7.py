"""Phase 7 realism report: season and world (cancellations, standings, RPI, selection, conference
tournaments, the NCAA tournament), against benchmarks.json season_world_2015_2026.

Gate rows (owner decision 2026-10-05): the RPI formula against the NCAA's published pre-selection RPI;
the cancellation rate; win% spread by tier and the best record; the RPI distribution; the field (at-large
bids by tier, conferences with more than one bid, the worst RPI rank given an at-large bid and the best
left out); seed rates (hosts winning regionals, top-8 national seeds reaching Omaha, CWS slots by tier);
postseason home field; conference tournaments won by the regular-season champion; the NCAA's same-
conference bracketing rule; every Phase 1, 2, 4, 5 and 6 row on the same run. Reported, not gated: games
per team (the sim schedules 56; real teams schedule fewer), the champion's tier, and the watch-item re-checks
on full seasons (top starters' innings, pitchers with 50+ IP, teams under 4.00 ERA).

Tolerance: GATE_SE_MULTIPLE x the combined standard error of the benchmark (as stored: binomial for pooled
rates, season-to-season SD / sqrt(seasons) for per-season means) and of the simulated mean at the number of
seasons run. The best record is a band row: the range of real seasons widened by that multiple of the sim's SE.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from config.phase2 import GATE_SE_MULTIPLE, LEADERBOARD_MIN_IP, SEASON_GAMES, TIERS
from config.phase7 import RPI_MIN_SPEARMAN
from engine.status import Status

ROOT = Path(__file__).resolve().parents[1]
P_G, P_GS, P_OUTS, P_ER = 0, 1, 2, 3          # columns of post["pstats_full"]


def season_extract7(res: dict) -> dict:
    post, lg = res["post"], res["league"]
    tier = {t.tid: t.tier for t in lg.teams}
    out = {}
    sched = sum(res["scheduled_games"].values()) / 2
    out["cancel_rate"] = res["canceled"] / sched
    out["games_per_team"] = sum(res["team_games"].values()) / len(lg.teams)
    # standings: regular season, teams with 30+ decided games
    pct = {t: w / (w + l) for t, (w, l) in post["standings"].items() if w + l >= 30}
    for tr in TIERS:
        out[f"win_pct_sd_{tr}"] = float(np.std([v for t, v in pct.items() if tier[t] == tr], ddof=1))
    out["best_win_pct"] = max(pct.values())
    f = post["field"]
    for k, v in f["rpi_at"].items():
        out[f"rpi_at_{k}"] = v
    for tr in TIERS:
        out[f"mean_rpi_{tr}"] = float(np.mean([v for t, v in f["rpi"].items() if tier[t] == tr]))
    atl = Counter(tier[t] for t in f["at_large"])
    fld = Counter(tier[t] for t in f["auto"] + f["at_large"])
    for tr in TIERS:
        out[f"at_large_{tr}"], out[f"field_{tr}"] = atl.get(tr, 0), fld.get(tr, 0)
    conf_of = {tid: c for tid, (_, c, _) in enumerate(_cfg().teams)}
    bids = Counter(conf_of[t] for t in f["auto"] + f["at_large"] if conf_of[t] != "DI Independent")
    out["conferences_multi_bid"] = sum(1 for v in bids.values() if v > 1)
    in_field = set(f["auto"]) | set(f["at_large"])
    out["worst_rpi_rank_at_large"] = max(f["rank"][t] for t in f["at_large"])
    out["best_rpi_rank_left_out"] = min(r for t, r in f["rank"].items() if t not in in_field)
    n = post["ncaa"]
    out["host_wins_regional"] = sum(x["winner"] == x["host"] for x in n["regionals"])
    out["top8_in_cws"] = sum(t in n["cws"] for t in f["national_seeds"][:8])
    out["top16_in_cws"] = sum(t in n["cws"] for t in f["national_seeds"][:16])
    cws = Counter(tier[t] for t in n["cws"])
    for tr in TIERS:
        out[f"cws_{tr}"] = cws.get(tr, 0)
        out[f"champion_{tr}"] = int(tier[n["champion"]] == tr)
    # postseason home field: hosts at their own park, listed home team at neutral sites
    hosts_reg = {x["host"] for x in n["regionals"]}
    sup_host = {frozenset(s["teams"]): s["host"] for s in n["supers"]}
    hf = {k: [0, 0] for k in ("regional_host", "regional_no_host_listed_home", "super_host", "cws_listed_home")}
    for date, h, a, hr, ar, neutral, stage in post["games"]:
        hw = hr > ar
        if stage == "regional":
            if not neutral:
                host = h if h in hosts_reg else a
                hf["regional_host"][0] += (host == h) == hw; hf["regional_host"][1] += 1
            else:
                hf["regional_no_host_listed_home"][0] += hw; hf["regional_no_host_listed_home"][1] += 1
        elif stage == "super":
            host = sup_host[frozenset((h, a))]
            hf["super_host"][0] += (host == h) == hw; hf["super_host"][1] += 1
        elif stage == "cws":
            hf["cws_listed_home"][0] += hw; hf["cws_listed_home"][1] += 1
    for k, (w, m) in hf.items():
        out[f"hf_{k}_w"], out[f"hf_{k}_n"] = w, m
    cc = [v["champion_is_regular_season_champion"] for v in post["conference"].values()]
    out["conf_champ_rs_w"], out["conf_champ_rs_n"] = sum(cc), len(cc)
    out["same_conf_in_regional"] = post["same_conf_in_regional"]
    # watch-item re-checks on full seasons (regular + postseason), 56-game equivalents as the benchmarks scale
    pf, tgf = post["pstats_full"], post["team_games_full"]
    pls = [x for x in lg.players if x.side == "pit"]
    ids = np.array([x.pid for x in pls])
    s56 = np.array([SEASON_GAMES / tgf[x.team] for x in pls])
    ip56 = pf[ids, P_OUTS] / 3 * s56
    out["full_pitchers_50ip"] = int((ip56 >= LEADERBOARD_MIN_IP).sum())
    team_of = np.array([x.team for x in pls])
    ranks = []
    for t in range(len(lg.teams)):
        ranks.append(np.sort(ip56[team_of == t])[::-1][:3])
    r = np.mean(ranks, axis=0)
    out["full_ip_rank1"], out["full_ip_rank2"], out["full_ip_rank3"] = (float(x) for x in r)
    er = np.bincount(team_of, pf[ids, P_ER], len(lg.teams)); outs = np.bincount(team_of, pf[ids, P_OUTS], len(lg.teams))
    out["full_teams_era_under_4"] = int((27 * er / outs < 4).sum())
    reg_era = []
    tg = res["team_game_rows"]
    for t in range(len(lg.teams)):
        rr = tg[tg[:, 0] == t]
        reg_era.append(27 * rr[:, 6].sum() / rr[:, 7].sum())
    out["reg_teams_era_under_4"] = int((np.array(reg_era) < 4).sum())
    out["postseason_games"] = len(post["games"])
    return out


_CFG = {}


def _cfg():
    if "c" not in _CFG:
        from config import phase2
        _CFG["c"] = phase2.load()
    return _CFG["c"]


def aggregate7(ex: list) -> dict:
    n = len(ex)
    keys = ex[0].keys()
    mean = {k: float(np.mean([e[k] for e in ex])) for k in keys}
    se = {k: float(np.std([e[k] for e in ex], ddof=1) / math.sqrt(n)) if n > 1 else 0.0 for k in keys}
    pooled = {}
    for k in keys:
        if k.endswith("_w"):
            base = k[:-2]
            w, m = sum(e[k] for e in ex), sum(e[base + "_n"] for e in ex)
            p = w / m if m else float("nan")
            # season-to-season SE of the pooled rate (games cluster within seasons)
            per = np.array([e[k] / e[base + "_n"] for e in ex if e[base + "_n"]])
            pooled[base] = {"value": p, "n": m, "se": float(per.std(ddof=1) / math.sqrt(len(per))) if len(per) > 1 else 0.0}
    return {"n_seasons": n, "mean": mean, "se": se, "pooled": pooled,
            "min": {k: float(np.min([e[k] for e in ex])) for k in keys}, "max": {k: float(np.max([e[k] for e in ex])) for k in keys}}


def build_report7(agg: dict, seeds: list, statuses: dict) -> tuple[str, Status]:
    b = json.loads((ROOT / "benchmarks.json").read_text())["season_world_2015_2026"]
    m, se, pooled, n = agg["mean"], agg["se"], agg["pooled"], agg["n_seasons"]
    k = GATE_SE_MULTIPLE
    st, rows = Status(), []

    def row(section, key, label, got, s_sim, real, s_real, nd=3, note="", conf="", gate=True):
        tol = k * math.sqrt(s_sim ** 2 + s_real ** 2)
        ok = bool(abs(got - real) <= tol)
        if gate:
            st[key] = ok
            st.record(key, got, s_sim)
        rows.append((section, f"| {label} | {got:.{nd}f} | {real:.{nd}f} | ±{tol:.{nd}f} | {conf} | {'yes' if gate else 'report'} | "
                              f"{('pass' if ok else 'FAIL') if gate else ('in range' if ok else 'outside')} | {note} |"))

    def rate(key, label, bench, sim_key, section, note=""):
        p = pooled[sim_key]
        row(section, key, label, p["value"], p["se"], bench["value"], bench["se"], 3, note, bench.get("conf", ""))

    # RPI formula (data check, no sim)
    rc = b["rpi_formula_check_2026"]
    ok = rc["spearman"] >= RPI_MIN_SPEARMAN
    st["p7_rpi_formula"] = ok
    rows.append(("rpi", f"| RPI formula vs NCAA published (2026, rank correlation) | {rc['spearman']:.5f} | ≥ {RPI_MIN_SPEARMAN} | — | {rc['conf']} | yes | "
                        f"{'pass' if ok else 'FAIL'} | {rc['exact_rank']}/{rc['teams']} ranks exact, {rc['within_3']} within 3; without site weighting {rc['spearman_unweighted']:.4f} |"))
    g = b["games"]
    row("season", "p7_cancel_rate", "Regular-season games canceled (share)", m["cancel_rate"], se["cancel_rate"], g["cancel_rate"]["value"], g["cancel_rate"]["se"], 4,
        "", g["conf"])
    played = np.mean(list(g["played_per_team"].values()))
    rows.append(("season", f"| Regular-season games per team | {m['games_per_team']:.2f} | {played:.2f} | — | {g['conf']} | report | — | "
                           f"real teams schedule {np.mean(list(g['scheduled_per_team'].values())):.1f} (the sim 56, the NCAA maximum; no shortened schedules by owner decision) "
                           f"and lose {np.mean(list(g['canceled_per_team'].values())):.2f} to cancellations |"))
    s = b["standings"]
    for tr in TIERS:
        x = s["win_pct_sd_by_tier"][tr]
        row("season", f"p7_win_pct_sd_{tr}", f"Win% SD across teams, {tr}", m[f"win_pct_sd_{tr}"], se[f"win_pct_sd_{tr}"], x["value"], x["se"], 4, "", s["conf"])
    bw = s["best_win_pct"]
    lo, hi = bw["range"]
    pad = k * se["best_win_pct"]
    ok = bool(lo - pad <= m["best_win_pct"] <= hi + pad)
    st["p7_best_win_pct"] = ok
    st.record("p7_best_win_pct", m["best_win_pct"], se["best_win_pct"])
    rows.append(("season", f"| Best regular-season win% | {m['best_win_pct']:.3f} (seasons {agg['min']['best_win_pct']:.3f}–{agg['max']['best_win_pct']:.3f}) | "
                           f"{lo:.3f}–{hi:.3f} | ±{pad:.3f} | {s['conf']} | yes | {'pass' if ok else 'FAIL'} | band of real seasons |"))
    rp = b["rpi"]
    nr = len(b["field"]["worst_rpi_rank_at_large"]["by_season"])
    for kk in ("1", "16", "32", "64"):
        x = rp["rpi_at_rank"][kk]
        row("rpi", f"p7_rpi_at_{kk}", f"RPI of the team ranked {kk}", m[f"rpi_at_{kk}"], se[f"rpi_at_{kk}"], x["mean"], x["sd"] / math.sqrt(nr), 4, "", rp["conf"])
    for tr in TIERS:
        x = rp["mean_rpi_by_tier"][tr]
        row("rpi", f"p7_mean_rpi_{tr}", f"Mean RPI, {tr}", m[f"mean_rpi_{tr}"], se[f"mean_rpi_{tr}"], x["mean"], x["sd"] / math.sqrt(nr), 4, "", rp["conf"])
    fb = b["field"]
    ns = len(fb["by_season"]["at_large"])
    for tr in TIERS:
        x = fb["at_large_by_tier"][tr]
        row("field", f"p7_at_large_{tr}", f"At-large bids, {tr}", m[f"at_large_{tr}"], se[f"at_large_{tr}"], x["mean"], x["sd"] / math.sqrt(ns), 2, "", fb["conf"])
    x = fb["conferences_multi_bid"]
    row("field", "p7_conferences_multi_bid", "Conferences with more than one bid", m["conferences_multi_bid"], se["conferences_multi_bid"], x["mean"], x["sd"] / math.sqrt(ns), 2, "", fb["conf"])
    for key, lab in (("worst_rpi_rank_at_large", "Worst RPI rank given an at-large bid"), ("best_rpi_rank_left_out", "Best RPI rank left out")):
        x = fb[key]
        row("field", f"p7_{key}", lab, m[key], se[key], x["mean"], x["sd"] / math.sqrt(nr), 1, "", fb["conf"])
    sd = b["seeds"]
    x = sd["host_wins_regional"]
    row("seeds", "p7_host_wins_regional", "Regional hosts winning their regional (share)", m["host_wins_regional"] / 16, se["host_wins_regional"] / 16, x["value"], x["se"], 3, "", sd["conf"])
    x = sd["top8_national_seeds_in_cws"]
    row("seeds", "p7_top8_in_cws", "Top-8 national seeds reaching Omaha (of 8)", m["top8_in_cws"], se["top8_in_cws"], x["value"], x["se"], 2, "", sd["conf"])
    x = sd["top16_national_seeds_in_cws"]
    row("seeds", "p7_top16_in_cws", "National seeds among the 8 CWS teams (2018 on)", m["top16_in_cws"], se["top16_in_cws"], x["value"], x["se"], 2, "", sd["conf"])
    for tr in TIERS:
        x = sd["cws_share_by_tier"][tr]
        row("seeds", f"p7_cws_{tr}", f"CWS slots, {tr} (share)", m[f"cws_{tr}"] / 8, se[f"cws_{tr}"] / 8, x["value"], x["se"], 3, "", sd["conf"], gate=tr != "low")
    champ = Counter(sd["champion_tier_by_season"].values())
    rows.append(("seeds", "| Champion's tier (P4 / mid / low) | " + " / ".join(f"{m[f'champion_{tr}']:.2f}" for tr in TIERS) + " | "
                          + " / ".join(f"{champ.get(tr, 0) / len(sd['champion_tier_by_season']):.2f}" for tr in TIERS) + f" | — | {sd['conf']} | report | — | 2015-2025 |"))
    hf = b["home_field"]
    for kk, lab in (("regional_host", "Regional host at its park (win%)"), ("regional_no_host_listed_home", "Regional games without the host: listed home (win%)"),
                    ("super_host", "Super regional host at its park (win%)"), ("cws_listed_home", "CWS (neutral): listed home (win%)")):
        rate(f"p7_hf_{kk}", lab, {**hf[kk], "conf": hf["conf"]}, f"hf_{kk}", "home")
    ct = b["conference_tournaments"]["won_by_regular_season_champion"]
    rate("p7_conf_champ_rs", "Conference tournaments won by a regular-season (co-)champion", ct, "conf_champ_rs", "conf")
    ok = m["same_conf_in_regional"] == 0
    st["p7_same_conf_rule"] = bool(ok)
    rows.append(("conf", f"| Regionals with two teams of one conference (per season) | {m['same_conf_in_regional']:.2f} | 0 | — | A | yes | {'pass' if ok else 'FAIL'} | NCAA bracketing principles (2025 manual, Section 2-3) |"))
    # earlier phases on the same run
    for ph in ("phase2", "phase4", "phase5", "phase6"):
        s_ = statuses[ph]
        st[f"{ph}_gate"] = all(v for v in s_.values() if v is not None)
    # watch-item re-checks (full seasons)
    u6 = json.loads((ROOT / "benchmarks.json").read_text())["usage_phase6_2025"]
    lb = json.loads((ROOT / "benchmarks.json").read_text())["leaderboards_2025"]["pitchers_50ip"]
    tl = json.loads((ROOT / "benchmarks.json").read_text())["team_leaders_2024_2026"]["teams_era_under_4"]
    watch = [f"- Top starters' innings, full seasons (regular + postseason, 56-game equivalent): #1 {m['full_ip_rank1']:.1f}, #2 {m['full_ip_rank2']:.1f}, "
             f"#3 {m['full_ip_rank3']:.1f} (real {u6['ip_rank1']['value']} / {u6['ip_rank2']['value']} ± {u6['ip_rank2']['tol']} / {u6['ip_rank3']['value']}); "
             f"pitchers with 50+ IP {m['full_pitchers_50ip']:.0f} (real {lb['value_56g']}; regular season only, Phase 6 report).",
             f"- Teams under 4.00 ERA, full seasons {m['full_teams_era_under_4']:.1f}, regular season {m['reg_teams_era_under_4']:.1f} "
             f"(2024-2026: {tl['lo']:.0f}–{tl['hi']:.0f}, real seasons include the postseason)."]
    hdr = "| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |\n|---|---|---|---|---|---|---|---|"
    sec = lambda name: "\n".join(r for s_, r in rows if s_ == name)
    gate_ok = all(v for v in st.values() if v is not None)
    md = "\n".join([
        "# Phase 7 realism report: season and world", "",
        f"{n} simulated seasons, seeds {seeds[0]}–{seeds[-1]}, with cancellations, conference tournaments, selection and the NCAA tournament "
        f"(config.phase7.FEATURES). Generated {dt.date.today().isoformat()}. Tolerances: {k} × the combined standard error of the benchmark and of the "
        f"simulated mean at {n} seasons. Mean postseason games per season {m['postseason_games']:.0f}.", "",
        f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
        "Phase 1-6 rows on the same run (regular season): " + ", ".join(f"{ph} **{'pass' if st[f'{ph}_gate'] else 'FAIL'}**" for ph in ("phase2", "phase4", "phase5", "phase6")) + ".", "",
        "## RPI", "", hdr, sec("rpi"), "",
        "## Season and standings", "", hdr, sec("season"), "",
        "## The field", "", hdr, sec("field"), "",
        "## Seeds and results", "", hdr, sec("seeds"), "",
        "## Postseason home field", "", hdr, sec("home"), "",
        "## Conference tournaments and bracketing", "", hdr, sec("conf"), "",
        "## Watch items (re-checked, not gated)", "", *watch, ""])
    return md, st
