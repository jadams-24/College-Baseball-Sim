"""The dynasty's world steps: what the world does on each simulated day, in order.

`Dynasty.advance` runs the registered steps once per calendar day (date 0 is the Monday of the opening week,
`engine/schedule.py`: date = 7 * week + weekday, weekday 0 Monday to 6 Sunday; the real calendar date of an engine
date is `app/calendar.py`, the one mapping every displayed date and every gate below goes through). A step has a name, a cadence (daily,
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

import datetime as dt
from dataclasses import dataclass
from typing import Callable

from app import calendar as cal

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
    gate: str = ""                   # the calendar dates it is gated on (Phase 9 spec), in words
    windows: Callable[[int], list] | None = None     # year -> [(start, end)] engine dates of the gate, through app.calendar; None: always

    @property
    def planned(self) -> bool:
        return self.run is None

    def due(self, today: int, year: int = 1) -> bool:
        if self.cadence == "weekly" and cal.weekday(today) != self.weekday:
            return False
        if self.windows is None:
            return True
        return any(a <= today <= b for a, b in self.windows(year))

    def gate_json(self, year: int = 1) -> list:
        if self.windows is None:
            return []
        return [{"start": cal.real_date(a, year).isoformat(), "end": cal.real_date(b, year).isoformat(), "start_date": a, "end_date": b}
                for a, b in self.windows(year)]


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


def steps_json(year: int = 1) -> list[dict]:
    return [{"name": s.name, "cadence": s.cadence, "weekday": None if s.weekday is None else WEEKDAYS[s.weekday], "order": s.order,
             "planned": s.planned, "phase": s.phase, "gate": s.gate, "windows": s.gate_json(year)} for s in _REGISTRY]


# ---- calendar gates (Phase 9 spec, Section 10 and 12.1), as engine-date windows of a dynasty year through app.calendar ----
def _cal_year(year: int) -> int:
    """The calendar year the dynasty year's season is played in (year 1: the engine's season)."""
    return cal.real_date(0, year).year


def _win(year: int, start: tuple, end: tuple, next_year: bool = False) -> tuple:
    y = _cal_year(year) + (1 if next_year else 0)
    return cal.engine_date(dt.date(y, *start), year), cal.engine_date(dt.date(y, *end), year)


def contact_periods(year: int) -> list:
    """The 2025-26 calendar's Contact periods after the season (the recruiting year that follows dynasty year
    `year`'s season): Aug 1-17, Sept 12 - Oct 12, and Mar 1 - Jul 31 of the next spring (with its dead periods)."""
    return [_win(year, (8, 1), (8, 17)), _win(year, (9, 12), (10, 12)), _win(year, (3, 1), (7, 31), next_year=True)]


def portal_windows(year: int) -> list:
    """December 1-15; the spring window (30 days from seven days after selections) needs the dynasty's
    Selection Monday, so it is added at runtime by the step that owns it."""
    return [_win(year, (12, 1), (12, 15))]


def signing_period(year: int) -> list:
    """Opens the second Wednesday of November and stays open (Bylaw 13.02.13.1): through the next season's start."""
    y = _cal_year(year)
    open_ = cal.nth_weekday(y, 11, 2, 2)
    return [(cal.engine_date(open_, year), cal.engine_date(dt.date(y + 1, 2, 1), year))]


def draft_window(year: int) -> list:
    """July: the draft is a live event on its dates (set when the draft is built, Phase 9) and the signing deadline follows."""
    return [_win(year, (7, 1), (7, 31))]


def roster_cut_day(year: int) -> list:
    """Rosters due at 34 the day before the first counted contest or December 1, whichever is earlier."""
    return [_win(year, (12, 1), (12, 1))]


def carousel(year: int) -> list:
    """June, after the postseason."""
    return [_win(year, (6, 1), (6, 30))]


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
                        "Contact Aug 1-17, Sept 12 - Oct 12 and Mar 1 - Jul 31 with the May 25 - Jun 1, Jun 20-22 and Jul 3-5 dead periods)",
                   windows=contact_periods))
register(WorldStep("d2_games", "daily", 110, None, phase="Phase 9 (other levels, spec Section 6)",
                   gate="every date with scheduled D2 games (the D2 world on the same talent scale)"))
register(WorldStep("juco_games", "daily", 120, None, phase="Phase 9 (other levels, spec Section 6)",
                   gate="every date with scheduled JUCO games"))
register(WorldStep("portal_window", "daily", 300, None, phase="Phase 9 (spec Section 7)",
                   gate="Dec 1-15, and the spring window of 30 days from seven days after selections (Jun 1-30 in 2026)",
                   windows=portal_windows))
register(WorldStep("mlb_draft", "daily", 400, None, phase="Phase 9 (spec Section 8)",
                   gate="the draft's dates in July (a live event), then the signing deadline; the ruleset is selectable",
                   windows=draft_window))
register(WorldStep("signing_period", "daily", 500, None, phase="Phase 9",
                   gate="opens the second Wednesday of November at 7 a.m. and stays open (Bylaw 13.02.13.1); Nov 10-13 is a dead period",
                   windows=signing_period))
register(WorldStep("roster_cuts", "daily", 600, None, phase="Phase 8",
                   gate="rosters due at 34 the day before the first counted contest or December 1, whichever is earlier",
                   windows=roster_cut_day))
register(WorldStep("coaching_carousel", "daily", 700, None, phase="Phase 11",
                   gate="June, after the postseason", windows=carousel))
