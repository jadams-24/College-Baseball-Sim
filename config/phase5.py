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
SOLVED = ROOT / "data/ncaa_2025/derived/phase5_chain_solved_2025.json"

EVENTS = ("B", "K", "S", "F", "P", "H", "N")
BIP_RESULTS = ("HR", "1B", "2B", "3B", "ROE", "OUT")
# PA outcomes the pitch chain is conditioned on (the engine's outcome classes; in-play outs of
# every subtype are OUT)
OUTCOMES = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")
# Player tilts of the pitch events come from the data (engine/pitch.py): directions measured per
# side (pitcher, batter) for the K and BB offsets, plus a correction solved so the chain's own K, BB
# and HBP rates equal the matchup's. Quasi-Newton steps for that correction after the first step
# (numerical; the conditioning on the drawn outcome makes the PA rates exact regardless).
TILT_STEPS = 2
# Rows reported but gated in Phase 6 (owner decision on PR #7, 2026-10-01; CLAUDE.md deferred rows):
# the pull hazards ignore tier, and low-tier staffs leave midweek starters in longer (manager AI).
DEFERRED_TO_PHASE6 = ("pitches_per_start_midweek_p10",)
# Pitch counts per PA are recorded up to this length for the distribution (longer PAs pool in the last bin)
MAX_PITCHES_HIST = 10


def load() -> dict:
    return json.loads(PITCH.read_text())


def load_solved() -> dict | None:
    """The league base chain solved so the simulated league's pitch events by count equal the data's."""
    return json.loads(SOLVED.read_text()) if SOLVED.exists() else None
