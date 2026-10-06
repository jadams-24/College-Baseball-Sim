"""Per-team controllers (engine restructure, 2026-10-06; CLAUDE.md, in-game management and sim controls).

The game session (engine.game2.GameSession) asks the controller of the side whose decision it is: the batting
side for pinch hitters, pinch runners, steals and bunts; the fielding side for relievers, defensive changes,
intentional walks and pitching changes; each side for its lineup and starting pitcher. A controller is an AI
manager (AIController around a Decider, e.g. engine.manager.Manager) or a human (any object with the same
`answer` method). The session hands every call a random generator positioned by (team, decision kind, plate
appearance, call number) on that team's own keyed stream (engine.rng.KeyedStream): the AI's answer at a point
is a function of the game state and the seed only, whoever answered before. The engine resolves every answer
the same way, whoever gave it.
"""
from __future__ import annotations

DECISIONS = ("lineup", "starting_pitcher", "relief_pitcher", "defensive_subs", "pinch_hit", "pinch_runner",
             "steal_attempt", "bunt", "intentional_walk", "pitching_change")
KIND = {k: i + 1 for i, k in enumerate(DECISIONS)}


class Controller:
    """One team's manager in one game."""

    def answer(self, kind: str, state, rng, *args):
        raise NotImplementedError


class AIController(Controller):
    """The AI manager: a Decider answering with the generator the session positioned for this call."""

    def __init__(self, decider):
        self.dec = decider

    def answer(self, kind: str, state, rng, *args):
        self.dec.rng = rng
        try:
            return getattr(self.dec, kind)(state, *args)
        finally:
            self.dec.rng = None
