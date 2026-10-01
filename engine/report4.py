"""Phase 4 round trip: ratings -> true rates -> simulated seasons -> observed rates.

Gate (forward): for each rated rate, every qualifying player-season's opponent-adjusted
observed rate is regressed on his true rate, logit scale. The engine records, per player and
rate, the sum over his own trials of the true probability p and of p (1 - p) against the
opponents he actually faced (E, V); the opponent-adjusted observed offset is z + (x - E) / V.
Slope 1, intercept 0 (at the group's own mean talent) and dispersion sum (x - E)^2 / sum V = 1,
within sampling error across folds; also by workload tercile. Stamina: pull decisions against
the manager's own baseline hazard, log leash regressed on the true log leash by maximum
likelihood. The manager orders players by true talent only (engine/league.py sets lineup,
rotation and bullpen order once from the true offsets), so workload is not selected on results.

Informational (not gated): the future scouting estimator for Phase 9, which estimates
ratings back from box-score information and is compared with the true ratings.
It sees only what a season's box scores give: each player's counting stats, the
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
Estimator statistics per rating, players with enough trials (config.phase4.MIN_TRIALS):
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
from config.phase4 import (BATTER_RATINGS, CENTER, EB_QUAD_NODES, FOLD_SEASONS, FOLD_WORKERS, GATE_COVERAGE, MIN_TRIALS, PITCHER_RATINGS, POINTS_PER_SD,
                           SHARED_TAU_ROLES, STAMINA_ROLE)
from engine import eb
from engine.game2 import (EXP_RATES, B_2B, B_3B, B_AB, B_BB, B_G, B_H, B_HBP, B_HR, B_K, B_PA, B_ROE, B_SF, B_SH, CELL_RESULTS, P_BB, P_BF, P_ER, P_G,
                          P_GS, P_HR, P_K, P_OUTS)
from engine.ratings import IDX, RatingScale, display, rating_names

ROOT = Path(__file__).resolve().parents[1]
TERCILES = ("light", "middle", "heavy")
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
        work = st[:, B_PA if side == "bat" else P_BF]          # workload: plate appearances or batters faced
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
                                    "z": np.array([players[i].z[IDX[rate]] for i in np.where(keep)[0]]), "work": work[keep].astype(float),
                                    "E": res["exp_trials"][ids, EXP_RATES.index(rate), 0][keep], "V": res["exp_trials"][ids, EXP_RATES.index(rate), 1][keep],
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
    hs = [pulls.get(x.pid, []) for x in cand]
    out["stamina"] = {"loglik": ll.astype(np.float32), "group": np.array([STAMINA_ROLE[x.group] for x in cand]),
                      "pgroup": np.array([x.group for x in cand]), "true": np.array([x.ratings["stamina"] for x in cand]),
                      "q": np.array([p[x.pid][P_G] for x in cand]) >= MIN_TRIALS["APPS"],
                      # forward test: true log leash, sum of log(1 - h) over stays, baseline h of each pull,
                      # observed pulls, and expected pulls and their variance under the true leash
                      "lt": np.array([x.log_theta for x in cand]), "S": np.array([surv.get(x.pid, 0.0) for x in cand]),
                      "pull_h": np.array([h for l_ in hs for h in l_]), "pull_owner": np.array([i for i, l_ in enumerate(hs) for _ in l_], int),
                      "O": np.array([len(l_) for l_ in hs], float), "E": np.array([res["leash_expected"].get(x.pid, 0.0) for x in cand]),
                      "V": np.array([res["leash_var"].get(x.pid, 0.0) for x in cand]),
                      # workload for the tercile split: appearances (batters faced are partly the pulls themselves)
                      "work": np.array([p[x.pid][P_G] for x in cand], float)}
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


def _mix(m: np.ndarray, v: np.ndarray, eta: np.ndarray):
    """Mean over a player's trials of p = expit(base + eta), base ~ N(m, v) (opponents differ):
    E p, E p^2 and E p(1 - p), by Gauss-Hermite quadrature."""
    nodes, w = np.polynomial.hermite_e.hermegauss(EB_QUAD_NODES)
    w = w / w.sum()
    p = _expit(m[:, None] + np.sqrt(v)[:, None] * nodes[None, :] + eta[:, None])
    return p @ w, (p ** 2) @ w, (p * (1 - p)) @ w


def _anchor(x, n, m, v, z) -> float:
    """The D1 average, measured on observables: the constant c at which true talent predicts the
    league's total count (sum n E p(m + c + z) = sum x over every player)."""
    c = 0.0
    for _ in range(50):
        P, _, dP = _mix(m, v, c + z)
        step = (x.sum() - (n * P).sum()) / (n * dP).sum()
        c += step
        if abs(step) < 1e-12:
            break
    return c


def _forward_glm(x, n, m, v, z, c, E, V) -> dict:
    """Observed rate on true rate, logit scale. The player's opponent-adjusted observed offset is
    o = z + (x - E) / V: one scoring step from his true offset z, with E and V the sum of p and of
    p (1 - p) over his own trials at his true rates against the opponents he actually faced (exact,
    recorded by the engine). o - mean z is regressed on z - mean z with weights V (its precision),
    the mean V-weighted over the players in the regression: slope 1 and intercept 0 under the null,
    the intercept being the average gap between observed and true offset; dispersion sum (x - E)^2 / sum V is 1 when the noise around the
    true rate is exactly the binomial noise of those trials.
    Informational, box-score version: the same regression with opponents adjusted from the
    team-by-team fit only (x ~ n E expit(m + c + a + b z), opponents mixed, quasi-binomial)."""
    o = z + (x - E) / V
    zc = z - np.average(z, weights=V)      # intercept at the group's own average talent: uncorrelated with the slope
    X = np.column_stack([np.ones(len(z)), zc])
    a, b = np.linalg.solve(X.T @ (V[:, None] * X), X.T @ (V * (o - (z - zc))))
    X = np.column_stack([np.ones(len(z)), z])
    ab, bb = 0.0, 1.0
    for _ in range(50):
        P, _, dP = _mix(m, v, c + ab + bb * z)
        P = np.clip(P, 1e-12, 1 - 1e-12)
        u = (x - n * P) * dP / (P * (1 - P))
        W = n * dP ** 2 / (P * (1 - P))
        d = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ u)
        ab, bb = ab + d[0], bb + d[1]
        if np.max(np.abs(d)) < 1e-10:
            break
    P, P2, _ = _mix(m, v, c + z)
    return {"intercept": float(a), "slope": float(b), "dispersion": float(((x - E) ** 2).sum() / V.sum()), "n": int(len(x)),
            "box_intercept": float(ab), "box_slope": float(bb), "box_dispersion": float(((x - n * P) ** 2).sum() / (n * (P - P2)).sum())}


def _leash_glm(lt, S, pull_h, owner, O, E, V) -> dict:
    """Pull decisions on true leash: each decision pulls with 1 - (1 - h)^theta,
    log theta = mean lt + a + b (lt - mean lt) (lt the pitcher's true log leash). Newton on (a, b), finite-difference derivatives. Null: a = 0,
    b = 1. Dispersion: sum over pitchers of (pulls - expected)^2 over the sum of the variance, both at
    the true leash (each decision is a Bernoulli draw given its hazard, so O - E is a martingale:
    E (O - E)^2 = E V)."""
    ls = np.log1p(-np.minimum(pull_h, 1 - 1e-9))

    lbar = float(lt.mean())                  # intercept at the group's average leash, as for the rates

    def ll(par):
        th = np.exp(lbar + par[0] + par[1] * (lt - lbar))
        return float((th * S).sum() + np.log(-np.expm1(th[owner] * ls)).sum())
    par, eps = np.array([0.0, 1.0]), 1e-4
    for _ in range(30):
        g = np.array([(ll(par + e) - ll(par - e)) / (2 * eps) for e in np.eye(2) * eps])
        H = np.array([[(ll(par + e1 + e2) - ll(par + e1 - e2) - ll(par - e1 + e2) + ll(par - e1 - e2)) / (4 * eps ** 2)
                       for e2 in np.eye(2) * eps] for e1 in np.eye(2) * eps])
        d = -np.linalg.solve(H, g)
        par = par + d
        if np.max(np.abs(d)) < 1e-8:
            break
    return {"intercept": float(par[0]), "slope": float(par[1]), "dispersion": float(((O - E) ** 2).sum() / V.sum()), "n": int(len(O))}


def _forward(ex: list) -> dict:
    """The forward round trip on a set of seasons: per rated rate, each qualifying player-season's
    opponent-adjusted observed count against his true rate; overall and by workload tercile."""
    out = {}
    for name in ex[0]["ratings"]:
        d = [e["ratings"][name] for e in ex]
        cat = lambda k: np.concatenate([x_[k] for x_ in d])
        x, n, m, v, z, q, work, E, V = (cat(k_) for k_ in ("x", "n", "m", "v", "z", "q", "work", "E", "V"))
        c = _anchor(x, n, m, v, z)
        r = {"all": _forward_glm(x[q], n[q], m[q], v[q], z[q], c, E[q], V[q]), "s": d[0]["s"], "sign": d[0]["sign"]}
        cut = np.quantile(work[q], [1 / 3, 2 / 3])
        t = np.digitize(work, cut)
        for k_, lab in enumerate(TERCILES):
            i = q & (t == k_)
            r[lab] = _forward_glm(x[i], n[i], m[i], v[i], z[i], c, E[i], V[i])
        out[name] = r
    st = [e["stamina"] for e in ex]
    cat = lambda k: np.concatenate([x_[k] for x_ in st])
    off = np.cumsum([0] + [len(x_["lt"]) for x_ in st[:-1]])
    owner = np.concatenate([x_["pull_owner"] + o for x_, o in zip(st, off)])
    lt, S, ph, O, E, V, q, work = cat("lt"), cat("S"), cat("pull_h"), cat("O"), cat("E"), cat("V"), cat("q"), cat("work")

    def sub(i):
        j = np.where(i)[0]
        remap = -np.ones(len(lt), int); remap[j] = np.arange(len(j))
        keep = remap[owner] >= 0
        return _leash_glm(lt[j], S[j], ph[keep], remap[owner[keep]], O[j], E[j], V[j])
    r = {"all": sub(q)}
    cut = np.quantile(work[q], [1 / 3, 2 / 3])
    t = np.digitize(work, cut)
    for k_, lab in enumerate(TERCILES):
        r[lab] = sub(q & (t == k_))
    out["stamina"] = r
    return out


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


def _fold_stats(runs: list, key: str) -> dict:
    v = np.array(runs, float)
    k = len(v)
    return {"mean": float(np.nanmean(v)), "se": float(np.nanstd(v, ddof=1) / np.sqrt(k)) if k > 1 else 0.0}


def aggregate4(ex: list, scale: RatingScale | None = None) -> dict:
    """Replicate the forward round trip and the scouting estimator over folds of FOLD_SEASONS
    seasons; report the mean and standard error of each statistic across folds."""
    scale = scale or RatingScale()
    n = len(ex)
    k = max(1, n // FOLD_SEASONS)
    folds = [ex[i * FOLD_SEASONS:(i + 1) * FOLD_SEASONS] if k > 1 else ex for i in range(k)]
    fw = [_forward(f) for f in folds]
    if k > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(FOLD_WORKERS) as pool:
            runs = list(pool.map(_estimate, folds, [scale] * k))
    else:
        runs = [_estimate(folds[0], scale)]
    out = {"n_seasons": n, "n_folds": k, "forward": {}, "ratings": {}, "true_dist": {}, "cards": ex[0]["cards"], "priors": runs[0]["priors"]}
    for name in fw[0]:
        out["forward"][name] = {}
        for lab in ("all",) + TERCILES:
            keys = [kk for kk in fw[0][name][lab] if kk != "n"]
            agg = {kk: _fold_stats([r[name][lab][kk] for r in fw], kk) for kk in keys}
            agg["n"] = float(np.mean([r[name][lab]["n"] for r in fw])) / len(folds[0])     # player-seasons per season
            out["forward"][name][lab] = agg
        out["forward"][name]["s"] = fw[0][name].get("s")
    for name in runs[0]["stats"]:
        agg = {}
        for key in ("slope", "bias", "sd_ratio", "resid_sd", "pred_sd", "reliability", "n"):
            agg[key] = _fold_stats([r["stats"][name][key] for r in runs], key)
        agg["n"]["mean"] /= len(folds[0])     # players per season
        out["ratings"][name] = agg
    for name in ex[0]["true_dist"]:
        out["true_dist"][name] = {kk: float(np.mean([e["true_dist"][name][kk] for e in ex])) for kk in ex[0]["true_dist"][name]}
    return out


RATE_LABEL = {"contact": "BABIP", "gap": "XBH share of hits", "power": "HR/PA", "eye": "BB/PA", "avoid_k": "K/PA",
              "stuff": "K/BF", "control": "BB/BF", "movement": "HR/BF", "stamina": "pull hazard (log leash)"}
WORK_LABEL = {"stamina": "appearances"}


def build_report4(agg: dict, seeds: list, phase2_status: dict) -> tuple[str, dict]:
    st, rows, trows, brows, erows = {}, [], [], [], []
    from engine.report2 import _t_quantile
    nf = agg["n_folds"]
    k = _t_quantile((1 + GATE_COVERAGE) / 2, nf - 1) if nf > 1 else float("inf")
    pm = lambda x, nd=3: f"{x['mean']:+.{nd}f} ± {k * x['se']:.{nd}f}"
    within = lambda x, null: abs(x["mean"] - null) <= k * x["se"]
    for name, r in agg["forward"].items():
        a, b, d = r["all"]["intercept"], r["all"]["slope"], r["all"]["dispersion"]
        ok = {"intercept": within(a, 0), "slope": within(b, 1), "dispersion": within(d, 1)}
        for kk, v in ok.items():
            st[f"fw_{name}_{kk}"] = bool(v)
        pts = f"{10 * a['mean'] / r['s']:+.2f}" if r.get("s") else "—"
        rows.append(f"| {name} | {RATE_LABEL[name]} | {int(round(r['all']['n']))} | {pm(a, 4)} | {pts} | {'pass' if ok['intercept'] else 'FAIL'} | "
                    f"{b['mean']:.3f} ± {k * b['se']:.3f} | {'pass' if ok['slope'] else 'FAIL'} | {d['mean']:.3f} ± {k * d['se']:.3f} | {'pass' if ok['dispersion'] else 'FAIL'} |")
        cells = []
        for lab in TERCILES:
            t = r[lab]
            flag = lambda x, null: "" if within(x, null) else " †"
            cells.append(f"{t['intercept']['mean']:+.4f}{flag(t['intercept'], 0)} / {t['slope']['mean']:.3f}{flag(t['slope'], 1)} / "
                         f"{t['dispersion']['mean']:.3f}{flag(t['dispersion'], 1)}")
        trows.append(f"| {name} | {WORK_LABEL.get(name, 'batters faced' if name in ('stuff', 'control', 'movement') else 'plate appearances')} | " + " | ".join(cells) + " |")
        if "box_slope" in r["all"]:
            brows.append(f"| {name} | {r['all']['box_slope']['mean']:.3f} | {r['all']['box_dispersion']['mean']:.3f} |")
    for name, r in agg["ratings"].items():
        sl, bi, sr = r["slope"], r["bias"], r["sd_ratio"]
        f = lambda x, nd=3: f"{x['mean']:.{nd}f} ± {k * x['se']:.{nd}f}"
        erows.append(f"| {name} | {int(r['n']['mean'])} | {f(sl)} | {f(bi, 2)} | {r['resid_sd']['mean']:.2f} / {r['pred_sd']['mean']:.2f} | {f(sr)} | "
                     f"{r['reliability']['mean']:.2f} |")
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
          "## Round trip, forward: true rates → 20 seasons → observed rates", "",
          "For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. "
          "The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over "
          "the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. "
          "The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is "
          "Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is "
          "1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same "
          "ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). "
          f"Statistics are means over {nf} folds of {FOLD_SEASONS} seasons. Tolerance is {k:.2f} SE across folds (Student t, {nf - 1} df, the coverage of 3 SE).", "",
          "| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |",
          "|---|---|---|---|---|---|---|---|---|---|", *rows, "",
          "### By workload tercile (informational)", "",
          "Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. "
          "The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets "
          "(engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice "
          "and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on "
          "his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game "
          "pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, "
          "since its batters faced are partly the pulls themselves.", "",
          "| Rating | Workload | Light | Middle | Heavy |", "|---|---|---|---|---|", *trows, "",
          "Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which "
          "team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its "
          "dispersion runs above 1.", "",
          "| Rating | Slope | Dispersion |", "|---|---|---|", *brows, "",
          "## True rating distributions (mean of 20 seasons)", "",
          "Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.", "",
          "| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |", "|---|---|---|---|---|---|---|", *sane, "",
          "## Example player cards (first simulated season)", "",
          "| Player | Team (tier) | Role | Ratings | Season |", "|---|---|---|---|---|"]
    for c in agg["cards"]:
        rat = ", ".join(f"{k_.replace('_', ' ').title()} {v}" for k_, v in c["ratings"].items())
        md.append(f"| {c['label']}: {c['name']} | {c['team']} ({c['tier']}) | {c['role']} | {rat} | {c['line']} |")
    md += ["", "## Future scouting estimator (Phase 9, informational; not gated)", "",
           "Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes "
           "from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. "
           "It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds "
           "(engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD "
           "over the posterior SD the estimator predicts.", "",
           "| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |", "|---|---|---|---|---|---|---|", *erows, "",
           "Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, "
           "so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a "
           "team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the "
           "pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias "
           "rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by "
           "trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, "
           "but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the "
           "spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.", ""]
    return "\n".join(md) + "\n", st
