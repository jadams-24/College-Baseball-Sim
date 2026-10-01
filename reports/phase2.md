# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-01.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7423 | 6.7500 | ±0.1607 | B | yes | pass |
| Batting average | 0.2819 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3802 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4424 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0684 | 1.0500 | ±0.0521 | B |  | pass |
| BB per PA | 0.1059 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1949 | 0.1927 | ±0.0056 | B |  | pass |
| HBP per PA | 0.0337 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0820 | 1.0990 | ±0.1503 | B |  | pass |
| PA per team-game | 40.5317 | 40.3100 | ±1.0036 | B |  | pass |
| ERA | 6.2210 | 6.0800 | ±0.3059 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1051 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.686 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6359, 0.1671, 0.0918, 0.0502, 0.0266, 0.0282 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0615 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1290 | 0.1524 | ±0.0171 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1720 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.381 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5969 | 0.5836 | ±0.0341 | A | yes | pass |
| Home run differential per game | 1.148 | 0.888 | ±0.526 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0356 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0329 | 0.0400 | -0.0071 | ±0.0101 | pass |
| 1 | 0.0574 | 0.0606 | -0.0032 | ±0.0101 | pass |
| 2 | 0.0760 | 0.0770 | -0.0010 | ±0.0101 | pass |
| 3 | 0.0889 | 0.0916 | -0.0027 | ±0.0101 | pass |
| 4 | 0.0944 | 0.0971 | -0.0027 | ±0.0101 | pass |
| 5 | 0.0957 | 0.0916 | +0.0041 | ±0.0102 | pass |
| 6 | 0.0920 | 0.0876 | +0.0044 | ±0.0102 | pass |
| 7 | 0.0833 | 0.0767 | +0.0066 | ±0.0101 | pass |
| 8 | 0.0741 | 0.0647 | +0.0094 | ±0.0101 | pass |
| 9 | 0.0631 | 0.0579 | +0.0052 | ±0.0101 | pass |
| 10 | 0.0550 | 0.0508 | +0.0042 | ±0.0101 | pass |
| 11 | 0.0465 | 0.0454 | +0.0011 | ±0.0101 | pass |
| 12 | 0.0369 | 0.0362 | +0.0007 | ±0.0100 | pass |
| 13 | 0.0288 | 0.0302 | -0.0014 | ±0.0101 | pass |
| 14 | 0.0217 | 0.0260 | -0.0043 | ±0.0100 | pass |
| 15+ | 0.0534 | 0.0664 | -0.0130 | ±0.0104 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.289 | 6.364 | ±0.502 | A | yes | pass |
| p4 batting vs mid pitching | 8.854 | 8.614 | ±0.644 | A | yes | pass |
| p4 batting vs low pitching | 10.911 | 9.820 | ±1.208 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.718 | 4.762 | ±0.548 | A | yes | pass |
| mid batting vs mid pitching | 6.653 | 6.724 | ±0.457 | A | yes | pass |
| mid batting vs low pitching | 8.737 | 8.457 | ±0.871 | A | yes | pass |
| low batting vs p4 pitching | 3.406 | 3.629 | ±0.671 | A | yes | pass |
| low batting vs mid pitching | 5.265 | 5.880 | ±0.670 | A | yes | pass |
| low batting vs low pitching | 6.945 | 7.046 | ±0.704 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.742 | 6.747 | ±0.207 | A | yes | pass |
| Team R/G SD across teams (all) | 1.201 | 1.162 | ±0.147 | A | yes | pass |
| Team RA/G mean (all) | 6.744 | 6.841 | ±0.280 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.671 | 1.596 | ±0.207 | A | yes | pass |
| Team R/G mean (p4) | 7.418 | 7.207 | ±0.309 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.839 | 0.793 | ±0.220 | A | yes | pass |
| Team RA/G mean (p4) | 5.592 | 5.767 | ±0.431 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.090 | 1.112 | ±0.307 | A | yes | pass |
| Team R/G mean (mid) | 6.670 | 6.668 | ±0.318 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.237 | 1.255 | ±0.223 | A | yes | pass |
| Team RA/G mean (mid) | 6.746 | 6.871 | ±0.349 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.470 | 1.377 | ±0.243 | A | yes | pass |
| Team R/G mean (low) | 6.383 | 6.553 | ±0.372 | A | yes | pass |
| Team R/G SD across teams (low) | 1.155 | 1.141 | ±0.263 | A | yes | pass |
| Team RA/G mean (low) | 7.559 | 7.560 | ±0.606 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.823 | 1.819 | ±0.433 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.62 vs data 7.56; pitchers sim 2.01 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2365 | 0.2370 | ±0.0186 | B | yes | pass |
| BA p50 | 0.2919 | 0.2953 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3478 | 0.3505 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3291 | 0.3363 | ±0.0091 | B | yes | pass |
| OBP p50 | 0.3879 | 0.3880 | ±0.0116 | B | yes | pass |
| OBP p90 | 0.4475 | 0.4477 | ±0.0126 | B | yes | pass |
| ISO p10 | 0.0870 | 0.0755 | ±0.0175 | B | yes | pass |
| ISO p50 | 0.1623 | 0.1632 | ±0.0179 | B | yes | pass |
| ISO p90 | 0.2779 | 0.2746 | ±0.0395 | B | yes | pass |
| K_pct p10 | 0.1177 | 0.1064 | ±0.0274 | B | yes | pass |
| K_pct p50 | 0.1825 | 0.1831 | ±0.0165 | B | yes | pass |
| K_pct p90 | 0.2635 | 0.2691 | ±0.0452 | B | yes | pass |
| BB_pct p10 | 0.0658 | 0.0663 | ±0.0099 | B | yes | pass |
| BB_pct p50 | 0.1031 | 0.1077 | ±0.0151 | B | yes | pass |
| BB_pct p90 | 0.1501 | 0.1544 | ±0.0147 | B | yes | pass |
| ERA p10 | 3.16 | 3.41 | ±0.679 | B | yes | pass |
| ERA p50 | 4.97 | 5.09 | ±0.658 | B | yes | pass |
| ERA p90 | 7.52 | 7.69 | ±1.372 | B | yes | pass |
| K9 p10 | 5.92 | 5.82 | ±0.760 | B | yes | pass |
| K9 p50 | 8.60 | 7.66 | ±0.781 | B | Phase 6 | FAIL |
| K9 p90 | 11.68 | 10.54 | ±1.186 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 870.5 (season range 851.0–894.0) | 882 | ±26.0 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 7.550 (season range 3.000–12.000) | 5 | ±5.883 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 63.5 (season range 52.0–78.0) | 57 | ±16.4 | A | yes | pass |
| Teams with ERA < 4.00 | 15.9 (season range 9.0–21.0) | 12 | ±6.9 | A | yes | pass |
| Best team ERA | 2.963 (season range 2.400–3.332) | 3.2 | ±0.499 | A | yes | pass |
| Best team BA | 0.347 (season range 0.334–0.359) | 0.356 | ±0.014 | A | yes | pass |
| Most team HR per game | 2.794 (season range 2.339–3.518) | 2.672 | ±0.714 | A | yes | pass |
| Top qualified BA | 0.444 (season range 0.422–0.493) | — | ±0.037 | D |  | n/a (no full-population source) |
| Most HR, individual | 43.5 (season range 33.0–75.0) | — | ±19.3 | D |  | n/a (no full-population source) |

## Diagnostics

- Earned share of runs 0.8830 (data 0.8824); pitchers per team-game 4.61 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 70.1, 59.9, 52.4 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
