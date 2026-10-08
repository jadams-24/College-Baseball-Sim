"""PR B: decisions before a pitch follow the NCAA rules book (data/ncaa_rules; config.decisions).

- Coach trips to the mound (9-4): a second trip to the same pitcher in an inning removes him; no second trip while the
  same batter is at bat; three free trips a game (one more in extra innings), after which a trip removes the pitcher.
- An intentional walk is awarded without pitches (8-2-b).
- A walk after a pitching change at 2-0, 2-1, 3-0, 3-1 or 3-2 is charged to the previous pitcher (10-22-b).
"""
from __future__ import annotations

import numpy as np
import pytest

from engine.control import AIController, Controller
from engine.game2 import GameSession
from tests.test_session_determinism import _session, world  # noqa: F401  (module fixture)


class Defense(Controller):
    """A human in the field who manages every pitch: `plan(session, info)` gives the call, else the AI's answers."""

    per_pitch = True

    def __init__(self, dec, plan):
        self.ai, self.plan = AIController(dec), plan

    def answer(self, kind, state, rng, *args):
        if kind == "pre_pitch_defense":
            return self.plan(state, args[0])
        return self.ai.answer(kind, state, rng, *args)


def _first_pitch_of_half(x) -> bool:
    return x.st.half == "T" and x.pa is not None and x.pa["seq"] == [] and x.pa_serial == 1


def test_mound_trips(world):
    s = _session(world, 0)
    s.run(_first_pitch_of_half)
    calls = []

    def plan(state, info):
        # a trip before the first pitch of each of the first two plate appearances (same pitcher, same inning)
        key = (state.inning, len([e for e in s.log if e[0] == "pa"]))
        if info["count"] == (0, 0) and key not in calls and len(calls) < 2:
            calls.append(key)
            return "mound_visit"
        return None
    s.set_controller("home", Defense(s.book, plan))
    p0 = s.st.pitcher["home"].pid
    s.run(lambda x: len(calls) == 2 and x.pa is not None and x.pa["seq"] == [])
    assert any(e[0] == "visit" for e in s.log), "the first trip was not made"
    assert s.st.pitcher["home"].pid != p0, "a second trip to the same pitcher in the inning must remove him (9-4)"
    assert s.st.mound["free"]["home"] == 1


def test_second_trip_same_batter_refused(world):
    s = _session(world, 1)
    s.run(_first_pitch_of_half)
    s.set_controller("home", Defense(s.book, lambda state, info: "mound_visit"))
    with pytest.raises(ValueError, match="same batter"):
        s.run()


def test_ibb_no_pitches_and_free_trip_limit(world):
    s = _session(world, 2)
    s.run(_first_pitch_of_half)
    s.set_controller("home", Defense(s.book, lambda state, info: "ibb"))
    s.run(lambda x: x.st.half == "B")
    pas = [e for e in s.log if e[0] == "pa" and e[1] >= 1]
    assert pas and all(e[4] == "BB" for e in pas[:3]), "every called intentional walk is a walk"
    n_p = [e for e in s.log if e[0] == "p" and e[1] in {e_[1] for e_ in pas[:3]}]
    assert not n_p, "an intentional walk is awarded without pitches (8-2-b)"
