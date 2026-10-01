"""20-80 ratings: a display and generation layer over the true per-PA rates (Phase 4).

A player's true rates are logit offsets z (engine.league). Each rating is a linear,
monotonic map of one of them (config.phase4):

    rating = 50 + 10 * sign * (z - m) / s        z = m + sign * (rating - 50) * s / 10

m, s: PA-weighted (BF-weighted) D1 mean and true-talent SD of z (scale file). Rates
without a rating (batter HBP, pitcher HBP, BABIP and XBH allowed) are carried as hidden
components so z is rebuilt exactly from ratings + hidden. Stamina maps to the pitcher's
leash multiplier: log theta = mu_role - (stamina - 50) * tau_role / 10.
True ratings are continuous; the card shows them rounded and clipped to 20-80.
"""
from __future__ import annotations

import numpy as np

from config.phase2 import RATES
from config.phase4 import (BATTER_RATINGS, CENTER, DISPLAY_MAX, DISPLAY_MIN, PITCHER_RATINGS, POINTS_PER_SD, RESERVED, STAMINA_ROLE,
                           load_scale, load_stamina)

IDX = {r: i for i, r in enumerate(RATES)}
DEFS = {"bat": BATTER_RATINGS, "pit": PITCHER_RATINGS}


class RatingScale:
    def __init__(self, scale: dict | None = None, stamina: dict | None = None):
        self.scale = scale if scale is not None else load_scale()
        self.stamina = stamina if stamina is not None else load_stamina()

    def ms(self, side: str, rate: str) -> tuple[float, float]:
        if self.scale is None:          # before scripts/build_phase4_scale.py has run: identity scale
            return 0.0, 1.0
        e = self.scale[side][rate]
        return e["mean"], e["sd"]

    # ---- rates <-> ratings ------------------------------------------------------------
    def split(self, side: str, z: np.ndarray) -> tuple[dict, dict]:
        ratings, rated = {}, set()
        for name, rate, sign in DEFS[side]:
            m, s = self.ms(side, rate)
            ratings[name] = CENTER + POINTS_PER_SD * sign * (z[IDX[rate]] - m) / s
            rated.add(rate)
        hidden = {r: float(z[IDX[r]]) for r in RATES if r not in rated}
        return ratings, hidden

    def compose(self, side: str, ratings: dict, hidden: dict) -> np.ndarray:
        z = np.zeros(len(RATES))
        for name, rate, sign in DEFS[side]:
            m, s = self.ms(side, rate)
            z[IDX[rate]] = m + sign * (ratings[name] - CENTER) * s / POINTS_PER_SD
        for r, v in hidden.items():
            z[IDX[r]] = v
        return z

    def stamina_rating(self, group: str, log_theta: float) -> float:
        p = self.stamina[STAMINA_ROLE[group]]
        return CENTER - POINTS_PER_SD * (log_theta - p["log_mean"]) / p["log_sd"]

    def log_theta(self, group: str, stamina: float) -> float:
        p = self.stamina[STAMINA_ROLE[group]]
        return p["log_mean"] - (stamina - CENTER) * p["log_sd"] / POINTS_PER_SD

    def draw_log_theta(self, group: str, rng: np.random.Generator, n: int) -> np.ndarray:
        p = self.stamina[STAMINA_ROLE[group]]
        return rng.normal(p["log_mean"], p["log_sd"], n)


def display(rating: float | None) -> str:
    if rating is None:
        return "—"
    return str(int(min(max(round(rating), DISPLAY_MIN), DISPLAY_MAX)))


def rating_names(side: str) -> list:
    names = [n for n, _, _ in DEFS[side]]
    return names + (["stamina"] if side == "pit" else list(RESERVED.get(side, ())))
