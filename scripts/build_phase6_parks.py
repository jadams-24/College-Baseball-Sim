"""Phase 6 park effects.

Magnitude, from the full 2025 scoreboard (every D1-vs-D1 final; scripts/build_phase2_teams.py fits
it with a park term, the home team's park, alongside team offense and run prevention): the true SD
and tier means of park effects in log runs per game, estimation noise removed by method of
moments. Composition, from the box scores of the play-by-play sample (data/ncaa_2025/pbp/parsed/
schedule_games_2025.csv, neutral sites dropped), for the full-season teams: per rate (K, BB,
HBP, HR per PA; BABIP; XBH share of hits) the classic park factor on the logit scale, both teams'
rate in the team's home games minus both teams' rate in its road games, then the covariance of the
park factors across rates with binomial noise removed (method of moments). The engine draws each team's park as
a vector of logit offsets from that covariance, scaled so its run variance (through the engine's
run-value gradient) equals the scoreboard's, with the tier mean placed along the run direction.
The run level itself is drawn conditional on the home team's offense and defense (the scoreboard
fit's within-tier joint covariance: parks correlate about -.4 with both).
Every plate appearance in the park carries the offsets, for both teams.
Writes the "parks6" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/build_phase6_parks.py      (after scripts/build_phase2_teams.py)
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
from config.phase2 import GAME_SCALE, INPUTS, RATES, RUN_SCALE  # noqa: E402
from config.phase6 import FULL_SEASON_GAMES, INPUTS6, MIN_PARK_GAMES  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"


def team_rows() -> pd.DataFrame:
    sg = pd.read_csv(P / "schedule_games_2025.csv")
    sg = sg[(sg.home_has_box == 1) if "home_has_box" in sg else slice(None)]
    sg = sg[(sg.neutral_site == 0) & sg.home_is_d1.astype(bool) & sg.away_is_d1.astype(bool)]
    rows = []
    for s, o in (("home", "away"), ("away", "home")):
        d = pd.DataFrame({"bat": sg[f"{s}_team_id"], "pit": sg[f"{o}_team_id"], "park": sg["home_team_id"],
                          "pa": sg[f"{s}_pa"], "ab": sg[f"{s}_ab"], "h": sg[f"{s}_h"], "d2": sg[f"{s}_2b"], "d3": sg[f"{s}_3b"],
                          "hr": sg[f"{s}_hr"], "bb": sg[f"{s}_bb"], "hbp": sg[f"{s}_hbp"], "k": sg[f"{s}_k"], "sf": sg[f"{s}_sf"]})
        rows.append(d)
    t = pd.concat(rows, ignore_index=True).dropna()
    t = t[t.pa > 20]
    return t


def counts(t: pd.DataFrame, rate: str) -> tuple:
    if rate in ("K", "BB", "HBP", "HR"):
        x = t[{"K": "k", "BB": "bb", "HBP": "hbp", "HR": "hr"}[rate]]
        n = t.pa
    elif rate == "BABIP":
        x = t.h - t.hr
        n = t.ab - t.k - t.hr + t.sf
    else:
        x = t.d2 + t.d3
        n = t.h - t.hr
    return x.values.astype(float), n.values.astype(float)


def park_effects(t: pd.DataFrame, rate: str, full: set) -> tuple:
    """Classic park factor per full-season team, on the logit scale: both teams' rate in its home
    games minus both teams' rate in its road games (opponents and road parks average out over a
    season). Returns the estimates (centred) and their binomial noise variances."""
    x, n = counts(t, rate)
    t = t.assign(x=x, n=n)
    est, var = {}, {}
    for k in full:
        h = t[t.park == k]
        r = t[((t.bat == k) | (t.pit == k)) & (t.park != k)]
        if len(h) < 2 * MIN_PARK_GAMES or len(r) < 2 * MIN_PARK_GAMES or h.n.sum() == 0 or r.n.sum() == 0:
            continue
        ph, pr = h.x.sum() / h.n.sum(), r.x.sum() / r.n.sum()
        if not (0 < ph < 1 and 0 < pr < 1):
            continue
        est[k] = np.log(ph / (1 - ph)) - np.log(pr / (1 - pr))
        var[k] = 1 / (h.n.sum() * ph * (1 - ph)) + 1 / (r.n.sum() * pr * (1 - pr))
    e, v = pd.Series(est), pd.Series(var)
    return e - e.mean(), v, 1.0


def main() -> None:
    t = team_rows()
    sg = pd.read_csv(P / "games_2025.csv")
    g2 = pd.concat([sg.home_team_id, sg.away_team_id])
    full = set(g2.value_counts()[lambda c: c >= FULL_SEASON_GAMES].index)
    est, noise = {}, {}
    for r in RATES:
        e, v, phi = park_effects(t, r, full)
        est[r], noise[r] = e, v
        print(f"{r}: {len(e)} parks, raw SD {e.std():.4f}, mean noise SD {np.sqrt(v.mean()):.4f}, true SD {np.sqrt(max(e.var() - v.mean(), 0)):.4f}, dispersion {phi:.2f}")
    common = sorted(set.intersection(*(set(e.index) for e in est.values())))
    E = np.column_stack([est[r].reindex(common).values for r in RATES])
    N = np.column_stack([noise[r].reindex(common).values for r in RATES])
    S = np.cov(E.T) - np.diag(N.mean(0))
    vals, vecs = np.linalg.eigh(S)
    S_psd = vecs @ np.diag(np.clip(vals, 0, None)) @ vecs.T
    rs = json.loads(RUN_SCALE.read_text())
    w = np.array(rs["w_gradient_logR"])
    run_var_box = float(w @ S_psd @ w)
    tt = json.loads(INPUTS.read_text())["team_talent"]
    pk = tt["parks"]
    # the scoreboard measures runs per game after run-rule and walk-off truncation, which compress
    # every effect; the engine's game scale (phase2_game_scale_2025.json, k_o) maps a scoreboard
    # rating to engine units, and a park acts on both offenses like a rating does
    k_o = json.loads(GAME_SCALE.read_text())["scale"]["k_o"]
    target = (k_o * pk["sd_pooled"]) ** 2
    scale = target / run_var_box if run_var_box > 0 else 0.0
    cov = S_psd * scale
    # tier mean along the run direction: the offset vector m with w.m = mean (log runs) of least norm in the metric of cov
    u = cov @ w / float(w @ cov @ w)
    tier_mean = {tier: (u * k_o * v["mean"]).round(5).tolist() for tier, v in pk["tiers"].items()}
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "rates": list(RATES), "n_parks_box": len(common),
           "box_true_sd": {r: round(float(np.sqrt(max(S[i, i], 0))), 4) for i, r in enumerate(RATES)},
           "box_corr": [[round(float(S_psd[i, j] / np.sqrt(S_psd[i, i] * S_psd[j, j])) if S_psd[i, i] > 0 and S_psd[j, j] > 0 else 0.0, 3)
                         for j in range(len(RATES))] for i in range(len(RATES))],
           "run_sd_box": round(float(np.sqrt(run_var_box)), 4), "run_sd_scoreboard": pk["sd_pooled"], "k_o": round(k_o, 4), "scale": round(scale, 4),
           "cov": cov.round(6).tolist(), "tier_mean": tier_mean,
           # the engine draws a park's run level (scoreboard log runs) from its regression on the home team's
           # (o, d) deviations from the tier mean (team_talent parks.joint), then its rate vector along run_dir
           # (w.run_dir = 1) plus the part of cov orthogonal to the run direction in that metric
           "w": [round(float(v), 6) for v in w], "run_dir": u.round(6).tolist(), "joint": pk.get("joint")}
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["parks6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("_note", "cov")}, indent=1))


if __name__ == "__main__":
    main()
