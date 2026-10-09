"""Phase 3 inputs: the AI manager's pitching changes and pinch hitters by hand (the lefty-specialist hook the Phase 6
bullpen Decider kept, and platoon pinch hitting). Decisions fitted from data, as in PR B; a human's same call resolves
with the same probabilities.

Data (data/ncaa_2025/roster_aggregates/, counts only, every tier pooled; plate appearances with both hands known):
  relief_by_hand.csv      after each plate appearance of a fielding side but its first: the current pitcher's hand x the
                          bats of the batter due up x inning bucket; changes, split by the new pitcher's hand
  pinch_hit_by_hand.csv   opportunities (every plate appearance) and pinch hitters by the pitcher's hand x the bats of the
                          batter due up (the one replaced) x inning bucket, with the pinch hitter's bats

Model (engine/manager.py):
  pull_mult[cur|bats|bucket]   the Phase 2/6 pull hazard times the real change rate in the cell over the bucket's rate
                               (the bucket's plate-appearance mix: the multipliers average 1 there, so pulls in total
                               are unchanged); the pitcher's own hand enters too (left-handers are pulled more often)
  relief_platoon[bucket]       g in the relief choice logit: +g/2 for a candidate of the batter's hand, -g/2 for the
                               other (switch hitters: 0). Odds of a left-hander for a left-handed batter over those for
                               a right-handed one are exp(2g): g is half the Mantel-Haenszel log odds ratio over the
                               current pitcher's hand
  relief_same_hand[bucket]     f: +f/2 for a candidate of the current pitcher's hand, -f/2 for the other (f < 0: teams
                               change hands); half the Mantel-Haenszel log odds ratio of a left-hander replacing a
                               left-hander over one replacing a right-hander, over the batter's hand
  ph_mult[pit|bats|bucket]     the Phase 6 pinch-hit hazard times the real rate in the cell over the bucket's
  ph_platoon                   gamma in the bench pick: a bench player with the platoon advantage (bats opposite the
                               pitcher, or switch) has his weight times exp(gamma); solved so the share of pinch hitters
                               with the advantage equals the real one, against the benches of simulated leagues
Then solved in the engine (solve(); --solve, repeated until the steps are small): the data-only choice terms ignore who
is available, so g, f, gamma and the pull multipliers' ratios are moved until the simulated statistics equal the real ones.
Writes the "usage" key of data/ncaa_2025/derived/phase3_inputs_2025.json.
    python3 scripts/build_phase3_usage.py
    python3 scripts/build_phase3_usage.py --solve runs/phase3_usage_step1.pkl
    python3 scripts/build_phase3_usage.py --normalize runs/phase3_usage_step2.pkl
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase3  # noqa: E402

AGG = ROOT / "data/ncaa_2025/roster_aggregates"
BUCKETS = ("1-6", "7+")


def relief() -> dict:
    r = pd.read_csv(AGG / "relief_by_hand.csv")
    a = r[(r.scope == "all") & r.cur_throws.isin(["L", "R"]) & r.batter_bats.isin(["L", "R", "S"])]
    mult, cells, g, same = {}, {}, {}, {}
    for b in BUCKETS:
        d = a[a.inning_bucket == b]
        base = d.changes.sum() / d.pas.sum()
        for x in d.itertuples():
            mult[f"{x.cur_throws}|{x.batter_bats}|{b}"] = round(float(x.changes / x.pas / base), 4)
            cells[f"{x.cur_throws}|{x.batter_bats}|{b}"] = {"pas": int(x.pas), "changes": int(x.changes), "to_L": int(x.changes_to_L),
                                                           "to_R": int(x.changes_to_R)}
        # Mantel-Haenszel odds ratio of a left-hander coming in, batter L against batter R, over the current pitcher's hand
        num = den = 0.0
        for cur in ("L", "R"):
            lft = d[(d.cur_throws == cur) & (d.batter_bats == "L")].iloc[0]
            rgt = d[(d.cur_throws == cur) & (d.batter_bats == "R")].iloc[0]
            n = lft.changes_to_L + lft.changes_to_R + rgt.changes_to_L + rgt.changes_to_R
            num += lft.changes_to_L * rgt.changes_to_R / n
            den += lft.changes_to_R * rgt.changes_to_L / n
        g[b] = round(math.log(num / den) / 2, 4)
        # the same, current pitcher L against R, over the batter's hand: a reliever of the current pitcher's hand
        num = den = 0.0
        for bats in ("L", "R"):
            cl = d[(d.cur_throws == "L") & (d.batter_bats == bats)].iloc[0]
            cr = d[(d.cur_throws == "R") & (d.batter_bats == bats)].iloc[0]
            n = cl.changes_to_L + cl.changes_to_R + cr.changes_to_L + cr.changes_to_R
            num += cl.changes_to_L * cr.changes_to_R / n
            den += cl.changes_to_R * cr.changes_to_L / n
        same[b] = round(math.log(num / den) / 2, 4)
    return {"pull_mult": mult, "relief_platoon": g, "relief_same_hand": same, "relief_cells": cells}


def pinch() -> dict:
    p = pd.read_csv(AGG / "pinch_hit_by_hand.csv")
    a = p[(p.scope == "all") & p.pitcher_throws.isin(["L", "R"]) & p.replaced_bats.isin(["L", "R", "S"])]
    mult, cells = {}, {}
    for b in BUCKETS:
        d = a[a.inning_bucket == b]
        opp = d[d.ph_bats == "opportunity"].set_index(["pitcher_throws", "replaced_bats"]).n
        ev = d[d.ph_bats != "opportunity"].groupby(["pitcher_throws", "replaced_bats"]).n.sum()
        base = ev.sum() / opp.sum()
        for (pt, rb), n in opp.items():
            mult[f"{pt}|{rb}|{b}"] = round(float(ev.get((pt, rb), 0) / n / base), 4)
            known = d[(d.pitcher_throws == pt) & (d.replaced_bats == rb) & d.ph_bats.isin(["L", "R", "S"])].set_index("ph_bats").n
            cells[f"{pt}|{rb}|{b}"] = {"opportunities": int(n), "ph": int(ev.get((pt, rb), 0)),
                                      **{f"ph_{k}": int(known.get(k, 0)) for k in ("L", "R", "S")}}
    k = a[a.ph_bats.isin(["L", "R", "S"])]
    adv = k[(k.ph_bats == "S") | ((k.ph_bats == "L") & (k.pitcher_throws == "R")) | ((k.ph_bats == "R") & (k.pitcher_throws == "L"))].n.sum()
    return {"ph_mult": mult, "ph_cells": cells, "ph_advantage_share": round(float(adv / k.n.sum()), 4), "ph_known": int(k.n.sum())}


def bench_gamma(target: float, pit_share_L: float, seeds=(7001, 7002)) -> tuple[float, float]:
    """gamma so the share of pinch hitters with the platoon advantage equals target: the bench (start rank 10-14) of
    simulated leagues with hands, each bench player weighted by his rank's bench-pick weight (Phase 6), against a
    pitcher who is left-handed at the share of plate appearances against left-handers (pit_share_L)."""
    from config import phase2, phase6
    from engine.league import build_league
    cfg = phase2.load()
    bw = phase6.load().get("subs6", {}).get("bench_pick_weight", {}).get("weight")
    rows = []
    for sd in seeds:
        lg = build_league(cfg, np.random.Generator(np.random.PCG64(np.random.SeedSequence(sd).spawn(3)[0])))
        for t in lg.teams:
            bench = [p for p in t.batters if p.order >= 9]
            w = np.array([bw[str(p.order + 1)] if bw else 1.0 for p in bench])
            rows.append((w, np.array([p.bats for p in bench])))

    def share(gam):
        tot = 0.0
        for pt, wt in (("L", pit_share_L), ("R", 1 - pit_share_L)):
            acc = []
            for w, bats in rows:
                a = (bats == "S") | ((bats == "L") & (pt == "R")) | ((bats == "R") & (pt == "L"))
                ww = w * np.exp(gam * a)
                acc.append((ww * a).sum() / ww.sum())
            tot += wt * np.mean(acc)
        return tot
    lo, hi = -5.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if share(mid) < target else (lo, mid)
    return round((lo + hi) / 2, 4), round(share(0.0), 4)


def _logit(p):
    return math.log(p / (1 - p))


def _season(seed: int) -> dict:
    from config import phase2
    from engine.season import simulate_season
    return simulate_season(phase2.load(), seed)["platoon"]


def solve(usage: dict, runs: list) -> dict:
    """One step of the in-engine solve: the choice terms and pull multipliers are moved so the simulated statistics equal the
    real ones the data-only estimates aimed at (the Mantel-Haenszel terms ignore who is available in a bullpen, the bench
    term the benches' hands). Per inning bucket: g by half the gap in the log odds ratio of a left-hander entering (batter due
    up L against R), f the same for the current pitcher's hand; gamma by the gap in the logit of the pinch hitters' platoon-
    advantage share; for each pitcher's hand, the pull multipliers by the square root of the gap in the change-rate ratio
    (batter due up of the other hand over his own), in opposite directions, so their mean stays near 1."""
    rel = sum(r["relief"] for r in runs).sum(axis=0)     # cur x bats x bucket x [opp, toL, toR]
    ph = sum(r["ph"] for r in runs).sum(axis=0)          # pit x due x bucket x [opp, L, R, S]
    r = pd.read_csv(AGG / "relief_by_hand.csv")
    a = r[(r.scope == "all") & r.cur_throws.isin(["L", "R"]) & r.batter_bats.isin(["L", "R"])]
    new = json.loads(json.dumps(usage))
    hands = ("L", "R")
    for bi, b in enumerate(BUCKETS):
        d = a[a.inning_bucket == b].set_index(["cur_throws", "batter_bats"])

        def mh(get, strata, pos, neg):
            num = den = 0.0
            for s_ in strata:
                (l1, r1), (l0, r0) = get(s_, pos), get(s_, neg)
                n = l1 + r1 + l0 + r0
                num += l1 * r0 / n; den += r1 * l0 / n
            return math.log(num / den)
        real_g = mh(lambda c, bt: (d.loc[(c, bt)].changes_to_L, d.loc[(c, bt)].changes_to_R), hands, "L", "R")
        sim_g = mh(lambda c, bt: (rel[hands.index(c), hands.index(bt), bi, 1], rel[hands.index(c), hands.index(bt), bi, 2]), hands, "L", "R")
        real_f = mh(lambda bt, c: (d.loc[(c, bt)].changes_to_L, d.loc[(c, bt)].changes_to_R), hands, "L", "R")
        sim_f = mh(lambda bt, c: (rel[hands.index(c), hands.index(bt), bi, 1], rel[hands.index(c), hands.index(bt), bi, 2]), hands, "L", "R")
        new["relief_platoon"][b] = round(usage["relief_platoon"][b] + (real_g - sim_g) / 2, 4)
        new["relief_same_hand"][b] = round(usage["relief_same_hand"][b] + (real_f - sim_f) / 2, 4)
        for ci, c in enumerate(hands):
            o = "R" if c == "L" else "L"
            rate = lambda bt: d.loc[(c, bt)].changes / d.loc[(c, bt)].pas
            srate = lambda bt: (rel[ci, hands.index(bt), bi, 1] + rel[ci, hands.index(bt), bi, 2]) / rel[ci, hands.index(bt), bi, 0]
            k = math.sqrt((rate(o) / rate(c)) / (srate(o) / srate(c)))
            new["pull_mult"][f"{c}|{o}|{b}"] = round(usage["pull_mult"][f"{c}|{o}|{b}"] * k, 4)
            new["pull_mult"][f"{c}|{c}|{b}"] = round(usage["pull_mult"][f"{c}|{c}|{b}"] / k, 4)
    allph = ph.sum(axis=(1, 2))                          # pitcher hand x [opp, L, R, S]
    sim_adv = (allph[0, 2] + allph[0, 3] + allph[1, 1] + allph[1, 3]) / allph[:, 1:].sum()
    new["ph_platoon"] = round(usage["ph_platoon"] + _logit(usage["ph_advantage_share"]) - _logit(sim_adv), 4)
    new["solve_steps"] = usage.get("solve_steps", 0) + 1
    print("relief g", usage["relief_platoon"], "->", new["relief_platoon"], "f", usage["relief_same_hand"], "->", new["relief_same_hand"],
          "ph gamma", usage["ph_platoon"], "->", new["ph_platoon"], f"(sim adv share {sim_adv:.4f})")
    return new


def normalize(usage: dict, runs: list) -> dict:
    """The pull and pinch-hit multipliers rescaled per inning bucket so they average 1 over the engine's own opportunity
    mix (the hands of pitchers and batters due up in simulated seasons with the final inputs): the hand terms move pulls
    and pinch hitters between matchups, not in total. Fitted on the real mix they averaged 1.02 on the engine's (2026-10-08:
    distinct batters per team-game 10.505 against 10.481 before Phase 3)."""
    new = json.loads(json.dumps(usage))
    hands, bats = "LR", "LRS"
    for key, arr in (("pull_mult", sum(r["relief"] for r in runs).sum(axis=0)), ("ph_mult", sum(r["ph"] for r in runs).sum(axis=0))):
        for bi, b in enumerate(BUCKETS):
            num = sum(arr[c, d, bi, 0] * usage[key][f"{hands[c]}|{bats[d]}|{b}"] for c in range(2) for d in range(3))
            mean = num / arr[:, :, bi, 0].sum()
            for c in hands:
                for d in bats:
                    new[key][f"{c}|{d}|{b}"] = round(usage[key][f"{c}|{d}|{b}"] / mean, 4)
            new.setdefault("normalized_mean_before", {})[f"{key}|{b}"] = round(float(mean), 4)
    print("multiplier means on the engine's mix before normalizing:", new["normalized_mean_before"])
    return new


def main() -> None:
    import argparse
    import pickle
    from concurrent.futures import ProcessPoolExecutor
    ap = argparse.ArgumentParser()
    ap.add_argument("--solve", type=Path, help="seasons file (runs/...pkl): one solve step from seasons played with the current inputs "
                                               "(simulated with config.phase3.USAGE_SEEDS when the file does not exist)")
    ap.add_argument("--normalize", type=Path, help="seasons file played with the final inputs: rescale the multipliers to average 1 on its mix")
    args = ap.parse_args()
    out = json.loads(phase3.INPUTS.read_text())
    if args.normalize:
        out["usage"] = normalize(out["usage"], pickle.loads(args.normalize.read_bytes()))
        phase3.INPUTS.write_text(json.dumps(out, indent=1))
        return
    if args.solve:
        if args.solve.exists():
            runs = pickle.loads(args.solve.read_bytes())
        else:
            with ProcessPoolExecutor(4) as ex:
                runs = list(ex.map(_season, phase3.USAGE_SEEDS))
            args.solve.write_bytes(pickle.dumps(runs))
        out["usage"] = solve(out["usage"], runs)
        phase3.INPUTS.write_text(json.dumps(out, indent=1))
        return
    rel, ph = relief(), pinch()
    pl = pd.read_csv(AGG / "platoon_league.csv")
    s = pl[(pl.scope == "all") & (pl.basis == "side_used")]
    share_L = float(s[s.pit_throws == "L"].pa.sum() / s.pa.sum())
    gam, base = bench_gamma(ph["ph_advantage_share"], share_L)
    out["usage"] = {"_doc": "scripts/build_phase3_usage.py: pull and pinch-hit hazard multipliers by hand, the platoon terms of the "
                            "relief choice and the bench pick", **rel, **ph, "ph_platoon": gam, "ph_advantage_share_at_gamma0": base,
                    "pa_share_vs_lhp": round(share_L, 4)}
    phase3.INPUTS.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out["usage"][k] for k in ("pull_mult", "relief_platoon", "relief_same_hand", "ph_mult", "ph_advantage_share", "ph_platoon",
                                                   "ph_advantage_share_at_gamma0")}, indent=1))


if __name__ == "__main__":
    main()
