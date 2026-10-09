"""Bullpen deployment, P4-only comparison (owner, 2026-10-09: "do the P4-only comparison first"). Sizes only.

Round 3 (reports/diagnosis_sizes_round3.md) compared the engine's relief-quality component, over every team, with the real
one over the 50 full-season staffs of the play-by-play (36 P4, 13 mid, 1 low). Here both sides are restricted to P4 pitching
teams:
  real    round 2's estimator (scripts/diag_tto_mopup.py mopup_dphi, relief entries' leave-game-out quality against the team's
          relief mean, noise-corrected, bootstrap over games) on the 36 P4 full-season staffs
  engine  the same on the instrumented seasons of scripts/diag_round3_sim.py, relief plate appearances of P4 pitching teams
          only (the team-games batting against them)
Also the entering pitcher's quality gap by margin bucket, both sides. Writes reports/diagnosis_bullpen_p4.json and .md.
    python3 scripts/diag_bullpen_p4.py [--dir runs/round3/<key>]
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import diag_round3 as r3  # noqa: E402
import diag_tto_mopup as m2  # noqa: E402

OUT = ROOT / "reports/diagnosis_bullpen_p4"
VERSIONS = (("blowout_5plus", 5), ("blowout_7plus_engine_bin", 7), ("all_relief", 0))
BUCKETS = (("0-1", 0, 1), ("2-3", 2, 3), ("4", 4, 4), ("5-7", 5, 7), ("8+", 8, 99))


def real_side() -> dict:
    pa = m2.plate_appearances()
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(t.ncaa_team_id, t.tier))
    full = {x for x in m2.full_season_teams() if tier.get(x) == "p4"}
    season, pg, _ = m2.pitcher_quality(pa)
    rng = np.random.default_rng(20261009)
    d = m2.mopup_dphi(pa, season, pg, full, rng)
    out = {"n_staffs": len(full)}
    for v, _ in VERSIONS:
        out[v] = {"dphi": d[v]["dphi_noise_corrected"], "se": d[v]["se"]["dphi_noise_corrected"], "corr": d[v]["corr_t_rest"]}
    g = m2.pa_gaps(pa, season, pg, full)
    k = g[g.gap_known]
    out["gap_by_bucket"] = {lab: float(k[k.entry_absm.between(lo, hi)].gap.mean()) for lab, lo, hi in BUCKETS}
    return out


def sim_season(r: dict, lw: dict) -> dict:
    pa, g = r3.frames(r, lw)
    tg, _ = r3.team_games(pa, g)
    p4 = {tid for tid, t in r["teams"].items() if t["tier"] == "p4"}
    pa_p4 = pa[pa.pit_team.isin(p4)]
    tg_p4 = tg[tg.pit_team.isin(p4)]
    # the quality gap uses every pitcher's season (leave-game-out) and his own team's relief mean; restricting to P4 staffs
    # keeps P4 relievers against P4 means
    res = r3.mopup_sim(pa_p4, tg_p4)
    out = {v: {"dphi": res[v]["dphi_noise_corrected"], "corr": res[v]["corr_t_rest"]} for v, _ in VERSIONS}
    # gap by entry-margin bucket (P4 relief plate appearances with a known leave-game-out quality)
    pg = pa_p4.groupby(["pid", "gid"]).agg(bf=("rv", "size"), rv=("rv", "sum")); season = pg.groupby("pid").sum()
    k = pd.MultiIndex.from_arrays([pa_p4.pid, pa_p4.gid])
    n_o = season.bf.reindex(pa_p4.pid).values - pg.bf.reindex(k).values
    s_o = season.rv.reindex(pa_p4.pid).values - pg.rv.reindex(k).values
    rl = (~pa_p4.is_sp).values & (n_o >= m2.MIN_OTHER_BF)
    team_rl = pa_p4[~pa_p4.is_sp].groupby("pit_team").rv.mean()
    gap = s_o / np.where(n_o > 0, n_o, 1) - pa_p4.pit_team.map(team_rl).values
    entry = pa_p4.groupby(["gid", "pit_team", "outing"]).margin.transform("first").abs().values
    out["gap_by_bucket"] = {lab: float(np.mean(gap[rl & (entry >= lo) & (entry <= hi)])) for lab, lo, hi in BUCKETS}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT / "runs/round3/57148fcc6c2ce905")
    a = ap.parse_args()
    lw = r3.real_round2()["lw"]
    per = []
    for f in sorted(a.dir.glob("season_*.pkl")):
        per.append(sim_season(pickle.loads(f.read_bytes()), lw))
        print(f.name, {v: round(per[-1][v]["dphi"], 4) for v, _ in VERSIONS}, flush=True)
    real = real_side()
    res = {"real_p4": real, "sim_p4": {}}
    for v, _ in VERSIONS:
        a_ = np.array([p[v]["dphi"] for p in per]); c_ = np.array([p[v]["corr"] for p in per])
        s, se = float(a_.mean()), float(a_.std(ddof=1) / math.sqrt(len(a_)))
        res["sim_p4"][v] = {"dphi": s, "se": se, "corr": float(c_.mean())}
        res.setdefault("gap", {})[v] = {"value": real[v]["dphi"] - s, "se": math.hypot(real[v]["se"], se)}
    res["sim_p4"]["gap_by_bucket"] = {lab: float(np.mean([p["gap_by_bucket"][lab] for p in per])) for lab, *_ in BUCKETS}
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
