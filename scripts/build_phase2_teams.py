"""Team strength on one talent scale, from every 2025 D1-vs-D1 final in the scoreboard.

Model (quasi-Poisson, log link), one row per team-game:
  log E[runs of i against j] = a + o_i - d_j + h * (+1/2 if i bats at home, -1/2 away) + p_k
p_k is the park effect of the listed home team's park (Phase 6; both teams' runs in the park), so
o and d are net of each team's home park.
o_i is offense and d_i run prevention, both in log runs relative to an average D1 team
(centred over teams); h is the matchup-controlled home effect (home runs over away
runs between equal teams). The scoreboard has no neutral-site flag, so h is the effect
of the listed home slot, the same slot the home-win and run-differential gate rows use.

Variance components per tier, with estimation noise removed (method of moments; the
noise covariance of each team's (o, d) comes from the fit's covariance matrix):
  (o, d)_i = m_tier + c_conf + u_i
  Sigma_u[tier]  pooled within-conference covariance minus mean noise
  Sigma_c[tier]  covariance of conference means around the tier mean minus
                 mean (Sigma_u + noise) / n_conf, projected to positive semi-definite.
                 Per tier: low-tier conferences spread far more than mid (SWAC vs Ivy);
                 P4 rests on 4 conferences. A pooled estimate is reported for reference.
Hosting of nonconference games: logistic in the tier pair (signed) and the strength gap
s_i - s_j (s = o + d), slope disattenuated for estimation noise in s.
Gate targets: the tier-vs-tier scoring matrix (R/G, batting tier x pitching tier),
home win pct and home run differential, with two-way (batting team, pitching team)
cluster-robust standard errors.

Writes the team_talent block of phase2_inputs_2025.json and the tier_matrix / home
blocks of phase2_gate_2025.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

TIERS = ("p4", "mid", "low")
INPUTS = Path("data/ncaa_2025/derived/phase2_inputs_2025.json")
GATE = Path("data/ncaa_2025/derived/phase2_gate_2025.json")
SRC = "NCAA scoreboard feed, every 2025 D1-vs-D1 final (data/ncaa_2025/scoreboard/games_2025.csv; fetched for PR #1)"
IND = "DI Independent"


def psd(m: np.ndarray) -> np.ndarray:
    vals, vecs = np.linalg.eigh((m + m.T) / 2)
    return vecs @ np.diag(np.clip(vals, 0, None)) @ vecs.T


def load():
    teams = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.team, teams.tier)); conf = dict(zip(teams.team, teams.conference))
    sb = pd.read_csv("data/ncaa_2025/scoreboard/games_2025.csv")
    sb = sb[(sb.state == "final") & sb.home_score.notna() & sb.away_score.notna()].drop_duplicates("url")
    sb = sb[sb.home.isin(tier) & sb.away.isin(tier)].reset_index(drop=True)
    names = sorted(set(sb.home) | set(sb.away))
    return sb, names, tier, conf


def fit(sb: pd.DataFrame, names: list, parks: bool = True) -> dict:
    """parks: also fit a park term for the listed home team's park (Phase 6), so o and d are net of
    each team's home park; the park estimates are centred like o and d."""
    n, G = len(names), len(sb)
    ix = {t: k for k, t in enumerate(names)}
    hi = sb.home.map(ix).values; ai = sb.away.map(ix).values
    X = np.zeros((2 * G, 2 + (3 if parks else 2) * n)); y = np.empty(2 * G)
    r = np.arange(G)
    for rows, bat, pit, sgn, score in ((2 * r, hi, ai, 0.5, sb.home_score), (2 * r + 1, ai, hi, -0.5, sb.away_score)):
        X[rows, 0] = 1; X[rows, 1] = sgn
        X[rows, 2 + bat] = 1; X[rows, 2 + n + pit] = -1
        if parks:
            X[rows, 2 + 2 * n + hi] = 1
        y[rows] = score.values.astype(float)
    beta = np.zeros(X.shape[1]); beta[0] = np.log(y.mean())
    for _ in range(25):
        eta = X @ beta; mu = np.exp(eta)
        z = eta + (y - mu) / mu
        A = (X * mu[:, None]).T @ X
        new = np.linalg.pinv(A) @ ((X * mu[:, None]).T @ z)
        if np.max(np.abs(new - beta)) < 1e-9:
            beta = new; break
        beta = new
    mu = np.exp(X @ beta)
    A = (X * mu[:, None]).T @ X
    rank = np.linalg.matrix_rank(A)
    phi = float(((y - mu) ** 2 / mu).sum() / (len(y) - rank))
    V = phi * np.linalg.pinv(A)
    # centre o and d over teams (estimable contrasts); transform the covariance
    C = np.eye(X.shape[1])
    for blk in (slice(2, 2 + n), slice(2 + n, 2 + 2 * n)) + ((slice(2 + 2 * n, 2 + 3 * n),) if parks else ()):
        C[blk, blk] -= 1.0 / n
    b = C @ beta; Vc = C @ V @ C.T
    o, d = b[2:2 + n], b[2 + n:2 + 2 * n]
    park = b[2 + 2 * n:] if parks else np.zeros(n)
    park_noise = np.diag(Vc)[2 + 2 * n:] if parks else np.zeros(n)
    noise = np.array([[[Vc[2 + i, 2 + i], Vc[2 + i, 2 + n + i]], [Vc[2 + n + i, 2 + i], Vc[2 + n + i, 2 + n + i]]] for i in range(n)])
    a_league = float(beta[0] + beta[2:2 + n].mean() - beta[2 + n:].mean())
    # correlation of the two teams' Pearson residuals within a game: variation shared by both
    # offenses (park, weather) as opposed to one team's day
    r_ = (y - mu) / np.sqrt(mu)
    rcorr = float(np.corrcoef(r_[0::2], r_[1::2])[0, 1])
    return {"o": o, "d": d, "noise": noise, "h": float(beta[1]), "h_se": float(np.sqrt(V[1, 1])), "phi": phi, "a": a_league,
            "n_games": G, "Vc": Vc, "n": n, "residual_corr": rcorr, "park": park, "park_noise": park_noise}


def parks_mom(names, tier, f) -> dict:
    """Park effects (log runs per game) by tier: mean and true SD, estimation noise removed."""
    out = {}
    p, v = f["park"], f["park_noise"]
    t = np.array([tier[x] for x in names])
    for tr in TIERS:
        k = t == tr
        out[tr] = {"n": int(k.sum()), "mean": round(float(p[k].mean()), 4),
                   "sd": round(float(np.sqrt(max(p[k].var(ddof=1) - v[k].mean(), 0.0))), 4),
                   "raw_sd": round(float(p[k].std(ddof=1)), 4), "noise_sd": round(float(np.sqrt(v[k].mean())), 4)}
    within = np.concatenate([p[t == tr] - p[t == tr].mean() for tr in TIERS])
    sd_pooled = float(np.sqrt(max(within.var(ddof=len(TIERS)) * len(within) / (len(within) - len(TIERS) + len(TIERS)) - v.mean(), 0.0)))
    return {"_note": "Park effect of the listed home team's park, log runs per game, from the scoreboard fit with a park term; "
                     "tier means relative to the D1 average park, SDs within tier with estimation noise removed (method of moments).",
            "tiers": out, "sd_pooled": round(sd_pooled, 4)}


def components(names, tier, conf, f) -> dict:
    x = np.column_stack([f["o"], f["d"]])
    df = pd.DataFrame({"team": names, "tier": [tier[t] for t in names], "conf": [conf[t] for t in names]})
    out = {}
    pooled_num, pooled_den = np.zeros((2, 2)), 0
    for t in TIERS:
        idx = np.where(df.tier == t)[0]
        m = x[idx].mean(0)
        a = np.zeros(len(names)); a[idx] = 1 / len(idx)
        se_o = float(np.sqrt(a @ f["Vc"][2:2 + f["n"], 2:2 + f["n"]] @ a)); se_d = float(np.sqrt(a @ f["Vc"][2 + f["n"]:2 + 2 * f["n"], 2 + f["n"]:2 + 2 * f["n"]] @ a))
        sub = df.iloc[idx]
        confs = [c for c in sub.conf.unique() if c != IND]
        Sw, dfw, Nw, cm, nk = np.zeros((2, 2)), 0, [], [], []
        for c in confs:
            k = idx[(sub.conf == c).values]
            dev = x[k] - x[k].mean(0)
            Sw += dev.T @ dev; dfw += len(k) - 1
            Nw.extend(f["noise"][k]); cm.append(x[k].mean(0)); nk.append(len(k))
        Sw /= dfw; N = np.mean(Nw, axis=0)
        Su = psd(Sw - N)
        cm = np.array(cm); mc = cm.mean(0)
        Sb = (cm - mc).T @ (cm - mc) / (len(cm) - 1)
        Sc_raw = Sb - np.mean([(Su + N) / k for k in nk], axis=0)
        pooled_num += (len(cm) - 1) * Sc_raw; pooled_den += len(cm) - 1
        tot_obs = np.cov(x[idx].T)
        out[t] = {"n_teams": int(len(idx)), "n_conferences": len(confs), "mean_o": round(float(m[0]), 4), "mean_d": round(float(m[1]), 4),
                  "mean_o_se": round(se_o, 4), "mean_d_se": round(se_d, 4),
                  "team_cov": [[round(float(v), 5) for v in row] for row in Su],
                  "team_sd": {"o": round(float(np.sqrt(Su[0, 0])), 4), "d": round(float(np.sqrt(Su[1, 1])), 4),
                              "corr": round(float(Su[0, 1] / np.sqrt(Su[0, 0] * Su[1, 1])), 3) if Su[0, 0] > 0 and Su[1, 1] > 0 else 0.0},
                  "conf_cov": [[round(float(v), 5) for v in row] for row in psd(Sc_raw)],
                  "conf_sd": {"o": round(float(np.sqrt(psd(Sc_raw)[0, 0])), 4), "d": round(float(np.sqrt(psd(Sc_raw)[1, 1])), 4)},
                  "observed_sd": {"o": round(float(np.sqrt(tot_obs[0, 0])), 4), "d": round(float(np.sqrt(tot_obs[1, 1])), 4)},
                  "noise_sd": {"o": round(float(np.sqrt(N[0, 0])), 4), "d": round(float(np.sqrt(N[1, 1])), 4)}}
    Sc = psd(pooled_num / pooled_den)
    return {"tiers": out, "conf_cov_pooled": [[round(float(v), 5) for v in row] for row in Sc],
            "conf_sd_pooled": {"o": round(float(np.sqrt(Sc[0, 0])), 4), "d": round(float(np.sqrt(Sc[1, 1])), 4),
                        "corr": round(float(Sc[0, 1] / np.sqrt(Sc[0, 0] * Sc[1, 1])), 3) if Sc[0, 0] > 0 and Sc[1, 1] > 0 else 0.0},
            "conf_df": pooled_den}


def hosting(sb, names, tier, conf, f) -> dict:
    ix = {t: k for k, t in enumerate(names)}
    s = f["o"] + f["d"]
    ns = f["noise"][:, 0, 0] + f["noise"][:, 1, 1] + 2 * f["noise"][:, 0, 1]
    nc = sb[(sb.home_conf != sb.away_conf) | (sb.home_conf == IND)]
    nc = nc[[conf[h] != conf[a] or conf[h] == IND for h, a in zip(nc.home, nc.away)]]
    rank = {"p4": 2, "mid": 1, "low": 0}
    pairs = (("p4", "mid"), ("p4", "low"), ("mid", "low"))
    rows, ys, noise = [], [], []
    for h, a in zip(nc.home, nc.away):
        for i, j, yv in ((h, a, 1.0), (a, h, 0.0)):
            feat = []
            for hi_t, lo_t in pairs:
                feat.append(1.0 if (tier[i], tier[j]) == (hi_t, lo_t) else (-1.0 if (tier[i], tier[j]) == (lo_t, hi_t) else 0.0))
            feat.append(s[ix[i]] - s[ix[j]])
            rows.append(feat); ys.append(yv); noise.append(ns[ix[i]] + ns[ix[j]])
    X, y, w = np.array(rows), np.array(ys), np.full(len(ys), 0.5)
    beta = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ beta))
        H = (X * (w * p * (1 - p))[:, None]).T @ X
        step = np.linalg.solve(H, X.T @ (w * (y - p)))
        beta += step
        if np.max(np.abs(step)) < 1e-10:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    # disattenuate the strength slope: reliability of the gap after removing pair-type means
    gap = X[:, 3]
    resid = gap.copy()
    for k in range(3):
        for sgn in (-1, 1):
            m = X[:, k] == sgn
            resid[m] -= gap[m].mean()
    same = (X[:, :3] == 0).all(1)
    resid[same] -= gap[same].mean()
    lam = 1 - float(np.mean(noise)) / float(np.var(resid))
    share = {f"{a}_hosts_vs_{b}": round(float(np.mean([tier[h] == a for h, aw in zip(nc.home, nc.away) if {tier[h], tier[aw]} == {a, b}])), 4) for a, b in pairs}
    return {"n_games": int(len(nc)), "tier_pair_logit": {f"{a}_vs_{b}": round(float(beta[k]), 4) for k, (a, b) in enumerate(pairs)},
            "tier_pair_se": {f"{a}_vs_{b}": round(float(se[k]), 4) for k, (a, b) in enumerate(pairs)},
            "strength_slope_observed": round(float(beta[3]), 4), "strength_slope_se": round(float(se[3]), 4),
            "reliability": round(lam, 4), "strength_slope": round(float(beta[3] / lam), 4), "raw_higher_tier_hosts": share}


def two_way_se(v: np.ndarray, g1: np.ndarray, g2: np.ndarray) -> float:
    e = v - v.mean(); n = len(v)
    def part(g):
        s = pd.Series(e).groupby(g).sum().values
        return float((s ** 2).sum())
    pair = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return float(np.sqrt(max(part(g1) + part(g2) - part(pair), 0.0)) / n)


def gate_targets(sb, tier) -> dict:
    rows = []
    for s, o in (("home", "away"), ("away", "home")):
        rows.append(pd.DataFrame({"team": sb[s].values, "opp": sb[o].values, "r": sb[f"{s}_score"].values.astype(float)}))
    tg = pd.concat(rows, ignore_index=True)
    tg["bt"] = tg.team.map(tier); tg["pt"] = tg.opp.map(tier)
    mat = {}
    for bt in TIERS:
        mat[bt] = {}
        for pt in TIERS:
            c = tg[(tg.bt == bt) & (tg.pt == pt)]
            se = two_way_se(c.r.values, c.team.values, c.opp.values)
            mat[bt][pt] = {"r_per_game": round(float(c.r.mean()), 3), "n_team_games": int(len(c)), "se": round(se, 4), "tol": round(3 * se, 3)}
    hw = (sb.home_score > sb.away_score).astype(float).values
    diff = (sb.home_score - sb.away_score).astype(float).values
    se_w = two_way_se(hw, sb.home.values, sb.away.values)
    se_d = two_way_se(diff, sb.home.values, sb.away.values)
    home = {"_note": f"{SRC}. Listed home team (no neutral-site flag in the feed). Tolerance 3 SE, two-way cluster-robust (home team, away team).",
            "conf": "A", "n_games": int(len(sb)),
            "home_win_pct": {"value": round(float(hw.mean()), 4), "tol": round(3 * se_w, 4)},
            "home_run_diff": {"value": round(float(diff.mean()), 4), "tol": round(3 * se_d, 4)},
            "home_runs_per_game": round(float(sb.home_score.mean()), 3), "away_runs_per_game": round(float(sb.away_score.mean()), 3)}
    tm = {"_note": f"{SRC}. Runs per team-game by batting tier (rows) and pitching tier (columns). Tolerance 3 SE, two-way cluster-robust (batting team, pitching team). Gate for Phase 2.",
          "conf": "A", "matrix": mat}
    return {"tier_matrix_2025": tm, "home_2025": home}


def main() -> None:
    sb, names, tier, conf = load()
    f0 = fit(sb, names, parks=False)     # the Phase 2 fit, kept for the within-game residual correlation without parks
    f = fit(sb, names)
    comp = components(names, tier, conf, f)
    host = hosting(sb, names, tier, conf, f)
    gate = gate_targets(sb, tier)
    talent = {
        "_note": ("Team strength on the log-runs scale (quasi-Poisson fit of runs on team offense o, run prevention d and the home slot; "
                  "(o, d) = tier mean + conference effect + team effect, noise removed by method of moments). " + SRC + "."),
        "src": SRC, "n_games": f["n_games"], "n_teams": len(names), "dispersion": round(f["phi"], 4),
        "residual_corr_within_game": round(f0["residual_corr"], 4),
        "residual_corr_within_game_with_parks": round(f["residual_corr"], 4),
        "dispersion_without_parks": round(f0["phi"], 4),
        "parks": parks_mom(names, tier, f),
        "log_runs_league": round(f["a"], 4), "home_log_ratio": round(f["h"], 4), "home_log_ratio_se": round(f["h_se"], 4),
        **comp, "hosting": host,
    }
    inp = json.loads(INPUTS.read_text()); inp["team_talent"] = talent
    INPUTS.write_text(json.dumps(inp, indent=1, default=float) + "\n")
    g = json.loads(GATE.read_text()); g.update(gate); g["team_talent"] = talent
    GATE.write_text(json.dumps(g, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in talent.items() if k not in ("_note",)}, indent=1))
    print(json.dumps(gate, indent=1))


if __name__ == "__main__":
    main()
