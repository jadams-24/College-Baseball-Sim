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
