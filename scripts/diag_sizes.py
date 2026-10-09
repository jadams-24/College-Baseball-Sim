"""Real-data sizes for the "offense extremes compressed" watch item (plans/combined_report_2026-10-06.md, section 1).

Measurement only: nothing here changes a benchmark, the engine or its config. Owner: "Report sizes only; no fixes yet."

  1. Non-D1 opponents in the scoreboard rows (run rule, 15+ bin), the qualified OBP p10 and the team R/G SD.
  2. Candidate 10, fielding independent of pitching: noise in team ERA and errors per game, the true correlation, the true
     error-rate variance left after run prevention, unearned shares.
  3. Candidate 11, starter day-to-day form: a start-level variance component in runs, beyond season talent, opponent
     and the game's shared conditions.
  4. Candidate 12, errors clustering into big innings.

Items 3 and 4 are put on one scale: the quasi-Poisson dispersion of runs per team-game around the scoreboard fit
(real 2.6185, sim 2.224, fit without parks). A source adding variance V_c (runs^2) to a team-game with mean mu adds
V_c / mu to that team-game's Pearson term, so its dispersion share is dphi_c = mean(V_c / mu) and its share of the
missing variance is dphi_c / (2.6185 - 2.224).

Reads data/ (committed), benchmarks.json and reports/phase*.json (sim values for comparison). Writes
reports/diagnosis_sizes.md and reports/diagnosis_sizes.json.

    python3 scripts/diag_sizes.py            # everything
    python3 scripts/diag_sizes.py --only 1   # one item (results of the others are read back from the json if present)
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
P = ROOT / "data/ncaa_2025/pbp/parsed"
OUT_MD = ROOT / "reports/diagnosis_sizes.md"
OUT_JSON = ROOT / "reports/diagnosis_sizes.json"
RNG_SEED = 20261006
BOOT = 400

# sim values (40-season reports of 2026-10-05: reports/phase2.md, phase6.md, phase7.md)
SIM = {"run_rule": 0.1201, "bin15": 0.0533, "obp_p10": 0.3242, "team_rg_sd": 1.032, "phi": 2.224, "rcorr": 0.0463,
       "corr_era_e": 0.727, "corr_ra_e": 0.801}
REAL_PHI, SIM_PHI = 2.6185, 2.224
# round 2 (scripts/diag_tto_mopup.py) appends to the same outputs; a rerun of this script keeps its parts
ROUND2_KEYS = ("item5_tto", "item6_mopup", "running_total", "_meta_round2")
ROUND2_MARKER = "<!-- round2: scripts/diag_tto_mopup.py -->"


def d1_names() -> set:
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    # teams_2025.csv names New Orleans "LSU New Orleans" (scripts/wmt_teams.py NAME_ALIAS); the scoreboard calls it "New Orleans"
    return set(t.team) | {"New Orleans"}


def scoreboard() -> pd.DataFrame:
    sb = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    sb = sb[(sb.state == "final") & sb.home_score.notna() & sb.away_score.notna()].drop_duplicates("url").reset_index(drop=True)
    D1 = d1_names()
    sb["home_isd1"] = sb.home.isin(D1); sb["away_isd1"] = sb.away.isin(D1)
    return sb


def r4(x, n=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


# ----------------------------------------------------------------------------------------------------------------------
# 1. Non-D1 opponents
# ----------------------------------------------------------------------------------------------------------------------

def bin15(sb: pd.DataFrame) -> dict:
    """P(15+ runs) per D1 team-game, as scripts/build_run_histogram.py counts it (D1 sides only), with a game-cluster SE."""
    c = np.zeros(len(sb)); n = np.zeros(len(sb))
    for s in ("home", "away"):
        d1 = sb[f"{s}_isd1"].values
        c += d1 * (sb[f"{s}_score"].values >= 15); n += d1
    p = c.sum() / n.sum()
    # ratio estimator, clustered by game
    G = len(sb); e = c - p * n
    se = float(np.sqrt((e ** 2).sum() * G / (G - 1)) / n.sum())
    return {"value": p, "se": se, "n_team_games": int(n.sum()), "n_games": int(G), "count": int(c.sum())}


def product_rr(sb: pd.DataFrame, wmt: pd.DataFrame) -> dict:
    margin = (sb.home_score - sb.away_score).abs()
    pb = float((margin >= 10).mean()); N = len(sb)
    m2 = (wmt.home_score - wmt.away_score).abs()
    big = wmt[m2 >= 10]
    pe = float((big.innings < 9).mean()); nb = len(big)
    var = pe ** 2 * pb * (1 - pb) / N + pb ** 2 * pe * (1 - pe) / nb
    return {"value": pb * pe, "se": float(np.sqrt(var)), "p_margin_10plus": pb, "n_scoreboard_games": int(N),
            "p_early_given_10plus_wmt": pe, "n_wmt_10plus": int(nb), "n_wmt_games": int(len(wmt))}


def item1() -> dict:
    sb = scoreboard()
    both = sb.home_isd1 & sb.away_isd1
    nond1 = sb[~both]
    out = {"n_scoreboard_final_games": int(len(sb)), "n_d1_vs_d1": int(both.sum()), "n_with_non_d1": int((~both).sum()),
           "n_non_d1_home": int((~sb.home_isd1).sum()), "n_non_d1_away": int((~sb.away_isd1).sum())}
    # those games: margins and D1 side runs
    m_nd = (nond1.home_score - nond1.away_score).abs()
    d1_runs = np.where(nond1.home_isd1, nond1.home_score, nond1.away_score)
    nd_runs = np.where(nond1.home_isd1, nond1.away_score, nond1.home_score)
    out["non_d1_games"] = {"share_margin_10plus": float((m_nd >= 10).mean()), "d1_side_runs_mean": float(d1_runs.mean()),
                           "non_d1_side_runs_mean": float(nd_runs.mean()), "d1_side_share_15plus": float((d1_runs >= 15).mean()),
                           "d1_side_win_pct": float(((d1_runs > nd_runs)).mean())}
    # how the earlier count of 141 arose: the names in teams_2025.csv (used by the team-strength fit) miss New Orleans
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    T = set(t.team)
    out["n_games_not_both_in_teams_2025_names"] = int((~(sb.home.isin(T) & sb.away.isin(T))).sum())
    out["new_orleans_games"] = int(((sb.home == "New Orleans") | (sb.away == "New Orleans")).sum())
    out["new_orleans_d1_games"] = int((((sb.home == "New Orleans") | (sb.away == "New Orleans")) & both).sum())

    # cross-check against WarrenNolan's D1 flags (same date, D1 team's slug)
    wn = pd.read_csv(ROOT / "data/ncaa_2025/warrennolan/games_2025.csv")
    nm = pd.read_csv(ROOT / "data/ncaa_2026/team_name_map.csv")
    slug = dict(zip(nm.ncaa_name, nm.warrennolan_slug)); slug.update({"New Orleans": "New-Orleans", "Purdue Fort Wayne": "Purdue-Fort-Wayne"})
    wnf = wn[wn.status == "final"]
    by = {}
    for r in wnf.itertuples(index=False):
        for s_, o_, od in ((r.home_slug, r.away, r.away_d1), (r.away_slug, r.home, r.home_d1)):
            if isinstance(s_, str):
                by.setdefault((r.date, s_), []).append(bool(od))
    agree = found = 0
    for r in nond1.itertuples(index=False):
        d1team = r.home if r.home_isd1 else r.away
        flags = by.get((r.date, slug.get(d1team)), [])
        if flags:
            found += 1
            agree += int(any(not f for f in flags))
    wn_nd = wnf[~(wnf.home_d1 & wnf.away_d1)]
    wn_nd_in_d1list = sorted(set(wn_nd.loc[~wn_nd.home_d1, "home"]) | set(wn_nd.loc[~wn_nd.away_d1, "away"]))
    D1slugs = {slug.get(x) for x in d1_names()}
    out["warrennolan_check"] = {"scoreboard_non_d1_games_found_in_wn": found, "of_which_wn_flags_opponent_non_d1": agree,
                                "wn_final_games_with_non_d1_flag": int(len(wn_nd)),
                                "wn_non_d1_names_that_are_d1_2025": [x for x in wn_nd_in_d1list if x.replace(" ", "-") in D1slugs]}

    # (b) the two rows, old (all 8,079 games) and D1-vs-D1
    sg = pd.read_csv(P / "schedule_games_2025.csv")
    fin = sg[sg.innings.notna() & (sg.innings > 0)]
    fin_d1 = fin[(fin.home_is_d1 == 1) & (fin.away_is_d1 == 1) & fin.game_date.str.startswith("2025")]
    rr_old = product_rr(sb, fin); rr_new = product_rr(sb[both], fin_d1)
    b_old = bin15(sb); b_new = bin15(sb[both])
    # direct estimate: WarrenNolan records innings for every final (blank = 9), D1-vs-D1
    wd = wnf[wnf.home_d1 & wnf.away_d1].copy()
    wd["inn"] = wd.innings.fillna(9)
    wm = (wd.home_score - wd.away_score).abs()
    rrw = ((wd.inn < 9) & (wm >= 10)); p_w = float(rrw.mean())
    big = wd[wm >= 10]
    # the same on the WarrenNolan games matched to the scoreboard's D1-vs-D1 finals (date, both teams, both scores)
    keys = {(r.date, frozenset([slug.get(r.home), slug.get(r.away)]), frozenset([int(r.home_score), int(r.away_score)])) for r in sb[both].itertuples()}
    wd["in_sb"] = [(r.date, frozenset([r.home_slug, r.away_slug]), frozenset([int(r.home_score), int(r.away_score)])) in keys for r in wd.itertuples()]
    ws = wd[wd.in_sb]; wsm = (ws.home_score - ws.away_score).abs(); ps = float(((ws.inn < 9) & (wsm >= 10)).mean())
    # tier mix of the 10-run games: P(ended early | margin >= 10) by the pair's tiers, WarrenNolan against the WMT sample
    tier_of = {slug.get(k): v for k, v in zip(pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv").team, pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv").tier)}
    tier_of["New-Orleans"] = "low"
    def pair(a, b):
        ta, tb = tier_of.get(a), tier_of.get(b)
        return "|".join(sorted([str(ta), str(tb)]))
    big = big.assign(pair=[pair(a, b) for a, b in zip(big.home_slug, big.away_slug)], early=(big.inn < 9))
    id2slug = {k: slug.get(v) for k, v in zip(pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv").ncaa_team_id, pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv").team)}
    wbig = fin_d1[(fin_d1.home_score - fin_d1.away_score).abs() >= 10]
    wbig = wbig.assign(pair=[pair(id2slug.get(a), id2slug.get(b)) for a, b in zip(wbig.home_team_id, wbig.away_team_id)], early=(wbig.innings < 9))
    by_pair = {}
    for k in sorted(set(big.pair)):
        a, b_ = big[big.pair == k], wbig[wbig.pair == k]
        by_pair[k] = {"wn_n": int(len(a)), "wn_p_early": float(a.early.mean()), "wmt_n": int(len(b_)), "wmt_p_early": float(b_.early.mean()) if len(b_) else None}
    conf_t = wd.event.notna()
    # the WarrenNolan 10-run games that are not in the WMT schedules: P(ended early) there against WMT's
    wkeys = {(r.game_date, frozenset([id2slug.get(r.home_team_id), id2slug.get(r.away_team_id)]), frozenset([int(r.home_score), int(r.away_score)]))
             for r in fin_d1.itertuples()}
    in_wmt = np.array([(r.date, frozenset([r.home_slug, r.away_slug]), frozenset([int(r.home_score), int(r.away_score)])) in wkeys for r in big.itertuples()])
    pn, nn = float(big.early[~in_wmt].mean()), int((~in_wmt).sum())
    pw, nw = float(big.early[in_wmt].mean()), int(in_wmt.sum())
    not_wmt = {"p_early_not_in_wmt": pn, "n_not_in_wmt": nn, "p_early_in_wmt": pw, "n_in_wmt": nw,
               "diff": pw - pn, "diff_se": float(np.sqrt(pw * (1 - pw) / nw + pn * (1 - pn) / nn))}
    out["run_rule"] = {"benchmark": 0.1524, "tol": 0.0155, "sim": SIM["run_rule"],
                       "old_reproduced": rr_old, "d1_vs_d1": rr_new,
                       "direct_warrennolan_d1_vs_d1": {"value": p_w, "se": float(np.sqrt(p_w * (1 - p_w) / len(wd))), "n_games": int(len(wd)),
                                                        "p_margin_10plus": float((wm >= 10).mean()), "p_early_given_10plus": float((big.inn < 9).mean()),
                                                        "n_10plus": int(len(big)),
                                                        "matched_to_scoreboard": {"value": ps, "se": float(np.sqrt(ps * (1 - ps) / len(ws))), "n_games": int(len(ws))},
                                                        "event_games_only": float((((wd.inn < 9) & (wm >= 10))[conf_t]).mean()), "n_event_games": int(conf_t.sum()),
                                                        "p_early_given_10plus_by_tier_pair": by_pair, "wmt_vs_rest": not_wmt,
},
                       "wmt_non_d1_games_removed": int(len(fin) - len(fin_d1)),
                       "gap_closed_share": (rr_old["value"] - rr_new["value"]) / (rr_old["value"] - SIM["run_rule"])}
    out["bin15"] = {"benchmark": 0.0664, "tol": 0.0103, "sim": SIM["bin15"], "old_reproduced": b_old, "d1_vs_d1": b_new,
                    "gap_closed_share": (b_old["value"] - b_new["value"]) / (b_old["value"] - SIM["bin15"])}

    # (d) team R/G SD: D1-vs-D1, and with New Orleans restored
    rows = []
    s2 = sb[both]
    for s, o in (("home", "away"), ("away", "home")):
        rows.append(pd.DataFrame({"team": s2[s].values, "r": s2[f"{s}_score"].values.astype(float)}))
    tg = pd.concat(rows)
    per = tg.groupby("team").r.agg(["mean", "size"])
    s3 = sb[sb.home.isin(T) & sb.away.isin(T)]
    per_old = pd.concat([pd.DataFrame({"team": s3[s].values, "r": s3[f"{s}_score"].values.astype(float)}) for s in ("home", "away")]).groupby("team").r.mean()
    out["team_rg_sd"] = {"benchmark": 1.162, "sim": SIM["team_rg_sd"], "reproduced_306_teams": float(per_old.std(ddof=1)),
                         "with_new_orleans_307_teams": float(per["mean"].std(ddof=1)), "n_teams": int(len(per)),
                         "new_orleans_r_per_game": float(per.loc["New Orleans", "mean"]), "new_orleans_games": int(per.loc["New Orleans", "size"])}
    out["obp_p10"] = obp_p10()
    return out


def obp_p10() -> dict:
    """Rebuild qualified_players_2025 with scripts/build_phase2_gate.py qualified(), first as committed, then with the
    play-by-play games against non-D1 opponents removed (games, PAs, base-running events and charged runs). The
    module's pandas reference is wrapped so the parsed tables are filtered as they are read."""
    import build_phase2_gate as bpg
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    ids = set(teams.ncaa_team_id)
    gm = pd.read_csv(P / "games_2025.csv")
    drop = set(gm.loc[~(gm.home_team_id.isin(ids) & gm.away_team_id.isin(ids)), "game_id"])

    res = {}
    real_pd, real_load = bpg.pd, bpg.load_pa
    for label, excl in (("committed", set()), ("d1_vs_d1", drop)):
        shim = types.SimpleNamespace(**{k: getattr(real_pd, k) for k in dir(real_pd) if not k.startswith("__")})

        def rc(path, *a, _excl=excl, **k):
            d = real_pd.read_csv(path, *a, **k)
            return d[~d.game_id.isin(_excl)].reset_index(drop=True) if "game_id" in d.columns and _excl else d
        shim.read_csv = rc
        bpg.pd = shim
        bpg.load_pa = (lambda _excl=excl: (lambda d: d[~d.game_id.isin(_excl)].reset_index(drop=True))(real_load()))
        bpg.RNG = np.random.default_rng(20251001)   # the module's seed, so the bootstrap reproduces the committed tolerances
        try:
            q, _ = bpg.qualified(teams)
        finally:
            bpg.pd, bpg.load_pa = real_pd, real_load
        res[label] = {"p10": q["batters"]["OBP"]["p10"], "tol3se": q["batters"]["OBP"]["tol"]["p10"],
                      "unpooled_p10": q["batters"]["unpooled"]["OBP"]["p10"], "n_batters": q["batters"]["n"],
                      "teams_by_tier": q["batters"]["teams_by_tier"]}
    res["n_pbp_games_removed"] = len(drop)
    res["removed_games"] = gm[gm.game_id.isin(drop)][["game_date", "home_team", "away_team"]].astype(str).values.tolist()
    res["benchmark"] = 0.3366; res["sim"] = SIM["obp_p10"]
    res["gap_closed_share"] = (res["committed"]["p10"] - res["d1_vs_d1"]["p10"]) / (res["committed"]["p10"] - SIM["obp_p10"])
    return res


# ----------------------------------------------------------------------------------------------------------------------
# shared: the scoreboard fit (scripts/build_phase2_teams.py), WMT box lines per team-game
# ----------------------------------------------------------------------------------------------------------------------

_FIT = {}


def sb_fit(parks: bool) -> dict:
    """The committed scoreboard decomposition (build_phase2_teams.load / fit)."""
    if parks not in _FIT:
        from build_phase2_teams import fit, load
        sb, names, tier, conf = load()
        f = fit(sb, names, parks=parks)
        f["names"] = names; f["tier"] = tier; f["sb"] = sb
        _FIT[parks] = f
    return _FIT[parks]


def wmt_sb_match_ids(sb: pd.DataFrame) -> dict:
    """Scoreboard row index -> WMT game_id for the WMT box-score games (same teams and scores, date within a day)."""
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    id2 = dict(zip(t.ncaa_team_id, t.team))
    sg = pd.read_csv(P / "schedule_games_2025.csv")
    sg = sg[sg.innings > 0]
    keys = {}
    for r in sg.itertuples(index=False):
        a, b = id2.get(r.home_team_id), id2.get(r.away_team_id)
        if a is None or b is None:
            continue
        d = pd.Timestamp(r.game_date)
        for dd in (d, d - pd.Timedelta(days=1), d + pd.Timedelta(days=1)):
            keys.setdefault((dd.strftime("%Y-%m-%d"), frozenset([a, b]), frozenset([int(r.home_score), int(r.away_score)])), r.game_id)
    out = {}
    for i, r in zip(sb.index, sb.itertuples(index=False)):
        k = (r.date, frozenset([r.home, r.away]), frozenset([int(r.home_score), int(r.away_score)]))
        if k in keys:
            out[i] = keys[k]
    return out


def wmt_team_games() -> pd.DataFrame:
    """One row per (fielding / pitching team, game) from the WMT box lines, D1-vs-D1 2025 games with both boxes."""
    sg = pd.read_csv(P / "schedule_games_2025.csv")
    sg = sg[(sg.innings > 0) & (sg.home_is_d1 == 1) & (sg.away_is_d1 == 1) & (sg.home_has_box == 1) & (sg.away_has_box == 1)
            & sg.game_date.str.startswith("2025")]
    rows = []
    for s in ("home", "away"):
        rows.append(pd.DataFrame({"team_id": sg[f"{s}_team_id"].values, "game_id": sg.game_id.values, "date": sg.game_date.values,
                                  "e": sg[f"{s}_e"].values, "po": sg[f"{s}_po"].values, "a": sg[f"{s}_a"].values,
                                  "er": sg[f"{s}_er"].values, "ra": sg[f"{s}_r_allowed"].values}))
    tg = pd.concat(rows, ignore_index=True)
    tg["outs"] = tg.po
    tg = tg[tg.outs > 0].sort_values(["team_id", "date", "game_id"]).reset_index(drop=True)
    tg["k"] = tg.groupby("team_id").cumcount()
    tg["half"] = tg.k % 2
    return tg


def ncaa_team_pages() -> pd.DataFrame:
    # tables extracted from the NCAA.com team pages 211 and 212 (raw pages removed 2026-10-08; build_phase7_era_fielding.py)
    tables = {211: ROOT / "data/ncaa_leaders/team_era_2025.csv", 212: ROOT / "data/ncaa_leaders/team_fielding_2025.csv"}

    def pages(stat):
        d = pd.read_csv(tables[stat], dtype=str, keep_default_na=False).drop_duplicates("Team")
        for c in d.columns:
            if c not in ("Team", "Rank"):
                d[c] = pd.to_numeric(d[c].str.replace(",", ""), errors="coerce")
        return d
    p, f = pages(211), pages(212)
    d = p.merge(f, on="Team", suffixes=("", "_f"))
    d["outs"] = [3 * int(x) + int(round(10 * (x - int(x)))) for x in d.IP]
    d["era"] = 27 * d.ER / d.outs; d["rag"] = d.R / d.G; d["eg"] = d.E / d.G_f
    d["ch"] = d.PO + d.A + d.E
    return d


def corr(a, b) -> float:
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])


# ----------------------------------------------------------------------------------------------------------------------
# 2. Fielding independent of pitching (candidate 10)
# ----------------------------------------------------------------------------------------------------------------------

def item2() -> dict:
    rng = np.random.default_rng(RNG_SEED)
    tg = wmt_team_games()
    out = {}

    # (a1) split halves (odd / even games in date order) on WMT teams with 30+ D1-vs-D1 box games
    n_g = tg.groupby("team_id").size()
    keep = n_g[n_g >= 30].index
    h = tg[tg.team_id.isin(keep)].groupby(["team_id", "half"]).agg(er=("er", "sum"), ra=("ra", "sum"), e=("e", "sum"), outs=("outs", "sum"),
                                                                   g=("e", "size"), po=("po", "sum"), a=("a", "sum")).reset_index()
    h["era"] = 27 * h.er / h.outs; h["rag"] = h.ra / h.g; h["eg"] = h.e / h.g
    w = h.pivot(index="team_id", columns="half")
    full = tg[tg.team_id.isin(keep)].groupby("team_id").agg(er=("er", "sum"), ra=("ra", "sum"), e=("e", "sum"), outs=("outs", "sum"), g=("e", "size"))
    full["era"] = 27 * full.er / full.outs; full["rag"] = full.ra / full.g; full["eg"] = full.e / full.g

    def split_stats(W, F):
        r = {}
        for x in ("era", "rag", "eg"):
            rh = corr(W[(x, 0)], W[(x, 1)])
            r[f"rel_half_{x}"] = rh; r[f"rel_full_{x}"] = 2 * rh / (1 + rh)
        for x in ("era", "rag"):
            cross = 0.5 * (corr(W[(x, 0)], W[("eg", 1)]) + corr(W[(x, 1)], W[("eg", 0)]))
            r[f"obs_corr_{x}_eg"] = corr(F[x], F["eg"])
            r[f"cross_half_corr_{x}_eg"] = cross
            r[f"true_corr_{x}_eg"] = cross / np.sqrt(r[f"rel_half_{x}"] * r["rel_half_eg"])
            r[f"classic_disattenuated_{x}_eg"] = r[f"obs_corr_{x}_eg"] / np.sqrt(r[f"rel_full_{x}"] * r["rel_full_eg"])
        return r
    pt = split_stats(w, full)
    ids = np.array(w.index)
    boots = []
    for _ in range(BOOT):
        pick = rng.choice(ids, size=len(ids), replace=True)
        boots.append(split_stats(w.loc[pick], full.loc[pick]))
    se = {k: float(np.nanstd([b[k] for b in boots], ddof=1)) for k in pt}
    out["split_half_wmt"] = {"n_teams": int(len(keep)), "games_per_team_mean": float(full.g.mean()),
                             "values": pt, "se": se}

    # (a2) per-game noise model from WMT (within-team game-to-game variation), applied to every D1 team (NCAA.com)
    t2 = tg[tg.team_id.isin(n_g[n_g >= 10].index)].copy()
    agg = t2.groupby("team_id").agg(er=("er", "sum"), ra=("ra", "sum"), e=("e", "sum"), outs=("outs", "sum"), g=("e", "size"))
    t2 = t2.join(agg, on="team_id", rsuffix="_t")
    corr_df = (t2.g / (t2.g - 1))
    u_er = t2.er - t2.er_t / t2.outs_t * t2.outs
    u_ra = t2.ra - t2.ra_t / t2.g
    u_e = t2.e - t2.e_t / t2.g
    noise = {"phi_er": float((corr_df * u_er ** 2).sum() / t2.er.sum()), "phi_ra": float((corr_df * u_ra ** 2).sum() / t2.ra.sum()),
             "phi_e": float((corr_df * u_e ** 2).sum() / t2.e.sum()),
             "rho_er_e": float((u_er * u_e).sum() / np.sqrt((u_er ** 2).sum() * (u_e ** 2).sum())),
             "rho_ra_e": float((u_ra * u_e).sum() / np.sqrt((u_ra ** 2).sum() * (u_e ** 2).sum())),
             "n_teams": int(agg.shape[0]), "n_team_games": int(len(t2))}
    out["per_game_noise_wmt"] = noise

    d = ncaa_team_pages()

    def model_true(d, scale_runs=1.0, scale_e=1.0):
        nv_era = scale_runs * (27 / d.outs) ** 2 * noise["phi_er"] * d.ER
        nv_rag = scale_runs * noise["phi_ra"] * d.R / d.G ** 2
        nv_eg = scale_e * noise["phi_e"] * d.E / d.G_f ** 2
        res = {}
        for x, nv, rho in (("era", nv_era, noise["rho_er_e"]), ("rag", nv_rag, noise["rho_ra_e"])):
            vx, ve = d[x].var(), d.eg.var()
            c = np.cov(d[x], d.eg)[0, 1]
            ncov = rho * np.sqrt(nv * nv_eg)
            tvx, tve, tc = vx - nv.mean(), ve - nv_eg.mean(), c - ncov.mean()
            res[x] = {"obs_corr": c / np.sqrt(vx * ve), "reliability": tvx / vx, "reliability_eg": tve / ve,
                      "noise_cov_share": float(ncov.mean() / c), "true_corr": tc / np.sqrt(tvx * tve),
                      "true_var": tvx, "true_var_eg": tve, "true_cov": tc, "nv": float(nv.mean()), "nv_eg": float(nv_eg.mean()), "ncov": float(ncov.mean())}
        return res
    base = model_true(d)
    # counterfactual: the same true team spreads, observed with the sim's per-game run noise (dispersion 2.224 / 2.6185)
    cf = {}
    for x in ("era", "rag"):
        b = base[x]
        for lab, sr, se_ in (("runs_noise_x_sim_ratio", SIM_PHI / REAL_PHI, 1.0), ("runs_and_errors_noise_x_sim_ratio", SIM_PHI / REAL_PHI, SIM_PHI / REAL_PHI)):
            nv, nve = b["nv"] * sr, b["nv_eg"] * se_
            ncov = b["ncov"] * np.sqrt(sr * se_)
            cf.setdefault(x, {})[lab] = (b["true_cov"] + ncov) / np.sqrt((b["true_var"] + nv) * (b["true_var_eg"] + nve))
    # bootstrap over teams for the NCAA.com side (the noise parameters held fixed)
    bt = []
    for _ in range(BOOT):
        dd = d.iloc[rng.integers(0, len(d), len(d))].reset_index(drop=True)
        m = model_true(dd)
        bt.append({f"{x}_{k}": m[x][k] for x in ("era", "rag") for k in ("obs_corr", "true_corr", "reliability", "reliability_eg")})
    se2 = {k: float(np.std([b[k] for b in bt], ddof=1)) for k in bt[0]}
    out["ncaa_com_all_d1"] = {"n_teams": int(len(d)), "model": {x: {k: v for k, v in base[x].items()} for x in base}, "se": se2,
                              "counterfactual_obs_corr_with_sim_noise": cf,
                              "sim_obs_corr": {"era": SIM["corr_era_e"], "rag": SIM["corr_ra_e"]}}
    # the same noise model on the WMT split-half teams, as a check of the model against split halves
    full2 = full.copy(); full2["ER"] = full2.er; full2["R"] = full2.ra; full2["E"] = full2.e; full2["G"] = full2.g; full2["G_f"] = full2.g
    chk = model_true(full2)
    out["noise_model_check_on_wmt_split_teams"] = {x: {"reliability_model": chk[x]["reliability"], "reliability_eg_model": chk[x]["reliability_eg"],
                                                       "true_corr_model": chk[x]["true_corr"]} for x in ("era", "rag")}

    # (b) error rate per chance left after run prevention d
    out["error_residual"] = error_residual(d, tg, noise, rng)
    # unearned shares
    out["unearned"] = unearned(d, rng)
    return out


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def error_residual(d: pd.DataFrame, tg: pd.DataFrame, noise: dict, rng) -> dict:
    """Team error log-odds per chance y = logit(E / (PO + A + E)) regressed on run prevention d.
    A. NCAA.com, every team (the refit in PHASE0_NOTES, binomial noise): reproduces slope -.685 and residual SD .127.
       Then: (i) errors' per-game overdispersion relative to the binomial (WMT, within team), (ii) noise in d (the
       fit's covariance) attenuating the slope.
    B. WMT box lines, split halves: the residual's true variance as the covariance of the two halves' residuals, with
       d refitted on the scoreboard games outside the WMT sample (no shared noise)."""
    out = {}
    f = sb_fit(parks=True)
    fd = dict(zip(f["names"], f["d"])); nd = dict(zip(f["names"], f["noise"][:, 1, 1]))
    var_d_true = float(np.var(f["d"]) - f["noise"][:, 1, 1].mean())
    # NCAA.com team names -> scoreboard names
    dd = d.copy()
    dd["d"] = dd.Team.map(fd); dd["nd"] = dd.Team.map(nd)
    unmatched = dd[dd.d.isna()].Team.tolist()
    dd = dd.dropna(subset=["d"]).reset_index(drop=True)
    sbg = pd.concat([f["sb"].home, f["sb"].away]).value_counts()
    dd["g_sb"] = dd.Team.map(sbg).fillna(0)
    # (i) overdispersion of a team's errors per game against binomial-by-chances (WMT, within team)
    t = tg.copy(); t["ch"] = t.po + t.a + t.e
    g = t.groupby("team_id").agg(e=("e", "sum"), ch=("ch", "sum"), n=("e", "size"))
    t = t.join(g, on="team_id", rsuffix="_t"); t = t[t.n >= 10]
    pt = t.e_t / t.ch_t
    phi_bin = float(((t.n / (t.n - 1)) * (t.e - pt * t.ch) ** 2).sum() / (pt * (1 - pt) * t.ch).sum())

    def chain(dd):
        p = dd.E.sum() / dd.ch.sum()
        y = (logit(dd.E / dd.ch) - logit(p))
        wgt = (dd.ch * p * (1 - p)).values
        wm = lambda v: float((wgt * np.asarray(v, float)).sum() / wgt.sum())
        dv = dd.d.values; dm = wm(dv); ym = wm(y)
        cov_yd = wm((dv - dm) * (y - ym)); var_dw = wm((dv - dm) ** 2); var_yw = wm((y - ym) ** 2)
        slope_raw = cov_yd / var_dw
        var_res = var_yw - slope_raw ** 2 * var_dw
        nbin = wm(1 / (dd.ch.values * p * (1 - p)))
        nd_w = wm(dd.nd.values)
        # (iii) game-level noise shared by a team's errors and its d: an error adds runs allowed in the same game.
        # Per game cov(runs allowed, errors) = rho * sqrt(phi_ra mu_ra phi_e mu_e) (WMT, within team); d moves by
        # -(runs allowed - expected) / (sum of expected runs) and y by (errors - expected) / (ch p (1 - p)), over the
        # scoreboard games (D1-vs-D1) that are also in the season totals.
        mu_ra = dd.R / dd.G; mu_e = dd.E / dd.G_f
        c_g = noise["rho_ra_e"] * np.sqrt(noise["phi_ra"] * mu_ra * noise["phi_e"] * mu_e)
        cov_mech = wm(-(dd.g_sb * c_g) / ((dd.g_sb * mu_ra) * dd.ch * p * (1 - p)))
        vy_true = var_yw - phi_bin * nbin
        vd_true = var_dw - nd_w
        r = {"rate_per_chance": float(p), "slope_d_binomial": slope_raw,
             "resid_sd_true_binomial": float(np.sqrt(max(var_res - nbin, 0))),
             "resid_sd_true_overdispersed": float(np.sqrt(max(var_res - phi_bin * nbin, 0))),
             "noise_var_d_mean": nd_w, "noise_var_y_binomial": nbin, "cov_noise_y_d_shared_games": cov_mech}
        sl = cov_yd / vd_true
        r["slope_d_noise_corrected"] = sl
        r["resid_sd_true_overdispersed_d_noise_corrected"] = float(np.sqrt(max(vy_true - sl ** 2 * vd_true, 0)))
        sl2 = (cov_yd - cov_mech) / vd_true
        r["slope_d_all_corrections"] = sl2
        r["resid_var_true_all_corrections"] = float(vy_true - sl2 ** 2 * vd_true)
        r["resid_sd_true_all_corrections"] = float(np.sqrt(max(vy_true - sl2 ** 2 * vd_true, 0)))
        r["true_corr_d_error_logodds_all_corrections"] = float((cov_yd - cov_mech) / np.sqrt(vd_true * vy_true))
        r["true_sd_error_logodds"] = float(np.sqrt(vy_true)); r["true_sd_d"] = float(np.sqrt(vd_true))
        return r
    res = chain(dd)
    bs = [chain(dd.iloc[rng.integers(0, len(dd), len(dd))].reset_index(drop=True)) for _ in range(BOOT)]
    res["se"] = {k: float(np.std([b[k] for b in bs], ddof=1)) for k in res}
    res.update({"n_teams": int(len(dd)), "unmatched": unmatched, "phi_errors_vs_binomial_wmt": phi_bin})
    out["ncaa_com"] = res
    # the engine's implied true correlation of d with the team error log-odds: slope sd_d / total sd
    sd_d_eng = float(np.sqrt(0.2377 ** 2 - 0.1361 ** 2) / 0.7202)
    out["engine_implied_true_corr_d_error_logodds"] = -0.7202 * sd_d_eng / 0.2377

    # B. WMT box lines split by game (game_id parity), each half's errors against d refitted without that half's games
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv"); id2 = dict(zip(teams.ncaa_team_id, teams.team))
    from build_phase2_teams import fit, load
    sb0, names0, _, _ = load()
    match = wmt_sb_match_ids(sb0)          # scoreboard row -> WMT game_id
    tt = tg.copy(); tt["ch"] = tt.po + tt.a + tt.e; tt["gh"] = tt.game_id % 2
    Y, Dd, Nd = {}, {}, {}
    for hh in (0, 1):
        drop_rows = [i for i, gid in match.items() if gid % 2 == hh]
        sbh = sb0.drop(index=drop_rows).reset_index(drop=True)
        nm = sorted(set(sbh.home) | set(sbh.away))
        fh = fit(sbh, nm, parks=True)
        Dd[hh] = dict(zip(nm, fh["d"])); Nd[hh] = dict(zip(nm, fh["noise"][:, 1, 1]))
        Y[hh] = tt[tt.gh == hh].groupby("team_id").agg(e=("e", "sum"), ch=("ch", "sum"), n=("e", "size"))
    W = Y[0].join(Y[1], lsuffix="0", rsuffix="1", how="inner")
    W["name"] = W.index.map(id2)
    for hh in (0, 1):
        W[f"d{hh}"] = W.name.map(Dd[hh]); W[f"nd{hh}"] = W.name.map(Nd[hh])
    W = W.dropna(subset=["d0", "d1"])

    def stats_B(W):
        pp = (W.e0.sum() + W.e1.sum()) / (W.ch0.sum() + W.ch1.sum())
        y0 = logit(W.e0 / W.ch0) - logit(pp); y1 = logit(W.e1 / W.ch1) - logit(pp)
        d0, d1 = W.d0.values, W.d1.values
        vd = 0.5 * (np.var(d0, ddof=1) - W.nd0.mean() + np.var(d1, ddof=1) - W.nd1.mean())
        cyd = 0.5 * (np.cov(y0, d0)[0, 1] + np.cov(y1, d1)[0, 1])
        vy = np.cov(y0, y1)[0, 1]
        sl = cyd / vd
        # the same without removing d's noise and with each half's own d (shared game noise), for comparison
        cyd_same = 0.5 * (np.cov(y0, d1)[0, 1] + np.cov(y1, d0)[0, 1])
        return {"slope_d": sl, "var_y_true": vy, "var_d_true": vd, "resid_var_true": vy - sl ** 2 * vd,
                "true_corr_d_y": cyd / np.sqrt(vd * vy) if vy > 0 else np.nan,
                "slope_d_shared_noise_halves": cyd_same / vd}
    rB = {}
    for mg in (8, 15):
        Wm = W[(W.n0 >= mg) & (W.n1 >= mg)]
        pt_ = stats_B(Wm)
        bs = [stats_B(Wm.iloc[rng.integers(0, len(Wm), len(Wm))]) for _ in range(BOOT)]
        pt_ = {k: float(v) for k, v in pt_.items()}
        pt_["se"] = {k: float(np.nanstd([b[k] for b in bs], ddof=1)) for k in pt_}
        pt_["n_teams"] = int(len(Wm)); pt_["games_per_half_mean"] = float(0.5 * (Wm.n0 + Wm.n1).mean())
        pt_["resid_sd_true"] = float(np.sqrt(max(pt_["resid_var_true"], 0)))
        rB[f"min_games_per_half_{mg}"] = pt_
    out["wmt_split_by_game_external_d"] = rB
    out["engine"] = {"slope_d": -0.7202, "resid_sd_true": 0.1361, "fielders_sd": 0.1191, "team_sd": 0.0657}
    return out


def unearned(d: pd.DataFrame, rng) -> dict:
    """Share of runs allowed that are unearned (1 - ER/R), NCAA.com 2025 full seasons, by ERA group."""
    d = d.copy(); d["ue"] = d.R - d.ER
    d = d.sort_values("era").reset_index(drop=True)
    groups = {"top50_era": d.index < 50, "era_under_4": d.era < 4.0, "rest_after_top50": d.index >= 50, "all": np.ones(len(d), bool)}
    # ERA quintiles
    q = pd.qcut(d.era, 5, labels=False)
    for k in range(5):
        groups[f"era_quintile_{k + 1}"] = (q == k).values
    out = {}
    for k, m in groups.items():
        x = d[m]
        agg = float(x.ue.sum() / x.R.sum()); mean_share = float((x.ue / x.R).mean())
        bs = []
        for _ in range(BOOT):
            xx = x.iloc[rng.integers(0, len(x), len(x))]
            bs.append(xx.ue.sum() / xx.R.sum())
        out[k] = {"n_teams": int(m.sum()), "unearned_share": agg, "se": float(np.std(bs, ddof=1)), "mean_team_share": mean_share,
                  "errors_per_game": float(x.eg.mean()), "unearned_per_error": float(x.ue.sum() / x.E.sum()),
                  "ra_per_game": float(x.rag.mean()), "era": float(x.era.mean())}
    # partial correlation of ERA and errors per game at equal runs allowed per game
    r_ee, r_er, r_re = corr(d.era, d.eg), corr(d.era, d.rag), corr(d.rag, d.eg)
    out["partial_corr_era_eg_given_rag"] = (r_ee - r_er * r_re) / np.sqrt((1 - r_er ** 2) * (1 - r_re ** 2))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# half-inning table from the WMT play-by-play (items 3 and 4)
# ----------------------------------------------------------------------------------------------------------------------

_HI = {}


def half_innings() -> pd.DataFrame:
    """One row per half-inning: batting / fielding team, runs (plate appearances plus base-running events; equals
    the box score in all 2,232 games), the pitcher who faced its first batter (name key, scripts/lib/players.py), the
    game's starter for the fielding team, errors and chances (PO + A + E) charged to the fielding team in that
    inning (fielding credits), error plays, and unearned runs (runs_charged, by the fielding team and inning)."""
    if "hi" in _HI:
        return _HI["hi"]
    from lib.players import load_pa
    pa = load_pa().sort_values(["game_id", "group_id"])
    rev = pd.read_csv(P / "runner_events_2025.csv.gz")
    key = ["game_id", "inning", "half"]
    runs = pa.groupby(key).runs_on_play.sum().add(rev[rev.to_base == 4].groupby(key).size(), fill_value=0).rename("runs")
    first = pa.groupby(key).agg(bat_team_id=("bat_team_id", "first"), pit_team_id=("pit_team_id", "first"), pkey=("pkey", "first"),
                                n_pa=("result", "size"))
    hi = first.join(runs).reset_index()
    st = pa.groupby(["game_id", "pit_team_id"]).pkey.first().rename("starter")
    hi = hi.join(st, on=["game_id", "pit_team_id"])
    hi["by_starter"] = hi.pkey == hi.starter
    fl = pd.read_csv(P / "fielding_2025.csv.gz")
    fe = fl.groupby(["game_id", "team_id", "inning"]).agg(errors=("errors", "sum"), po=("put_outs", "sum"), a=("assists", "sum"))
    eplays = fl[fl.errors > 0].groupby(["game_id", "team_id", "inning"]).play_by_play_id.nunique().rename("error_plays")
    fe = fe.join(eplays).fillna({"error_plays": 0})
    hi = hi.join(fe, on=["game_id", "pit_team_id", "inning"]).fillna({"errors": 0, "po": 0, "a": 0, "error_plays": 0})
    hi["chances"] = hi.po + hi.a + hi.errors
    rc = pd.read_csv(P / "runs_charged_2025.csv.gz")
    ue = rc.groupby(["game_id", "pit_team_id", "inning"]).unearned.sum().rename("unearned")
    hi = hi.join(ue, on=["game_id", "pit_team_id", "inning"]).fillna({"unearned": 0})
    _HI["hi"] = hi
    return hi


def expected_runs(hi: pd.DataFrame) -> pd.DataFrame:
    """Expected runs in each half-inning from the scoreboard fit without parks (the fit whose dispersion is 2.6185):
    mu_g = exp(a + o_bat - d_pit + h/2 sign) per team-game, times the league share of a team-game's runs scored in that
    inning number (WMT sample). Half-innings of teams outside the fit (non-D1, New Orleans) are dropped."""
    f = sb_fit(parks=False)
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv"); id2 = dict(zip(teams.ncaa_team_id, teams.team))
    fo = dict(zip(f["names"], f["o"])); fdd = dict(zip(f["names"], f["d"]))
    gm = pd.read_csv(P / "games_2025.csv")[["game_id", "home_team_id", "neutral_site"]]
    x = hi.merge(gm, on="game_id", how="left")
    x["o"] = x.bat_team_id.map(id2).map(fo); x["d"] = x.pit_team_id.map(id2).map(fdd)
    x = x.dropna(subset=["o", "d"]).copy()
    sgn = np.where(x.bat_team_id == x.home_team_id, 0.5, -0.5)
    x["mu_g"] = np.exp(f["a"] + x.o - x.d + f["h"] * sgn)
    # inning-number shares: mean runs in inning i over all half-innings played, scaled so a 9-inning team-game sums to
    # the team-game mean
    inn = x.inning.clip(upper=10)
    m_i = x.groupby(inn).runs.mean()
    per_tg = x.groupby(["game_id", "bat_team_id"]).runs.sum().mean()
    w = m_i / per_tg
    x["e"] = x.mu_g * inn.map(w).values
    # rescale so expected and observed totals agree in the sample (the WMT sample's level vs the scoreboard's)
    x["e"] *= x.runs.sum() / x.e.sum()
    x["r"] = x.runs - x.e
    return x


# ----------------------------------------------------------------------------------------------------------------------
# 3. Starter day-to-day form (candidate 11)
# ----------------------------------------------------------------------------------------------------------------------

def item3() -> dict:
    """Multiplicative random effects on a half-inning's expected runs, by method of moments on pairs of half-innings
    of one batting team (cov(r_i, r_j) = e_i e_j sigma^2 for a shared log-scale effect of variance sigma^2):
      A  pairs within one start (both half-innings begun by the same starter, same game)  = P + F + G
      B  pairs of the same starter's half-innings in different games                     = P
      C  same game, a starter half-inning with a relief half-inning                      = G + c(P, pen)
      Cb same starter, starter half-inning in one game with relief half-innings in another = c(P, pen)
    P: the starter's season talent beyond his team's run prevention; F: start-level form; G: the game's shared part
    for that batting team (its lineup's day, park and weather, the fielding team's defensive day).
    F = (A - B) - (C - Cb).  Bootstrap over starters."""
    rng = np.random.default_rng(RNG_SEED + 3)
    x = expected_runs(half_innings())
    x["sp"] = x.pit_team_id.astype(str) + "|" + x.starter.astype(str)
    starts_per = x[x.by_starter].groupby("sp").game_id.nunique()
    out = {"n_half_innings": int(len(x)), "n_games": int(x.game_id.nunique())}
    res = {}
    for min_starts in (5, 10):
        keep = starts_per[starts_per >= min_starts].index
        y = x[x.sp.isin(keep)]
        # per start (game, starter): sums over his half-innings and over the relief half-innings of the same batting team
        y = y.assign(S=y.by_starter)
        g = y.groupby(["sp", "game_id", "S"]).agg(T=("r", "sum"), TE=("e", "sum"), Q=("r", lambda v: (v ** 2).sum()),
                                                QE=("e", lambda v: (v ** 2).sum()), k=("r", "size")).unstack("S")
        g.columns = [f"{a}{'S' if b else 'R'}" for a, b in g.columns]
        g = g.fillna(0).reset_index()
        g = g[g.kS > 0]
        stats = pd.DataFrame({
            "A_n": g.TS ** 2 - g.QS, "A_d": g.TES ** 2 - g.QES,
            "C_n": g.TS * g.TR, "C_d": g.TES * g.TER,
            "TS": g.TS, "TES": g.TES, "TR": g.TR, "TER": g.TER, "sp": g.sp, "kS": g.kS})
        ps = stats.groupby("sp").agg(A_n=("A_n", "sum"), A_d=("A_d", "sum"), C_n=("C_n", "sum"), C_d=("C_d", "sum"),
                                     sT=("TS", "sum"), sTE=("TES", "sum"), sR=("TR", "sum"), sRE=("TER", "sum"),
                                     qT=("TS", lambda v: (v ** 2).sum()), qTE=("TES", lambda v: (v ** 2).sum()), n=("TS", "size"))
        ps["B_n"] = ps.sT ** 2 - ps.qT; ps["B_d"] = ps.sTE ** 2 - ps.qTE
        ps["Cb_n"] = ps.sT * ps.sR - ps.C_n; ps["Cb_d"] = ps.sTE * ps.sRE - ps.C_d

        def comp(ps):
            A = ps.A_n.sum() / ps.A_d.sum(); B = ps.B_n.sum() / ps.B_d.sum()
            C = ps.C_n.sum() / ps.C_d.sum(); Cb = ps.Cb_n.sum() / ps.Cb_d.sum()
            return {"A_within_start": A, "B_same_starter_other_games": B, "C_same_game_starter_x_relief": C,
                    "Cb_same_starter_other_games_x_relief": Cb, "talent_P": B, "game_shared_G": C - Cb, "form_F": (A - B) - (C - Cb),
                    "A_minus_B": A - B}
        pt = comp(ps)
        ids = np.array(ps.index)
        bs = [comp(ps.loc[rng.choice(ids, size=len(ids), replace=True)]) for _ in range(BOOT)]
        se = {k: float(np.std([b[k] for b in bs], ddof=1)) for k in pt}
        # contribution of a start-level effect of log-variance F to runs per team-game: F (sum of the starter's
        # expected runs)^2, in dispersion units mean(F (sum e_S)^2 / mu_g)
        eS = y[y.by_starter].groupby(["game_id", "bat_team_id"]).e.sum()
        etot = y.groupby(["game_id", "bat_team_id"]).e.sum()
        ratio = float(((eS.reindex(etot.index).fillna(0) ** 2) / etot).mean())   # mean (sum e_S)^2 / (team-game expected runs)
        share_starter = float(eS.sum() / etot.sum())
        res[f"min_starts_{min_starts}"] = {"n_starters": int(len(ps)), "n_starts": int(ps.n.sum()), "values": pt, "se": se,
                                            "mean_sq_starter_expected_over_mu": ratio, "starter_share_of_expected_runs": share_starter,
                                            "dphi_form": pt["form_F"] * ratio, "dphi_form_se": se["form_F"] * ratio}
    out["components"] = res
    # descriptive dispersion: half-inning level and start level (runs in the half-innings the starter began),
    # against the expectation from the fit (no pitcher term)
    s = x[x.by_starter]
    out["dispersion_half_inning_all"] = float(((x.runs - x.e) ** 2 / x.e).mean())
    agg = s.groupby(["game_id", "pit_team_id"]).agg(R=("runs", "sum"), E=("e", "sum"), k=("runs", "size"))
    out["dispersion_per_start"] = float(((agg.R - agg.E) ** 2 / agg.E).mean())
    out["dispersion_half_inning_starter"] = float(((s.runs - s.e) ** 2 / s.e).mean())
    out["innings_begun_per_start_mean"] = float(agg.k.mean())
    # per-start quasi-Poisson dispersion with a pitcher term (each starter's season ratio of runs to expected runs),
    # starters with 5+ starts: the expectation a "season rate x opponent" model gives
    agg = agg.reset_index().merge(s[["game_id", "pit_team_id", "sp"]].drop_duplicates(), on=["game_id", "pit_team_id"])
    cnt = agg.groupby("sp").size(); agg = agg[agg.sp.map(cnt) >= 5]
    ratio_p = agg.groupby("sp").R.sum() / agg.groupby("sp").E.sum()
    mu = agg.E * agg.sp.map(ratio_p)
    out["dispersion_per_start_pitcher_term"] = float((((agg.R - mu) ** 2) / mu).sum() / (len(agg) - len(ratio_p)))
    out["n_starts_pitcher_term"] = int(len(agg))
    # innings 1-3 against 4-6 of the same start (starts that began inning 4 or later), raw correlation of residual
    # sums; the same across two different starts of the same starter, and against relief innings 7-9 of the same game
    s13 = s[s.inning <= 3].groupby(["game_id", "pit_team_id", "sp"]).agg(r13=("r", "sum"), k13=("r", "size"))
    s46 = s[(s.inning >= 4) & (s.inning <= 6)].groupby(["game_id", "pit_team_id", "sp"]).agg(r46=("r", "sum"))
    j = s13[s13.k13 == 3].join(s46, how="inner").reset_index()
    rel = x[(~x.by_starter) & (x.inning >= 7) & (x.inning <= 9)].groupby(["game_id", "pit_team_id"]).r.sum().rename("r79")
    j = j.join(rel, on=["game_id", "pit_team_id"])
    # other start of the same starter: pair each start with the next one by that starter
    j = j.sort_values(["sp", "game_id"])
    j["r46_next"] = j.groupby("sp").r46.shift(-1)
    def cc(a, b):
        m = a.notna() & b.notna()
        r = corr(a[m], b[m]); n = int(m.sum())
        return {"r": r, "se": float((1 - r ** 2) / np.sqrt(max(n - 3, 1))), "n": n}
    out["innings_1_3_vs_4_6"] = {"same_start": cc(j.r13, j.r46), "next_start_same_starter": cc(j.r13, j.r46_next),
                                 "same_game_relief_7_9": cc(j.r13, j.r79)}
    out["missing"] = {"real_phi": REAL_PHI, "sim_phi": SIM_PHI, "dphi_missing": REAL_PHI - SIM_PHI}
    out["team_game_split"] = team_game_split(x, rng)
    return out


def team_game_split(x: pd.DataFrame, rng) -> dict:
    """Exact split of the team-game Pearson dispersion (runs around the fit) into the part inside half-innings and the
    part from pairs of different half-innings of the same team-game: (sum r)^2 / E = sum r^2 / E + sum_{i != j} r_i r_j / E.
    The cross part is split by pair type (both begun by the starter, starter x relief, both relief)."""
    x = x.assign(rS=np.where(x.by_starter, x.r, 0.0), rR=np.where(x.by_starter, 0.0, x.r), r2=x.r ** 2,
                 r2S=np.where(x.by_starter, x.r ** 2, 0.0), r2R=np.where(x.by_starter, 0.0, x.r ** 2))
    g = x.groupby(["game_id", "bat_team_id"]).agg(Tt=("r", "sum"), E=("e", "sum"), Q=("r2", "sum"), TS=("rS", "sum"), TR=("rR", "sum"),
                                                  QS=("r2S", "sum"), QR=("r2R", "sum"), n=("r", "size"))
    def parts(g):
        tot = (g.Tt ** 2 / g.E).mean(); within = (g.Q / g.E).mean()
        ss = ((g.TS ** 2 - g.QS) / g.E).mean(); rr = ((g.TR ** 2 - g.QR) / g.E).mean(); sr = (2 * g.TS * g.TR / g.E).mean()
        return {"phi_team_game": tot, "within_half_inning": within, "cross_half_inning": tot - within,
                "cross_starter_starter": ss, "cross_starter_relief": sr, "cross_relief_relief": rr}
    pt = parts(g)
    games = g.index.get_level_values(0).unique().values
    gi = g.reset_index().set_index("game_id")
    bs = []
    for _ in range(200):
        pick = rng.choice(games, size=len(games), replace=True)
        bs.append(parts(gi.loc[pick]))
    return {"values": pt, "se": {k: float(np.std([b[k] for b in bs], ddof=1)) for k in pt}, "n_team_games": int(len(g)),
            "mean_expected_runs": float(g.E.mean())}


# ----------------------------------------------------------------------------------------------------------------------
# 4. Errors clustering into big innings (candidate 12)
# ----------------------------------------------------------------------------------------------------------------------

def item4() -> dict:
    """Errors per half-inning against independence. Expectations, per half-inning, mixed over half-innings:
      Poisson: the fielding team's own errors per half-inning in the sample;
      binomial-by-chances: Binomial(chances in that half-inning, the fielding team's errors per chance), chances =
      PO + A + E credited in the half-inning (an error that extends the inning adds chances, so this expectation
      already allows more errors in long innings).
    Variance contribution: conditional moments of runs given the half-inning's error count k (0, 1, 2, 3+), mixed
    over the observed and the binomial-by-chances distribution of k; the difference in runs variance per
    half-inning, times half-innings per team-game, over mean runs per team-game, is the dispersion share. It
    attributes every run difference between multi-error and single-error half-innings to the clustering, so it is
    an upper bound."""
    from math import factorial
    rng = np.random.default_rng(RNG_SEED + 4)

    class st:   # the two pmfs needed (k = 0, 1, 2), without scipy
        class poisson:
            @staticmethod
            def pmf(k, lam):
                return np.exp(-lam) * lam ** k / factorial(k)

        class binom:
            @staticmethod
            def pmf(k, n, p):
                n = np.asarray(n, float)
                c = {0: np.ones_like(n), 1: n, 2: n * (n - 1) / 2}[k]
                return c * p ** k * (1 - p) ** (n - k)
    hi = half_innings().copy()
    hi = hi[hi.chances > 0]
    team = hi.groupby("pit_team_id").agg(e_t=("errors", "sum"), ch_t=("chances", "sum"), n_t=("errors", "size"))
    hi = hi.join(team, on="pit_team_id")
    lam = hi.e_t / hi.n_t; p = hi.e_t / hi.ch_t
    K = 4   # 0, 1, 2, 3+

    def dist_obs(h):
        k = h.errors.clip(upper=K - 1).astype(int)
        return np.bincount(k, minlength=K)[:K] / len(h)

    def dist_pois(lam):
        pm = np.column_stack([st.poisson.pmf(k, lam) for k in range(K - 1)])
        return np.append(pm.mean(0), 1 - pm.mean(0).sum())

    def dist_bin(n, p):
        pm = np.column_stack([st.binom.pmf(k, n, p) for k in range(K - 1)])
        return np.append(pm.mean(0), 1 - pm.mean(0).sum())
    obs, pois, binom = dist_obs(hi), dist_pois(lam.values), dist_bin(hi.chances.values.astype(int), p.values)
    # error plays (a play with two errors counts once)
    kp = hi.error_plays.clip(upper=K - 1).astype(int)
    obs_plays = np.bincount(kp, minlength=K)[:K] / len(hi)
    pp = hi.groupby("pit_team_id").error_plays.transform("sum") / hi.ch_t
    binom_plays = dist_bin(hi.chances.values.astype(int), pp.values)
    # run moments given k
    k = hi.errors.clip(upper=K - 1).astype(int)
    m = hi.groupby(k).runs.mean().reindex(range(K)).values
    s2 = hi.groupby(k).apply(lambda d: (d.runs ** 2).mean()).reindex(range(K)).values
    def var_mix(w):
        return float((w * s2).sum() - ((w * m).sum()) ** 2), float((w * m).sum())
    v_obs, m_obs = var_mix(obs); v_bin, m_bin = var_mix(binom); v_poi, m_poi = var_mix(pois)
    hpg = float(len(hi) / hi.groupby(["game_id", "bat_team_id"]).ngroups)
    rpg = float(hi.groupby(["game_id", "bat_team_id"]).runs.sum().mean())
    out = {"n_half_innings": int(len(hi)), "n_games": int(hi.game_id.nunique()), "errors": int(hi.errors.sum()),
           "error_plays": int(hi.error_plays.sum()),
           "dist": {"observed": obs.tolist(), "poisson_team_rate": pois.tolist(), "binomial_by_chances": binom.tolist()},
           "dist_error_plays": {"observed": obs_plays.tolist(), "binomial_by_chances": binom_plays.tolist()},
           "share_2plus": {"observed": float(obs[2:].sum()), "poisson": float(pois[2:].sum()), "binomial": float(binom[2:].sum()),
                           "observed_plays": float(obs_plays[2:].sum()), "binomial_plays": float(binom_plays[2:].sum())},
           "runs_given_errors": {"k": ["0", "1", "2", "3+"], "mean_runs": m.tolist(), "n": np.bincount(k, minlength=K).tolist(),
                                 "p_3plus_runs": hi.groupby(k).runs.apply(lambda v: (v >= 3).mean()).reindex(range(K)).tolist(),
                                 "unearned_per_half_inning": hi.groupby(k).unearned.mean().reindex(range(K)).tolist()},
           "p_3plus_given_any_error": float((hi[hi.errors > 0].runs >= 3).mean()),
           "p_3plus_given_no_error": float((hi[hi.errors == 0].runs >= 3).mean()),
           "unearned_per_error": float(hi.unearned.sum() / hi.errors.sum()),
           "unearned_per_error_by_k": {str(kk): float(hi[k == kk].unearned.sum() / hi[k == kk].errors.sum()) for kk in (1, 2, 3)},
           "half_innings_per_team_game": hpg, "runs_per_team_game": rpg,
           "var_runs_per_half_inning": {"observed_mix": v_obs, "binomial_mix": v_bin, "poisson_mix": v_poi},
           "mean_runs_per_half_inning": {"observed_mix": m_obs, "binomial_mix": m_bin, "poisson_mix": m_poi}}
    dvar_tg = hpg * (v_obs - v_bin)
    out["dvar_team_game_vs_binomial"] = dvar_tg
    out["dphi_vs_binomial"] = dvar_tg / rpg
    out["dvar_team_game_vs_poisson"] = hpg * (v_obs - v_poi)
    out["dphi_vs_poisson"] = hpg * (v_obs - v_poi) / rpg
    # errors per team-game: variance observed against the sum of independent half-innings (binomial by chances)
    tgm = hi.assign(vb=hi.chances * p * (1 - p), eb=hi.chances * p).groupby(["game_id", "pit_team_id"]).agg(E=("errors", "sum"), vb=("vb", "sum"), eb=("eb", "sum"))
    out["errors_per_team_game"] = {"mean": float(tgm.E.mean()), "var_around_binomial_expectation": float(((tgm.E - tgm.eb) ** 2).mean()),
                                   "binomial_variance": float(tgm.vb.mean())}
    # bootstrap over games
    games = hi.game_id.unique()
    gi = hi.set_index("game_id")
    bs = []
    for _ in range(200):
        h = gi.loc[rng.choice(games, size=len(games), replace=True)]
        kk = h.errors.clip(upper=K - 1).astype(int)
        o_ = np.bincount(kk, minlength=K)[:K] / len(h)
        b_ = dist_bin(h.chances.values.astype(int), (h.e_t / h.ch_t).values)
        mm = h.groupby(kk).runs.mean().reindex(range(K)).values
        ss = h.groupby(kk).runs.apply(lambda v: (v ** 2).mean()).reindex(range(K)).values
        vo = (o_ * ss).sum() - ((o_ * mm).sum()) ** 2; vb = (b_ * ss).sum() - ((b_ * mm).sum()) ** 2
        bs.append({"obs2": o_[2:].sum(), "bin2": b_[2:].sum(), "ratio2": o_[2:].sum() / b_[2:].sum(),
                   "p3_err": (h[h.errors > 0].runs >= 3).mean(), "p3_noerr": (h[h.errors == 0].runs >= 3).mean(),
                   "ue_per_e": h.unearned.sum() / h.errors.sum(), "dphi": hpg * (vo - vb) / rpg})
    out["se"] = {kk: float(np.std([b[kk] for b in bs], ddof=1)) for kk in bs[0]}
    out["ratio_2plus_obs_over_binomial"] = out["share_2plus"]["observed"] / out["share_2plus"]["binomial"]
    return out


# ----------------------------------------------------------------------------------------------------------------------
# report
# ----------------------------------------------------------------------------------------------------------------------

def plain(o):
    if isinstance(o, dict):
        return {str(k): plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    if hasattr(o, "item"):
        o = o.item()
    if isinstance(o, float):
        return None if not np.isfinite(o) else round(o, 6)
    return o


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, choices=(1, 2, 3, 4))
    a = ap.parse_args()
    import os
    os.chdir(ROOT)     # build_phase2_gate reads relative paths
    prev = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    res = prev if a.only else {k: v for k, v in prev.items() if k in ROUND2_KEYS}   # round 2 keys survive a rerun
    fns = {1: item1, 2: item2, 3: item3, 4: item4}
    for k, fn in fns.items():
        if a.only in (None, k):
            print(f"item {k} ...", flush=True)
            res[f"item{k}"] = plain(fn())
    f = sb_fit(parks=False)
    mu_bar = float(pd.concat([f["sb"].home_score, f["sb"].away_score]).mean())
    res["scale"] = {"real_phi": REAL_PHI, "sim_phi": SIM_PHI, "dphi_missing": REAL_PHI - SIM_PHI, "mean_runs_per_team_game_fit": mu_bar,
                    "missing_raw_variance_runs2": (REAL_PHI - SIM_PHI) * mu_bar, "missing_log_variance": (REAL_PHI - SIM_PHI) / mu_bar,
                    "fit_dispersion_reproduced": f["phi"], "fit_residual_corr_reproduced": f["residual_corr"]}
    res["_meta"] = {"script": "scripts/diag_sizes.py", "date": "2026-10-06", "bootstrap_reps": BOOT,
                    "note": "Real-data sizes only. Sim values are copied from reports/phase2.md, phase6.md, phase7.md (40 seasons, 2026-10-05)."}
    OUT_JSON.write_text(json.dumps(plain(res), indent=1) + "\n")
    md = markdown(res)
    old_md = OUT_MD.read_text() if OUT_MD.exists() else ""
    if ROUND2_MARKER in old_md:      # keep round 2's sections (scripts/diag_tto_mopup.py); rerun that script to refresh them
        md = md.rstrip("\n") + "\n\n" + old_md[old_md.index(ROUND2_MARKER):]
    OUT_MD.write_text(md)
    print("wrote", OUT_JSON, OUT_MD)


def f3(x, n=3):
    return "n/a" if x is None else f"{x:.{n}f}"


def markdown(R: dict) -> str:
    i1, i2, i3, i4, sc = R["item1"], R["item2"], R["item3"], R["item4"], R["scale"]
    rr, b15, obp, sd = i1["run_rule"], i1["bin15"], i1["obp_p10"], i1["team_rg_sd"]
    wn = rr["direct_warrennolan_d1_vs_d1"]
    miss = sc["dphi_missing"]
    c5 = i3["components"]["min_starts_5"]; c10 = i3["components"]["min_starts_10"]
    split = i3["team_game_split"]
    nc = i2["ncaa_com_all_d1"]; sh = i2["split_half_wmt"]; er = i2["error_residual"]["ncaa_com"]
    eb = i2["error_residual"]["wmt_split_by_game_external_d"]["min_games_per_half_8"]
    ue = i2["unearned"]
    sim_margin = SIM["run_rule"] / rr["old_reproduced"]["p_early_given_10plus_wmt"]
    d3, d3se = c5["dphi_form"], c5["dphi_form_se"]
    d4, d4se = i4["dphi_vs_binomial"], i4["se"]["dphi"]
    L = []
    w = L.append
    w("# Diagnosis sizes: \"offense extremes compressed\" (real data only)")
    w("")
    w("2026-10-06. Measurement only, no fixes (owner: \"Report sizes only; no fixes yet\"). Script: `scripts/diag_sizes.py`; "
      "machine-readable output: `reports/diagnosis_sizes.json`. Context: `plans/combined_report_2026-10-06.md`, section 1 "
      "(step 1 and candidates 10, 11, 12). Sim values are copied from the 40-season reports of 2026-10-05 "
      "(`reports/phase2.md`, `phase6.md`, `phase7.md`); nothing was simulated. SEs are bootstrap (400 reps over teams or "
      "starters, 200 over games) or binomial where stated.")
    w("")
    w("## Summary")
    w("")
    w("Benchmark definitions (item 1), in row units:")
    w("")
    w("| Row | Benchmark now | Recomputed | SE | Sim | Share of the sim gap closed |")
    w("|---|---|---|---|---|---|")
    w(f"| Run-rule frequency, product estimator, D1-vs-D1 only | {rr['benchmark']:.4f} | {rr['d1_vs_d1']['value']:.4f} | {rr['d1_vs_d1']['se']:.4f} | {SIM['run_rule']:.4f} | {100 * rr['gap_closed_share']:.0f}% |")
    w(f"| Run-rule frequency, direct count, WarrenNolan D1-vs-D1 finals matched to the scoreboard | {rr['benchmark']:.4f} | {wn['matched_to_scoreboard']['value']:.4f} | {wn['matched_to_scoreboard']['se']:.4f} | {SIM['run_rule']:.4f} | {100 * (rr['benchmark'] - wn['matched_to_scoreboard']['value']) / (rr['benchmark'] - SIM['run_rule']):.0f}% (see caveat: the engine reads the same conditional) |")
    w(f"| Runs per team-game, 15+ bin, D1-vs-D1 only | {b15['benchmark']:.4f} | {b15['d1_vs_d1']['value']:.4f} | {b15['d1_vs_d1']['se']:.4f} | {SIM['bin15']:.4f} | {100 * b15['gap_closed_share']:.0f}% |")
    w(f"| Qualified OBP p10, play-by-play without non-D1 games | {obp['benchmark']:.4f} | {obp['d1_vs_d1']['p10']:.4f} | {obp['d1_vs_d1']['tol3se'] / 3:.4f} | {SIM['obp_p10']:.4f} | {100 * obp['gap_closed_share']:.0f}% |")
    w(f"| Team R/G SD (all) | 1.162 | {sd['with_new_orleans_307_teams']:.3f} (New Orleans restored) | 0.047 | {SIM['team_rg_sd']:.3f} | already D1-vs-D1; {100 * (1.162 - sd['with_new_orleans_307_teams']) / (1.162 - SIM['team_rg_sd']):.0f}% |")
    w("")
    w(f"Game-level variance (items 3 and 4), on the dispersion scale: real {REAL_PHI} against sim {SIM_PHI}, missing "
      f"{miss:.4f} (about {sc['missing_raw_variance_runs2']:.2f} runs² per team-game, or {sc['missing_log_variance']:.3f} in log runs).")
    w("")
    w("| Candidate | Real size (Δφ) | SE | Share of the missing .3945 | Running total | 95% upper bound of the share |")
    w("|---|---|---|---|---|---|")
    w(f"| 11. Starter day-to-day form (starters with 5+ starts) | {d3:+.3f} | {d3se:.3f} | {100 * d3 / miss:+.0f}% | {100 * d3 / miss:+.0f}% | {100 * (d3 + 1.96 * d3se) / miss:.0f}% |")
    w(f"| 12. Errors clustering in half-innings | {d4:+.3f} | {d4se:.3f} | {100 * d4 / miss:+.0f}% | {100 * (d3 + d4) / miss:+.0f}% | {100 * (d4 + 1.96 * d4se) / miss:.0f}% |")
    tot_se = float(np.sqrt(d3se ** 2 + d4se ** 2))
    w(f"| Total of 11 and 12 | {d3 + d4:+.3f} | {tot_se:.3f} | {100 * (d3 + d4) / miss:+.0f}% | | {100 * (d3 + d4 + 1.96 * tot_se) / miss:.0f}% |")
    w("")
    w("These are real-data sizes of each mechanism, so they are upper bounds on what each could add to the sim: the sim's own values "
      "of the same measures are not measured here (they come later, on the new engine). Neither candidate is detectably "
      "different from zero.")
    w("")
    w(f"Context from item 3: in the real play-by-play, the covariance between different half-innings of one team-game is worth {split['values']['cross_half_inning']:.2f} ± {split['se']['cross_half_inning']:.2f} "
      f"dispersion units. Two of the starter's innings covary about as much as one of his innings and a bullpen inning of the same game, so it is a game-level part "
      f"(G = {c5['values']['game_shared_G']:.3f} ± {c5['se']['game_shared_G']:.3f} in log variance), not starter-specific. Its sim counterpart is the first thing to measure on the new engine.")
    w("")
    w("Candidate 10 (fielding independent of pitching), in its own units:")
    w("")
    w("| Measure | Real | SE | Engine or sim |")
    w("|---|---|---|---|")
    w(f"| ERA vs errors per game, observed correlation (NCAA.com, {nc['n_teams']} teams) | {nc['model']['era']['obs_corr']:.3f} | {nc['se']['era_obs_corr']:.3f} | sim {SIM['corr_era_e']} |")
    w(f"| Same, true (noise-removed) correlation | {nc['model']['era']['true_corr']:.3f} | {nc['se']['era_true_corr']:.3f} | not measured |")
    w(f"| Same, the real true correlation observed with the sim's run noise (counterfactual) | {nc['counterfactual_obs_corr_with_sim_noise']['era']['runs_noise_x_sim_ratio']:.3f} to {nc['counterfactual_obs_corr_with_sim_noise']['era']['runs_and_errors_noise_x_sim_ratio']:.3f} | | sim {SIM['corr_era_e']} |")
    w(f"| Team error log-odds left after run prevention d, true SD (all corrections) | {er['resid_sd_true_all_corrections']:.3f} | {er['se']['resid_sd_true_all_corrections']:.3f} | engine 0.136 |")
    w(f"| Slope of error log-odds on d (all corrections) | {er['slope_d_all_corrections']:.3f} | {er['se']['slope_d_all_corrections']:.3f} | engine -0.720 |")
    w(f"| Unearned share of runs, 50 best teams by ERA / all teams | {ue['top50_era']['unearned_share']:.3f} / {ue['all']['unearned_share']:.3f} | {ue['top50_era']['se']:.3f} / {ue['all']['se']:.3f} | sim 0.099 / 0.117 (1 − earned shares .901 / .883, means of team shares) |")
    w("")
    cf = nc['counterfactual_obs_corr_with_sim_noise']['era']
    gap = SIM['corr_era_e'] - nc['model']['era']['obs_corr']
    w(f"Of the .072 gap in the ERA-errors correlation, noise attenuation can account for {cf['runs_noise_x_sim_ratio'] - nc['model']['era']['obs_corr']:.3f} to "
      f"{cf['runs_and_errors_noise_x_sim_ratio'] - nc['model']['era']['obs_corr']:.3f} ({100 * (cf['runs_noise_x_sim_ratio'] - nc['model']['era']['obs_corr']) / gap:.0f}% to "
      f"{100 * (cf['runs_and_errors_noise_x_sim_ratio'] - nc['model']['era']['obs_corr']) / gap:.0f}%). The real independent fielding variance is "
      "not larger than the engine's; it is somewhat smaller.")
    w("")

    # ---------------- item 1
    w("## 1. Non-D1 opponents")
    w("")
    w("### (a) How many scoreboard games involve a non-D1 opponent")
    w("")
    w(f"- Method: a side is D1 if its scoreboard name is one of the 307 teams in `data/ncaa_2025/pbp/teams_2025.csv`, with "
      "New Orleans added (that file names it \"LSU New Orleans\"; the scoreboard calls it \"New Orleans\"). This is the same "
      "split as the conference-tag rule in `scripts/build_run_histogram.py`: the two agree on every one of the 16,158 sides.")
    w(f"- Result: **{i1['n_with_non_d1']} of {i1['n_scoreboard_final_games']:,} games** involve a non-D1 opponent "
      f"({i1['n_non_d1_away']} with the non-D1 team listed away, {i1['n_non_d1_home']} home), 1.1%. D1-vs-D1: {i1['n_d1_vs_d1']:,}.")
    w(f"- The plan's \"about 141\" was {i1['n_games_not_both_in_teams_2025_names']} games: the 90 above plus "
      f"{i1['new_orleans_d1_games']} D1-vs-D1 games of New Orleans, which the team-strength fit drops because of the name mismatch "
      "(`scripts/build_phase2_teams.py` `load()` and `build_phase2_gate.py` `team_strength()` filter on the names in teams_2025.csv). "
      "That is why `team_strength_2025` has 306 teams and 7,938 games. Reported, not changed.")
    wc = i1["warrennolan_check"]
    w(f"- WarrenNolan cross-check: {wc['scoreboard_non_d1_games_found_in_wn']} of the 90 games are on the D1 team's WarrenNolan page on the same date, "
      f"and WarrenNolan flags the opponent non-D1 in all {wc['of_which_wn_flags_opponent_non_d1']}. The other 12 are not on WarrenNolan "
      f"(it omits some non-D1 games, as `data/README.md` notes for 2026). WarrenNolan has {wc['wn_final_games_with_non_d1_flag']} final games against "
      "non-D1 opponents; none of its non-D1 opponents is a 2025 D1 team.")
    nd = i1["non_d1_games"]
    w(f"- Those games are lopsided: margin of 10+ in {nd['share_margin_10plus']:.3f} of them (all games .195), the D1 side scores "
      f"{nd['d1_side_runs_mean']:.2f} runs on average, 15+ in {nd['d1_side_share_15plus']:.3f} of them, and wins {nd['d1_side_win_pct']:.3f}.")
    w("")
    w("### (b) Run-rule frequency and the 15+ bin on D1-vs-D1 games")
    w("")
    o, n = rr["old_reproduced"], rr["d1_vs_d1"]
    w(f"- Run rule, the benchmark's product estimator P(margin ≥ 10, scoreboard) × P(ended before the 9th | margin ≥ 10, WMT), SE by the delta method as in `scripts/write_phase2_benchmarks.py`:")
    w(f"  - as committed (reproduced): {o['p_margin_10plus']:.4f} × {o['p_early_given_10plus_wmt']:.4f} = **{o['value']:.4f}** ± {o['se']:.4f} ({o['n_scoreboard_games']:,} scoreboard games; {o['n_wmt_10plus']} WMT 10-run games of {o['n_wmt_games']:,});")
    w(f"  - D1-vs-D1 only (both factors; the WMT factor also loses {rr['wmt_non_d1_games_removed']} games: 14 against non-D1 teams and one 2024 game in the 2025 file): "
      f"{n['p_margin_10plus']:.4f} × {n['p_early_given_10plus_wmt']:.4f} = **{n['value']:.4f}** ± {n['se']:.4f}. Closes {100 * rr['gap_closed_share']:.1f}% of the gap to the sim (.1524 − .1201 = .0323).")
    w(f"- A direct count is possible on a sample almost four times larger: WarrenNolan records innings for every final (blank = 9). On the {2248:,} games it shares with the WMT schedules, its innings equal WMT's in every game. Direct D1-vs-D1 run-rule rate (game ended before the 9th with a margin of 10+, scheduled 7-inning games included as in the benchmark):")
    w(f"  - all {wn['n_games']:,} WarrenNolan D1-vs-D1 finals: **{wn['value']:.4f}** ± {wn['se']:.4f} (P(margin ≥ 10) {wn['p_margin_10plus']:.4f}, P(ended early | margin ≥ 10) {wn['p_early_given_10plus']:.4f} on {wn['n_10plus']:,} games);")
    w(f"  - the {wn['matched_to_scoreboard']['n_games']:,} of them matched to the scoreboard's D1-vs-D1 finals: **{wn['matched_to_scoreboard']['value']:.4f}** ± {wn['matched_to_scoreboard']['se']:.4f};")
    w(f"  - the {wn['n_event_games']} conference-tournament games (WarrenNolan event label; most are placeholders without scores in the scoreboard): {wn['event_games_only']:.4f}.")
    wr = wn["wmt_vs_rest"]
    w(f"- Why the direct count is lower: P(ended early | margin ≥ 10) is {wr['p_early_in_wmt']:.3f} on the {wr['n_in_wmt']} WarrenNolan 10-run games that are in the WMT schedules and "
      f"{wr['p_early_not_in_wmt']:.3f} on the other {wr['n_not_in_wmt']:,} (difference {wr['diff']:.3f} ± {wr['diff_se']:.3f}, about {wr['diff'] / wr['diff_se']:.1f} SE). "
      "It is higher in the WMT games in every tier pair with more than a handful of WMT games, so it is not only tier mix:")
    w("")
    w("  | Tier pair | WarrenNolan n | P(early) | WMT n | P(early) |")
    w("  |---|---|---|---|---|")
    for k, v in wn["p_early_given_10plus_by_tier_pair"].items():
        w(f"  | {k.replace('|', '–')} | {v['wn_n']} | {v['wn_p_early']:.3f} | {v['wmt_n']} | {f3(v['wmt_p_early'])} |")
    w("")
    w("  WMT holds every game of its client programs, so the WMT factor describes those programs' games (their conferences' and opponents' run-rule agreements), not D1 as a whole. "
      "The data cannot say which agreements differ; candidate 1 (run rules by conference) is the place to look.")
    w(f"- **Caveat that limits what a benchmark change buys:** the engine plays the rule with probability `p_run_rule_in_effect` = "
      f"the same WMT conditional ({o['p_early_given_10plus_wmt']:.4f}; `config/phase1.py` reads it from this benchmark entry). If the "
      "benchmark's conditional moves to WarrenNolan's .740, the engine's input moves with it and the sim's run-rule rate falls in proportion. "
      f"What is left is the margin distribution: P(final margin ≥ 10) is {n['p_margin_10plus']:.4f} real (D1-vs-D1) against about "
      f"{sim_margin:.3f} implied for the sim (.1201 / .7805; approximate, since the sim's rule acts after the 7th). Non-D1 games close "
      f"{100 * (o['p_margin_10plus'] - n['p_margin_10plus']) / (o['p_margin_10plus'] - sim_margin):.0f}% of that margin gap.")
    w(f"- 15+ runs bin, P(15+) per D1 team-game, game-cluster SE: committed {b15['old_reproduced']['value']:.4f} ± {b15['old_reproduced']['se']:.4f} "
      f"({b15['old_reproduced']['n_team_games']:,} team-games, reproduced exactly); D1-vs-D1 **{b15['d1_vs_d1']['value']:.4f}** ± {b15['d1_vs_d1']['se']:.4f} "
      f"({b15['d1_vs_d1']['n_team_games']:,} team-games). Closes {100 * b15['gap_closed_share']:.0f}% of the gap (.0664 − .0533). The 90 D1 sides against non-D1 opponents score 15+ at {nd['d1_side_share_15plus']:.3f}.")
    w("")
    w("### (c) Qualified OBP p10")
    w("")
    w("- How it is built (`scripts/build_phase2_gate.py` `qualified()`): qualified batters (2.0 PA per team game, 75% of team games) on the WMT "
      "teams with 40+ parsed games, plus 11 Sidearm full-season pages, each tier weighted by its share of D1 teams, tiers under 50 qualified "
      "players pooled with the nearest; tolerance 3 SE from a team-cluster bootstrap. The WMT part counts every parsed game, including games "
      "against non-D1 opponents.")
    w(f"- Non-D1 games in the parsed play-by-play: {obp['n_pbp_games_removed']} (Hawaii 4: Chaminade twice, Hawaii Hilo, Hawaii Pacific; Iowa 2: Loras, Augustana; Nevada 1: Simpson). "
      "Removed from the games, plate appearances, base-running events and charged runs, and from the team-game counts used by the qualification rule.")
    w(f"- Result (same code, same bootstrap seed; the committed value reproduces exactly): **{obp['committed']['p10']:.4f} → {obp['d1_vs_d1']['p10']:.4f}** "
      f"(3 SE {obp['d1_vs_d1']['tol3se']:.4f}); unpooled {obp['committed']['unpooled_p10']:.4f} → {obp['d1_vs_d1']['unpooled_p10']:.4f}; {obp['d1_vs_d1']['n_batters']} qualified batters either way. "
      f"Closes {100 * obp['gap_closed_share']:.0f}% of the gap to the sim ({SIM['obp_p10']}).")
    w("- Not removable: the 11 Sidearm pages are season totals. By the scoreboard, those teams played 5 non-D1 games in all (Troy 2, Missouri State, Cal Poly, SFA 1 each).")
    w("")
    w("### (d) Team R/G SD")
    w("")
    w(f"- Confirmed D1-vs-D1 only: `team_strength()` in `scripts/build_phase2_gate.py` keeps a team-game only when both teams are in teams_2025.csv. "
      f"Reproduced: {sd['reproduced_306_teams']:.4f} (benchmark 1.162, 306 teams). Non-D1 games cannot move this row.")
    w(f"- The name mismatch drops New Orleans (51 D1 games, {sd['new_orleans_r_per_game']:.2f} R/G). With it restored: {sd['with_new_orleans_307_teams']:.4f} on 307 teams. "
      "SE of the SD about .047 (1.162 / √(2 × 305)).")
    w("")

    # ---------------- item 2
    w("## 2. Fielding independent of pitching (candidate 10)")
    w("")
    w("### (a) Reliability of team ERA and errors per game, and the true correlation")
    w("")
    v, s_ = sh["values"], sh["se"]
    w(f"- **Split halves, WMT box lines.** {sh['n_teams']} teams with 30+ D1-vs-D1 box-score games ({sh['games_per_team_mean']:.1f} on average; "
      "these are WMT's full-season programs, mostly P4). Games in date order, odd against even. Reliability of the full season by Spearman-Brown; true correlation from cross-half "
      "correlations (ERA of one half with errors of the other), which removes the within-game link between errors and runs:")
    w("")
    w("  | | Half-season reliability | Full-season reliability | Observed corr with E/G | True corr with E/G |")
    w("  |---|---|---|---|---|")
    w(f"  | ERA | {v['rel_half_era']:.3f} ± {s_['rel_half_era']:.3f} | {v['rel_full_era']:.3f} ± {s_['rel_full_era']:.3f} | {v['obs_corr_era_eg']:.3f} ± {s_['obs_corr_era_eg']:.3f} | {v['true_corr_era_eg']:.3f} ± {s_['true_corr_era_eg']:.3f} |")
    w(f"  | Runs allowed per game | {v['rel_half_rag']:.3f} ± {s_['rel_half_rag']:.3f} | {v['rel_full_rag']:.3f} ± {s_['rel_full_rag']:.3f} | {v['obs_corr_rag_eg']:.3f} ± {s_['obs_corr_rag_eg']:.3f} | {v['true_corr_rag_eg']:.3f} ± {s_['true_corr_rag_eg']:.3f} |")
    w(f"  | Errors per game | {v['rel_half_eg']:.3f} ± {s_['rel_half_eg']:.3f} | {v['rel_full_eg']:.3f} ± {s_['rel_full_eg']:.3f} | | |")
    w("")
    pg = i2["per_game_noise_wmt"]
    w(f"- **All of D1 (NCAA.com 2025 pages, {nc['n_teams']} teams).** Split halves are not available there, so the noise variance of each team's season "
      f"statistic is computed from its own games, runs and errors with per-game dispersions measured within team on the WMT box lines "
      f"({pg['n_teams']} teams, {pg['n_team_games']:,} team-games): earned runs φ = {pg['phi_er']:.2f}, runs allowed φ = {pg['phi_ra']:.2f}, errors φ = {pg['phi_e']:.2f} "
      f"(variance / mean per game); within-game correlation of errors with earned runs {pg['rho_er_e']:.3f}, with runs allowed {pg['rho_ra_e']:.3f}. "
      "Noise variance, noise covariance and true variance follow; true correlation = (observed covariance − noise covariance) / √(true variances).")
    m = nc["model"]; se2 = nc["se"]
    w("")
    w("  | | Reliability of the stat | Reliability of E/G | Observed corr | True corr |")
    w("  |---|---|---|---|---|")
    w(f"  | ERA | {m['era']['reliability']:.3f} ± {se2['era_reliability']:.3f} | {m['era']['reliability_eg']:.3f} ± {se2['era_reliability_eg']:.3f} | {m['era']['obs_corr']:.3f} ± {se2['era_obs_corr']:.3f} | {m['era']['true_corr']:.3f} ± {se2['era_true_corr']:.3f} |")
    w(f"  | Runs allowed per game | {m['rag']['reliability']:.3f} ± {se2['rag_reliability']:.3f} | {m['rag']['reliability_eg']:.3f} | {m['rag']['obs_corr']:.3f} ± {se2['rag_obs_corr']:.3f} | {m['rag']['true_corr']:.3f} ± {se2['rag_true_corr']:.3f} |")
    w("")
    ck = i2["noise_model_check_on_wmt_split_teams"]
    w(f"  Check of the noise model on the 50 split-half teams: it gives reliabilities {ck['era']['reliability_model']:.3f} (ERA) and {ck['era']['reliability_eg_model']:.3f} (E/G) "
      f"against split-half {v['rel_full_era']:.3f} and {v['rel_full_eg']:.3f}, and a true correlation of {ck['era']['true_corr_model']:.3f} against {v['true_corr_era_eg']:.3f}. They agree within SE. "
      "SEs on the NCAA.com rows are a bootstrap over teams with the noise parameters fixed.")
    w(f"- The NCAA.com observed .655 reproduces. Its true correlation is about {m['era']['true_corr']:.2f}; the 50 WMT teams' {v['true_corr_era_eg']:.2f} is lower because "
      "they cover a narrower range of team quality.")
    w(f"- **How much of the sim's .727 can be noise attenuation.** The sim's game-to-game run variance is lower (dispersion 2.224 against 2.6185). "
      f"Holding the real true spreads and true correlation fixed and shrinking the run noise of ERA by 2.224 / 2.6185 gives an observed correlation of "
      f"{cf['runs_noise_x_sim_ratio']:.3f}; shrinking the error noise by the same ratio as well gives {cf['runs_and_errors_noise_x_sim_ratio']:.3f}. "
      f"That is {cf['runs_noise_x_sim_ratio'] - m['era']['obs_corr']:.3f} to {cf['runs_and_errors_noise_x_sim_ratio'] - m['era']['obs_corr']:.3f} of the .072 gap. "
      f"For runs allowed per game: {nc['counterfactual_obs_corr_with_sim_noise']['rag']['runs_noise_x_sim_ratio']:.3f} to {nc['counterfactual_obs_corr_with_sim_noise']['rag']['runs_and_errors_noise_x_sim_ratio']:.3f} against real .721 and sim .801. "
      "So at most about a quarter of the gap is the sim's lower noise. The rest has to be a tighter true relation in the sim, or wider true team spreads "
      "(the sim has more elite run-prevention teams). The sim's own split-half reliabilities would settle which; they are not measured here.")
    w("")
    w("### (b) True variance of the team error rate left after run prevention")
    w("")
    w("- Model as in `scripts/build_phase6_fielding.py` `team_error()`: y = logit(E / (PO + A + E)) − logit(league rate), weighted by chances, on d from the "
      "scoreboard fit with parks. Run on the NCAA.com pages (every team, full seasons), with three corrections applied in turn:")
    w("")
    w("  | Step | Slope on d | Residual true SD |")
    w("  |---|---|---|")
    w(f"  | Binomial noise only (the PHASE0_NOTES refit; reproduces −.685 / .127) | {er['slope_d_binomial']:.3f} ± {er['se']['slope_d_binomial']:.3f} | {er['resid_sd_true_binomial']:.3f} ± {er['se']['resid_sd_true_binomial']:.3f} |")
    w(f"  | + errors overdispersed against binomial-by-chances (φ = {er['phi_errors_vs_binomial_wmt']:.3f}, WMT within team) | same | {er['resid_sd_true_overdispersed']:.3f} ± {er['se']['resid_sd_true_overdispersed']:.3f} |")
    w(f"  | + noise in d (fit covariance, mean noise variance {er['noise_var_d_mean']:.4f} against true variance of d {er['true_sd_d'] ** 2:.4f}) | {er['slope_d_noise_corrected']:.3f} ± {er['se']['slope_d_noise_corrected']:.3f} | {er['resid_sd_true_overdispersed_d_noise_corrected']:.3f} ± {er['se']['resid_sd_true_overdispersed_d_noise_corrected']:.3f} |")
    w(f"  | + noise shared by errors and d in the same games (an error adds runs allowed; covariance {er['cov_noise_y_d_shared_games']:.4f}) | **{er['slope_d_all_corrections']:.3f}** ± {er['se']['slope_d_all_corrections']:.3f} | **{er['resid_sd_true_all_corrections']:.3f}** ± {er['se']['resid_sd_true_all_corrections']:.3f} |")
    w("")
    w(f"- Independent check, WMT box lines split by game (game id parity): each half's error rate against d refitted on the scoreboard without that half's games, "
      f"so no game noise is shared; true variance of y from the covariance of the two halves. {eb['n_teams']} teams with 8+ games per half: slope "
      f"{eb['slope_d']:.3f} ± {eb['se']['slope_d']:.3f}, residual true variance {eb['resid_var_true']:.4f} ± {eb['se']['resid_var_true']:.4f} (SD {eb['resid_sd_true']:.3f}). "
      f"Consistent with the NCAA.com estimate ({er['resid_var_true_all_corrections']:.4f} ± {er['se']['resid_var_true_all_corrections']:.4f}) but much less precise.")
    w(f"- Against the engine (fielders .119, team .066, total residual .136, slope −.720): the real residual is **{er['resid_sd_true_all_corrections']:.3f} ± {er['se']['resid_sd_true_all_corrections']:.3f}**, "
      f"variance {er['resid_var_true_all_corrections']:.4f} against the engine's {0.1361 ** 2:.4f}, about 2 SE smaller. The true correlation of d with the error log-odds is "
      f"{er['true_corr_d_error_logodds_all_corrections']:.3f} ± {er['se']['true_corr_d_error_logodds_all_corrections']:.3f} real against {i2['error_residual']['engine_implied_true_corr_d_error_logodds']:.3f} implied by the engine's parameters. "
      "So the engine already gives fielding at least as much independence from run prevention as the data shows. Candidate 10 as stated (fielding too tied to pitching in the engine) is not supported by the error model's parameters.")
    w("")
    w("### Unearned runs, low-ERA teams against the rest (NCAA.com 2025, full seasons)")
    w("")
    w("| Group | Teams | Unearned share of runs (Σ(R − ER) / ΣR) | SE | Errors per game | Unearned runs per error |")
    w("|---|---|---|---|---|---|")
    for k, lab in (("top50_era", "50 best by ERA"), ("era_under_4", "ERA under 4.00"), ("rest_after_top50", "the other 249"), ("all", "all")):
        x = ue[k]
        w(f"| {lab} | {x['n_teams']} | {x['unearned_share']:.3f} | {x['se']:.3f} | {x['errors_per_game']:.3f} | {x['unearned_per_error']:.3f} |")
    for q in range(1, 6):
        x = ue[f"era_quintile_{q}"]
        w(f"| ERA quintile {q} | {x['n_teams']} | {x['unearned_share']:.3f} | {x['se']:.3f} | {x['errors_per_game']:.3f} | {x['unearned_per_error']:.3f} |")
    w("")
    w(f"Real low-ERA teams make fewer errors ({ue['top50_era']['errors_per_game']:.2f} against {ue['rest_after_top50']['errors_per_game']:.2f} per game) and fewer unearned runs per error "
      f"({ue['top50_era']['unearned_per_error']:.2f} against {ue['rest_after_top50']['unearned_per_error']:.2f}), but they also allow fewer runs in all, so their unearned share "
      f"({ue['top50_era']['unearned_share']:.3f}) is the same as the other teams' ({ue['rest_after_top50']['unearned_share']:.3f}). The sim's 50 best by ERA have an unearned share of about .099 (earned share .901). The partial correlation of ERA with errors per game "
      f"at equal runs allowed per game is {ue['partial_corr_era_eg_given_rag']:.3f} (real): at fixed total run prevention, teams with more errors have lower ERA, "
      "which is the same partition the engine uses (pitching takes the remainder). The engine's partition can be compared on this row once the sim side is measured.")
    w("")

    # ---------------- item 3
    w("## 3. Starter day-to-day form (candidate 11)")
    w("")
    w("### Method")
    w("")
    w(f"- Unit: a half-inning, from the WMT play-by-play ({i3['n_half_innings']:,} half-innings, {i3['n_games']:,} games; runs from plate appearances plus base-running events "
      "equal the box score in every game). A half-inning belongs to the starter if he faced its first batter; all its runs count, including those after he left.")
    w("- Expectation e_i: the scoreboard fit without parks (the fit whose dispersion is 2.6185) gives each team-game's expected runs; it is spread over innings by the league's "
      "share of runs by inning number, and scaled so the sample's expected and observed totals agree. Residual r_i = runs − e_i.")
    w("- A shared multiplicative effect of log-variance σ² on a group of half-innings gives cov(r_i, r_j) = e_i e_j σ² for any two of them. Each component is estimated as "
      "Σ r_i r_j / Σ e_i e_j over one type of pair, all pairs within one batting team:")
    w("  - A: two half-innings of the same start (talent P + form F + the game's shared part G);")
    w("  - B: the same starter's half-innings in two different games (P);")
    w("  - C: a starter half-inning and a relief half-inning of the same game (G, plus the covariance of the starter's and the bullpen's deviations from team d);")
    w("  - Cb: the same starter's half-innings in one game with relief half-innings in another of his starts (that covariance alone);")
    w("  - F = (A − B) − (C − Cb). G is the batting team's day, park and weather, umpire and the fielding team's day together.")
    w("- Bootstrap over starters (400). Conversion to the dispersion scale: a start-level effect adds F × (Σ e over the starter's half-innings)² to the team-game's variance, so Δφ = F × mean((Σ e_S)² / E_team-game).")
    w("")
    w("### Results")
    w("")
    w("| | Starters with 5+ starts | 10+ starts |")
    w("|---|---|---|")
    w(f"| Starters / starts | {c5['n_starters']} / {c5['n_starts']:,} | {c10['n_starters']} / {c10['n_starts']:,} |")
    for k, lab in (("A_within_start", "A within start"), ("B_same_starter_other_games", "B = P, same starter other games"),
                   ("C_same_game_starter_x_relief", "C same game, starter × relief"), ("Cb_same_starter_other_games_x_relief", "Cb"),
                   ("game_shared_G", "G = C − Cb, game's shared part"), ("form_F", "**F, start-level form**")):
        w(f"| {lab} | {c5['values'][k]:+.4f} ± {c5['se'][k]:.4f} | {c10['values'][k]:+.4f} ± {c10['se'][k]:.4f} |")
    w(f"| Δφ from F | {c5['dphi_form']:+.3f} ± {c5['dphi_form_se']:.3f} | {c10['dphi_form']:+.3f} ± {c10['dphi_form_se']:.3f} |")
    w(f"| Share of the missing .3945 | {100 * c5['dphi_form'] / miss:+.0f}% ± {100 * c5['dphi_form_se'] / miss:.0f}% | {100 * c10['dphi_form'] / miss:+.0f}% ± {100 * c10['dphi_form_se'] / miss:.0f}% |")
    w("")
    w(f"- Form is not detectable: F is {c5['values']['form_F']:+.3f} ± {c5['values']['form_F'] * 0 + c5['se']['form_F']:.3f} (5+ starts) and {c10['values']['form_F']:+.3f} ± {c10['se']['form_F']:.3f} (10+). "
      "Almost all of the covariance inside a start (A) is also present between the starter's innings and the bullpen's innings of the same game (C): it belongs to the game, not to the starter. "
      f"The 95% upper bound on form's share of the missing variance is about {100 * (c5['dphi_form'] + 1.96 * c5['dphi_form_se']) / miss:.0f}% (5+ starts) or {100 * (c10['dphi_form'] + 1.96 * c10['dphi_form_se']) / miss:.0f}% (10+).")
    j = i3["innings_1_3_vs_4_6"]
    w(f"- Innings 1–3 against 4–6 (starts in which the starter began innings 1, 2 and 3 and at least one of 4–6; correlation of residual sums): same start "
      f"{j['same_start']['r']:.3f} ± {j['same_start']['se']:.3f} (n {j['same_start']['n']:,}); his next start's 4–6 {j['next_start_same_starter']['r']:.3f} ± {j['next_start_same_starter']['se']:.3f} "
      f"(talent); relief innings 7–9 of the same game {j['same_game_relief_7_9']['r']:.3f} ± {j['same_game_relief_7_9']['se']:.3f} (game). "
      f"Beyond talent and the game, about {j['same_start']['r'] - j['next_start_same_starter']['r'] - j['same_game_relief_7_9']['r']:+.3f}, within its SE (about .035).")
    w(f"- Dispersions (runs around the fit, no pitcher term unless stated): half-innings {i3['dispersion_half_inning_all']:.2f}; half-innings begun by the starter "
      f"{i3['dispersion_half_inning_starter']:.2f}; per start (sum of his half-innings, {i3['innings_begun_per_start_mean']:.2f} on average) {i3['dispersion_per_start']:.2f}; "
      f"per start with a pitcher term (each starter's season ratio, 5+ starts, {i3['n_starts_pitcher_term']:,} starts) {i3['dispersion_per_start_pitcher_term']:.2f}. "
      "The rise from half-inning to start is the cross-inning covariance (P, G, F); the decomposition above assigns it to G.")
    w("- Caveats: a starter is pulled after bad innings, so bad days contribute fewer within-start pairs, which biases F (and A) down. The pairing C uses relief innings, which are "
      "later in the game; if game conditions change during a game, G from C is smaller than the G inside a start and F is biased up. The WMT sample is 59% P4.")
    w("")
    vv, ss = split["values"], split["se"]
    w("### Where the real cross-inning covariance sits (context for the sim side)")
    w("")
    w(f"Exact split of the team-game dispersion in the WMT sample ({split['n_team_games']:,} team-games, runs around the same expectation): total "
      f"{vv['phi_team_game']:.2f} ± {ss['phi_team_game']:.2f} (above the scoreboard's 2.62: different sample, P4-heavy); inside half-innings {vv['within_half_inning']:.2f} ± {ss['within_half_inning']:.2f}; "
      f"between half-innings of the same team-game {vv['cross_half_inning']:.2f} ± {ss['cross_half_inning']:.2f}, of which starter × starter {vv['cross_starter_starter']:.2f}, "
      f"starter × relief {vv['cross_starter_relief']:.2f}, relief × relief {vv['cross_relief_relief']:.2f}. The sim's total 2.224 is below this sample's within-half-inning part alone "
      "(the bases differ: the WMT total is 2.81 against the scoreboard's 2.62, so this is an indication, not a comparison). "
      "Measuring the same split on the sim (the runs-per-half-inning distribution already passes its Phase 1 gate) would show whether the missing .39 sits between half-innings, "
      "i.e. in the game's shared part G, which no single-pitcher or single-play mechanism supplies.")
    w("")

    # ---------------- item 4
    w("## 4. Errors clustering into big innings (candidate 12)")
    w("")
    w(f"- Data: {i4['n_half_innings']:,} half-innings with at least one chance, {i4['n_games']:,} games, {i4['errors']:,} errors on {i4['error_plays']:,} plays "
      "(fielder credits from `fielding_2025.csv.gz`; they equal the box-score errors in 99.96% of team-games). Unearned runs from `runs_charged_2025.csv.gz`.")
    w("- Expectations: Poisson with the fielding team's errors per half-inning; binomial with the half-inning's chances (PO + A + E) and the team's errors per chance. "
      "The binomial already gives long innings more errors, including the chances an error itself creates.")
    w("")
    w("| Errors in the half-inning | 0 | 1 | 2 | 3+ |")
    w("|---|---|---|---|---|")
    w("| Observed | " + " | ".join(f"{x:.4f}" for x in i4["dist"]["observed"]) + " |")
    w("| Poisson, team rate | " + " | ".join(f"{x:.4f}" for x in i4["dist"]["poisson_team_rate"]) + " |")
    w("| Binomial by chances | " + " | ".join(f"{x:.4f}" for x in i4["dist"]["binomial_by_chances"]) + " |")
    w("| Mean runs | " + " | ".join(f"{x:.3f}" for x in i4["runs_given_errors"]["mean_runs"]) + " |")
    w("| P(3+ runs) | " + " | ".join(f"{x:.3f}" for x in i4["runs_given_errors"]["p_3plus_runs"]) + " |")
    w("| Half-innings | " + " | ".join(f"{x:,}" for x in i4["runs_given_errors"]["n"]) + " |")
    w("")
    s4 = i4["se"]
    w(f"- Share of half-innings with 2+ errors: observed {i4['share_2plus']['observed']:.4f} ± {s4['obs2']:.4f}, Poisson {i4['share_2plus']['poisson']:.4f}, binomial "
      f"{i4['share_2plus']['binomial']:.4f} ± {s4['bin2']:.4f}; ratio observed / binomial **{i4['ratio_2plus_obs_over_binomial']:.2f} ± {s4['ratio2']:.2f}**. Counting error plays instead of errors "
      f"(two errors on one play count once): {i4['share_2plus']['observed_plays']:.4f} against {i4['share_2plus']['binomial_plays']:.4f}, so double-error plays are a small part of it.")
    w(f"- P(3+ run half-inning | at least one error) {i4['p_3plus_given_any_error']:.3f} ± {s4['p3_err']:.3f}; P(3+ | no error) {i4['p_3plus_given_no_error']:.3f} ± {s4['p3_noerr']:.3f}.")
    w(f"- Unearned runs per error {i4['unearned_per_error']:.3f} ± {s4['ue_per_e']:.3f} (NCAA.com, all D1: .769); by errors in the half-inning: 1: {i4['unearned_per_error_by_k']['1']:.3f}, 2: {i4['unearned_per_error_by_k']['2']:.3f}, 3+: {i4['unearned_per_error_by_k']['3']:.3f}.")
    w(f"- Errors per team-game: variance around the binomial-by-chances expectation {i4['errors_per_team_game']['var_around_binomial_expectation']:.3f} against binomial {i4['errors_per_team_game']['binomial_variance']:.3f} (mean {i4['errors_per_team_game']['mean']:.3f}).")
    w(f"- **Variance contribution.** Runs per half-inning mixed over the observed error-count distribution have variance {i4['var_runs_per_half_inning']['observed_mix']:.4f}; over the binomial "
      f"distribution {i4['var_runs_per_half_inning']['binomial_mix']:.4f} (means equal to 4 decimals). Times {i4['half_innings_per_team_game']:.2f} half-innings per team-game: "
      f"{i4['dvar_team_game_vs_binomial']:.3f} runs² per team-game; over {i4['runs_per_team_game']:.2f} runs per team-game: **Δφ = {d4:.4f} ± {d4se:.4f}**, "
      f"{100 * d4 / miss:.1f}% of the missing .3945 (against Poisson: {i4['dphi_vs_poisson']:.4f}). It credits every run difference between multi-error and single-error "
      "half-innings to the clustering (multi-error half-innings are also long ones), so it is an upper bound.")
    w("")

    # ---------------- what's not measured
    w("## Not measured here")
    w("")
    w("- Every sim-side counterpart: split-half reliabilities, the error residual as the sim realizes it, F and G, the error-count distribution per half-inning, and the "
      "within/between half-inning split of the sim's dispersion. They need sim play-by-play, which waits for the new engine (no season was simulated here).")
    w("- Step 0 (offense / pitching / shared split by weekend and conference) and candidates 1, 3, 4, 5, 7 were not part of this task.")
    w("- Sidearm season totals cannot be split by opponent (item 1c).")
    w("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
