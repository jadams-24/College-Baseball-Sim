"""The hub's Next game card (owner feedback 2026-10-11, dynasty.next_game_json): always the user's next scheduled game,
even days ahead; both teams' records, RPI rank and 20-80 ratings; the date, site, ballpark, conference marker,
series context and head-to-head; the engine's own probable starters on game day and the rotation-order projection
before it, labeled; nothing consumes a draw (the dynasty equality tests hold). The played game stays in recent
results and the schedule (the record the owner saw was a real midweek game played that day)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import api as api_mod                                   # noqa: E402

TID = 99                                                         # Iowa, the owner's dynasty


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    api_mod.dynasty_api.SAVE_DIR = tmp_path_factory.mktemp("saves")
    with TestClient(api_mod.app) as c:
        yield c


def _wait(client, did):
    for _ in range(20000):
        p = client.get(f"/api/dynasties/{did}/progress").json()
        if not p["running"]:
            assert p["error"] is None, p["error"]
            return p["hub"]
        time.sleep(0.05)
    raise AssertionError("the sim did not finish")


def _check_card(g, d, pending):
    assert g["pending"] is pending and g["side"] in ("home", "away") and g["user_side"] == g["side"]
    me = d.tid
    assert (g["home"] if g["side"] == "home" else g["away"]) == me
    for side in ("home", "away"):
        t = g["teams"][side]
        assert t["tid"] == g[side] and t["name"] and t["abbr"] and len(t["record"]) == 2 and len(t["conf_record"]) == 2
        assert 20 <= t["ratings"]["off"] <= 80 and 20 <= t["ratings"]["def"] <= 80
        assert t["me"] == (t["tid"] == me)
    assert g["conf_game"] == (d.real_conf[g["home"]] == d.real_conf[g["away"]])
    if g["stage"] == "regular":
        sch = d.schedule[g["i"]]
        assert int(sch.date) == g["date"] and {int(sch.home), int(sch.away)} == {g["home"], g["away"]}
        if g["weekend"]:
            assert g["series"] and 1 <= g["series"]["game"] <= g["series"]["of"] <= 4
        else:
            assert g["series"] is None
        if g["side"] == "home":
            assert g["venue"] and g["venue"]["kind"] == "home"
    for side in ("home", "away"):
        sp = g["probables"][side]
        if sp is not None:
            assert sp["projected"] is (not pending)
            assert sp["pid"] in {p.pid for p in d.league.players.values()} if hasattr(d.league.players, "values") else True
            assert set(sp["stats"]) >= {"w", "l", "era", "ip", "k", "bb"} and set(sp["ratings"]) == {"stuff", "control", "movement", "stamina"}


def test_card_shows_the_next_game_days_ahead_then_game_day_then_the_game_after(client):
    r = client.post("/api/dynasties", json={"seed": 1}).json()            # seed 1: Iowa's first game is the Tuesday midweek, not canceled
    did = r["id"]
    h = client.post(f"/api/dynasties/{did}/start", json={"tid": TID}).json()
    d = api_mod.dynasty_api._get(did)
    g = h["next_game"]
    assert g is not None and g["date"] >= h["date"]
    _check_card(g, d, pending=False)
    assert all(sp is not None and sp["projected"] for sp in g["probables"].values())      # before game day: rotation-order projections
    n = client.get(f"/api/dynasties/{did}/next_games").json()
    assert n["rows"][0]["i"] == g["i"]                                              # the same game the Next 10 widget lists first
    # game day: the pending game, the engine's own probables
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "game", "pause_mine": True, "stops": []}).status_code == 200
    h = _wait(client, did)
    g = h["next_game"]
    assert g["pending"] is True and h["pending"]["date"] == g["date"] and h["pending"]["home"] == g["home"]
    _check_card(g, d, pending=True)
    if h["pending"].get("probables"):
        for side, sp in h["pending"]["probables"].items():
            if sp:
                assert g["probables"][side]["pid"] == sp["pid"] and g["probables"][side]["projected"] is False
    played_date = g["date"]
    # the game is played: the record moves, the card shows the following game while the hub's date stays on game day
    client.post(f"/api/dynasties/{did}/game/sim")
    h = _wait(client, did)
    assert sum(h["record"]) == 1 and h["date"] == played_date and h["pending"] is None
    assert h["recent"] and h["recent"][0]["date"] == played_date                     # the played game stays visible
    g = h["next_game"]
    assert g is not None and g["date"] > played_date and g["pending"] is False
    _check_card(g, d, pending=False)
    sch = client.get(f"/api/dynasties/{did}/schedule").json()
    assert any(x["date"] == played_date and x["status"] == "played" for x in sch["games"])
    assert "games_played" in h and "games_total" in h                                # the counter lives on (Settings), not in the strip


def test_projection_reads_the_rotation_without_a_draw(client):
    r = client.post("/api/dynasties", json={"seed": 3}).json()
    did = r["id"]
    h = client.post(f"/api/dynasties/{did}/start", json={"tid": TID}).json()
    d = api_mod.dynasty_api._get(did)
    g = h["next_game"]
    if g is None or g["pending"]:
        pytest.skip("no scheduled game ahead on this seed")
    sch = d.schedule[g["i"]]
    for side in ("home", "away"):
        t = d.league.teams[g[side]]
        exp = (list(t.weekend_sp)[min(int(sch.day), len(t.weekend_sp) - 1)] if sch.weekend else (list(t.midweek_sp) or list(t.weekend_sp))[0])
        assert g["probables"][side]["pid"] == exp.pid and g["probables"][side]["projected"]
    again = client.get(f"/api/dynasties/{did}").json()["next_game"]
    assert again["probables"] == g["probables"]                                      # deterministic, nothing drawn
