"""Samplers over the empirical tables in config. All randomness enters as a uniform
draw passed in by the caller, so the game loop controls the RNG stream."""
from __future__ import annotations

from engine.rng import Categorical


class OutcomeTable:
    """The single league-average PA outcome table, with the in-play-out class
    (IP_OUT + SF + SH) drawn as one bucket and subtyped by state feasibility."""

    def __init__(self, probs: dict[str, float], results: tuple, in_play_class: tuple, subtype_counts: dict):
        self.probs = probs
        labels = [r for r in results if r not in in_play_class] + ["IN_PLAY_OUT"]
        weights = [probs[r] for r in results if r not in in_play_class] + [sum(probs[r] for r in in_play_class)]
        self.full = Categorical(labels, weights)
        self.no_bunt = Categorical(labels, weights)  # SH exclusion handled in subtype step
        self.subtype = {cls: Categorical.from_counts(c) for cls, c in subtype_counts.items()}

    @staticmethod
    def feasibility_class(outs: int, bases: list) -> str:
        if outs < 2 and bases[2]:
            return "on3_lt2"
        if outs < 2 and any(bases):
            return "on_lt2"
        if any(bases):
            return "on_2out"
        return "empty"

    def draw(self, u_result: float, u_sub: float, outs: int, bases: list, allow_bunt: bool = True, force_bunt: bool = False) -> str:
        r = self.full.draw(u_result)
        if r != "IN_PLAY_OUT":
            return r
        cls = self.feasibility_class(outs, bases)
        sub = self.subtype[cls]
        if force_bunt and cls in ("on3_lt2", "on_lt2"):
            return "SH"
        s = sub.draw(u_sub)
        if s == "SH" and not allow_bunt:
            # manager said no bunt: renormalize over the remaining subtypes by re-drawing
            # within the non-SH mass (deterministic transform of the same uniform)
            others = {k: v for k, v in zip(sub.labels, _weights(sub)) if k != "SH"}
            s = Categorical.from_counts(others).draw(u_sub)
        return s


def _weights(cat: Categorical) -> list[float]:
    prev, out = 0.0, []
    for c in cat.cum:
        out.append(c - prev); prev = c
    return out


class AdvancementTable:
    """Joint runner/batter destinations given result and pre-play base-out state."""

    def __init__(self, pa_joint: dict, min_cell_n: int):
        self.min_n = min_cell_n
        self.cells: dict[tuple[str, str], Categorical] = {}
        self.marg: dict[tuple[str, str], Categorical] = {}
        self.fallbacks = {"exact": 0, "pooled_outs": 0, "marginal": 0}
        for res, d in pa_joint.items():
            for key, counts in d.items():
                if "|" in key:
                    if sum(counts.values()) >= min_cell_n:
                        self.cells[(res, key)] = Categorical.from_counts(counts)
                else:
                    self.marg[(res, key)] = Categorical.from_counts(counts)

    def draw(self, res: str, outs: int, base_code: str, u: float, u_more: list[float]) -> tuple[list, str, int]:
        """Return (runner destinations [r1, r2, r3] as str or '', batter destination, errors)."""
        cell = self.cells.get((res, f"{outs}|{base_code}"))
        if cell is not None:
            self.fallbacks["exact"] += 1
        else:
            cell = self.cells.get((res, f"*|{base_code}"))
            if cell is not None:
                self.fallbacks["pooled_outs"] += 1
        if cell is not None:
            r1, r2, r3, b, _outs, err = cell.draw(u).split(",")
            return [r1, r2, r3], b, int(err)
        # independent per-runner marginals (sparse cells only)
        self.fallbacks["marginal"] += 1
        dests = []
        for i, on in enumerate(base_code):
            if on == "1":
                m = self.marg.get((res, f"from{i+1}"))
                dests.append(m.draw(u_more[i]) if m else str(i + 1))
            else:
                dests.append("")
        bm = self.marg.get((res, "batter"))
        b = bm.draw(u_more[3]) if bm else ("0" if res in ("K", "IP_OUT", "SF", "SH") else "1")  # FC/ROE: batter reaches
        return dests, b, 0


class PrePaEventTable:
    """Non-PA base running events (steal attempts, WP, PB, pickoffs, balks, other)
    sampled once before each plate appearance at the empirical per-PA rate."""

    def __init__(self, pre_pa: dict, events: tuple, min_cell_n: int):
        self.events = events
        self.rate: dict[str, Categorical] = {}     # state -> categorical over events + "NONE"
        self.outcome: dict[tuple[str, str], Categorical] = {}
        for key, d in pre_pa.items():
            n_pa = d["n_pa"]
            if n_pa < min_cell_n:
                continue
            weights, labels = [], []
            for et in events:
                c = d["events"].get(et)
                if c:
                    labels.append(et); weights.append(sum(c.values()) / n_pa)
                    self.outcome[(key, et)] = Categorical.from_counts(c)
            labels.append("NONE"); weights.append(max(0.0, 1.0 - sum(weights)))
            self.rate[key] = Categorical(labels, weights)

    def draw_event(self, outs: int, base_code: str, u: float) -> str | None:
        cat = self.rate.get(f"{outs}|{base_code}") or self.rate.get(f"*|{base_code}")
        if cat is None:
            return None
        ev = cat.draw(u)
        return None if ev == "NONE" else ev

    def draw_outcome(self, event: str, outs: int, base_code: str, u: float) -> tuple[list, int, int] | None:
        cat = self.outcome.get((f"{outs}|{base_code}", event)) or self.outcome.get((f"*|{base_code}", event))
        if cat is None:
            return None
        r1, r2, r3, _outs, err = cat.draw(u).split(",")
        return [r1, r2, r3], 0, int(err)
