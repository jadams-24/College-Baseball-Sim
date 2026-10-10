# Report cards: Omaha Contender input audit, absolute Climate and Academic Prestige

Owner request 2026-10-09. Built by `scripts/build_report_cards.py`.

## Omaha Contender: what the formula used, and what it uses now

**Before:** one input, the reference world's drawn team strength (o + d) for the sim team that carries the school's identity (`engine/league.py`, seed 20251000). The league draws each team's strength from its tier and conference distribution (tiers and conferences are distributions of team strength), not from the school's own results, so the grade had no link to the real program. Nothing was missing and no join failed: the input was simply not about the school.

**Now:**

| Input | Source file | Seasons | Missing data |
|---|---|---|---|
| Current strength: the scoreboard fit's o + d per season (log runs; `scripts/build_phase2_teams.fit`, no parks), recency half-life 1.5 seasons | `data/ncaa_<year>/scoreboard/games_<year>.csv` (data.ncaa.com) | 2021-2025 | seasons without data skipped (not zero); confidence B with 3+ seasons, C with 1-2, D with none |
| Recent Omaha appearances (+ 0.15 per weighted appearance) and super regionals (half that) | `data/ncaa_brackets/` | 2021-2025 | a year a school is absent is a year it did not make it |

The dynasty regrades with the same function: `config.report_cards.omaha_score(strength, omaha_recent, super_recent)` and `grade_values` (the UI passes its dynasty's own team strength and postseason history).

## Non-D1 opponents (fixed 2026-10-10)

The 2021-2024 scoreboards label non-NCAA opponents with the conference "NON-NCAA ORG", frequent enough (137-239 entries a season) to pass the Division I conference count. Those games entered the per-season strength fit and the RPI. A handful of NAIA teams with one to three games fitted near -24 log runs, and the fit's centring over teams moved every D1 team by about +.1 in those seasons, so schools missing a season were compared on a shifted scale. The label is now excluded (NON_D1_CONF). Effect: 57 grades moved by one step (24 Omaha Contender, 9 Conference Prestige, 8 Program Tradition, 8 Ballpark Atmosphere, 6 Draft Development, 2 Facilities), none by two.

## Name joins

One shared alias table for every source: `data/schools/name_aliases.csv`. Joins fixed on 2026-10-09 (they had silently dropped data):

| Spelling in the source | School | Effect before the fix |
|---|---|---|
| New Orleans (scoreboards) | LSU New Orleans | every season 2021-2025 missing (win pct imputed at the median, out of its conference's RPI) |
| Fairleigh Dickinson (scoreboards) | FDU | 2021-2022 missing |
| Houston Baptist (scoreboards) | Houston Christian | 2021-2022 missing |
| Dixie St. (scoreboards) | Utah Tech | 2021-2022 missing |

Bracket spellings already handled by the old alias list (Lamar, Long Island, Northern Illinois, Saint Mary's) moved into the same table. Bracket teams not among the 307 programs: Hartford (left D1).

## Coverage (strength and RPI seasons found, of 5)

| School | Strength seasons | RPI seasons | Status | Omaha / supers 2021-25 | Confidence |
|---|---|---|---|---|---|
| LSU | 5 | 5 | present | 2 / 3 | B |
| Vanderbilt | 5 | 5 | present | 1 / 1 | B |
| Stanford | 5 | 5 | present | 3 / 3 | B |
| Oregon St. | 5 | 5 | present | 1 / 3 | B |
| Nebraska | 5 | 5 | present | 0 / 0 | B |
| Coastal Carolina | 5 | 5 | present | 1 / 1 | B |
| DBU | 5 | 5 | present | 0 / 1 | B |
| Murray St. | 5 | 5 | present | 1 / 1 | B |
| Wright St. | 5 | 5 | present | 0 / 0 | B |
| Army West Point | 5 | 5 | present | 0 / 0 | B |
| Alabama A&M | 5 | 5 | present | 0 / 0 | B |

Every other school with any missing or partial season (18; the rest of the 307 have all five):

| School | Strength seasons | RPI seasons | Status | Omaha / supers 2021-25 | Confidence |
|---|---|---|---|---|---|
| Bethune-Cookman | 4 | 4 | partial | 0 / 0 | B |
| Brown | 4 | 4 | partial | 0 / 0 | B |
| Columbia | 4 | 4 | partial | 0 / 0 | B |
| Cornell | 4 | 4 | partial | 0 / 0 | B |
| Dartmouth | 4 | 4 | partial | 0 / 0 | B |
| Harvard | 4 | 4 | partial | 0 / 0 | B |
| Le Moyne | 2 | 2 | partial | 0 / 0 | C |
| Lindenwood | 3 | 3 | partial | 0 / 0 | B |
| Mercyhurst | 1 | 1 | partial | 0 / 0 | C |
| Penn | 4 | 4 | partial | 0 / 0 | B |
| Princeton | 4 | 4 | partial | 0 / 0 | B |
| Queens (NC) | 3 | 3 | partial | 0 / 0 | B |
| Southern Ind. | 3 | 3 | partial | 0 / 0 | B |
| St. Thomas (MN) | 4 | 4 | partial | 0 / 0 | B |
| Stonehill | 3 | 3 | partial | 0 / 0 | B |
| UMES | 4 | 4 | partial | 0 / 0 | B |
| West Ga. | 1 | 1 | partial | 0 / 0 | C |
| Yale | 4 | 4 | partial | 0 / 0 | B |

Why they are partial: the Ivy League and Bethune-Cookman did not play in 2021; the others joined Division I after 2021 (their earlier seasons were not D1 games). LSU New Orleans now has all five.

## Coastal Carolina and LSU, before and after

| School | Before: sim draw o + d | Before grade | Real strength 2021-25 (per season) | Weighted | Omaha / supers 2021-25 | Score | After grade |
|---|---|---|---|---|---|---|---|
| Coastal Carolina | -0.48 | D+ | 2021: +0.35, 2022: +0.62, 2023: +0.57, 2024: +0.67, 2025: +0.99 | +0.762 | 1 / 1 | +0.987 | A |
| LSU | +0.28 | B | 2021: +0.84, 2022: +0.84, 2023: +1.18, 2024: +0.76, 2025: +1.09 | +0.976 | 2 / 3 | +1.302 | A+ |

Sanity anchor: every 2021-2025 Omaha team (27), its grade (target B+ or better unless its strength collapsed):

Tennessee A+, Arkansas A+, LSU A+, Oregon St. A+, North Carolina A+, Texas A&M A+, Virginia A+, Florida A+, Texas A+, Coastal Carolina A, Florida St. A, Kentucky A, Vanderbilt A, Auburn A, Wake Forest A, Arizona A, UCLA A, Louisville A, TCU A, NC State A, Mississippi St. A-, Oklahoma A-, Ole Miss A-, Stanford A-, Notre Dame A-, Murray St. B+, Oral Roberts B.

## Climate and Academic Prestige: absolute scales

| Category | A+ | A | A- | B+ | B | B- | C+ | C | C- | D+ | D | D- | F |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Climate | 82 | 43 | 9 | 9 | 23 | 16 | 20 | 33 | 24 | 17 | 17 | 9 | 5 |
| Academic Prestige | 29 | 13 | 9 | 17 | 10 | 31 | 64 | 76 | 51 | 4 | 3 | 0 | 0 |

A+ in Academic Prestige (29): Harvard, Columbia, Princeton, Stanford, Brown, Yale, Northeastern, Vanderbilt, Penn, Dartmouth, Northwestern, Duke, Cornell, Rice, UCLA, Navy, Southern California, California, Notre Dame, Georgetown, Air Force, Army West Point, Davidson, Tulane, Boston College, Georgia Tech, Virginia, Michigan, North Carolina.

A+ in Climate (82): New Mexico St., UNLV, Grand Canyon, Arizona St., Arizona, LMU (CA), UTRGV, Cal St. Fullerton, UCLA, CSUN, CSU Bakersfield, Southern California, Utah Tech, Long Beach St., California Baptist, UC Irvine, UC Riverside, Texas Tech, Houston, Rice, Texas Southern, San Diego St., Fresno St., UC San Diego, A&M-Corpus Christi, Abilene Christian, South Fla., Cal Poly, Pacific, Bethune-Cookman, Ga. Southern, UC Davis, Miami (FL), Florida, Sacramento St., Tarleton St., FGCU, Troy, UT Arlington, Baylor, The Citadel, Col. of Charleston, Texas St., UCF, TCU, Stetson, Santa Clara, Florida St., Florida A&M, Fla. Atlantic, Coastal Carolina, UTSA, Tulane, FIU, Sam Houston, North Florida, Jacksonville, San Jose St., New Mexico, Texas A&M, McNeese, Alcorn, LSU New Orleans, Lamar University, UIW, Prairie View, Northwestern St., Texas, Charleston So., Georgia, Southeastern La., South Alabama, Wofford, USC Upstate, Louisiana, Southern U., DBU, Mercer, Alabama St., LSU, Louisiana Tech, Grambling.

Climate score = min(Feb-May mean daily high, 68 °F) - 0.07 °F x rain days; cutoffs A+ ≥ 65.5, A ≥ 64.5, A- ≥ 63.5, B+ ≥ 62.0, B ≥ 60.0, B- ≥ 58.0, C+ ≥ 56.0, C ≥ 53.5, C- ≥ 51.0, D+ ≥ 49.5, D ≥ 47.5, D- ≥ 45.0, else F.
Academic: admission rate sets the grade (≤20% A+, ≤30% A, ≤40% A-, ≤50% B+, ≤60% B, ≤70% B-, ≤80% C+, ≤90% C, ≤100% C-), graduation rate caps it (below 85%: at most A, below 80%: at most A-, below 70%: at most B, below 60%: at most B-, below 50%: at most C+, below 40%: at most C, below 30%: at most D+, below 25%: at most D). The service academies report admission and graduation to IPEDS like any school (Navy 9% / 92%, Army 14% / 85%, Air Force 14% / 88%): no override needed.
