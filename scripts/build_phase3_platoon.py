"""Phase 3 inputs: platoon shifts, the logit offsets a matchup gets from the side the batter hits from and the pitcher's hand,
for the six engine rates (K, BB, HBP, HR per PA; BABIP; extra-base share of hits).

Real: data/ncaa_2025/roster_aggregates/platoon_league.csv (2025 play-by-play, plate appearances with both hands known;
basis side_used: a switch hitter counts on the side he batted from), by the batting team's tier.
Simulated: seasons of the engine with hands and usage on and platoon off (config.phase3.PLATOON_SEEDS), the same cells.

Net of who faced whom: each simulated cell already carries the talent of the players in it (hands are drawn with talent,
lineups and bullpens choose by hand), so the gap between a real cell and the simulated one is the platoon effect. Per tier
and rate, d = logit(real) - logit(sim) for each of the four (side, hand) pairs, less its plate-appearance-weighted mean over
the pairs (a tier-level gap between the engine and the sample is not a platoon effect); the shift is the average of these
over the tiers, weighted by the real cell's plate appearances. Each rate's four shifts are then centred so the league's
rate does not move to first order: sum over pairs of n p (1 - p) shift = 0 (n the simulated D1 plate appearances in the
pair, p the rate there). Standard errors from the binomial variance of the real cells.

Writes the "platoon" key of data/ncaa_2025/derived/phase3_inputs_2025.json.
    python3 scripts/build_phase3_platoon.py [--seasons runs/phase3_platoon_seasons.pkl] [--iterate]
--iterate refits on seasons played with the current shifts (adds the remaining gap to them); --recentre runs/x.pkl centres the
shifts exactly on the final engine's mix (after the usage solve and normalization).
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase3  # noqa: E402

AGG = ROOT / "data/ncaa_2025/roster_aggregates"
TIERS = ("p4", "mid", "low")
PAIRS = (("L", "L"), ("L", "R"), ("R", "L"), ("R", "R"))
RATES6 = ("K", "BB", "HBP", "HR", "BABIP", "XBH")
SIM_COLS = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")      # engine.game2 CELL_RESULTS


def _season(args) -> dict:
    seed, platoon = args
    phase3.FEATURES["platoon"] = platoon
    from config import phase2
    from engine.season import simulate_season
    res = simulate_season(phase2.load(), seed)
    return res["platoon"]


def seasons(path: Path | None, platoon: bool, workers: int) -> list:
    if path is not None and path.exists():
        return pickle.loads(path.read_bytes())
    with ProcessPoolExecutor(workers) as ex:
        out = list(ex.map(_season, [(s, platoon) for s in phase3.PLATOON_SEEDS]))
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(out))
    return out


def rates_from(c: dict) -> dict:
    """The six rates and their trials from outcome counts (keys K, BB, HBP, HR, 1B, 2B, 3B, ROE and outs in play)."""
    pa = c["PA"]
    h = c["1B"] + c["2B"] + c["3B"]
    bip = pa - c["K"] - c["BB"] - c["HBP"] - c["HR"] - c["ROE"]
    return {"K": (c["K"], pa), "BB": (c["BB"], pa), "HBP": (c["HBP"], pa), "HR": (c["HR"], pa), "BABIP": (h, bip),
            "XBH": (c["2B"] + c["3B"], h)}


def real_cells() -> dict:
    pl = pd.read_csv(AGG / "platoon_league.csv")
    s = pl[(pl.scope == "bat_tier") & (pl.basis == "side_used")]
    out = {}
    for x in s.to_dict("records"):
        c = {k: x[k] for k in ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE")}
        c["PA"] = x["pa"]
        out[(x["scope_value"], x["bat_hand"], x["pit_throws"])] = rates_from(c)
    return out


def sim_cells(runs: list) -> dict:
    used = sum(r["used"] for r in runs)        # tier x side (L, R) x pitcher hand (L, R) x outcome
    out = {}
    for ti, tier in enumerate(TIERS):
        for si, side in enumerate("LR"):
            for hi, hand in enumerate("LR"):
                v = used[ti, si, hi]
                c = dict(zip(SIM_COLS, v.tolist()))
                c["PA"] = int(v.sum())
                out[(tier, side, hand)] = rates_from(c)
    return out


def logit(x, n):
    p = (x + 0.5) / (n + 1.0)
    return np.log(p / (1 - p)), 1.0 / ((n + 1.0) * p * (1 - p))


def fit(real: dict, sim: dict, prior: dict | None = None) -> dict:
    shift, se, gap = {}, {}, {}
    for r in RATES6:
        acc = {pr: [0.0, 0.0, 0.0] for pr in PAIRS}           # sum w d, sum w, sum w^2 var
        for tier in TIERS:
            d, var, w = {}, {}, {}
            for pr in PAIRS:
                xr, nr = real[(tier, *pr)][r]
                xs, ns = sim[(tier, *pr)][r]
                lr, vr = logit(xr, nr)
                ls, vs = logit(xs, ns)
                d[pr], var[pr], w[pr] = lr - ls, vr + vs, nr
            ws = {pr: sim[(tier, *pr)][r][1] for pr in PAIRS}
            mean = sum(ws[pr] * d[pr] for pr in PAIRS) / sum(ws.values())
            for pr in PAIRS:
                a = acc[pr]
                a[0] += w[pr] * (d[pr] - mean); a[1] += w[pr]; a[2] += w[pr] ** 2 * var[pr]
        raw = {pr: acc[pr][0] / acc[pr][1] for pr in PAIRS}
        if prior:
            raw = {pr: raw[pr] + prior[f"{pr[0]}|{pr[1]}"][RATES6.index(r)] for pr in PAIRS}
        # centring on the simulated D1 mix (all tiers): sum n p (1 - p) shift = 0
        wt = {}
        for pr in PAIRS:
            x = sum(sim[(t, *pr)][r][0] for t in TIERS); n = sum(sim[(t, *pr)][r][1] for t in TIERS)
            p = x / n
            wt[pr] = n * p * (1 - p)
        c = sum(wt[pr] * raw[pr] for pr in PAIRS) / sum(wt.values())
        for pr in PAIRS:
            shift.setdefault(pr, [0.0] * 6)[RATES6.index(r)] = round(raw[pr] - c, 5)
            se.setdefault(pr, [0.0] * 6)[RATES6.index(r)] = round(float(np.sqrt(acc[pr][2]) / acc[pr][1]), 5)
            gap.setdefault(pr, [0.0] * 6)[RATES6.index(r)] = round(acc[pr][0] / acc[pr][1], 5)
    key = lambda pr: f"{pr[0]}|{pr[1]}"
    return {"shift": {key(pr): v for pr, v in shift.items()}, "se": {key(pr): v for pr, v in se.items()},
            "remaining_gap": {key(pr): v for pr, v in gap.items()}}


def recentre(shift: dict, runs: list) -> dict:
    """Exact centring on the final engine's plate-appearance mix: per rate, one constant c added to the four shifts so that
    sum over pairs of n expit(logit p + c) equals sum of n expit(logit p - shift), p the simulated rate in the pair with the
    shifts on, n its trials (seasons with the final inputs). The first-order centring of fit() used the mix before the usage
    solve; stronger bullpen matching then raised same-hand plate appearances (L vs L .094 -> .101) and HR per PA fell 1%."""
    sim = sim_cells(runs)
    new = {k: list(v) for k, v in shift.items()}
    cs = {}
    for ri, r in enumerate(RATES6):
        cells = []
        for pr in PAIRS:
            x = sum(sim[(t, *pr)][r][0] for t in TIERS); n = sum(sim[(t, *pr)][r][1] for t in TIERS)
            cells.append((n, np.log(x / (n - x)), shift[f"{pr[0]}|{pr[1]}"][ri]))
        target = sum(n * 1 / (1 + np.exp(-(lp - d))) for n, lp, d in cells)
        c = 0.0
        for _ in range(50):
            f = sum(n / (1 + np.exp(-(lp + c))) for n, lp, _ in cells) - target
            g = sum(n * np.exp(-(lp + c)) / (1 + np.exp(-(lp + c))) ** 2 for n, lp, _ in cells)
            c -= f / g
            if abs(f) < 1e-9:
                break
        cs[r] = round(float(c), 5)
        for pr in PAIRS:
            new[f"{pr[0]}|{pr[1]}"][ri] = round(shift[f"{pr[0]}|{pr[1]}"][ri] + c, 5)
    print("recentring constants:", cs)
    return new, cs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=Path, default=ROOT / "runs/phase3_platoon_seasons.pkl")
    ap.add_argument("--iterate", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--recentre", type=Path, help="seasons file played with the final inputs (simulated if missing): exact centring")
    args = ap.parse_args()
    out = json.loads(phase3.INPUTS.read_text())
    if args.recentre:
        runs = seasons(args.recentre, True, args.workers)
        out["platoon"]["shift"], out["platoon"]["recentre_constants"] = recentre(out["platoon"]["shift"], runs)
        phase3.INPUTS.write_text(json.dumps(out, indent=1))
        return
    prior = out.get("platoon", {}).get("shift") if args.iterate else None
    runs = seasons(args.seasons, bool(args.iterate), args.workers)
    res = fit(real_cells(), sim_cells(runs), prior)
    res["_doc"] = ("scripts/build_phase3_platoon.py: logit offsets added to the batter's (RATES order: K, BB, HBP, HR, BABIP, XBH) by "
                   "'side used|pitcher hand', net of who faced whom, centred on the league mix")
    res["rates"] = list(RATES6)
    res["seeds"] = list(phase3.PLATOON_SEEDS)
    res["iterated"] = bool(args.iterate)
    out["platoon"] = res
    phase3.INPUTS.write_text(json.dumps(out, indent=1))
    for k in ("shift", "se", "remaining_gap"):
        print(k, json.dumps(res[k]))


if __name__ == "__main__":
    main()
