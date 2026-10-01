"""Solve the location (intercept) of each true-talent distribution so that simulated,
PA-weighted league rates equal the league outcome table.

The talent model fixes each rate's spread (tier, team, individual) from data; its mean
is defined by the league table, which is a PA-weighted average over real usage (better
hitters bat more, better pitchers pitch more). The usage-weighted mean is only known
after simulating usage, so the six intercepts are found by fixed-point iteration on
simulated seasons:  c <- c + logit(table rate) - logit(simulated rate).
Only K, BB, HBP, HR per PA, BABIP and XBH are matched; runs, team spreads and player
distributions are not used. Calibration seeds (900000+) are disjoint from gate seeds.
Output: data/ncaa_2025/derived/phase2_location_2025.json
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import phase2  # noqa: E402
from engine import league as league_mod  # noqa: E402
from engine.season import simulate_season  # noqa: E402

OUT = Path("data/ncaa_2025/derived/phase2_location_2025.json")
SEEDS = (900001, 900002)
ITERS = 4


def realized(res: dict) -> dict:
    b = res["bstats"]
    pa, ab, h, d2, d3, hr, bb, hbp, k, sf, sh = (b[:, i].sum() for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11))
    hits = h - hr
    # balls in play excluding reached-on-error: AB - K - HR - ROE + SF + SH; ROE is not tracked per batter,
    # so use the out class via PA identity: non-ROE BIP = PA - K - BB - HBP - HR - ROE
    roe = res["roe"]
    bip_noroe = pa - k - bb - hbp - hr - roe
    return {"K": k / pa, "BB": bb / pa, "HBP": hbp / pa, "HR": hr / pa, "BABIP": hits / bip_noroe, "XBH": (d2 + d3) / hits}


def main() -> None:
    cfg = phase2.load()
    c = {r: 0.0 for r in phase2.RATES}
    lg = lambda p: math.log(p / (1 - p))
    history = []
    for it in range(ITERS):
        league_mod.FIXED_LOCATION = dict(c)
        rates = []
        for s in SEEDS:
            res = simulate_season(cfg, s)
            rates.append(realized(res))
        avg = {r: float(np.mean([x[r] for x in rates])) for r in c}
        gap = {r: lg(cfg.league_rates[r]) - lg(avg[r]) for r in c}
        history.append({"iteration": it, "location": dict(c), "realized": avg, "logit_gap": gap})
        print(it, {r: f"{avg[r]:.4f}/{cfg.league_rates[r]:.4f}" for r in c})
        c = {r: c[r] + gap[r] for r in c}
    OUT.write_text(json.dumps({"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": SEEDS, "location": c, "history": history}, indent=1) + "\n")
    print("location:", {r: round(v, 4) for r, v in c.items()})


if __name__ == "__main__":
    main()
