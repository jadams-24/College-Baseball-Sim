# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-03.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7311 | 6.7500 | ±0.1760 | B | yes | pass |
| Batting average | 0.2820 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3798 | 0.3805 | ±0.0055 | B | yes | pass |
| Slugging pct | 0.4412 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0543 | 1.0500 | ±0.0519 | B |  | pass |
| BB per PA | 0.1051 | 0.1059 | ±0.0052 | B |  | pass |
| K per PA | 0.1945 | 0.1927 | ±0.0055 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1049 | 1.0990 | ±0.1515 | B |  | pass |
| PA per team-game | 40.5066 | 40.3100 | ±1.0045 | B |  | pass |
| ERA | 6.1713 | 6.0800 | ±0.3108 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1047 | 0.1031 | ±0.0094 | A | yes | pass |
| PA per half-inning | 4.681 | 4.694 | ±0.056 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6375, 0.1663, 0.0916, 0.0496, 0.0266, 0.0285 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0621 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1292 | 0.1524 | ±0.0173 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1726 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.464 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5956 | 0.5836 | ±0.0340 | A | yes | pass |
| Home run differential per game | 1.121 | 0.888 | ±0.527 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0284 (limit 0.0402) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0341 | 0.0400 | -0.0059 | ±0.0101 | pass |
| 1 | 0.0588 | 0.0606 | -0.0018 | ±0.0101 | pass |
| 2 | 0.0772 | 0.0770 | +0.0002 | ±0.0101 | pass |
| 3 | 0.0898 | 0.0916 | -0.0018 | ±0.0102 | pass |
| 4 | 0.0954 | 0.0971 | -0.0017 | ±0.0102 | pass |
| 5 | 0.0965 | 0.0916 | +0.0049 | ±0.0101 | pass |
| 6 | 0.0905 | 0.0876 | +0.0029 | ±0.0102 | pass |
| 7 | 0.0831 | 0.0767 | +0.0064 | ±0.0102 | pass |
| 8 | 0.0728 | 0.0647 | +0.0081 | ±0.0101 | pass |
| 9 | 0.0610 | 0.0579 | +0.0031 | ±0.0101 | pass |
| 10 | 0.0538 | 0.0508 | +0.0030 | ±0.0101 | pass |
| 11 | 0.0450 | 0.0454 | -0.0004 | ±0.0101 | pass |
| 12 | 0.0361 | 0.0362 | -0.0001 | ±0.0101 | pass |
| 13 | 0.0282 | 0.0302 | -0.0020 | ±0.0101 | pass |
| 14 | 0.0218 | 0.0260 | -0.0042 | ±0.0101 | pass |
| 15+ | 0.0561 | 0.0664 | -0.0103 | ±0.0109 | pass (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 5.946 | 6.364 | ±0.507 | A | yes | pass |
| p4 batting vs mid pitching | 8.477 | 8.614 | ±0.649 | A | yes | pass |
| p4 batting vs low pitching | 10.595 | 9.820 | ±1.308 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.555 | 4.762 | ±0.553 | A | yes | pass |
| mid batting vs mid pitching | 6.637 | 6.724 | ±0.461 | A | yes | pass |
| mid batting vs low pitching | 8.879 | 8.457 | ±0.951 | A | yes | pass |
| low batting vs p4 pitching | 3.327 | 3.629 | ±0.676 | A | yes | pass |
| low batting vs mid pitching | 5.287 | 5.880 | ±0.668 | A | yes | pass |
| low batting vs low pitching | 7.268 | 7.046 | ±0.730 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.731 | 6.747 | ±0.219 | A | yes | pass |
| Team R/G SD across teams (all) | 1.098 | 1.162 | ±0.146 | A | yes | pass |
| Team RA/G mean (all) | 6.733 | 6.841 | ±0.289 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.881 | 1.596 | ±0.235 | A | yes | FAIL |
| Team R/G mean (p4) | 7.067 | 7.207 | ±0.314 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.815 | 0.793 | ±0.216 | A | yes | pass |
| Team RA/G mean (p4) | 5.324 | 5.767 | ±0.438 | A | yes | FAIL |
| Team RA/G SD across teams (p4) | 1.065 | 1.112 | ±0.306 | A | yes | pass |
| Team R/G mean (mid) | 6.657 | 6.668 | ±0.321 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.134 | 1.255 | ±0.221 | A | yes | pass |
| Team RA/G mean (mid) | 6.693 | 6.871 | ±0.355 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.523 | 1.377 | ±0.252 | A | yes | pass |
| Team R/G mean (low) | 6.620 | 6.553 | ±0.383 | A | yes | pass |
| Team R/G SD across teams (low) | 1.159 | 1.141 | ±0.264 | A | yes | pass |
| Team RA/G mean (low) | 7.803 | 7.560 | ±0.661 | A | yes | pass |
| Team RA/G SD across teams (low) | 2.144 | 1.819 | ±0.451 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.60 vs data 7.56; pitchers sim 1.95 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2325 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2894 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3458 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3237 | 0.3366 | ±0.0109 | B | yes | FAIL |
| OBP p50 | 0.3844 | 0.3889 | ±0.0136 | B | yes | pass |
| OBP p90 | 0.4450 | 0.4487 | ±0.0130 | B | yes | pass |
| ISO p10 | 0.0795 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1594 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2625 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1182 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1824 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2649 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0641 | 0.0668 | ±0.0107 | B | yes | pass |
| BB_pct p50 | 0.1016 | 0.1058 | ±0.0137 | B | yes | pass |
| BB_pct p90 | 0.1485 | 0.1584 | ±0.0160 | B | yes | pass |
| ERA p10 | 3.25 | 3.41 | ±0.619 | B | yes | pass |
| ERA p50 | 5.15 | 5.12 | ±0.667 | B | yes | pass |
| ERA p90 | 7.63 | 7.64 | ±1.276 | B | yes | pass |
| K9 p10 | 5.75 | 5.72 | ±0.674 | B | yes | pass |
| K9 p50 | 8.38 | 7.88 | ±0.924 | B | Phase 6 | pass |
| K9 p90 | 11.36 | 10.56 | ±1.307 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 783.1 (season range 744.0–829.0) | 821.1 (56-game eq. of 882) | ±41.5 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 6.200 (season range 4.000–10.000) | 5 | ±3.656 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 48.7 (season range 37.0–65.0) | 57 | ±14.4 | A | yes | pass |
| Teams with ERA < 4.00 | 19.2 (season range 11.0–28.0) | 12 | ±10.1 | A | yes | pass |
| Best team ERA | 2.918 (season range 2.304–3.325) | 3.2 | ±0.544 | A | yes | pass |
| Best team BA | 0.345 (season range 0.329–0.379) | 0.356 | ±0.027 | A | yes | pass |
| Most team HR per game | 2.598 (season range 2.161–3.214) | 2.672 | ±0.625 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 28.3 (season range 23.0–35.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±2.2 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.35 (season range 0.00–1.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.33 | A | yes | pass |
| BA leader (qualified) | 0.443 (season range 0.419–0.472) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.011 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.470 (season range 0.398–0.516) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.023 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 35 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8778 (data 0.8824); pitchers per team-game 4.34 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 71.7, 60.8, 50.7 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
