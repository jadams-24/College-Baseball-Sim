"""Phase 7 realism report: season and world (cancellations, standings, RPI, selection, conference
tournaments, the NCAA tournament), against benchmarks.json season_world_2015_2026.

Gate rows (owner decision 2026-10-05): the RPI formula against the NCAA's published pre-selection RPI;
the cancellation rate; win% spread by tier and the best record; the RPI distribution; the field (at-large
bids by tier, conferences with more than one bid, the worst RPI rank given an at-large bid and the best
left out); seed rates (hosts winning regionals, top-8 national seeds reaching Omaha, CWS slots by tier);
postseason home field; conference tournaments won by the regular-season champion; the NCAA's same-
conference bracketing rule; every Phase 1, 2, 4, 5 and 6 row on the same run. Reported, not gated: games
per team (the sim schedules 56; real teams schedule fewer), the champion's tier, and the watch-item re-checks
on full seasons (top starters' innings, pitchers with 50+ IP, teams with an ERA under four).

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
    sg = np.array([res["scheduled_games"].get(t.tid, 0) for t in lg.teams])
    out["scheduled_mean"], out["scheduled_share_56"], out["scheduled_p10"] = float(sg.mean()), float((sg >= 56).mean()), float(np.percentile(sg, 10))
    # P4 against mid-tier, nonconference regular season: P4 win%, run margin and its SD
    conf_of = {tid: c for tid, (_, c, _) in enumerate(_cfg().teams)}
    marg = [(hs - as_) if tier[h] == "p4" else (as_ - hs) for h, a, hs, as_, *_ in res["games"]
            if {tier[h], tier[a]} == {"p4", "mid"} and conf_of[h] != conf_of[a]]
    marg = np.array(marg, float)
    out["p4mid_p4_win"], out["p4mid_margin"], out["p4mid_margin_sd"] = float((marg > 0).mean()), float(marg.mean()), float(marg.std(ddof=1))
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
    rseed = {t: i for x in n["regionals"] for i, t in enumerate(x["teams"])}      # regional seed - 1
    sup_host = {frozenset(s["teams"]): s["host"] for s in n["supers"]}
    hf = {k: [0, 0] for k in ("regional_host", "regional_no_host_better_seed", "super_host", "cws_listed_home")}
    for date, h, a, hr, ar, neutral, stage in post["games"]:
        hw = hr > ar
        if stage == "regional":
            if not neutral:
                host = h if h in hosts_reg else a
                hf["regional_host"][0] += (host == h) == hw; hf["regional_host"][1] += 1
            else:
                better_home = rseed[h] < rseed[a]
                hf["regional_no_host_better_seed"][0] += better_home == hw; hf["regional_no_host_better_seed"][1] += 1
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
    # unearned runs, full seasons (the NCAA.com team ERA page counts every game of the season, postseason included):
    # earned share overall and for the 50 teams with the lowest ERA, unearned runs per game for those 50
    T = len(lg.teams)
    pl_ = post["post_lines"]
    ra = np.bincount(tg[:, 0].astype(int), tg[:, 2], T) + np.bincount(pl_[:, 0].astype(int), pl_[:, 3], T)
    erx = np.bincount(tg[:, 0].astype(int), tg[:, 6], T) + np.bincount(pl_[:, 0].astype(int), pl_[:, 1], T)
    ipo = np.bincount(tg[:, 0].astype(int), tg[:, 7], T) + np.bincount(pl_[:, 0].astype(int), pl_[:, 2], T)
    gms = np.array([tgf[t] for t in range(T)], float)
    top50 = np.argsort(27 * erx / ipo)[:50]
    out["earned_share_all"] = float(erx.sum() / ra.sum())
    out["earned_share_top50"] = float(erx[top50].sum() / ra[top50].sum())
    out["unearned_per_game_top50"] = float(((ra - erx)[top50] / gms[top50]).mean())
    out["ra_per_game_top50"] = float((ra[top50] / gms[top50]).mean())
    # pitching against fielding (ERA watch item, owner request 2026-10-05): the rows of scripts/build_phase7_era_fielding.py
    # on the same full-season basis (fielding percentage is not computed: the engine does not count assists)
    err = np.bincount(tg[:, 0].astype(int), tg[:, 8], T) + np.bincount(pl_[:, 0].astype(int), pl_[:, 7], T)
    for k, v in era_fielding_measures(27 * erx / ipo, ra / gms, err / gms, np.full(T, np.nan), erx / ra).items():
        if k != "corr_era_fpct":
            out[f"ef_{k}"] = v
    out["postseason_games"] = len(post["games"])
    return out


def era_fielding_measures(era, ra_g, e_g, fpct, es) -> dict:
    """Team pitching against fielding, the same rows for real teams (scripts/build_phase7_era_fielding.py) and sim teams."""
    era, ra_g, e_g, fpct, es = map(np.asarray, (era, ra_g, e_g, fpct, es))
    import pandas as pd
    _S = pd.Series
    rc = lambda a, b: float(_S(a).corr(_S(b)))
    by_ra, by_era = np.argsort(ra_g)[:50], np.argsort(era)[:50]
    return {"corr_era_errors_pg": rc(era, e_g), "corr_era_fpct": rc(era, fpct), "corr_ra_errors_pg": rc(ra_g, e_g),
            "rank_corr_era_errors_pg": rc(_S(era).rank(), _S(e_g).rank()),
            "errors_pg_all": float(e_g.mean()), "errors_pg_top50_ra": float(e_g[by_ra].mean()), "errors_pg_top50_era": float(e_g[by_era].mean()),
            "earned_share_top50_ra": float(np.mean(es[by_ra])), "earned_share_top50_era": float(np.mean(es[by_era])), "earned_share_all": float(np.mean(es))}


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
    cur = b["current"]["rows"]
    cconf = b["current"]["conf"]

    def crow(section, key, label, sim_key, bkey, nd=3, gate=True, note=""):
        """Current-map row (2025-2026): tolerance from the sim's SE and the season-to-season SD of a two-season mean."""
        x = cur[bkey]
        s_real = (x["season_sd"] or 0.0) / math.sqrt(len(x["by_season"]))
        bs = " / ".join(f"{v:.{nd}f}" for v in x["by_season"].values())
        row(section, key, label, m[sim_key], se[sim_key], x["value"], s_real, nd, f"2025 / 2026: {bs}; season SD {x['season_sd']}. {note}", cconf, gate)
    g = b["games"]
    row("season", "p7_cancel_rate", "Regular-season games canceled (share)", m["cancel_rate"], se["cancel_rate"], g["cancel_rate"]["value"], g["cancel_rate"]["se"], 4,
        "", g["conf"])
    pm = g["played_mean"]
    row("season", "p7_games_per_team", "Regular-season games played per team", m["games_per_team"], se["games_per_team"], pm["value"], pm["season_sd"] / math.sqrt(2), 2,
        f"2025 / 2026: {g['played_per_team']['2025']:.2f} / {g['played_per_team']['2026']:.2f}", g["conf"])
    sdist = g["scheduled_distribution"]
    rows.append(("season", f"| Scheduled games per team: mean / share at 56 / 10th percentile | {m['scheduled_mean']:.2f} / {m['scheduled_share_56']:.3f} / {m['scheduled_p10']:.1f} | "
                           f"{sdist['mean']:.2f} / {sdist['share_56']:.3f} / 50 | — | {g['conf']} | report | — | real targets above 56 ({sdist['share_above_56']:.3f}) are capped at the 56-game frame and "
                           f"below 42 ({sdist['share_below_42']:.3f}) at its 42 weekend games |"))
    s = b["standings"]
    for tr in TIERS:
        crow("season", f"p7_win_pct_sd_{tr}", f"Win% SD across teams, {tr}", f"win_pct_sd_{tr}", f"win_pct_sd_by_tier/{tr}", 4)
    bw = s["best_win_pct"]
    lo, hi = bw["range"]
    pad = k * se["best_win_pct"]
    ok = bool(lo - pad <= m["best_win_pct"] <= hi + pad)
    st["p7_best_win_pct"] = ok
    st.record("p7_best_win_pct", m["best_win_pct"], se["best_win_pct"])
    rows.append(("season", f"| Best regular-season win% | {m['best_win_pct']:.3f} (seasons {agg['min']['best_win_pct']:.3f}–{agg['max']['best_win_pct']:.3f}) | "
                           f"{lo:.3f}–{hi:.3f} | ±{pad:.3f} | {s['conf']} | yes | {'pass' if ok else 'FAIL'} | band of real seasons 2017-2025 |"))
    for kk in ("1", "16", "32", "64"):
        # ranks 32 and 64: watch item "offense extremes compressed" (owner decisions 2026-10-05 and 2026-10-07): the
        # RPI of the middle of the table runs high because the sim's records spread less from game to game
        watch = kk in ("32", "64")
        crow("rpi", f"p7_rpi_at_{kk}", f"RPI of the team ranked {kk}", f"rpi_at_{kk}", f"rpi_at_rank/{kk}", 4, gate=not watch,
             note="watch item 'offense extremes compressed'" if watch else "")
    for tr in TIERS:
        crow("rpi", f"p7_mean_rpi_{tr}", f"Mean RPI, {tr}", f"mean_rpi_{tr}", f"mean_rpi_by_tier/{tr}", 4)
    for tr in TIERS:
        crow("field", f"p7_at_large_{tr}", f"At-large bids, {tr}", f"at_large_{tr}", f"at_large_by_tier/{tr}", 2, gate=tr != "low",
             note="no low-tier at-large bid in 2022-2026: reported" if tr == "low" else "")
    crow("field", "p7_conferences_multi_bid", "Conferences with more than one bid", "conferences_multi_bid", "conferences_multi_bid", 2)
    crow("field", "p7_worst_rpi_rank_at_large", "Worst RPI rank given an at-large bid", "worst_rpi_rank_at_large", "worst_rpi_rank_at_large", 1)
    crow("field", "p7_best_rpi_rank_left_out", "Best RPI rank left out", "best_rpi_rank_left_out", "best_rpi_rank_left_out", 1)
    # P4 against mid-tier, nonconference regular season (the check behind the field rows; not gated)
    for kk, lab, nd in (("p4_win", "P4 vs mid nonconference: P4 win%", 3), ("margin", "P4 vs mid nonconference: run margin", 2),
                        ("margin_sd", "P4 vs mid nonconference: run margin SD", 2)):
        crow("field", f"p7_p4mid_{kk}", lab, f"p4mid_{kk}", f"p4_vs_mid/{kk}", nd, gate=False,
             note="watch item 'offense extremes compressed'" if kk == "margin_sd" else "")
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
    for kk, lab in (("regional_host", "Regional host at its park (win%)"), ("regional_no_host_better_seed", "Regional games without the host: better seed (win%)"),
                    ("super_host", "Super regional host at its park (win%)")):
        rate(f"p7_hf_{kk}", lab, {**hf[kk], "conf": hf["conf"]}, f"hf_{kk}", "home")
    x, pc = hf["cws_listed_home"], pooled["hf_cws_listed_home"]
    row("home", "p7_hf_cws_listed_home", "CWS (neutral): listed home (win%)", pc["value"], pc["se"], x["value"], x["se"], 3,
        "the sim lists the better seed as home; the feed's listing convention is not known", hf["conf"], gate=False)
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
    # upset rates: with the real game-to-game spread (P4 vs mid margin SD), a per-game win probability p becomes
    # Phi(Phi^-1(p) * sd_sim / sd_real) (normal margin model)
    ratio = m["p4mid_margin_sd"] / cur["p4_vs_mid/margin_sd"]["value"]
    from statistics import NormalDist
    nd_ = NormalDist()
    adj = lambda q: nd_.cdf(nd_.inv_cdf(q) * ratio)
    hb, hs_ = pooled["hf_regional_no_host_better_seed"]["value"], pooled["hf_regional_host"]["value"]
    upset = (f"- Game-to-game spread and postseason upsets (watch item 'offense extremes compressed'): P4 vs mid nonconference margin SD "
             f"{m['p4mid_margin_sd']:.2f} against {cur['p4_vs_mid/margin_sd']['value']:.2f} real (2025-2026), ratio {ratio:.3f}. With the real spread "
             f"the better seed's win% in regional games without the host would be about {adj(hb):.3f} instead of {hb:.3f}, and the host's {adj(hs_):.3f} "
             f"instead of {hs_:.3f} (normal margin model: an upset rate higher by {100 * (hb - adj(hb)):.1f} and {100 * (hs_ - adj(hs_)):.1f} points per game).")
    u6 = json.loads((ROOT / "benchmarks.json").read_text())["usage_phase6_2025"]
    lb = json.loads((ROOT / "benchmarks.json").read_text())["leaderboards_2025"]["pitchers_50ip"]
    tl = json.loads((ROOT / "benchmarks.json").read_text())["team_leaders_2024_2026"]["teams_era_under_4"]
    watch = [f"- Top starters' innings, full seasons (regular + postseason, 56-game equivalent): #1 {m['full_ip_rank1']:.1f}, #2 {m['full_ip_rank2']:.1f}, "
             f"#3 {m['full_ip_rank3']:.1f} (real {u6['ip_rank1']['value']} / {u6['ip_rank2']['value']} ± {u6['ip_rank2']['tol']} / {u6['ip_rank3']['value']}); "
             f"pitchers with 50+ IP {m['full_pitchers_50ip']:.0f} (real {lb['value_56g']}; regular season only, Phase 6 report).",
             f"- Teams under 4.00 ERA, full seasons {m['full_teams_era_under_4']:.1f}, regular season {m['reg_teams_era_under_4']:.1f} "
             f"(2024-2026: {tl['lo']:.0f}–{tl['hi']:.0f}). Same definition on both sides: the NCAA.com team ERA page counts every game of a "
             f"season, conference tournaments and the NCAA tournament included (2025 data year: Northeastern 60 games, Coastal Carolina 69); the "
             f"sim's full season is its regular season plus its postseason (it has no non-Division I games).",
             f"- Unearned runs, full seasons: earned share of runs allowed {m['earned_share_all']:.3f} (real .882, WMT play-by-play 2025); the 50 lowest-ERA "
             f"teams {m['earned_share_top50']:.3f} (real .869 / .866 / .867 in 2024 / 2025 / 2026, NCAA.com team ERA page), unearned runs per game for "
             f"them {m['unearned_per_game_top50']:.2f} (real .67 / .65 / .65), runs allowed per game {m['ra_per_game_top50']:.2f} (real 5.05 / 4.80 / 4.81).",
             upset]
    ef = b.get("era_fielding")
    if ef:
        watch.append(
            f"- Pitching against fielding, full seasons (lead from the unearned-run check, owner request 2026-10-05): correlation across teams of "
            f"ERA with errors per game {m['ef_corr_era_errors_pg']:.3f} (real 2025 {ef['corr_era_errors_pg']:.3f}; with fielding % {ef['corr_era_fpct']:.3f}), "
            f"of runs allowed per game with errors per game {m['ef_corr_ra_errors_pg']:.3f} (real {ef['corr_ra_errors_pg']:.3f}). Errors per game: all teams "
            f"{m['ef_errors_pg_all']:.3f} (real {ef['errors_pg_all']:.3f}), the 50 best by runs allowed per game {m['ef_errors_pg_top50_ra']:.3f} (real "
            f"{ef['errors_pg_top50_ra']:.3f}), the 50 best by ERA {m['ef_errors_pg_top50_era']:.3f} (real {ef['errors_pg_top50_era']:.3f}). Earned share "
            f"(mean of team ER/R): all {m['ef_earned_share_all']:.3f} (real {ef['earned_share_all']:.3f}), the 50 best by ERA "
            f"{m['ef_earned_share_top50_era']:.3f} (real {ef['earned_share_top50_era']:.3f}). Real: NCAA.com team pages, 2025, every game; "
            f"scripts/build_phase7_era_fielding.py.")
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
