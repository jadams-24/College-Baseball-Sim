"""School report cards (Phase 9 prep, owner request 2026-10-08): grade cutoffs, category definitions and weights.

Report cards are for recruiting and display only. Nothing in engine/ reads this file or data/schools/report_cards.csv, and no
grade feeds team strength or any gated row (owner rule 2026-10-08; tests/test_report_cards.py checks the engine never imports
it). Built by scripts/build_report_cards.py; the spec is design/phase9_recruiting.md, Section 15.

Grades are percentile ranks across the 307 D1 programs (ties share their mean rank), cut so the distribution looks like a real
report card: few A+ and few F. The UI recomputes the one dynasty-dependent category (Omaha Contender, from the dynasty's own
drawn team strength) with grade_values() and the same cutoffs.
"""
from __future__ import annotations

import numpy as np

GRADES = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F")
# share of programs at or above each grade, from the top (A+ the top 3%, F the bottom 3%)   # GUESS (report-card shape)
TOP_SHARE = (0.03, 0.08, 0.15, 0.25, 0.37, 0.50, 0.62, 0.73, 0.82, 0.89, 0.94, 0.97, 1.00)
NEUTRAL = "C"          # Coach Prestige and Coach Stability for a new coach  # GUESS (neutral baseline, owner request)

# recency weight of a season in Program Tradition: 0.5 ** ((last season - season) / half-life)   # GUESS
TRADITION_HALF_LIFE = 4.0
# Program Tradition points per season, cumulative (a champion scores every line)   # GUESS
TRADITION_POINTS = {"field": 1.0, "host": 1.0, "super": 2.0, "omaha": 3.0, "final": 1.0, "title": 2.0}
# the D1 win pct (2021-2025, recency-weighted) breaks ties among programs without postseason points   # GUESS
TRADITION_WINPCT_WEIGHT = 1.0
# Conference Prestige: members' mean RPI and NCAA bids per member, seasons 2021-2025 on the 2025 map   # GUESS (weights)
CONFERENCE_WEIGHTS = {"rpi": 0.5, "bids": 0.5}
# Academic Prestige (owner decision 2026-10-09, second pass): an absolute scale, so every highly selective school shares the top.
# The admission rate sets the grade (ACADEMIC_ADMIT_CUTOFFS: at or below the rate, that grade; open admission counts as 100%);
# the six-year graduation rate caps it (ACADEMIC_GRAD_CAPS: below the rate, at most that grade)   # GUESS (all cutoffs)
ACADEMIC_ADMIT_CUTOFFS = ((20, "A+"), (30, "A"), (40, "A-"), (50, "B+"), (60, "B"), (70, "B-"), (80, "C+"), (90, "C"), (100, "C-"))
ACADEMIC_GRAD_CAPS = ((85, "A"), (80, "A-"), (70, "B"), (60, "B-"), (50, "C+"), (40, "C"), (30, "D+"), (25, "D"), (0, "D-"))
# Campus Life: total enrollment (log) and IPEDS locale   # GUESS (weights and locale scores)
CAMPUS_WEIGHTS = {"enrollment": 0.6, "locale": 0.4}
LOCALE_SCORE = {11: 1.0, 12: 0.9, 13: 0.8, 21: 0.75, 22: 0.65, 23: 0.55, 31: 0.45, 32: 0.4, 33: 0.35, 41: 0.3, 42: 0.2, 43: 0.1}
# Climate (owner decision 2026-10-09, second pass): an absolute scale, not a curve, so any number of schools can share a grade.
# Score in degrees F: the Feb-May mean daily high counted up to CLIMATE_WARM_CAP_F (warmer adds nothing, so mild but playable
# highs are not penalized and heat is not rewarded), minus CLIMATE_RAIN_F_PER_DAY per Feb-May day with 0.01"+ precipitation.
# Cutoffs calibrated to the owner's anchors (scripts/build_report_cards.py prints them): A+ Florida, the Gulf Coast, south and
# central Texas, Arizona, Southern California; A/A- the Carolinas, Georgia, Alabama, Mississippi, Oklahoma, Las Vegas, the Bay
# Area; B Tennessee, Arkansas, Virginia, Kentucky; C the lower Midwest, Mid-Atlantic, Oregon, Washington, Nebraska; D/F Michigan,
# Minnesota, Wisconsin, New England, upstate New York   # GUESS (cap, rain rate and cutoffs, fitted to the anchors)
CLIMATE_WARM_CAP_F = 68.0
CLIMATE_RAIN_F_PER_DAY = 0.07
CLIMATE_CUTOFFS = ((65.5, "A+"), (64.5, "A"), (63.5, "A-"), (62.0, "B+"), (60.0, "B"), (58.0, "B-"), (56.0, "C+"), (53.5, "C"),
                   (51.0, "C-"), (49.5, "D+"), (47.5, "D"), (45.0, "D-"))
# Omaha Contender (owner audit 2026-10-09): the reference card grades current real strength (the scoreboard fit's o + d per
# season, OMAHA_STRENGTH_SEASONS, recency half-life OMAHA_HALF_LIFE seasons; seasons a school has no data for are skipped, not
# zeroed) plus recent postseason (Omaha and super regional appearances in OMAHA_POST_SEASONS, same weights)   # GUESS (weights)
OMAHA_STRENGTH_SEASONS = (2021, 2022, 2023, 2024, 2025)
OMAHA_POST_SEASONS = (2021, 2022, 2023, 2024, 2025)
OMAHA_HALF_LIFE = 1.5
OMAHA_POST_WEIGHT = 0.15
OMAHA_SUPER_SHARE = 0.5
# proxies until real data replaces them (graded D confidence, marked for replacement)   # GUESS (all four)
FACILITIES_WEIGHTS = {"money": 0.5, "hosting": 0.3, "conference": 0.2}
ATMOSPHERE_WEIGHTS = {"hosting": 0.4, "enrollment": 0.3, "conference": 0.3}
# Brand Exposure (owner calibration 2026-10-09: a low-tier school should not outrank most P4 programs): the conference's media
# footprint (national network or streaming reach, by conference: GUESS until TV and streaming appearance counts replace it),
# NCAA tournament appearances 2015-2025 and Omaha / super regional history (percentiles)   # GUESS (all)
EXPOSURE_WEIGHTS = {"media": 0.5, "field": 0.25, "omaha": 0.25}
MEDIA_FOOTPRINT = {"SEC": 1.0, "ACC": 0.95, "Big Ten": 0.95, "Big 12": 0.9, "DI Independent": 0.7,
                   "The American": 0.5, "Sun Belt": 0.5, "CUSA": 0.5, "Big East": 0.5, "Mountain West": 0.45, "WCC": 0.45,
                   "Big West": 0.4, "ASUN": 0.4, "CAA": 0.4, "MVC": 0.4, "SoCon": 0.4, "Atlantic 10": 0.4, "MAC": 0.4,
                   "Big South": 0.35, "WAC": 0.35, "Ivy League": 0.25}
MEDIA_DEFAULT = 0.2      # the other low-tier conferences
DRAFT_WEIGHTS = {"tradition": 0.4, "money": 0.3, "conference": 0.3}

CATEGORIES = ("program_tradition", "conference_prestige", "omaha_contender", "academic_prestige", "campus_life", "climate", "money",
              "facilities", "ballpark_atmosphere", "brand_exposure", "draft_development", "coach_prestige", "coach_stability")


def percentile(values) -> np.ndarray:
    """Mid-rank percentile in [0, 1] (ties share their mean rank); higher values rank higher."""
    v = np.asarray(values, float)
    order = v.argsort(kind="mergesort")
    ranks = np.empty(len(v)); ranks[order] = np.arange(len(v))
    for x in np.unique(v):           # ties: mean rank
        k = v == x
        ranks[k] = ranks[k].mean()
    return (ranks + 0.5) / len(v)


def climate_score(tmax_feb_may_f: float, rain_days_feb_may: float) -> float:
    """The absolute climate score in degrees F (higher better)."""
    return min(float(tmax_feb_may_f), CLIMATE_WARM_CAP_F) - CLIMATE_RAIN_F_PER_DAY * float(rain_days_feb_may)


def climate_grade(score: float) -> str:
    for cut, g in CLIMATE_CUTOFFS:
        if score >= cut:
            return g
    return "F"


def academic_grade(admit_rate_pct: float, grad_rate_pct: float) -> str:
    """Absolute academic grade: selectivity sets it, graduation caps it."""
    g = next(g for cut, g in ACADEMIC_ADMIT_CUTOFFS if admit_rate_pct <= cut)
    caps = [cap for cut, cap in ACADEMIC_GRAD_CAPS if grad_rate_pct < cut]
    if caps and GRADES.index(caps[-1]) > GRADES.index(g):      # the cap of the lowest band the rate falls short of
        g = caps[-1]
    return g


def omaha_score(strength: float, omaha_recent: float, super_recent: float) -> float:
    """Omaha Contender score (owner audit 2026-10-09): current team strength (o + d, log runs; real seasons for the reference
    card, the dynasty's own teams in a dynasty) plus a bonus for recent Omaha and super regional appearances (recency-weighted
    counts). Graded on percentiles with grade_values; the UI calls this same function with the dynasty's numbers."""
    return float(strength) + OMAHA_POST_WEIGHT * (float(omaha_recent) + OMAHA_SUPER_SHARE * float(super_recent))


def grade_of(pct: float) -> str:
    """Grade of a percentile (1 = best)."""
    top = 1.0 - pct
    for g, s in zip(GRADES, TOP_SHARE):
        if top < s:
            return g
    return GRADES[-1]


def grade_values(values) -> list:
    """Grades of a set of values across D1 (higher better)."""
    return [grade_of(p) for p in percentile(values)]
