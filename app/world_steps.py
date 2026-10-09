"""The dynasty's world steps: what the world does on each simulated day, in order.

`Dynasty.advance` runs the registered steps once per calendar day (date 0 is the Monday of the opening week,
`engine/schedule.py`: date = 7 * week + weekday, weekday 0 Monday to 6 Sunday). A step has a name, a cadence (daily,
or weekly on one weekday), an order position and a run function that reads and writes the dynasty's state and
returns the auto-pause events it raised. The loop stops after the step that raised an event whose type is enabled
for the call (the Settings' auto-pauses, plus the call's own target conditions); a step that paused is run again on
the next call, so a step must be resumable within its day (`d1_games` plays whatever is left of today's games).

Registered now: `d1_games`. Later phases register theirs with `register` without changing the loop; the planned
slots below are documented placeholders, not built (owner spec 2026-10-09), each gated on its calendar dates from
the Phase 9 spec (`design/phase9_recruiting.md`, Section 10 and 12.1). The postseason (conference tournaments,
Selection Monday, the bracket) is the engine's World pipeline, replayed over the recorded results by
`Dynasty._run_post`; it follows the day loop once the regular season's last game is played.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# the auto-pause event types the Settings can enable (dynasty.STOPS are the three a longer sim can stop at;
# my_game is pause_mine). Targets add their own conditions: my_game_done (Advance to next game with the AI playing
# it) and week_end (Advance week).
PAUSE_TYPES = ("my_game", "week_end", "postseason", "selection")


@dataclass
class PauseEvent:
    type: str
    message: str
    link: str | None = None          # a screen of the dynasty UI (hub, schedule, postseason, ...) to open

    def as_dict(self) -> dict:
        return {"type": self.type, "message": self.message, "link": self.link}


@dataclass
class StepContext:
    today: int
    enabled: set                     # the pause types this call stops on
    target: str
    progress: Callable | None = None
    worked: bool = False             # set by a step that changed the world today (a day with no work is skipped by "Advance day")

    @property
    def weekday(self) -> int:
        return self.today % 7


@dataclass(frozen=True)
class WorldStep:
    name: str
    cadence: str                     # "daily" | "weekly"
    order: int                       # steps run in ascending order each day
    run: Callable[["Dynasty", StepContext], list] | None = None     # None: a planned slot, documented and not run
    weekday: int | None = None       # weekly steps: 0 Monday .. 6 Sunday
    phase: str = ""                  # the phase that builds it
    gate: str = ""                   # the calendar dates it is gated on (Phase 9 spec)

    @property
    def planned(self) -> bool:
        return self.run is None

    def due(self, today: int) -> bool:
        return self.cadence == "daily" or today % 7 == self.weekday


_REGISTRY: list[WorldStep] = []


def register(step: WorldStep) -> WorldStep:
    if step.cadence not in ("daily", "weekly") or (step.cadence == "weekly") != (step.weekday is not None):
        raise ValueError("a daily step has no weekday; a weekly step has one")
    if any(s.name == step.name for s in _REGISTRY):
        raise ValueError(f"world step {step.name!r} is registered twice")
    _REGISTRY.append(step)
    _REGISTRY.sort(key=lambda s: s.order)
    return step


def steps(include_planned: bool = False) -> list[WorldStep]:
    return [s for s in _REGISTRY if include_planned or not s.planned]


def steps_json() -> list[dict]:
    return [{"name": s.name, "cadence": s.cadence, "weekday": None if s.weekday is None else WEEKDAYS[s.weekday], "order": s.order,
             "planned": s.planned, "phase": s.phase, "gate": s.gate} for s in _REGISTRY]


# ---- registered now ------------------------------------------------------------------------------------
def d1_games(d, ctx: StepContext) -> list:
    """Play every D1 game scheduled today in schedule order, the user's game pausing the loop when my_game is
    enabled (the game is set pending for the user to play or sim; the games behind it are deferred, and the
    background sim plays the ones that do not depend on it, `Dynasty.background_plan`). When the schedule's last
    game is played the regular season is over: the stage moves to the conference tournaments and a postseason
    pause is raised."""
    events = []
    while True:
        i = d.next_index()
        if i is None:
            d.stage = "conf"
            d.pos = len(d.schedule)
            events.append(PauseEvent("postseason", "The regular season is over: the conference tournaments are next.", "postseason"))
            return events
        g = d.schedule[i]
        if int(g.date) > ctx.today:
            return events
        if d.mine(g) and "my_game" in ctx.enabled:
            d.pending = {"i": i, "home": g.home, "away": g.away, "date": g.date, "weekend": g.weekend, "stage": "regular", "neutral": False}
            events.append(PauseEvent("my_game", "Your game is next.", "hub"))
            return events
        d._play(i)
        d.pos = i + 1
        ctx.worked = True
        if ctx.progress:
            ctx.progress(d)
        if d.mine(g) and "my_game_done" in ctx.enabled:
            events.append(PauseEvent("my_game_done", "Your game was played by the AI.", "hub"))
            return events


register(WorldStep("d1_games", "daily", 100, d1_games, phase="Phase 7 (built)",
                   gate="every date with scheduled D1 games, opening week to the regular season's last game"))

# ---- planned slots: documented placeholders, not built -------------------------------------------------
register(WorldStep("recruiting_week", "weekly", 200, None, weekday=0, phase="Phase 9",
                   gate="the NCAA calendar's period for the week: Contact / Quiet / Dead / Recruiting Shutdown (spec Section 10; "
                        "in season Mar 1 - Jul 31 Contact with the May 25 - Jun 1, Jun 20-22 and Jul 3-5 dead periods)"))
register(WorldStep("d2_games", "daily", 110, None, phase="Phase 9 (other levels, spec Section 6)",
                   gate="every date with scheduled D2 games (the D2 world on the same talent scale)"))
register(WorldStep("juco_games", "daily", 120, None, phase="Phase 9 (other levels, spec Section 6)",
                   gate="every date with scheduled JUCO games"))
register(WorldStep("portal_window", "daily", 300, None, phase="Phase 9 (spec Section 7)",
                   gate="Dec 1-15, and the spring window of 30 days from seven days after selections (Jun 1-30 in 2026)"))
register(WorldStep("mlb_draft", "daily", 400, None, phase="Phase 9 (spec Section 8)",
                   gate="the draft's dates in July (a live event), then the signing deadline; the ruleset is selectable"))
register(WorldStep("signing_period", "daily", 500, None, phase="Phase 9",
                   gate="opens the second Wednesday of November at 7 a.m. and stays open (Bylaw 13.02.13.1); Nov 10-13 is a dead period"))
register(WorldStep("roster_cuts", "daily", 600, None, phase="Phase 8",
                   gate="rosters due at 34 the day before the first counted contest or December 1, whichever is earlier"))
register(WorldStep("coaching_carousel", "daily", 700, None, phase="Phase 11",
                   gate="June, after the postseason"))
