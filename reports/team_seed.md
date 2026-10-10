# Teams seeded from their real programs (dynasty year 0)

Owner decision 2026-10-09. 40 leagues (the report's league seeds, 20251000+). The drawn strength set is unchanged per tier and conference: conference effects are reordered among a tier's conferences and team deviations among a conference's teams, by a noisy version of each program's 2021-2025 strength (`scripts/build_team_seed.py`, `engine/league.py` seed_order). The noise is set so the prior's correlation with the year-0 strength equals the real correlation of a program's recent history with its next season's true strength (fitted on 2023-2025, each season from the seasons before it, divided by the square root of that season's reliability).

## Recovery: prior against the drawn year-0 strength

| Level | Tier | Real target r | Best achievable with the sets kept | Seeded | Unseeded |
|---|---|---|---|---|---|
| Teams within conference | p4 | 0.620 | 0.928 | 0.623 ± 0.010 | -0.013 ± 0.020 |
| Teams within conference | mid | 0.751 | 0.888 | 0.750 ± 0.005 | 0.006 ± 0.016 |
| Teams within conference | low | 0.804 | 0.871 | 0.798 ± 0.005 | 0.024 ± 0.020 |
| Conference means within tier | p4 | 0.934 | 0.821 | 0.803 ± 0.022 | -0.161 ± 0.094 |
| Conference means within tier | mid | 0.899 | 0.799 | 0.792 ± 0.014 | 0.000 ± 0.049 |
| Conference means within tier | low | 0.924 | 0.864 | 0.855 ± 0.011 | -0.078 ± 0.052 |

The ranking noise is solved per tier and level on a simulation of the engine's own procedure, so the achieved correlation equals the real target where it can (teams within conference: all three tiers). Conference means cannot reach theirs: a conference's mean strength is its effect plus the mean of its members' team draws, and those draws are only reordered within the conference (the set per conference is kept), so that part stays random; P4 also has only four conferences to rank. The conference effects are therefore ordered with no noise, the closest the kept sets allow (best achievable column). Closing the rest would mean moving team draws across conferences within a tier (the tier's set kept, the conferences' not): owner decision.

## Omaha Contender, year 0 against the reference card

The dynasty's grade: drawn strength (o + d) plus the program's real recent Omaha and super regional bonus, graded with `config.report_cards.omaha_score` and `grade_values` (the function the UI calls). Reference: the committed card (real 2021-2025 strength).

| Agreement | Seeded | Unseeded |
|---|---|---|
| Same grade | 0.345 ± 0.005 | 0.163 ± 0.004 |
| Within one step | 0.785 ± 0.006 | 0.450 ± 0.006 |
| Rank correlation of the scores | 0.906 ± 0.003 | 0.581 ± 0.010 |
| 2021-2025 Omaha teams graded B+ or better | 0.963 ± 0.004 | 0.849 ± 0.012 |

Oregon St. (the one independent) is a group of one: its conference effect and deviation stay as drawn.
