"""Phase 7 constants: season/world (cancellations, conference tournaments, RPI, selection, the NCAA
tournament).

Inputs come from data/ncaa_2025/derived/phase7_inputs.json (scripts/build_phase7_*.py), built from the
scoreboard feed 2015-2025 (data/ncaa_<season>/scoreboard), the published brackets
(data/ncaa_brackets) and conference tournament formats (data/conf_tournaments). Anything else is
marked # GUESS and listed in GUESSES.md.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS7 = ROOT / "data/ncaa_2025/derived/phase7_inputs.json"

# NCAA Division I baseball RPI (adopted for baseball in 2013; the NCAA's published method): RPI =
# 0.25 WP + 0.50 OWP + 0.25 OOWP over Division I games only. WP weights each result by site: a home
# win counts 0.7 and a road win 1.3, a home loss 1.3 and a road loss 0.7, neutral-site games 1.0.
# OWP is each opponent's unweighted winning percentage with its games against the team removed,
# averaged over the team's games; OOWP is the average of the opponents' OWP, likewise.
RPI_WEIGHTS = (0.25, 0.50, 0.25)
RPI_SITE_WEIGHT = {"home_win": 0.7, "road_win": 1.3, "home_loss": 1.3, "road_loss": 0.7, "neutral": 1.0}

# Benchmarks (scripts/build_phase7_benchmarks.py): a season's feed is used for standings only when at most this share of
# its regular-season entries lacks a result (2015, 2016 and 2021 fail it).
MAX_UNRESOLVED = 0.05                # GUESS (data-coverage threshold)

# Tournament pitching (scripts/build_phase7_usage.py): starts on or after this date in the 2025 play-by-play are
# conference tournament or NCAA tournament starts (the Tuesday of conference tournament week).
TOURNAMENT_START = "2025-05-20"

# Season calendar: day 0 is opening day (config.phase6.SEASON_START, the 2025 opening day). After the last
# regular-season game (day D) the 2025 calendar puts conference tournaments from D + 3 (Tue May 20 after the
# final series ended Sat May 17), regionals from D + 13 (Fri May 30), super regionals from D + 20 (Fri Jun 6)
# and the College World Series from D + 27 (Fri Jun 13). Selection Monday was May 26.
SEASON_START = "2025-02-14"
POST_OFFSETS = {"conf": 3, "regional": 13, "super": 20, "cws": 27}
FIELD_SIZE = 64                      # NCAA Division I baseball championship field (bracketing principles)
N_NATIONAL_SEEDS = 16                # national seeds since 2018 (bracketing principles, 2025 manual)
FEATURES = {"world": True}           # scripts set FEATURES["world"] = False for a regular season only

# RPI gate row (reports/phase7.md): the computed RPI ranks must agree with the NCAA's published pre-selection ranks
# (2026) at least this well (rank correlation). The check gives .99994; site labels of a few dozen games (conference
# tournaments at a member's park) and 7 tie games account for the rest.
RPI_MIN_SPEARMAN = 0.999             # GUESS (acceptance threshold)

_CACHE: dict = {}


def load() -> dict:
    if "inputs" not in _CACHE:
        _CACHE["inputs"] = json.loads(INPUTS7.read_text()) if INPUTS7.exists() else {}
    return _CACHE["inputs"]


def on(feature: str) -> bool:
    return bool(FEATURES.get(feature)) and bool(load())
