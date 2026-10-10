"""Prospect value constants for the app's Draft tab (owner request 2026-10-10): display only, never read by the engine
or any gated row, and kept in app/ because the app never writes config/ (CLAUDE.md: engine, config and benchmarks are
untouched by the app). The GUESS entries below are listed in app/README.md ("The Draft tab"), not in GUESSES.md, which
belongs to the engine. The Overall rating reuses this later (OVR is on hold, owner); nothing here shows a number as OVR.

Hitters are ranked by expected runs above average per 600 PA, pitchers by runs prevented per 100 IP. Both come
from the player's true rates through the engine's own rating -> rate maps (engine.ratings) and matchup model
(engine.matchup.matchup_probs against a league-average opponent, no park, no platoon), valued with linear weights.

Linear weights: runs per event above an out, MLB-era linear weights (Tango, "The Book"-style), scaled to no league
particular. # GUESS: D1 linear weights would come from the engine's own base-out run expectancy (Phase 1 tables);
these are the standard MLB values until that is derived. Listed in app/README.md.
"""
LINEAR_WEIGHTS = {"BB": 0.69, "HBP": 0.72, "1B": 0.89, "2B": 1.27, "3B": 1.62, "HR": 2.10, "ROE": 0.89, "K": 0.0, "OUT": 0.0}   # GUESS
PA_PER_600 = 600                    # the hitter's season scale (runs above average per 600 PA)
IP_PER_100 = 100                    # the pitcher's season scale (runs prevented per 100 IP)
# The projection blends the rating-based value with the season line as it accumulates: weight PA / (PA + K_OBS)
# on the observed line. # GUESS: a stabilization constant of a full season's plate appearances (hitters) or
# batters faced (pitchers); the empirical-Bayes estimator of Phase 9 replaces it.
K_OBS_BAT = 400                     # GUESS
K_OBS_PIT = 300                     # GUESS
BOARD_SIZE = 100
# Hitters and pitchers merge on one board by percentile within their side (the normal score of the value's rank
# among D1 hitters, or among D1 pitchers), the value breaking ties. # GUESS: the exchange rate between runs above
# average per 600 PA and runs prevented per 100 IP is the Overall rating's to set later; until then neither side
# can crowd the other off the board.
MERGE_BY_SIDE_PERCENTILE = True     # GUESS
# the ratings that matter most by position (display choice): the three or four shown on the board
KEY_RATINGS = {"C": ("contact", "power", "eye", "arm"), "1B": ("contact", "power", "gap", "eye"), "2B": ("contact", "eye", "glove", "speed"),
               "3B": ("contact", "power", "glove", "arm"), "SS": ("contact", "glove", "arm", "speed"), "LF": ("contact", "power", "gap", "speed"),
               "CF": ("contact", "speed", "glove", "gap"), "RF": ("contact", "power", "arm", "gap"), "DH": ("contact", "power", "gap", "eye"),
               "SP": ("stuff", "control", "movement", "stamina"), "RP": ("stuff", "control", "movement")}
# the mock draft's small, labeled randomness: at each slot the pick is drawn from the best available with weight
# exp(-k / MOCK_TAU) on the k-th best (k = 0 the best); MOCK_TOP caps how far down a pick can reach. # GUESS
MOCK_TAU = 1.2                      # GUESS
MOCK_TOP = 5                        # GUESS
PICKS_PER_ROUND = 30                # the round of a board rank beyond the real first-round slots (display)
