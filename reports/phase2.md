# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-01.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7332 | 6.7500 | ±0.1612 | B | yes | pass |
| Batting average | 0.2817 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3798 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4421 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0667 | 1.0500 | ±0.0521 | B |  | pass |
| BB per PA | 0.1057 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1950 | 0.1927 | ±0.0056 | B |  | pass |
| HBP per PA | 0.0337 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0842 | 1.0990 | ±0.1501 | B |  | pass |
| PA per team-game | 40.5067 | 40.3100 | ±1.0039 | B |  | pass |
| ERA | 6.2093 | 6.0800 | ±0.3062 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1048 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.684 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6359, 0.1673, 0.0920, 0.0500, 0.0267, 0.0281 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0611 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1288 | 0.1524 | ±0.0168 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1724 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.386 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5971 | 0.5836 | ±0.0343 | A | yes | pass |
| Home run differential per game | 1.148 | 0.888 | ±0.527 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0358 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0329 | 0.0400 | -0.0071 | ±0.0101 | pass |
| 1 | 0.0587 | 0.0606 | -0.0019 | ±0.0102 | pass |
| 2 | 0.0757 | 0.0770 | -0.0013 | ±0.0101 | pass |
| 3 | 0.0884 | 0.0916 | -0.0032 | ±0.0101 | pass |
| 4 | 0.0947 | 0.0971 | -0.0024 | ±0.0101 | pass |
| 5 | 0.0963 | 0.0916 | +0.0047 | ±0.0101 | pass |
| 6 | 0.0911 | 0.0876 | +0.0035 | ±0.0101 | pass |
| 7 | 0.0836 | 0.0767 | +0.0069 | ±0.0101 | pass |
| 8 | 0.0736 | 0.0647 | +0.0089 | ±0.0102 | pass |
| 9 | 0.0629 | 0.0579 | +0.0050 | ±0.0101 | pass |
| 10 | 0.0550 | 0.0508 | +0.0042 | ±0.0101 | pass |
| 11 | 0.0470 | 0.0454 | +0.0016 | ±0.0101 | pass |
| 12 | 0.0373 | 0.0362 | +0.0011 | ±0.0101 | pass |
| 13 | 0.0288 | 0.0302 | -0.0014 | ±0.0100 | pass |
| 14 | 0.0214 | 0.0260 | -0.0046 | ±0.0100 | pass |
| 15+ | 0.0527 | 0.0664 | -0.0137 | ±0.0104 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.261 | 6.364 | ±0.504 | A | yes | pass |
| p4 batting vs mid pitching | 8.879 | 8.614 | ±0.648 | A | yes | pass |
| p4 batting vs low pitching | 10.878 | 9.820 | ±1.205 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.708 | 4.762 | ±0.544 | A | yes | pass |
| mid batting vs mid pitching | 6.645 | 6.724 | ±0.457 | A | yes | pass |
| mid batting vs low pitching | 8.733 | 8.457 | ±0.874 | A | yes | pass |
| low batting vs p4 pitching | 3.437 | 3.629 | ±0.684 | A | yes | pass |
| low batting vs mid pitching | 5.258 | 5.880 | ±0.667 | A | yes | pass |
| low batting vs low pitching | 6.935 | 7.046 | ±0.704 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.733 | 6.747 | ±0.208 | A | yes | pass |
| Team R/G SD across teams (all) | 1.200 | 1.162 | ±0.145 | A | yes | pass |
| Team RA/G mean (all) | 6.735 | 6.841 | ±0.280 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.685 | 1.596 | ±0.207 | A | yes | pass |
| Team R/G mean (p4) | 7.405 | 7.207 | ±0.308 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.845 | 0.793 | ±0.219 | A | yes | pass |
| Team RA/G mean (p4) | 5.576 | 5.767 | ±0.434 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.086 | 1.112 | ±0.304 | A | yes | pass |
| Team R/G mean (mid) | 6.662 | 6.668 | ±0.316 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.229 | 1.255 | ±0.221 | A | yes | pass |
| Team RA/G mean (mid) | 6.742 | 6.871 | ±0.352 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.490 | 1.377 | ±0.243 | A | yes | pass |
| Team R/G mean (low) | 6.375 | 6.553 | ±0.377 | A | yes | pass |
| Team R/G SD across teams (low) | 1.167 | 1.141 | ±0.264 | A | yes | pass |
| Team RA/G mean (low) | 7.547 | 7.560 | ±0.605 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.837 | 1.819 | ±0.435 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.62 vs data 7.56; pitchers sim 1.71 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2370 | 0.2370 | ±0.0186 | B | yes | pass |
| BA p50 | 0.2919 | 0.2953 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3472 | 0.3505 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3284 | 0.3363 | ±0.0090 | B | yes | pass |
| OBP p50 | 0.3871 | 0.3880 | ±0.0115 | B | yes | pass |
| OBP p90 | 0.4470 | 0.4477 | ±0.0127 | B | yes | pass |
| ISO p10 | 0.0868 | 0.0755 | ±0.0175 | B | yes | pass |
| ISO p50 | 0.1623 | 0.1632 | ±0.0179 | B | yes | pass |
| ISO p90 | 0.2768 | 0.2746 | ±0.0395 | B | yes | pass |
| K_pct p10 | 0.1176 | 0.1064 | ±0.0274 | B | yes | pass |
| K_pct p50 | 0.1825 | 0.1831 | ±0.0165 | B | yes | pass |
| K_pct p90 | 0.2630 | 0.2691 | ±0.0452 | B | yes | pass |
| BB_pct p10 | 0.0656 | 0.0663 | ±0.0099 | B | yes | pass |
| BB_pct p50 | 0.1029 | 0.1077 | ±0.0151 | B | yes | pass |
| BB_pct p90 | 0.1497 | 0.1544 | ±0.0147 | B | yes | pass |
| ERA p10 | 3.09 | 3.41 | ±0.678 | B | yes | pass |
| ERA p50 | 4.86 | 5.09 | ±0.657 | B | yes | pass |
| ERA p90 | 7.12 | 7.69 | ±1.368 | B | yes | pass |
| K9 p10 | 6.02 | 5.82 | ±0.758 | B | yes | pass |
| K9 p50 | 8.67 | 7.66 | ±0.783 | B | Phase 6 | FAIL |
| K9 p90 | 11.77 | 10.54 | ±1.189 | B | Phase 6 | FAIL |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 768.6 (season range 749.0–806.0) | 882 | ±31.3 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 8.700 (season range 5.000–12.000) | 5 | ±4.673 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 62.8 (season range 54.0–78.0) | 57 | ±13.7 | A | yes | pass |
| Teams with ERA < 4.00 | 16.6 (season range 8.0–25.0) | 12 | ±11.7 | A | yes | pass |
| Best team ERA | 2.926 (season range 2.552–3.361) | 3.2 | ±0.533 | A | yes | pass |
| Best team BA | 0.345 (season range 0.331–0.353) | 0.356 | ±0.013 | A | yes | pass |
| Most team HR per game | 2.737 (season range 2.286–3.411) | 2.672 | ±0.688 | A | yes | pass |
| Top qualified BA | 0.444 (season range 0.424–0.471) | — | ±0.023 | D |  | n/a (no full-population source) |
| Most HR, individual | 43.2 (season range 33.0–62.0) | — | ±14.8 | D |  | n/a (no full-population source) |

## Diagnostics

- Earned share of runs 0.8823 (data 0.8824); pitchers per team-game 4.56 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 67.2, 57.6, 50.1 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
