"""The action menu (app/menu.py) offers only engine-legal calls for the side the user is on (owner condition,
UI v2, 2026-10-08).

On games paused at random sim targets, with random menu calls queued along the way:
1. Batting calls appear only when the user's team bats the coming pitch, pitching calls only when it fields it;
   the kinds come from engine.control.DECISIONS.
2. Every enabled item's order validates against the engine's eligibility rules (app.catalogue.to_engine): the
   call itself, and each player the item lets the user pick. A disabled item says why.
3. Steal and hit-and-run appear only when the engine's lead-runner rule allows a steal, and name the runner.
4. Queuing an enabled item (with a random pick) is accepted by the connector, and the game plays on to its end.
5. The API's turn carries the same menu.
"""
from __future__ import annotations

import numpy as np
import pytest

from app import catalogue as cat
from app.connector import GameRunner
from app.menu import menu
from app.world import World
from engine.control import DECISIONS

PAIRS = [(5, 200), (12, 61), (300, 7), (150, 151)]
TARGETS = ("pitch",) * 6 + ("pa",) * 3 + ("half",)      # mostly short steps: many paused states (the game ends on its own)
BATTING_KINDS = {"pre_pitch", "pinch_hit"}
PITCHING_KINDS = {"pre_pitch_defense", "pitching_change", "defensive_subs"}


@pytest.fixture(scope="module")
def world():
    return World()


def _order_value(item, rng):
    """The order an item sends, with a random pick where it needs one."""
    v, pick = item["value"], item["pick"]
    if pick is None:
        return v
    pid = int(rng.choice(pick["options"]))
    slot = int(rng.integers(0, 9))
    if item["kind"] == "pinch_hit":
        return pid
    if item["kind"] == "pitching_change":
        return {"yes": True, "reliever": pid}
    if item["kind"] == "defensive_subs":
        return [[slot, pid]]
    if "pinch_runner" in v:
        return {"pinch_runner": pid, "slot": v["slot"]}
    if "pitching_change" in v:
        return {"pitching_change": pid}
    if "defensive_sub" in v:
        return {"defensive_sub": [slot, pid]}
    raise AssertionError(item)


def _check(r, items):
    st = r.current.st
    user = r.user
    bats_next = (st.batting_side != user) if st.outs >= 3 else (st.batting_side == user)
    kinds = {i["kind"] for i in items}
    assert kinds <= set(DECISIONS)
    if bats_next:
        assert kinds <= BATTING_KINDS and not (kinds & PITCHING_KINDS), items
    else:
        assert kinds <= PITCHING_KINDS and not (kinds & BATTING_KINDS), items
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids))
    sb = cat.steal_base(st) if (bats_next and st.outs < 3) else 0
    assert ("steal" in ids) == bool(sb) and ("hit_and_run" in ids) == bool(sb)
    for i in items:
        if not i["enabled"]:
            assert i["reason"], i
            continue
        d = cat.CATALOGUE[i["kind"]]
        if i["pick"] is None:
            d.to_engine(i["value"], st, user)                       # raises when the engine would refuse it
            if i["id"] in ("steal", "hit_and_run"):
                runner = next(x for x in cat.runners(st, user) if x["base"] == sb - 1)
                assert st.lineup[user][runner["slot"]].name in i["label"]
        else:
            assert i["pick"]["options"], i
            rng = np.random.default_rng(0)
            for pid in i["pick"]["options"]:
                fake = dict(i, pick={"what": i["pick"]["what"], "options": [pid]})
                v = _order_value(fake, rng)
                if i["kind"] == "pitching_change":
                    cat.CATALOGUE["relief_pitcher"].to_engine(v["reliever"], st, user)
                else:
                    d.to_engine(v, st, user)


def test_menu_offers_only_legal_calls_for_the_users_side(world):
    rng = np.random.default_rng(7)
    checked = queued = 0
    seen = set()
    for i, (h, a) in enumerate(PAIRS):
        user = str(rng.choice(["home", "away"]))
        r = GameRunner.new(world, h, a, user, 700 + i)
        assert menu(r) == []                                        # pregame: the lineup panel's job
        r.step("pitch")
        while not r.over:
            items = menu(r)
            if r.turn()["phase"] == "pitch" or r.turn()["phase"] == "boundary":
                _check(r, items)
                checked += 1
                seen.update(x["id"] for x in items if x["enabled"])
                on = [x for x in items if x["enabled"] and not x["default"]]
                if on and rng.random() < .35:
                    item = on[int(rng.integers(0, len(on)))]
                    r.queue(item["kind"], _order_value(item, rng))
                    queued += 1
                    assert any(x["queued"] for x in menu(r) if x["id"] == item["id"]), item
            r.step(TARGETS[int(rng.integers(0, len(TARGETS)))])
        assert r.turn()["phase"] == "over" and menu(r) == []
    assert checked > 200 and queued > 40
    for must in ("swing", "bunt", "steal", "pinch_hit", "pitch", "ibb", "pitchout", "mound_visit", "pitching_change", "defensive_change"):
        assert must in seen, must


def test_api_turn_carries_the_menu(world):
    from fastapi.testclient import TestClient
    from app import api as api_mod
    api_mod.store.world = world
    with TestClient(api_mod.app) as c:
        t = c.post("/api/games", json={"home": 5, "away": 200, "user_side": "home", "seed": 3}).json()
        assert t["menu"] == []
        t = c.post(f"/api/games/{t['game_id']}/sim", json={"target": "pa"}).json()
        r = api_mod.store.games[t["game_id"]]
        assert t["menu"] == menu(r) and t["menu"]
        item = next(x for x in t["menu"] if x["enabled"] and x["pick"] is None and not x["default"])
        t = c.post(f"/api/games/{t['game_id']}/orders", json={"kind": item["kind"], "value": item["value"]}).json()
        assert any(x["queued"] for x in t["menu"] if x["id"] == item["id"])
