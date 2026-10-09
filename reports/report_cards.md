# School report cards: distribution and examples

Built by `scripts/build_report_cards.py` (Phase 9 prep, owner request 2026-10-08). Data only: grades never feed the engine's team strength or any gated row. Grading: percentile across the 307 D1 programs, cutoffs in `config/report_cards.py` (top shares A+ 3%, A 8%, A- 15%, B+ 25%, B 37%, B- 50%, C+ 62%, C 73%, C- 82%, D+ 89%, D 94%, D- 97%, F 100%).

## Grade distribution (programs per grade)

| Category | A+ | A | A- | B+ | B | B- | C+ | C | C- | D+ | D | D- | F | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Program Tradition | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | B 307 |
| Conference Prestige | 16 | 16 | 14 | 27 | 43 | 39 | 38 | 27 | 30 | 23 | 22 | 0 | 12 | B 306, D 1 |
| Omaha Contender | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | B 304, C 3 |
| Academic Prestige | 29 | 13 | 9 | 17 | 10 | 31 | 64 | 76 | 51 | 4 | 3 | 0 | 0 | A 305, B 2 |
| Campus Life | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | C 307 |
| Climate | 82 | 43 | 9 | 9 | 23 | 16 | 20 | 33 | 24 | 17 | 17 | 9 | 5 | A 307 |
| Money | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | A 304, D 3 |
| Facilities | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | D 307 |
| Ballpark Atmosphere | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 15 | 10 | 9 | D 307 |
| Brand Exposure | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 32 | 13 | 38 | 0 | 0 | D 307 |
| Draft Development | 9 | 16 | 21 | 31 | 37 | 39 | 37 | 34 | 28 | 21 | 16 | 9 | 9 | D 307 |
| Coach Prestige | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 307 | 0 | 0 | 0 | 0 | 0 | D 307 |
| Coach Stability | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 307 | 0 | 0 | 0 | 0 | 0 | D 307 |

Grades by tier (share of the tier's programs at B- or better):

| Category | P4 | Mid | Low |
|---|---|---|---|
| Program Tradition | 0.84 | 0.42 | 0.38 |
| Conference Prestige | 0.98 | 0.60 | 0.00 |
| Omaha Contender | 0.98 | 0.54 | 0.09 |
| Academic Prestige | 0.59 | 0.30 | 0.28 |
| Campus Life | 0.91 | 0.48 | 0.23 |
| Climate | 0.59 | 0.72 | 0.38 |
| Money | 0.98 | 0.58 | 0.02 |
| Facilities | 1.00 | 0.57 | 0.02 |
| Ballpark Atmosphere | 1.00 | 0.52 | 0.10 |
| Brand Exposure | 1.00 | 0.48 | 0.18 |
| Draft Development | 1.00 | 0.52 | 0.11 |

## Example report cards

Omaha Contender is real current strength plus recent Omaha history (a dynasty regrades it from its own teams). Climate and Academic Prestige are absolute scales; the other categories are percentiles. Money for the service academies is imputed (no EADA filing; confidence D). Oregon St. is an independent: Conference Prestige neutral.

| School | Conf | Tier | Trad | Conf | Omaha | Acad | Campus | Climate | Money | Facil | Atmos | Brand | Draft | Coach | Stab |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LSU | SEC | p4 | A+ | A+ | A+ | C+ | A- | A+ | A+ | A+ | A+ | A+ | A+ | C | C |
| Vanderbilt | SEC | p4 | A | A+ | A | A+ | B- | A- | A+ | A+ | A- | A+ | A+ | C | C |
| Stanford | ACC | p4 | A | A | A- | A+ | B- | A | A- | A- | A- | A | A | C | C |
| Oregon St. | DI Independent | p4 | A+ | C | A+ | C+ | B+ | C | A | A- | A- | A- | A- | C | C |
| Nebraska | Big Ten | p4 | A- | B+ | B+ | C+ | B+ | C+ | A- | A- | A- | A- | A- | C | C |
| Coastal Carolina | Sun Belt | mid | A | B | A | C+ | C+ | A+ | A- | A- | B+ | B+ | A- | C | C |
| DBU | CUSA | mid | A- | B+ | A- | C- | C | A+ | A- | A- | B | B+ | A- | C | C |
| Murray St. | MVC | mid | A- | B- | B+ | C | D+ | B+ | C | C | C+ | B | B | C | C |
| Wright St. | Horizon | low | B+ | C | B | C- | C | C | C | C | C | B | B- | C | C |
| Army West Point | Patriot | low | B+ | C+ | C+ | A+ | D- | C- | D+ | C- | C- | B- | B- | C | C |
| Alabama A&M | SWAC | low | F | F | F | D+ | C | A | D- | F | D | D | F | C | C |

| School | Field / hosts / Omaha / titles 2015-25 | Conf. RPI | Real o+d 2021-25 | Grad rate | Admit rate | Enrollment | Locale | Feb-May high °F | Precip days | Baseball expenses |
|---|---|---|---|---|---|---|---|---|---|---|
| LSU | 10 / 6 / 4 / 2 | 0.582 | +1.09 | 68% | 74% | 39,418 | 12 | 74.5 | 35.0 | $10.99M |
| Vanderbilt | 10 / 6 / 3 / 1 | 0.582 | +1.01 | 93% | 6% | 13,456 | 11 | 67.4 | 45.3 | $10.10M |
| Stanford | 6 / 6 / 3 / 0 | 0.564 | +0.59 | 93% | 4% | 18,446 | 21 | 67.3 | 26.0 | $4.34M |
| Oregon St. | 10 / 6 / 3 / 1 | — | +1.02 | 71% | 79% | 35,622 | 13 | 59.1 | 68.1 | $5.82M |
| Nebraska | 7 / 1 / 0 / 0 | 0.524 | +0.61 | 66% | 77% | 23,986 | 11 | 58.5 | 35.7 | $5.22M |
| Coastal Carolina | 9 / 3 / 2 / 1 | 0.523 | +0.88 | 51% | 80% | 10,829 | 13 | 71.8 | 30.6 | $5.21M |
| DBU | 10 / 1 / 0 / 0 | 0.513 | +0.83 | 60% | 91% | 4,201 | 11 | 72.6 | 34.2 | $4.33M |
| Murray St. | 1 / 0 / 1 / 0 | 0.495 | +0.34 | 63% | 86% | 9,841 | 32 | 65.3 | 44.3 | $1.15M |
| Wright St. | 7 / 0 / 0 / 0 | 0.460 | +0.31 | 46% | 95% | 9,884 | 21 | 57.5 | 48.0 | $1.17M |
| Army West Point | 6 / 0 / 0 / 0 | 0.467 | +0.06 | 85% | 14% | 4,508 | 31 | 54.5 | 39.9 | $0.92M (imputed) |
| Alabama A&M | 0 / 0 / 0 / 0 | 0.419 | -1.23 | 29% | 66% | 6,614 | 12 | 70.0 | 42.6 | $0.67M |

Bracket teams not among the 307 programs (left D1 or not matched): Hartford.
