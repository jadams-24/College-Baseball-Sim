"""20-80 ratings: a display and generation layer over the true per-PA rates (Phase 4).

A player's true rates are logit offsets z (engine.league). Each rating is a monotonic map of
one of them (config.phase4), on percentiles of the D1 distribution of that true rate:

    rating = 50 + 10 * sign * Phi^-1(F(z))          z = F^-1(Phi(sign * (rating - 50) / 10))

F: the PA-weighted (BF-weighted) D1 distribution of true z, all tiers together, as the league
generator draws it (fitted true-talent shapes included), stored as a quantile table at normal
scores (scale file, scripts/build_phase4_scale.py). So 50 is the D1 median player, 60 the 84th
percentile, 70 the 97.7th and 80 the 99.87th, whatever the shape; for a Gaussian F this is the
linear map 50 + 10 * sign * (z - m) / s. Between table points the map is linear in both
directions (exact inverse); beyond the table it continues the end segments. Rates without a
rating (batter HBP, pitcher HBP, BABIP and XBH allowed) are carried as hidden components so z
is rebuilt exactly from ratings + hidden. Stamina maps to the pitcher's leash multiplier:
log theta = mu_role - (stamina - 50) * tau_role / 10.
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
        """PA-weighted D1 mean and SD of true z (descriptive; the map itself is percentile-based)."""
        if self.scale is None:          # before scripts/build_phase4_scale.py has run: identity scale
            return 0.0, 1.0
        e = self.scale[side][rate]
        return e["mean"], e["sd"]

    def _table(self, side: str, rate: str):
        e = (self.scale or {}).get(side, {}).get(rate, {})
        q = e.get("quantiles")
        if q is None:                   # no quantile table: the linear map on mean and SD
            m, s = self.ms(side, rate)
            return np.array([-1.0, 1.0]), np.array([m - s, m + s])
        return np.asarray(q["normal_scores"], float), np.asarray(q["z"], float)

    def score(self, side: str, rate: str, z):
        """Normal score Phi^-1(F(z)) of true offset(s) z in the D1 distribution."""
        x, y = self._table(side, rate)
        return _interp_ext(z, y, x)

    def offset(self, side: str, rate: str, score):
        """True offset z at normal score(s) score: F^-1(Phi(score))."""
        x, y = self._table(side, rate)
        return _interp_ext(score, x, y)

    def rating(self, side: str, rate: str, sign: int, z):
        return CENTER + POINTS_PER_SD * sign * self.score(side, rate, z)

    # ---- rates <-> ratings ------------------------------------------------------------
    def split(self, side: str, z: np.ndarray) -> tuple[dict, dict]:
        ratings, rated = {}, set()
        for name, rate, sign in DEFS[side]:
            ratings[name] = float(self.rating(side, rate, sign, z[IDX[rate]]))
            rated.add(rate)
        hidden = {r: float(z[IDX[r]]) for r in RATES if r not in rated}
        return ratings, hidden

    def compose(self, side: str, ratings: dict, hidden: dict) -> np.ndarray:
        z = np.zeros(len(RATES))
        for name, rate, sign in DEFS[side]:
            z[IDX[rate]] = float(self.offset(side, rate, sign * (ratings[name] - CENTER) / POINTS_PER_SD))
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


def _interp_ext(v, x: np.ndarray, y: np.ndarray):
    """Piecewise-linear y(v) through the increasing knots (x, y), continued linearly beyond the ends."""
    v = np.asarray(v, float)
    out = np.interp(v, x, y)
    lo, hi = v < x[0], v > x[-1]
    out = np.where(lo, y[0] + (v - x[0]) * (y[1] - y[0]) / (x[1] - x[0]), out)
    out = np.where(hi, y[-1] + (v - x[-1]) * (y[-1] - y[-2]) / (x[-1] - x[-2]), out)
    return out if out.ndim else float(out)
