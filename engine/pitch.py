"""Pitch-by-pitch (Phase 5): each plate appearance decomposed into pitches.

The PA outcome is drawn first, from the unchanged matchup model (engine.matchup), so every
PA-level rate is exactly the Phase 4 rate. The pitch sequence is then drawn from a count-state
pitch chain conditioned on that outcome.

Chain. At each count (balls 0-3, strikes 0-2) the next pitch is one of B ball, K called strike,
S swinging strike, F foul, P in play, H hit by pitch, N a pitch with no ball/strike call (the
feed's mid-sequence P; it leaves the count unchanged). League probabilities by count come from
the 2025 play-by-play (config.phase5). A ball in play at count c ends in HR/1B/2B/3B/ROE/OUT with
the data's shares for contact at that count. The matchup tilts three events at every count:
balls by the walk offset (pitcher Control vs batter Eye), swinging strikes by the strikeout
offset (Stuff vs Avoid K), HBP by the HBP offset. The tilt sizes solve J t = d, with d the
matchup's K, BB and HBP logits minus the untilted chain's (the data's league average) and J the
chain's Jacobian of those logits in the tilts: the chain alone then reproduces each matchup's
K, BB and HBP rates to first order.

Conditioning (exact). With h_o(c) the chain's probability of ending in outcome o from count c, the
chain conditioned on ending in o is again a chain (Doob h-transform): from c, an event leading to
c' has probability q(c, e) h_o(c') / h_o(c); repeat pitches (fouls with two strikes, N) keep their
probability. So the sequence follows the pitch chain exactly given the outcome, and the outcome
follows the PA model exactly.
"""
from __future__ import annotations

import numpy as np

from config.phase5 import BIP_RESULTS, EVENTS, OUTCOMES, TILT_STEPS, TILTED

COUNTS = [(b, s) for b in range(4) for s in range(3)]
CI = {c: i for i, c in enumerate(COUNTS)}
ORDER = sorted(COUNTS, key=lambda c: -(c[0] + c[1]))    # every transition raises balls + strikes
B_, K_, S_, F_, P_, H_, N_ = (EVENTS.index(e) for e in ("B", "K", "S", "F", "P", "H", "N"))
TILT_COL = [EVENTS.index(TILTED[o]) for o in ("K", "BB", "HBP")]
O_K, O_BB, O_HBP = OUTCOMES.index("K"), OUTCOMES.index("BB"), OUTCOMES.index("HBP")
BIP_OF = {OUTCOMES.index(o): BIP_RESULTS.index(o) for o in BIP_RESULTS}


def _logit(p):
    return np.log(p / (1 - p))


class PitchModel:
    def __init__(self, data: dict, league_p: dict | None = None):
        ch = data["chain"]
        assert tuple(ch["events"]) == EVENTS and tuple(ch["bip_results"]) == BIP_RESULTS
        self.q0 = np.array([ch["by_count"][f"{b}-{s}"] for b, s in COUNTS], float)
        self.r = [list(map(float, ch["bip_by_count"][f"{b}-{s}"])) for b, s in COUNTS]
        # tilts are measured from the chain's own league outcome mix (the data's league average)
        self.base = self._logit_abs(np.zeros(3))
        eps = 1e-4
        J = np.zeros((3, 3))
        for j in range(3):
            tp, tm = np.zeros(3), np.zeros(3)
            tp[j], tm[j] = eps, -eps
            J[:, j] = (self._logit_abs(tp) - self._logit_abs(tm)) / (2 * eps)
        self.J = J
        self.Jinv = np.linalg.inv(J)
        self.chain_league = self.absorb_all(self.chain(np.zeros(3)))[CI[(0, 0)]]

    # ---- the chain -----------------------------------------------------------------------
    def chain(self, t: np.ndarray) -> list:
        q = self.q0.copy()
        q[:, TILT_COL] *= np.exp(t)[None, :]
        q /= q.sum(axis=1, keepdims=True)
        return q.tolist()

    def tilts(self, p_k: float, p_bb: float, p_hbp: float) -> np.ndarray:
        """Tilts at which the chain's own K, BB and HBP rates equal the matchup's: a first-order
        step from the league, then quasi-Newton steps with the same Jacobian."""
        target = _logit(np.array([p_k, p_bb, p_hbp]))
        t = self.Jinv @ (target - self.base)
        for _ in range(TILT_STEPS):
            t = t + self.Jinv @ (target - self._logit_abs3(t))
        return t

    def _logit_abs3(self, t) -> np.ndarray:
        q = self.chain(t)
        return _logit(np.array([self.absorb(q, O_K)[0], self.absorb(q, O_BB)[0], self.absorb(q, O_HBP)[0]]))

    def _logit_abs(self, t) -> np.ndarray:
        a = self.absorb_all(self.chain(t))[CI[(0, 0)]]
        return _logit(np.array([a[O_K], a[O_BB], a[O_HBP]]))

    def absorb(self, q: list, o: int) -> list:
        """h_o(c): probability of ending in outcome o from each count."""
        j = BIP_OF.get(o, -1)
        is_k, is_bb, is_hbp = float(o == O_K), float(o == O_BB), float(o == O_HBP)
        h = [0.0] * 12
        for b, s in ORDER:
            i = b * 3 + s
            qs = q[i]
            stay = qs[N_] + (qs[F_] if s == 2 else 0.0)
            tot = qs[B_] * (h[i + 3] if b < 3 else is_bb)
            tot += (qs[K_] + qs[S_]) * (h[i + 1] if s < 2 else is_k)
            if s < 2:
                tot += qs[F_] * h[i + 1]
            if j >= 0:
                tot += qs[P_] * self.r[i][j]
            tot += qs[H_] * is_hbp
            h[i] = tot / (1.0 - stay)
        return h

    def absorb_all(self, q: list) -> np.ndarray:
        return np.array([self.absorb(q, o) for o in range(len(OUTCOMES))]).T     # (12 counts, outcomes)

    # ---- one plate appearance --------------------------------------------------------------
    def sequence(self, q: list, o: int, rng) -> str:
        """The pitch sequence of a PA that ends in outcome o (one uniform draw per pitch)."""
        h = self.absorb(q, o)
        j = BIP_OF.get(o, -1)
        b = s = 0
        out = []
        while True:
            i = b * 3 + s
            qs = q[i]
            stay = qs[N_] + (qs[F_] if s == 2 else 0.0)
            u = rng.random()
            if u < stay:
                out.append("N" if u < qs[N_] else "F")
                continue
            target = (u - stay) / (1.0 - stay) * h[i] * (1.0 - stay)
            # non-repeat events with weight q(c, e) * h_o(next): they sum to h_o(c) (1 - stay)
            nb = h[i + 3] if b < 3 else float(o == O_BB)
            ns = h[i + 1] if s < 2 else float(o == O_K)
            opts = (("B", qs[B_] * nb), ("K", qs[K_] * ns), ("S", qs[S_] * ns), ("F", qs[F_] * h[i + 1] if s < 2 else 0.0),
                    ("P", qs[P_] * self.r[i][j] if j >= 0 else 0.0), ("H", qs[H_] * float(o == O_HBP)))
            acc, sym = 0.0, None
            for e, w in opts:
                if w > 0.0:
                    acc += w
                    sym = e
                    if target < acc:
                        break
            out.append(sym)
            if sym == "B":
                if b == 3:
                    return "".join(out)
                b += 1
            elif sym in ("K", "S"):
                if s == 2:
                    return "".join(out)
                s += 1
            elif sym == "F":
                s += 1
            else:            # P or H end the plate appearance
                return "".join(out)
