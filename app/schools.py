"""The real school identity of every sim team and its report card (engine PR #17, `data/schools/`): display and
recruiting only, never read by the engine. Loaded once from the committed files; the dynasty-dependent category
(Omaha Contender) is regraded from the dynasty's own drawn team strength with the engine's grading
(`config.report_cards.grade_values`), as the spec says (design/phase9_recruiting.md, Section 15)."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from config import report_cards as rc

ROOT = Path(__file__).resolve().parents[1]
SCHOOLS = ROOT / "data/schools/schools.csv"
CARDS = ROOT / "data/schools/report_cards.csv"

LABELS = {"program_tradition": "Program Tradition", "conference_prestige": "Conference Prestige", "omaha_contender": "Omaha Contender",
          "academic_prestige": "Academic Prestige", "campus_life": "Campus Life", "climate": "Climate", "money": "Money",
          "facilities": "Facilities", "ballpark_atmosphere": "Ballpark Atmosphere", "brand_exposure": "Brand Exposure",
          "draft_development": "Draft Development", "coach_prestige": "Coach Prestige", "coach_stability": "Coach Stability"}
SHORT = {"program_tradition": "Trad", "conference_prestige": "Conf", "omaha_contender": "Omaha", "academic_prestige": "Acad",
         "campus_life": "Campus", "climate": "Climate", "money": "Money", "facilities": "Facil", "ballpark_atmosphere": "Atmos",
         "brand_exposure": "Brand", "draft_development": "Draft", "coach_prestige": "Coach", "coach_stability": "Stab"}
HEADLINE = ("program_tradition", "conference_prestige", "omaha_contender", "academic_prestige", "climate", "money")


@lru_cache(maxsize=1)
def _load() -> tuple:
    with SCHOOLS.open() as f:
        schools = {int(r["tid"]): r for r in csv.DictReader(f)}
    with CARDS.open() as f:
        cards = {int(r["tid"]): r for r in csv.DictReader(f)}
    return schools, cards


def available() -> bool:
    return SCHOOLS.exists() and CARDS.exists()


def school(tid: int) -> dict | None:
    s = _load()[0].get(int(tid))
    if s is None:
        return None
    return {"tid": int(tid), "school": s["school"], "institution": s["institution"], "conference": s["conference"], "tier": s["tier"],
            "city": s["city"], "state": s["state"], "location": f"{s['city']}, {s['state']}",
            "latitude": float(s["latitude"]), "longitude": float(s["longitude"])}


def categories() -> list:
    return [{"key": k, "label": LABELS[k], "short": SHORT[k], "headline": k in HEADLINE} for k in rc.CATEGORIES]


def report_card(tid: int, omaha_grade: str | None = None) -> dict | None:
    """The 13 grades with confidence and source; `omaha_grade` replaces the file's reference-world Omaha Contender
    grade with the dynasty's own (confidence A either way)."""
    c = _load()[1].get(int(tid))
    if c is None:
        return None
    grades = {}
    for k in rc.CATEGORIES:
        g = c[f"{k}_grade"]
        if k == "omaha_contender" and omaha_grade is not None:
            g = omaha_grade
        grades[k] = {"grade": g, "confidence": c.get(f"{k}_confidence", ""), "source": c.get(f"{k}_source", "")}
    return {"tid": int(tid), "grades": grades}


def omaha_grades(teams) -> dict:
    """Omaha Contender regraded across this dynasty's teams from their drawn strength o + d (log runs)."""
    tids = [t.tid for t in teams]
    return dict(zip(tids, rc.grade_values([float(t.o + t.d) for t in teams])))


def grade_rank(grade: str) -> int:
    """0 for A+ .. 12 for F (for sorting and coloring)."""
    return rc.GRADES.index(grade) if grade in rc.GRADES else len(rc.GRADES)
