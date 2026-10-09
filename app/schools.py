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
NAMES = ROOT / "app/school_names.csv"          # app-side display names: full, short, abbreviation (scripts/build_school_names.py)

LABELS = {"program_tradition": "Program Tradition", "conference_prestige": "Conference Prestige", "omaha_contender": "Omaha Contender",
          "academic_prestige": "Academic Prestige", "campus_life": "Campus Life", "climate": "Climate", "money": "Money",
          "facilities": "Facilities", "ballpark_atmosphere": "Ballpark Atmosphere", "brand_exposure": "Brand Exposure",
          "draft_development": "Draft Development", "coach_prestige": "Coach Prestige", "coach_stability": "Coach Stability"}
SHORT = {"program_tradition": "Trad", "conference_prestige": "Conf", "omaha_contender": "Omaha", "academic_prestige": "Acad",
         "campus_life": "Campus", "climate": "Climate", "money": "Money", "facilities": "Facil", "ballpark_atmosphere": "Atmos",
         "brand_exposure": "Brand", "draft_development": "Draft", "coach_prestige": "Coach", "coach_stability": "Stab"}
HEADLINE = ("program_tradition", "conference_prestige", "omaha_contender", "academic_prestige", "climate", "money")
# the identity file's conference labels spelled out for headers (owner rule 2026-10-09); the short labels stay in tight spots
CONFERENCE_FULL = {"ACC": "Atlantic Coast Conference", "ASUN": "Atlantic Sun Conference", "America East": "America East Conference",
                   "Atlantic 10": "Atlantic 10 Conference", "Big 12": "Big 12 Conference", "Big East": "Big East Conference",
                   "Big South": "Big South Conference", "Big Ten": "Big Ten Conference", "Big West": "Big West Conference",
                   "CAA": "Coastal Athletic Association", "CUSA": "Conference USA", "DI Independent": "Independent",
                   "Horizon": "Horizon League", "Ivy League": "Ivy League", "MAAC": "Metro Atlantic Athletic Conference",
                   "MAC": "Mid-American Conference", "MVC": "Missouri Valley Conference", "Mountain West": "Mountain West Conference",
                   "NEC": "Northeast Conference", "OVC": "Ohio Valley Conference", "Patriot": "Patriot League", "SEC": "Southeastern Conference",
                   "SWAC": "Southwestern Athletic Conference", "SoCon": "Southern Conference", "Southland": "Southland Conference",
                   "Summit League": "Summit League", "Sun Belt": "Sun Belt Conference", "The American": "American Athletic Conference",
                   "WAC": "Western Athletic Conference", "WCC": "West Coast Conference"}


def conference_full(short: str) -> str:
    return CONFERENCE_FULL.get(short, short)


@lru_cache(maxsize=1)
def _load() -> tuple:
    with SCHOOLS.open() as f:
        schools = {int(r["tid"]): r for r in csv.DictReader(f)}
    with CARDS.open() as f:
        cards = {int(r["tid"]): r for r in csv.DictReader(f)}
    names = {}
    if NAMES.exists():
        with NAMES.open() as f:
            names = {int(r["tid"]): r for r in csv.DictReader(f)}
    return schools, cards, names


# ---- the one lookup every screen uses for a team's display fields (owner rule 2026-10-09: engine names appear
# nowhere in the UI except the "engine id" line in a tooltip or debug spot) ----
def display(tid: int) -> dict | None:
    """Display fields of a sim team: full school name ("Central Michigan"), short name ("Central Mich."), a 2-5 letter
    abbreviation ("CMU"), conference, tier and location. None when the identity file is missing."""
    if not available():
        return None
    schools_, _, names = _load()
    sch = schools_.get(int(tid))
    if sch is None:
        return None
    nm = names.get(int(tid), {})
    return {"tid": int(tid), "name": nm.get("full") or sch["school"], "short": nm.get("short") or sch["school"], "abbr": nm.get("abbr") or sch["school"][:4].upper(),
            "conference": sch["conference"], "conference_full": conference_full(sch["conference"]), "tier": sch["tier"], "location": f"{sch['city']}, {sch['state']}"}


def team_name(tid: int, fallback: str = "") -> str:
    """The full school name of a sim team (the engine's own name only when the identity file is missing)."""
    d = display(tid)
    return d["name"] if d else fallback


def team_fields(team) -> dict:
    """The display fields of an engine Team object, with its engine name under `engine_name` (the one place it may show)."""
    d = display(team.tid) or {"tid": team.tid, "name": team.name, "short": team.name, "abbr": "".join(w[0] for w in team.name.split())[:4].upper(),
                               "conference": None, "conference_full": None, "tier": team.tier, "location": ""}
    return dict(d, engine_name=team.name, tier=team.tier)


def conference_of(tid: int, fallback: str = "") -> str:
    d = display(tid)
    return d["conference"] if d else fallback


def conference_check(league, real_conf: dict) -> dict:
    """Each engine conference's members against the identity file's conferences: a mismatch is an engine conference
    whose members map to more than one real conference (reported, never hidden: it may need an engine-side fix)."""
    by_engine: dict = {}
    for t in league.teams:
        by_engine.setdefault(t.conference, []).append(t.tid)
    mismatches = []
    for ci, tids in sorted(by_engine.items()):
        reals = {}
        for t in tids:
            reals.setdefault(conference_of(t, real_conf.get(t, "?")), []).append(t)
        cfg_names = {real_conf.get(t) for t in tids}
        if len(reals) > 1 or len(cfg_names) > 1:
            mismatches.append({"engine_conference": ci, "engine_name": league.conferences[ci][0] if ci < len(league.conferences) else None,
                               "members": {name: [team_name(t) for t in ts] for name, ts in reals.items()},
                               "config_conferences": sorted(c for c in cfg_names if c)})
    return {"engine_conferences": len(by_engine), "mismatches": mismatches}


def abbreviation_guesses() -> list:
    """The abbreviations chosen here rather than taken from common use, for the owner to check."""
    _, _, names = _load()
    return [{"tid": t, "school": r["short"], "full": r["full"], "abbr": r["abbr"]} for t, r in sorted(names.items()) if r["abbr_source"] == "guess"]


def available() -> bool:
    return SCHOOLS.exists() and CARDS.exists()


def school(tid: int) -> dict | None:
    s = _load()[0].get(int(tid))
    if s is None:
        return None
    d = display(tid) or {}
    return {"tid": int(tid), "school": d.get("name", s["school"]), "short": d.get("short", s["school"]), "abbr": d.get("abbr", ""),
            "institution": s["institution"], "conference": s["conference"], "tier": s["tier"],
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
