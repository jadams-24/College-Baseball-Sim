"""In-game decisions that change outcomes (PR B, owner approval 2026-10-06/07; CLAUDE.md, in-game management).

Fitted inputs: data/ncaa_2025/derived/prb_steals.json (scripts/build_prb_steals.py: steal attempt and success by
count and game state) and data/ncaa_2025/derived/prb_inputs.json (scripts/build_prb_decisions.py: bunts, intentional
walks, the pitcher's hold). Rules: the NCAA baseball rules book (data/ncaa_rules, PHASE0_NOTES).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEALS = ROOT / "data/ncaa_2025/derived/prb_steals.json"
INPUTS = ROOT / "data/ncaa_2025/derived/prb_inputs.json"

FEATURES = {"decisions": True,     # the AI's decisions change outcomes (PR B); off: the PR A engine's league rates
            "steals": True,        # with decisions: steals decided before each pitch (off: the pre-PA steal table)
            "bunts": True,         # with decisions: called bunts with their own pitches and outcomes (off: SH as an out subtype)
            "ibb": True}           # with decisions: intentional walks called and awarded without pitches (off: folded into BB)

# ---- rules (NCAA baseball rules book, data/ncaa_rules/PRMBA_RulesBook.pdf) ----
FREE_TRIPS = 3                  # 9-4-a: free coach trips to the mound (of six defensive charged conferences)
FREE_TRIPS_EXTRA = 1            # 9-4-a: one more in an extra-inning game
IBB_PITCHES = 0                 # 8-2-b: an intentional walk is awarded on the coach's notification, no pitches
WALK_TO_PRIOR = ((2, 0), (2, 1), (3, 0), (3, 1), (3, 2))   # 10-22-b: counts at a pitching change after which a walk is the previous pitcher's

# ---- documented rules where the play-by-play has no data (GUESSES.md) ----
PITCHOUT_SUCCESS_LOGIT = -1.5   # GUESS: a steal on a pitchout succeeds at odds x exp(-1.5) (about .80 -> .47)
BUNT_TWO_STRIKES = "swing"      # GUESS: at two strikes a called bunt is taken off and the batter swings away
HIT_AND_RUN_RUNNER_EXTRA = True # GUESS: on a hit-and-run ball in play the runner from first takes third on a single
                                # and is safe at second on an out (no double play)
MOUND_VISIT_EFFECT = None       # GUESS: a mound visit changes no probability (no data); the rules limits apply
BUNT_CALL_MAX = 0.95            # GUESS: cap on the AI's bunt-call probability (data's bunt rate / chance a called bunt is put in play)


def on(name: str) -> bool:
    """A feature; the three decision kinds are on only with "decisions" on (used to decompose their effects)."""
    if name in ("steals", "bunts", "ibb"):
        return FEATURES.get("decisions", False) and FEATURES.get(name, False)
    return FEATURES.get(name, False)


@lru_cache(maxsize=1)
def load() -> dict:
    return {"steals": json.loads(STEALS.read_text()), **json.loads(INPUTS.read_text())}
