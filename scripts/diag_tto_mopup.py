"""Real-data sizes, round 2, for the "offense extremes compressed" watch item: candidates 3 (times through the order)
and 4 (mop-up pitching in blowouts). Owner: "size times through the order and mop-up pitching in blowouts next, from
real data only... Keep the running total of explained variance. Sizes only, no fixes."

Measurement only: nothing here changes a benchmark, the engine or its config, and no season is simulated. Sim values
are copied from the committed 40-season reports. Conventions, loaders and the common scale are those of
scripts/diag_sizes.py (round 1):

  common scale  quasi-Poisson dispersion of runs per team-game around the scoreboard fit, real 2.6185 against sim
                2.224 (missing 0.3945). A component t_g of a team-game's runs (centred) changes that team-game's
                Pearson term from (r_g - t_g)^2 / mu_g to r_g^2 / mu_g, so its size is
                    dphi = mean((r_g^2 - (r_g - t_g)^2) / mu_g) = mean(t_g^2 / mu_g) + 2 mean((r_g - t_g) t_g / mu_g),
                its own variance plus twice its covariance with the rest of the team-game's runs. For a component
                independent of the rest this is round 1's mean(V / mu). r_g and mu_g are round 1's: WMT half-innings,
                expected runs from the scoreboard fit without parks (diag_sizes.expected_runs).

  5. Candidate 3, times through the order (TTO). (a) The change in a batter's outcome by his 1st / 2nd / 3rd / 4th
     time facing the game's starter, within starts, with batter fixed effects. (b) The variance that a penalty of that
     size adds to runs per team-game once it is combined with the hook (long starts take the penalty, short ones do
     not). (c) The real pull hazard by runs allowed in the outing at a given pitch count, and what else moves it.
  6. Candidate 4, mop-up pitching. (a) Season quality of the relievers who enter at margins of 5+ and 8+, against
     close games. (b) Their run values in those outings against what their quality predicts. (c) Persistence of a
     5+ margin, its size on the dispersion scale, and its size on the 15+ bin and the run-rule rate.
  Running total: candidates 11 and 12 (round 1) plus 3 and 4.

Reads data/ (committed) and reports/diagnosis_sizes.json (round 1). Appends its sections to
reports/diagnosis_sizes.md and its keys to reports/diagnosis_sizes.json, keeping round 1's content; run after
scripts/diag_sizes.py.

    python3 scripts/diag_tto_mopup.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import diag_sizes as ds  # noqa: E402  (round 1: loaders, the fit, the common scale)

P = ds.P
OUT_MD, OUT_JSON = ds.OUT_MD, ds.OUT_JSON
RNG_SEED = 20261007
BOOT = 400
REAL_PHI, SIM_PHI = ds.REAL_PHI, ds.SIM_PHI
MISS = REAL_PHI - SIM_PHI
FULL_SEASON_GAMES = 40          # config.phase6.FULL_SEASON_GAMES: a team with this many parsed games has its season
WEEKEND = {3, 4, 5, 6}          # Thu-Sun, as scripts/build_phase6_pull.py
MARKER_START = "<!-- round2: scripts/diag_tto_mopup.py -->"
MARKER_END = "<!-- /round2 -->"
POINTER = ("Round 2 (2026-10-07, `scripts/diag_tto_mopup.py`): candidates 3 (times through the order) and 4 (mop-up "
           "pitching) and the updated running total are in the section \"Round 2\" at the end.")
# sim values (40-season reports, read here only for comparison)
SIM = {"bin15": 0.0533, "run_rule": 0.1201}
REAL = {"bin15": 0.0650, "run_rule_product": 0.1509, "run_rule_direct": 0.1440}   # round 1, D1-vs-D1


# ----------------------------------------------------------------------------------------------------------------------
# plate appearances: base-out run values, linear weights, outings, starters
# ----------------------------------------------------------------------------------------------------------------------

_PA = {}


def plate_appearances() -> pd.DataFrame:
    """Every parsed plate appearance in game order, with:
      rv      the linear weight of its result (mean RE24 of that result over the sample; runs per PA, context-free);
      re24    its own RE24 (end state from batter_to / r*_to, run expectancy from the sample's complete half-innings);
      outing  the pitching team's outing number in the game (1 = the starter's), is_sp, starter, BF number;
      tto     the batter's time facing this pitcher in the game (1, 2, 3, 4+), counted by batter;
      pitches_before  the pitcher's pitches before this PA in the outing (missing pitch counts as the PA mean, 2.8%);
      margin  the score from the pitching team's side at the start of the PA; weekend (Thu-Sun)."""
    if "pa" in _PA:
        return _PA["pa"]
    from lib.players import load_pa
    pa = load_pa().sort_values(["game_id", "group_id"]).reset_index(drop=True)
    rev = pd.read_csv(P / "runner_events_2025.csv.gz")
    gm = pd.read_csv(P / "games_2025.csv")
    key = ["game_id", "inning", "half"]
    # complete half-innings: three outs recorded (plate appearances plus base-running outs)
    outs_hi = pa.groupby(key).outs_on_play.sum().add(rev[rev.to_base == 0].groupby(key).size(), fill_value=0)
    complete = outs_hi[outs_hi >= 3].index
    # runs from the start of each PA to the end of its half-inning: runs of this and later PAs, plus base-running runs
    # at or after this PA's group
    pa["_runs_after"] = pa.iloc[::-1].groupby(key).runs_on_play.cumsum().iloc[::-1]
    rs = rev[rev.to_base == 4][key + ["group_id"]].copy()
    if len(rs):
        m = pa[key + ["group_id"]].reset_index().merge(rs, on=key, suffixes=("", "_r"))
        m = m[m.group_id_r >= m.group_id]
        extra = m.groupby("index").size()
        pa["_runs_after"] += extra.reindex(pa.index).fillna(0).values
    pa["state"] = pa.outs.astype(int) * 8 + pa.on1.astype(int) + 2 * pa.on2.astype(int) + 4 * pa.on3.astype(int)
    idx = pa.set_index(key).index
    ok = idx.isin(complete)
    re = pa[ok].groupby("state")._runs_after.mean()
    out_end = pa.outs + pa.outs_on_play
    b1 = (pa.batter_to == 1) | (pa.r1_to == 1)
    b2 = (pa.batter_to == 2) | (pa.r1_to == 2) | (pa.r2_to == 2)
    b3 = (pa.batter_to == 3) | (pa.r1_to == 3) | (pa.r2_to == 3) | (pa.r3_to == 3)
    end_state = out_end.clip(upper=2).astype(int) * 8 + b1.astype(int) + 2 * b2.astype(int) + 4 * b3.astype(int)
    re_end = np.where(out_end >= 3, 0.0, end_state.map(re).values)
    pa["re24"] = re_end - pa.state.map(re).values + pa.runs_on_play
    res = pa.result.replace({"IBB": "BB", "CI": "HBP"})
    lw = pa[ok].groupby(res[ok]).re24.mean()
    pa["res"] = res
    pa["rv"] = res.map(lw).values
    pa["K"] = (res == "K").astype(float)
    pa["BB"] = (res == "BB").astype(float)
    pa["HBP"] = (res == "HBP").astype(float)
    pa["HR"] = (res == "HR").astype(float)
    pa["OB"] = res.isin(["1B", "2B", "3B", "HR", "BB", "HBP"]).astype(float)
    # outings, starters
    g = pa.groupby(["game_id", "pit_team_id"])
    pa["outing"] = (pa.pkey != g.pkey.shift()).groupby([pa.game_id, pa.pit_team_id]).cumsum()
    pa["starter"] = g.pkey.transform("first")
    pa["is_sp"] = (pa.outing == 1)
    pa["bf"] = pa.groupby(["game_id", "pit_team_id", "outing"]).cumcount() + 1
    pp = pa.pitches.fillna(pa.pitches.mean())
    pa["pitches_before"] = pp.groupby([pa.game_id, pa.pit_team_id, pa.outing]).cumsum() - pp
    pa["out_runs_before"] = pa.groupby(["game_id", "pit_team_id", "outing"]).runs_on_play.cumsum() - pa.runs_on_play
    pa["tto"] = (pa.groupby(["game_id", "pit_team_id", "outing", "bkey"]).cumcount() + 1).clip(upper=4)
    pa["tto_order"] = ((pa.bf - 1) // 9 + 1).clip(upper=4)
    pa["margin"] = np.where(pa.half == "T", pa.home_score - pa.away_score, pa.away_score - pa.home_score)
    wd = pd.to_datetime(gm.game_date).dt.dayofweek
    pa["weekend"] = pa.game_id.map(dict(zip(gm.game_id, wd.isin(WEEKEND)))).astype(bool)
    pa["pid"] = pa.pit_team_id.astype(str) + "|" + pa.pkey
    pa["bid"] = pa.bat_team_id.astype(str) + "|" + pa.bkey
    pa = pa.drop(columns=["_runs_after"])
    _PA["pa"] = pa
    _PA["lw"] = lw
    _PA["re"] = re
    return pa


def full_season_teams() -> set:
    gm = pd.read_csv(P / "games_2025.csv")
    g2 = pd.concat([gm.home_team_id, gm.away_team_id])
    n = g2.value_counts()
    return set(n[n >= FULL_SEASON_GAMES].index)


# ----------------------------------------------------------------------------------------------------------------------
# two-way fixed effects by alternating projections, cluster-robust SEs
# ----------------------------------------------------------------------------------------------------------------------

def _codes(s) -> np.ndarray:
    return pd.factorize(s)[0]


def absorb(M: np.ndarray, groups: list, tol: float = 1e-9, max_iter: int = 1000) -> np.ndarray:
    """Residualize the columns of M on the fixed effects of each grouping (alternating projections)."""
    M = M.astype(float).copy()
    cnt = [np.bincount(g) for g in groups]
    for _ in range(max_iter):
        delta = 0.0
        for g, c in zip(groups, cnt):
            for j in range(M.shape[1]):
                mu = np.bincount(g, weights=M[:, j], minlength=len(c)) / c
                M[:, j] -= mu[g]
                delta = max(delta, float(np.abs(mu).max()))
        if delta < tol:
            break
    return M


def fe_ols(Y: np.ndarray, X: np.ndarray, groups: list, cluster: np.ndarray) -> list:
    """OLS of each column of Y on X with the fixed effects of `groups` absorbed (FWL); cluster-robust covariance (CR1).
    Returns one (b, se, V) per column of Y."""
    Y = Y.reshape(len(Y), -1)
    Z = absorb(np.column_stack([Y, X]), groups)
    Yr, Xr = Z[:, :Y.shape[1]], Z[:, Y.shape[1]:]
    XtX = Xr.T @ Xr
    inv = np.linalg.inv(XtX)
    G = int(cluster.max()) + 1
    out = []
    for j in range(Y.shape[1]):
        b = inv @ (Xr.T @ Yr[:, j])
        e = Yr[:, j] - Xr @ b
        S = np.column_stack([np.bincount(cluster, weights=Xr[:, k] * e, minlength=G) for k in range(X.shape[1])])
        V = inv @ (S.T @ S) @ inv * G / (G - 1)
        out.append((b, np.sqrt(np.diag(V)), V))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 5. Times through the order (candidate 3)
# ----------------------------------------------------------------------------------------------------------------------

OUTCOMES = ("rv", "K", "BB", "HBP", "HR", "OB")
HOOK_LABELS = {"runs_in_outing": "runs in the outing", "runs_this_half_inning": "runs in the current half-inning",
               "runners_on_after_pa": "runners on base after the PA", "trailing_by_1_4": "trailing by 1-4",
               "trailing_by_5plus": "trailing by 5+", "leading_by_5plus": "leading by 5+",
               "next_batter_tto3plus": "next batter's 3rd+ time through"}
MAIN_SPEC = "team_game_fe"
PITCH_EDGES = (25, 50, 75, 100)        # bins of the starter's pitches before the PA (reporting bins, not rates)


def tto_regressions(pa: pd.DataFrame) -> dict:
    """y = batter FE + pitcher-outing FE (or pitcher FE) + TTO dummies (2, 3, 4+; the 1st is the reference) on the
    starter's plate appearances, with every relief PA included (zero TTO dummies, its own outing FE) so that the batter
    effects use all of a batter's PAs. CR1 SEs clustered by pitcher (a starter's starts are one cluster)."""
    d = pa.copy()
    d["sp_tto"] = np.where(d.is_sp, d.tto, 0)
    d["sp_tto_order"] = np.where(d.is_sp, d.tto_order, 0)
    d["app"] = d.game_id.astype(str) + "|" + d.pid + "|" + d.outing.astype(str)
    d["tg"] = d.game_id.astype(str) + "|" + d.bat_team_id.astype(str)
    out = {}
    specs = {
        "pitcher_fe": dict(fe="pid", sample=None, pitch=False, tto="sp_tto"),
        "team_game_fe": dict(fe="pid+tg", sample=None, pitch=False, tto="sp_tto"),
        "team_game_fe_pitch_bins": dict(fe="pid+tg", sample=None, pitch=True, tto="sp_tto"),
        "start_fe": dict(fe="app", sample=None, pitch=False, tto="sp_tto"),
        "start_fe_order": dict(fe="app", sample=None, pitch=False, tto="sp_tto_order"),
        "start_fe_pitch_bins": dict(fe="app", sample=None, pitch=True, tto="sp_tto"),
        "balanced_27": dict(fe="app", sample="bal27", pitch=False, tto="sp_tto"),
    }
    sp_bf = d[d.is_sp].groupby(["game_id", "pit_team_id"]).bf.max()
    long_start = d.set_index(["game_id", "pit_team_id"]).index.map(sp_bf).values >= 27
    for name, s in specs.items():
        x = d
        if s["sample"] == "bal27":
            keep = (~x.is_sp) | (long_start & (x.bf <= 27))
            x = x[keep]
        t = x[s["tto"]].values
        cols = [(t == k).astype(float) for k in (2, 3, 4)]
        labels = ["tto2", "tto3", "tto4"]
        if s["sample"] == "bal27":
            cols, labels = cols[:2], labels[:2]
        if s["pitch"]:
            pb = np.searchsorted(PITCH_EDGES, x.pitches_before.values, side="right")
            for k in range(1, len(PITCH_EDGES) + 1):
                cols.append(((pb == k) & x.is_sp.values).astype(float)); labels.append(f"pitch_bin{k}")
        X = np.column_stack(cols)
        groups = [_codes(x.bid)] + [_codes(x[f]) for f in s["fe"].split("+")]
        cl = _codes(x.pid)
        fits = fe_ols(x[list(OUTCOMES)].values.astype(float), X, groups, cl)
        res = {yname: {lab: {"b": float(bb), "se": float(ss)} for lab, bb, ss in zip(labels, b, se)}
               for yname, (b, se, _) in zip(OUTCOMES, fits)}
        if name == MAIN_SPEC:
            res["_cov_rv"] = fits[0][2][:3, :3].tolist()
        res["n_pa"] = int(len(x)); res["n_starter_pa"] = int(x.is_sp.sum())
        res["n_by_tto"] = {str(k): int(((t == k) & x.is_sp.values).sum()) for k in (1, 2, 3, 4)}
        out[name] = res
    # raw means by TTO (starter PAs), for reference
    sp = d[d.is_sp]
    out["raw_means"] = {str(k): {y: float(sp.loc[sp.tto == k, y].mean()) for y in OUTCOMES} for k in (1, 2, 3, 4)}
    out["league_rv_per_pa"] = float(d.rv.mean())
    return out


def team_games() -> pd.DataFrame:
    """Round 1's team-game table: runs R, expected runs mu (scoreboard fit without parks, spread over the half-innings
    played and scaled to the sample), residual r = R - mu, and the same split into the half-innings begun by the
    fielding team's starter (S) and the rest (relief, Rl). Teams outside the fit are dropped (diag_sizes.expected_runs)."""
    x = ds.expected_runs(ds.half_innings())
    x = x.assign(rS=np.where(x.by_starter, x.r, 0.0), eS=np.where(x.by_starter, x.e, 0.0))
    g = x.groupby(["game_id", "bat_team_id"]).agg(R=("runs", "sum"), mu=("e", "sum"), r=("r", "sum"), rS=("rS", "sum"), eS=("eS", "sum"),
                                                  pit_team_id=("pit_team_id", "first"))
    g["rR"] = g.r - g.rS
    return g


def dphi_component(tg: pd.DataFrame, t: np.ndarray) -> dict:
    """Size of a component t_g of team-game runs on the dispersion scale (module docstring): t is centred over the
    team-games, dphi = mean(t^2 / mu) + 2 mean((r - t) t / mu); the covariance with the rest is also split into the
    half-innings begun by the starter and the relief half-innings."""
    t = np.asarray(t, float); t = t - t.mean()
    mu, r = tg.mu.values, tg.r.values
    var = float(np.mean(t ** 2 / mu))
    cov = float(2 * np.mean((r - t) * t / mu))
    return {"dphi": var + cov, "var_part": var, "cov_part": cov,
            "cov_part_starter_innings": float(2 * np.mean((tg.rS.values - t) * t / mu)),
            "cov_part_relief_innings": float(2 * np.mean(tg.rR.values * t / mu)),
            "sd_t": float(t.std()), "corr_t_rest": float(np.corrcoef(t, r - t)[0, 1])}


def tto_exposure(pa: pd.DataFrame, delta: dict) -> pd.Series:
    """Expected TTO runs per batting team-game: sum over its PAs against the opposing starter of delta[tto]."""
    sp = pa[pa.is_sp]
    v = sp.tto.map({1: 0.0, 2: delta[2], 3: delta[3], 4: delta[4]})
    return v.groupby([sp.game_id, sp.bat_team_id]).sum()


def hook_hazard(pa: pd.DataFrame, rng) -> dict:
    """Real pull hazard of starters after each batter (as scripts/build_phase2_benchmarks.py builds the engine's table:
    pitches and runs of the outing after the PA, runs counted on plate appearances), by runs allowed at a given pitch
    count; and a discrete-time logit with the engine's conditioning cells (pitch bin x inning end x weekend) plus runs
    allowed, then what the engine's table does not condition on: runs in the current half-inning, runners on base,
    the score margin, the next batter's time through the order. SEs clustered by pitcher (CR1)."""
    d = pa.copy()
    nxt = d.groupby(["game_id", "pit_team_id"]).pkey.shift(-1)
    d["pulled"] = (nxt.notna() & (nxt != d.pkey)).astype(int)
    d = d[nxt.notna() & d.is_sp].copy()
    pp = d.pitches.fillna(pa.pitches.mean())
    d["out_pitches"] = d.pitches_before + pp
    d["out_runs"] = d.out_runs_before + d.runs_on_play
    d["inning_end"] = ((d.outs + d.outs_on_play) >= 3).astype(int)
    d["pbin"] = (d.out_pitches // 10).clip(upper=12).astype(int)
    d["rbin"] = d.out_runs.clip(upper=5).astype(int)
    key = ["game_id", "inning", "half"]
    d["inning_runs"] = d.groupby(key + ["pit_team_id"]).runs_on_play.cumsum()
    b1 = (d.batter_to == 1) | (d.r1_to == 1); b2 = (d.batter_to == 2) | (d.r1_to == 2) | (d.r2_to == 2)
    b3 = (d.batter_to == 3) | (d.r1_to == 3) | (d.r2_to == 3) | (d.r3_to == 3)
    d["on_base"] = np.where(d.inning_end == 1, 0, b1.astype(int) + b2.astype(int) + b3.astype(int))
    # margin after the PA from the pitching team's side
    d["margin_after"] = d.margin - d.runs_on_play
    nb = d.groupby(["game_id", "pit_team_id"]).bf.transform("max")
    # the next batter's time through the order: TTO of batter number bf + 1 (by order)
    d["next_tto_order"] = ((d.bf) // 9 + 1).clip(upper=4)
    out = {"n_decisions": int(len(d)), "n_pulls": int(d.pulled.sum()), "n_starts": int(d.groupby(["game_id", "pit_team_id"]).ngroups)}
    # hazard table: inning ends, pitch bins grouped, runs 0..5+
    tab = {}
    for lo, hi in ((3, 4), (5, 6), (7, 8), (9, 10)):
        s = d[(d.inning_end == 1) & d.pbin.between(lo, hi)]
        g = s.groupby("rbin").pulled.agg(["mean", "size"])
        tab[f"{10 * lo}-{10 * hi + 9}"] = {str(k): {"h": float(v["mean"]), "n": int(v["size"]),
                                                     "se": float(np.sqrt(v["mean"] * (1 - v["mean"]) / v["size"]))} for k, v in g.iterrows()}
    out["hazard_inning_end_by_pitches_runs"] = tab
    mid = d[d.inning_end == 0]
    out["hazard_mid_inning"] = {"overall": float(mid.pulled.mean()), "n": int(len(mid))}
    # logits
    cell = d.pbin.astype(str) + "|" + d.inning_end.astype(str) + "|" + d.weekend.astype(int).astype(str)
    C = pd.get_dummies(cell).values.astype(float)
    cl = _codes(d.pid)
    y = d.pulled.values.astype(float)

    def run(extra: dict) -> dict:
        X = np.column_stack([C] + [v for v in extra.values()]) if extra else C
        b, V = logit_irls(y, X, cl)
        k = C.shape[1]
        return {name: {"b": float(b[k + i]), "se": float(np.sqrt(V[k + i, k + i]))} for i, name in enumerate(extra)}
    r1 = {f"runs_{k}": (d.rbin == k).astype(float).values for k in range(1, 6)}
    out["logit_runs_dummies"] = run(r1)
    out["logit_runs_linear"] = run({"runs_in_outing": d.out_runs.clip(upper=8).values.astype(float)})
    ext = {"runs_in_outing": d.out_runs.clip(upper=8).values.astype(float),
           "runs_this_half_inning": d.inning_runs.clip(upper=6).values.astype(float),
           "runners_on_after_pa": d.on_base.values.astype(float),
           "trailing_by_1_4": d.margin_after.between(-4, -1).astype(float).values,
           "trailing_by_5plus": (d.margin_after <= -5).astype(float).values,
           "leading_by_5plus": (d.margin_after >= 5).astype(float).values,
           "next_batter_tto3plus": (d.next_tto_order >= 3).astype(float).values}
    out["logit_extended"] = run(ext)
    out["engine"] = ("the 2025 table P(pulled | weekend rotation rank or midweek, "
                     "outing pitches // 10 (cap 12), outing runs (cap 5), inning just ended), backed off to the table "
                     "without runs when a cell has under MIN_HAZARD_N decisions, scaled by the pitcher's Stamina leash and "
                     "the tier / season-week multipliers. Nothing else enters: no current-inning runs, runners, margin or "
                     "times through the order.")
    return out


def logit_irls(y: np.ndarray, X: np.ndarray, cluster: np.ndarray, iters: int = 50) -> tuple:
    """Logistic regression by Newton-Raphson; CR1 sandwich covariance by cluster."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = np.clip(X @ b, -30, 30); p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    eta = np.clip(X @ b, -30, 30); p = 1 / (1 + np.exp(-eta))
    H = X.T @ (X * (p * (1 - p) + 1e-9)[:, None]) + 1e-6 * np.eye(X.shape[1])
    inv = np.linalg.inv(H)
    G = int(cluster.max()) + 1
    S = np.column_stack([np.bincount(cluster, weights=X[:, k] * (y - p), minlength=G) for k in range(X.shape[1])])
    V = inv @ (S.T @ S) @ inv * G / (G - 1)
    return b, V


def item5() -> dict:
    rng = np.random.default_rng(RNG_SEED + 5)
    pa = plate_appearances()
    out = {"n_pa": int(len(pa)), "n_games": int(pa.game_id.nunique()), "n_starts": int(pa[pa.is_sp].groupby(["game_id", "pit_team_id"]).ngroups),
           "linear_weights": {k: float(v) for k, v in _PA["lw"].items()}}
    reg = tto_regressions(pa)
    out["regressions"] = reg
    # relief placebo: relievers' first-time batters by inning, pitcher + batter FE (a game-time trend that is not TTO)
    rl = pa[(~pa.is_sp) & (pa.tto == 1)].copy()
    ib = np.searchsorted([4, 6, 8], rl.inning.values, side="right")      # 1-3, 4-5, 6-7, 8+
    X = np.column_stack([(ib == k).astype(float) for k in (1, 2, 3)])
    fits = fe_ols(rl[["rv", "K"]].values.astype(float), X, [_codes(rl.bid), _codes(rl.pid)], _codes(rl.pid))
    out["relief_inning_placebo"] = {y: {lab: {"b": float(b), "se": float(s)} for lab, b, s in zip(("inn4_5", "inn6_7", "inn8plus"), f[0], f[1])}
                                    for y, f in zip(("rv", "K"), fits)}
    out["relief_inning_placebo"]["n_pa"] = int(len(rl))
    # exposure: the starter's PAs by TTO per start
    sp = pa[pa.is_sp]
    per = sp.groupby(["game_id", "pit_team_id"]).tto.value_counts().unstack(fill_value=0)
    out["exposure_per_start"] = {str(k): {"mean": float(per[k].mean()), "sd": float(per[k].std()), "share_starts_with_any": float((per[k] > 0).mean())}
                                 for k in per.columns}
    out["bf_per_start"] = {"mean": float(sp.groupby(["game_id", "pit_team_id"]).size().mean()), "sd": float(sp.groupby(["game_id", "pit_team_id"]).size().std())}
    # (b) size on the dispersion scale
    m = reg[MAIN_SPEC]["rv"]
    beta = np.array([m["tto2"]["b"], m["tto3"]["b"], m["tto4"]["b"]]); V = np.array(reg[MAIN_SPEC]["_cov_rv"])
    tg = team_games()
    T = tto_exposure(pa, {2: beta[0], 3: beta[1], 4: beta[2]}).reindex(tg.index).fillna(0.0)
    pt = dphi_component(tg, T.values)
    pt["mean_T"] = float(T.mean()); pt["sd_T"] = float(T.std())
    pt["corr_T_starter_innings_r"] = float(np.corrcoef(T, tg.rS)[0, 1]); pt["corr_T_relief_innings_r"] = float(np.corrcoef(T, tg.rR)[0, 1])
    # per-start exposure counts by TTO, for the bootstrap (delta drawn from its sampling distribution each time)
    cnt = sp.groupby([sp.game_id, sp.bat_team_id]).tto.value_counts().unstack(fill_value=0).reindex(tg.index).fillna(0)
    N = np.column_stack([cnt.get(k, pd.Series(0, index=cnt.index)).values for k in (2, 3, 4)])
    games = tg.index.get_level_values(0).values
    ug, inv = np.unique(games, return_inverse=True)
    rows_by_game = pd.Series(np.arange(len(tg))).groupby(inv).apply(list).values
    bs = []
    for _ in range(BOOT):
        pick = np.concatenate([rows_by_game[i] for i in rng.integers(0, len(ug), len(ug))])
        bb = rng.multivariate_normal(beta, V)
        bs.append(dphi_component(tg.iloc[pick], N[pick] @ bb))
    # the covariance with the relief half-innings can only come through the game's shared part G (the hook does not
    # see them); G loads on the starter's half-innings in proportion to their expected runs, so the G share of the
    # starter-innings covariance is about cov_relief x (eS / eR). What is left is the hook's own response to runs.
    ratio = float(tg.eS.sum() / (tg.mu.sum() - tg.eS.sum()))
    pt["eS_over_eR"] = ratio
    pt["g_part_starter_innings_approx"] = pt["cov_part_relief_innings"] * ratio
    pt["dphi_without_game_shared_part"] = pt["dphi"] - pt["cov_part_relief_innings"] * (1 + ratio)
    out["dphi"] = pt
    for b in bs:
        b["dphi_without_game_shared_part"] = b["dphi"] - b["cov_part_relief_innings"] * (1 + ratio)
    out["dphi_se"] = {k: float(np.std([b[k] for b in bs], ddof=1)) for k in ("dphi", "var_part", "cov_part", "cov_part_starter_innings",
                                                                             "cov_part_relief_innings", "dphi_without_game_shared_part")}
    # the same exposure with the bracketing estimates of the penalty (pitcher FE, start FE)
    for spec in ("pitcher_fe", "start_fe"):
        mm = reg[spec]["rv"]
        Ts = tto_exposure(pa, {2: mm["tto2"]["b"], 3: mm["tto3"]["b"], 4: mm["tto4"]["b"]}).reindex(tg.index).fillna(0.0)
        out[f"dphi_{spec}"] = dphi_component(tg, Ts.values)
    out["n_team_games"] = int(len(tg))
    out["hook"] = hook_hazard(pa, rng)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 6. Mop-up pitching in blowouts (candidate 4)
# ----------------------------------------------------------------------------------------------------------------------

MARGIN_BINS = (("0-1", 0, 1), ("2-3", 2, 3), ("4", 4, 4), ("5-7", 5, 7), ("8+", 8, 99))
MIN_OTHER_BF = 10       # reporting cut: a reliever's quality needs this many batters faced outside the game


def pitcher_quality(pa: pd.DataFrame) -> tuple:
    """Season lines of every pitcher of a full-season team, and per (pitcher, game) lines, for leave-game-out rates:
    rv per PA allowed (linear weights) and a FIP-type rate per PA, (13 HR + 3 (BB + HBP) - 2 K) / PA."""
    full = full_season_teams()
    d = pa[pa.pit_team_id.isin(full)].copy()
    d["fipn"] = 13 * d.HR + 3 * (d.BB + d.HBP) - 2 * d.K
    pg = d.groupby(["pid", "game_id"]).agg(bf=("rv", "size"), rv=("rv", "sum"), fipn=("fipn", "sum"))
    season = pg.groupby("pid").sum()
    return season, pg, full


def batter_quality(pa: pd.DataFrame) -> tuple:
    bg = pa.groupby(["bid", "game_id"]).agg(n=("rv", "size"), rv=("rv", "sum"))
    return bg.groupby("bid").sum(), bg


def runs_while_in(pa: pd.DataFrame) -> pd.DataFrame:
    """Runs and outs while each pitcher is in: those of his plate appearances plus base-running events, each event
    assigned to the pitcher of the next plate appearance of the half-inning (else the previous one)."""
    rev = pd.read_csv(P / "runner_events_2025.csv.gz")
    key = ["game_id", "inning", "half"]
    a = pa[key + ["group_id", "pid", "pit_team_id", "outing"]].sort_values(key + ["group_id"])
    r = rev[key + ["group_id", "to_base"]].sort_values("group_id")
    m = pd.merge_asof(r, a.sort_values("group_id"), on="group_id", by=key, direction="forward")
    miss = m.pid.isna()
    if miss.any():
        m2 = pd.merge_asof(r[miss.values], a.sort_values("group_id"), on="group_id", by=key, direction="backward")
        m.loc[miss, ["pid", "pit_team_id", "outing"]] = m2[["pid", "pit_team_id", "outing"]].values
    m = m.dropna(subset=["pid"])
    m["runs"] = (m.to_base == 4).astype(int); m["outs"] = (m.to_base == 0).astype(int)
    ev = m.groupby(["game_id", "pit_team_id", "outing"]).agg(runs_ev=("runs", "sum"), outs_ev=("outs", "sum"))
    return ev


def relief_entries(pa: pd.DataFrame) -> pd.DataFrame:
    """One row per relief outing: entry inning and margin (pitching team's side), batters faced, run values allowed,
    the batters' expected run values (leave-game-out season rates), runs and outs while in."""
    rl = pa[~pa.is_sp]
    bseason, bgame = batter_quality(pa)
    lg = float(pa.rv.mean())
    bkey = pd.MultiIndex.from_arrays([rl.bid, rl.game_id])
    n_o = bseason.n.reindex(rl.bid).values - bgame.n.reindex(bkey).values
    s_o = bseason.rv.reindex(rl.bid).values - bgame.rv.reindex(bkey).values
    badj = np.where(n_o >= 20, s_o / np.maximum(n_o, 1) - lg, 0.0)
    rl = rl.assign(badj=badj)
    e = rl.groupby(["game_id", "pit_team_id", "outing"]).agg(
        pid=("pid", "first"), inning=("inning", "first"), margin=("margin", "first"), half=("half", "first"),
        bf=("rv", "size"), rv=("rv", "sum"), badj=("badj", "sum"), runs_pa=("runs_on_play", "sum"), outs_pa=("outs_on_play", "sum"),
        K=("K", "sum"), BB=("BB", "sum"), HBP=("HBP", "sum"), HR=("HR", "sum"))
    ev = runs_while_in(pa)
    e = e.join(ev).fillna({"runs_ev": 0, "outs_ev": 0})
    e["runs"] = e.runs_pa + e.runs_ev; e["outs"] = e.outs_pa + e.outs_ev
    e["absm"] = e.margin.abs()
    e["mbin"] = None
    for lab, lo, hi in MARGIN_BINS:
        e.loc[e.absm.between(lo, hi), "mbin"] = lab
    return e.reset_index()


def item6() -> dict:
    rng = np.random.default_rng(RNG_SEED + 6)
    pa = plate_appearances()
    season, pg, full = pitcher_quality(pa)
    e = relief_entries(pa)
    e = e[e.pit_team_id.isin(full)].copy()
    # leave-game-out quality of the entering pitcher
    k = pd.MultiIndex.from_arrays([e.pid, e.game_id])
    e["bf_other"] = season.bf.reindex(e.pid).values - pg.bf.reindex(k).values
    e["q_rv"] = (season.rv.reindex(e.pid).values - pg.rv.reindex(k).values) / e.bf_other.where(e.bf_other > 0)
    e["q_fip"] = (season.fipn.reindex(e.pid).values - pg.fipn.reindex(k).values) / e.bf_other.where(e.bf_other > 0)
    # the team's relief quality: BF-weighted mean of its relievers' season rates over its relief PAs (full season)
    rlp = pa[(~pa.is_sp) & pa.pit_team_id.isin(full)]
    tq = rlp.groupby("pit_team_id").agg(rv=("rv", "mean"))
    rlp_f = rlp.assign(fipn=13 * rlp.HR + 3 * (rlp.BB + rlp.HBP) - 2 * rlp.K)
    tq["fip"] = rlp_f.groupby("pit_team_id").fipn.mean()
    e["team_q_rv"] = e.pit_team_id.map(tq.rv); e["team_q_fip"] = e.pit_team_id.map(tq.fip)
    # position players pitching: the pitcher also has 20+ PAs as a batter for his team (two-way players included)
    bat_n = pa.groupby("bid").size()
    e["batter_too"] = e.pid.map(lambda p: bat_n.get(p, 0) >= 20)
    out = {"n_entries": int(len(e)), "n_teams": int(e.pit_team_id.nunique()), "min_other_bf": MIN_OTHER_BF}
    ok = e.bf_other >= MIN_OTHER_BF

    def by_bin(x: pd.DataFrame) -> dict:
        r = {}
        groups = [(lab, x.mbin == lab) for lab, *_ in MARGIN_BINS]
        groups += [("close_0_3", x.absm <= 3), ("late_close", (x.inning >= 7) & (x.absm <= 3)),
                   ("blowout_5plus", x.absm >= 5), ("blowout_8plus", x.absm >= 8), ("engine_blowout_7plus", x.absm >= 7),
                   ("leading_5plus", x.margin >= 5), ("trailing_5plus", x.margin <= -5)]
        for lab, msk in groups:
            y = x[msk]; w = y.bf
            q = y[y.bf_other >= MIN_OTHER_BF]; wq = q.bf
            r[lab] = {"entries": int(len(y)), "bf": int(w.sum()),
                      "share_bf_quality_known": float(wq.sum() / max(w.sum(), 1)),
                      "q_rv": float((wq * q.q_rv).sum() / wq.sum()) if len(q) else np.nan,
                      "q_rv_minus_team": float((wq * (q.q_rv - q.team_q_rv)).sum() / wq.sum()) if len(q) else np.nan,
                      "q_fip": float((wq * q.q_fip).sum() / wq.sum()) if len(q) else np.nan,
                      "q_fip_minus_team": float((wq * (q.q_fip - q.team_q_fip)).sum() / wq.sum()) if len(q) else np.nan,
                      # (b) observed run values in the outing against the prediction (pitcher's other games + batters)
                      "obs_rv_per_pa": float(q.rv.sum() / wq.sum()) if len(q) else np.nan,
                      "pred_rv_per_pa": float(((wq * q.q_rv).sum() + q.badj.sum()) / wq.sum()) if len(q) else np.nan,
                      "batter_adj_per_pa": float(q.badj.sum() / wq.sum()) if len(q) else np.nan,
                      "runs_per_9": float(27 * y.runs.sum() / max(y.outs.sum(), 1)),
                      "share_bf_position_players": float(y.loc[y.batter_too, "bf"].sum() / max(w.sum(), 1))}
            r[lab]["obs_minus_pred_per_pa"] = r[lab]["obs_rv_per_pa"] - r[lab]["pred_rv_per_pa"] if len(q) else np.nan
        for a_, b_ in (("blowout_5plus", "close_0_3"), ("blowout_8plus", "close_0_3"), ("blowout_5plus", "late_close"),
                       ("engine_blowout_7plus", "close_0_3")):
            for f in ("q_rv", "q_rv_minus_team", "q_fip", "q_fip_minus_team", "obs_minus_pred_per_pa", "obs_rv_per_pa", "runs_per_9"):
                r[f"gap_{a_}_vs_{b_}_{f}"] = r[a_][f] - r[b_][f]
        return r
    pt = by_bin(e)
    teams = e.pit_team_id.unique()
    ei = e.set_index("pit_team_id")
    bs = []
    for _ in range(BOOT):
        pick = rng.choice(teams, size=len(teams), replace=True)
        x = ei.loc[pick].reset_index()
        bs.append(by_bin(x))
    se = {}
    for kk, v in pt.items():
        if isinstance(v, dict):
            se[kk] = {f: float(np.nanstd([b[kk][f] for b in bs], ddof=1)) for f in v if isinstance(v[f], float)}
        else:
            se[kk] = float(np.nanstd([b[kk] for b in bs], ddof=1))
    out["by_margin"] = pt; out["by_margin_se"] = se
    out["share_entries_quality_known"] = float(ok.mean())
    # sensitivity: every reliever with any other batters faced
    e1 = e[e.bf_other >= 1]
    def gap(x, f):
        a = x[x.absm >= 5]; b = x[x.absm <= 3]
        return float((a.bf * a[f]).sum() / a.bf.sum() - (b.bf * b[f]).sum() / b.bf.sum())
    out["sensitivity_min_other_bf_1"] = {"gap_5plus_vs_close_q_rv_minus_team": gap(e1.assign(d=e1.q_rv - e1.team_q_rv), "d")}
    out["persistence"] = persistence(pa, e, season, pg, full, rng)
    out["dphi"] = mopup_dphi(pa, season, pg, full, rng)
    out["engine"] = engine_relief_shares()
    out["role_quality_real"] = role_quality(pa, season, full)
    return out


def pa_gaps(pa: pd.DataFrame, season: pd.DataFrame, pg: pd.DataFrame, full: set, min_other: int = MIN_OTHER_BF) -> pd.DataFrame:
    """Per relief PA of a full-season pitching team: the entering pitcher's leave-game-out rv per PA minus his team's
    relief mean (0 when he has fewer than `min_other` batters faced outside the game), the noise variance of that
    leave-game-out rate (sigma^2 / n_other), and the |margin| at his entry. Per PA of every batter: his leave-game-out
    rv per PA minus his team's batting mean (0 under 20 other PAs)."""
    d = pa.copy()
    rl = (~d.is_sp) & d.pit_team_id.isin(full)
    k = pd.MultiIndex.from_arrays([d.pid, d.game_id])
    n_o = season.bf.reindex(d.pid).values - pg.bf.reindex(k).values
    s_o = season.rv.reindex(d.pid).values - pg.rv.reindex(k).values
    team_rl = d[rl].groupby("pit_team_id").rv.mean()
    within = d.rv - d.groupby("pid").rv.transform("mean")
    sig2 = float((within ** 2).sum() / (len(d) - d.pid.nunique()))
    okp = rl & (np.nan_to_num(n_o) >= min_other)
    d["gap"] = np.where(okp, s_o / np.where(n_o > 0, n_o, 1) - d.pit_team_id.map(team_rl).values, 0.0)
    d["gap_noise"] = np.where(okp, sig2 / np.where(n_o > 0, n_o, 1), 0.0)
    d["gap_known"] = rl & okp
    d["relief_full"] = rl
    entry_m = d.groupby(["game_id", "pit_team_id", "outing"]).margin.transform("first")
    d["entry_absm"] = entry_m.abs()
    bseason, bgame = batter_quality(pa)
    kb = pd.MultiIndex.from_arrays([d.bid, d.game_id])
    nb = bseason.n.reindex(d.bid).values - bgame.n.reindex(kb).values
    sb = bseason.rv.reindex(d.bid).values - bgame.rv.reindex(kb).values
    team_b = d.groupby("bat_team_id").rv.mean()
    d["bgap"] = np.where(nb >= 20, sb / np.maximum(nb, 1) - d.bat_team_id.map(team_b).values, 0.0)
    d.attrs["sigma2_rv"] = sig2
    return d


def persistence(pa, e, season, pg, full, rng) -> dict:
    """Margins of 5+ after inning k (both halves of innings 1..k played, the game continued): further runs of the
    leading and the trailing side against (i) the fit's expected runs for the half-innings played (no state
    dependence: no mop-up gap), (ii) that plus the mop-up quality gap of the pitchers they faced (relief PAs of
    full-season pitching teams), and the lineup gap (the batters' own leave-game-out quality against their team's).
    Controls: margins of 0-2. Pooled over k = 3..7, SE by bootstrap over games."""
    x = ds.expected_runs(ds.half_innings())
    d = pa_gaps(pa, season, pg, full)
    hg = d.groupby(["game_id", "inning", "half"]).agg(gap=("gap", "sum"), known=("relief_full", "sum"), bgap=("bgap", "sum"))
    x = x.join(hg, on=["game_id", "inning", "half"]).fillna({"gap": 0.0, "known": 0, "bgap": 0.0})
    x["pit_full"] = x.pit_team_id.isin(full)
    rows = []
    for gid, g in x.groupby("game_id"):
        g = g.sort_values(["inning", "half"], key=lambda s: s if s.name == "inning" else s.map({"T": 0, "B": 1}))
        top = g[g.half == "T"].set_index("inning"); bot = g[g.half == "B"].set_index("inning")
        for k in range(3, 8):
            if not all(i in top.index and i in bot.index for i in range(1, k + 1)):
                break
            fa, fh = top[top.index > k], bot[bot.index > k]
            if len(fa) + len(fh) == 0:
                break
            ma = top.loc[:k, "runs"].sum(); mh = bot.loc[:k, "runs"].sum()
            m = mh - ma
            if abs(m) >= 5 or abs(m) <= 2:
                lead, trail = (fh, fa) if m > 0 else (fa, fh)
                for side, f in (("lead", lead), ("trail", trail)):
                    rows.append({"game_id": gid, "k": k, "absm": abs(m), "side": side, "runs": f.runs.sum(), "e": f.e.sum(),
                                 "gap": f.gap.sum(), "bgap": f.bgap.sum(), "pit_full": bool(f.pit_full.all()) if len(f) else True,
                                 "n_hi": len(f)})
    s = pd.DataFrame(rows)
    s["state"] = np.where(s.absm >= 8, "8+", np.where(s.absm >= 5, "5-7", "0-2"))

    def summ(s):
        r = {}
        for st in ("5-7", "8+", "5+", "0-2"):
            y = s[(s.absm >= 5) if st == "5+" else (s.state == st)]
            for side in ("lead", "trail"):
                z = y[y.side == side]; zf = z[z.pit_full]
                r[f"{st}|{side}"] = {"n": int(len(z)), "runs": float(z.runs.mean()), "expected": float(z.e.mean()),
                                     "excess": float((z.runs - z.e).mean()),
                                     "excess_full": float((zf.runs - zf.e).mean()), "mopup_gap_full": float(zf.gap.mean()),
                                     "lineup_gap": float(z.bgap.mean()), "n_full": int(len(zf)),
                                     "dispersion": float(((z.runs - z.e) ** 2 / z.e).mean())}
            zl, zt = y[y.side == "lead"], y[y.side == "trail"]
            r[f"{st}|margin_change"] = {"observed": float(zl.runs.mean() - zt.runs.mean()), "expected": float(zl.e.mean() - zt.e.mean())}
        return r
    pt = summ(s)
    games = s.game_id.unique(); si = s.set_index("game_id")
    bs = [summ(si.loc[rng.choice(games, size=len(games), replace=True)].reset_index()) for _ in range(BOOT // 2)]
    se = {kk: {f: float(np.nanstd([b[kk][f] for b in bs], ddof=1)) for f in v} for kk, v in pt.items()}
    return {"values": pt, "se": se, "n_states": int(len(s) // 2), "n_games": int(s.game_id.nunique()), "k_range": [3, 7]}


def mopup_dphi(pa, season, pg, full, rng) -> dict:
    """The mop-up component of a team-game's runs, t_g = sum over the relief PAs it had against a full-season pitching
    team of (the reliever's leave-game-out rv per PA - his team's relief mean): (i) entries at |margin| >= 5 only,
    (ii) >= 8, (iii) every relief entry (all leverage sorting, close games' best relievers included). Size by
    dphi_component, with the variance part corrected for the noise in the leave-game-out rates. Its effect on the
    15+ bin and the 10-run margin, to first order: the share of team-games (games) at the boundary times the mean
    component there."""
    d = pa_gaps(pa, season, pg, full)
    tg = team_games()
    tg = tg[tg.pit_team_id.isin(full)].copy()
    out = {"n_team_games": int(len(tg)), "sigma2_rv_per_pa": d.attrs["sigma2_rv"],
           "share_relief_bf_quality_known": float(d.loc[d.relief_full, "gap_known"].mean()),
           "share_relief_bf_quality_known_5plus": float(d.loc[d.relief_full & (d.entry_absm >= 5), "gap_known"].mean())}
    versions = {"blowout_5plus": d.entry_absm >= 5, "blowout_7plus_engine_bin": d.entry_absm >= 7, "blowout_8plus": d.entry_absm >= 8,
                "all_relief": d.entry_absm >= 0}
    games = tg.index.get_level_values(0).values
    ug, inv = np.unique(games, return_inverse=True)
    rows_by_game = pd.Series(np.arange(len(tg))).groupby(inv).apply(list).values
    # final margins of the batting team (for the 10-run boundary)
    gm = pd.read_csv(P / "games_2025.csv").set_index("game_id")
    bt = tg.index.get_level_values(1).values; gid = tg.index.get_level_values(0).values
    home = gm.home_team_id.reindex(gid).values == bt
    D = np.where(home, gm.home_score.reindex(gid).values - gm.away_score.reindex(gid).values,
                 gm.away_score.reindex(gid).values - gm.home_score.reindex(gid).values)
    p_early = 0.7805    # the benchmark's P(ended early | margin >= 10), WMT (round 1)

    def boundary(R, Dm, t):
        tc = t - t.mean()
        win15 = (R >= 13) & (R <= 16)
        dens15 = 0.5 * (np.mean(R == 14) + np.mean(R == 15))
        d15 = dens15 * tc[win15].mean() if win15.any() else np.nan
        # 10-run margin: a team-game's component moves its margin by +t (its runs) and the opponent's by -t_opp; to
        # first order the shift of |margin| at the boundary is E[t | won by ~10] - E[t | lost by ~10] (one-sided, so
        # games with one full-season team count)
        w = (np.abs(Dm) >= 8) & (np.abs(Dm) <= 11)
        dens10 = 0.5 * (np.mean(np.abs(Dm) == 9) + np.mean(np.abs(Dm) == 10))
        shift = tc[w & (Dm > 0)].mean() - tc[w & (Dm < 0)].mean()
        return {"p15": float(np.mean(R >= 15)), "dens15": float(dens15), "mean_t_near15": float(tc[win15].mean()), "d_bin15": float(d15),
                "p_margin10": float(np.mean(np.abs(Dm) >= 10)), "dens10": float(dens10), "shift_margin_near10": float(shift),
                "d_p_margin10": float(dens10 * shift), "d_run_rule": float(p_early * dens10 * shift)}
    for name, msk in versions.items():
        sel = d.relief_full & msk
        g = d[sel].groupby(["game_id", "bat_team_id"])
        t = g.gap.sum().reindex(tg.index).fillna(0.0).values
        # noise variance of t_g: sum over pitchers of (PAs in the game)^2 sigma^2 / n_other
        pp = d[sel].groupby(["game_id", "bat_team_id", "pid"]).agg(n=("gap", "size"), nv=("gap_noise", "first"))
        nv = (pp.n ** 2 * pp.nv).groupby(level=[0, 1]).sum().reindex(tg.index).fillna(0.0).values

        def calc(rows):
            x = tg.iloc[rows]; tt = t[rows]
            c = dphi_component(x, tt)
            c["noise_part"] = float(np.mean(nv[rows] / x.mu.values))
            c["dphi_noise_corrected"] = c["dphi"] - c["noise_part"]
            c["var_part_noise_corrected"] = c["var_part"] - c["noise_part"]
            c.update(boundary(x.R.values, D[rows], tt))
            return c
        pt = calc(np.arange(len(tg)))
        bs = []
        for _ in range(BOOT):
            rows = np.concatenate([rows_by_game[i] for i in rng.integers(0, len(ug), len(ug))])
            bs.append(calc(rows))
        pt["se"] = {kk: float(np.nanstd([b[kk] for b in bs], ddof=1)) for kk in pt if isinstance(pt[kk], float)}
        pt["mean_abs_t"] = float(np.abs(t).mean()); pt["share_team_games_nonzero"] = float((t != 0).mean())
        out[name] = pt
    return out


def engine_relief_shares() -> dict:
    """The engine's relief choice (engine/manager.py relief_pitcher): conditional logit over the unused staff,
    utility role x leverage + rest; leverage 'blowout' at |margin| >= LEVERAGE_BLOWOUT (7), 'late_close' from inning
    LEVERAGE_LATE_INNING (7) within LEVERAGE_CLOSE (3), else 'other'. Choice shares by role with every pitcher rested
    and unused, the starter (wk1) excluded; the engine's r8 role is relievers 8 to 13 (six alternatives)."""
    sys.path.insert(0, str(ROOT))
    from config.phase6 import INPUTS6, LEVERAGE_BLOWOUT, LEVERAGE_CLOSE, LEVERAGE_LATE_INNING
    from config.phase2 import N_RELIEVERS
    coef = json.loads(Path(INPUTS6).read_text())["usage6"]["relief"]["coef"]
    roles = ["wk2", "wk3", "mid1", "mid2"] + [f"r{k}" for k in range(1, 8)] + ["r8"] * (N_RELIEVERS - 7)
    out = {"leverage_blowout_min_margin": LEVERAGE_BLOWOUT, "late_inning": LEVERAGE_LATE_INNING, "close_max_margin": LEVERAGE_CLOSE}
    for lev in ("late_close", "other", "blowout"):
        u = np.array([coef.get(f"{r}|{lev}", 0.0) for r in roles])
        p = np.exp(u - u.max()); p /= p.sum()
        sh = {}
        for r, pp in zip(roles, p):
            sh[r] = sh.get(r, 0.0) + float(pp)
        out[lev] = sh
    return out


def role_quality(pa, season, full) -> dict:
    """Real season quality (rv per PA allowed, all his batters faced) by the engine's role definition
    (scripts/build_phase6_usage.py roles: relief batters faced rank among non-rotation pitchers), full-season teams;
    BF-weighted, with the per-role spread. In the engine roles r1..r8+ are ordered by the pitcher's K - BB - HR talent."""
    import build_phase6_usage as bu
    pa2 = pa[pa.pit_team_id.isin(full)].copy()
    meta = pd.read_csv(P / "games_meta_2025.csv")
    pa2 = pa2.merge(meta[["game_id", "local_date", "dbl_header_game_no"]], on="game_id", how="inner")
    pa2["ord"] = np.arange(len(pa2))
    a = bu.appearances(pa2)
    ro = bu.roles(a)
    ro["pid"] = ro.pit_team_id.astype(str) + "|" + ro.pkey
    ro = ro.join(season, on="pid")
    ro["q"] = ro.rv / ro.bf
    out = {}
    for r, g in ro.groupby("role"):
        out[r] = {"n_pitchers": int(len(g)), "q_rv_bf_weighted": float((g.rv.sum()) / g.bf.sum()), "bf_mean": float(g.bf.mean())}
    return out


# ----------------------------------------------------------------------------------------------------------------------
# running total, report
# ----------------------------------------------------------------------------------------------------------------------

def running_total(r1: dict, i5: dict, i6: dict) -> dict:
    c5 = r1["item3"]["components"]["min_starts_5"]
    rows = [("11", "Starter day-to-day form (5+ starts)", c5["dphi_form"], c5["dphi_form_se"]),
            ("12", "Errors clustering in half-innings", r1["item4"]["dphi_vs_binomial"], r1["item4"]["se"]["dphi"]),
            ("3", "Times through the order, with the real hook", i5["dphi"]["dphi"], i5["dphi_se"]["dphi"]),
            ("4", "Mop-up pitching, relief entries at a margin of 5+", i6["dphi"]["blowout_5plus"]["dphi_noise_corrected"],
             i6["dphi"]["blowout_5plus"]["se"]["dphi_noise_corrected"])]
    out, tot, v = [], 0.0, 0.0
    for c, lab, x, se in rows:
        tot += x; v += se ** 2
        out.append({"candidate": c, "label": lab, "dphi": x, "se": se, "share": x / MISS, "share_upper95": (x + 1.96 * se) / MISS,
                    "running_dphi": tot, "running_se": float(np.sqrt(v)), "running_share": tot / MISS,
                    "running_share_upper95": (tot + 1.96 * np.sqrt(v)) / MISS})
    ex = [r for r in out if r["candidate"] != "3"]
    t2 = sum(r["dphi"] for r in ex); s2 = float(np.sqrt(sum(r["se"] ** 2 for r in ex)))
    return {"rows": out, "missing": MISS, "total_dphi": tot, "total_se": float(np.sqrt(v)), "total_share": tot / MISS,
            "total_share_upper95": (tot + 1.96 * np.sqrt(v)) / MISS,
            "without_3": {"dphi": t2, "se": s2, "share": t2 / MISS, "share_upper95": (t2 + 1.96 * s2) / MISS}}


def f(x, n=3, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"


def markdown(i5: dict, i6: dict, rt: dict) -> str:
    L = []; w = L.append
    reg = i5["regressions"]; mreg = reg[MAIN_SPEC]
    d5, s5 = i5["dphi"], i5["dphi_se"]
    w(MARKER_START)
    w("## Round 2: times through the order (candidate 3) and mop-up pitching (candidate 4)")
    w("")
    w("2026-10-07. Owner: \"size times through the order and mop-up pitching in blowouts next, from real data only... Keep the running total of explained "
      "variance. Sizes only, no fixes.\" Script: `scripts/diag_tto_mopup.py` (run after `scripts/diag_sizes.py`); its numbers are under `item5_tto`, "
      "`item6_mopup` and `running_total` in `reports/diagnosis_sizes.json`. Data: the WMT play-by-play (2,232 games, 178,073 plate appearances), "
      "round 1's half-inning table and expectation. Nothing was simulated. SEs: cluster-robust by pitcher for regressions, bootstrap "
      f"({BOOT} reps) over games or teams otherwise, as stated.")
    w("")
    w("### Running total of explained variance (real-data sizes)")
    w("")
    w("Common scale (round 1): missing dispersion 2.6185 − 2.224 = 0.3945. A component t_g of a team-game's runs (centred) is worth "
      "Δφ = mean((r_g² − (r_g − t_g)²) / μ_g) = mean(t_g² / μ_g) + 2 mean((r_g − t_g) t_g / μ_g): its own variance plus twice its covariance with "
      "the rest of the team-game's runs. For a component independent of the rest this is round 1's mean(V / μ).")
    w("")
    w("| Candidate | Real size (Δφ) | SE | Share of .3945 | 95% upper bound of the share | Running total (share) | Running 95% upper bound |")
    w("|---|---|---|---|---|---|---|")
    for r in rt["rows"]:
        w(f"| {r['candidate']}. {r['label']} | {r['dphi']:+.3f} | {r['se']:.3f} | {100 * r['share']:+.0f}% | {100 * r['share_upper95']:.0f}% | "
          f"{r['running_dphi']:+.3f} ± {r['running_se']:.3f} ({100 * r['running_share']:+.0f}%) | {100 * r['running_share_upper95']:.0f}% |")
    wo = rt["without_3"]
    w(f"| **Total of 11, 12, 3, 4** | **{rt['total_dphi']:+.3f}** | {rt['total_se']:.3f} | **{100 * rt['total_share']:+.0f}%** | **{100 * rt['total_share_upper95']:.0f}%** | | |")
    w(f"| Total without 3 (sources that add variance only) | {wo['dphi']:+.3f} | {wo['se']:.3f} | {100 * wo['share']:+.0f}% | {100 * wo['share_upper95']:.0f}% | | |")
    w("")
    w("- These are real-data sizes of each mechanism, so they are upper bounds on what each could add to the sim. The sim side (how much of each the "
      "engine already produces) is not measured here; it comes later, on the new engine.")
    w(f"- Candidate 3 is negative: the times-through-the-order penalty is real and large per PA, but combined with the real hook it *reduces* the "
      f"variance of runs per team-game (the long starts that take the penalty are the low-scoring ones). Built into the engine as it stands, it "
      f"would widen the gap by about {abs(d5['dphi_without_game_shared_part']):.2f} rather than close it.")
    m4 = i6["dphi"]["blowout_5plus"]; m7 = i6["dphi"]["blowout_7plus_engine_bin"]
    w(f"- Candidate 4 is the first positive, detectable size: {m4['dphi_noise_corrected']:+.3f} ± {m4['se']['dphi_noise_corrected']:.3f} "
      f"({100 * m4['dphi_noise_corrected'] / MISS:.0f}% of the missing variance). The engine already has a blowout bin (|margin| ≥ 7) in its relief choice; "
      f"entries at 7+ alone are worth {m7['dphi_noise_corrected']:+.3f} ± {m7['se']['dphi_noise_corrected']:.3f}, so the part the engine's bins cannot "
      f"represent at all (entries at 5–6) is about {m4['dphi_noise_corrected'] - m7['dphi_noise_corrected']:+.3f}. The bin edge is not what is missing; "
      "whether the engine's blowout relievers are as much worse than its close-game relievers as the real ones are is the sim-side check.")
    w(f"- Four candidates together explain {100 * rt['total_share']:+.0f}% (95% upper bound {100 * rt['total_share_upper95']:.0f}%). Round 1's pointer stands: "
      "most of the missing variance is a game-level shared part, between half-innings, that no single-pitcher mechanism sized so far supplies.")
    w("")
    # ---------------- 5
    w("### 5. Times through the order (candidate 3)")
    w("")
    w("**(a) The penalty per PA.** Method: every plate appearance's outcome (run value by linear weights, K, BB, HBP, HR, on base) regressed on dummies for "
      "the batter's 2nd, 3rd and 4th+ time facing the game's starter (counted by batter in the outing), with fixed effects for the batter, the pitcher "
      "(season) and the batting team-game; relief PAs stay in the regression (TTO dummies zero) so the batter and team-game effects use every PA. "
      "The team-game effect absorbs the game's shared part G (round 1); comparing within the team-game, not within the start, avoids the bias of a "
      "start-level effect under the hook (a start is cut right after a bad stretch, so its observed later PAs are worse than its mean). SEs cluster-robust by pitcher.")
    lw = i5["linear_weights"]
    w(f"Linear weights (mean RE24 by result, complete half-innings of the sample): 1B {lw['1B']:.3f}, 2B {lw['2B']:.3f}, 3B {lw['3B']:.3f}, HR {lw['HR']:.3f}, "
      f"BB {lw['BB']:.3f}, HBP {lw['HBP']:.3f}, K {lw['K']:.3f}, GO {lw['GO']:.3f}, FO {lw['FO']:.3f}.")
    w("")
    w("| Outcome, change from the 1st time through | 2nd | 3rd | 4th+ |")
    w("|---|---|---|---|")
    labs = {"rv": "Runs per PA (linear weights)", "K": "K%", "BB": "BB%", "HBP": "HBP%", "HR": "HR%", "OB": "On-base rate"}
    for y in OUTCOMES:
        r = mreg[y]
        w(f"| {labs[y]} | {r['tto2']['b']:+.4f} ± {r['tto2']['se']:.4f} | {r['tto3']['b']:+.4f} ± {r['tto3']['se']:.4f} | {r['tto4']['b']:+.4f} ± {r['tto4']['se']:.4f} |")
    nb = mreg["n_by_tto"]
    w(f"| Starter PAs | {nb['2']:,} | {nb['3']:,} | {nb['4']:,} (1st: {nb['1']:,}) |")
    w("")
    w("The same penalty in runs per PA under other designs (bias direction in brackets):")
    w("")
    w("| Design | 2nd | 3rd | 4th+ |")
    w("|---|---|---|---|")
    desc = {"pitcher_fe": "Batter + pitcher FE, no game effect (starters go deeper on good days: biased down)",
            "team_game_fe": "**Batter + pitcher + team-game FE (main)**",
            "start_fe": "Batter + start FE (cut after bad stretches: biased up)",
            "start_fe_order": "Batter + start FE, TTO by lineup turn (batters 1–9, 10–18, ...)",
            "balanced_27": "Batter + start FE, only starts of 27+ batters, first 27 (survivors of the 3rd time through: biased down)",
            "team_game_fe_pitch_bins": "Main + the starter's pitch count before the PA (25/50/75/100 bins), TTO net of pitch count",
            "start_fe_pitch_bins": "Start FE + pitch-count bins"}
    for k in ("pitcher_fe", "team_game_fe", "start_fe", "start_fe_order", "balanced_27", "team_game_fe_pitch_bins"):
        r = reg[k]["rv"]
        c4 = f"{r['tto4']['b']:+.4f} ± {r['tto4']['se']:.4f}" if "tto4" in r else "n/a"
        w(f"| {desc[k]} | {r['tto2']['b']:+.4f} ± {r['tto2']['se']:.4f} | {r['tto3']['b']:+.4f} ± {r['tto3']['se']:.4f} | {c4} |")
    pb = reg["team_game_fe_pitch_bins"]["rv"]
    w("")
    w(f"- The penalty is large: {mreg['rv']['tto3']['b']:+.3f} runs per PA the third time through, with K% down {100 * abs(mreg['K']['tto3']['b']):.1f} points and "
      f"BB% up {100 * mreg['BB']['tto3']['b']:.1f}. Its bracketing designs give {reg['pitcher_fe']['rv']['tto3']['b']:+.3f} to {reg['start_fe']['rv']['tto3']['b']:+.3f}. "
      "The balanced design (only starts that lasted 27 batters) finds none, which is the hook's selection: those starts are the ones where the third time "
      "through went well.")
    w(f"- Times through and pitch count cannot be told apart within a game: with pitch-count bins added, the pitch-count terms carry it "
      f"({pb['pitch_bin1']['b']:+.3f}, {pb['pitch_bin2']['b']:+.3f}, {pb['pitch_bin3']['b']:+.3f}, {pb['pitch_bin4']['b']:+.3f} runs per PA at 26–50, 51–75, 76–100, 100+ pitches) and "
      f"the TTO terms turn negative ({pb['tto2']['b']:+.3f} ± {pb['tto2']['se']:.3f}, {pb['tto3']['b']:+.3f} ± {pb['tto3']['se']:.3f}). The engine has neither "
      "(its fatigue is between games: rest days), so the combined within-game decline is what it lacks; the size below uses the main design's TTO terms.")
    pl = i5["relief_inning_placebo"]
    w(f"- Not a game-time trend: relievers facing a batter for the first time (pitcher and batter FE, {pl['n_pa']:,} PAs) allow no more in later innings "
      f"(run value vs innings 1–3: 4–5 {pl['rv']['inn4_5']['b']:+.4f} ± {pl['rv']['inn4_5']['se']:.4f}, 6–7 {pl['rv']['inn6_7']['b']:+.4f} ± {pl['rv']['inn6_7']['se']:.4f}, "
      f"8+ {pl['rv']['inn8plus']['b']:+.4f} ± {pl['rv']['inn8plus']['se']:.4f}).")
    ex = i5["exposure_per_start"]
    w(f"- Exposure per start ({i5['n_starts']:,} starts, {i5['bf_per_start']['mean']:.1f} ± {i5['bf_per_start']['sd']:.1f} batters): 1st time {ex['1']['mean']:.2f} PAs, "
      f"2nd {ex['2']['mean']:.2f} (SD {ex['2']['sd']:.2f}), 3rd {ex['3']['mean']:.2f} (SD {ex['3']['sd']:.2f}; any in {100 * ex['3']['share_starts_with_any']:.0f}% of starts), "
      f"4th+ {ex['4']['mean']:.2f}.")
    w("")
    w("**(b) What it adds to runs per team-game, with the hook.** Method: each batting team-game gets its expected TTO runs T_g = Σ over its PAs against "
      "the opposing starter of the penalty for that PA's time through (main design). T_g varies with how deep the starter went, which the hook sets. "
      "Its size is Δφ above with t_g = T_g centred, against round 1's r_g and μ_g; SE by bootstrap over games with the penalty drawn from its sampling distribution.")
    w("")
    w("| | Value | SE |")
    w("|---|---|---|")
    w(f"| T_g, expected TTO runs per team-game: mean / SD | {d5['mean_T']:.3f} / {d5['sd_T']:.3f} | |")
    w(f"| Correlation of T_g with runs in the starter's half-innings (residual) | {d5['corr_T_starter_innings_r']:+.3f} | |")
    w(f"| Correlation of T_g with runs in the relief half-innings (residual) | {d5['corr_T_relief_innings_r']:+.3f} | |")
    w(f"| Variance part, mean(t² / μ) | {d5['var_part']:+.4f} | {s5['var_part']:.4f} |")
    w(f"| Covariance part, 2 mean((r − t) t / μ) | {d5['cov_part']:+.4f} | {s5['cov_part']:.4f} |")
    w(f"| of which with the starter's half-innings | {d5['cov_part_starter_innings']:+.4f} | {s5['cov_part_starter_innings']:.4f} |")
    w(f"| of which with the relief half-innings | {d5['cov_part_relief_innings']:+.4f} | {s5['cov_part_relief_innings']:.4f} |")
    w(f"| **Δφ, real (penalty with the real hook and the real game-to-game variation)** | **{d5['dphi']:+.3f}** | {s5['dphi']:.3f} |")
    w(f"| Δφ with the bracketing penalties (pitcher FE / start FE) | {i5['dphi_pitcher_fe']['dphi']:+.3f} / {i5['dphi_start_fe']['dphi']:+.3f} | |")
    w(f"| Δφ if the engine had it (game-shared part removed, below) | {d5['dphi_without_game_shared_part']:+.3f} | {s5['dphi_without_game_shared_part']:.3f} |")
    w("")
    w(f"- Share of the missing .3945: {100 * d5['dphi'] / MISS:+.0f}% (95% upper bound {100 * (d5['dphi'] + 1.96 * s5['dphi']) / MISS:+.0f}%). The penalty's own variance "
      f"is small ({d5['var_part']:.3f}); the covariance dominates and is negative, because a starter who lasts into the third time through is one who "
      "has allowed few runs. The penalty raises exactly the team-games that are low, which compresses the distribution.")
    w(f"- If the engine had it: the engine plays the same matchup rate every time through, with the 2025 pull hazard by pitch count and outing runs "
      "(item c), so its starters' exposure depends on their runs allowed as the real ones' does. What the engine would not reproduce is the part of the "
      "covariance that comes from the game's shared part G (bad days for the pitching side shorten starts and raise every inning's runs). That part shows "
      f"in the covariance with relief half-innings ({d5['cov_part_relief_innings']:+.4f}), which the hook cannot cause; scaled to the starter's half-innings by "
      f"their expected runs (eS / eR = {d5['eS_over_eR']:.2f}) it is {d5['g_part_starter_innings_approx']:+.4f}. Removing both leaves "
      f"{d5['dphi_without_game_shared_part']:+.3f} ± {s5['dphi_without_game_shared_part']:.3f}: an effect of this size in the engine would lower its dispersion, "
      "not raise it. This is an approximation from real data; the engine's own number needs the new engine's play-by-play.")
    w("")
    hk = i5["hook"]
    w("**(c) Does the hook respond to damage beyond pitch count?** Method: every batter a starter faced that was not the game's last for his team "
      f"({hk['n_decisions']:,} decisions, {hk['n_pulls']:,} pulls), pulled = a different pitcher faces the next batter, as the engine's table is built "
      "(`scripts/build_phase2_benchmarks.py`). Logit with a cell for every (outing pitches // 10, inning just ended, weekend), the engine's own "
      "conditioning, plus runs; SEs clustered by pitcher.")
    w("")
    w("Real hazard of a pull at the end of an inning, by runs allowed in the outing (± binomial SE):")
    w("")
    w("| Outing pitches | 0 runs | 1 | 2 | 3 | 4 | 5+ |")
    w("|---|---|---|---|---|---|---|")
    for band, t in hk["hazard_inning_end_by_pitches_runs"].items():
        w(f"| {band} | " + " | ".join(f"{t[str(k)]['h']:.3f} ± {t[str(k)]['se']:.3f} (n {t[str(k)]['n']})" if str(k) in t else "" for k in range(6)) + " |")
    w("")
    lr = hk["logit_runs_linear"]["runs_in_outing"]; le = hk["logit_extended"]
    w(f"- Yes. At equal pitch count, each run allowed in the outing raises the log-odds of a pull by {lr['b']:.3f} ± {lr['se']:.3f} (odds × {np.exp(lr['b']):.2f}); "
      "by dummies: " + ", ".join(f"{k.split('_')[1]} run{'s' if k != 'runs_1' else ''} {v['b']:+.2f} ± {v['se']:.2f}" for k, v in hk["logit_runs_dummies"].items()) + " (5 = 5+).")
    w("- Beyond what the engine conditions on (log-odds, same model with outing runs linear): " +
      "; ".join(f"{HOOK_LABELS.get(k, k)} {v['b']:+.3f} ± {v['se']:.3f}" for k, v in le.items()) + ". "
      "Runs in the current half-inning and runners on base move the real hook strongly (a starter is lifted mid-inning with traffic), and so do a "
      "deficit of 5+ and the third time through the order.")
    w(f"- The engine (`engine/manager.py` `pitching_change` / `_hazard`): {hk['engine']} So the engine's hook responds to runs allowed as the real one "
      "does on the margins it has, but a starter in the engine is not lifted for the current inning's damage or for runners on base, and his exposure to "
      "the third time through is not part of the decision.")
    w("")
    # ---------------- 6
    bm, bs_ = i6["by_margin"], i6["by_margin_se"]
    w("### 6. Mop-up pitching in blowouts (candidate 4)")
    w("")
    w(f"**(a) Who enters.** Method: every relief outing of the {i6['n_teams']} full-season teams (40+ parsed games; {i6['n_entries']:,} entries), margin at entry from the "
      "pitching team's side. Quality is the reliever's season line without that game (leave-game-out): run value allowed per PA (linear weights) and a "
      f"FIP-type rate per PA, (13 HR + 3 (BB + HBP) − 2 K) / PA; entries need {MIN_OTHER_BF}+ batters faced outside the game "
      f"({100 * i6['share_entries_quality_known']:.1f}% of entries). Means are weighted by batters faced in the outing; \"− team\" subtracts the team's relief mean. "
      "SEs by bootstrap over teams.")
    w("")
    w("| Margin at entry | Entries | BF | Quality known (BF) | rv/PA allowed, season | − team | FIP-type/PA | − team | Position players' BF share |")
    w("|---|---|---|---|---|---|---|---|---|")
    for k in [b[0] for b in MARGIN_BINS] + ["close_0_3", "late_close", "blowout_5plus", "engine_blowout_7plus", "blowout_8plus", "leading_5plus", "trailing_5plus"]:
        r, s = bm[k], bs_[k]
        lab = {"close_0_3": "Close, 0–3", "late_close": "Late and close (7th+, 0–3)", "blowout_5plus": "**5+**", "engine_blowout_7plus": "7+ (engine's blowout bin)",
               "blowout_8plus": "**8+**", "leading_5plus": "Leading by 5+", "trailing_5plus": "Trailing by 5+"}.get(k, k)
        w(f"| {lab} | {r['entries']:,} | {r['bf']:,} | {100 * r['share_bf_quality_known']:.0f}% | {r['q_rv']:+.4f} ± {s['q_rv']:.4f} | {r['q_rv_minus_team']:+.4f} ± {s['q_rv_minus_team']:.4f} | "
          f"{r['q_fip']:.3f} ± {s['q_fip']:.3f} | {r['q_fip_minus_team']:+.3f} ± {s['q_fip_minus_team']:.3f} | {100 * r['share_bf_position_players']:.1f}% |")
    w("")
    g = lambda a, b, fld: (bm[f"gap_{a}_vs_{b}_{fld}"], bs_[f"gap_{a}_vs_{b}_{fld}"])
    w("Leverage gap (blowout minus close, within team):")
    w("")
    w("| | rv/PA − team | FIP-type/PA − team |")
    w("|---|---|---|")
    for a, b, lab in (("blowout_5plus", "close_0_3", "5+ vs close (0–3)"), ("engine_blowout_7plus", "close_0_3", "7+ vs close"),
                      ("blowout_8plus", "close_0_3", "8+ vs close"), ("blowout_5plus", "late_close", "5+ vs late and close")):
        x1, e1 = g(a, b, "q_rv_minus_team"); x2, e2 = g(a, b, "q_fip_minus_team")
        w(f"| {lab} | **{x1:+.4f}** ± {e1:.4f} | {x2:+.3f} ± {e2:.3f} |")
    w("")
    w(f"- Blowout relievers are clearly worse: {g('blowout_5plus', 'close_0_3', 'q_rv_minus_team')[0]:+.3f} runs per PA at 5+ and "
      f"{g('blowout_8plus', 'close_0_3', 'q_rv_minus_team')[0]:+.3f} at 8+ against the relievers of close games of the same team; with every reliever kept "
      f"(1+ other batters faced) the 5+ gap is {i6['sensitivity_min_other_bf_1']['gap_5plus_vs_close_q_rv_minus_team']:+.4f}. Trailing teams go deeper into the "
      f"staff than leading ones ({bm['trailing_5plus']['q_fip_minus_team']:+.3f} against {bm['leading_5plus']['q_fip_minus_team']:+.3f} FIP-type per PA). Position players "
      "pitching are rare (about 1% of blowout batters faced; a pitcher who also has 20+ PAs, two-way players included).")
    rq = i6["role_quality_real"]
    w("- By the engine's role definition (relief batters faced rank, `scripts/build_phase6_usage.py`), real season run value per PA: " +
      ", ".join(f"{k} {rq[k]['q_rv_bf_weighted']:+.3f}" for k in [f"r{j}" for j in range(1, 9)] if k in rq) +
      " (r8 = 8th and deeper, " + f"{rq['r8']['n_pitchers']} pitchers). The engine orders r1–r8+ by K − BB − HR talent instead, so its gradient by role is at least as steep.")
    eng = i6["engine"]
    deep = lambda lev: sum(v for k_, v in eng[lev].items() if k_ in ("r6", "r7", "r8"))
    w(f"- The engine (`engine/manager.py` `relief_pitcher`) does use the score: leverage is \"blowout\" at |margin| ≥ {eng['leverage_blowout_min_margin']} "
      f"(`config/phase6.LEVERAGE_BLOWOUT`, a GUESS bin edge), \"late_close\" from the {eng['late_inning']}th inning within {eng['close_max_margin']}, else \"other\"; "
      "the choice is the 2025 conditional logit of role × leverage plus rest. With everyone rested, the share of entries going to roles r6–r8+ is "
      f"{100 * deep('blowout'):.0f}% in a blowout, {100 * deep('other'):.0f}% in \"other\" and {100 * deep('late_close'):.0f}% late and close; r1 gets "
      f"{100 * eng['blowout']['r1']:.0f}%, {100 * eng['other']['r1']:.0f}% and {100 * eng['late_close']['r1']:.0f}%. Margins of 5–6 fall in \"other\", "
      "so the engine treats them like a 4-run game.")
    w("")
    w("**(b) How they pitch against their quality.** Prediction for each outing: the reliever's leave-game-out rv per PA plus the batters' "
      "leave-game-out rv per PA above league (20+ other PAs, else 0). Observed minus predicted, per PA:")
    w("")
    w("| Margin at entry | Observed rv/PA | Predicted | Batters' adjustment | Observed − predicted | Runs per 9 IP while in |")
    w("|---|---|---|---|---|---|")
    for k, lab in (("close_0_3", "Close, 0–3"), ("late_close", "Late and close"), ("blowout_5plus", "5+"), ("blowout_8plus", "8+"),
                   ("leading_5plus", "Leading by 5+"), ("trailing_5plus", "Trailing by 5+")):
        r, s = bm[k], bs_[k]
        w(f"| {lab} | {r['obs_rv_per_pa']:+.4f} ± {s['obs_rv_per_pa']:.4f} | {r['pred_rv_per_pa']:+.4f} | {r['batter_adj_per_pa']:+.4f} | "
          f"{r['obs_minus_pred_per_pa']:+.4f} ± {s['obs_minus_pred_per_pa']:.4f} | {r['runs_per_9']:.2f} ± {s['runs_per_9']:.2f} |")
    x1, e1 = g("blowout_5plus", "close_0_3", "obs_minus_pred_per_pa"); x2, e2 = g("blowout_8plus", "close_0_3", "obs_minus_pred_per_pa")
    x3, e3 = g("blowout_5plus", "close_0_3", "runs_per_9")
    w("")
    w(f"- Blowout relievers allow more ({x3:+.2f} ± {e3:.2f} runs per 9 at 5+ against close games), as their quality predicts, but not more than it "
      f"predicts: observed − predicted is {x1:+.4f} ± {e1:.4f} per PA relative to close games at 5+ and {x2:+.4f} ± {e2:.4f} at 8+. There is no extra "
      "\"garbage time\" decline beyond who pitches. The split by side is the game's shared part again: relievers of a team leading by 5+ do much better than "
      f"predicted ({bm['leading_5plus']['obs_minus_pred_per_pa']:+.3f}), those of a team trailing by 5+ worse ({bm['trailing_5plus']['obs_minus_pred_per_pa']:+.3f}), "
      "the day's offense persisting into the late innings.")
    w("")
    ps = i6["persistence"]; pv, pse = ps["values"], ps["se"]
    w(f"**(c) Do blowouts grow?** Method: games after inning k = 3..7 (both halves of 1..k played, the game continued; {ps['n_states']:,} game-states in "
      f"{ps['n_games']:,} games, pooled, SE by bootstrap over games). Further runs of each side against the fit's expected runs for the half-innings played "
      "(a model with no state dependence, so no mop-up gap), and the mop-up gap the side's batters met: Σ over its later relief PAs of (the reliever's "
      "leave-game-out rv/PA − his team's relief mean), counted where the pitching team is full-season (\"full\" columns). Lineup gap: the same for the "
      "side's own batters against its team's batting mean.")
    w("")
    w("| State after inning k | Side | n | Further runs | Expected (no gap) | Excess | Excess, full | Mop-up gap, full | Lineup gap | Dispersion of further runs |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for st in ("5+", "5-7", "8+", "0-2"):
        for side in ("lead", "trail"):
            r, s = pv[f"{st}|{side}"], pse[f"{st}|{side}"]
            w(f"| margin {st} | {side} | {r['n']:,} | {r['runs']:.3f} | {r['expected']:.3f} | {r['excess']:+.3f} ± {s['excess']:.3f} | {r['excess_full']:+.3f} ± {s['excess_full']:.3f} | "
              f"{r['mopup_gap_full']:+.3f} ± {s['mopup_gap_full']:.3f} | {r['lineup_gap']:+.3f} | {r['dispersion']:.2f} |")
    w("")
    mc = pv["5+|margin_change"]; mc0 = pv["0-2|margin_change"]
    w(f"- A 5+ margin grows: the leader outscores the trailer by {mc['observed']:.2f} more runs (expected {mc['expected']:.2f} from team strengths; "
      f"margins of 0–2: {mc0['observed']:.2f} against {mc0['expected']:.2f}). The leader's excess ({pv['5+|lead']['excess_full']:+.2f} where its opponent's quality is known) "
      f"is mostly the mop-up gap it meets ({pv['5+|lead']['mopup_gap_full']:+.2f}). The trailing side meets a smaller gap ({pv['5+|trail']['mopup_gap_full']:+.2f}) "
      f"and scores below even the no-gap expectation ({pv['5+|trail']['excess_full']:+.2f}): its bad day persists. Lineup changes push the other way "
      f"(the leader's lineup gap {pv['5+|lead']['lineup_gap']:+.2f}).")
    w("")
    w("**Size on the common scale.** Method: t_g = Σ over the batting team-game's relief PAs against a full-season pitching team of (the reliever's "
      "leave-game-out rv/PA − his team's relief mean), for entries at the given margin; Δφ as above, the variance part corrected for the sampling noise "
      "of the leave-game-out rates (Σ PAs² σ² / n_other, σ² the within-pitcher per-PA variance of rv, "
      f"{i6['dphi']['sigma2_rv_per_pa']:.3f}); {i6['dphi']['n_team_games']:,} team-games, SE by bootstrap over games.")
    w("")
    w("| Entries counted | Variance part (noise-corrected) | Covariance part | of which relief half-innings | **Δφ** | Share of .3945 | Adds to the 15+ bin | Adds to P(margin ≥ 10) | Adds to the run-rule rate |")
    w("|---|---|---|---|---|---|---|---|---|")
    for k, lab in (("blowout_5plus", "Margin 5+ at entry"), ("blowout_7plus_engine_bin", "7+ (the engine's blowout bin)"),
                   ("blowout_8plus", "8+"), ("all_relief", "Every relief entry (all leverage sorting)")):
        r = i6["dphi"][k]; s = r["se"]
        w(f"| {lab} | {r['var_part_noise_corrected']:+.4f} ± {s['var_part_noise_corrected']:.4f} | {r['cov_part']:+.4f} ± {s['cov_part']:.4f} | "
          f"{r['cov_part_relief_innings']:+.4f} | **{r['dphi_noise_corrected']:+.3f}** ± {s['dphi_noise_corrected']:.3f} | {100 * r['dphi_noise_corrected'] / MISS:+.0f}% | "
          f"{r['d_bin15']:+.4f} ± {s['d_bin15']:.4f} | {r['d_p_margin10']:+.4f} ± {s['d_p_margin10']:.4f} | {r['d_run_rule']:+.4f} ± {s['d_run_rule']:.4f} |")
    r = i6["dphi"]["blowout_5plus"]
    w("")
    w(f"- The mop-up component adds variance through its covariance with the rest of the game: it lands on team-games already ahead (corr with the rest "
      f"{r['corr_t_rest']:+.2f}). Entries at 5+ are worth {r['dphi_noise_corrected']:+.3f} ± {r['se']['dphi_noise_corrected']:.3f}, {100 * r['dphi_noise_corrected'] / MISS:.0f}% "
      f"of the missing variance (95% upper bound {100 * (r['dphi_noise_corrected'] + 1.96 * r['se']['dphi_noise_corrected']) / MISS:.0f}%). Counting every relief entry "
      "adds the close-game use of the best relievers, which offsets it.")
    w(f"- 15+ bin and run rule, to first order (the share of team-games, or games, at the boundary times the mean component there; the columns show "
      f"what the component adds, i.e. what a sim without it would lack). In this sample P(15+) is {r['p15']:.4f} (team-games against "
      f"full-season, mostly P4, staffs) and P(margin ≥ 10) {r['p_margin10']:.4f}. Entries at 5+: 15+ bin {r['d_bin15']:+.4f} ± {r['se']['d_bin15']:.4f}, "
      f"{100 * r['d_bin15'] / r['p15']:.0f}% of the sample's bin, which applied to the D1 bin (.065) is {r['d_bin15'] / r['p15'] * REAL['bin15']:+.4f}, "
      f"{100 * r['d_bin15'] / r['p15'] * REAL['bin15'] / (REAL['bin15'] - SIM['bin15']):.0f}% of the gap to the sim (.0650 − .0533); "
      f"run rule {r['d_run_rule']:+.4f} ± {r['se']['d_run_rule']:.4f} (P(margin ≥ 10) {r['d_p_margin10']:+.4f} × P(ended early | 10+) .7805), "
      f"{100 * r['d_run_rule'] / (REAL['run_rule_product'] - SIM['run_rule']):.0f}% of the gap .1509 − .1201 "
      f"({100 * r['d_run_rule'] / (REAL['run_rule_direct'] - SIM['run_rule']):.0f}% of .1440 − .1201). These are upper bounds: the engine's blowout bin already "
      f"supplies part (7+ entries: 15+ {i6['dphi']['blowout_7plus_engine_bin']['d_bin15']:+.4f}, run rule {i6['dphi']['blowout_7plus_engine_bin']['d_run_rule']:+.4f}).")
    w("")
    w("### Not measured in round 2")
    w("")
    w("- Every sim-side counterpart: the engine's own exposure-runs covariance under its hook, its blowout relievers' quality gap and the persistence of its "
      "margins. They need play-by-play from the new engine.")
    w("- Times through the order apart from pitch count: within a game the two are almost collinear; only their sum is sized.")
    w("- Relievers' quality on teams without a full season in the play-by-play (their opponents' relievers): the mop-up component is counted only "
      "against the 50 full-season staffs, so its sizes are a P4-heavy sample's.")
    w("- Heterogeneity of the TTO penalty across pitchers (a per-pitcher penalty would add variance of its own); not estimated.")
    w(MARKER_END)
    return "\n".join(L) + "\n"


def main() -> None:
    import os
    os.chdir(ROOT)
    r1 = json.loads(OUT_JSON.read_text())
    print("item 5 ...", flush=True)
    i5 = ds.plain(item5())
    print("item 6 ...", flush=True)
    i6 = ds.plain(item6())
    rt = ds.plain(running_total(r1, i5, i6))
    r1["item5_tto"] = i5; r1["item6_mopup"] = i6; r1["running_total"] = rt
    r1["_meta_round2"] = {"script": "scripts/diag_tto_mopup.py", "date": "2026-10-07", "bootstrap_reps": BOOT,
                          "note": "Real-data sizes only (round 2: candidates 3 and 4). No season simulated."}
    OUT_JSON.write_text(json.dumps(ds.plain(r1), indent=1) + "\n")
    md = OUT_MD.read_text()
    if MARKER_START in md:
        md = md[:md.index(MARKER_START)].rstrip("\n") + "\n"
    anchor = "different from zero."
    if POINTER not in md and anchor in md:
        i = md.index(anchor) + len(anchor)
        md = md[:i] + "\n\n" + POINTER + md[i:]
    OUT_MD.write_text(md.rstrip("\n") + "\n\n" + markdown(i5, i6, rt))
    print("wrote", OUT_JSON, OUT_MD)


if __name__ == "__main__":
    main()
