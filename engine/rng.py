"""Deterministic randomness. One master seed spawns an independent child stream per
game, so game i reproduces exactly regardless of how many games are simulated."""
from __future__ import annotations

from bisect import bisect_right

import numpy as np


def game_seeds(master_seed: int, n_games: int) -> list[np.random.SeedSequence]:
    return np.random.SeedSequence(master_seed).spawn(n_games)


class Categorical:
    """Fixed-order categorical distribution sampled by one uniform draw."""

    # split_err / split_ok: lazily cached splits of the cell (engine/tables.py _err_split, _ok_split), kept on the object
    # itself. They were once module dicts keyed by id(cell): CPython reuses the id of a freed object, so a new cell
    # could get a dead cell's split (found 2026-10-09: a fresh-process resume differed in CI after earlier tests had
    # built and freed engines; also any process that builds tables more than once, e.g. a worker's later seasons)
    __slots__ = ("labels", "cum", "split_err", "split_ok")

    def __init__(self, labels: list, weights: list[float]):
        tot = float(sum(weights))
        if tot <= 0:
            raise ValueError("categorical needs positive total weight")
        self.labels = list(labels)
        acc, self.cum = 0.0, []
        for w in weights:
            acc += w / tot
            self.cum.append(acc)
        self.cum[-1] = 1.0

    def draw(self, u: float):
        return self.labels[min(bisect_right(self.cum, u), len(self.labels) - 1)]

    @classmethod
    def from_counts(cls, counts: dict) -> "Categorical":
        items = sorted(counts.items())  # sorted keys => reproducible order
        return cls([k for k, _ in items], [float(v) for _, v in items])


class KeyedStream:
    """A random stream whose draws at a position depend only on (key, position): Philox, counter-based.
    `at(a, b, c)` returns the generator positioned at counter (0, a, b, c); draws then advance the low
    counter word, which never reaches the next position. The game engine and each team's AI manager get
    their own key, so who answers a decision, or how many draws an earlier answer used, never moves a
    later draw (engine.game2.GameSession)."""

    def __init__(self, key):
        self.key = np.asarray(key, dtype=np.uint64)
        self.bg = np.random.Philox(key=self.key)
        self.gen = np.random.Generator(self.bg)
        self._counter = np.zeros(4, dtype=np.uint64)
        # the state template, built once (speed pass, 2026-10-09): setting the state copies these values into the generator
        self._state = {"bit_generator": "Philox", "state": {"counter": self._counter, "key": self.key},
                       "buffer": np.zeros(4, dtype=np.uint64), "buffer_pos": 4, "has_uint32": 0, "uinteger": 0}

    def __getstate__(self):
        return {"key": self.key, "bg": self.bg, "gen": self.gen}

    def __setstate__(self, d):
        self.__init__(d["key"])
        self.bg.state = d["bg"].state

    def at(self, a: int = 0, b: int = 0, c: int = 0) -> np.random.Generator:
        cnt = self._counter
        cnt[1] = a; cnt[2] = b; cnt[3] = c
        self.bg.state = self._state
        return self.gen
