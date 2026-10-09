"""Real school names everywhere (owner rule 2026-10-09): every screen's data, rendered through the API, carries the
real school from data/schools (app/schools.py) and never an engine team name in user-facing text. The engine's
own name may appear only under the `engine_name` key (the tooltip's "engine id" line). Engine ids stay the keys
and the saves' content: display only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import api as api_mod                                   # noqa: E402
from app import schools                                          # noqa: E402

TID = 5
ALLOWED_KEYS = {"engine_name"}


@pytest.fixture(scope="module")
def client():
    with TestClient(api_mod.app) as c:
        yield c


def _strings(obj, path=""):
    """Every string in a JSON document with its key path, skipping the allowed engine-id keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ALLOWED_KEYS:
                continue
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def _assert_no_engine_names(doc, engine_names, where):
    hits = [(p, s) for p, s in _strings(doc) if any(n in s for n in engine_names)]
    assert not hits, f"{where}: engine team names in user-facing text: {hits[:5]}"


def _wait(client, did):
    import time
    for _ in range(100000):
        p = client.get(f"/api/dynasties/{did}/progress").json()
        if not p["running"]:
            assert p["error"] is None, p["error"]
            return p["hub"]
        time.sleep(0.05)
    raise AssertionError("the sim did not finish")


def test_every_screen_shows_real_schools_and_no_engine_names(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod.dynasty_api, "SAVE_DIR", tmp_path / "saves")      # the server saves go to a temporary directory
    assert schools.available()
    world = api_mod.store.ready()
    engine_names = [t.name for t in world.league.teams]
    assert len(engine_names) == 307 and all(engine_names)

    # the league and a team page (exhibition flow)
    league = client.get("/api/league").json()
    _assert_no_engine_names(league, engine_names, "/api/league")
    assert league["teams"][TID]["name"] == schools.team_name(TID) and league["teams"][TID]["abbr"]
    _assert_no_engine_names(client.get(f"/api/teams/{TID}").json(), engine_names, "/api/teams")

    # a dynasty: picker, hub, schedule, standings, stats, team stats, roster, postseason, saves
    r = client.post("/api/dynasties", json={"seed": 7}).json()
    did = r["id"]
    dyn_names = [t.name for t in api_mod.dynasty_api._get(did).league.teams]      # the dynasty's own league draw: its own engine names
    engine_names = engine_names + dyn_names
    _assert_no_engine_names(r, engine_names, "POST /api/dynasties")
    assert all(t["name"] == schools.team_name(t["tid"]) for t in r["teams"])
    h = client.post(f"/api/dynasties/{did}/start", json={"tid": TID}).json()
    _assert_no_engine_names(h, engine_names, "start")
    assert h["team"] == schools.team_name(TID) and h["engine_name"] == dyn_names[TID]
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "game", "pause_mine": True}).status_code == 200
    h = _wait(client, did)
    _assert_no_engine_names(h, engine_names, "hub after advance")
    assert h["pending"] is not None
    # the user's game on the manager screen: state, events, box score, then its finish
    t = client.post(f"/api/dynasties/{did}/game/open", json={"modes": {}}).json()
    gid = t["game_id"]
    _assert_no_engine_names(t, engine_names, "game open")
    assert t["state"]["teams"]["home"]["abbr"] and t["state"]["teams"]["home"]["short"]
    t = client.post(f"/api/games/{gid}/sim", json={"target": "three_innings"}).json()
    _assert_no_engine_names(t, engine_names, "game turn")
    _assert_no_engine_names(client.get(f"/api/games/{gid}/box").json(), engine_names, "box")
    _assert_no_engine_names(client.get(f"/api/games/{gid}").json(), engine_names, "game state")
    t = client.post(f"/api/games/{gid}/sim", json={"target": "game"}).json()
    _assert_no_engine_names(t, engine_names, "final turn")
    h = client.post(f"/api/dynasties/{did}/game/finish").json()
    _assert_no_engine_names(h, engine_names, "finish")
    _wait(client, did)
    for route in ("", "/schedule", "/standings", "/stats", f"/teams/{TID}/stats", "/roster", "/postseason", "/games/0"):
        resp = client.get(f"/api/dynasties/{did}{route}")
        if resp.status_code == 200:
            _assert_no_engine_names(resp.json(), engine_names, route or "hub")
    sched = client.get(f"/api/dynasties/{did}/schedule").json()
    played = next(g for g in sched["games"] if g["status"] == "played")
    _assert_no_engine_names(client.get(f"/api/dynasties/{did}/games/{played['i']}").json(), engine_names, "game json")
    st = client.get(f"/api/dynasties/{did}/standings").json()
    assert st["mine"] == schools.conference_of(TID) and all(rw["name"] == schools.team_name(rw["tid"]) for rw in st["conferences"][st["mine"]])
    _assert_no_engine_names(client.get("/api/saves").json(), engine_names, "saves")
    _assert_no_engine_names(client.get(f"/api/dynasties/{did}/save").json()["meta"], engine_names, "save meta")


def test_names_table_covers_every_school_with_unique_abbreviations():
    rows = [schools.display(t) for t in range(307)]
    assert all(r and r["name"] and r["short"] and 2 <= len(r["abbr"]) <= 5 for r in rows)
    assert len({r["abbr"] for r in rows}) == 307
    assert schools.display(5)["name"] == "Alabama A&M"
    guesses = schools.abbreviation_guesses()
    assert all(g["abbr"] for g in guesses)


def test_conference_check_reports_and_never_hides():
    world = api_mod.store.ready()
    chk = schools.conference_check(world.league, {tid: c for tid, (_, c, _) in enumerate(world.cfg.teams)})
    assert chk["engine_conferences"] >= 29
    assert isinstance(chk["mismatches"], list)           # a mismatch is reported in /api/schools, never hidden; it is the engine's to fix
