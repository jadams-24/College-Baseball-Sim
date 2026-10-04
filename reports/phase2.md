# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-04.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7273 | 6.7500 | ±0.1734 | B | yes | pass |
| Batting average | 0.2820 | 0.2800 | ±0.0053 | B | yes | pass |
| On-base pct | 0.3799 | 0.3805 | ±0.0054 | B | yes | pass |
| Slugging pct | 0.4410 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0552 | 1.0500 | ±0.0518 | B |  | pass |
| BB per PA | 0.1053 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1945 | 0.1927 | ±0.0055 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0870 | 1.0990 | ±0.1517 | B |  | pass |
| PA per team-game | 40.6742 | 40.3100 | ±1.0036 | B |  | pass |
| ERA | 6.1609 | 6.0800 | ±0.3095 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1045 | 0.1031 | ±0.0093 | A | yes | pass |
| PA per half-inning | 4.690 | 4.694 | ±0.056 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6372, 0.1664, 0.0919, 0.0500, 0.0265, 0.0280 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0636 | 0.0546 | ±0.0152 | B | yes | pass |
| Run-rule frequency | 0.1217 | 0.1524 | ±0.0170 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1624 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.366 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5890 | 0.5836 | ±0.0343 | A | yes | pass |
| Home run differential per game | 0.937 | 0.888 | ±0.525 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0352 (limit 0.0402) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0324 | 0.0400 | -0.0076 | ±0.0102 | pass |
| 1 | 0.0571 | 0.0606 | -0.0035 | ±0.0101 | pass |
| 2 | 0.0766 | 0.0770 | -0.0004 | ±0.0102 | pass |
| 3 | 0.0890 | 0.0916 | -0.0026 | ±0.0103 | pass |
| 4 | 0.0955 | 0.0971 | -0.0016 | ±0.0103 | pass |
| 5 | 0.0971 | 0.0916 | +0.0055 | ±0.0102 | pass |
| 6 | 0.0919 | 0.0876 | +0.0043 | ±0.0102 | pass |
| 7 | 0.0835 | 0.0767 | +0.0068 | ±0.0102 | pass |
| 8 | 0.0741 | 0.0647 | +0.0094 | ±0.0101 | pass |
| 9 | 0.0626 | 0.0579 | +0.0047 | ±0.0101 | pass |
| 10 | 0.0544 | 0.0508 | +0.0036 | ±0.0101 | pass |
| 11 | 0.0459 | 0.0454 | +0.0005 | ±0.0101 | pass |
| 12 | 0.0368 | 0.0362 | +0.0006 | ±0.0101 | pass |
| 13 | 0.0287 | 0.0302 | -0.0015 | ±0.0101 | pass |
| 14 | 0.0208 | 0.0260 | -0.0052 | ±0.0101 | pass |
| 15+ | 0.0537 | 0.0664 | -0.0127 | ±0.0107 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.139 | 6.364 | ±0.513 | A | yes | pass |
| p4 batting vs mid pitching | 8.530 | 8.614 | ±0.659 | A | yes | pass |
| p4 batting vs low pitching | 9.581 | 9.820 | ±1.234 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.575 | 4.762 | ±0.572 | A | yes | pass |
| mid batting vs mid pitching | 6.675 | 6.724 | ±0.463 | A | yes | pass |
| mid batting vs low pitching | 8.155 | 8.457 | ±0.888 | A | yes | pass |
| low batting vs p4 pitching | 3.669 | 3.629 | ±0.668 | A | yes | pass |
| low batting vs mid pitching | 5.694 | 5.880 | ±0.659 | A | yes | pass |
| low batting vs low pitching | 7.189 | 7.046 | ±0.721 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.727 | 6.747 | ±0.217 | A | yes | pass |
| Team R/G SD across teams (all) | 1.009 | 1.162 | ±0.145 | A | yes | FAIL |
| Team RA/G mean (all) | 6.729 | 6.841 | ±0.288 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.649 | 1.596 | ±0.214 | A | yes | pass |
| Team R/G mean (p4) | 7.118 | 7.207 | ±0.321 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.780 | 0.793 | ±0.216 | A | yes | pass |
| Team RA/G mean (p4) | 5.478 | 5.767 | ±0.445 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.085 | 1.112 | ±0.305 | A | yes | pass |
| Team R/G mean (mid) | 6.604 | 6.668 | ±0.318 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.037 | 1.255 | ±0.219 | A | yes | pass |
| Team RA/G mean (mid) | 6.776 | 6.871 | ±0.359 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.432 | 1.377 | ±0.247 | A | yes | pass |
| Team R/G mean (low) | 6.660 | 6.553 | ±0.384 | A | yes | pass |
| Team R/G SD across teams (low) | 1.025 | 1.141 | ±0.265 | A | yes | pass |
| Team RA/G mean (low) | 7.538 | 7.560 | ±0.638 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.743 | 1.819 | ±0.421 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.61 vs data 7.56; pitchers sim 1.94 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2339 | 0.2385 | ±0.0136 | B | yes | pass |
| BA p50 | 0.2892 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3449 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3260 | 0.3366 | ±0.0109 | B | watch item: offense extremes compressed | pass |
| OBP p50 | 0.3849 | 0.3889 | ±0.0136 | B | yes | pass |
| OBP p90 | 0.4438 | 0.4487 | ±0.0130 | B | yes | pass |
| ISO p10 | 0.0802 | 0.0755 | ±0.0189 | B | yes | pass |
| ISO p50 | 0.1586 | 0.1667 | ±0.0199 | B | yes | pass |
| ISO p90 | 0.2619 | 0.2775 | ±0.0406 | B | yes | pass |
| K_pct p10 | 0.1184 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1823 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2642 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0640 | 0.0668 | ±0.0107 | B | yes | pass |
| BB_pct p50 | 0.1018 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1486 | 0.1584 | ±0.0160 | B | yes | pass |
| ERA p10 | 3.32 | 3.41 | ±0.621 | B | yes | pass |
| ERA p50 | 5.19 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.57 | 7.64 | ±1.277 | B | yes | pass |
| K9 p10 | 5.78 | 5.72 | ±0.676 | B | yes | pass |
| K9 p50 | 8.34 | 7.88 | ±0.925 | B | Phase 6 | pass |
| K9 p90 | 11.35 | 10.56 | ±1.306 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 787.2 (season range 747.0–815.0) | 821.1 (56-game eq. of 882) | ±33.9 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 4.250 (season range 1.000–13.000) | 5 | ±5.817 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 45.7 (season range 30.0–64.0) | 57 | ±18.8 | A | yes | pass |

## National team leaders (NCAA.com team pages, 2024–2026)

Rates and counts of teams (real seasons include the postseason and non-D1 games). A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Teams with ERA < 4.00 | 14.6 (season range 5.0–23.0) | 6.0–12.0 (2024 6.0, 2025 12.0, 2026 12.0) | ±3.0 | A | yes | pass |
| Best team ERA | 3.037 (season range 2.612–3.526) | 3.060–3.780 (2024 3.780, 2025 3.060, 2026 3.220) | ±0.209 | A | yes | pass |
| Best team BA | 0.336 (season range 0.323–0.363) | 0.337–0.359 (2024 0.359, 2025 0.337, 2026 0.356) | ±0.006 | A | yes | pass |
| Most team HR per game | 2.488 (season range 2.107–2.857) | 2.400–2.672 (2024 2.607, 2025 2.400, 2026 2.672) | ±0.146 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 27.9 (season range 25.0–33.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.5 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.25 (season range 0.00–2.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.37 | A | yes | pass |
| BA leader (qualified) | 0.446 (season range 0.429–0.470) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.008 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.460 (season range 0.417–0.514) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.016 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 33 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8789 (data 0.8824); pitchers per team-game 4.36 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 71.5, 60.7, 50.8 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
