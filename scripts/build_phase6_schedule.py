"""Strength-matched nonconference scheduling (Phase 6).

Real nonconference schedules are not random within tiers. On the 2025 scoreboard (regular season:
games before the NCAA tournament, May 26; the sim plays no postseason), the low-tier teams that play
P4 teams are .15 log runs stronger than their tier's mean, and the mid-tier teams that play low-tier
teams are .06 weaker. Opponents' strengths also covary within tier pairs. A schedule that draws teams
at random within the tier mix puts the average low team against the average P4 team and widens every
cross-tier gap. This moves the tier-vs-tier matrix, team RA/G spread and the elite run-prevention
rows.

Measured (team strength = o + d of the additive scoreboard fit without parks, the totals the engine
draws; deviation = strength minus its tier's mean):
  mean deviation of the teams in each directed cross-tier pairing (team-games); the fit's noise has
  mean zero given the schedule, so these are the true means
  covariance of the two teams' deviations in cross-tier games, less the fit's noise covariance
  between opponents (from the fit's covariance matrix)
Solved, on schedules of generated leagues (calibration seeds 950001-950012, no games played):
  beta[t|u]  weight on deviation for a tier-t team filling a slot against tier u
  sigma      matching noise in tier-SD units (rank matching on z + sigma N(0, 1))
by fixed-point iteration on the six means and the covariance. Same-tier nonconference means are
reported as a check, not matched (they follow from who is left).

    python3 scripts/build_phase6_schedule.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from build_phase2_teams import IND, SRC, fit, load  # noqa: E402
from config import phase2, phase6  # noqa: E402
from config.phase6 import INPUTS6  # noqa: E402

POSTSEASON = "2025-05-26"      # first day after the conference tournaments (NCAA regionals from May 30)
SEEDS = tuple(range(950001, 950013))
CROSS = ("low|mid", "low|p4", "mid|low", "mid|p4", "p4|low", "p4|mid")
SAME = ("low|low", "mid|mid", "p4|p4")


def nonconf(home, away, conf_of) -> bool:
    return conf_of[home] != conf_of[away] or conf_of[home] == IND


def real_targets() -> dict:
    sb, names, tier, conf = load()
    f = fit(sb, names, parks=False)
    n = len(names); ix = {t: k for k, t in enumerate(names)}
    s = f["o"] + f["d"]
    tr = np.array([tier[t] for t in names])
    dev = s.copy()
    for t in set(tr):
        dev[tr == t] -= s[tr == t].mean()
    # noise covariance of two teams' strengths: V[o_i,o_j] + V[o_i,d_j] + V[d_i,o_j] + V[d_i,d_j]
    V = f["Vc"]; o_, d_ = slice(2, 2 + n), slice(2 + n, 2 + 2 * n)
    Vs = V[o_, o_] + V[o_, d_] + V[d_, o_] + V[d_, d_]
    reg = sb[pd.to_datetime(sb.date) < POSTSEASON]
    rows = []
    for h, a in zip(reg.home, reg.away):
        if nonconf(h, a, conf):
            i, j = ix[h], ix[a]
            rows += [(tier[h], tier[a], dev[i], dev[j], Vs[i, j]), (tier[a], tier[h], dev[j], dev[i], Vs[i, j])]
    D = pd.DataFrame(rows, columns=["t", "u", "dev", "odev", "vnoise"])
    D["pair"] = D.t + "|" + D.u
    g = D.groupby("pair").dev
    means = {k: round(float(v), 4) for k, v in g.mean().items()}
    se = {k: round(float(v), 4) for k, v in (g.std() / np.sqrt(g.size())).items()}
    x = D[D.t != D.u]
    cov_fit = float(np.cov(x.dev, x.odev)[0, 1]); noise = float(x.vnoise.mean())
    return {"mean_dev": means, "mean_dev_se": se, "n_team_games": {k: int(v) for k, v in g.size().items()},
            "cross_cov_fitted": round(cov_fit, 5), "cross_cov_noise": round(noise, 5), "cross_cov": round(cov_fit - noise, 5),
            "tier_sd_fitted": {t: round(float(dev[tr == t].std()), 4) for t in sorted(set(tr))}}


def sched_moments(leagues: list, beta: dict, sigma: float) -> dict:
    from engine.schedule import make_schedule
    phase6.load()["schedule6"] = {"beta": beta, "sigma": sigma}
    cfg = phase2.load()
    conf_of = {tid: c for tid, (_, c, _) in enumerate(cfg.teams)}
    rows = []
    for seed, L in leagues:
        s = {t.tid: t.s_total for t in L.teams}; tier_of = {t.tid: t.tier for t in L.teams}
        m = {tr: np.mean([s[t] for t in s if tier_of[t] == tr]) for tr in set(tier_of.values())}
        for g in make_schedule(cfg, L, np.random.default_rng(seed)):
            if nonconf(g.home, g.away, conf_of):
                a, b = g.home, g.away
                da, db = s[a] - m[tier_of[a]], s[b] - m[tier_of[b]]
                rows += [(f"{tier_of[a]}|{tier_of[b]}", da, db), (f"{tier_of[b]}|{tier_of[a]}", db, da)]
    D = pd.DataFrame(rows, columns=["pair", "dev", "odev"])
    x = D[D.pair.isin(CROSS)]
    return {"mean_dev": D.groupby("pair").dev.mean().to_dict(), "cross_cov": float(np.cov(x.dev, x.odev)[0, 1]),
            "tier_var": {tr: float(np.var([t.s_total for _, L in leagues for t in L.teams if t.tier == tr])) for tr in ("low", "mid", "p4")}}


def main() -> None:
    from engine.league import build_league
    tg = real_targets()
    print("targets:", json.dumps(tg))
    cfg = phase2.load()
    leagues = [(seed, build_league(cfg, np.random.default_rng(seed))) for seed in SEEDS]
    beta = {k: 0.0 for k in CROSS}; sigma = 3.0
    for it in range(25):
        m = sched_moments(leagues, beta, sigma)
        err = {k: tg["mean_dev"][k] - m["mean_dev"][k] for k in CROSS}
        print(it, {k: round(v, 3) for k, v in beta.items()}, round(sigma, 3), "| mean err", {k: round(v, 4) for k, v in err.items()},
              "| cov", round(m["cross_cov"], 5), "target", tg["cross_cov"])
        if max(abs(v) for v in err.values()) < 0.003 and abs(m["cross_cov"] - tg["cross_cov"]) < 0.0008:
            break
        for k in CROSS:
            beta[k] += 0.8 * err[k] / m["tier_var"][k.split("|")[0]]   # d mean / d beta ~ within-tier variance
        # more covariance <- less matching noise; multiplicative step on sigma
        sigma *= float(np.clip((max(m["cross_cov"], 1e-4) / max(tg["cross_cov"], 1e-4)) ** 0.5, 0.7, 1.4))
    m = sched_moments(leagues, beta, sigma)
    blk = {"_note": __doc__, "built": dt.date.today().isoformat(), "source": SRC + "; regular season (before " + POSTSEASON + ")",
           "seeds": list(SEEDS), "targets": tg, "beta": {k: round(float(v), 4) for k, v in beta.items()}, "sigma": round(float(sigma), 4),
           "achieved": {"mean_dev": {k: round(float(v), 4) for k, v in m["mean_dev"].items()}, "cross_cov": round(m["cross_cov"], 5)}}
    cur = json.loads(INPUTS6.read_text()); cur["schedule6"] = blk
    INPUTS6.write_text(json.dumps(cur, indent=1) + "\n")
    print("wrote schedule6:", json.dumps({k: blk[k] for k in ("beta", "sigma", "achieved")}))
    print("same-tier check (not matched):", {k: (tg["mean_dev"].get(k), round(m["mean_dev"].get(k, float("nan")), 4)) for k in SAME})


if __name__ == "__main__":
    main()
