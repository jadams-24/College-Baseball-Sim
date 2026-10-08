"""Phase 3 constants: handedness and platoon splits (plan approved 2026-10-08, plans/phase3_plan_2026-10-08.md).

Inputs come from data/ncaa_2025/derived/phase3_inputs_2025.json (scripts/build_phase3_hands.py, scripts/build_phase3_platoon.py),
built from the roster aggregates (data/ncaa_2025/roster_aggregates/: counts and shares only, owner decision 2026-10-07) and the
2025 WMT play-by-play. Anything else is marked # GUESS and listed in GUESSES.md.

Design rule (owner, 2026-10-08): no code path reads tier to set handedness. Hands are drawn per player, conditional on talent
and role (pitchers) or position (batters); the tier gradient is a check, not a fit.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data/ncaa_2025/derived/phase3_inputs_2025.json"

FEATURES = {"hands": True,      # players carry a throwing and a batting hand (drawn from their own stream: no other draw moves)
            "platoon": True,    # with hands: matchups shift by the batter's side and the pitcher's hand (centred: league rates kept)
            "usage": True}      # with hands: the AI's pitching changes and pinch hitters by hand (relief_by_hand, pinch_hit_by_hand)

# Engine fielding position -> the roster aggregates' position group (tools/aggregate_rosters.position_group)
POS_GROUP = {"c": "C", "1b": "1B", "2b": "IF", "3b": "IF", "ss": "IF", "lf": "OF", "cf": "OF", "rf": "OF", "dh": "UT/DH"}
BATTER_GROUPS = ("C", "1B", "IF", "OF", "UT/DH")

# The aggregator's talent-bin cuts (tools/aggregate_rosters.py MIN_BF_BIN, MIN_PA_BIN, STARTER_SHARE): the fit reproduces them
MIN_BF_BIN = 30
MIN_PA_BIN = 50
STARTER_SHARE = 0.5
LATE_INNING = 7        # its usage tables' inning buckets, 1-6 and 7+
MIN_SPLIT = 50         # MIN_SPLIT_PA: trials against each hand for a player to enter the individual platoon spread
SPLIT_SMOOTH = 0.5     # the spread's smoothed logit, logit((x + .5) / (n + 1)) (tools/aggregate_rosters.smoothed_logit_var)
K_SHRINK = 50          # its opponent adjustment's shrinkage, n / (n + K_SHRINK); emulated by the fit

# Talent indexes (owner 2026-10-08): pitchers opponent- and platoon-adjusted K-BB per batter faced (run value as a
# sensitivity check); batters linear-weights run value per PA
PITCHER_INDEX = "k_minus_bb"
BATTER_INDEX = "run_value"

# Deconvolution through the observed bins: noise replicates per simulated player (numerical, not a rate)
N_NOISE_REPLICATES = 40
POP_SEEDS = (7001, 7002, 7003, 7004)
PLATOON_SEEDS = (7101, 7102, 7103, 7104)
USAGE_SEEDS = (7201, 7202, 7203, 7204)     # seasons behind each step of the usage solve (scripts/build_phase3_usage.py --solve)   # seasons with hands and usage on, platoon off, behind the platoon fit   # seasons of the engine (hands off) that give the talent and playing-time population


def on(name: str) -> bool:
    """A feature; platoon and usage are on only with hands on."""
    if name in ("platoon", "usage"):
        return FEATURES.get("hands", False) and FEATURES.get(name, False)
    return FEATURES.get(name, False)


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(INPUTS.read_text()) if INPUTS.exists() else {}
