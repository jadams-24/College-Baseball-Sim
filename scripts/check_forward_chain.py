"""Forward pitch-by-pitch play against the outcome-first method it replaces (engine restructure, 2026-10-06; owner
condition: "before replacing the outcome-first draw, run both methods on a large sample and show they produce the
same distributions").

Both methods on the same matchups: batter and pitcher pairs drawn from a generated league, at the batting team's
park or a neutral site, against the pitcher's team's defense (its error odds as engine._fielding_context sets them
for a lineup of its nine regulars).
  old  the PA outcome drawn from the matchup, the reached-on-error tilt applied, then the pitch sequence drawn from
       the chain conditioned on the outcome (engine.pitch.PitchModel.sequence; the Phase 5-7 engine)
  new  the transformed chain played forward one pitch at a time (engine.pitch.PitchModel.forward; GameSession)
Compared: the PA outcome distribution, the count each PA ended at, how often each count is reached, pitches per PA,
the pitch events at each count, and the outcome x pitches joint, by two-sample chi-square; each method's outcome
counts against the exact law, matchup by matchup; and the forward chain's exact outcome law against the matchup's
(no sampling).

    python3 scripts/check_forward_chain.py [--matchups 3000] [--per 400] [--seed 7]
Writes reports/forward_chain_check.md and .json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from bisect import bisect_right
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase2  # noqa: E402
from config.phase5 import OUTCOMES as POUT  # noqa: E402
from engine.game2 import B_NCOL, P_NCOL, SLOT_DEST, PlayerGameEngine  # noqa: E402
from engine.league import build_league  # noqa: E402
from engine.matchup import OUTCOMES  # noqa: E402
from engine.pitch import N_SLOTS, SLOT_SYM, _DEST  # noqa: E402

EVENTS = "BKSFPHN"
MAXP = 12


def chi2_two_sample(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    """Two-sample chi-square on counts (cells with no observations dropped)."""
    a, b = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    keep = (a + b) > 0
    a, b = a[keep], b[keep]
    na, nb = a.sum(), b.sum()
    e_a = (a + b) * na / (na + nb)
    e_b = (a + b) * nb / (na + nb)
    stat = float((((a - e_a) ** 2) / e_a).sum() + (((b - e_b) ** 2) / e_b).sum())
    return stat, int(keep.sum() - 1)


def p_chi2(stat: float, df: int) -> float:
    """Upper tail of chi-square (Wilson-Hilferty normal approximation; no scipy)."""
    from statistics import NormalDist
    if df <= 0:
        return 1.0
    z = ((stat / df) ** (1 / 3) - (1 - 2 / (9 * df))) / np.sqrt(2 / (9 * df))
    return 1 - NormalDist().cdf(z)


class Tally:
    def __init__(self):
        self.out = np.zeros(len(OUTCOMES), np.int64)
        self.end = np.zeros(12, np.int64)
        self.reach = np.zeros(12, np.int64)
        self.npitch = np.zeros(MAXP + 1, np.int64)
        self.ev = np.zeros((12, len(EVENTS)), np.int64)
        self.joint = np.zeros((len(OUTCOMES), MAXP + 1), np.int64)
        self.per_matchup = []

    def add(self, res: int, seq: str):
        self.out[res] += 1
        b = s = 0
        seen = set()
        for c in seq:
            i = b * 3 + s
            seen.add(i)
            self.ev[i, EVENTS.index(c)] += 1
            if c == "B":
                b += 1
            elif c in "KS":
                s += 1
            elif c == "F" and s < 2:
                s += 1
        last = i
        self.end[last] += 1
        for i in seen:
            self.reach[i] += 1
        n = min(len(seq), MAXP)
        self.npitch[n] += 1
        self.joint[res, n] += 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matchups", type=int, default=3000)
    ap.add_argument("--per", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    t0 = time.time()
    cfg = phase2.load()
    rng = np.random.default_rng(a.seed)
    lg = build_league(cfg, np.random.Generator(np.random.PCG64(a.seed)))
    n = len(lg.players)
    eng = PlayerGameEngine(cfg, lg, [[0] * B_NCOL for _ in range(n)], [[0] * P_NCOL for _ in range(n)])
    bats = [p for p in lg.players if p.side == "bat"]
    pits = [p for p in lg.players if p.side == "pit"]
    i_roe, i_out = OUTCOMES.index("ROE"), OUTCOMES.index("OUT")
    assert tuple(OUTCOMES) == tuple(POUT)
    old, new = Tally(), Tally()
    exact_err = 0.0
    gof = {"old": [0.0, 0], "new": [0.0, 0]}
    for _ in range(a.matchups):
        bt, pt = bats[rng.integers(len(bats))], pits[rng.integers(len(pits))]
        eng.neutral = bool(rng.random() < 0.15)
        home_batting = bool(rng.random() < 0.5)
        tm = lg.teams[pt.team]
        x = tm.err_team + sum(eng.err_share.get(p.pos, 0.0) * p.err for p in tm.batters[:9])
        eo = float(np.exp(x + eng.delta["err"])) if eng.fielding_on else 1.0
        # the law both methods must produce: the matchup with the error tilt
        m = eng._pa_law(bt, pt, home_batting, eo)
        qs, h = eng._matchup_chain(bt, pt, home_batting)
        q = eng.pitch.chain(eng.tilt_cache[eng._key(bt, pt, home_batting)])
        cum = eng.pitch.forward(qs, h, m)
        # exact outcome law of the forward chain (no sampling)
        W = np.diff(np.concatenate([np.zeros((12, 1)), np.array(cum)], axis=1), axis=1)
        T = np.zeros((12, 12)); R = np.zeros((12, len(OUTCOMES)))
        for i in range(12):
            for k in range(N_SLOTS):
                d = _DEST[i, k]
                if d >= 0:
                    T[i, d] += W[i, k]
                else:
                    R[i, -1 - d] += W[i, k]
        exact_err = max(exact_err, float(np.abs(np.linalg.solve(np.eye(12) - T, R)[0] - m).max()))
        cat = eng._probs(bt, pt, home_batting)
        p_roe, p_out = eng.roe_cache[eng._key(bt, pt, home_batting)]
        r = p_roe / (p_roe + p_out)
        r2 = r * eo / (1 - r + r * eo)
        oc_old, oc_new = np.zeros(len(OUTCOMES)), np.zeros(len(OUTCOMES))
        for _ in range(a.per):
            # old: outcome first (with the tilt as engine._roe_tilt draws it), then the conditioned sequence
            res = cat.draw(rng.random())
            if res == "ROE" and r2 < r and rng.random() < 1 - r2 / r:
                res = "OUT"
            elif res == "OUT" and r2 > r and rng.random() < (r2 - r) / (1 - r):
                res = "ROE"
            o = OUTCOMES.index(res)
            old.add(o, eng.pitch.sequence(q, o, rng)); oc_old[o] += 1
            # new: forward, one pitch at a time
            i, seq = 0, []
            while True:
                row = cum[i]
                k = min(bisect_right(row, rng.random() * row[-1]), N_SLOTS - 1)
                seq.append(SLOT_SYM[k])
                d = SLOT_DEST[i][k]
                if d < 0:
                    o = -1 - d
                    break
                i = d
            new.add(o, "".join(seq)); oc_new[o] += 1
        for lab, oc in (("old", oc_old), ("new", oc_new)):
            e = m * a.per
            keep = e > 0
            gof[lab][0] += float((((oc - e) ** 2)[keep] / e[keep]).sum())
            gof[lab][1] += int(keep.sum() - 1)
    rows = []
    for name, ta, tb in (("PA outcome", old.out, new.out), ("Count the PA ended at", old.end, new.end), ("Pitches per PA", old.npitch, new.npitch),
                         ("Pitch events by count", old.ev, new.ev), ("Outcome x pitches", old.joint, new.joint)):
        stat, df = chi2_two_sample(ta, tb)
        rows.append({"comparison": name, "chi2": round(stat, 1), "df": df, "p": round(p_chi2(stat, df), 4)})
    N = old.out.sum()
    # count reach: a PA reaches several counts, so each count is its own two-proportion test (Bonferroni over 12)
    from statistics import NormalDist
    pa_, pb_ = old.reach / N, new.reach / N
    pool = (old.reach + new.reach) / (2 * N)
    z = (pa_ - pb_) / np.sqrt(np.maximum(pool * (1 - pool) * 2 / N, 1e-300))
    zmax = float(np.abs(z).max())
    rows.append({"comparison": "Counts reached (largest of 12 two-proportion z; Bonferroni p)", "chi2": round(zmax, 2), "df": 12,
                 "p": round(min(1.0, 12 * 2 * (1 - NormalDist().cdf(zmax))), 4)})
    mean_old = float((old.npitch * np.arange(MAXP + 1)).sum() / N)
    mean_new = float((new.npitch * np.arange(MAXP + 1)).sum() / N)
    gofr = {k: {"chi2": round(v[0], 1), "df": v[1], "p": round(p_chi2(v[0], v[1]), 4)} for k, v in gof.items()}
    out = {"matchups": a.matchups, "pa_per_method": int(N), "seed": a.seed, "exact_outcome_law_max_abs_diff": exact_err,
           "two_sample": rows, "against_exact_law": gofr,
           "pitches_per_pa": {"old": round(mean_old, 4), "new": round(mean_new, 4)},
           "outcome_shares": {"old": dict(zip(OUTCOMES, np.round(old.out / N, 5).tolist())), "new": dict(zip(OUTCOMES, np.round(new.out / N, 5).tolist()))},
           "secs": round(time.time() - t0)}
    (ROOT / "reports/forward_chain_check.json").write_text(json.dumps(out, indent=1) + "\n")
    md = ["# Forward pitch-by-pitch play against outcome-first (engine restructure)", "",
          f"{a.matchups} matchups from a generated league (seed {a.seed}), {a.per} plate appearances each by both methods "
          f"({N:,} per method). Old: outcome drawn first, reached-on-error tilt, then the sequence from the chain "
          "conditioned on the outcome. New: the transformed chain played forward one pitch at a time. See "
          "`scripts/check_forward_chain.py` and `engine/pitch.py`.", "",
          f"Exact (no sampling): the forward chain's outcome law equals the matchup's to {exact_err:.1e} (largest absolute "
          "difference over every matchup and outcome).", "",
          "| Two-sample comparison | Chi-square (or z) | df (or tests) | p |", "|---|---|---|---|"]
    md += [f"| {r['comparison']} | {r['chi2']} | {r['df']} | {r['p']} |" for r in rows]
    md += ["", "| Against the exact law, matchup by matchup (outcome counts) | Chi-square | df | p |", "|---|---|---|---|"]
    md += [f"| {k} | {v['chi2']} | {v['df']} | {v['p']} |" for k, v in gofr.items()]
    md += ["", f"Pitches per PA: old {mean_old:.4f}, new {mean_new:.4f}.", "",
           "| Outcome | Old | New |", "|---|---|---|"]
    md += [f"| {o} | {out['outcome_shares']['old'][o]:.5f} | {out['outcome_shares']['new'][o]:.5f} |" for o in OUTCOMES]
    md += ["", "A p-value is the chance of a difference at least this large if the two methods draw from the same "
           "distribution; small values on several rows would mean they differ.", ""]
    (ROOT / "reports/forward_chain_check.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
