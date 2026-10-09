"""School report cards are data for recruiting and display only (owner rule 2026-10-08): the engine never reads them, and the
committed files cover every sim team with a grade in every category."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from config import report_cards as rc

ROOT = Path(__file__).resolve().parents[1]


def test_engine_never_reads_report_cards():
    pat = re.compile(r"report_cards|data/schools")
    hits = [p.name for p in (ROOT / "engine").glob("*.py") if pat.search(p.read_text())]
    assert not hits, f"engine modules reading report cards: {hits}"


def test_schools_cover_every_sim_team():
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    teams = teams[teams.tier.notna()].reset_index(drop=True)
    s = pd.read_csv(ROOT / "data/schools/schools.csv")
    assert list(s.tid) == list(range(len(teams)))
    assert list(s.ncaa_team_id) == list(teams.ncaa_team_id)
    assert s[["school", "institution", "conference", "city", "state", "latitude", "longitude"]].notna().all().all()


def test_every_category_graded():
    c = pd.read_csv(ROOT / "data/schools/report_cards.csv")
    assert len(c) == 307
    for cat in rc.CATEGORIES:
        assert c[f"{cat}_grade"].isin(rc.GRADES).all(), cat
        assert c[f"{cat}_confidence"].isin(list("ABCD")).all(), cat


def test_grade_shape():
    grades = rc.grade_values(range(307))
    n = pd.Series(grades).value_counts()
    assert n["A+"] <= 0.04 * 307 and n["F"] <= 0.04 * 307
    assert grades[-1] == "A+" and grades[0] == "F"
