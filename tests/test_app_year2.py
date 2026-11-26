"""Dynasty, the next year (Phase 8: app/dynasty.py new_year on engine/roster.py advance_year).

The offseason after a finished season: every returning player of the user's team is one class up with the same
ratings, leavers' roster slots hold newcomers, the finished year is in the history, the new year has its own
schedule and empty stats and plays, and the dynasty saves and loads. A dynasty whose players carry no class year
(started before Phase 8) cannot advance. The season is cut short here (the stage is set to done after one game):
the full season to Year 2 is the same call.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import dynasty as dm       # noqa: E402
from config import phase2, phase8   # noqa: E402

TID = 120


def test_next_year_turns_the_roster_over_and_plays():
    cfg = phase2.load()
    d = dm.Dynasty(cfg, 7, "t")
    d.start(TID)
    assert all(p.year in phase8.CLASSES for p in d.league.players)
    with pytest.raises(ValueError):
        d.new_year()                                    # the season is not over
    d.set_lineup(d.default_lineup())
    d.advance("game", True)
    d.sim_game()
    d.stage = "done"
    assert dm.summary_json(d)["can_advance"]
    before = {p.uid: (p.year, p.z.copy(), p.pid) for p in d.team.batters + dm.staff(d.team)}
    off = d.new_year()
    assert d.year == 2 and d.stage == "regular" and d.pending is None and not d.results and not d.reg_games
    assert len(d.history) == 1 and d.history[0]["year"] == 1
    now = d.team.batters + dm.staff(d.team)
    back = [p for p in now if p.uid in before]
    assert len(back) + len(off["arrived"]) == len(now) == len(before) and len(off["left"]) == len(off["arrived"]) > 0
    for p in back:
        y0, z0, pid0 = before[p.uid]
        assert phase8.CLASSES.index(p.year) == phase8.CLASSES.index(y0) + 1 and np.array_equal(p.z, z0) and p.pid == pid0
    assert {x[0] for x in off["left"]} == set(before) - {p.uid for p in back}
    assert all(sum(r) == 0 for r in d.bstats) and d.hub()["record"] == [0, 0]
    if d.pref_lineup is not None:                       # kept only when all nine are back
        assert all(d._player(pid).uid in before for pid in d.pref_lineup)
    assert [r["year"] for r in dm.roster_json(d)["batters"]] and dm.lineup_json(d)["next"] is not None
    d.advance("game", True)
    rec = d.sim_game()
    assert rec["hr"] != rec["ar"]
    d2 = dm.load_bytes(cfg, dm.save_bytes(d))
    assert d2.year == 2 and d2.history == d.history and d2.offseason["year"] == 2
    d2.advance("day", False)
    assert len(d2.reg_games) > len(d.reg_games)


def test_a_dynasty_from_before_class_years_cannot_advance():
    cfg = phase2.load()
    d = dm.Dynasty(cfg, 8, "t")
    d.start(5)
    for p in d.league.players:
        p.year = ""
    d.stage = "done"
    assert not dm.summary_json(d)["can_advance"]
    with pytest.raises(ValueError):
        d.new_year()
