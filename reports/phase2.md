# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-02.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.6237 | 6.7500 | ±0.1700 | B | yes | pass |
| Batting average | 0.2807 | 0.2800 | ±0.0053 | B | yes | pass |
| On-base pct | 0.3782 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4355 | 0.4400 | ±0.0103 | B | yes | pass |
| HR per team-game | 1.0070 | 1.0500 | ±0.0516 | B |  | pass |
| BB per PA | 0.1047 | 0.1059 | ±0.0050 | B |  | pass |
| K per PA | 0.1962 | 0.1927 | ±0.0056 | B |  | pass |
| HBP per PA | 0.0336 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0995 | 1.0990 | ±0.1513 | B |  | pass |
| PA per team-game | 40.4380 | 40.3100 | ±1.0034 | B |  | pass |
| ERA | 6.0687 | 6.0800 | ±0.3083 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1027 | 0.1031 | ±0.0093 | A | yes | pass |
| PA per half-inning | 4.669 | 4.694 | ±0.055 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6415, 0.1653, 0.0905, 0.0492, 0.0258, 0.0276 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0621 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1250 | 0.1524 | ±0.0165 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1668 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.405 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5959 | 0.5836 | ±0.0339 | A | yes | pass |
| Home run differential per game | 1.046 | 0.888 | ±0.519 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0278 (limit 0.0402) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0358 | 0.0400 | -0.0042 | ±0.0101 | pass |
| 1 | 0.0609 | 0.0606 | +0.0003 | ±0.0103 | pass |
| 2 | 0.0788 | 0.0770 | +0.0018 | ±0.0102 | pass |
| 3 | 0.0912 | 0.0916 | -0.0004 | ±0.0101 | pass |
| 4 | 0.0972 | 0.0971 | +0.0001 | ±0.0102 | pass |
| 5 | 0.0965 | 0.0916 | +0.0049 | ±0.0102 | pass |
| 6 | 0.0916 | 0.0876 | +0.0040 | ±0.0101 | pass |
| 7 | 0.0824 | 0.0767 | +0.0057 | ±0.0102 | pass |
| 8 | 0.0712 | 0.0647 | +0.0065 | ±0.0101 | pass |
| 9 | 0.0603 | 0.0579 | +0.0024 | ±0.0101 | pass |
| 10 | 0.0530 | 0.0508 | +0.0022 | ±0.0101 | pass |
| 11 | 0.0445 | 0.0454 | -0.0009 | ±0.0101 | pass |
| 12 | 0.0356 | 0.0362 | -0.0006 | ±0.0101 | pass |
| 13 | 0.0274 | 0.0302 | -0.0028 | ±0.0101 | pass |
| 14 | 0.0205 | 0.0260 | -0.0055 | ±0.0100 | pass |
| 15+ | 0.0529 | 0.0664 | -0.0135 | ±0.0106 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 5.918 | 6.364 | ±0.516 | A | yes | pass |
| p4 batting vs mid pitching | 8.374 | 8.614 | ±0.648 | A | yes | pass |
| p4 batting vs low pitching | 10.472 | 9.820 | ±1.146 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.476 | 4.762 | ±0.566 | A | yes | pass |
| mid batting vs mid pitching | 6.557 | 6.724 | ±0.459 | A | yes | pass |
| mid batting vs low pitching | 8.707 | 8.457 | ±0.906 | A | yes | pass |
| low batting vs p4 pitching | 3.219 | 3.629 | ±0.638 | A | yes | pass |
| low batting vs mid pitching | 5.154 | 5.880 | ±0.676 | A | yes | FAIL |
| low batting vs low pitching | 7.080 | 7.046 | ±0.718 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.623 | 6.747 | ±0.214 | A | yes | pass |
| Team R/G SD across teams (all) | 1.121 | 1.162 | ±0.146 | A | yes | pass |
| Team RA/G mean (all) | 6.625 | 6.841 | ±0.285 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.791 | 1.596 | ±0.208 | A | yes | pass |
| Team R/G mean (p4) | 7.010 | 7.207 | ±0.320 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.927 | 0.793 | ±0.216 | A | yes | pass |
| Team RA/G mean (p4) | 5.273 | 5.767 | ±0.442 | A | yes | FAIL |
| Team RA/G SD across teams (p4) | 1.115 | 1.112 | ±0.308 | A | yes | pass |
| Team R/G mean (mid) | 6.566 | 6.668 | ±0.321 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.087 | 1.255 | ±0.220 | A | yes | pass |
| Team RA/G mean (mid) | 6.604 | 6.871 | ±0.352 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.525 | 1.377 | ±0.250 | A | yes | pass |
| Team R/G mean (low) | 6.447 | 6.553 | ±0.380 | A | yes | pass |
| Team R/G SD across teams (low) | 1.221 | 1.141 | ±0.271 | A | yes | pass |
| Team RA/G mean (low) | 7.622 | 7.560 | ±0.628 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.915 | 1.819 | ±0.431 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.95 vs data 7.56; pitchers sim 1.96 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2306 | 0.2385 | ±0.0136 | B | yes | pass |
| BA p50 | 0.2873 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3452 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3210 | 0.3366 | ±0.0108 | B | yes | FAIL |
| OBP p50 | 0.3821 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4437 | 0.4487 | ±0.0129 | B | yes | pass |
| ISO p10 | 0.0755 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1530 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2564 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1193 | 0.1075 | ±0.0251 | B | yes | pass |
| K_pct p50 | 0.1842 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2677 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0632 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1007 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1487 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.18 | 3.41 | ±0.621 | B | yes | pass |
| ERA p50 | 5.08 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.55 | 7.64 | ±1.280 | B | yes | pass |
| K9 p10 | 5.82 | 5.72 | ±0.673 | B | yes | pass |
| K9 p50 | 8.39 | 7.88 | ±0.928 | B | Phase 6 | pass |
| K9 p90 | 11.37 | 10.56 | ±1.309 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 785.0 (season range 768.0–809.0) | 821.1 (56-game eq. of 882) | ±28.3 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 7.100 (season range 3.000–13.000) | 5 | ±5.649 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 55.8 (season range 38.0–72.0) | 57 | ±18.4 | A | yes | pass |
| Teams with ERA < 4.00 | 23.1 (season range 15.0–36.0) | 12 | ±10.4 | A | yes | FAIL |
| Best team ERA | 2.731 (season range 2.204–3.380) | 3.2 | ±0.647 | A | yes | pass |
| Best team BA | 0.346 (season range 0.331–0.369) | 0.356 | ±0.022 | A | yes | pass |
| Most team HR per game | 2.541 (season range 2.143–3.339) | 2.672 | ±0.676 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 28.2 (season range 24.0–34.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±2.0 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.60 (season range 0.00–2.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.55 | A | yes | pass |
| BA leader (qualified) | 0.451 (season range 0.421–0.480) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.011 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.472 (season range 0.434–0.545) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.025 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 34 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8781 (data 0.8824); pitchers per team-game 4.32 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 71.9, 61.0, 50.8 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
