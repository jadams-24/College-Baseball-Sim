"""Phase 3 inputs: the hands of the engine's players, drawn per player conditional on talent and role (pitchers) or
position (batters) (owner rule 2026-10-08: no code path reads tier; the tier gradient is a check, not a fit).

Data (data/ncaa_2025/roster_aggregates/, counts only):
  hand_by_talent_pitchers.csv   matched pitchers by role x quintile of an opponent- and platoon-adjusted index x throws, by tier
  hand_by_talent_batters.csv    matched batters by position group x quintile x throws x bats, by tier
  handedness_by_position.csv    bats x throws of every roster player by position group
  pitcher_throws_by_role.csv    throws of the pitchers who appeared in the play-by-play, by role and tier

The quintiles are of an observed index: a pitcher in bin q2 is not a q2 talent, his true K-BB is spread around it by the
noise of his batters faced. The fit goes through that noise (deconvolution). A population of simulated players (seasons
of the engine with hands off: their true rates and playing time, config.phase3.POP_SEEDS) stands in for the real players
behind the table: each simulated player's play-by-play workload is his season's times the coverage of his tier and role
(solved so the binned players' mean workload equals the table's), his observed index is his true one plus binomial noise
at that workload (N_NOISE_REPLICATES draws), and he falls in the table's bins by its edges. The model
    pitchers  logit P(throws L) = a_role + b_role * s          s = (true index - D1 mean) / D1 SD, within role
    batters   log P(bats L) / P(bats R) = base_L[group, throws] + bL * s,   log P(S) / P(R) = base_S[group, throws] + bS * s
is fitted by maximum likelihood on the table's cells (tier x role or group x bin x hands; the predicted share of a cell is
the average over the simulated players in it). Tier enters only through who is in each cell. Then:
  - the intercepts are set so the D1 shares match: pitchers, the share of left-handers among the pitchers who appeared, by
    role, tiers weighted by their number of teams (the play-by-play sample over-represents P4); batters, the roster shares
    by position group and throws (rosters cover the tiers evenly, approved as representative 2026-10-08);
  - diagnostics: the same fit with a tier term (the effect of tier at equal talent, the size for the Phase 9 requirement if
    the gradient check fails), the talent-only model's tier gradient on the population against the real one with its
    conference-clustered interval, and the run-value index as a sensitivity check (owner adjustment 1).

Writes data/ncaa_2025/derived/phase3_inputs_2025.json (keys hands_pitchers, hands_batters, throws_by_group, hand_checks).
    python3 scripts/build_phase3_hands.py [--pop runs/phase3_pop.pkl]
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase3  # noqa: E402
from config.phase3 import BATTER_GROUPS, MIN_BF_BIN, MIN_PA_BIN, N_NOISE_REPLICATES, POS_GROUP, STARTER_SHARE  # noqa: E402

AGG = ROOT / "data/ncaa_2025/roster_aggregates"
OUT = phase3.INPUTS
TIERS = ("p4", "mid", "low")
BINS = tuple(f"q{i}" for i in range(1, 6))
LW_OUTCOME = {"K": "out", "BB": "BB", "HBP": "HBP", "HR": "HR", "1B": "1B", "2B": "2B", "3B": "3B", "ROE": "ROE", "OUT": "out"}
Z95 = 1.959964


# ------------------------------------------------------------------ population of simulated players
def _season(seed: int) -> list:
    from config import phase2
    phase3.FEATURES["hands"] = False            # the population is the engine without hands (no circularity)
    from engine.game2 import B_PA, P_BF, P_G, P_GS
    from engine.season import simulate_season
    res = simulate_season(phase2.load(), seed)
    lg = res["league"]
    rows = []
    for p in lg.players:
        b, q = res["bstats"][p.pid], res["pstats"][p.pid]
        rows.append(dict(seed=seed, pid=p.pid, team=p.team, tier=lg.teams[p.team].tier, side=p.side, group=p.group, pos=p.pos,
                         z=np.array(p.z, float), pa=int(b[B_PA]), bf=int(q[P_BF]), g=int(q[P_G]), gs=int(q[P_GS])))
    return rows


def population(path: Path | None, workers: int = 4) -> pd.DataFrame:
    if path is not None and path.exists():
        return pd.DataFrame(pickle.loads(path.read_bytes()))
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(_season, phase3.POP_SEEDS):
            rows += r
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(rows))
    return pd.DataFrame(rows)


def true_indexes(pop: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Each player's index against a league-average opponent (the table's indexes are adjusted for the opponents and for
    platoon), and its per-PA variance (the noise of the observed index is var / n): K-BB for pitchers and run value."""
    from config import phase2
    from engine.league import load_location
    from engine.matchup import matchup_probs
    cfg, loc = phase2.load(), load_location()
    zero = np.zeros(6)
    w = np.array([weights[LW_OUTCOME[o]] for o in ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")])
    out = {k: [] for k in ("kbb", "kbb_var", "rv", "rv_var")}
    for side, z in zip(pop.side, pop.z):
        p = matchup_probs(cfg, z, zero, loc) if side == "bat" else matchup_probs(cfg, zero, z, loc)
        pv = np.array([p[o] for o in ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")])
        k, bb = p["K"], p["BB"]
        out["kbb"].append(k - bb); out["kbb_var"].append(k + bb - (k - bb) ** 2)
        m = float(pv @ w)
        out["rv"].append(m); out["rv_var"].append(float(pv @ w ** 2) - m * m)
    return pop.assign(**out)


def opponent_shift(pop: pd.DataFrame, cov: dict, col: str) -> np.ndarray:
    """What the table's opponent adjustment does to a player's index, emulated on the simulated schedules. The aggregator
    (tools/aggregate_rosters.adjusted_index) subtracts from each PA's y the opponent's own mean y minus the league mean,
    shrunk by n / (n + K_SHRINK), n the opponent's play-by-play PA. The opponent's mean carries the players he faced, so
    the one-step adjustment over-corrects for a schedule: with y additive in the two sides' deviations (dev, from the
    league mean), a player's index is
        t + mean over his opponents o of [dev(o) - k(o) (dev(o) + faced(o))],
    faced(o) the mean deviation of the players o faced (his own team among them). Team-level means (PA- or BF-weighted),
    opponents by games on the season's schedule (engine.schedule, the population's seeds), coverage per tier as in the fit."""
    from config import phase2
    from engine.league import build_league
    from engine.schedule import make_schedule
    from config.phase3 import K_SHRINK
    cfg = phase2.load()
    shift = np.zeros(len(pop))
    for seed, d in pop.groupby("seed"):
        ss = np.random.SeedSequence(int(seed))
        s_league, s_sched, _ = ss.spawn(3)
        lg = build_league(cfg, np.random.Generator(np.random.PCG64(s_league)))
        sched = make_schedule(cfg, lg, np.random.Generator(np.random.PCG64(s_sched)))
        nt = len(lg.teams)
        W = np.zeros((nt, nt))
        for g in sched:
            W[g.home, g.away] += 1; W[g.away, g.home] += 1
        W = W / W.sum(axis=1, keepdims=True)
        dev, kk = {}, {}
        for side, n_col, ckey in (("bat", "pa", "bat"), ("pit", "bf", "pit")):
            s = d[d.side == side]
            lm = np.average(s[col], weights=s[n_col])
            n_obs = s[n_col].to_numpy(float) * np.array([cov[ckey].get(t, 1.0) for t in s.tier])
            dev[side] = np.zeros(nt); kk[side] = np.zeros(nt)
            for tid, g in s.assign(n_obs=n_obs).groupby("team"):
                w = g[n_col].to_numpy(float)
                if w.sum() > 0:
                    dev[side][tid] = np.average(g[col] - lm, weights=w)
                    kk[side][tid] = np.average(g.n_obs / (g.n_obs + K_SHRINK), weights=w)
        for side, opp in (("pit", "bat"), ("bat", "pit")):
            faced = W @ dev[side]                       # what the opponents' players faced: this side's teams
            term = W @ (dev[opp] - kk[opp] * (dev[opp] + faced))
            m = (pop.seed == seed).to_numpy() & (pop.side == side).to_numpy()
            shift[m] = term[pop.team.to_numpy()[m]]
    return shift


def coverage(n_season: np.ndarray, target_mean: float, min_n: int) -> float:
    """Coverage c in (0, 1]: the play-by-play workload is c x the season's; c solves mean(c n | c n >= min_n) = target
    (the binned players' mean workload in the table). Bisection; 1 when even full coverage falls short."""
    def f(c):
        m = c * n_season
        m = m[m >= min_n]
        return (m.mean() if len(m) else 0.0) - target_mean
    lo, hi = 1e-3, 1.0
    if f(hi) < 0:
        return 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def bin_of(x: np.ndarray, edges: list) -> np.ndarray:
    return np.array([f"q{int(i) + 1}" for i in np.searchsorted(np.array(edges), x, side="right")])


# ------------------------------------------------------------------ maximum likelihood (small, dense: Newton on numeric derivatives)
def newton(nll, x0: np.ndarray, iters: int = 100, h: float = 1e-4) -> tuple[np.ndarray, np.ndarray]:
    x = np.array(x0, float)
    k = len(x)

    def grad_hess(x):
        g, H = np.zeros(k), np.zeros((k, k))
        f0 = nll(x)
        for i in range(k):
            e = np.zeros(k); e[i] = h
            fp, fm = nll(x + e), nll(x - e)
            g[i] = (fp - fm) / (2 * h)
            H[i, i] = (fp - 2 * f0 + fm) / h ** 2
            for j in range(i):
                e2 = np.zeros(k); e2[j] = h
                H[i, j] = H[j, i] = (nll(x + e + e2) - nll(x + e - e2) - nll(x - e + e2) + nll(x - e - e2)) / (4 * h * h)
        return f0, g, H
    for _ in range(iters):
        f0, g, H = grad_hess(x)
        try:
            step = np.linalg.solve(H + 1e-9 * np.eye(k), g)
        except np.linalg.LinAlgError:
            step = g
        t = 1.0
        while nll(x - t * step) > f0 and t > 1e-6:
            t /= 2
        x = x - t * step
        if np.max(np.abs(t * step)) < 1e-7:
            break
    _, _, H = grad_hess(x)
    return x, np.linalg.inv(H)


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


# ------------------------------------------------------------------ pitchers
def pitchers_of(pop: pd.DataFrame) -> pd.DataFrame:
    P = pop[(pop.side == "pit") & (pop.g > 0)].copy()
    P["role_obs"] = np.where(P.gs / P.g >= STARTER_SHARE, "starter", "reliever")
    P["grp"] = np.where(P.group == "rp", "reliever", "starter")
    return P


def pitcher_coverage(P: pd.DataFrame, tab: pd.DataFrame, index: str) -> dict:
    """Coverage by tier and observed role: the binned pitchers' mean BF equals the table's."""
    t = tab[tab["index"] == index]
    cov = {}
    for tier in TIERS:
        for role in ("starter", "reliever"):
            q = t[(t.scope == "tier") & (t.scope_value == tier) & (t.role == role) & t.bin.isin(BINS)]
            n_real = q.pitchers.sum()
            target = q.bf_sum.sum() / n_real if n_real else MIN_BF_BIN
            S = P[(P.tier == tier) & (P.role_obs == role)]
            cov[f"{tier}|{role}"] = round(coverage(S.bf.to_numpy(float), target, MIN_BF_BIN), 4)
    return cov


def batter_coverage(B: pd.DataFrame, tab: pd.DataFrame, index: str) -> dict:
    t = tab[tab["index"] == index]
    cov = {}
    for tier in TIERS:
        q = t[(t.scope == "tier") & (t.scope_value == tier) & t.bin.isin(BINS) & t.position_group.isin(BATTER_GROUPS)]
        n_real = q.batters.sum()
        target = q.pa_sum.sum() / n_real if n_real else MIN_PA_BIN
        cov[tier] = round(coverage(B[B.tier == tier].pa.to_numpy(float), target, MIN_PA_BIN), 4)
    return cov


def tier_coverage(pop: pd.DataFrame, tab_p: pd.DataFrame, tab_b: pd.DataFrame) -> dict:
    """Coverage per tier for each side (pitchers: the roles' BF-weighted average), for the opponent-adjustment emulation."""
    P = pitchers_of(pop)
    cp = pitcher_coverage(P, tab_p, phase3.PITCHER_INDEX)
    pit = {}
    for tier in TIERS:
        w = {r: P[(P.tier == tier) & (P.role_obs == r)].bf.sum() for r in ("starter", "reliever")}
        pit[tier] = sum(w[r] * cp[f"{tier}|{r}"] for r in w) / max(sum(w.values()), 1)
    return {"pit": pit, "bat": batter_coverage(pop[pop.side == "bat"], tab_b, phase3.BATTER_INDEX)}


def pitcher_cells(pop: pd.DataFrame, tab: pd.DataFrame, index: str, rng) -> tuple[dict, pd.DataFrame, dict]:
    """The simulated pitchers behind each real cell (tier, observed role, bin): their engine role and standardized true
    index, with replicate weights. Returns cells, the pitcher frame (with s) and the coverage factors."""
    P = pitchers_of(pop)
    col, var = ("kbb", "kbb_var") if index == "k_minus_bb" else ("rv", "rv_var")
    sign = 1.0 if index == "k_minus_bb" else -1.0            # run value allowed: lower is better; s is "better = higher"
    for g in ("starter", "reliever"):
        m = P.grp == g
        P.loc[m, "s"] = sign * (P.loc[m, col] - P.loc[m, col].mean()) / P.loc[m, col].std()
    t = tab[tab["index"] == index]
    edges = {r: [float(t[(t.scope == "all") & (t.role == r) & (t.bin == f"q{i}")].bin_hi.iloc[0]) for i in range(1, 5)]
             for r in ("starter", "reliever")}
    cov, cells = pitcher_coverage(P, tab, index), {}
    for tier in TIERS:
        for role in ("starter", "reliever"):
            S = P[(P.tier == tier) & (P.role_obs == role)]
            n = cov[f"{tier}|{role}"] * S.bf.to_numpy(float)
            keep = n >= MIN_BF_BIN
            S, n = S[keep], n[keep]
            obs = (S[col] + S[f"{col}_shift"]).to_numpy()[:, None] + np.sqrt(S[var].to_numpy()[:, None] / n[:, None]) * rng.standard_normal((len(S), N_NOISE_REPLICATES))
            b = np.array([bin_of(o, edges[role]) for o in obs])
            for bn in BINS:
                w = (b == bn).sum(axis=1).astype(float)
                sel = w > 0
                cells[(tier, role, bn)] = (S.grp.to_numpy()[sel], S.s.to_numpy()[sel], w[sel] / N_NOISE_REPLICATES,
                                           S[col].to_numpy()[sel])
    return cells, P, cov


def real_counts(tab: pd.DataFrame, index: str) -> dict:
    t = tab[(tab["index"] == index) & (tab.scope == "tier")]
    out = {}
    for (tier, role, bn), g in t[t.bin.isin(BINS) & t.scope_value.isin(TIERS)].groupby(["scope_value", "role", "bin"]):
        d = dict(zip(g.throws, g.pitchers))
        out[(tier, role, bn)] = (int(d.get("L", 0)), int(d.get("R", 0)))
    return out


def fit_pitchers(cells: dict, counts: dict, tier_term: bool = False) -> dict:
    """ML of a_role, b_role (and tier effects at equal talent, mid the reference, when tier_term) on the cells."""
    keys = [k for k in counts if k in cells and sum(counts[k]) > 0]
    roles = ("starter", "reliever")

    def nll(x):
        a, b = dict(zip(roles, x[:2])), dict(zip(roles, x[2:4]))
        tau = {"p4": x[4], "mid": 0.0, "low": x[5]} if tier_term else {"p4": 0.0, "mid": 0.0, "low": 0.0}
        f = 0.0
        for k in keys:
            grp, s, w, _ = cells[k]
            if w.sum() == 0:
                continue
            lin = np.array([a[g] for g in grp]) + np.array([b[g] for g in grp]) * s + tau[k[0]]
            p = float((w * expit(lin)).sum() / w.sum())
            p = min(max(p, 1e-9), 1 - 1e-9)
            nL, nR = counts[k]
            f -= nL * math.log(p) + nR * math.log(1 - p)
        return f
    x0 = np.array([-1.0, -1.0, 0.0, 0.0] + ([0.0, 0.0] if tier_term else []))
    x, cov = newton(nll, x0)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    out = {"a": dict(zip(roles, x[:2].round(4).tolist())), "b": dict(zip(roles, x[2:4].round(4).tolist())),
           "b_se": dict(zip(roles, se[2:4].round(4).tolist())), "cells": len(keys), "nll": round(nll(x), 3)}
    if tier_term:
        out["tier_logodds_vs_mid"] = {"p4": round(float(x[4]), 4), "low": round(float(x[5]), 4)}
        out["tier_logodds_se"] = {"p4": round(float(se[4]), 4), "low": round(float(se[5]), 4)}
        # p4 vs low at equal talent and its SE (from the covariance of the two tier terms)
        d = float(x[4] - x[5]); v = float(cov[4, 4] + cov[5, 5] - 2 * cov[4, 5])
        out["tier_p4_minus_low"] = {"logodds": round(d, 4), "se": round(math.sqrt(max(v, 0)), 4)}
    return out


def tier_weights() -> dict:
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    from scripts.roster_representativeness import REGION  # noqa: F401  (same team list as the representativeness report)
    listed = pd.read_csv(ROOT / "tools/roster_teams.csv")
    listed = listed[listed.d1 == 1] if "d1" in listed else listed
    m = listed.merge(t.rename(columns={"ncaa_team_id": "team_ncaa_id"})[["team_ncaa_id", "tier"]], on="team_ncaa_id", how="left")
    c = m.tier.value_counts()
    return {k: int(c.get(k, 0)) for k in TIERS}


def real_lhp(tw: dict) -> dict:
    """Share of left-handers among the pitchers who appeared, by role: by tier (with the conference-clustered interval of
    the representativeness report) and D1 (tiers weighted by their number of teams; the variance combines the tiers')."""
    from scripts.roster_representativeness import clustered
    pr = pd.read_csv(AGG / "pitcher_throws_by_role.csv")
    out = {}
    for role in ("starter", "reliever"):
        by = {}
        for tier in TIERS:
            c = pr[(pr.scope == "conference") & (pr.role == role)]
            confs = _conf_tier()
            c = c[c.scope_value.map(confs) == tier]
            xs, ns = [], []
            for _, g in c.groupby("scope_value"):
                d = dict(zip(g.throws, g.pitchers))
                xs.append(d.get("L", 0)); ns.append(d.get("L", 0) + d.get("R", 0))
            p, lo, hi = clustered(xs, ns)
            by[tier] = {"share": round(p, 4), "lo": round(lo, 4), "hi": round(hi, 4), "pitchers": int(sum(ns)), "se": round((hi - lo) / (2 * Z95), 4)}
        W = sum(tw.values())
        d1 = sum(tw[t] * by[t]["share"] for t in TIERS) / W
        se = math.sqrt(sum((tw[t] / W * by[t]["se"]) ** 2 for t in TIERS))
        out[role] = {"by_tier": by, "d1": {"share": round(d1, 4), "se": round(se, 4)}}
    return out


def _conf_tier() -> dict:
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    return t.groupby("conference").tier.agg(lambda s: s.mode().iloc[0]).to_dict()


def calibrate_pitchers(P: pd.DataFrame, fit: dict, target: dict) -> dict:
    """Intercepts so the D1 share of left-handers among simulated pitchers by observed role, tiers weighted by number of
    teams, equals the real one (two equations, two unknowns: a_starter, a_reliever), the slopes kept."""
    tw = tier_weights()
    a = dict(fit["a"])
    roles = ("starter", "reliever")
    team_n = P.groupby("tier").apply(lambda d: d.seed.astype(str).add("|").add(d.team.astype(str)).nunique(), include_groups=False)

    def shares(a):
        lin = P.grp.map(a).to_numpy() + P.grp.map(fit["b"]).to_numpy() * P.s.to_numpy()
        pl = expit(lin)
        out = {}
        for role in roles:
            m = (P.role_obs == role).to_numpy()
            # tiers weighted by their real number of teams (the population has the real tier sizes, so this is the plain share)
            num = sum(tw[t] * pl[m & (P.tier == t).to_numpy()].mean() for t in TIERS)
            out[role] = num / sum(tw.values())
        return out
    for _ in range(50):
        s = shares(a)
        err = np.array([s[r] - target[r]["d1"]["share"] for r in roles])
        if np.max(np.abs(err)) < 1e-6:
            break
        J = np.zeros((2, 2))
        for j, r in enumerate(roles):
            a2 = dict(a); a2[r] += 1e-4
            s2 = shares(a2)
            J[:, j] = [(s2[q] - s[q]) / 1e-4 for q in roles]
        d = np.linalg.solve(J, err)
        a = {r: a[r] - d[j] for j, r in enumerate(roles)}
    s = shares(a)
    by_tier = {}
    lin = P.grp.map(a).to_numpy() + P.grp.map(fit["b"]).to_numpy() * P.s.to_numpy()
    pl = expit(lin)
    for role in roles:
        by_tier[role] = {t: round(float(pl[((P.role_obs == role) & (P.tier == t)).to_numpy()].mean()), 4) for t in TIERS}
    _ = team_n
    return {"a": {r: round(float(a[r]), 4) for r in roles}, "d1_share": {r: round(float(s[r]), 4) for r in roles}, "predicted_by_tier": by_tier}


def composition_check(cells: dict, tab: pd.DataFrame, index: str) -> dict:
    """The simulated pitchers' spread over the bins against the table's, by tier and role (does the population stand in
    for the real players behind the table?)."""
    t = tab[(tab["index"] == index) & (tab.scope == "tier")]
    out = {}
    for tier in TIERS:
        for role in ("starter", "reliever"):
            sim = np.array([cells.get((tier, role, b), (None, None, np.zeros(0), None))[2].sum() for b in BINS])
            real = np.array([t[(t.scope_value == tier) & (t.role == role) & (t.bin == b)].pitchers.sum() for b in BINS], float)
            if real.sum() == 0 or sim.sum() == 0:
                continue
            out[f"{tier}|{role}"] = {"real": (real / real.sum()).round(3).tolist(), "sim": (sim / sim.sum()).round(3).tolist(), "n_real": int(real.sum())}
    return out


# ------------------------------------------------------------------ batters
def batter_base() -> dict:
    """Roster shares: P(throws L | group); P(bats | throws R, group); P(bats | throws L) pooled over the position groups
    (left-handed throwers are few outside 1B and OF). From handedness_by_position, scope all, position players."""
    h = pd.read_csv(AGG / "handedness_by_position.csv")
    a = h[(h.scope == "all") & h.position_group.isin(BATTER_GROUPS) & h.throws.isin(["L", "R"]) & h.bats.isin(["L", "R", "S"])]
    thr = {g: round(float(a[(a.position_group == g) & (a.throws == "L")]["count"].sum() / a[a.position_group == g]["count"].sum()), 4)
           for g in BATTER_GROUPS}
    thr_n = {g: int(a[a.position_group == g]["count"].sum()) for g in BATTER_GROUPS}
    bats = {}
    for g in BATTER_GROUPS:
        d = a[(a.position_group == g) & (a.throws == "R")].groupby("bats")["count"].sum()
        bats[f"{g}|R"] = {k: round(float(d.get(k, 0) / d.sum()), 4) for k in ("L", "R", "S")}
    d = a[a.throws == "L"].groupby("bats")["count"].sum()
    for g in BATTER_GROUPS:
        bats[f"{g}|L"] = {k: round(float(d.get(k, 0) / d.sum()), 4) for k in ("L", "R", "S")}
    return {"throws_L": thr, "throws_n": thr_n, "bats": bats}


def batter_cells(pop: pd.DataFrame, tab: pd.DataFrame, index: str, rng) -> tuple[dict, pd.DataFrame, dict]:
    B = pop[(pop.side == "bat")].copy()
    B["grp"] = B.pos.map(POS_GROUP)
    col, var = ("rv", "rv_var")
    if index == "on_base":
        raise NotImplementedError
    B["s"] = (B[col] - B[col].mean()) / B[col].std()
    t = tab[tab["index"] == index]
    edges = [float(t[(t.scope == "all") & (t.bin == f"q{i}")].bin_hi.dropna().iloc[0]) for i in range(1, 5)]
    cov, cells = batter_coverage(B, tab, index), {}
    for tier in TIERS:
        S = B[B.tier == tier]
        n = cov[tier] * S.pa.to_numpy(float)
        keep = n >= MIN_PA_BIN
        S, n = S[keep], n[keep]
        obs = (S[col] + S[f"{col}_shift"]).to_numpy()[:, None] + np.sqrt(S[var].to_numpy()[:, None] / n[:, None]) * rng.standard_normal((len(S), N_NOISE_REPLICATES))
        b = np.array([bin_of(o, edges) for o in obs])
        for g in BATTER_GROUPS:
            for bn in BINS:
                w = ((b == bn) & (S.grp.to_numpy() == g)[:, None]).sum(axis=1).astype(float)
                sel = w > 0
                cells[(tier, g, bn)] = (S.s.to_numpy()[sel], w[sel] / N_NOISE_REPLICATES)
    return cells, B, cov


def fit_batters(cells: dict, tab: pd.DataFrame, base: dict, index: str) -> dict:
    """ML of the talent slopes bL, bS (bats L and S against R) with the roster's base logits as offsets."""
    t = tab[(tab["index"] == index) & (tab.scope == "tier") & tab.bin.isin(BINS) & tab.position_group.isin(BATTER_GROUPS)]
    obs = []
    for (tier, g, bn, thr), d in t[t.scope_value.isin(TIERS)].groupby(["scope_value", "position_group", "bin", "throws"]):
        n = dict(zip(d.bats, d.batters))
        if sum(n.values()) and (tier, g, bn) in cells and cells[(tier, g, bn)][1].sum() > 0:
            obs.append(((tier, g, bn), thr, n))

    def logits(g, thr):
        pb = base["bats"][f"{g}|{thr}"]
        return math.log(max(pb["L"], 1e-6) / pb["R"]), math.log(max(pb["S"], 1e-6) / pb["R"])

    def nll(x):
        bL, bS = x
        f = 0.0
        for key, thr, n in obs:
            s, w = cells[key]
            lL, lS = logits(key[1], thr)
            eL, eS = np.exp(lL + bL * s), np.exp(lS + bS * s)
            den = 1 + eL + eS
            pr = {"L": float((w * eL / den).sum() / w.sum()), "S": float((w * eS / den).sum() / w.sum()), "R": float((w / den).sum() / w.sum())}
            f -= sum(n.get(k, 0) * math.log(max(pr[k], 1e-12)) for k in ("L", "R", "S"))
        return f
    x, cov = newton(nll, np.zeros(2))
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return {"bL": round(float(x[0]), 4), "bS": round(float(x[1]), 4), "bL_se": round(float(se[0]), 4), "bS_se": round(float(se[1]), 4),
            "cells": len(obs), "batters": int(sum(sum(n.values()) for _, _, n in obs))}


def calibrate_batters(B: pd.DataFrame, base: dict, fit: dict) -> dict:
    """Base logits so the population's average shares equal the roster's, by group and throws (the talent term is centred
    on the population, so this moves them little)."""
    out = {}
    for g in BATTER_GROUPS:
        s = B[B.grp == g].s.to_numpy()
        for thr in ("L", "R"):
            pb = base["bats"][f"{g}|{thr}"]
            lL, lS = math.log(max(pb["L"], 1e-6) / pb["R"]), math.log(max(pb["S"], 1e-6) / pb["R"])
            for _ in range(100):
                eL, eS = np.exp(lL + fit["bL"] * s), np.exp(lS + fit["bS"] * s)
                den = 1 + eL + eS
                mL, mS = (eL / den).mean(), (eS / den).mean()
                dl, ds = math.log(pb["L"] / mL) if pb["L"] > 0 else 0.0, math.log(pb["S"] / mS) if pb["S"] > 0 else 0.0
                lL += dl; lS += ds
                if abs(dl) + abs(ds) < 1e-10:
                    break
            out[f"{g}|{thr}"] = {"L": round(lL, 5), "S": round(lS, 5) if pb["S"] > 0 else -20.0}
    return out


def batter_tier_check(B: pd.DataFrame, base: dict, logit_base: dict, fit: dict) -> dict:
    """Predicted share of each bats hand by tier: the population's talent within each position group, the groups weighted
    by the tier's real roster counts (C, 1B, IF, OF, UT/DH), throws by group. Real: the same groups (real_batter_tiers)."""
    h = pd.read_csv(AGG / "handedness_by_position.csv")
    mix = h[(h.scope == "tier") & h.position_group.isin(BATTER_GROUPS)].groupby(["scope_value", "position_group"])["count"].sum()
    pred = {}
    for tier in TIERS:
        S = B[B.tier == tier]
        acc = np.zeros(3)
        for g, d in S.groupby("grp"):
            # each group weighted by its real roster count in the tier (the check compares talent effects, not position mixes)
            wg = float(mix.get((tier, g), 0.0)) / len(d)
            s = d.s.to_numpy()
            pl = base["throws_L"][g]
            for thr, wt in (("L", pl), ("R", 1 - pl)):
                lb = logit_base[f"{g}|{thr}"]
                eL, eS = np.exp(lb["L"] + fit["bL"] * s), np.exp(lb["S"] + fit["bS"] * s)
                den = 1 + eL + eS
                acc += wg * wt * np.array([(eL / den).sum(), (1 / den).sum(), (eS / den).sum()])
        pred[tier] = dict(zip(("L", "R", "S"), (acc / acc.sum()).round(4).tolist()))
    return pred


def real_batter_tiers() -> dict:
    from scripts.roster_representativeness import clustered
    h = pd.read_csv(AGG / "handedness_by_position.csv")
    c = h[(h.scope == "conference") & h.position_group.isin(BATTER_GROUPS) & h.bats.isin(["L", "R", "S"])]
    confs = _conf_tier()
    out = {}
    for tier in TIERS:
        d = c[c.scope_value.map(confs) == tier]
        g = d.groupby("scope_value")
        n = g["count"].sum()
        out[tier] = {}
        for hand in ("L", "R", "S"):
            x = d[d.bats == hand].groupby("scope_value")["count"].sum().reindex(n.index, fill_value=0)
            p, lo, hi = clustered(list(x), list(n))
            out[tier][hand] = {"share": round(p, 4), "lo": round(lo, 4), "hi": round(hi, 4)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", type=Path, default=ROOT / "runs/phase3_pop.pkl")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-emulate", dest="emulate", action="store_false", help="skip the opponent-adjustment emulation (diagnostic)")
    args = ap.parse_args()
    phase3.FEATURES["hands"] = False            # the population and the schedules it plays are the engine without hands
    rng = np.random.default_rng(20261008)
    lw = pd.read_csv(AGG / "linear_weights.csv")
    weights = dict(zip(lw.term, lw.run_value))
    pop = true_indexes(population(args.pop, args.workers), weights)
    tab_p = pd.read_csv(AGG / "hand_by_talent_pitchers.csv")
    tab_b = pd.read_csv(AGG / "hand_by_talent_batters.csv")
    cov_t = tier_coverage(pop, tab_p, tab_b)
    for col in ("kbb", "rv"):
        pop[f"{col}_shift"] = opponent_shift(pop, cov_t, col) if args.emulate else 0.0
    print("index shift by tier (mean):", {f"{sd}|{col}": pop[pop.side == sd].groupby("tier")[f"{col}_shift"].mean().round(4).to_dict()
                                          for sd in ("pit", "bat") for col in ("kbb", "rv")}, flush=True)
    tw = tier_weights()
    target = real_lhp(tw)

    res = {}
    for index in ("k_minus_bb", "run_value"):
        cells, P, cov = pitcher_cells(pop, tab_p, index, rng)
        counts = real_counts(tab_p, index)
        fit = fit_pitchers(cells, counts)
        cal = calibrate_pitchers(P, fit, target)
        fit_t = fit_pitchers(cells, counts, tier_term=True)
        res[index] = {"fit": fit, "calibrated": cal, "tier_term_fit": fit_t, "coverage": cov,
                      "composition": composition_check(cells, tab_p, index),
                      "s_scale": {g: {"mean": round(float(P[P.grp == g][("kbb" if index == "k_minus_bb" else "rv")].mean()), 5),
                                      "sd": round(float(P[P.grp == g][("kbb" if index == "k_minus_bb" else "rv")].std()), 5)}
                                  for g in ("starter", "reliever")}}
        print(index, json.dumps({k: res[index][k] for k in ("fit", "calibrated", "tier_term_fit", "coverage")}, indent=1), flush=True)
    prim = res[phase3.PITCHER_INDEX]

    base = batter_base()
    cells_b, B, cov_b = batter_cells(pop, tab_b, phase3.BATTER_INDEX, rng)
    fit_b = fit_batters(cells_b, tab_b, base, phase3.BATTER_INDEX)
    logit_base = calibrate_batters(B, base, fit_b)
    pred_b = batter_tier_check(B, base, logit_base, fit_b)
    print("batters", json.dumps({"fit": fit_b, "coverage": cov_b, "pred": pred_b}, indent=1), flush=True)

    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    out["hands_pitchers"] = {
        "_doc": "logit P(throws L) = a[role] + b[role] * s, s = (true K-BB vs an average batter - mean) / sd of the role's D1 "
                "population (engine.league draws it per pitcher; role: weekend and midweek starters 'starter', relievers 'reliever')",
        "index": phase3.PITCHER_INDEX, "a": prim["calibrated"]["a"], "b": prim["fit"]["b"], "b_se": prim["fit"]["b_se"],
        "s_scale": prim["s_scale"], "a_before_calibration": prim["fit"]["a"], "coverage": prim["coverage"]}
    out["hands_batters"] = {
        "_doc": "throws: P(L | position group); bats: log P(L)/P(R) = base_L[group|throws] + bL s, log P(S)/P(R) = base_S[group|throws] "
                "+ bS s, s = (true run value per PA vs an average pitcher - mean) / sd of the D1 batter population",
        "throws_L": base["throws_L"], "base": logit_base, "bL": fit_b["bL"], "bS": fit_b["bS"], "bL_se": fit_b["bL_se"], "bS_se": fit_b["bS_se"],
        "s_scale": {"mean": round(float(B.rv.mean()), 5), "sd": round(float(B.rv.std()), 5)}, "coverage": cov_b,
        "run_weights": {o: round(float(weights[LW_OUTCOME[o]]), 4) for o in LW_OUTCOME},
        "roster_shares": base}
    out["hand_checks"] = {
        "tier_weights_teams": tw,
        "lhp_real": target,
        "lhp_predicted_by_tier": prim["calibrated"]["predicted_by_tier"],
        "lhp_tier_effect_at_equal_talent": prim["tier_term_fit"],
        "lhp_composition": prim["composition"],
        "sensitivity_run_value": {"fit": res["run_value"]["fit"], "predicted_by_tier": res["run_value"]["calibrated"]["predicted_by_tier"],
                                  "tier_term_fit": res["run_value"]["tier_term_fit"]},
        "batter_real_by_tier": real_batter_tiers(), "batter_predicted_by_tier": pred_b, "batter_fit": fit_b,
        "population_seeds": list(phase3.POP_SEEDS)}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=1))
    tmp.replace(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
