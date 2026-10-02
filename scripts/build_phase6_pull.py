"""Phase 6 pull-hazard multipliers by tier and season week, from the 2025 play-by-play.

The engine's pull hazard (engine/manager.py) is the Phase 2 baseline h(role, weekend, outing
pitches, outing runs, inning just ended), times the pitcher's own leash (Stamina):
h' = 1 - (1 - h)^theta. Phase 2 tabulated h over all teams pooled, a P4-heavy sample, so low-tier
managers' longer leash on midweek starters was averaged away (the deferred midweek p10 row).
Here every pull decision of the sample (after each batter faced: replaced before the next batter
or not) gets its baseline h from the engine's own tables, and a multiplier is fitted by maximum
likelihood:  log theta = a[tier] + b[season week bin]  per role (weekend starter, midweek starter,
reliever), with the season-week term for starters only (build-up early in the season and wear late).
The multipliers are centred so that their batters-faced-weighted mean log theta is 0 within each
role: the pooled leash, and with it every Phase 2 and Phase 5 row tuned on it, is unchanged on
average; only its split by tier and week is new.
Writes the "pull6" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/build_phase6_pull.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import phase2  # noqa: E402
from config.phase2 import SPOT_STARTER_RANK, TIERS  # noqa: E402
from config.phase6 import INPUTS6, SEASON_START, WEEK_BINS  # noqa: E402
from engine.manager import Manager  # noqa: E402
from lib.players import load_pa  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"
# the engine's split (Phase 6 calendar): series games Thu-Sun use the weekend tables, Mon-Wed the
# midweek ones. The Phase 2 baseline tables pool Thursday with midweek; the multipliers fitted here
# on the engine's split absorb the difference (Thursday games are series openers by weekend aces).
WEEKEND = {3, 4, 5, 6}


def decisions() -> pd.DataFrame:
    pa = load_pa()
    gm = pd.read_csv(P / "games_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.ncaa_team_id, teams.tier))
    gm["d"] = pd.to_datetime(gm.game_date)
    pa = pa.merge(gm[["game_id", "d"]], on="game_id").sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["wd"] = pa.d.dt.dayofweek
    pa["weekend"] = pa.wd.isin(WEEKEND).astype(int)
    pa["week"] = ((pa.d - pd.Timestamp(SEASON_START)).dt.days // 7).clip(lower=0)
    first = pa.groupby(["game_id", "pit_team_id"]).pkey.first().rename("starter").reset_index()
    pa = pa.merge(first, on=["game_id", "pit_team_id"])
    pa["is_sp"] = (pa.pkey == pa.starter).astype(int)
    pa["outing"] = (pa.pkey != pa.groupby(["game_id", "pit_team_id"]).pkey.shift()).groupby([pa.game_id, pa.pit_team_id]).cumsum()
    pa["out_pitches"] = pa.groupby(["game_id", "pit_team_id", "outing"]).pitches.cumsum()
    pa["out_runs"] = pa.groupby(["game_id", "pit_team_id", "outing"]).runs_on_play.cumsum()
    nxt = pa.groupby(["game_id", "pit_team_id"]).pkey.shift(-1)
    pa["pulled"] = (nxt.notna() & (nxt != pa.pkey)).astype(int)
    pa["last_of_game"] = nxt.isna()
    pa["inning_end"] = ((pa.outs + pa.outs_on_play) >= 3).astype(int)
    pa["tier"] = pa.pit_team_id.map(tier)
    h = pa[~pa.last_of_game & pa.out_pitches.notna() & pa.tier.notna()].copy()
    # weekend rotation rank (most series starts on the team), as the Phase 2 rank tables
    st = h[(h.is_sp == 1) & (h.weekend == 1)].drop_duplicates(["game_id", "pit_team_id"])
    cnt = st.groupby(["pit_team_id", "pkey"]).size().rename("n").reset_index()
    cnt["rank"] = cnt.groupby("pit_team_id").n.rank(ascending=False, method="first").astype(int).clip(upper=SPOT_STARTER_RANK)
    h = h.merge(cnt[["pit_team_id", "pkey", "rank"]], on=["pit_team_id", "pkey"], how="left")
    mgr = Manager(phase2.load())
    base = []
    for r in h.itertuples():
        rank = int(r.rank) if (r.is_sp and r.weekend and not np.isnan(r.rank)) else None
        x = mgr._hazard(bool(r.is_sp), int(r.weekend), int(r.out_pitches), int(r.out_runs), int(r.inning_end), rank)
        base.append(np.nan if x is None else x)
    h["h"] = base
    h["role"] = np.where(h.is_sp == 0, "rp", np.where(h.weekend == 1, "sp_weekend", "sp_midweek"))
    h["wbin"] = np.searchsorted(np.array(WEEK_BINS), h.week.values, side="right") - 1
    return h[h.h.notna() & (h.h > 0) & (h.h < 1)]


def fit_role(d: pd.DataFrame, with_week: bool) -> dict:
    """MLE of log theta = a[tier] + b[week bin] (p4 and the middle week bin the reference before
    centring) by Newton on the exact Bernoulli likelihood: P(pulled) = 1 - (1 - h)^theta."""
    tiers = [t for t in TIERS if (d.tier == t).any()]
    wbins = sorted(d.wbin.unique()) if with_week else []
    ref_w = wbins[len(wbins) // 2] if wbins else None
    cols = [f"tier|{t}" for t in tiers] + [f"week|{w}" for w in wbins if w != ref_w]
    X = np.zeros((len(d), len(cols)))
    for i, t in enumerate(tiers):
        X[:, i] = (d.tier == t).values
    for j, w in enumerate([w for w in wbins if w != ref_w]):
        X[:, len(tiers) + j] = (d.wbin == w).values
    L = np.log1p(-d.h.values)          # log(1 - h) < 0
    y = d.pulled.values
    b = np.zeros(len(cols))
    for _ in range(100):
        th = np.exp(X @ b)
        s = np.exp(th * L)             # survival (1 - h)^theta
        # d/d eta of the log-likelihood, eta = log theta: pulled: -s th L / (1 - s); stayed: th L
        g1 = np.where(y == 1, -s * th * L / np.maximum(1 - s, 1e-12), th * L)
        # second derivative in eta: stayed rows f = theta L, f'' = theta L; pulled rows f = log(1 - e^a),
        # a = theta L: f'' = -[e^a a (1 + a)(1 - e^a) + e^2a a^2] / (1 - e^a)^2
        a_ = th * L
        ea = s
        h2 = np.where(y == 1, -(ea * a_ * (1 + a_) * (1 - ea) + ea ** 2 * a_ ** 2) / np.maximum(1 - ea, 1e-12) ** 2, a_)
        g = X.T @ g1
        H = X.T @ (h2[:, None] * X) - 1e-6 * np.eye(len(cols))
        step = np.linalg.solve(H, -g)
        b = b + np.clip(step, -1, 1)
        if np.abs(step).max() < 1e-8:
            break
    cov = np.linalg.inv(-H)
    # centre: the BF-weighted (decision-weighted) mean of log theta is 0
    eta = X @ b
    c = float(eta.mean())
    coef = dict(zip(cols, b))
    out = {"n_decisions": int(len(d)), "n_pulls": int(y.sum())}
    out["log_theta_tier"] = {t: round(coef[f"tier|{t}"] - c, 4) for t in tiers}
    out["se_tier"] = {t: round(float(np.sqrt(cov[i, i])), 4) for i, t in enumerate(tiers)}
    if with_week:
        wk = {int(w): (coef.get(f"week|{w}", 0.0)) for w in wbins}
        out["log_theta_week"] = {str(w): round(v, 4) for w, v in wk.items()}
        out["se_week"] = {str(w): (round(float(np.sqrt(cov[cols.index(f'week|{w}'), cols.index(f'week|{w}')])), 4) if f"week|{w}" in cols else 0.0) for w in wbins}
        out["week_bins"] = list(WEEK_BINS)
    return out


def main() -> None:
    d = decisions()
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "season_start": SEASON_START}
    for role, wk in (("sp_weekend", True), ("sp_midweek", True), ("rp", False)):
        out[role] = fit_role(d[d.role == role], wk)
        print(role, json.dumps(out[role]))
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["pull6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
