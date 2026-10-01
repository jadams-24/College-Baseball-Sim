"""Phase 4 inputs: individual pitcher leash (the Stamina rating) from the play-by-play.

The engine pulls a pitcher with a hazard from the Phase 2 usage tables (engine/manager.py):
P(replaced before the next batter | role, weekend, rotation rank, outing pitch count,
outing runs, inning just ended). Real pitchers differ around that baseline: some are
left in longer at the same pitch count and runs. That individual leash is modelled as a
proportional-hazards multiplier theta_i: h_i = 1 - (1 - h)^theta_i, with log theta normal.

Estimate: empirical Bayes with the exact likelihood (engine/eb.py, the estimator the
Phase 4 round trip uses on simulated seasons). Each decision after a batter has the
baseline hazard h from the Manager's own lookup chain (including the weekend rotation-rank
leash on full-season teams); a pitcher's log theta has prior N(mu, tau^2) per role (starter,
reliever), fitted by marginal maximum likelihood. tau is the true spread of individual leash.
Pitchers with >= MIN_APPS appearances in the role. A method-of-moments check (O/E ratio,
observed variance minus Poisson noise) is reported alongside.
Output: data/ncaa_2025/derived/phase4_inputs_2025.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.players import load_pa  # noqa: E402

from config.phase2 import MIN_HAZARD_N, SPOT_STARTER_RANK  # noqa: E402
from engine import eb  # noqa: E402

INPUTS2 = Path("data/ncaa_2025/derived/phase2_inputs_2025.json")
OUT = Path("data/ncaa_2025/derived/phase4_inputs_2025.json")
FULL_SEASON_GAMES = 40   # same sample definition as build_phase2_benchmarks.py
MIN_APPS = 5             # appearances in the role before a pitcher enters the moments
WEEKEND = {4, 5, 6}


def lookup(chain, tables):
    for name, key in chain:
        c = tables[name].get(key)
        if c is not None and c[1] >= MIN_HAZARD_N:
            return c[0] / c[1]
    c = tables[chain[-1][0]].get(chain[-1][1]) if chain else None
    return None if c is None or c[1] == 0 else c[0] / c[1]


def main() -> None:
    u = json.loads(INPUTS2.read_text())["usage"]
    tables = {"sp": u["starter_pull"]["table"], "spb": u["starter_pull"]["backoff"], "rp": u["reliever_pull"]["table"],
              "rpb": u["reliever_pull"]["backoff"], "wr": u["weekend_starter_pull_by_rank"]["table"], "wrb": u["weekend_starter_pull_by_rank"]["backoff"]}
    pa = load_pa()
    gm = pd.read_csv("data/ncaa_2025/pbp/parsed/games_2025.csv")
    gm["wd"] = pd.to_datetime(gm.game_date).dt.dayofweek
    pa = pa.merge(gm[["game_id", "wd", "game_date"]], on="game_id").sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["weekend"] = pa.wd.isin(WEEKEND).astype(int)
    first = pa.groupby(["game_id", "pit_team_id"]).pkey.transform("first")
    pa["is_sp"] = (pa.pkey == first).astype(int)
    g2 = pd.concat([gm[["game_id", "home_team_id"]].rename(columns={"home_team_id": "t"}), gm[["game_id", "away_team_id"]].rename(columns={"away_team_id": "t"})])
    gpt = g2.groupby("t").game_id.nunique()
    full = set(gpt[gpt >= FULL_SEASON_GAMES].index)
    # rotation rank of weekend starters on full-season teams (as in build_phase2_benchmarks.py)
    sg = pa[(pa.is_sp == 1) & (pa.weekend == 1) & pa.pit_team_id.isin(full)].drop_duplicates(["game_id", "pit_team_id"])
    cnt = sg.groupby(["pit_team_id", "pkey"]).size().rename("n").reset_index()
    cnt["rank"] = cnt.groupby("pit_team_id").n.rank(ascending=False, method="first").astype(int).clip(upper=SPOT_STARTER_RANK)
    rank = {(t, k): r for t, k, r in zip(cnt.pit_team_id, cnt.pkey, cnt["rank"])}
    # outing state before each pull decision
    pa["outing"] = (pa.pkey != pa.groupby(["game_id", "pit_team_id"]).pkey.shift()).groupby([pa.game_id, pa.pit_team_id]).cumsum()
    pa["out_pitches"] = pa.groupby(["game_id", "pit_team_id", "outing"]).pitches.cumsum()
    pa["out_runs"] = pa.groupby(["game_id", "pit_team_id", "outing"]).runs_on_play.cumsum()
    nxt = pa.groupby(["game_id", "pit_team_id"]).pkey.shift(-1)
    pa["pulled"] = (nxt.notna() & (nxt != pa.pkey)).astype(int)
    h = pa[nxt.notna() & pa.out_pitches.notna()].copy()
    h["starter"] = h.groupby(["game_id", "pit_team_id", "outing"]).is_sp.transform("max")
    h["ie"] = ((h.outs + h.outs_on_play) >= 3).astype(int)
    pb = (h.out_pitches // 10).clip(upper=12).astype(int).values
    rb = h.out_runs.clip(upper=5).astype(int).values
    base = []
    for s, wk, p, r, ie, t, k in zip(h.starter.values, h.weekend.values, pb, rb, h.ie.values, h.pit_team_id.values, h.pkey.values):
        rk = rank.get((t, k)) if (s and wk) else None
        if s and rk is not None:
            chain = [("wr", f"{rk}|{p}|{r}|{ie}"), ("wrb", f"{rk}|{p}|{ie}"), ("sp", f"{wk}|{p}|{r}|{ie}"), ("spb", f"{wk}|{p}|{ie}")]
        elif s:
            chain = [("sp", f"{wk}|{p}|{r}|{ie}"), ("spb", f"{wk}|{p}|{ie}")]
        else:
            chain = [("rp", f"{p}|{r}|{ie}"), ("rpb", f"{p}|{ie}")]
        base.append(lookup(chain, tables))
    h["h"] = base
    h = h[h.h.notna()]
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "src": "WMT play-by-play 2025 (data/ncaa_2025/pbp), Phase 2 usage tables", "stamina": {}}
    for role, sub in (("starter", h[h.starter == 1]), ("reliever", h[h.starter == 0])):
        g = sub.groupby(["pit_team_id", "pkey"]).agg(O=("pulled", "sum"), E=("h", "sum"), apps=("game_id", "nunique"))
        g = g[(g.apps >= MIN_APPS) & (g.E > 0)]
        keep = sub.set_index(["pit_team_id", "pkey"]).loc[g.index].reset_index()
        keep["ls"] = np.log1p(-keep.h.clip(upper=1 - 1e-9))
        surv = keep[keep.pulled == 0].groupby(["pit_team_id", "pkey"]).ls.sum().reindex(g.index).fillna(0).values
        pulls = keep[keep.pulled == 1].groupby(["pit_team_id", "pkey"]).h.apply(list).reindex(g.index)
        pulls = [x if isinstance(x, list) else [] for x in pulls]
        fit = eb.fit(eb.hazard_loglik(surv, pulls), np.zeros(len(g), int))
        pr = fit["prior"][0]
        R = g.O / g.E
        w = g.E / g.E.sum()
        m = float((w * R).sum())
        vobs = float((w * (R - m) ** 2).sum())
        noise = float((w * (m / g.E)).sum())
        vt = max(vobs - noise, 0.0)
        out["stamina"][role] = {"n_pitchers": int(len(g)), "log_sd": round(pr["tau"], 4), "log_mean": round(pr["mu"], 4),
                                "posterior_sd_mean": round(float(np.mean(fit["sd"])), 4),
                                "mom_check": {"mean_ratio": round(m, 4), "var_obs": round(vobs, 5), "var_noise": round(noise, 5), "var_true": round(vt, 5),
                                              "log_sd": round(float(np.sqrt(np.log(1 + vt / m ** 2))), 4)},
                                "ratio_sd_obs": round(float(np.sqrt(vobs)), 4)}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["stamina"], indent=1))


if __name__ == "__main__":
    main()
