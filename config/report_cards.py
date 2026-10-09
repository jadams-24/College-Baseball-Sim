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
# Academic Prestige: selectivity (1 - admission rate) weighted over the six-year bachelor's graduation rate (owner calibration
# 2026-10-09: Stanford, Vanderbilt, Duke, Rice and the Ivies at the top)   # GUESS (weights)
ACADEMIC_WEIGHTS = {"grad_rate": 0.25, "selectivity": 0.75}
# Campus Life: total enrollment (log) and IPEDS locale   # GUESS (weights and locale scores)
CAMPUS_WEIGHTS = {"enrollment": 0.6, "locale": 0.4}
LOCALE_SCORE = {11: 1.0, 12: 0.9, 13: 0.8, 21: 0.75, 22: 0.65, 23: 0.55, 31: 0.45, 32: 0.4, 33: 0.35, 41: 0.3, 42: 0.2, 43: 0.1}
# Climate (owner calibration 2026-10-09: a comfortable band, not "warmer is better"): each month Feb-May, the normal daily high's
# distance below CLIMATE_BAND_F[0] or above CLIMATE_BAND_F[1] (heat counted at CLIMATE_HEAT_WEIGHT per degree), averaged over the
# four months (less is better); and Feb-May days with 0.01"+ precipitation (fewer better)   # GUESS (band, heat weight, weights)
CLIMATE_BAND_F = (65.0, 85.0)
CLIMATE_HEAT_WEIGHT = 1.0
CLIMATE_WEIGHTS = {"comfort": 0.7, "dry_days": 0.3}
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
