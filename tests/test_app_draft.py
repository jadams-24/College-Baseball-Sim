"""The Draft tab (owner request 2026-10-10, app/prospects.py): the ranking is deterministic for a dynasty and week; the
mock uses each pick slot exactly once with no player picked twice; the draft order matches app/mlb_draft_order_2025.csv;
and the module is display only (no engine or config read)."""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import api as api_mod                                   # noqa: E402
from app import prospects                                        # noqa: E402

TID = 111


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    api_mod.dynasty_api.SAVE_DIR = tmp_path_factory.mktemp("saves")
    with TestClient(api_mod.app) as c:
        yield c


@pytest.fixture(scope="module")
def dyn(client):
    r = client.post("/api/dynasties", json={"seed": 7}).json()
    client.post(f"/api/dynasties/{r['id']}/start", json={"tid": TID})
    return r["id"], api_mod.dynasty_api._get(r["id"])


def _wait(client, did):
    for _ in range(20000):
        p = client.get(f"/api/dynasties/{did}/progress").json()
        if not p["running"]:
            assert p["error"] is None, p["error"]
            return p["hub"]
        time.sleep(0.05)
    raise AssertionError("the sim did not finish")


def test_ranking_is_deterministic_for_a_dynasty_and_week(client, dyn):
    did, d = dyn
    a = prospects.board(d); b = prospects.board(d)
    assert [r[0] for r in a] == [r[0] for r in b] and len(a) == 100
    j1 = client.get(f"/api/dynasties/{did}/draft").json()
    j2 = client.get(f"/api/dynasties/{did}/draft").json()
    assert [r["pid"] for r in j1["board"]] == [r["pid"] for r in j2["board"]] == [r[0] for r in a]
    assert [r["rank"] for r in j1["board"]] == list(range(1, 101))
    assert j1["week"] == j2["week"] and all(r["change"] is None for r in j1["board"])        # week 1: nothing to compare to
    # both sides reach the board; values carry their own units; every player is a real D1 player with a school
    sides = {r["side"] for r in j1["board"]}
    assert sides == {"bat", "pit"}
    assert all(r["school"] and r["abbr"] and r["pos"] and len(r["key_ratings"]) in (3, 4) for r in j1["board"])
    assert all(r["line"] is None for r in j1["board"])                                    # before any game: dashes
    # the same state reloaded from its save gives the same board and keeps the week's snapshot
    sv = client.get(f"/api/dynasties/{did}/save").json()["save"]
    h = client.post("/api/dynasties/load", json={"save": sv}).json()
    d2 = api_mod.dynasty_api._get(h["id"])
    assert [r[0] for r in prospects.board(d2)] == [r[0] for r in a]
    assert d2.board_history == d.board_history and j1["week"] in d2.board_history


def test_mock_uses_each_slot_once_and_no_player_twice(client, dyn):
    did, d = dyn
    j = client.get(f"/api/dynasties/{did}/draft").json()
    picks = j["mock"]["picks"]
    order = prospects.draft_order()
    assert [p["pick"] for p in picks] == [o["pick"] for o in order] == list(range(1, len(order) + 1))
    assert len({p["pid"] for p in picks}) == len(picks)
    assert all(p["board_rank"] <= p["pick"] + prospects.P.MOCK_TOP - 1 for p in picks)       # a small reach, never a deep one
    assert j["mock"]["label"] == "Mock draft: projection, not results"
    again = client.get(f"/api/dynasties/{did}/draft").json()["mock"]["picks"]
    assert [p["pid"] for p in again] == [p["pid"] for p in picks]                            # seeded by dynasty and week


def test_draft_order_matches_the_csv(client, dyn):
    did, d = dyn
    with prospects.ORDER_CSV.open() as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["source"].startswith("https://en.wikipedia.org/wiki/2025_Major_League_Baseball_draft") and r["fetch_date"] for r in rows)
    assert rows[0]["team"] == "Washington Nationals" and rows[0]["round"] == "Round 1"
    assert sum(1 for r in rows if r["round"] == "Round 1") == 27
    assert any(r["round"] == "Competitive Balance Round A" for r in rows)
    picks = client.get(f"/api/dynasties/{did}/draft").json()["mock"]["picks"]
    assert [(p["pick"], p["team"], p["round"]) for p in picks] == [(int(r["pick"]), r["team"], r["round"]) for r in rows]


def test_board_moves_with_the_season_and_the_program_lists_the_users_players(client, dyn):
    did, d = dyn
    before = client.get(f"/api/dynasties/{did}/draft").json()
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "week", "pause_mine": False, "stops": []}).status_code == 200
    _wait(client, did)
    after = client.get(f"/api/dynasties/{did}/draft").json()
    assert after["week"] > before["week"] and after["prev_week"] == before["week"]
    assert any(r["line"] is not None for r in after["board"])
    assert any(isinstance(r["change"], int) and r["change"] != 0 for r in after["board"]) or [r["pid"] for r in after["board"]] != [r["pid"] for r in before["board"]]
    pr = after["program"]
    assert all(r["mine"] and r["tid"] == TID and r["round_range"] for r in pr["players"])
    assert pr["history"] == [] and "carry over" in pr["history_note"]
    assert after["live"]["enabled"] is False and "Phase 9" in after["live"]["text"]
    assert "every D1 player" in after["banner"]


def test_prospects_are_display_only():
    for sub in ("engine",):
        for f in (ROOT / sub).rglob("*.py"):
            txt = f.read_text()
            assert "prospects" not in txt and "from app" not in txt, f
    cfg = (ROOT / "config/prospects.py").read_text()
    assert "GUESS" in cfg and "LINEAR_WEIGHTS" in cfg
