"""Every choice point in the engine goes through a Decider. The engine never decides;
it asks. Phase 1 has no players, so the only real choices are base-running and
bunting, and the default answer is "behave at league rates"."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class Decision(Enum):
    LEAGUE_RATE = "league_rate"   # let the empirical rate tables decide
    YES = "yes"                   # force the action
    NO = "no"                     # suppress the action


class Decider(ABC):
    """Interface a manager (AI now, human later) implements. `state` is a GameState."""

    @abstractmethod
    def steal_attempt(self, state) -> Decision: ...

    @abstractmethod
    def bunt(self, state) -> Decision: ...

    @abstractmethod
    def intentional_walk(self, state) -> Decision: ...

    @abstractmethod
    def pitching_change(self, state) -> Decision: ...

    @abstractmethod
    def pinch_hitter(self, state) -> Decision: ...

    @abstractmethod
    def lineup(self, state, team: str):
        """Return a lineup for `team` ('away'/'home'); None means no players yet."""

    def starting_pitcher(self, state, team: str):
        """Return the starting pitcher for `team`; None means no players (Phase 1)."""
        return None

    def relief_pitcher(self, state, team: str):
        """Return the reliever who replaces the current pitcher; None means no players."""
        return None

    def pinch_hit(self, state, team: str, slot: int):
        """Return a bench player to bat for lineup slot `slot` now, or None (no change)."""
        return None

    def pinch_runner(self, state, team: str, slot: int):
        """Return a bench player to run for the batter of slot `slot` who just reached base, or None."""
        return None

    def defensive_subs(self, state, team: str) -> list:
        """At the start of a half-inning in the field: [(slot, bench player), ...] to substitute."""
        return []

    def pre_pitch(self, state, info: dict):
        """Before a pitch, the batting side: None, "steal", "hit_and_run", "bunt", "swing" (take the bunt off) or
        ("pinch_runner", slot, bench player). info: count, steal_base (the base the lead runner would steal, 0 if
        none), runner, pitcher (engine.game2 GameSession._pitch)."""
        return None

    def pre_pitch_defense(self, state, info: dict):
        """Before a pitch, the fielding side: None, "pitchout", "intentional_ball", "ibb", "mound_visit",
        ("pitching_change", reliever) or ("defensive_sub", slot, bench player)."""
        return None


class LeagueAverageDecider(Decider):
    """Phase 1 manager: everything at league rates, no substitutions, no players."""

    def steal_attempt(self, state) -> Decision:
        return Decision.LEAGUE_RATE

    def bunt(self, state) -> Decision:
        return Decision.LEAGUE_RATE

    def intentional_walk(self, state) -> Decision:
        return Decision.LEAGUE_RATE  # IBB is inside the table's BB share

    def pitching_change(self, state) -> Decision:
        return Decision.NO  # no pitchers exist in Phase 1

    def pinch_hitter(self, state) -> Decision:
        return Decision.NO

    def lineup(self, state, team: str):
        return None
