"""The real school identity and report cards (data/schools, engine PR #17) as the app shows them: every sim team
in the picker with its school, conference, tier, location and grades, Omaha Contender regraded from the dynasty's
own draw; the hub carries the user's card. Data only: the engine never reads these files."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import api as api_mod                                   # noqa: E402
from app import schools                                          # noqa: E402
from config import report_cards as rc                            # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(api_mod.app) as c:
        yield c


def test_every_sim_team_has_a_school_and_a_card(client):
    r = client.get("/api/schools").json()
    assert r["available"] and len(r["schools"]) == 307
    assert [s["tid"] for s in r["schools"]] == list(range(307))
    assert all(s["school"] and s["conference"] and s["tier"] in ("p4", "mid", "low") and s["location"] for s in r["schools"])
    assert [c["key"] for c in r["categories"]] == list(rc.CATEGORIES)
    card = schools.report_card(0)
    assert set(card["grades"]) == set(rc.CATEGORIES) and all(g["grade"] in rc.GRADES for g in card["grades"].values())


def test_picker_and_hub_carry_identity_and_regraded_cards(client):
    r = client.post("/api/dynasties", json={"seed": 7}).json()
    teams = r["teams"]
    assert len(teams) == 307 and all(t["school"] and t["location"] and t["grades"] for t in teams)
    tids = [t["tid"] for t in teams]
    d = api_mod.dynasty_api._get(r["id"])
    expected = schools.omaha_grades(d.league.teams)
    assert all(t["grades"]["omaha_contender"] == expected[t["tid"]] for t in teams)
    assert sorted(t["grades"]["omaha_contender"] for t in teams).count("A+") <= 0.04 * 307
    file_grades = {t: schools.report_card(t)["grades"]["program_tradition"]["grade"] for t in tids}
    assert all(t["grades"]["program_tradition"] == file_grades[t["tid"]] for t in teams)   # the other categories are the file's
    h = client.post(f"/api/dynasties/{r['id']}/start", json={"tid": 5}).json()
    assert h["school"]["tid"] == 5 and h["school"]["school"] == schools.school(5)["school"]
    assert h["report_card"]["grades"]["omaha_contender"]["grade"] == expected[5]
    assert h["calendar"]["date0"] == "2025-02-10" and h["calendar"]["opening_day"] == min(g.date for g in d.schedule)
    assert client.get("/api/league").json()["calendar"]["date0"] == "2025-02-10"
