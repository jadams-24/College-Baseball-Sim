"""Phase 5 constants: pitch-by-pitch.

Inputs come from data/ncaa_2025/derived/phase5_pitch_2025.json (scripts/build_phase5_benchmarks.py):
pitch events by count before the pitch (B ball, K called strike, S swinging strike, F foul, P in
play, H hit by pitch, N a pitch with no ball/strike call recorded), batted-ball results by the
count of contact, and the pitch-level benchmarks. The WMT play-by-play has no pitch type,
velocity or location, so none of those exist in the model.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PITCH = ROOT / "data/ncaa_2025/derived/phase5_pitch_2025.json"

EVENTS = ("B", "K", "S", "F", "P", "H", "N")
BIP_RESULTS = ("HR", "1B", "2B", "3B", "ROE", "OUT")
# PA outcomes the pitch chain is conditioned on (the engine's outcome classes; in-play outs of
# every subtype are OUT)
OUTCOMES = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")
# Player tilts of the pitch events (logit shifts on one event's probability at every count):
# the walk offset (Control vs Eye) moves balls, the strikeout offset (Stuff vs Avoid K) moves
# swinging strikes, the HBP offset moves HBP. Their strength is not a guess: engine/pitch.py sets
# it from the chain's own Jacobian, so the chain alone reproduces each matchup's K, BB and HBP
# rates to first order (the conditioning on the drawn outcome makes it exact).
TILTED = {"K": "S", "BB": "B", "HBP": "H"}
# Pitch counts per PA are recorded up to this length for the distribution (longer PAs pool in the last bin)
MAX_PITCHES_HIST = 10


def load() -> dict:
    return json.loads(PITCH.read_text())
