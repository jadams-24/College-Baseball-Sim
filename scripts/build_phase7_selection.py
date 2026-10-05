"""NCAA tournament selection and seeding models, fitted on every season the scoreboard feed covers
with complete results (2017-2019, 2021-2025; 2015-2016 leave results missing, 2020 had no tournament).

RPI: engine.rpi (the NCAA's formula, checked against the published 2026 ranks; scripts/check_rpi_2026.py)
on the feed's Division I games before selection Monday. The feed has no neutral-site flag, so every game is
weighted as home/road; 2025's conference tournament games are mostly placeholders without results.

Models (logistic, a separate intercept per season, Newton-Raphson):
  at_large       among Division I teams without an automatic bid: P(at-large) from the RPI z-score within the
                 season (and, compared by likelihood ratio, a P4 indicator)
  national_seed  among the 64-team field: P(national seed) from the same predictors (2018 on: 16 seeds)
With a per-season intercept the engine's draw is the same model: the k teams with the largest score +
standard logistic noise (k = the season's open slots).

Also the field benchmarks that the models must reproduce in the sim: the worst RPI rank given an at-large
bid and the best RPI rank left out, per season.
Writes the "selection7" block of data/ncaa_2025/derived/phase7_inputs.json and the rank rows into
data/ncaa_2025/derived/phase7_benchmarks.json.

    python3 scripts/build_phase7_selection.py
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
from build_phase7_benchmarks import SELECTION  # noqa: E402
from config.phase7 import INPUTS7  # noqa: E402
from engine.rpi import rpi  # noqa: E402
from lib.brackets import brackets, feed_counts, feed_games, feed_name, name_map, tier_of, tiers  # noqa: E402

FIT_SEASONS = ("2017", "2018", "2019", "2021", "2022", "2023", "2024", "2025")
MIN_D1_GAMES = 15        # a feed name with fewer decided games before selection is not a Division I team's (non-D1 opponents)
BENCH = ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json"


def season_table(y: str, b, m, tier) -> pd.DataFrame:
    d = feed_games(y); fc = feed_counts(d)
    f = d[(d.state == "final") & d.home_score.notna() & (d.home_score != d.away_score) & (d.date < SELECTION[y])].drop_duplicates("url")
    cnt = pd.concat([f.home, f.away]).value_counts()
    d1 = set(cnt[cnt >= MIN_D1_GAMES].index)
    g = f[f.home.isin(d1) & f.away.isin(d1)]
    r = rpi(zip(g.home, g.away, g.home_score > g.away_score, [False] * len(g)))
    t = pd.DataFrame({"team": list(r), "rpi": [r[k]["rpi"] for k in r]})
    t["rank"] = t.rpi.rank(ascending=False, method="min").astype(int)
    t["z"] = (t.rpi - t.rpi.mean()) / t.rpi.std()
    s = b[y]
    bid = {feed_name(x["team"], fc, m): x for x in s["teams"]}
    t["bid"] = t.team.map(lambda n: bid[n]["bid"] if n in bid else None)
    t["auto"] = t.bid == "auto"
    t["field"] = t.team.isin(bid)
    t["at_large"] = t.field & ~t.auto
    t["seed"] = t.team.map(lambda n: bid[n]["national_seed"] if n in bid else None)
    back = {feed_name(x["team"], fc, m): x["team"] for x in s["teams"]}
    t["p4"] = t.team.map(lambda n: tier_of(back.get(n, n), tier, m) == "p4" if n in back else tier.get(n) == "p4")
    t["season"] = y
    return t


def logit_fit(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Logistic regression with a separate intercept per group. Returns (coefficients of X, their SEs, log-likelihood)."""
    G = sorted(set(groups))
    D = np.column_stack([(groups == g).astype(float) for g in G] + [X])
    beta = np.zeros(D.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-(D @ beta)))
        W = p * (1 - p)
        H = D.T @ (D * W[:, None]) + 1e-9 * np.eye(D.shape[1])
        step = np.linalg.solve(H, D.T @ (y - p))
        beta += step
        if np.max(np.abs(step)) < 1e-10:
            break
    p = np.clip(1 / (1 + np.exp(-(D @ beta))), 1e-12, 1 - 1e-12)
    cov = np.linalg.inv(D.T @ (D * (p * (1 - p))[:, None]))
    k = len(G)
    return beta[k:], np.sqrt(np.diag(cov))[k:], float((y * np.log(p) + (1 - y) * np.log(1 - p)).sum())


def main() -> None:
    b, m, tier = brackets(), name_map(), tiers()
    T = pd.concat([season_table(y, b, m, tier) for y in FIT_SEASONS], ignore_index=True)
    out = {"built": dt.date.today().isoformat(), "seasons": list(FIT_SEASONS), "_note": __doc__}
    checks = {}
    for name, rows, ycol in (("at_large", ~T.auto, "at_large"), ("national_seed", T.field & (T.season != "2017"), "seed")):
        D = T[rows]
        yv = (D[ycol].notna() & (D[ycol] != False)).astype(float).values if ycol == "seed" else D[ycol].astype(float).values  # noqa: E712
        g = D.season.values
        c1, s1, ll1 = logit_fit(D[["z"]].values, yv, g)
        c2, s2, ll2 = logit_fit(D[["z", "p4"]].astype(float).values, yv, g)
        lr = 2 * (ll2 - ll1)
        keep_p4 = lr > 3.84                     # likelihood-ratio test at 5% (one degree of freedom)
        coef, se = (c2, s2) if keep_p4 else (c1, s1)
        out[name] = {"predictors": ["rpi_z", "p4"] if keep_p4 else ["rpi_z"], "coef": [round(float(x), 4) for x in coef],
                     "se": [round(float(x), 4) for x in se], "loglik_rpi_only": round(ll1, 2), "loglik_with_p4": round(ll2, 2),
                     "lr_p4": round(lr, 2), "n": int(len(D)), "events": int(yv.sum())}
        # in-sample check: the model's top-k per season (no noise) against the real selection
        hit = []
        for y_ in FIT_SEASONS if name == "at_large" else FIT_SEASONS[1:]:
            Ds = D[D.season == y_]
            sc = Ds.z.values * coef[0] + (Ds.p4.values * coef[1] if keep_p4 else 0)
            k = int((Ds[ycol].notna() & (Ds[ycol] != False)).sum()) if ycol == "seed" else int(Ds[ycol].sum())  # noqa: E712
            top = set(Ds.team.values[np.argsort(-sc)[:k]])
            real = set(Ds.team[(Ds[ycol].notna() & (Ds[ycol] != False)) if ycol == "seed" else Ds[ycol]])  # noqa: E712
            hit.append(len(top & real) / k)
        checks[name] = round(float(np.mean(hit)), 3)
        out[name]["in_sample_top_k_agreement"] = checks[name]
    # field benchmarks the selection must reproduce
    worst_atl, best_out = {}, {}
    for y_ in FIT_SEASONS:
        Ds = T[T.season == y_]
        worst_atl[y_] = int(Ds[Ds.at_large]["rank"].max())
        best_out[y_] = int(Ds[~Ds.field]["rank"].min())
    # RPI distribution: RPI at ranks 1, 16, 32, 64 and mean RPI by tier (2025 tiers of the feed names)
    tier_all = tiers()
    at = {k: [] for k in (1, 16, 32, 64)}
    by_tier = {t: [] for t in ("p4", "mid", "low")}
    for y_ in FIT_SEASONS:
        Ds = T[T.season == y_].sort_values("rpi", ascending=False)
        for k in at:
            at[k].append(float(Ds.rpi.iloc[k - 1]))
        tt = Ds.team.map(tier_all)
        for t in by_tier:
            by_tier[t].append(float(Ds.rpi[tt == t].mean()))
    rpi_bench = {"_note": "RPI from the feed (engine.rpi), Division I games before selection Monday, seasons " + ", ".join(FIT_SEASONS)
                          + "; tiers by the 2025 conference of the feed name (teams not in the 2025 list left out of the tier means)",
                 "conf": "B",
                 "rpi_at_rank": {str(k): {"mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v, ddof=1)), 4)} for k, v in at.items()},
                 "mean_rpi_by_tier": {t: {"mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v, ddof=1)), 4)} for t, v in by_tier.items()}}
    out["conf"] = "B"
    out["conf_note"] = ("RPI recomputed from the scoreboard feed (formula checked on 2026: rank correlation .99994 with the published RPI), "
                        "but without neutral-site flags and, in 2025, without most conference tournament results; 8 seasons, 270 at-large bids")
    cur = json.loads(INPUTS7.read_text()) if INPUTS7.exists() else {}
    cur["selection7"] = out
    INPUTS7.write_text(json.dumps(cur, indent=1) + "\n")
    bench = json.loads(BENCH.read_text())
    wa, bo = np.array(list(worst_atl.values()), float), np.array(list(best_out.values()), float)
    bench["field"]["worst_rpi_rank_at_large"] = {"mean": round(float(wa.mean()), 2), "sd": round(float(wa.std(ddof=1)), 2),
                                                 "median": float(np.median(wa)), "range": [int(wa.min()), int(wa.max())], "by_season": worst_atl}
    bench["field"]["best_rpi_rank_left_out"] = {"mean": round(float(bo.mean()), 2), "sd": round(float(bo.std(ddof=1)), 2),
                                                "median": float(np.median(bo)), "range": [int(bo.min()), int(bo.max())], "by_season": best_out}
    bench["rpi"] = rpi_bench
    bench["field"]["rpi_note"] = "RPI from the feed (engine.rpi), Division I games before selection Monday; seasons " + ", ".join(FIT_SEASONS)
    BENCH.write_text(json.dumps(bench, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k in ("at_large", "national_seed")}, indent=1))
    print("worst at-large rank", worst_atl, "| best left out", best_out)


if __name__ == "__main__":
    main()
