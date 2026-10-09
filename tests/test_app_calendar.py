"""The one calendar (app/calendar.py): engine dates map to the real calendar with date 0 the Monday of the
opening week, the anchor the engine's own season start, so weekdays and the Phase 9 dates land where they should."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import calendar as cal           # noqa: E402
from app import world_steps as ws         # noqa: E402
from config import phase6                 # noqa: E402


def test_anchor_is_the_engines_season_start():
    assert cal.SEASON_START == dt.date.fromisoformat(phase6.SEASON_START)
    assert cal.DATE0.weekday() == 0 and 0 <= (cal.SEASON_START - cal.DATE0).days <= 6
    assert cal.real_date(0) == dt.date(2025, 2, 10)                    # the Monday of the 2025 opening week


def test_known_dates_land_on_their_weekdays():
    known = [(dt.date(2025, 2, 10), "Monday", 0), (dt.date(2025, 2, 14), "Friday", 4),      # opening day, a Friday
             (dt.date(2025, 5, 26), "Monday", 105),                                           # Selection Monday 2025
             (dt.date(2025, 8, 1), "Friday", 172), (dt.date(2025, 9, 1), "Monday", 203),      # the Phase 9 contact dates
             (dt.date(2025, 11, 12), "Wednesday", 275), (dt.date(2025, 12, 1), "Monday", 294)]
    for real, wd, engine in known:
        assert cal.engine_date(real) == engine
        assert cal.real_date(engine) == real
        assert cal.WEEKDAYS[cal.weekday(engine)] == wd == cal.WEEKDAYS[real.weekday()]
    assert cal.nth_weekday(2025, 11, 2, 2) == dt.date(2025, 11, 12)    # the second Wednesday of November
    assert cal.nth_weekday(2026, 11, 2, 2) == dt.date(2026, 11, 11)
    assert cal.label(4, with_weekday=True) == "Fri Feb 14"


def test_engine_schedule_weekdays_agree_with_the_calendar():
    """The engine's date = 7 * week + weekday (engine/schedule.py): its weekday is the calendar's."""
    for date in range(0, 120):
        assert cal.weekday(date) == cal.real_date(date).weekday() == date % 7


def test_opening_day_comes_from_the_schedule():
    class G:
        def __init__(self, date):
            self.date = date
    assert cal.opening_day([G(11), G(4), G(5)]) == 4
    assert cal.calendar_json([G(4)])["opening_day"] == 4
    assert cal.calendar_json()["date0"] == "2025-02-10"


def test_later_years_keep_date_0_on_a_monday():
    for year in (2, 3, 4):
        d0 = cal.real_date(0, year)
        assert d0.weekday() == 0 and d0.year == 2025 + year - 1
        assert cal.engine_date(d0, year) == 0


def test_world_step_gates_use_the_calendar():
    byname = {s["name"]: s for s in ws.steps_json(1)}
    assert byname["signing_period"]["windows"][0]["start"] == "2025-11-12"       # the second Wednesday of November
    assert byname["portal_window"]["windows"][0] == {"start": "2025-12-01", "end": "2025-12-15", "start_date": 294, "end_date": 308}
    assert byname["recruiting_week"]["windows"][0]["start"] == "2025-08-01"
    assert byname["d1_games"]["windows"] == []
    step = next(s for s in ws.steps(include_planned=True) if s.name == "recruiting_week")
    assert step.due(217, 1) and not step.due(218, 1)                               # Monday Sept 15 2025 is in a contact period; Tuesday is not its day
    assert not step.due(203, 1) and not step.due(0, 1)                             # Monday Sept 1 (quiet period) and February: not contact periods
