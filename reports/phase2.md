# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-02.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7491 | 6.7500 | ±0.1603 | B | yes | pass |
| Batting average | 0.2821 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3801 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4427 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0673 | 1.0500 | ±0.0522 | B |  | pass |
| BB per PA | 0.1056 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1947 | 0.1927 | ±0.0055 | B |  | pass |
| HBP per PA | 0.0336 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0844 | 1.0990 | ±0.1502 | B |  | pass |
| PA per team-game | 40.5163 | 40.3100 | ±1.0034 | B |  | pass |
| ERA | 6.2233 | 6.0800 | ±0.3053 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1051 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.685 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6356, 0.1668, 0.0925, 0.0501, 0.0268, 0.0282 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0609 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1283 | 0.1524 | ±0.0167 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1705 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.376 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5988 | 0.5836 | ±0.0341 | A | yes | pass |
| Home run differential per game | 1.155 | 0.888 | ±0.523 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0372 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0322 | 0.0400 | -0.0078 | ±0.0101 | pass |
| 1 | 0.0574 | 0.0606 | -0.0032 | ±0.0102 | pass |
| 2 | 0.0765 | 0.0770 | -0.0005 | ±0.0101 | pass |
| 3 | 0.0879 | 0.0916 | -0.0037 | ±0.0102 | pass |
| 4 | 0.0942 | 0.0971 | -0.0029 | ±0.0102 | pass |
| 5 | 0.0955 | 0.0916 | +0.0039 | ±0.0101 | pass |
| 6 | 0.0917 | 0.0876 | +0.0041 | ±0.0102 | pass |
| 7 | 0.0849 | 0.0767 | +0.0082 | ±0.0101 | pass |
| 8 | 0.0741 | 0.0647 | +0.0094 | ±0.0101 | pass |
| 9 | 0.0635 | 0.0579 | +0.0056 | ±0.0101 | pass |
| 10 | 0.0551 | 0.0508 | +0.0043 | ±0.0101 | pass |
| 11 | 0.0463 | 0.0454 | +0.0009 | ±0.0101 | pass |
| 12 | 0.0372 | 0.0362 | +0.0010 | ±0.0101 | pass |
| 13 | 0.0290 | 0.0302 | -0.0012 | ±0.0101 | pass |
| 14 | 0.0216 | 0.0260 | -0.0044 | ±0.0100 | pass |
| 15+ | 0.0529 | 0.0664 | -0.0135 | ±0.0103 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.319 | 6.364 | ±0.502 | A | yes | pass |
| p4 batting vs mid pitching | 8.838 | 8.614 | ±0.657 | A | yes | pass |
| p4 batting vs low pitching | 11.000 | 9.820 | ±1.207 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.731 | 4.762 | ±0.557 | A | yes | pass |
| mid batting vs mid pitching | 6.660 | 6.724 | ±0.457 | A | yes | pass |
| mid batting vs low pitching | 8.720 | 8.457 | ±0.855 | A | yes | pass |
| low batting vs p4 pitching | 3.473 | 3.629 | ±0.675 | A | yes | pass |
| low batting vs mid pitching | 5.282 | 5.880 | ±0.671 | A | yes | pass |
| low batting vs low pitching | 6.932 | 7.046 | ±0.703 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.749 | 6.747 | ±0.207 | A | yes | pass |
| Team R/G SD across teams (all) | 1.197 | 1.162 | ±0.146 | A | yes | pass |
| Team RA/G mean (all) | 6.751 | 6.841 | ±0.280 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.658 | 1.596 | ±0.206 | A | yes | pass |
| Team R/G mean (p4) | 7.441 | 7.207 | ±0.314 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.860 | 0.793 | ±0.220 | A | yes | pass |
| Team RA/G mean (p4) | 5.622 | 5.767 | ±0.435 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.097 | 1.112 | ±0.307 | A | yes | pass |
| Team R/G mean (mid) | 6.675 | 6.668 | ±0.314 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.221 | 1.255 | ±0.223 | A | yes | pass |
| Team RA/G mean (mid) | 6.752 | 6.871 | ±0.351 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.474 | 1.377 | ±0.242 | A | yes | pass |
| Team R/G mean (low) | 6.380 | 6.553 | ±0.375 | A | yes | pass |
| Team R/G SD across teams (low) | 1.150 | 1.141 | ±0.263 | A | yes | pass |
| Team RA/G mean (low) | 7.552 | 7.560 | ±0.602 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.792 | 1.819 | ±0.429 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.62 vs data 7.56; pitchers sim 2.00 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2380 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2921 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3475 | 0.3533 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3287 | 0.3366 | ±0.0108 | B | yes | pass |
| OBP p50 | 0.3872 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4467 | 0.4487 | ±0.0129 | B | yes | pass |
| ISO p10 | 0.0868 | 0.0755 | ±0.0189 | B | yes | pass |
| ISO p50 | 0.1669 | 0.1667 | ±0.0199 | B | yes | pass |
| ISO p90 | 0.2755 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1184 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1834 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2636 | 0.2689 | ±0.0411 | B | yes | pass |
| BB_pct p10 | 0.0654 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1028 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1501 | 0.1584 | ±0.0160 | B | yes | pass |
| ERA p10 | 3.17 | 3.41 | ±0.620 | B | yes | pass |
| ERA p50 | 5.00 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.56 | 7.64 | ±1.277 | B | yes | pass |
| K9 p10 | 5.88 | 5.72 | ±0.676 | B | yes | pass |
| K9 p50 | 8.56 | 7.88 | ±0.930 | B | Phase 6 | pass |
| K9 p90 | 11.70 | 10.56 | ±1.308 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 870.4 (season range 845.0–902.0) | 882 | ±30.5 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 8.000 (season range 3.000–15.000) | 5 | ±8.055 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 62.0 (season range 50.0–78.0) | 57 | ±19.2 | A | yes | pass |
| Teams with ERA < 4.00 | 16.5 (season range 10.0–25.0) | 12 | ±8.9 | A | yes | pass |
| Best team ERA | 2.979 (season range 2.417–3.421) | 3.2 | ±0.554 | A | yes | pass |
| Best team BA | 0.346 (season range 0.334–0.369) | 0.356 | ±0.023 | A | yes | pass |
| Most team HR per game | 2.679 (season range 2.161–3.607) | 2.672 | ±0.771 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 29.7 (season range 26.0–35.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.8 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.95 (season range 0.00–5.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.98 | A | yes | pass |
| BA leader (qualified) | 0.442 (season range 0.417–0.476) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.011 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.499 (season range 0.428–0.581) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.025 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 35 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8823 (data 0.8824); pitchers per team-game 4.60 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 70.5, 60.1, 52.3 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
