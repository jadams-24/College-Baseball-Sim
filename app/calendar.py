"""The one mapping between the engine's dates and the real calendar (owner request 2026-10-09).

The engine counts days from the opening week: a game's date is 7 * week + weekday with weekday 0 Monday to 6 Sunday
(`engine/schedule.py`), so date 0 is the Monday of the opening week. The anchor is the engine's own season start
(`config.phase6.SEASON_START`, the 2025 opening day, a Friday): DATE0 is the Monday of that week, and the opening
day is read from the schedule (the first game's date), never hard-coded. Every displayed date and weekday, and
every world step's calendar gate (`app/world_steps.py`), goes through this module, so the Phase 9 dates (August 1,
September 1, the second Wednesday of November, the portal windows) land on the right days.

The engine's own month lookup (`engine/world.py` `_month`) counts from opening day itself; it is used only to pick
the conference tournament month and is four days off at most, inside the engine: not changed here (the app never
changes the engine).
"""
from __future__ import annotations

import datetime as dt

from config import phase6

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

SEASON_START = dt.date.fromisoformat(phase6.SEASON_START)          # the engine's opening day (2025-02-14, a Friday)
DATE0 = SEASON_START - dt.timedelta(days=SEASON_START.weekday())   # the Monday of the opening week: engine date 0


def real_date(engine_date: int, year: int = 1) -> dt.date:
    """The calendar date of an engine date in dynasty year `year` (year 1 is the engine's season; later years
    are the same grid one calendar year on, so the weekday of each date moves as real years do)."""
    base = DATE0.replace(year=DATE0.year + int(year) - 1)
    base = base - dt.timedelta(days=base.weekday())                 # keep date 0 on a Monday in every year
    return base + dt.timedelta(days=int(engine_date))


def engine_date(real: dt.date, year: int = 1) -> int:
    """The engine date of a calendar date (negative before the opening week; past the season for the offseason)."""
    return (real - real_date(0, year)).days


def weekday(engine_date_: int) -> int:
    """0 Monday .. 6 Sunday: the engine's own convention, equal to the real weekday."""
    return int(engine_date_) % 7


def opening_day(schedule) -> int:
    """The engine date of the first scheduled game: the season's opening day."""
    return int(min(g.date for g in schedule)) if len(schedule) else 0


def nth_weekday(year: int, month: int, wd: int, n: int) -> dt.date:
    """The n-th weekday `wd` (0 Monday) of a month, e.g. the second Wednesday of November."""
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(wd - first.weekday()) % 7 + 7 * (n - 1))


def label(engine_date_: int, year: int = 1, with_weekday: bool = False) -> str:
    d = real_date(engine_date_, year)
    s = f"{MONTHS[d.month - 1]} {d.day}"
    return f"{WEEKDAYS[d.weekday()][:3]} {s}" if with_weekday else s


def calendar_json(schedule=None, year: int = 1) -> dict:
    """What the page needs to format every date itself: date 0's calendar date (ISO) for this year, the opening
    day and the season start the anchor came from."""
    return {"date0": real_date(0, year).isoformat(), "year": int(year), "season_start": SEASON_START.isoformat(),
            "opening_day": opening_day(schedule) if schedule is not None else None, "weekdays": list(WEEKDAYS)}
