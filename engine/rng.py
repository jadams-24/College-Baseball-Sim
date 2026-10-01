"""Deterministic randomness. One master seed spawns an independent child stream per
game, so game i reproduces exactly regardless of how many games are simulated."""
from __future__ import annotations

from bisect import bisect_right

import numpy as np


def game_seeds(master_seed: int, n_games: int) -> list[np.random.SeedSequence]:
    return np.random.SeedSequence(master_seed).spawn(n_games)


class Categorical:
    """Fixed-order categorical distribution sampled by one uniform draw."""

    __slots__ = ("labels", "cum")

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
