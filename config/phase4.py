"""Phase 4 constants: the 20-80 ratings layer.

Ratings are a display and generation layer over the true per-PA rates the engine already
uses (Phase 2). Each rating maps to one true rate (logit offset z) by a monotonic function on
percentiles of the D1 distribution: rating = 50 + 10 * sign * Phi^-1(F(z)), F the PA-weighted
(BF-weighted for pitchers) distribution of true z across all D1 players, so 50 is the D1 median
and each 10 points one standard-normal step in percentile (60, 70, 80 = 84.1st, 97.7th, 99.87th
percentiles), the meaning of 50/60/70/80 under a Gaussian, kept whatever the fitted shapes. They
are relative to all of D1, not to a player's tier. F comes from scripts/build_phase4_scale.py.
Stamina is the pitcher's individual leash: a proportional-hazards multiplier theta on the
pull hazard (h' = 1 - (1 - h)^theta), log theta ~ N(mu, sd^2) by role (starter, reliever),
both fitted by empirical Bayes on the 2025 play-by-play (scripts/build_phase4_inputs.py).
stamina = 50 - 10 * (log theta - mu) / sd (higher stamina, longer leash).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data/ncaa_2025/derived/phase4_inputs_2025.json"
SCALE = ROOT / "data/ncaa_2025/derived/phase4_rating_scale_2025.json"

# (rating, true rate it maps to, sign: +1 if a higher rate is better for the player)
BATTER_RATINGS = (("contact", "BABIP", 1), ("gap", "XBH", 1), ("power", "HR", 1), ("eye", "BB", 1), ("avoid_k", "K", -1))
PITCHER_RATINGS = (("stuff", "K", 1), ("control", "BB", -1), ("movement", "HR", -1))
# Speed has no speed-linked rate in the engine yet (base running is league tables); Phase 6.
RESERVED = {"bat": ("speed",)}
# True components with no rating: batter HBP; pitcher HBP; pitcher BABIP and XBH allowed (team
# defense, rated with fielding in Phase 6). They stay part of the player's true rates.
CENTER = 50
POINTS_PER_SD = 10                         # 10 points per normal score: 60 = 84.1st, 70 = 97.7th, 80 = 99.87th D1 percentile
# The percentile table of each rated rate (scripts/build_phase4_scale.py): z quantiles of the D1
# distribution at normal scores -SCALE_MAX_SCORE..+SCALE_MAX_SCORE, step SCALE_SCORE_STEP, from
# SCALE_LEAGUES generated leagues (about 4,300 batters and 4,000 pitchers each: at 200 leagues the
# outermost table point, p = 1e-5 at score 4.25, still has about 8 batters beyond it).
SCALE_LEAGUES = 200
SCALE_MAX_SCORE = 4.25
SCALE_SCORE_STEP = 0.05
DISPLAY_MIN, DISPLAY_MAX = 20, 80          # displayed ratings are rounded and clipped; the true rating is not
STAMINA_ROLE = {"sp_weekend": "starter", "sp_midweek": "starter", "rp": "reliever"}

# Empirical Bayes estimator (engine/eb.py): grid over the latent offset and EM settings
EB_GRID_HALF_WIDTH = 4                     # logit / log-hazard units
EB_GRID_POINTS = 401                       # step 0.02: fine against the narrowest true spreads (~0.05)
EB_OUTER_ITERS = 3                         # alternations of the tau search and the mu steps
EB_GOLDEN_ITERS = 20                       # golden-section steps on log tau (interval shrinks 0.618^20 ~ 7e-5)
EB_MU_STEPS = 4
EB_FIT_MAX_UNITS = 2500                    # units per group used to fit the prior (random subsample above that)
EB_TAU_START_MIN = 0.1                     # starting prior SD (the search does not depend on it)
EB_QUAD_NODES = 9                          # Gauss-Hermite nodes over the spread of opponents faced

# Qualifying player-seasons for the round trip (tests/test_phase4_gate.py): the forward regression
# of observed on true rates (the gate) and the scouting estimator (informational) both use players
# with at least this many trials. Below roughly half a regular's season a player's observed rate
# says little about his rate (with ~12 hits the binomial noise in extra-base share is ~60 times its
# true spread). 150 PA / 150 BF is about half an everyday player's season.
MIN_TRIALS = {"PA": 150, "BIP": 100, "HITS": 35, "BF": 150, "APPS": 8}
# Scouting estimator (informational, Phase 9): role groups whose prior SD is shared across tiers
# (only the mean differs by tier): bench players' few trials leave a per-tier spread unidentified.
SHARED_TAU_ROLES = ("bench",)
# The round trip is replicated in folds of FOLD_SEASONS seasons (the scouting estimator fits its own
# priors in each); every statistic is the mean and standard error across folds, which for the
# estimator carries the priors' own sampling error.
FOLD_SEASONS = 2
FOLD_WORKERS = 4
# Gate tolerance for statistics replicated over k folds: the Student-t quantile with k - 1 degrees of
# freedom at the coverage of the project's 3-SE convention (two-sided 99.73%), times the SE.
GATE_COVERAGE = 0.9973


def load_stamina() -> dict:
    return json.loads(INPUTS.read_text())["stamina"]


def load_scale() -> dict | None:
    return json.loads(SCALE.read_text())["scale"] if SCALE.exists() else None
