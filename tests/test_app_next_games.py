"""The hub's "Next 10 games" widget (owner request 2026-10-10): its rows match the dynasty's schedule exactly (the next
ten unplayed games of the user's team by date, home or away as scheduled, cancellations the engine drew ahead not
revealed) and the opponents' current standings exactly (records and RPI rank as the standings screen has them);
nothing on a row hints at an outcome; the conference-tournament row closes the list when fewer than ten remain."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import api as api_mod                                   # noqa: E402

TID = 5
FORBIDDEN = {"hr", "ar", "result", "status", "canceled", "winner", "inning", "run_rule"}


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


def _check(client, did, d):
    j = client.get(f"/api/dynasties/{did}/next_games").json()
    rows = j["rows"]
    games = [r for r in rows if r["kind"] == "game"]
    # the schedule: the next ten of the user's unplayed games from today, in date order, exactly as scheduled
    today = d.date_now()
    expect = sorted(((int(g.date), i) for i, g in enumerate(d.schedule) if TID in (g.home, g.away) and i not in d.results and int(g.date) >= today))[:10]
    assert [(r["date"], r["i"]) for r in games] == expect
    for r in games:
        g = d.schedule[r["i"]]
        assert r["side"] == ("home" if g.home == TID else "away") and r["opp"]["tid"] == (g.away if g.home == TID else g.home)
        assert r["weekend"] == bool(g.weekend) and r["week"] == int(g.week) + 1
        assert not (set(r) & FORBIDDEN), set(r) & FORBIDDEN                  # nothing hints at an outcome
        assert r["played"] is False
        assert r["conf_game"] == (d.real_conf[g.home] == d.real_conf[g.away])
        assert 20 <= r["ratings"]["off"] <= 80 and 20 <= r["ratings"]["def"] <= 80
        if r["side"] == "home":
            assert r["venue"] and r["venue"]["kind"] == "home"
    # a cancellation the engine drew for a future game is shown as scheduled (not revealed)
    skipped = [r for r in games if d.skip[r["i"]]]
    for r in skipped:
        assert "status" not in r
    # the opponents' standings: records and RPI rank as the standings screen has them
    st = client.get(f"/api/dynasties/{did}/standings").json()
    by_tid = {row["tid"]: row for conf in st["conferences"].values() for row in conf}
    for r in games:
        srow = by_tid[r["opp"]["tid"]]
        assert r["record"] == [srow["w"], srow["l"]] and r["conf_record"] == [srow["cw"], srow["cl"]], (r["opp"], srow)
        assert r["rpi_rank"] == srow["rpi_rank"]
        assert r["opp"]["abbr"] == srow.get("abbr", r["opp"]["abbr"]) and r["opp"]["name"] == srow["name"]
    # probables only on the pending game, never further out
    assert sum(1 for r in games if r["pending"]) <= 1
    # the tail: fewer than ten left means the conference-tournament row closes the list
    if len(games) < 10 and d.stage == "regular":
        assert rows[-1]["kind"] == "conf_tournament" and "bracket set after the regular season" in rows[-1]["text"]
    else:
        assert all(r["kind"] == "game" for r in rows)
    return games


def test_next_games_match_the_schedule_and_the_standings(client):
    r = client.post("/api/dynasties", json={"seed": 7}).json()
    did = r["id"]
    client.post(f"/api/dynasties/{did}/start", json={"tid": TID})
    d = api_mod.dynasty_api._get(did)
    games = _check(client, did, d)                                          # before any game: stats are dashes, ratings carry the row
    assert len(games) == 10 and all(r["line"] is None and r["form"] is None and r["h2h"] is None for r in games)
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "week", "pause_mine": False, "stops": []}).status_code == 200
    _wait(client, did)
    games = _check(client, did, d)
    assert len(games) == 10
    assert any(r["line"] is not None and r["form"] is not None for r in games)   # opponents that have played carry stats
    for r in games:
        if r["form"]:
            w, l = (int(x) for x in r["form"]["last10"].split("-"))
            assert w + l == min(10, r["form"]["g"]) and r["form"]["streak"][0] in "WL"
    # the team line matches the stats screen's players summed (batting average from the same accumulators)
    opp = next(r for r in games if r["line"])
    ts = client.get(f"/api/dynasties/{did}/teams/{opp['opp']['tid']}/stats").json()
    ab = sum(b["stats"]["ab"] for b in ts["batting"]); h = sum(b["stats"]["h"] for b in ts["batting"])
    assert abs(opp["line"]["avg"] - round(h / ab, 3)) < 1e-9
    # late in the regular season: what is there, then the conference-tournament row
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "regular", "pause_mine": False, "stops": []}).status_code == 200
    _wait(client, did)
    j = client.get(f"/api/dynasties/{did}/next_games").json()
    assert j["stage"] != "regular" or (len([x for x in j["rows"] if x["kind"] == "game"]) < 10 and j["rows"][-1]["kind"] == "conf_tournament")
    if j["stage"] != "regular":
        assert len(j["rows"]) == 1 and j["rows"][0]["kind"] == "postseason"
        assert "postseason" in j["rows"][0]["text"].lower() or "bracket" in j["rows"][0]["text"].lower()
