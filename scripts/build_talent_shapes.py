"""Shape of the true-talent distributions, by deconvolution of the 2025 play-by-play.

Phase 2 estimated each rate's individual true-talent spread by method of moments (mean and
SD, scripts/build_phase2_benchmarks.py) and the league generator drew it as Gaussian on the
logit scale. This fits the whole shape, with binomial noise removed, per side and rate.

Model, per player i in role group g on team t (same player-season lines, role groups, tier
expectations and qualifying cut as the method of moments):

    x_i ~ Binomial(n_i, expit(logit q_i + u_t + mu_g + sd_g * s_i)),   s_i ~ G

q_i: the player's tier-cell expectation (opponent tiers faced); u_t: his team's effect,
shrunk (empirical Bayes, team variance from the method of moments); mu_g, sd_g: the method-
of-moments group mean and individual SD. G is the standardized individual shape, shared by
the role groups of a side and rate (groups with sd_g = 0 carry no information on G).

Two fits of G, each a deconvolution (the binomial likelihood integrated over G):
  - NPMLE (Kiefer-Wolfowitz): G free on a fine grid, EM. The nonparametric reference; its
    log-likelihood bounds every smooth family from above.
  - Sinh-arcsinh (Jones & Pewsey 2009): s = xi + eta * sinh((asinh(Z) + eps) / delta),
    Z ~ N(0, 1). eps is skew (eps > 0 a longer right tail), delta tail weight (delta > 1
    lighter tails than Gaussian, < 1 heavier); eps = 0, delta = 1 is the Gaussian. Fitted by
    marginal maximum likelihood (Nelder-Mead over the four parameters).
The Gaussian (eps = 0, delta = 1; xi, eta free) is tested against the sinh-arcsinh by a
likelihood-ratio test with 2 degrees of freedom. A rate whose shape differs meaningfully
(statistic above config.phase2.SHAPE_LRT_CRIT) is drawn from its whole fitted distribution:
shape, location and scale of the maximum-likelihood fit (stored as a standardized quantile
table plus loc and scale in method-of-moments SD units). The method of moments measures
variance on the probability scale and converts it to the logit scale at the group mean (delta
method), and takes the logit of the mean rate as the location; both assume a near-symmetric,
narrow spread, so for a skewed shape the fitted location and scale replace them. Rates that
pass as Gaussian keep the method-of-moments mean and SD unchanged.
Output: data/ncaa_2025/derived/talent_shapes_2025.json (quantile tables used by
engine/league.py through config.phase2).

    python3 scripts/build_talent_shapes.py            # fit, write the JSON and reports/talent_shapes.md
    python3 scripts/build_talent_shapes.py --report   # rewrite the report from the JSON
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_phase2_benchmarks import (FULL_SEASON_GAMES, MIN_TEAM_GAMES, MIN_TRIALS, P, RATES, WEEKEND,  # noqa: E402
                                     expit, logit, trials_successes)
from config.phase2 import (INPUTS, SHAPE_LRT_CRIT, SHAPE_NPMLE_GRID, SHAPE_NPMLE_ITERS, SHAPE_QUANTILE_POINTS, SHAPE_Z_GRID,  # noqa: E402
                           TALENT_SHAPES)
from lib.players import load_pa  # noqa: E402

TODAY = dt.date.today().isoformat()


# ---- the data: player-season lines as in the method of moments --------------------------
def player_data() -> dict:
    inp = json.loads(INPUTS.read_text())
    tier_fx, talent = inp["tier_effects_logit"], inp["talent"]
    pa = load_pa()
    gm = pd.read_csv(P / "games_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier_of = dict(zip(teams.ncaa_team_id, teams.tier))
    gm["wd"] = pd.to_datetime(gm.game_date).dt.dayofweek
    pa = pa.merge(gm[["game_id", "wd"]], on="game_id", how="left").sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["bt"] = pa.bat_team_id.map(tier_of)
    pa["pt"] = pa.pit_team_id.map(tier_of)
    pa = pa[pa.bt.notna() & pa.pt.notna()].copy()
    g2 = pd.concat([gm[["game_id", "home_team_id"]].rename(columns={"home_team_id": "t"}),
                    gm[["game_id", "away_team_id"]].rename(columns={"away_team_id": "t"})])
    in_sample = g2.groupby("t").game_id.nunique()
    est_teams = set(in_sample[in_sample >= MIN_TEAM_GAMES].index)
    first = pa.groupby(["game_id", "pit_team_id"]).pkey.first().rename("starter").reset_index()
    pa = pa.merge(first, on=["game_id", "pit_team_id"], how="left")
    pa["is_sp"] = (pa.pkey == pa.starter).astype(int)
    pa["weekend"] = pa.wd.isin(WEEKEND).astype(int)

    def expected(rate):
        f = tier_fx[rate]
        return expit(f["intercept"] + pa.bt.map(f["bat"]).values + pa.pt.map(f["pit"]).values)

    # pitcher role groups, as in the method of moments
    app = pa.groupby(["pit_team_id", "pkey", "game_id"]).agg(sp=("is_sp", "max"), wkd=("weekend", "max")).reset_index()
    app["wsp"] = app.sp * app.wkd
    role = app.groupby(["pit_team_id", "pkey"]).agg(apps=("game_id", "size"), starts=("sp", "sum"), wkd_starts=("wsp", "sum")).reset_index()
    role["group"] = np.where(role.starts >= 0.5 * role.apps, np.where(role.wkd_starts >= 0.5 * role.starts, "sp_weekend", "sp_midweek"), "rp")
    role = role.rename(columns={"pit_team_id": "team", "pkey": "key"})[["team", "key", "group"]]

    out = {}
    for side, team_col, key, sname in (("bat", "bat_team_id", "bkey", "batter"), ("pit", "pit_team_id", "pkey", "pitcher")):
        out[side] = {}
        for rate in RATES:
            if rate not in talent[sname]:
                continue
            ent = talent[sname][rate]
            n, x = trials_successes(pa, rate)
            q = expected(rate)
            d = pd.DataFrame({"team": pa[team_col], "key": pa[key], "n": n, "x": x, "qn": q * n, "qqn": q * (1 - q) * n})
            # team effect, shrunk: team residual (prob. scale) times var_u / (var_u + noise), to logit
            t = d.groupby("team")[["n", "x", "qn", "qqn"]].sum()
            var_u = ent["team_var_prob"]
            resid = (t.x - t.qn) / t.n
            noise = t.qqn / t.n / t.n
            L = ent["league"]
            u = (resid * var_u / (var_u + noise)) / (L * (1 - L))
            lines = d.groupby(["team", "key"])[["n", "x", "qn"]].sum().reset_index()
            if side == "bat":
                pa_n = pd.DataFrame({"team": pa[team_col], "key": pa[key]}).groupby(["team", "key"]).size().rename("pa").reset_index()
                lines = lines.merge(pa_n, on=["team", "key"])
                lines["rank"] = lines.groupby("team").pa.rank(ascending=False, method="first")
                lines["group"] = np.where(lines["rank"] <= 9, "regular", "bench")
            else:
                lines = lines.merge(role, on=["team", "key"], how="left")
            lines = lines[lines.team.isin(est_teams) & (lines.n >= (MIN_TRIALS if rate in ("K", "BB", "HBP", "HR") else MIN_TRIALS // 2))]
            g = ent["groups"]
            lines = lines[lines.group.isin(g.keys())]
            mu = lines.group.map({k: v["mu_logit"] for k, v in g.items()}).values
            sd = lines.group.map({k: v["sd_ind_logit"] for k, v in g.items()}).values
            base = logit(lines.qn.values / lines.n.values) + lines.team.map(u).fillna(0.0).values + mu
            keep = sd > 0
            out[side][rate] = {"x": lines.x.values[keep].astype(float), "n": lines.n.values[keep].astype(float),
                               "base": base[keep], "sd": sd[keep], "groups": sorted(set(lines.group[keep])),
                               "n_players": int(keep.sum())}
    return out


# ---- likelihoods ----------------------------------------------------------------------------
def _lbinom(x, n):
    return np.array([math.lgamma(a + 1) - math.lgamma(b + 1) - math.lgamma(a - b + 1) for a, b in zip(n, x)])


def lik_matrix(d: dict, s: np.ndarray) -> np.ndarray:
    """log P(x_i | s_j) for every player i and grid value s_j."""
    eta = d["base"][:, None] + d["sd"][:, None] * s[None, :]
    lp = -np.logaddexp(0, -eta)
    lq = -np.logaddexp(0, eta)
    return d["lc"][:, None] + d["x"][:, None] * lp + (d["n"] - d["x"])[:, None] * lq


def _logsumexp(a, axis):
    m = a.max(axis=axis, keepdims=True)
    return (m + np.log(np.exp(a - m).sum(axis=axis, keepdims=True))).squeeze(axis)


def npmle(d: dict) -> dict:
    lo, hi, k = SHAPE_NPMLE_GRID
    s = np.linspace(lo, hi, k)
    ll = lik_matrix(d, s)
    rmax = ll.max(1)
    L = np.exp(ll - rmax[:, None])                  # likelihood matrix, each row scaled by its maximum
    w = np.full(k, 1.0 / k)
    prev = -np.inf
    for it in range(SHAPE_NPMLE_ITERS):
        f = L @ w
        cur = float(np.log(f).sum() + rmax.sum())
        if cur - prev < 1e-8:
            break
        prev = cur
        w = w * (L.T @ (1.0 / f)) / len(f)          # EM step for the mixing weights
    m = float((w * s).sum())
    sd = float(np.sqrt((w * (s - m) ** 2).sum()))
    return {"loglik": cur, "iters": it + 1, "mean": m, "sd": sd, "s": s, "w": w}


ZG = np.linspace(-SHAPE_Z_GRID[0], SHAPE_Z_GRID[0], SHAPE_Z_GRID[1])
ZW = np.exp(-0.5 * ZG ** 2)
ZW /= ZW.sum()


def shash(z, eps, delta):
    return np.sinh((np.arcsinh(z) + eps) / delta)


def shash_loglik(d: dict, theta) -> float:
    xi, log_eta, eps, log_delta = theta
    s = xi + np.exp(log_eta) * shash(ZG, eps, np.exp(log_delta))
    return float(_logsumexp(lik_matrix(d, s) + np.log(ZW)[None, :], 1).sum())


def nelder_mead(f, x0, step, iters=4000, tol=1e-9):
    """Minimise f by Nelder-Mead (standard coefficients)."""
    n = len(x0)
    pts = [np.array(x0, float)] + [np.array(x0, float) + np.eye(n)[i] * step[i] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = np.argsort(vals)
        pts = [pts[i] for i in order]; vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1]); fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1]); fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c); fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (p - pts[0]) for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = int(np.argmin(vals))
    return pts[i], vals[i]


def fit(d: dict) -> dict:
    d["lc"] = _lbinom(d["x"], d["n"])
    gauss, fg = nelder_mead(lambda t: -shash_loglik(d, [t[0], t[1], 0.0, 0.0]), [0.0, 0.0], [0.2, 0.2])
    full, ff = nelder_mead(lambda t: -shash_loglik(d, t), [gauss[0], gauss[1], 0.0, 0.0], [0.2, 0.2, 0.3, 0.2])
    # second start from the other side of the skew, keep the better optimum
    full2, ff2 = nelder_mead(lambda t: -shash_loglik(d, t), [gauss[0], gauss[1], -0.5, 0.2], [0.2, 0.2, 0.3, 0.2])
    if ff2 < ff:
        full, ff = full2, ff2
    np_ = npmle(d)
    xi, eta, eps, delta = full[0], math.exp(full[1]), full[2], math.exp(full[3])
    lrt = 2 * (fg - ff)
    return {"n_players": d["n_players"], "groups": d["groups"],
            "gaussian": {"xi": float(gauss[0]), "eta": float(math.exp(gauss[1])), "loglik": -float(fg)},
            "shash": {"xi": float(xi), "eta": float(eta), "eps": float(eps), "delta": float(delta), "loglik": -float(ff)},
            "npmle": {"loglik": np_["loglik"], "mean": np_["mean"], "sd": np_["sd"], "iters": np_["iters"],
                      "cdf": {"s": np_["s"].tolist(), "w": np_["w"].tolist()}},
            "lrt_vs_gaussian": float(lrt)}


# ---- the standardized shape and its tails ---------------------------------------------------
def standard_shape(eps: float, delta: float) -> dict:
    """Moments of S = sinh((asinh(Z) + eps) / delta) by quadrature, and the quantile table of
    (S - mean) / sd at normal scores, the form the generator reads (engine/league.py)."""
    zg = np.linspace(-10, 10, 20001)
    w = np.exp(-0.5 * zg ** 2); w /= w.sum()
    s = shash(zg, eps, delta)
    m = float((w * s).sum()); sd = float(np.sqrt((w * (s - m) ** 2).sum()))
    lo, hi, k = SHAPE_QUANTILE_POINTS
    zq = np.linspace(lo, hi, k)
    return {"mean": m, "sd": sd, "normal_scores": zq.round(4).tolist(), "values": ((shash(zq, eps, delta) - m) / sd).round(6).tolist()}


REPORT = ROOT / "reports/talent_shapes.md"
LABEL = {"K": "K/PA", "BB": "BB/PA", "HBP": "HBP/PA", "HR": "HR/PA", "BABIP": "BABIP", "XBH": "XBH share of hits"}


def write_report(out: dict) -> str:
    """reports/talent_shapes.md from the fitted shapes."""
    L = ["# True-talent shapes (deconvolution of the 2025 play-by-play)", "",
         f"Built {out['built']} by `scripts/build_talent_shapes.py`. For each side and rate, the individual true-talent distribution "
         "(logit offset from the player's tier expectation and his team's shrunk effect, in units of the method-of-moments SD of his role "
         "group) is fitted by deconvolution: the binomial likelihood of each player-season integrated over the distribution. Fits: the "
         "Gaussian, the sinh-arcsinh family (skew eps, tail weight delta; eps 0 and delta 1 is the Gaussian), and the NPMLE "
         "(nonparametric, the likelihood's upper bound). LRT: 2 × (log-likelihood sinh-arcsinh − Gaussian), 2 degrees of freedom; "
         f"a shape is used when LRT > {out['lrt_crit']} (p < .001). Tails: quantiles of the standardized fitted shape "
         "(Gaussian: q.001 −3.09, q.01 −2.33, q.99 +2.33, q.999 +3.09). sd/MoM: SD of the fitted distribution over the method-of-moments SD.", "",
         "| Side | Rate | Players | eps | delta | LRT | NPMLE − SHASH log-lik | sd/MoM | q.001 | q.01 | q.99 | q.999 | Drawn as |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, e in out["rates"].items():
        side, rate = key.split("_", 1)
        sd = "batters" if side == "bat" else "pitchers"
        if "shash" not in e:
            L.append(f"| {sd} | {LABEL[rate]} | {e['n_players']} | — | — | — | — | — | — | — | — | — | Gaussian ({e['reason']}) |")
            continue
        t, sh = e["tails_std"], e["shash"]
        L.append(f"| {sd} | {LABEL[rate]} | {e['n_players']} | {sh['eps']:+.2f} | {sh['delta']:.2f} | {e['lrt_vs_gaussian']:.1f} | "
                 f"{e['npmle']['loglik'] - sh['loglik']:.1f} | {e['fitted_sd_over_mom']:.2f} | {t['q0.001']:+.2f} | {t['q0.01']:+.2f} | "
                 f"{t['q0.99']:+.2f} | {t['q0.999']:+.2f} | {'**fitted shape**' if e['shape'] == 'shash' else 'Gaussian'} |")
    used = [k for k, e in out["rates"].items() if e.get("shape") == "shash"]
    L += ["", "Rates drawn from a fitted shape: " + (", ".join(used) if used else "none") + ". "
          "Those are drawn from the whole fitted distribution (location, scale and shape) through a Gaussian copula on the play-by-play "
          "correlations (engine/league.py); every other rate keeps the method-of-moments Gaussian. Fits whose eps and delta run to large "
          "values (eps above 5) sit on a flat likelihood: the data do not distinguish them from the Gaussian (LRT near 0).", ""]
    for k in used:
        e = out["rates"][k]
        np_ = e["npmle"]["cdf"]
        s, w = np.array(np_["s"]), np.array(np_["w"])
        top = s[w > 1e-3].max()
        L.append(f"- {k}: sinh-arcsinh eps {e['shash']['eps']:+.3f}, delta {e['shash']['delta']:.3f}; location {e['standard']['loc']:+.3f} and scale "
                 f"{e['standard']['scale']:.3f} in method-of-moments SD units. The NPMLE puts no mass above {top:+.2f} SD units "
                 f"(the fitted shape's 99.9th percentile: {e['standard']['loc'] + e['standard']['scale'] * e['tails_std']['q0.999']:+.2f}).")
    md = "\n".join(L) + "\n"
    REPORT.write_text(md)
    return md


def main() -> None:
    if "--report" in sys.argv:
        print(write_report(json.loads(TALENT_SHAPES.read_text())))
        return
    data = player_data()
    out = {"_note": __doc__, "built": TODAY, "lrt_crit": SHAPE_LRT_CRIT, "rates": {}}
    rows = []
    for side in ("bat", "pit"):
        for rate, d in data[side].items():
            if d["n_players"] < 50:
                out["rates"][f"{side}_{rate}"] = {"shape": "gaussian", "reason": f"not identifiable: {d['n_players']} players with individual spread > 0",
                                                   "n_players": d["n_players"]}
                rows.append((side, rate, d["n_players"], None))
                continue
            f = fit(d)
            sh = f["shash"]
            std = standard_shape(sh["eps"], sh["delta"])
            # the fitted distribution of s in method-of-moments SD units: location and scale of the ML fit
            std["loc"] = round(sh["xi"] + sh["eta"] * std["mean"], 5)
            std["scale"] = round(sh["eta"] * std["sd"], 5)
            use = f["lrt_vs_gaussian"] > SHAPE_LRT_CRIT
            fitted_sd = sh["eta"] * std["sd"]          # in units of the method-of-moments SD
            tails = {}
            for p in (0.001, 0.01, 0.99, 0.999):
                zq = float(np.sqrt(2) * _erfinv(2 * p - 1))
                tails[f"q{p}"] = round(float((shash(zq, sh["eps"], sh["delta"]) - std["mean"]) / std["sd"]), 3)
            out["rates"][f"{side}_{rate}"] = {**f, "shape": "shash" if use else "gaussian", "standard": std,
                                               "fitted_sd_over_mom": round(fitted_sd, 4), "tails_std": tails}
            rows.append((side, rate, d["n_players"], (f, use, tails, fitted_sd)))
    TALENT_SHAPES.write_text(json.dumps(out, indent=1) + "\n")
    write_report(out)
    print(f"{'rate':10s} {'n':>5s} {'eps':>7s} {'delta':>6s} {'LRT':>7s} {'NPMLE-SHASH':>11s} {'sd/mom':>7s}  q.001  q.01  q.99  q.999  use")
    for side, rate, n, r in rows:
        if r is None:
            print(f"{side}_{rate:6s} {n:5d}  not identifiable (gaussian)")
            continue
        f, use, t, fsd = r
        print(f"{side}_{rate:6s} {n:5d} {f['shash']['eps']:7.3f} {f['shash']['delta']:6.3f} {f['lrt_vs_gaussian']:7.2f} "
              f"{f['npmle']['loglik'] - f['shash']['loglik']:11.2f} {fsd:7.3f}  {t['q0.001']:+.2f} {t['q0.01']:+.2f} {t['q0.99']:+.2f} {t['q0.999']:+.2f}  "
              f"{'shash' if use else 'gaussian'}")
    print("Gaussian reference: q.001 -3.09, q.01 -2.33, q.99 +2.33, q.999 +3.09")


def _erfinv(y: float) -> float:
    # Newton on erf, adequate for |y| < 1 - 1e-12
    x = 0.0
    for _ in range(100):
        err = math.erf(x) - y
        x -= err / (2 / math.sqrt(math.pi) * math.exp(-x * x))
    return x


if __name__ == "__main__":
    main()
