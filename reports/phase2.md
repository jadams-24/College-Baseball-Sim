# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 40 simulated 56-game seasons, a new league per season, seeds 20251000–20251039. Generated 2026-10-08.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 40 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.6448 | 6.7500 | ±0.1640 | B | yes | pass |
| Batting average | 0.2817 | 0.2800 | ±0.0051 | B | yes | pass |
| On-base pct | 0.3795 | 0.3805 | ±0.0052 | B | yes | pass |
| Slugging pct | 0.4406 | 0.4400 | ±0.0101 | B | yes | pass |
| HR per team-game | 1.0570 | 1.0500 | ±0.0511 | B |  | pass |
| BB per PA | 0.1049 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1944 | 0.1927 | ±0.0052 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1044 | 1.0990 | ±0.1506 | B |  | pass |
| PA per team-game | 40.6958 | 40.3100 | ±1.0027 | B |  | pass |
| ERA | 6.0650 | 6.0800 | ±0.3059 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1023 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.687 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6391, 0.1670, 0.0917, 0.0492, 0.0261, 0.0270 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0633 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1164 | 0.1524 | ±0.0161 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1563 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.326 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5872 | 0.5836 | ±0.0338 | A | yes | pass |
| Home run differential per game | 0.888 | 0.888 | ±0.516 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0358 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0337 | 0.0400 | -0.0063 | ±0.0100 | pass |
| 1 | 0.0581 | 0.0606 | -0.0025 | ±0.0101 | pass |
| 2 | 0.0780 | 0.0770 | +0.0010 | ±0.0101 | pass |
| 3 | 0.0900 | 0.0916 | -0.0016 | ±0.0101 | pass |
| 4 | 0.0964 | 0.0971 | -0.0007 | ±0.0101 | pass |
| 5 | 0.0974 | 0.0916 | +0.0058 | ±0.0101 | pass |
| 6 | 0.0924 | 0.0876 | +0.0048 | ±0.0101 | pass |
| 7 | 0.0845 | 0.0767 | +0.0078 | ±0.0100 | pass |
| 8 | 0.0741 | 0.0647 | +0.0094 | ±0.0100 | pass |
| 9 | 0.0624 | 0.0579 | +0.0045 | ±0.0101 | pass |
| 10 | 0.0533 | 0.0508 | +0.0025 | ±0.0100 | pass |
| 11 | 0.0454 | 0.0454 | -0.0000 | ±0.0101 | pass |
| 12 | 0.0357 | 0.0362 | -0.0005 | ±0.0101 | pass |
| 13 | 0.0275 | 0.0302 | -0.0027 | ±0.0100 | pass |
| 14 | 0.0201 | 0.0260 | -0.0059 | ±0.0100 | pass |
| 15+ | 0.0509 | 0.0664 | -0.0155 | ±0.0103 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.067 | 6.364 | ±0.503 | A | yes | pass |
| p4 batting vs mid pitching | 8.410 | 8.614 | ±0.634 | A | yes | pass |
| p4 batting vs low pitching | 9.529 | 9.820 | ±1.099 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.491 | 4.762 | ±0.547 | A | yes | pass |
| mid batting vs mid pitching | 6.619 | 6.724 | ±0.458 | A | yes | pass |
| mid batting vs low pitching | 8.037 | 8.457 | ±0.827 | A | yes | pass |
| low batting vs p4 pitching | 3.597 | 3.629 | ±0.637 | A | yes | pass |
| low batting vs mid pitching | 5.582 | 5.880 | ±0.629 | A | yes | pass |
| low batting vs low pitching | 7.078 | 7.046 | ±0.707 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.645 | 6.747 | ±0.210 | A | yes | pass |
| Team R/G SD across teams (all) | 1.020 | 1.162 | ±0.143 | A | watch item: offense extremes compressed | pass |
| Team RA/G mean (all) | 6.645 | 6.841 | ±0.282 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.661 | 1.596 | ±0.203 | A | yes | pass |
| Team R/G mean (p4) | 6.995 | 7.207 | ±0.306 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.777 | 0.793 | ±0.215 | A | yes | pass |
| Team RA/G mean (p4) | 5.429 | 5.767 | ±0.432 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.092 | 1.112 | ±0.302 | A | yes | pass |
| Team R/G mean (mid) | 6.543 | 6.668 | ±0.314 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.065 | 1.255 | ±0.218 | A | yes | pass |
| Team RA/G mean (mid) | 6.699 | 6.871 | ±0.350 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.452 | 1.377 | ±0.243 | A | yes | pass |
| Team R/G mean (low) | 6.571 | 6.553 | ±0.373 | A | yes | pass |
| Team R/G SD across teams (low) | 1.028 | 1.141 | ±0.263 | A | yes | pass |
| Team RA/G mean (low) | 7.418 | 7.560 | ±0.604 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.777 | 1.819 | ±0.423 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.50 vs data 7.56; pitchers sim 2.06 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2324 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2888 | 0.2959 | ±0.0148 | B | yes | pass |
| BA p90 | 0.3452 | 0.3533 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3238 | 0.3366 | ±0.0107 | B | watch item: offense extremes compressed | FAIL |
| OBP p50 | 0.3838 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4439 | 0.4487 | ±0.0129 | B | yes | pass |
| ISO p10 | 0.0794 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1582 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2638 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1169 | 0.1075 | ±0.0249 | B | yes | pass |
| K_pct p50 | 0.1818 | 0.1829 | ±0.0139 | B | yes | pass |
| K_pct p90 | 0.2645 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0630 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1011 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1488 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.27 | 3.41 | ±0.620 | B | yes | pass |
| ERA p50 | 5.15 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.67 | 7.64 | ±1.274 | B | yes | pass |
| K9 p10 | 5.71 | 5.72 | ±0.670 | B | yes | pass |
| K9 p50 | 8.31 | 7.88 | ±0.922 | B | Phase 6 | pass |
| K9 p90 | 11.36 | 10.56 | ±1.304 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 806.6 (season range 763.0–840.0) | 821.1 (56-game eq. of 882) | ±34.7 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 6.800 (season range 0.000–13.000) | 5 | ±5.645 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 52.8 (season range 38.0–72.0) | 57 | ±19.4 | A | yes | pass |

## National team leaders (NCAA.com team pages, 2024–2026)

Rates and counts of teams on full seasons: real seasons include conference tournaments, the NCAA tournament and non-D1 games; the sim's its regular season plus its postseason when the Phase 7 world is on (the rest of this report is the regular season). A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Teams with ERA < 4.00 | 15.4 (season range 6.0–28.0) | 6.0–12.0 (2024 6.0, 2025 12.0, 2026 12.0) | ±2.3 | A | watch item: teams under 4.00 ERA | FAIL |
| Best team ERA | 3.043 (season range 2.184–3.661) | 3.060–3.780 (2024 3.780, 2025 3.060, 2026 3.220) | ±0.150 | A | yes | pass |
| Best team BA | 0.338 (season range 0.322–0.353) | 0.337–0.359 (2024 0.359, 2025 0.337, 2026 0.356) | ±0.004 | A | yes | pass |
| Most team HR per game | 2.466 (season range 2.040–3.258) | 2.400–2.672 (2024 2.607, 2025 2.400, 2026 2.672) | ±0.115 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 28.7 (season range 23.7–35.7) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.2 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.33 (season range 0.00–3.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.29 | A | yes | pass |
| BA leader (qualified) | 0.446 (season range 0.421–0.489) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.009 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.469 (season range 0.409–0.570) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.013 | A | yes | pass |
| Most HR by any player, all 40 seasons (hard ceiling) | 33 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8770 (data 0.8824); pitchers per team-game 4.32 (data 4.298)
- Weekend starts by a team's top three starters 0.808 (data 0.789); weekend starters per team 6.19 (data 6.48)
- Innings of a team's three busiest pitchers 69.6, 58.5, 48.3 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
