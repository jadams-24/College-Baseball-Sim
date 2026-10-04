# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 40 simulated 56-game seasons, a new league per season, seeds 20251000–20251039. Generated 2026-10-04.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 40 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7259 | 6.7500 | ±0.1626 | B | yes | pass |
| Batting average | 0.2819 | 0.2800 | ±0.0051 | B | yes | pass |
| On-base pct | 0.3798 | 0.3805 | ±0.0052 | B | yes | pass |
| Slugging pct | 0.4411 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0576 | 1.0500 | ±0.0512 | B |  | pass |
| BB per PA | 0.1053 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1943 | 0.1927 | ±0.0052 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0877 | 1.0990 | ±0.1507 | B |  | pass |
| PA per team-game | 40.6627 | 40.3100 | ±1.0020 | B |  | pass |
| ERA | 6.1592 | 6.0800 | ±0.3055 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1044 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.688 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6373, 0.1663, 0.0919, 0.0499, 0.0265, 0.0280 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0635 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1213 | 0.1524 | ±0.0161 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1624 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.374 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5892 | 0.5836 | ±0.0340 | A | yes | pass |
| Home run differential per game | 0.947 | 0.888 | ±0.517 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0341 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0327 | 0.0400 | -0.0073 | ±0.0101 | pass |
| 1 | 0.0569 | 0.0606 | -0.0037 | ±0.0101 | pass |
| 2 | 0.0766 | 0.0770 | -0.0004 | ±0.0101 | pass |
| 3 | 0.0894 | 0.0916 | -0.0022 | ±0.0101 | pass |
| 4 | 0.0959 | 0.0971 | -0.0012 | ±0.0101 | pass |
| 5 | 0.0966 | 0.0916 | +0.0050 | ±0.0101 | pass |
| 6 | 0.0920 | 0.0876 | +0.0044 | ±0.0101 | pass |
| 7 | 0.0836 | 0.0767 | +0.0069 | ±0.0101 | pass |
| 8 | 0.0737 | 0.0647 | +0.0090 | ±0.0100 | pass |
| 9 | 0.0629 | 0.0579 | +0.0050 | ±0.0101 | pass |
| 10 | 0.0540 | 0.0508 | +0.0032 | ±0.0100 | pass |
| 11 | 0.0455 | 0.0454 | +0.0001 | ±0.0100 | pass |
| 12 | 0.0367 | 0.0362 | +0.0005 | ±0.0100 | pass |
| 13 | 0.0285 | 0.0302 | -0.0017 | ±0.0100 | pass |
| 14 | 0.0209 | 0.0260 | -0.0051 | ±0.0100 | pass |
| 15+ | 0.0540 | 0.0664 | -0.0124 | ±0.0103 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.106 | 6.364 | ±0.503 | A | yes | pass |
| p4 batting vs mid pitching | 8.536 | 8.614 | ±0.636 | A | yes | pass |
| p4 batting vs low pitching | 9.580 | 9.820 | ±1.113 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.557 | 4.762 | ±0.546 | A | yes | pass |
| mid batting vs mid pitching | 6.683 | 6.724 | ±0.457 | A | yes | pass |
| mid batting vs low pitching | 8.192 | 8.457 | ±0.820 | A | yes | pass |
| low batting vs p4 pitching | 3.644 | 3.629 | ±0.629 | A | yes | pass |
| low batting vs mid pitching | 5.674 | 5.880 | ±0.633 | A | yes | pass |
| low batting vs low pitching | 7.188 | 7.046 | ±0.705 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.726 | 6.747 | ±0.209 | A | yes | pass |
| Team R/G SD across teams (all) | 1.015 | 1.162 | ±0.143 | A | watch item: offense extremes compressed | FAIL |
| Team RA/G mean (all) | 6.727 | 6.841 | ±0.281 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.680 | 1.596 | ±0.203 | A | yes | pass |
| Team R/G mean (p4) | 7.105 | 7.207 | ±0.307 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.786 | 0.793 | ±0.214 | A | yes | pass |
| Team RA/G mean (p4) | 5.447 | 5.767 | ±0.432 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.066 | 1.112 | ±0.302 | A | yes | pass |
| Team R/G mean (mid) | 6.610 | 6.668 | ±0.312 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.053 | 1.255 | ±0.218 | A | yes | pass |
| Team RA/G mean (mid) | 6.782 | 6.871 | ±0.350 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.464 | 1.377 | ±0.243 | A | yes | pass |
| Team R/G mean (low) | 6.654 | 6.553 | ±0.372 | A | yes | pass |
| Team R/G SD across teams (low) | 1.020 | 1.141 | ±0.261 | A | yes | pass |
| Team RA/G mean (low) | 7.546 | 7.560 | ±0.603 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.782 | 1.819 | ±0.420 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.62 vs data 7.56; pitchers sim 1.94 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2337 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2892 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3448 | 0.3533 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3257 | 0.3366 | ±0.0107 | B | watch item: offense extremes compressed | FAIL |
| OBP p50 | 0.3846 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4435 | 0.4487 | ±0.0129 | B | yes | pass |
| ISO p10 | 0.0804 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1588 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2625 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1181 | 0.1075 | ±0.0249 | B | yes | pass |
| K_pct p50 | 0.1819 | 0.1829 | ±0.0139 | B | yes | pass |
| K_pct p90 | 0.2637 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0641 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1018 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1486 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.31 | 3.41 | ±0.619 | B | yes | pass |
| ERA p50 | 5.18 | 5.12 | ±0.665 | B | yes | pass |
| ERA p90 | 7.58 | 7.64 | ±1.273 | B | yes | pass |
| K9 p10 | 5.76 | 5.72 | ±0.670 | B | yes | pass |
| K9 p50 | 8.33 | 7.88 | ±0.922 | B | Phase 6 | pass |
| K9 p90 | 11.39 | 10.56 | ±1.303 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 785.1 (season range 747.0–815.0) | 821.1 (56-game eq. of 882) | ±32.4 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 5.100 (season range 1.000–13.000) | 5 | ±5.600 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 45.9 (season range 30.0–64.0) | 57 | ±17.2 | A | yes | pass |

## National team leaders (NCAA.com team pages, 2024–2026)

Rates and counts of teams (real seasons include the postseason and non-D1 games). A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Teams with ERA < 4.00 | 15.5 (season range 5.0–26.0) | 6.0–12.0 (2024 6.0, 2025 12.0, 2026 12.0) | ±2.2 | A | watch item: teams under 4.00 ERA | FAIL |
| Best team ERA | 2.980 (season range 2.332–3.526) | 3.060–3.780 (2024 3.780, 2025 3.060, 2026 3.220) | ±0.133 | A | yes | pass |
| Best team BA | 0.338 (season range 0.323–0.363) | 0.337–0.359 (2024 0.359, 2025 0.337, 2026 0.356) | ±0.004 | A | yes | pass |
| Most team HR per game | 2.506 (season range 2.089–3.089) | 2.400–2.672 (2024 2.607, 2025 2.400, 2026 2.672) | ±0.118 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 27.9 (season range 23.0–33.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.3 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.30 (season range 0.00–2.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.31 | A | yes | pass |
| BA leader (qualified) | 0.444 (season range 0.418–0.486) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.007 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.462 (season range 0.409–0.529) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.014 | A | yes | pass |
| Most HR by any player, all 40 seasons (hard ceiling) | 33 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8789 (data 0.8824); pitchers per team-game 4.36 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 71.5, 60.7, 50.8 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
