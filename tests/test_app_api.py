"""The web API (app/api.py) through FastAPI's TestClient (owner conditions, 2026-10-08).

1. A game played through the API with a seed and a sequence of decisions equals the engine run directly with the
   same seed and decisions (the scripted controller of tests/test_app_connector.py).
2. Save and load through the API replays identically: the game is saved at random turns, the server copy
   dropped, the save loaded, and the rest of the script played.
3. The endpoints answer: league, roster, catalogue, coach, box score, modes, an illegal order is a 400, an
   unknown game a 404, a tampered save a 400.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_app_connector import PAIRS, Policy, _scripted_game  # noqa: E402

from app import api as api_mod                                   # noqa: E402
from engine.control import DECISIONS                             # noqa: E402
from engine.game2 import STOPS                                   # noqa: E402

N_GAMES = 4


@pytest.fixture(scope="module")
def client():
    with TestClient(api_mod.app) as c:
        yield c


def _runner(gid):
    return api_mod.store.games[gid]


def _play_script(client, gid, user, rng, save_every=0):
    """Play a game through the API: every kind on 'ask me', the policy answering each question; random sim
    targets; optionally save, drop and reload every `save_every` turns. Returns the final game id."""
    for k in DECISIONS:
        assert client.post(f"/api/games/{gid}/modes", json={"kind": k, "mode": "ask"}).status_code == 200
    t = client.post(f"/api/games/{gid}/sim", json={"target": STOPS[int(rng.integers(0, len(STOPS)))]}).json()
    n = 0
    while t["phase"] != "over":
        n += 1
        if save_every and n % save_every == 0 and t["phase"] != "question":
            sv = client.get(f"/api/games/{gid}/save").json()
            api_mod.store.games.pop(gid)
            assert client.get(f"/api/games/{gid}").status_code == 404
            t = client.post("/api/games/load", json={"save": sv["save"]}).json()
            gid = t["game_id"]
        if t["phase"] == "question":
            kind = t["pending"]["kind"]
            value = Policy.value(kind, _runner(gid).current.st, user)
            t = client.post(f"/api/games/{gid}/decide", json={"kind": kind, "value": value}).json()
        else:
            assert t["state"]["score"] is not None and isinstance(t["events"], list)
            t = client.post(f"/api/games/{gid}/sim", json={"target": STOPS[int(rng.integers(0, len(STOPS)))]}).json()
    return gid


def test_api_game_equals_engine(client):
    rng = np.random.default_rng(11)
    world = api_mod.store.world
    for i, (h, a) in enumerate(PAIRS[:N_GAMES]):
        user = str(rng.choice(["home", "away"]))
        ref = _scripted_game(world, h, a, user, 900 + i, per_window=False)
        t = client.post("/api/games", json={"home": h, "away": a, "user_side": user, "seed": 900 + i}).json()
        assert t["phase"] == "pregame" and t["game_id"]
        gid = _play_script(client, t["game_id"], user, rng)
        assert _runner(gid).base.log == ref, f"game {i}"
        box = client.get(f"/api/games/{gid}/box").json()
        assert box["score"] == _runner(gid).base.st.score and box["feed"][-1]["type"] == "final"


def test_api_save_load_replays(client):
    rng = np.random.default_rng(12)
    world = api_mod.store.world
    for i, (h, a) in enumerate(PAIRS[:N_GAMES]):
        user = "away"
        ref = _scripted_game(world, h, a, user, 950 + i, per_window=False)
        t = client.post("/api/games", json={"home": h, "away": a, "user_side": user, "seed": 950 + i}).json()
        gid = _play_script(client, t["game_id"], user, rng, save_every=13)
        assert _runner(gid).base.log == ref, f"game {i}: a reloaded game diverged"


def test_steal_on_2_0_through_the_api(client):
    """The owner's example through HTTP: at a 2-0 count with the user's runner on first and second open, queue
    'steal' for the coming pitch; the next pitch runs it and the feed says so."""
    for seed in range(1, 60):
        t = client.post("/api/games", json={"home": 5, "away": 200, "user_side": "home", "seed": seed}).json()
        gid = t["game_id"]
        t = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"}).json()
        while t["phase"] != "over":
            st = t["state"]
            if t["phase"] == "pitch" and st["batting_side"] == "home" and st["count"] == [2, 0] and st["bases"][0] and not st["bases"][1]:
                act = next(a for a in t["actions"] if a["kind"] == "pre_pitch")
                assert act["legal"] and act["picks"]["steal_base"] == 2
                t = client.post(f"/api/games/{gid}/orders", json={"kind": "pre_pitch", "value": "steal"}).json()
                assert any(o["kind"] == "pre_pitch" for o in t["orders"])
                t = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"}).json()
                texts = [e["text"] for e in t["events"]]
                assert any(e["type"] == "decision" and e["source"] == "order" and "steal on" in e["text"] for e in t["events"]), texts
                if any(("steals second on the 2-0 pitch" in x) or ("out at second on the 2-0 pitch" in x) for x in texts):
                    return
                break                               # fouled or put in play: try another game
            t = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"}).json()
    pytest.fail("no called steal on a 2-0 ball or strike in the sample")


def test_endpoints(client):
    lg = client.get("/api/league").json()
    assert len(lg["teams"]) == 307 and {"tid", "name", "conference", "tier"} <= set(lg["teams"][0])
    roster = client.get("/api/teams/5").json()
    assert len(roster["batters"]) >= 9 and len(roster["pitchers"]) >= 5 and "contact" in roster["batters"][0]["ratings"]
    assert "hold" in roster["pitchers"][0]["ratings"]
    assert client.get("/api/teams/9999").status_code == 404
    cat = client.get("/api/decisions").json()
    assert [k["kind"] for k in cat["kinds"]] == list(DECISIONS) and cat["stops"] == list(STOPS)
    assert {"pre_pitch", "pre_pitch_defense"} <= {k["kind"] for k in cat["kinds"]}      # PR B's per-pitch decisions
    assert "steal" in next(k for k in cat["kinds"] if k["kind"] == "pre_pitch")["choices"]
    t = client.post("/api/games", json={"home": 5, "away": 200, "user_side": "home", "seed": 3}).json()
    gid = t["game_id"]
    coach = client.get(f"/api/games/{gid}/coach").json()["advice"]
    assert any(a["kind"] == "lineup" and len(a["pids"]) == 9 for a in coach)
    assert any(a["kind"] == "starting_pitcher" and a["name"] for a in coach)
    # the pregame: set the lineup the coach suggests but with the top two swapped, and the second starter
    lineup = next(a["pids"] for a in coach if a["kind"] == "lineup")
    lineup[0], lineup[1] = lineup[1], lineup[0]
    t = client.post(f"/api/games/{gid}/orders", json={"kind": "lineup", "value": lineup}).json()
    assert any(o["kind"] == "lineup" for o in t["orders"])
    sp2 = roster["pitchers"][1]["pid"]
    assert client.post(f"/api/games/{gid}/orders", json={"kind": "starting_pitcher", "value": sp2}).status_code == 200
    assert client.post(f"/api/games/{gid}/orders", json={"kind": "lineup", "value": lineup[:8]}).status_code == 400
    t = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"}).json()
    st = t["state"]
    assert st["lineups"]["home"][0]["pid"] == lineup[0] and st["pitcher"] is not None
    assert [e["type"] for e in t["events"]][:1] == ["decision"] and t["phase"] == "pitch" and st["count"] == [0, 0]
    assert st["batter"]["name"] and st["line_score"]["innings"][:9] == list(range(1, 10))
    # a pitching change with the first reliever, queued now, happens after this plate appearance
    bullpen = st["bullpen"]["home"]
    t = client.post(f"/api/games/{gid}/orders", json={"kind": "pitching_change", "value": {"yes": True, "reliever": bullpen[0]["pid"]}}).json()
    assert {o["kind"] for o in t["orders"]} >= {"pitching_change", "relief_pitcher"}
    t = client.post(f"/api/games/{gid}/sim", json={"target": "pa"}).json()
    assert t["phase"] in ("boundary", "pitch")
    t = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"}).json()
    assert t["state"]["pitcher"]["pid"] == bullpen[0]["pid"]
    assert any(e["type"] == "decision" and e["source"] == "order" for e in client.get(f"/api/games/{gid}?full=1").json()["events"])
    # an illegal order, an unknown game, a tampered save
    assert client.post(f"/api/games/{gid}/orders", json={"kind": "pinch_hit", "value": lineup[0]}).status_code == 400
    assert client.post(f"/api/games/{gid}/orders", json={"kind": "nonsense", "value": "yes"}).status_code == 400
    assert client.get("/api/games/nope").status_code == 404
    sv = client.get(f"/api/games/{gid}/save").json()["save"]
    assert client.post("/api/games/load", json={"save": sv[:-6] + "AAAAAA"}).status_code == 400
    assert client.post("/api/games/load", json={"save": sv}).json()["phase"] in ("pitch", "boundary")
    # ask-me mode blocks with a question; "auto" answers it
    client.post(f"/api/games/{gid}/modes", json={"kind": "pitching_change", "mode": "ask"})
    t = client.post(f"/api/games/{gid}/sim", json={"target": "game"}).json()
    assert t["phase"] == "question" and t["pending"]["kind"] == "pitching_change"
    assert client.post(f"/api/games/{gid}/sim", json={"target": "game"}).status_code == 409
    t = client.post(f"/api/games/{gid}/decide", json={"kind": "pitching_change", "value": "auto"}).json()
    assert t["phase"] in ("question", "over")
    client.post(f"/api/games/{gid}/modes", json={"kind": "pitching_change", "mode": "auto"})
    t = client.post(f"/api/games/{gid}/sim", json={"target": "game"}).json()
    assert t["phase"] == "over" and t["state"]["over"]
    box = client.get(f"/api/games/{gid}/box").json()
    for side in ("away", "home"):
        assert sum(b["line"]["r"] for b in box["batting"][side]) == box["score"][side]
    assert client.get("/").status_code == 200
