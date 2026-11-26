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


def test_absolute_scales_and_audit_fixes():
    """Owner calibration 2026-10-09: Climate and Academic Prestige on fixed cutoffs; the shared alias table joins every
    scoreboard season it covers; Omaha Contender from real strength and recent postseason through omaha_score."""
    c = pd.read_csv(ROOT / "data/schools/report_cards.csv").set_index("school")
    # academic: every highly selective school shares the top; the service academies are A+; open admission with low
    # graduation is no better than C+
    for s in ("Harvard", "Stanford", "Duke", "Vanderbilt", "Rice", "Northwestern", "Georgia Tech", "Army West Point", "Navy", "Air Force"):
        assert c.loc[s, "academic_prestige_grade"] == "A+", s
    assert rc.GRADES.index(c.loc["Alabama A&M", "academic_prestige_grade"]) >= rc.GRADES.index("C+")
    assert c.academic_prestige_grade.tolist() == [rc.academic_grade(a, g) for a, g in zip(c.admit_rate, c.grad_rate_6yr)]
    # climate: absolute, south above north
    assert c.climate_grade.tolist() == [rc.climate_grade(x) for x in c.climate_score]
    for s in ("Florida", "Miami (FL)", "Arizona", "UCLA", "Texas"):
        assert c.loc[s, "climate_grade"] == "A+", s
    for s in ("Michigan", "Minnesota", "Maine"):
        assert rc.GRADES.index(c.loc[s, "climate_grade"]) >= rc.GRADES.index("D+"), s
    # joins: LSU New Orleans' scoreboard seasons are found (it was every season missing before the alias table)
    assert c.loc["LSU New Orleans", "strength_seasons"] == 5
    # Omaha Contender: the dynasty's grading path (omaha_score, then grade_values) reproduces the committed grades
    raw = [rc.omaha_score(s_, 0.0, 0.0) for s_ in range(3)]
    assert raw == sorted(raw)
    assert c.loc["Coastal Carolina", "omaha_contender_grade"] in ("A+", "A", "A-", "B+")
    assert c.loc["LSU", "omaha_contender_grade"] in ("A+", "A", "A-", "B+")
    assert rc.grade_values(c.omaha_contender_raw.values) == c.omaha_contender_grade.tolist()
