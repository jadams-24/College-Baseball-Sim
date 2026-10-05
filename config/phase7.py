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

_CACHE: dict = {}


def load() -> dict:
    if "inputs" not in _CACHE:
        _CACHE["inputs"] = json.loads(INPUTS7.read_text()) if INPUTS7.exists() else {}
    return _CACHE["inputs"]
