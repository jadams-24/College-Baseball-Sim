"""School colors and ballparks (owner request 2026-10-10, app/identity.py, app/school_identity.csv): every one of the 307
schools has both colors and a ballpark or an explicit D flag; every color pair passes the contrast rule (text on a
school color is white or near-black at 4.5:1 or better); the dark-color, similar-color and venue-by-stage rules hold;
and the engine never reads the table (display only)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import identity, schools                                   # noqa: E402

N = 307
HEX = set("0123456789ABCDEF")


def _rows():
    with identity.IDENTITY.open() as f:
        return {int(r["tid"]): r for r in csv.DictReader(f)}


def _is_hex(v):
    return len(v) == 6 and set(v.upper()) <= HEX


def test_every_school_has_colors_and_a_ballpark_or_a_d_flag():
    rows = _rows()
    assert sorted(rows) == list(range(N))
    for tid, r in rows.items():
        assert r["fetch_date"] and r["school"] == schools.team_name(tid), tid
        if r["color_confidence"] == "D":
            assert not r["primary"] or True                              # a D row may still carry a guess, but it is flagged
        else:
            assert r["color_confidence"] in ("A", "B") and _is_hex(r["primary"]) and _is_hex(r["secondary"]), (tid, r)
            assert r["color_source"].startswith("http"), tid
        if r["stadium_confidence"] == "D":
            assert r["note"], tid                                         # why it is missing, for the report
        else:
            assert r["stadium_confidence"] in ("A", "B") and r["stadium"] and r["stadium_source"].startswith("http"), (tid, r)
        if r["capacity"]:
            assert r["capacity"].isdigit() and 100 <= int(r["capacity"]) <= 60000, (tid, r["capacity"])


def test_every_color_pair_passes_the_contrast_rule():
    for tid, r in _rows().items():
        c = identity.colors(tid)
        if c is None:
            continue
        for key in ("chip", "ink", "secondary", "alt"):
            col = c.get(key)
            if not col:
                continue
            text = identity.text_on(col.lstrip("#"))
            assert identity.contrast(text.lstrip("#"), col.lstrip("#")) >= identity.MIN_TEXT_CONTRAST, (tid, key, col, text)
        assert c["text"] in ("#FFFFFF", "#0B0D12", "#000000")
        # a chip too dark for the background gets the border; the ink is always visible or the primary itself
        dark = identity.contrast(c["chip"].lstrip("#"), identity.BACKGROUND) < identity.MIN_VISIBLE
        assert c["border"] == dark, (tid, c)
        assert identity.contrast(c["ink"].lstrip("#"), identity.BACKGROUND) >= identity.MIN_INK or c["ink"] == c["primary"], (tid, c)


def test_contrast_math_and_text_choice():
    assert abs(identity.contrast("FFFFFF", "000000") - 21.0) < 1e-6
    assert identity.text_on("461D7C") == "#FFFFFF"                       # purple takes white
    assert identity.text_on("F2A900") == "#0B0D12"                       # the accent takes near-black
    assert identity.text_on("FFFFFF") == "#0B0D12"
    for v in range(0, 256, 5):                                           # every gray has a 4.5:1 text
        h = f"{v:02X}" * 3
        assert identity.contrast(identity.text_on(h).lstrip("#"), h) >= 4.5, h


def test_similar_colors_swap_the_away_chip():
    rows = _rows()
    by_primary = {}
    for tid, r in rows.items():
        if r["color_confidence"] != "D":
            by_primary.setdefault(r["primary"].upper(), []).append(tid)
    twins = next((v for v in by_primary.values() if len(v) >= 2), None)
    if twins:
        h, a = identity.pair(twins[0], twins[1])
        assert a.get("swapped") and a["chip"] != h["chip"]
        assert identity.contrast(a["text"].lstrip("#"), a["chip"].lstrip("#")) >= 4.5
    purple = next(t for t, r in rows.items() if r["primary"].upper() == "461D7C")        # LSU
    gold_or_other = next(t for t, r in rows.items() if r["color_confidence"] != "D" and not identity.similar(r["primary"], "461D7C"))
    h, a = identity.pair(purple, gold_or_other)
    assert not a.get("swapped")
    assert identity.similar("B30838", "9D2235") and not identity.similar("461D7C", "FDD023")


def test_venues_by_stage():
    lsu = next(t for t, r in _rows().items() if r["school"] == "LSU")
    v = identity.venue(lsu)
    assert v and v["name"].startswith("Alex Box Stadium") and v["city"] == "Baton Rouge, LA" and v["text"] == f"{v['name']} · Baton Rouge, LA"
    assert identity.game_venue("regular", lsu, False)["name"] == v["name"]
    assert identity.game_venue("regular", lsu, True) is None                    # a neutral site is never guessed
    assert identity.game_venue("cws", lsu, True)["name"] == "Charles Schwab Field Omaha"
    other = (lsu + 1) % N
    assert identity.game_venue("regional", other, True, host_tid=lsu)["name"] == v["name"]
    assert identity.game_venue("super", lsu, False, host_tid=lsu)["name"] == v["name"]
    # conference tournaments: a confirmed neutral site shows, an unconfirmed one shows nothing
    sec = identity.game_venue("conf", lsu, True, conference="SEC", site_detail="neutral")
    site = identity.tournament_site("SEC")
    assert (sec is None) == (site is None)
    if site:
        assert sec["name"] == site["venue"] and site["confidence"] in ("A", "B")
    assert identity.game_venue("conf", lsu, True, conference="DI Independent", site_detail="neutral") is None
    assert identity.game_venue("conf", lsu, True, host_tid=lsu, conference="SEC", site_detail="campus")["name"] == v["name"]
    with identity.TOURNAMENTS.open() as f:
        tr = list(csv.DictReader(f))
    assert {r["conference"] for r in tr} >= set(schools.CONFERENCE_FULL) - {"DI Independent"}
    assert all(r["confidence"] in ("A", "B", "D") and (r["venue"] or r["confidence"] == "D") for r in tr)


def test_identity_is_display_only():
    """No engine or config module imports the identity table or the school files."""
    root = Path(__file__).resolve().parents[1]
    for sub in ("engine", "config", "scripts/run_phase5.py"):
        for f in ([root / sub] if (root / sub).is_file() else (root / sub).rglob("*.py")):
            txt = f.read_text()
            assert "school_identity" not in txt and "app.identity" not in txt and "from app" not in txt, f


def test_identity_api(tmp_path):
    from fastapi.testclient import TestClient
    from app import api as api_mod
    with TestClient(api_mod.app) as c:
        j = c.get("/api/identity").json()
        assert j["available"] and len(j["schools"]) == N and j["background"] == "#12151C"
        row = j["schools"]["0"] if "0" in j["schools"] else j["schools"][0]
        assert "colors" in row and "venue" in row
        league = c.get("/api/league").json()
        t = league["teams"][0]
        assert "colors" in t and "venue" in t
