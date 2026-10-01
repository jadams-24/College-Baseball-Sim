"""Phase 4 round trip: estimate ratings back from simulated season stats and compare them
with the true ratings the players were generated from.

The estimator sees only what a season's box scores give: each player's counting stats, the
league's results by batting team x pitching team, home and away, and which teams each player
faced at home and away.
  1. Opponent strength: an additive logit fit of every batting team x pitching team x home
     rate, logit p = a + B_i + P_j + eta * (+1 home, -1 away) (binomial, Newton). Adjusting by
     opponent team rather than opponent tier matters: within a tier, schedules differ by
     conference and team, and unadjusted schedule strength would be read as talent.
  2. Each player's baseline: the opponents he himself faced, home and away, weighted by the
     rating's own trials (plate appearances; balls in play for Contact; hits for Gap): the
     mean and spread of their logits, the spread including the variation of individual
     players inside an opposing team (Phase 2 individual SDs). The likelihood averages over
     that spread (engine.eb.binomial_mix_loglik): with mixed opponents a player's talent moves
     his expected count by less than a single average opponent implies, and ignoring it
     compresses the estimates. (A midweek starter's opponents are not his team's average,
     and hits pile up against weak pitching.)
     His offset z has a normal prior per role group and tier, fitted by marginal maximum
     likelihood on all simulated seasons pooled; for bench players, whose few trials leave
     the spread unidentified within one tier, the SD is shared across tiers
     (config.phase4.SHARED_TAU_ROLES). His estimate is the posterior mean (engine.eb).
     Stamina: the same with the discrete-time pull-hazard likelihood, prior per role.
  3. Anchor: 50 is the D1 average, so offsets are centred on their PA- (BF-) weighted mean,
     an observable, then rating = 50 + 10 * sign * (z - anchor) / s (the rating scale's SD).
The estimator runs on folds of FOLD_SEASONS seasons, each fitting its own priors (one season
leaves bench spreads unidentified; folds keep the replicates independent, so the standard
error across folds includes the priors' own sampling error).
Gate statistics per rating, players with enough trials (config.phase4.MIN_TRIALS):
  slope of true rating on estimated rating (1 when the estimates are calibrated), mean bias
  (true - estimated), and residual SD over the SD the estimator itself predicts (posterior
  SD): 1 when sampling noise is removed exactly, not double-counted or ignored.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

from config import phase2
from config.phase2 import GAMES_PER_WEEKEND, N_BENCH, N_REGULARS, SEASON_GAMES, TIERS, WEEKS
from config.phase4 import (BATTER_RATINGS, CENTER, FOLD_SEASONS, FOLD_WORKERS, GATE_COVERAGE, MIN_TRIALS, PITCHER_RATINGS, POINTS_PER_SD,
                           SHARED_TAU_ROLES, STAMINA_ROLE)
from engine import eb
from engine.game2 import (B_2B, B_3B, B_AB, B_BB, B_G, B_H, B_HBP, B_HR, B_K, B_PA, B_ROE, B_SF, B_SH, CELL_RESULTS, P_BB, P_BF, P_ER, P_G,
                          P_GS, P_HR, P_K, P_OUTS)
from engine.ratings import RatingScale, display, rating_names

ROOT = Path(__file__).resolve().parents[1]
C = {r: i for i, r in enumerate(CELL_RESULTS)}


def _logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def _expit(x):
    return 1 / (1 + np.exp(-x))


def _cell_rates(cell: np.ndarray, rate: str) -> tuple[np.ndarray, np.ndarray]:
    hits = cell[..., C["1B"]] + cell[..., C["2B"]] + cell[..., C["3B"]]
    if rate in ("K", "BB", "HR", "HBP"):
        n = cell.sum(axis=-1); x = cell[..., C[rate]]
    elif rate == "BABIP":
        n = hits + cell[..., C["OUT"]]; x = hits
    else:  # XBH
        n = hits; x = cell[..., C["2B"]] + cell[..., C["3B"]]
    return x.astype(float), n.astype(float)


def _team_fit(x: np.ndarray, n: np.ndarray, iters: int = 40) -> tuple[float, np.ndarray, np.ndarray, float]:
    """Binomial logit p_ijh = a + B_i + P_j + eta * s_h over batting team i x pitching team j x
    batting at home (s = +1) or away (s = -1); Newton on the structured Hessian for (a, B, P),
    then a Newton step for eta. B centred on batting PA, P on pitching BF."""
    T = n.shape[0]
    s = np.array([-1.0, 1.0])
    a, B, P, eta = float(_logit(x.sum() / n.sum())), np.zeros(T), np.zeros(T), 0.0
    for _ in range(iters):
        mu = _expit(a + B[:, None, None] + P[None, :, None] + eta * s[None, None, :])
        r3, w3 = x - n * mu, n * mu * (1 - mu)
        r, w = r3.sum(axis=2), w3.sum(axis=2)
        g = np.concatenate([[r.sum()], r.sum(axis=1), r.sum(axis=0)])
        H = np.zeros((2 * T + 1, 2 * T + 1))
        H[0, 0] = w.sum()
        H[0, 1:T + 1] = H[1:T + 1, 0] = w.sum(axis=1)
        H[0, T + 1:] = H[T + 1:, 0] = w.sum(axis=0)
        H[1:T + 1, 1:T + 1] = np.diag(w.sum(axis=1))
        H[T + 1:, T + 1:] = np.diag(w.sum(axis=0))
        H[1:T + 1, T + 1:] = w
        H[T + 1:, 1:T + 1] = w.T
        d = np.linalg.lstsq(H, g, rcond=None)[0]
        a, B, P = a + d[0], B + d[1:T + 1], P + d[T + 1:]
        mu = _expit(a + B[:, None, None] + P[None, :, None] + eta * s[None, None, :])
        de = float((s * (x - n * mu)).sum() / (n * mu * (1 - mu)).sum())
        eta += de
        if np.max(np.abs(d)) < 1e-9 and abs(de) < 1e-9:
            break
    nb, np_ = n.sum(axis=(1, 2)), n.sum(axis=(0, 2))
    cb, cp = float(nb @ B / nb.sum()), float(np_ @ P / np_.sum())
    return a + cb + cp, B - cb, P - cp, eta


def _recovery(true: np.ndarray, est: np.ndarray, psd: np.ndarray) -> dict:
    slope = float(np.polyfit(est, true, 1)[0]) if len(est) > 2 and np.std(est) > 0 else float("nan")
    resid = true - est
    return {"n": int(len(true)), "slope": slope, "bias": float(resid.mean()), "resid_sd": float(resid.std()),
            "pred_sd": float(np.sqrt(np.mean(psd ** 2))), "sd_ratio": float(resid.std() / np.sqrt(np.mean(psd ** 2))),
            "reliability": float(np.polyfit(true, est, 1)[0]) if np.std(true) > 0 else float("nan")}


def _within_team_var(cfg) -> dict:
    """Spread of the opposing players a batter (pitcher) faces inside one opposing team, per
    rate: usage-weighted variance of the opposing staff's (lineup's) individual offsets around
    the team mean, from the Phase 2 talent estimates (group means and individual SDs). Team
    means are in the team fit; this is the part a box score cannot attribute."""
    tal, u = cfg.talent, cfg.usage
    wk = WEEKS * GAMES_PER_WEEKEND / SEASON_GAMES
    pit_share = {"sp_weekend": u["starter_bf_share"]["weekend"] * wk, "sp_midweek": u["starter_bf_share"]["midweek"] * (1 - wk)}
    pit_share["rp"] = 1 - sum(pit_share.values())
    starts = [u["batter_start_share_by_rank"][str(k + 1)] for k in range(N_REGULARS + N_BENCH)]
    bat_share = {"regular": sum(starts[:N_REGULARS]) / sum(starts), "bench": sum(starts[N_REGULARS:]) / sum(starts)}
    out = {}
    for side, opp, shares in (("bat", "pitcher", pit_share), ("pit", "batter", bat_share)):
        for rate in ("K", "BB", "HR", "BABIP", "XBH"):
            if rate not in tal[opp]:
                out[(side, rate)] = 0.0
                continue
            g = tal[opp][rate]["groups"]
            mbar = sum(sh * g[k]["mu_logit"] for k, sh in shares.items())
            out[(side, rate)] = float(sum(sh * (g[k]["sd_ind_logit"] ** 2 + (g[k]["mu_logit"] - mbar) ** 2) for k, sh in shares.items()))
    return out


def season_extract4(res: dict, scale: RatingScale | None = None) -> dict:
    """Everything the round trip needs from one simulated season: per rating, each player's
    true rating, his count and trials, his baseline logit and his prior group; the true
    rating distributions; example cards. Estimation runs on all seasons pooled (aggregate4)."""
    scale = scale or RatingScale()
    lg, b, p = res["league"], res["bstats"], res["pstats"]
    team = {t.tid: t for t in lg.teams}
    bats = [x for x in lg.players if x.side == "bat"]
    pits = [x for x in lg.players if x.side == "pit"]
    tcell = res["team_cell"].astype(float)
    trials = res["opp_trials"]
    within = _within_team_var(phase2.load())
    sgn = np.array([-1.0, 1.0])
    out = {"ratings": {}, "true_dist": {}}
    for side, players, defs, stats in (("bat", bats, BATTER_RATINGS, b), ("pit", pits, PITCHER_RATINGS, p)):
        ids = np.array([x.pid for x in players])
        st = stats[ids]
        groups = np.array([f"{x.group}|{team[x.team].tier}" for x in players])
        for name, rate, sign in defs:
            xc, nc = _cell_rates(tcell, rate)
            a, B, P, eta = _team_fit(xc, nc)
            opp = P if side == "bat" else B
            # each player's own opponents, home and away, weighted by this rating's trials:
            # the rate an average D1 player would post against exactly that schedule
            kind_i = 0 if (side == "pit" or rate in ("K", "BB", "HR")) else (1 if rate == "BABIP" else 2)
            W = trials[ids, :, :, kind_i].astype(float)
            c = a + opp[:, None] + eta * sgn[None, :]                 # opposing team x home logit
            tot = np.maximum(W.sum(axis=(1, 2)), 1)
            m_ = (W * c[None]).sum(axis=(1, 2)) / tot
            v_ = (W * (c[None] - m_[:, None, None]) ** 2).sum(axis=(1, 2)) / tot + within[(side, rate)]
            if side == "bat":
                if rate in ("K", "BB", "HR"):
                    x, n = st[:, {"K": B_K, "BB": B_BB, "HR": B_HR}[rate]], st[:, B_PA]
                elif rate == "BABIP":
                    x, n = st[:, B_H] - st[:, B_HR], st[:, B_AB] - st[:, B_HR] - st[:, B_K] - st[:, B_ROE] + st[:, B_SF] + st[:, B_SH]
                else:
                    x, n = st[:, B_2B] + st[:, B_3B], st[:, B_H] - st[:, B_HR]
                kind = "PA" if rate in ("K", "BB", "HR") else ("BIP" if rate == "BABIP" else "HITS")
            else:
                x, n = st[:, {"K": P_K, "BB": P_BB, "HR": P_HR}[rate]], st[:, P_BF]
                kind = "BF"
            keep = n > 0
            m, s_ = scale.ms(side, rate)
            out["ratings"][name] = {"x": x[keep].astype(float), "n": n[keep].astype(float), "m": m_[keep], "v": v_[keep], "group": groups[keep],
                                    "true": np.array([players[i].ratings[name] for i in np.where(keep)[0]]),
                                    "q": n[keep] >= MIN_TRIALS[kind], "sign": sign, "s": s_}
        # true rating distributions: D1 (PA/BF weighted) and by tier for everyday players
        wcol = B_PA if side == "bat" else P_BF
        w = st[:, wcol].astype(float)
        everyday = "regular" if side == "bat" else "sp_weekend"
        for name in rating_names(side):
            if name == "speed":
                continue
            v = np.array([x.ratings[name] for x in players])
            d = {"d1_weighted_mean": float(np.average(v, weights=w)) if w.sum() else float("nan"),
                 "d1_weighted_sd": float(np.sqrt(np.average((v - np.average(v, weights=w)) ** 2, weights=w))) if w.sum() else float("nan")}
            for t in TIERS:
                sel = np.array([x.group == everyday and team[x.team].tier == t for x in players])
                d[f"{t}_everyday_mean"] = float(v[sel].mean())
            out["true_dist"][name] = d
    # stamina: the pull-decision likelihood is built here (it needs every pull's hazard)
    surv, pulls = res["leash_survive"], res["leash_pulls"]
    cand = [x for x in pits if (x.pid in surv or x.pid in pulls)]
    ll = eb.hazard_loglik(np.array([surv.get(x.pid, 0.0) for x in cand]), [pulls.get(x.pid, []) for x in cand])
    out["stamina"] = {"loglik": ll.astype(np.float32), "group": np.array([STAMINA_ROLE[x.group] for x in cand]),
                      "pgroup": np.array([x.group for x in cand]), "true": np.array([x.ratings["stamina"] for x in cand]),
                      "q": np.array([p[x.pid][P_G] for x in cand]) >= MIN_TRIALS["APPS"]}
    out["cards"] = _cards(res, scale)
    return out


def _cards(res: dict, scale: RatingScale) -> list:
    lg, b, p = res["league"], res["bstats"], res["pstats"]
    team = {t.tid: t for t in lg.teams}
    g = {t.tid: c for t, c in ((t, sum(1 for r in res["team_game_rows"] if int(r[0]) == t.tid)) for t in lg.teams)}

    def bline(x):
        s = b[x.pid]
        ab, h, bb, hbp, sf, pa = s[B_AB], s[B_H], s[B_BB], s[B_HBP], s[B_SF], s[B_PA]
        tb = h + s[B_2B] + 2 * s[B_3B] + 3 * s[B_HR]
        avg = h / ab if ab else 0
        obp = (h + bb + hbp) / (ab + bb + hbp + sf) if pa else 0
        return (f"{int(s[B_G])} G, {int(pa)} PA, {avg:.3f}/{obp:.3f}/{tb / ab if ab else 0:.3f}, {int(s[B_HR])} HR, "
                f"{bb / pa:.1%} BB, {s[B_K] / pa:.1%} K") if pa else "did not play"

    def pline(x):
        s = p[x.pid]
        ip = s[P_OUTS] / 3
        if not ip:
            return "did not pitch"
        whole = int(s[P_OUTS] // 3); frac = int(s[P_OUTS] % 3)
        return (f"{int(s[P_G])} G, {int(s[P_GS])} GS, {whole}.{frac} IP, {9 * s[P_ER] / ip:.2f} ERA, {9 * s[P_K] / ip:.1f} K/9, "
                f"{9 * s[P_BB] / ip:.1f} BB/9, {9 * s[P_HR] / ip:.1f} HR/9")

    def ops(x):
        s = b[x.pid]
        if s[B_PA] < 2 * g[x.team]:
            return -1
        obp = (s[B_H] + s[B_BB] + s[B_HBP]) / max(1, s[B_AB] + s[B_BB] + s[B_HBP] + s[B_SF])
        return obp + (s[B_H] + s[B_2B] + 2 * s[B_3B] + 3 * s[B_HR]) / max(1, s[B_AB])
    bats = [x for x in lg.players if x.side == "bat"]
    pits = [x for x in lg.players if x.side == "pit"]
    reg = lambda t: [x for x in bats if x.group == "regular" and team[x.team].tier == t and ops(x) > 0]
    picks = []
    picks.append(("Best P4 hitter (OPS, qualified)", max(reg("p4"), key=ops)))
    mids = sorted(reg("mid"), key=ops); picks.append(("Median mid-major regular", mids[len(mids) // 2]))
    lows = sorted(reg("low"), key=ops); picks.append(("Median low-tier regular", lows[len(lows) // 2]))
    picks.append(("Home-run leader", max(bats, key=lambda x: b[x.pid][B_HR])))
    picks.append(("Highest true Contact, qualified", max([x for x in bats if ops(x) > 0], key=lambda x: x.ratings["contact"])))
    picks.append(("Bench player with most PA", max([x for x in bats if x.group == "bench"], key=lambda x: b[x.pid][B_PA])))
    era = lambda x: 9 * p[x.pid][P_ER] / (p[x.pid][P_OUTS] / 3) if p[x.pid][P_OUTS] >= 3 * g[x.team] else 99
    sp = lambda t: [x for x in pits if x.group == "sp_weekend" and team[x.team].tier == t and p[x.pid][P_OUTS] >= 3 * g[x.team]]
    picks.append(("Best P4 weekend starter (ERA, qualified)", min(sp("p4"), key=era)))
    mids_p = sorted(sp("mid"), key=era); picks.append(("Median mid-major weekend starter", mids_p[len(mids_p) // 2]))
    picks.append(("Low-tier reliever with most innings", max([x for x in pits if x.group == "rp" and team[x.team].tier == "low"], key=lambda x: p[x.pid][P_OUTS])))
    picks.append(("Starter with the highest true Stamina", max([x for x in pits if x.group.startswith("sp")], key=lambda x: x.ratings["stamina"])))
    cards = []
    for label, x in picks:
        tm = team[x.team]
        rat = {n: display(x.ratings.get(n)) for n in rating_names(x.side)}
        cards.append({"label": label, "name": x.name, "team": tm.name, "tier": tm.tier, "role": x.group, "ratings": rat,
                      "line": bline(x) if x.side == "bat" else pline(x)})
    return cards


def _estimate(ex: list, scale: RatingScale) -> dict:
    """Run the estimator on a set of seasons pooled: fit priors, posterior for every player,
    anchor; return recovery statistics over the qualifying players, and the priors."""
    stats, priors = {}, {}
    for name in ex[0]["ratings"]:
        d = [e["ratings"][name] for e in ex]
        cat = lambda k: np.concatenate([x[k] for x in d])
        grp = cat("group")
        role = np.array([g.split("|")[0] for g in grp])
        xs, ns, ms, vs = cat("x"), cat("n"), cat("m"), cat("v")
        mean, sd = np.zeros(len(xs)), np.zeros(len(xs))
        for r_ in np.unique(role):          # one role at a time keeps the likelihood grid in memory
            i = np.where(role == r_)[0]
            # bench spreads are not identified per tier (few trials each): one SD across tiers there
            f = eb.fit(eb.binomial_mix_loglik(xs[i], ns[i], ms[i], vs[i]), grp[i], role[i] if r_ in SHARED_TAU_ROLES else grp[i])
            mean[i], sd[i] = f["mean"], f["sd"]
            priors.setdefault(name, {}).update({g: {k: round(v, 4) for k, v in pr.items()} for g, pr in f["prior"].items()})
        anchor = float(np.average(mean, weights=ns))   # the D1 average, measured on the estimates
        s_, sign = d[0]["s"], d[0]["sign"]
        est = CENTER + POINTS_PER_SD * sign * (mean - anchor) / s_
        psd = POINTS_PER_SD * sd / s_
        q, true = cat("q"), cat("true")
        # 50 is the D1 average of this simulated world on both sides: the estimates are anchored on
        # the league's own average, so the true ratings are measured from the realized average too
        true = true - (np.average(true, weights=ns) - CENTER)
        stats[name] = _recovery(true[q], est[q], psd[q])
    st = [e["stamina"] for e in ex]
    f = eb.fit(np.concatenate([x["loglik"] for x in st]).astype(float), np.concatenate([x["group"] for x in st]))
    pg = np.concatenate([x["pgroup"] for x in st])
    est = np.array([scale.stamina_rating(g, lt) for g, lt in zip(pg, f["mean"])])
    psd = np.array([POINTS_PER_SD * sdv / scale.stamina[STAMINA_ROLE[g]]["log_sd"] for g, sdv in zip(pg, f["sd"])])
    q = np.concatenate([x["q"] for x in st])
    stats["stamina"] = _recovery(np.concatenate([x["true"] for x in st])[q], est[q], psd[q])
    priors["stamina"] = {g: {k: round(v, 4) for k, v in pr.items()} for g, pr in f["prior"].items()}
    return {"stats": stats, "priors": priors}


def aggregate4(ex: list, scale: RatingScale | None = None) -> dict:
    """Replicate the estimator over folds of FOLD_SEASONS seasons (each fits its own priors) and
    report the mean and standard error of each recovery statistic across folds."""
    scale = scale or RatingScale()
    n = len(ex)
    k = max(1, n // FOLD_SEASONS)
    folds = [ex[i * FOLD_SEASONS:(i + 1) * FOLD_SEASONS] if k > 1 else ex for i in range(k)]
    if k > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(FOLD_WORKERS) as pool:
            runs = list(pool.map(_estimate, folds, [scale] * k))
    else:
        runs = [_estimate(folds[0], scale)]
    out = {"n_seasons": n, "n_folds": k, "ratings": {}, "true_dist": {}, "cards": ex[0]["cards"], "priors": runs[0]["priors"]}
    for name in runs[0]["stats"]:
        agg = {}
        for key in ("slope", "bias", "sd_ratio", "resid_sd", "pred_sd", "reliability", "n"):
            v = np.array([r["stats"][name][key] for r in runs], float)
            agg[key] = {"mean": float(np.nanmean(v)), "se": float(np.nanstd(v, ddof=1) / np.sqrt(k)) if k > 1 else 0.0}
        agg["n"]["mean"] /= len(folds[0])     # players per season
        out["ratings"][name] = agg
    for name in ex[0]["true_dist"]:
        out["true_dist"][name] = {kk: float(np.mean([e["true_dist"][name][kk] for e in ex])) for kk in ex[0]["true_dist"][name]}
    return out


def build_report4(agg: dict, seeds: list, phase2_status: dict) -> tuple[str, dict]:
    st, rows = {}, []
    from engine.report2 import _t_quantile
    k = _t_quantile((1 + GATE_COVERAGE) / 2, agg["n_folds"] - 1) if agg["n_folds"] > 1 else float("inf")
    for name, r in agg["ratings"].items():
        sl, bi, sr = r["slope"], r["bias"], r["sd_ratio"]
        ok_s = abs(sl["mean"] - 1) <= k * sl["se"]
        ok_b = abs(bi["mean"]) <= k * bi["se"]
        ok_r = abs(sr["mean"] - 1) <= k * sr["se"]
        st[f"rt_{name}_slope"], st[f"rt_{name}_bias"], st[f"rt_{name}_sd_ratio"] = bool(ok_s), bool(ok_b), bool(ok_r)
        f = lambda x, nd=3: f"{x['mean']:.{nd}f} ± {k * x['se']:.{nd}f}"
        rows.append(f"| {name} | {int(r['n']['mean'])} | {f(sl)} | {'pass' if ok_s else 'FAIL'} | {f(bi, 2)} | {'pass' if ok_b else 'FAIL'} | "
                    f"{r['resid_sd']['mean']:.2f} / {r['pred_sd']['mean']:.2f} | {f(sr)} | {'pass' if ok_r else 'FAIL'} | {r['reliability']['mean']:.2f} |")
    sane = []
    for name, d in agg["true_dist"].items():
        ok = d["p4_everyday_mean"] > d["mid_everyday_mean"] > d["low_everyday_mean"] and d["p4_everyday_mean"] > CENTER > d["low_everyday_mean"]
        st[f"dist_{name}"] = bool(ok) if name != "stamina" else None
        sane.append(f"| {name} | {d['d1_weighted_mean']:.1f} | {d['d1_weighted_sd']:.1f} | {d['p4_everyday_mean']:.1f} | {d['mid_everyday_mean']:.1f} | "
                    f"{d['low_everyday_mean']:.1f} | {'—' if name == 'stamina' else ('pass' if ok else 'FAIL')} |")
    p2_ok = all(v for v in phase2_status.values() if v is not None)
    st["phase2_gate"] = bool(p2_ok)
    gate_ok = all(v for v in st.values() if v is not None)
    md = ["# Phase 4 realism report: 20–80 ratings", "",
          f"{agg['n_seasons']} simulated seasons, seeds {seeds[0]}–{seeds[-1]}, players generated from ratings. Generated {dt.date.today().isoformat()}.",
          "Ratings re-express the true rates the engine uses: 50 is the D1 average (PA- or BF-weighted), 10 points one true-talent SD, all of D1 on one scale. "
          "Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), "
          "Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.", "",
          f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
          f"Phase 1 and Phase 2 gate rows on the same run: **{'pass' if p2_ok else 'FAIL'}** (reports/phase2.md).", "",
          "## Round trip: ratings → 20 seasons → ratings estimated from the stats", "",
          "Estimated from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results (engine/report4.py). "
          f"The estimator is replicated in {agg['n_folds']} folds of {FOLD_SEASONS} seasons, each fitting its own priors; each statistic is the mean over folds, "
          f"tolerance {k:.2f} SE across folds (Student t, {agg['n_folds'] - 1} df, the coverage of 3 SE). True ratings are measured from the simulated world's own D1 average, as the estimates are. Slope is the true rating regressed on the estimate (1 = calibrated). Bias is the mean of true − estimated. "
          "SD ratio is the residual SD over the posterior SD the estimator predicts (1 = sampling noise removed exactly, neither double-counted nor ignored). "
          "Reliability is the estimate regressed on the truth (the expected shrinkage; informational).", "",
          "| Rating | Players per season | Slope | Status | Bias | Status | Resid SD / predicted | SD ratio | Status | Reliability |",
          "|---|---|---|---|---|---|---|---|---|---|", *rows, "",
          "## True rating distributions (mean of 20 seasons)", "",
          "Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.", "",
          "| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |", "|---|---|---|---|---|---|---|", *sane, "",
          "## Example player cards (first simulated season)", "",
          "| Player | Team (tier) | Role | Ratings | Season |", "|---|---|---|---|---|"]
    for c in agg["cards"]:
        rat = ", ".join(f"{k_.replace('_', ' ').title()} {v}" for k_, v in c["ratings"].items())
        md.append(f"| {c['label']}: {c['name']} | {c['team']} ({c['tier']}) | {c['role']} | {rat} | {c['line']} |")
    return "\n".join(md) + "\n", st
