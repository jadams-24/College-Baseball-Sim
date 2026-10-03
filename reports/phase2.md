# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-03.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7137 | 6.7500 | ±0.1744 | B | yes | pass |
| Batting average | 0.2818 | 0.2800 | ±0.0053 | B | yes | pass |
| On-base pct | 0.3798 | 0.3805 | ±0.0055 | B | yes | pass |
| Slugging pct | 0.4404 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0524 | 1.0500 | ±0.0518 | B |  | pass |
| BB per PA | 0.1053 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1946 | 0.1927 | ±0.0055 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1038 | 1.0990 | ±0.1518 | B |  | pass |
| PA per team-game | 40.5902 | 40.3100 | ±1.0039 | B |  | pass |
| ERA | 6.1488 | 6.0800 | ±0.3101 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1042 | 0.1031 | ±0.0093 | A | yes | pass |
| PA per half-inning | 4.680 | 4.694 | ±0.056 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6371, 0.1672, 0.0915, 0.0501, 0.0263, 0.0279 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0631 | 0.0546 | ±0.0152 | B | yes | pass |
| Run-rule frequency | 0.1211 | 0.1524 | ±0.0170 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1613 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.361 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5878 | 0.5836 | ±0.0343 | A | yes | pass |
| Home run differential per game | 0.935 | 0.888 | ±0.527 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0354 (limit 0.0402) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0324 | 0.0400 | -0.0076 | ±0.0101 | pass |
| 1 | 0.0562 | 0.0606 | -0.0044 | ±0.0101 | pass |
| 2 | 0.0764 | 0.0770 | -0.0006 | ±0.0101 | pass |
| 3 | 0.0903 | 0.0916 | -0.0013 | ±0.0102 | pass |
| 4 | 0.0961 | 0.0971 | -0.0010 | ±0.0102 | pass |
| 5 | 0.0980 | 0.0916 | +0.0064 | ±0.0103 | pass |
| 6 | 0.0925 | 0.0876 | +0.0049 | ±0.0101 | pass |
| 7 | 0.0837 | 0.0767 | +0.0070 | ±0.0101 | pass |
| 8 | 0.0740 | 0.0647 | +0.0093 | ±0.0101 | pass |
| 9 | 0.0622 | 0.0579 | +0.0043 | ±0.0100 | pass |
| 10 | 0.0544 | 0.0508 | +0.0036 | ±0.0101 | pass |
| 11 | 0.0450 | 0.0454 | -0.0004 | ±0.0100 | pass |
| 12 | 0.0363 | 0.0362 | +0.0001 | ±0.0101 | pass |
| 13 | 0.0282 | 0.0302 | -0.0020 | ±0.0101 | pass |
| 14 | 0.0212 | 0.0260 | -0.0048 | ±0.0101 | pass |
| 15+ | 0.0532 | 0.0664 | -0.0132 | ±0.0108 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.213 | 6.364 | ±0.511 | A | yes | pass |
| p4 batting vs mid pitching | 8.655 | 8.614 | ±0.645 | A | yes | pass |
| p4 batting vs low pitching | 9.550 | 9.820 | ±1.223 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.602 | 4.762 | ±0.562 | A | yes | pass |
| mid batting vs mid pitching | 6.650 | 6.724 | ±0.467 | A | yes | pass |
| mid batting vs low pitching | 8.104 | 8.457 | ±0.892 | A | yes | pass |
| low batting vs p4 pitching | 3.703 | 3.629 | ±0.691 | A | yes | pass |
| low batting vs mid pitching | 5.591 | 5.880 | ±0.663 | A | yes | pass |
| low batting vs low pitching | 7.124 | 7.046 | ±0.731 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.714 | 6.747 | ±0.218 | A | yes | pass |
| Team R/G SD across teams (all) | 1.032 | 1.162 | ±0.144 | A | yes | pass |
| Team RA/G mean (all) | 6.715 | 6.841 | ±0.288 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.636 | 1.596 | ±0.220 | A | yes | pass |
| Team R/G mean (p4) | 7.197 | 7.207 | ±0.313 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.804 | 0.793 | ±0.219 | A | yes | pass |
| Team RA/G mean (p4) | 5.536 | 5.767 | ±0.445 | A | watch item: mismatch interaction (Phase 6b) | pass |
| Team RA/G SD across teams (p4) | 1.073 | 1.112 | ±0.308 | A | yes | pass |
| Team R/G mean (mid) | 6.582 | 6.668 | ±0.322 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.052 | 1.255 | ±0.221 | A | yes | pass |
| Team RA/G mean (mid) | 6.759 | 6.871 | ±0.363 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.418 | 1.377 | ±0.252 | A | yes | pass |
| Team R/G mean (low) | 6.594 | 6.553 | ±0.388 | A | yes | pass |
| Team R/G SD across teams (low) | 1.026 | 1.141 | ±0.263 | A | yes | pass |
| Team RA/G mean (low) | 7.478 | 7.560 | ±0.647 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.767 | 1.819 | ±0.434 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.60 vs data 7.56; pitchers sim 1.94 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2335 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2892 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3450 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3249 | 0.3366 | ±0.0108 | B | watch item: mismatch interaction (Phase 6b) | FAIL |
| OBP p50 | 0.3844 | 0.3889 | ±0.0136 | B | yes | pass |
| OBP p90 | 0.4438 | 0.4487 | ±0.0131 | B | yes | pass |
| ISO p10 | 0.0803 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1577 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2624 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1188 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1822 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2653 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0644 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1015 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1487 | 0.1584 | ±0.0160 | B | yes | pass |
| ERA p10 | 3.37 | 3.41 | ±0.618 | B | yes | pass |
| ERA p50 | 5.19 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.61 | 7.64 | ±1.278 | B | yes | pass |
| K9 p10 | 5.78 | 5.72 | ±0.675 | B | yes | pass |
| K9 p50 | 8.32 | 7.88 | ±0.925 | B | Phase 6 | pass |
| K9 p90 | 11.33 | 10.56 | ±1.306 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 789.0 (season range 747.0–831.0) | 821.1 (56-game eq. of 882) | ±41.8 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 4.700 (season range 1.000–9.000) | 5 | ±4.876 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 42.8 (season range 28.0–53.0) | 57 | ±15.1 | A | yes | pass |
| Teams with ERA < 4.00 | 13.6 (season range 7.0–21.0) | 12 | ±8.9 | A | yes | pass |
| Best team ERA | 3.081 (season range 2.718–3.515) | 3.2 | ±0.507 | A | yes | pass |
| Best team BA | 0.339 (season range 0.327–0.351) | 0.356 | ±0.013 | A | yes | FAIL |
| Most team HR per game | 2.527 (season range 2.125–3.232) | 2.672 | ±0.560 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 29.1 (season range 24.0–36.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±2.4 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.50 (season range 0.00–2.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.41 | A | yes | pass |
| BA leader (qualified) | 0.445 (season range 0.407–0.483) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.013 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.472 (season range 0.402–0.541) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.023 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 36 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8790 (data 0.8824); pitchers per team-game 4.35 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 71.4, 60.8, 50.8 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
