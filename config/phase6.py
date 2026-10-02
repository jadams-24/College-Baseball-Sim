"""Phase 6 constants: fielding, parks, fatigue, bullpen, manager AI.

Inputs come from data/ncaa_2025/derived/phase6_inputs_2025.json (scripts/build_phase6_*.py), built
from the 2025 WMT play-by-play (data/ncaa_2025/pbp) and the full-season scoreboard. Anything else
is marked # GUESS and listed in GUESSES.md.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS6 = ROOT / "data/ncaa_2025/derived/phase6_inputs_2025.json"

# Teams with this many games in the play-by-play sample have (nearly) their whole season: the
# same cut as Phase 2 (scripts/build_phase2_benchmarks.FULL_SEASON_GAMES). Usage dynamics
# (rest, who pitches when) need complete game logs.
FULL_SEASON_GAMES = 40

# Staff roles of the engine (config.phase2 roster shape): weekend rotation, midweek starters,
# relievers ranked by relief work; the 8th and deeper real relievers pool into r8.
N_ROLE_RELIEVERS = 8
ROLES = ("wk1", "wk2", "wk3", "mid1", "mid2") + tuple(f"r{k}" for k in range(1, N_ROLE_RELIEVERS + 1))

# Rest state of a pitcher before a game: days since his last appearance; for 1-3 days, split by the
# pitches of that outing at these bounds (<=15, 16-30, 31-50, 51+). 6+ days (or no appearance yet)
# is the reference.
PITCH_BINS = (15, 30, 50)            # GUESS (bin edges; the fitted effects come from the data)
REST_SPLIT_DAYS = (1, 2, 3)

# Leverage of a relief entry, from the pitching team's side: a blowout is a margin of this many runs
# or more; late and close is this inning or later with a margin within LEVERAGE_CLOSE.
LEVERAGE_BLOWOUT = 7                 # GUESS (bin edge)
LEVERAGE_LATE_INNING = 7             # GUESS (bin edge)
LEVERAGE_CLOSE = 3                   # GUESS (bin edge; a save situation is up to 3 runs)

# Ridge penalty on the usage choice logits (a N(0, 1/0.01) = N(0, 10^2) prior on each coefficient):
# keeps cells that are (almost) never chosen, such as a reliever on one day's rest after 50+ pitches,
# at a large finite negative value instead of minus infinity. Numerical, not a baseball rate.
CLOGIT_RIDGE = 0.01

# Season calendar of the 2025 data: opening day (the first D1 games, benchmarks game_structure.
# season_window); season week = days since it // 7. Starter leash by week bin: weeks [0, 2), [2, 4),
# [4, 7), [7, 10), [10, ...).
SEASON_START = "2025-02-14"
WEEK_BINS = (0, 2, 4, 7, 10)         # GUESS (bin edges; the fitted effects come from the data)


# Substitution hazards (scripts/build_phase6_subs.py): inning bins [1, 6), 6, 7, 8, 9+ and margin bins
# (from the substituting team's side) <=-7, -6..-4, -3..-1, 0, 1..3, 4..6, >=7; a cell with fewer
# opportunities than MIN_SUB_CELL backs off to its inning bin.
INNING_BINS = (1, 6, 7, 8, 9)        # GUESS (bin edges; the hazards come from the data)
MARGIN_BINS = (-99, -6, -3, 0, 1, 4, 7)
MIN_SUB_CELL = 200                   # GUESS (statistical threshold)

# Parks (scripts/build_phase6_parks.py): parks with fewer home games than this in the box-score
# sample are left out of the composition estimate.
MIN_PARK_GAMES = 5                   # GUESS (statistical threshold)

# Fielding and speed (scripts/build_phase6_fielding.py): a fielder needs this many chances (balls hit
# to his zone for range) to enter the method of moments; a runner or catcher this many opportunities.
MIN_FIELD_CHANCES = 30               # GUESS (statistical threshold)
MIN_RUNNER_OPP = 10                  # GUESS (statistical threshold)

# Phase 6 mechanisms, switchable one by one so each one's effect on the gate rows can be measured
# (scripts set FEATURES[...] = False for an ablation run; the engine reads it at season start).
FEATURES = {"calendar": True, "bullpen": True, "leash": True, "subs": True, "parks": True, "fielding": True, "speed": True}

_CACHE: dict = {}


def load() -> dict:
    if "inputs" not in _CACHE:
        _CACHE["inputs"] = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    return _CACHE["inputs"]


def on(feature: str) -> bool:
    return bool(FEATURES.get(feature)) and bool(load())
