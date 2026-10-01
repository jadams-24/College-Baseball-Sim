"""Game state and per-team tallies for the base-out state machine."""
from __future__ import annotations

from dataclasses import dataclass, field

HIT_RESULTS = ("1B", "2B", "3B", "HR")
BASES_FOR_TB = {"1B": 1, "2B": 2, "3B": 3, "HR": 4}


@dataclass
class TeamTally:
    runs: int = 0
    pa: int = 0
    ab: int = 0
    h: int = 0
    tb: int = 0
    bb: int = 0
    hbp: int = 0
    k: int = 0
    hr: int = 0
    sf: int = 0
    sh: int = 0
    roe: int = 0
    fc: int = 0
    sb: int = 0
    cs: int = 0
    errors_committed: int = 0   # by this team's fielders
    lob: int = 0

    def record_pa(self, result: str) -> None:
        self.pa += 1
        if result in ("BB",):
            self.bb += 1
        elif result == "HBP":
            self.hbp += 1
        elif result == "SF":
            self.sf += 1
        elif result == "SH":
            self.sh += 1
        else:
            self.ab += 1
            if result == "K":
                self.k += 1
            elif result in HIT_RESULTS:
                self.h += 1
                self.tb += BASES_FOR_TB[result]
                if result == "HR":
                    self.hr += 1
            elif result == "ROE":
                self.roe += 1
            elif result == "FC":
                self.fc += 1


@dataclass
class GameState:
    inning: int = 1
    half: str = "T"                 # 'T' away bats, 'B' home bats
    outs: int = 0
    bases: list = field(default_factory=lambda: [False, False, False])  # 1st, 2nd, 3rd occupied
    away: TeamTally = field(default_factory=TeamTally)
    home: TeamTally = field(default_factory=TeamTally)
    over: bool = False
    run_rule_in_effect: bool = False
    ended_by_run_rule: bool = False

    @property
    def batting(self) -> TeamTally:
        return self.away if self.half == "T" else self.home

    @property
    def fielding(self) -> TeamTally:
        return self.home if self.half == "T" else self.away

    @property
    def base_code(self) -> str:
        return "".join("1" if b else "0" for b in self.bases)

    @property
    def state_key(self) -> str:
        return f"{self.outs}|{self.base_code}"

    @property
    def margin_home(self) -> int:
        return self.home.runs - self.away.runs
