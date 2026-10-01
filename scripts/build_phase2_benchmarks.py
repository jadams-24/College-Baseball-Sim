"""Phase 2 inputs and gate benchmarks from the 2025 data.

Writes data/ncaa_2025/derived/phase2_inputs_2025.json (everything the league
generator and engine read) and the Phase 2 blocks of benchmarks.json:
  player_talent_2025, team_strength_2025, usage_2025, qualified_players_2025,
  leaderboards_2025.

Talent model, per rate r and on the logit scale:
  logit p = logit L_r + mu_role + T_tier + U_team + e_player
  - T_tier: batting and pitching tier effects from an additive logit fit to the
    3x3 (batting tier x pitching tier) cell table of the play-by-play.
  - U_team, e_player: variance components by method of moments. Observed player
    rates minus their tier-cell expectation have variance = true + binomial noise;
    the noise term sum q(1-q)/n is subtracted. Team means (teams with a full season
    in the sample) give var(U) + var(e)/k_eff; solving the two equations splits
    team from individual variance. Probability-scale variances are converted to
    the logit scale at the group mean rate.
Rates: K, BB, HBP, HR per PA; BABIP = hits / (non-HR balls in play excluding
reached-on-error); XBH = (2B+3B) / (1B+2B+3B).
Correlations: player-level covariance of the same residuals with the multinomial
sampling covariance subtracted, projected to the nearest positive semi-definite matrix.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.players import load_pa  # noqa: E402

P = Path("data/ncaa_2025/pbp/parsed")
OUT = Path("data/ncaa_2025/derived/phase2_inputs_2025.json")
BENCH = Path("benchmarks.json")
TODAY = dt.date.today().isoformat()
TIERS = ("p4", "mid", "low")
RATES = ("K", "BB", "HBP", "HR", "BABIP", "XBH")
FULL_SEASON_GAMES = 40     # a team with this many games in the sample has (nearly) its whole season
MIN_TEAM_GAMES = 25        # teams used for player-level estimates (complete enough rosters)
MIN_TRIALS = 30            # player-seasons below this many trials are left out of the moments
WEEKEND = {4, 5, 6}        # Fri, Sat, Sun
HIT = ("1B", "2B", "3B")
BIP_NOROE = ("1B", "2B", "3B", "FO", "GO", "GIDP", "DP", "SF", "SH", "FC")


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def trials_successes(df: pd.DataFrame, rate: str) -> tuple[pd.Series, pd.Series]:
    r = df.result
    if rate in ("K", "BB", "HBP", "HR"):
        n = pd.Series(1, index=df.index)
        x = {"K": r == "K", "BB": r.isin(["BB", "IBB"]), "HBP": r == "HBP", "HR": r == "HR"}[rate].astype(int)
    elif rate == "BABIP":
        n = r.isin(BIP_NOROE).astype(int)
        x = r.isin(HIT).astype(int)
    else:  # XBH
        n = r.isin(HIT).astype(int)
        x = r.isin(["2B", "3B"]).astype(int)
    return n, x


def main() -> None:
    pa = load_pa()
    gm = pd.read_csv(P / "games_2025.csv")
    rc = pd.read_csv(P / "runs_charged_2025.csv.gz")
    teams = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv")
    tier_of = dict(zip(teams.ncaa_team_id, teams.tier))
    d1_share = teams.tier.value_counts(normalize=True).to_dict()
    gm["wd"] = pd.to_datetime(gm.game_date).dt.dayofweek
    pa = pa.merge(gm[["game_id", "wd"]], on="game_id", how="left").sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["bt"] = pa.bat_team_id.map(tier_of)
    pa["pt"] = pa.pit_team_id.map(tier_of)
    pa = pa[pa.bt.notna() & pa.pt.notna()].copy()
    g2 = pd.concat([gm[["game_id", "home_team_id"]].rename(columns={"home_team_id": "t"}), gm[["game_id", "away_team_id"]].rename(columns={"away_team_id": "t"})])
    games_in_sample = g2.groupby("t").game_id.nunique()
    full_teams = set(games_in_sample[games_in_sample >= FULL_SEASON_GAMES].index)
    est_teams = set(games_in_sample[games_in_sample >= MIN_TEAM_GAMES].index)
    league = {}
    src = f"WMT play-by-play, {pa.game_id.nunique()} games / {len(pa)} PA, 2025 (data/ncaa_2025/pbp, built {TODAY})"

    # ---- league rate and tier effects ------------------------------------------------
    tier_fx = {}
    for rate in RATES:
        n, x = trials_successes(pa, rate)
        d = pd.DataFrame({"bt": pa.bt, "pt": pa.pt, "n": n, "x": x})
        cell = d.groupby(["bt", "pt"])[["n", "x"]].sum()
        L = cell.x.sum() / cell.n.sum()
        league[rate] = L
        # weighted least squares: logit(cell) = a + B_bt + P_pt, weights n p (1-p)
        rows, y, w = [], [], []
        for (b, p_), c in cell.iterrows():
            pr = c.x / c.n
            rows.append([1] + [int(b == t) for t in TIERS[1:]] + [int(p_ == t) for t in TIERS[1:]])
            y.append(logit(pr)); w.append(c.n * pr * (1 - pr))
        X, Y, W = np.array(rows, float), np.array(y), np.diag(w)
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ Y)
        B = {"p4": 0.0, "mid": beta[1], "low": beta[2]}
        Pp = {"p4": 0.0, "mid": beta[3], "low": beta[4]}
        # centre each set on the D1 team mix so an average team is 0
        cb = sum(d1_share[t] * B[t] for t in TIERS); cp = sum(d1_share[t] * Pp[t] for t in TIERS)
        tier_fx[rate] = {"bat": {t: round(B[t] - cb, 4) for t in TIERS}, "pit": {t: round(Pp[t] - cp, 4) for t in TIERS},
                         "intercept": round(beta[0] + cb + cp, 4),
                         "max_cell_residual": round(float(np.max(np.abs(Y - X @ beta))), 4)}

    def expected(df: pd.DataFrame, rate: str) -> np.ndarray:
        f = tier_fx[rate]
        return expit(f["intercept"] + df.bt.map(f["bat"]).values + df.pt.map(f["pit"]).values)

    # ---- player-season lines -----------------------------------------------------------
    first = pa.groupby(["game_id", "pit_team_id"]).pkey.first().rename("starter").reset_index()
    pa = pa.merge(first, on=["game_id", "pit_team_id"], how="left")
    pa["is_sp"] = (pa.pkey == pa.starter).astype(int)
    pa["weekend"] = pa.wd.isin(WEEKEND).astype(int)

    def player_lines(side: str) -> pd.DataFrame:
        team_col, key = ("bat_team_id", "bkey") if side == "bat" else ("pit_team_id", "pkey")
        rows = []
        for rate in RATES:
            n, x = trials_successes(pa, rate)
            q = expected(pa, rate)
            d = pd.DataFrame({"team": pa[team_col], "key": pa[key], "n": n, "x": x, "qn": q * n, "qqn": q * (1 - q) * n})
            agg = d.groupby(["team", "key"])[["n", "x", "qn", "qqn"]].sum()
            agg.columns = [f"{rate}_{c}" for c in agg.columns]
            rows.append(agg)
        lines = pd.concat(rows, axis=1).reset_index()
        lines["pa"] = lines.K_n
        lines["tier"] = lines.team.map(tier_of)
        return lines

    bat = player_lines("bat")
    pit = player_lines("pit")
    # batter groups: regulars = top 9 by PA on their team
    bat["rank"] = bat.groupby("team").pa.rank(ascending=False, method="first")
    bat["group"] = np.where(bat["rank"] <= 9, "regular", "bench")
    # pitcher roles
    app = pa.groupby(["pit_team_id", "pkey", "game_id"]).agg(sp=("is_sp", "max"), wkd=("weekend", "max")).reset_index()
    role = app.groupby(["pit_team_id", "pkey"]).agg(apps=("game_id", "size"), starts=("sp", "sum"),
                                                     wkd_starts=("wkd", lambda s: int((s * app.loc[s.index, "sp"]).sum()))).reset_index()
    role["group"] = np.where(role.starts >= 0.5 * role.apps, np.where(role.wkd_starts >= 0.5 * role.starts, "sp_weekend", "sp_midweek"), "rp")
    pit = pit.merge(role.rename(columns={"pit_team_id": "team", "pkey": "key"}), on=["team", "key"], how="left")

    # ---- method of moments ------------------------------------------------------------
    def mom(df: pd.DataFrame, rate: str) -> dict:
        d = df[df[f"{rate}_n"] >= (MIN_TRIALS if rate in ("K", "BB", "HBP", "HR") else MIN_TRIALS // 2)]
        n, x, qn, qqn = d[f"{rate}_n"], d[f"{rate}_x"], d[f"{rate}_qn"], d[f"{rate}_qqn"]
        resid = x / n - qn / n
        w = n / n.sum()
        m = float((w * resid).sum())
        var_obs = float((w * (resid - m) ** 2).sum())
        # binomial noise of each player's observed rate is q(1-q)/n; take its weighted mean
        noise = float((w * (qqn / n) / n).sum())
        qbar = float((w * qn / n).sum())
        return {"n_players": int(len(d)), "trials": int(n.sum()), "qbar": qbar, "mean_resid": m,
                "var_obs": var_obs, "var_noise": noise, "var_true": max(var_obs - noise, 0.0)}

    def team_mom(df: pd.DataFrame, team_col: str, key: str, rate: str) -> dict:
        n_, x_ = trials_successes(pa, rate)
        q = expected(pa, rate)
        d = pd.DataFrame({"team": pa[team_col], "n": n_, "x": x_, "qn": q * n_, "qqn": q * (1 - q) * n_})
        d = d[d.team.isin(full_teams)]
        t = d.groupby("team")[["n", "x", "qn", "qqn"]].sum()
        resid = t.x / t.n - t.qn / t.n
        var_obs = float(resid.var(ddof=1))
        noise = float((t.qqn / t.n / t.n).mean())
        # effective number of players per team (trial-weighted)
        pl = pd.DataFrame({"team": pa[team_col], "key": pa[key], "n": n_})
        pl = pl[pl.team.isin(full_teams)].groupby(["team", "key"]).n.sum()
        shares = pl / pl.groupby(level=0).transform("sum")
        k_eff = float((1 / (shares ** 2).groupby(level=0).sum()).mean())
        return {"n_teams": int(len(t)), "var_obs": var_obs, "var_noise": noise, "var_true": max(var_obs - noise, 0.0), "k_eff": k_eff}

    talent = {"batter": {}, "pitcher": {}}
    for side, df, team_col, key, groups in (("batter", bat, "bat_team_id", "bkey", ("regular", "bench")),
                                            ("pitcher", pit, "pit_team_id", "pkey", ("sp_weekend", "sp_midweek", "rp"))):
        df_est = df[df.team.isin(est_teams)]
        for rate in RATES:
            if side == "pitcher" and rate == "XBH":
                continue  # hit-type mix is attributed to the batter (see notes)
            allp = mom(df_est[df_est.team.isin(full_teams)], rate)  # all players on full-season teams: var(U)+var(e)
            tm = team_mom(df, team_col, key, rate)
            k = tm["k_eff"]
            var_u = max((tm["var_true"] - allp["var_true"] / k) / (1 - 1 / k), 0.0)
            entry = {"league": round(league[rate], 5), "team_var_prob": var_u, "team_mom": tm, "all_players_mom": allp, "groups": {}}
            for g in groups:
                gm_ = mom(df_est[df_est.group == g], rate)
                base = gm_["qbar"]
                p_mean = base + gm_["mean_resid"]
                var_e = max(gm_["var_true"] - var_u, 0.0)
                jac = p_mean * (1 - p_mean)
                entry["groups"][g] = {
                    **{k2: (round(v, 6) if isinstance(v, float) else v) for k2, v in gm_.items()},
                    "mu_logit": round(float(logit(p_mean) - logit(base)), 4),
                    "sd_ind_logit": round(float(np.sqrt(var_e) / jac), 4),
                    "sd_total_true_logit": round(float(np.sqrt(gm_["var_true"]) / jac), 4),
                }
            jac_l = league[rate] * (1 - league[rate])
            entry["sd_team_logit"] = round(float(np.sqrt(var_u) / jac_l), 4)
            talent[side][rate] = entry

    # ---- correlations (regular batters, starting pitchers + relievers pooled) --------------
    def corr_matrix(df: pd.DataFrame, rates: tuple) -> dict:
        d = df[(df.pa >= 100)].copy()
        R, S = [], []
        for _, r in d.iterrows():
            v, s = [], np.zeros((len(rates), len(rates)))
            for i, rate in enumerate(rates):
                n_ = r[f"{rate}_n"]
                q = r[f"{rate}_qn"] / n_ if n_ else 0
                v.append(r[f"{rate}_x"] / n_ - q if n_ else 0.0)
                s[i, i] = q * (1 - q) / n_ if n_ else 0
            for i, a in enumerate(rates):
                for j, b in enumerate(rates):
                    if i != j and a in ("K", "BB", "HBP", "HR") and b in ("K", "BB", "HBP", "HR"):
                        qa = r[f"{a}_qn"] / r[f"{a}_n"]; qb = r[f"{b}_qn"] / r[f"{b}_n"]
                        s[i, j] = -qa * qb / r["pa"]
            R.append(v); S.append(s * r["pa"])
        R = np.array(R); w = d.pa.values / d.pa.sum()
        mu = (w[:, None] * R).sum(0)
        C = ((R - mu).T * w) @ (R - mu)
        Snoise = sum(w_i * s / p for w_i, s, p in zip(w, S, d.pa.values))  # mean sampling covariance
        T = C - Snoise
        sd = np.sqrt(np.clip(np.diag(T), 1e-12, None))
        corr = T / np.outer(sd, sd)
        vals, vecs = np.linalg.eigh((corr + corr.T) / 2)
        corr = vecs @ np.diag(np.clip(vals, 1e-3, None)) @ vecs.T
        dd = np.sqrt(np.diag(corr)); corr = corr / np.outer(dd, dd)
        return {"rates": list(rates), "n_players": int(len(d)), "matrix": [[round(float(c), 3) for c in row] for row in corr]}

    corr = {"batter": corr_matrix(bat[(bat.group == "regular") & bat.team.isin(est_teams)], RATES),
            "pitcher": corr_matrix(pit[pit.team.isin(est_teams)], ("K", "BB", "HBP", "HR"))}
    # pitcher BABIP: individual true variance is ~0 once team is removed (see talent table), so it
    # carries no individual correlation; team-level BABIP variance is kept in the team effect
    corr["pitcher"]["rates"].append("BABIP")
    for row in corr["pitcher"]["matrix"]:
        row.append(0.0)
    corr["pitcher"]["matrix"].append([0.0, 0.0, 0.0, 0.0, 1.0])

    # ---- usage tables --------------------------------------------------------------------
    # pitches per PA by result
    pp = pa[pa.pitches.notna()]
    pitches_by_result = {res: {str(int(k)): int(v) for k, v in Counter(g.pitches.clip(upper=14).astype(int)).items()} for res, g in pp.groupby(pp.result.replace({"IBB": "BB", "CI": "HBP"}))}
    # pull hazards: after each batter faced, was the pitcher replaced before the next batter?
    pa["outing"] = (pa.pkey != pa.groupby(["game_id", "pit_team_id"]).pkey.shift()).groupby([pa.game_id, pa.pit_team_id]).cumsum()
    pa["out_pitches"] = pa.groupby(["game_id", "pit_team_id", "outing"]).pitches.cumsum()
    pa["out_runs"] = pa.groupby(["game_id", "pit_team_id", "outing"]).runs_on_play.cumsum()
    nxt = pa.groupby(["game_id", "pit_team_id"]).pkey.shift(-1)
    pa["pulled"] = (nxt.notna() & (nxt != pa.pkey)).astype(int)
    pa["last_of_game"] = nxt.isna()
    pa["inning_end"] = ((pa.outs + pa.outs_on_play) >= 3).astype(int)
    h = pa[~pa.last_of_game & pa.out_pitches.notna()].copy()
    h["pbin"] = (h.out_pitches // 10).clip(upper=12).astype(int)
    h["rbin"] = h.out_runs.clip(upper=5).astype(int)

    def hazard(df: pd.DataFrame, keys: list) -> dict:
        g = df.groupby(keys).pulled.agg(["sum", "count"])
        return {"|".join(str(v) for v in (k if isinstance(k, tuple) else (k,))): [int(r["sum"]), int(r["count"])] for k, r in g.iterrows()}
    sp = h[h.is_sp == 1]; rp = h[h.is_sp == 0]
    usage = {
        "pitches_per_pa_by_result": pitches_by_result,
        "starter_pull": {"keys": ["weekend", "pitch_bin10", "runs_bin", "inning_end"], "table": hazard(sp, ["weekend", "pbin", "rbin", "inning_end"]),
                         "backoff": hazard(sp, ["weekend", "pbin", "inning_end"])},
        "reliever_pull": {"keys": ["pitch_bin10", "runs_bin", "inning_end"], "table": hazard(rp, ["pbin", "rbin", "inning_end"]),
                          "backoff": hazard(rp, ["pbin", "inning_end"])},
    }
    spg = pa[pa.is_sp == 1].groupby(["game_id", "pit_team_id"]).agg(bf=("result", "size"), pitches=("pitches", "sum"), outs=("outs_on_play", "sum"), wk=("weekend", "first"))
    usage["starter_summary"] = {wk: {"starts": int(len(g)), "bf_mean": round(g.bf.mean(), 2), "pitches_mean": round(g.pitches.mean(), 1), "ip_mean": round(g.outs.mean() / 3, 2)} for wk, g in
                                (("weekend", spg[spg.wk == 1]), ("midweek", spg[spg.wk == 0]))}
    usage["starter_bf_share"] = {"weekend": round(pa[pa.weekend == 1].is_sp.mean(), 4), "midweek": round(pa[pa.weekend == 0].is_sp.mean(), 4)}
    usage["pitchers_per_team_game"] = round(pa.groupby(["game_id", "pit_team_id"]).pkey.nunique().mean(), 3)
    # lineup: share of team games in which the k-th most-used batter batted
    fb = pa[pa.bat_team_id.isin(full_teams)]
    app_b = fb.groupby(["bat_team_id", "bkey"]).game_id.nunique().rename("g").reset_index()
    app_b["tg"] = app_b.bat_team_id.map(games_in_sample)
    app_b["share"] = app_b.g / app_b.tg
    app_b["rank"] = app_b.groupby("bat_team_id").share.rank(ascending=False, method="first")
    usage["batter_appearance_share_by_rank"] = {str(int(k)): round(v, 4) for k, v in app_b.groupby("rank").share.mean().head(14).items()}
    usage["batters_per_team_game"] = round(fb.groupby(["game_id", "bat_team_id"]).bkey.nunique().mean(), 3)
    # starts: the first nine distinct batters of each team-game are that game's starting lineup
    st = fb.drop_duplicates(["game_id", "bat_team_id", "bkey"]).copy()
    st["order"] = st.groupby(["game_id", "bat_team_id"]).cumcount()
    st = st[st.order < 9]
    start_b = st.groupby(["bat_team_id", "bkey"]).game_id.nunique().rename("gs").reset_index()
    start_b["share"] = start_b.gs / start_b.bat_team_id.map(games_in_sample)
    start_b["rank"] = start_b.groupby("bat_team_id").share.rank(ascending=False, method="first")
    usage["batter_start_share_by_rank"] = {str(int(k)): round(v, 4) for k, v in start_b.groupby("rank").share.mean().head(16).items()}
    usage["batter_start_share_by_rank_note"] = "share of team games started by the k-th most-started batter, full-season teams; ranks sum to ~9"
    # reliever usage: share of relief batters faced by reliever rank on the staff
    rbf = pa[(pa.is_sp == 0) & pa.pit_team_id.isin(full_teams)].groupby(["pit_team_id", "pkey"]).size().rename("bf").reset_index()
    rbf["share"] = rbf.bf / rbf.groupby("pit_team_id").bf.transform("sum")
    rbf["rank"] = rbf.groupby("pit_team_id").share.rank(ascending=False, method="first")
    usage["reliever_bf_share_by_rank"] = {str(int(k)): round(v, 4) for k, v in rbf.groupby("rank").share.mean().head(10).items()}
    usage["earned_run_share"] = round(1 - rc.unearned.mean(), 4)
    usage["_src"] = src

    # ---- write ---------------------------------------------------------------------------
    out = {"_meta": {"built": TODAY, "src": src, "full_season_teams": len(full_teams), "estimation_teams": len(est_teams),
                     "full_season_teams_by_tier": dict(Counter(tier_of[t] for t in full_teams)), "d1_tier_share": d1_share},
           "league": {k: round(v, 5) for k, v in league.items()}, "tier_effects_logit": tier_fx, "talent": talent,
           "correlation": corr, "usage": usage}
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(f"wrote {OUT}")
    for side in talent:
        for rate, e in talent[side].items():
            gs = "  ".join(f"{g}: mu {v['mu_logit']:+.3f} sd_ind {v['sd_ind_logit']:.3f} (n {v['n_players']})" for g, v in e["groups"].items())
            print(f"{side:7} {rate:5} L {e['league']:.4f} team_sd {e['sd_team_logit']:.3f} | {gs}")
    for side in corr:
        print(side, corr[side]["rates"]); [print("  ", r) for r in corr[side]["matrix"]]
    print("tier effects K:", tier_fx["K"], "\nHR:", tier_fx["HR"])
    print("usage:", {k: usage[k] for k in ("starter_summary", "starter_bf_share", "pitchers_per_team_game", "batters_per_team_game", "earned_run_share")})
    print("appearance share by rank:", usage["batter_appearance_share_by_rank"]); print("reliever share by rank:", usage["reliever_bf_share_by_rank"])


if __name__ == "__main__":
    main()
