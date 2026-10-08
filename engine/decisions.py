"""The fitted decision models (PR B): steal attempt and success by count and game state, the AI's bunt and
intentional-walk rates, a called bunt's pitches and outcome, and the pitcher's hold. Read by the engine (to resolve
a decision, and to keep every plate-appearance rate at the data's when the AI decides) and by the AI manager (to
decide). Inputs: config.decisions.
"""
from __future__ import annotations

import numpy as np

from engine.rng import Categorical

COUNTS = [(b, s) for b in range(4) for s in range(3)]
CI = {c: i for i, c in enumerate(COUNTS)}
BUNT_EVENTS = "BKSFPHN"
BUNT_RES_CLASS = {"SH": "OUT", "IP_OUT": "OUT", "FC": "OUT", "SF": "OUT", "1B": "1B", "2B": "2B", "ROE": "ROE"}


def _expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def _bucket(v, buckets) -> int:
    for k, (lo, hi) in enumerate(buckets):
        if lo <= v <= hi:
            return k
    return len(buckets) - 1


def base_class(bases) -> int:
    """empty 0, first 1, second 2, first and second 3, third occupied 4 (scripts/build_prb_decisions.py)."""
    on1, on2, on3 = (b is not None for b in bases)
    if on3:
        return 4
    return {(False, False): 0, (True, False): 1, (False, True): 2, (True, True): 3}[(on1, on2)]


class DecisionModels:
    def __init__(self, inp: dict):
        st = inp["steals"]
        self.att = dict(zip(st["attempt"]["names"], st["attempt"]["coef"]))
        self.suc = dict(zip(st["success"]["names"], st["success"]["coef"]))
        b = st["buckets"]
        self.lead_b, self.inn_b = [tuple(x) for x in b["lead"]], [tuple(x) for x in b["inning"]]
        bk = inp["buckets"]
        self.slot_g = [tuple(x) for x in bk["slot_groups"]]
        self.base_names = bk["base_classes"]
        self.bunt = dict(zip(inp["bunt_ai"]["names"], inp["bunt_ai"]["coef"]))
        self.ibb = dict(zip(inp["ibb_ai"]["names"], inp["ibb_ai"]["coef"]))
        self.hold = inp["pitcher_hold"]
        # a called bunt's pitches, by count before two strikes
        self.bunt_pitch = {}
        for k, ev in inp["bunt_pitch"]["by_count"].items():
            b_, s_ = (int(x) for x in k.split("-"))
            w = [float(ev.get(e, 0)) for e in BUNT_EVENTS]
            if sum(w) > 0:
                self.bunt_pitch[CI[(b_, s_)]] = Categorical(list(BUNT_EVENTS), w)
        # a bunt in play: result and destinations by outs and bases
        cells = inp["bunt_outcome"]["cells"]
        self.min_cell = inp["bunt_outcome"]["min_cell"]
        self.bunt_cells = {k: Categorical.from_counts(v) for k, v in cells.items() if sum(v.values()) >= self.min_cell or k == "*|*"}
        self._law_cache: dict = {}
        self.slot_bunt, self.slot_ibb = inp["by_slot"]["bunt"], inp["by_slot"]["ibb"]

    # ---- features shared by the models ----
    def _lead(self, st) -> str:
        bat = st.batting_side
        lead = st.score[bat] - st.score["home" if bat == "away" else "away"]
        k = _bucket(lead, self.lead_b)
        return None if k == 2 else f"lead_{self.lead_b[k][0]}_{self.lead_b[k][1]}"

    def _inning(self, st) -> str:
        k = _bucket(st.inning, self.inn_b)
        return None if k == 0 else f"inning_{self.inn_b[k][0]}_{self.inn_b[k][1]}"

    def _slot(self, slot: int) -> str:
        k = _bucket(slot, self.slot_g)
        return None if k == 0 else f"slot_{self.slot_g[k][0]}_{self.slot_g[k][1]}"

    @staticmethod
    def _sum(coef: dict, feats) -> float:
        return coef["intercept"] + sum(coef.get(f, 0.0) for f in feats if f)

    # ---- steals ----
    def steal_logits(self, st, count: tuple, steal_base: int) -> tuple[float, float]:
        """League attempt and success logits for the lead runner on the coming pitch."""
        c = f"count_{count[0]}-{count[1]}"
        outs = f"outs_{st.outs}" if st.outs in (1, 2) else None
        third = "steal_third" if steal_base == 3 else None
        a = self._sum(self.att, (c, outs, third, self._lead(st), self._inning(st)))
        s = self._sum(self.suc, (c, outs, third))
        return a, s

    # ---- bunts and intentional walks: the AI's rates ----
    def bunt_prob(self, st, slot: int) -> float:
        """P(the plate appearance ends in a bunt in play): one cell per outs x occupied bases (what a team bunts for
        depends on both), plus the lead, inning and slot (scripts/build_prb_decisions.py cell_features)."""
        cell = f"cell_{st.outs}|{st.base_code}"
        feats = (cell, self._lead(st), self._inning(st), self._slot(slot))
        return float(_expit(self._sum(self.bunt, feats)))

    def ibb_prob(self, st, slot: int) -> float:
        bc = base_class(st.bases)
        feats = (f"base_{self.base_names[bc]}" if bc else None, "first_open" if st.bases[0] is None else None,
                 f"outs_{st.outs}" if st.outs in (1, 2) else None, self._lead(st), self._inning(st), self._slot(slot))
        return float(_expit(self._sum(self.ibb, feats)))

    # ---- a called bunt ----
    def bunt_outcome(self, outs: int, base_code: str, u: float) -> tuple[str, list, str, int]:
        cell = self.bunt_cells.get(f"{outs}|{base_code}") or self.bunt_cells.get(f"*|{base_code}") or self.bunt_cells["*|*"]
        res, tup = cell.draw(u).split("|")
        r1, r2, r3, b, _outs, err = tup.split(",")
        return res, [r1, r2, r3], b, int(err)

    def slot_shares(self, slot: int) -> tuple[float, float]:
        """The batter's average share of called bunts and of intentional walks in lineup slot `slot` (1-9): the data's
        bunts in play per plate appearance over the chance a called bunt ends in one, and intentional walks per plate
        appearance."""
        _, q = self.bunt_law("*", "*")
        return self.slot_bunt[slot - 1] / max(q, 1e-9), self.slot_ibb[slot - 1]

    def bunt_law(self, outs, base_code) -> tuple[np.ndarray, float]:
        """A called bunt in a base-out state: its outcome law (OUTCOMES order) and the probability q that it ends
        with a bunt in play. Bunt pitches before two strikes (a bunt in play ends it with the bunt table's result),
        then the league chain from the two-strike count (the bunt is taken off, GUESS)."""
        key = (outs, base_code)
        if key in self._law_cache:
            return self._law_cache[key]
        from engine.matchup import OUTCOMES as outcomes
        h_league = self.h_league()
        n_o = len(outcomes)
        cell = self.bunt_cells.get(f"{outs}|{base_code}") or self.bunt_cells.get(f"*|{base_code}") or self.bunt_cells["*|*"]
        p_in = np.zeros(n_o + 1)           # the last entry tracks a bunt in play
        prev = 0.0
        for lab, c in zip(cell.labels, cell.cum):
            res = lab.split("|")[0]
            p_in[outcomes.index(BUNT_RES_CLASS.get(res, "OUT"))] += c - prev
            prev = c
        p_in[n_o] = 1.0
        ext = lambda v: np.concatenate([v, [0.0]])
        unit = lambda o: ext(np.eye(n_o)[outcomes.index(o)])
        law = {}
        for b in (3, 2, 1, 0):
            for s in (1, 0):
                i = CI[(b, s)]
                cat = self.bunt_pitch.get(i)
                if cat is None:
                    law[i] = ext(h_league[i])
                    continue
                pe = dict(zip(cat.labels, np.diff(np.concatenate([[0.0], cat.cum]))))
                stay = pe.get("N", 0.0)
                v = pe.get("B", 0.0) * (law[CI[(b + 1, s)]] if b < 3 else unit("BB"))
                nxt = law[CI[(b, s + 1)]] if s + 1 < 2 else ext(h_league[CI[(b, 2)]])
                v = v + (pe.get("K", 0.0) + pe.get("S", 0.0) + pe.get("F", 0.0)) * nxt
                v = v + pe.get("P", 0.0) * p_in + pe.get("H", 0.0) * unit("HBP")
                law[i] = v / (1.0 - stay)
        v = law[CI[(0, 0)]]
        self._law_cache[key] = out = (v[:n_o], float(v[n_o]))
        return out

    def bunt_call_prob(self, st, slot: int) -> float:
        """The AI's probability of calling a bunt: the data's rate of plate appearances that end in a bunt in play
        (bunt_prob), divided by the chance a called bunt ends in one here (some are walked, struck out, or reach two
        strikes and swing away)."""
        _, q = self.bunt_law(st.outs, st.base_code)
        return min(self.bunt_prob(st, slot) / max(q, 1e-9), 0.95)

    _H = None

    @classmethod
    def h_league(cls) -> np.ndarray:
        """The league pitch chain's absorption probabilities h_o(count), (12, outcomes)."""
        if cls._H is None:
            from config.phase5 import EVENTS, load, load_solved
            from engine.pitch import PitchModel
            pm = PitchModel(load(), load_solved())
            cls._H = pm.absorb_matrix(pm.slots(pm.chain(np.zeros(len(EVENTS)))))
        return cls._H
