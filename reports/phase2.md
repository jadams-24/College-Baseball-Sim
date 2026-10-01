# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-01.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7265 | 6.7500 | ±0.1603 | B | yes | pass |
| Batting average | 0.2816 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3796 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4418 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0655 | 1.0500 | ±0.0522 | B |  | pass |
| BB per PA | 0.1057 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1950 | 0.1927 | ±0.0056 | B |  | pass |
| HBP per PA | 0.0336 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0834 | 1.0990 | ±0.1501 | B |  | pass |
| PA per team-game | 40.5034 | 40.3100 | ±1.0038 | B |  | pass |
| ERA | 6.2028 | 6.0800 | ±0.3057 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1048 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.683 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6361, 0.1673, 0.0918, 0.0501, 0.0266, 0.0281 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0612 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1278 | 0.1524 | ±0.0169 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1715 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.364 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5977 | 0.5836 | ±0.0342 | A | yes | pass |
| Home run differential per game | 1.140 | 0.888 | ±0.525 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0362 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0328 | 0.0400 | -0.0072 | ±0.0101 | pass |
| 1 | 0.0584 | 0.0606 | -0.0022 | ±0.0101 | pass |
| 2 | 0.0759 | 0.0770 | -0.0011 | ±0.0101 | pass |
| 3 | 0.0883 | 0.0916 | -0.0033 | ±0.0101 | pass |
| 4 | 0.0951 | 0.0971 | -0.0020 | ±0.0101 | pass |
| 5 | 0.0963 | 0.0916 | +0.0047 | ±0.0101 | pass |
| 6 | 0.0913 | 0.0876 | +0.0037 | ±0.0101 | pass |
| 7 | 0.0836 | 0.0767 | +0.0069 | ±0.0101 | pass |
| 8 | 0.0739 | 0.0647 | +0.0092 | ±0.0101 | pass |
| 9 | 0.0624 | 0.0579 | +0.0045 | ±0.0101 | pass |
| 10 | 0.0549 | 0.0508 | +0.0041 | ±0.0101 | pass |
| 11 | 0.0470 | 0.0454 | +0.0016 | ±0.0100 | pass |
| 12 | 0.0377 | 0.0362 | +0.0015 | ±0.0101 | pass |
| 13 | 0.0288 | 0.0302 | -0.0014 | ±0.0101 | pass |
| 14 | 0.0213 | 0.0260 | -0.0047 | ±0.0100 | pass |
| 15+ | 0.0522 | 0.0664 | -0.0142 | ±0.0104 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.257 | 6.364 | ±0.505 | A | yes | pass |
| p4 batting vs mid pitching | 8.935 | 8.614 | ±0.647 | A | yes | pass |
| p4 batting vs low pitching | 10.830 | 9.820 | ±1.184 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.692 | 4.762 | ±0.544 | A | yes | pass |
| mid batting vs mid pitching | 6.652 | 6.724 | ±0.457 | A | yes | pass |
| mid batting vs low pitching | 8.660 | 8.457 | ±0.859 | A | yes | pass |
| low batting vs p4 pitching | 3.423 | 3.629 | ±0.679 | A | yes | pass |
| low batting vs mid pitching | 5.290 | 5.880 | ±0.662 | A | yes | pass |
| low batting vs low pitching | 6.898 | 7.046 | ±0.703 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.726 | 6.747 | ±0.207 | A | yes | pass |
| Team R/G SD across teams (all) | 1.200 | 1.162 | ±0.146 | A | yes | pass |
| Team RA/G mean (all) | 6.728 | 6.841 | ±0.280 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.651 | 1.596 | ±0.204 | A | yes | pass |
| Team R/G mean (p4) | 7.414 | 7.207 | ±0.306 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.848 | 0.793 | ±0.221 | A | yes | pass |
| Team RA/G mean (p4) | 5.568 | 5.767 | ±0.435 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.123 | 1.112 | ±0.305 | A | yes | pass |
| Team R/G mean (mid) | 6.658 | 6.668 | ±0.315 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.232 | 1.255 | ±0.223 | A | yes | pass |
| Team RA/G mean (mid) | 6.758 | 6.871 | ±0.350 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.480 | 1.377 | ±0.242 | A | yes | pass |
| Team R/G mean (low) | 6.353 | 6.553 | ±0.378 | A | yes | pass |
| Team R/G SD across teams (low) | 1.149 | 1.141 | ±0.263 | A | yes | pass |
| Team RA/G mean (low) | 7.503 | 7.560 | ±0.600 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.745 | 1.819 | ±0.427 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.62 vs data 7.56; pitchers sim 1.71 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2369 | 0.2370 | ±0.0186 | B | yes | pass |
| BA p50 | 0.2917 | 0.2953 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3470 | 0.3505 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3286 | 0.3363 | ±0.0090 | B | yes | pass |
| OBP p50 | 0.3872 | 0.3880 | ±0.0115 | B | yes | pass |
| OBP p90 | 0.4471 | 0.4477 | ±0.0126 | B | yes | pass |
| ISO p10 | 0.0866 | 0.0755 | ±0.0175 | B | yes | pass |
| ISO p50 | 0.1619 | 0.1632 | ±0.0179 | B | yes | pass |
| ISO p90 | 0.2769 | 0.2746 | ±0.0396 | B | yes | pass |
| K_pct p10 | 0.1179 | 0.1064 | ±0.0274 | B | yes | pass |
| K_pct p50 | 0.1828 | 0.1831 | ±0.0165 | B | yes | pass |
| K_pct p90 | 0.2634 | 0.2691 | ±0.0452 | B | yes | pass |
| BB_pct p10 | 0.0655 | 0.0663 | ±0.0098 | B | yes | pass |
| BB_pct p50 | 0.1027 | 0.1077 | ±0.0151 | B | yes | pass |
| BB_pct p90 | 0.1500 | 0.1544 | ±0.0147 | B | yes | pass |
| ERA p10 | 3.09 | 3.41 | ±0.679 | B | yes | pass |
| ERA p50 | 4.87 | 5.09 | ±0.658 | B | yes | pass |
| ERA p90 | 7.10 | 7.69 | ±1.367 | B | yes | pass |
| K9 p10 | 6.01 | 5.82 | ±0.756 | B | yes | pass |
| K9 p50 | 8.64 | 7.66 | ±0.781 | B | Phase 6 | FAIL |
| K9 p90 | 11.78 | 10.54 | ±1.189 | B | Phase 6 | FAIL |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 769.1 (season range 742.0–796.0) | 882 | ±31.4 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 9.750 (season range 4.000–16.000) | 5 | ±6.742 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 64.2 (season range 52.0–78.0) | 57 | ±16.8 | A | yes | pass |
| Teams with ERA < 4.00 | 17.6 (season range 11.0–25.0) | 12 | ±9.3 | A | yes | pass |
| Best team ERA | 2.858 (season range 2.527–3.370) | 3.2 | ±0.494 | A | yes | pass |
| Best team BA | 0.346 (season range 0.332–0.357) | 0.356 | ±0.014 | A | yes | pass |
| Most team HR per game | 2.749 (season range 2.357–3.518) | 2.672 | ±0.772 | A | yes | pass |
| Top qualified BA | 0.447 (season range 0.427–0.472) | — | ±0.033 | D |  | n/a (no full-population source) |
| Most HR, individual | 43.5 (season range 36.0–64.0) | — | ±15.1 | D |  | n/a (no full-population source) |

## Diagnostics

- Earned share of runs 0.8824 (data 0.8824); pitchers per team-game 4.56 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 67.2, 57.7, 50.1 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
