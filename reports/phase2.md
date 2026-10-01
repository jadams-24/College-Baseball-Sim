# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-01.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7329 | 6.7500 | ±0.1634 | B | yes | pass |
| Batting average | 0.2818 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3799 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4420 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0660 | 1.0500 | ±0.0522 | B |  | pass |
| BB per PA | 0.1057 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1949 | 0.1927 | ±0.0056 | B |  | pass |
| HBP per PA | 0.0337 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.0821 | 1.0990 | ±0.1504 | B |  | pass |
| PA per team-game | 40.5145 | 40.3100 | ±1.0043 | B |  | pass |
| ERA | 6.2110 | 6.0800 | ±0.3065 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1048 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.684 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6363, 0.1667, 0.0923, 0.0502, 0.0264, 0.0281 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0613 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1284 | 0.1524 | ±0.0166 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1710 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.385 | 4.676 | — | A |  | n/a |
| Home win pct | 0.6003 | 0.5836 | ±0.0340 | A | yes | pass |
| Home run differential per game | 1.171 | 0.888 | ±0.521 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0339 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0330 | 0.0400 | -0.0070 | ±0.0102 | pass |
| 1 | 0.0575 | 0.0606 | -0.0031 | ±0.0102 | pass |
| 2 | 0.0768 | 0.0770 | -0.0002 | ±0.0102 | pass |
| 3 | 0.0887 | 0.0916 | -0.0029 | ±0.0101 | pass |
| 4 | 0.0956 | 0.0971 | -0.0015 | ±0.0101 | pass |
| 5 | 0.0949 | 0.0916 | +0.0033 | ±0.0101 | pass |
| 6 | 0.0919 | 0.0876 | +0.0043 | ±0.0102 | pass |
| 7 | 0.0835 | 0.0767 | +0.0068 | ±0.0101 | pass |
| 8 | 0.0739 | 0.0647 | +0.0092 | ±0.0101 | pass |
| 9 | 0.0629 | 0.0579 | +0.0050 | ±0.0101 | pass |
| 10 | 0.0552 | 0.0508 | +0.0044 | ±0.0101 | pass |
| 11 | 0.0456 | 0.0454 | +0.0002 | ±0.0101 | pass |
| 12 | 0.0371 | 0.0362 | +0.0009 | ±0.0101 | pass |
| 13 | 0.0287 | 0.0302 | -0.0015 | ±0.0101 | pass |
| 14 | 0.0217 | 0.0260 | -0.0043 | ±0.0100 | pass |
| 15+ | 0.0532 | 0.0664 | -0.0132 | ±0.0105 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.270 | 6.364 | ±0.505 | A | yes | pass |
| p4 batting vs mid pitching | 8.835 | 8.614 | ±0.645 | A | yes | pass |
| p4 batting vs low pitching | 10.874 | 9.820 | ±1.197 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.694 | 4.762 | ±0.556 | A | yes | pass |
| mid batting vs mid pitching | 6.669 | 6.724 | ±0.458 | A | yes | pass |
| mid batting vs low pitching | 8.710 | 8.457 | ±0.861 | A | yes | pass |
| low batting vs p4 pitching | 3.438 | 3.629 | ±0.682 | A | yes | pass |
| low batting vs mid pitching | 5.282 | 5.880 | ±0.663 | A | yes | pass |
| low batting vs low pitching | 6.899 | 7.046 | ±0.704 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.732 | 6.747 | ±0.209 | A | yes | pass |
| Team R/G SD across teams (all) | 1.208 | 1.162 | ±0.146 | A | yes | pass |
| Team RA/G mean (all) | 6.734 | 6.841 | ±0.282 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.673 | 1.596 | ±0.208 | A | yes | pass |
| Team R/G mean (p4) | 7.398 | 7.207 | ±0.313 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.835 | 0.793 | ±0.215 | A | yes | pass |
| Team RA/G mean (p4) | 5.578 | 5.767 | ±0.436 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.100 | 1.112 | ±0.306 | A | yes | pass |
| Team R/G mean (mid) | 6.676 | 6.668 | ±0.316 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.248 | 1.255 | ±0.224 | A | yes | pass |
| Team RA/G mean (mid) | 6.758 | 6.871 | ±0.352 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.481 | 1.377 | ±0.243 | A | yes | pass |
| Team R/G mean (low) | 6.354 | 6.553 | ±0.377 | A | yes | pass |
| Team R/G SD across teams (low) | 1.164 | 1.141 | ±0.266 | A | yes | pass |
| Team RA/G mean (low) | 7.517 | 7.560 | ±0.604 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.822 | 1.819 | ±0.433 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.62 vs data 7.56; pitchers sim 2.03 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2372 | 0.2370 | ±0.0186 | B | yes | pass |
| BA p50 | 0.2916 | 0.2953 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3475 | 0.3505 | ±0.0169 | B | yes | pass |
| OBP p10 | 0.3289 | 0.3363 | ±0.0091 | B | yes | pass |
| OBP p50 | 0.3875 | 0.3880 | ±0.0115 | B | yes | pass |
| OBP p90 | 0.4471 | 0.4477 | ±0.0126 | B | yes | pass |
| ISO p10 | 0.0867 | 0.0755 | ±0.0175 | B | yes | pass |
| ISO p50 | 0.1625 | 0.1632 | ±0.0179 | B | yes | pass |
| ISO p90 | 0.2776 | 0.2746 | ±0.0395 | B | yes | pass |
| K_pct p10 | 0.1179 | 0.1064 | ±0.0274 | B | yes | pass |
| K_pct p50 | 0.1827 | 0.1831 | ±0.0165 | B | yes | pass |
| K_pct p90 | 0.2632 | 0.2691 | ±0.0452 | B | yes | pass |
| BB_pct p10 | 0.0657 | 0.0663 | ±0.0099 | B | yes | pass |
| BB_pct p50 | 0.1028 | 0.1077 | ±0.0151 | B | yes | pass |
| BB_pct p90 | 0.1497 | 0.1544 | ±0.0147 | B | yes | pass |
| ERA p10 | 3.14 | 3.41 | ±0.679 | B | yes | pass |
| ERA p50 | 4.99 | 5.09 | ±0.657 | B | yes | pass |
| ERA p90 | 7.50 | 7.69 | ±1.369 | B | yes | pass |
| K9 p10 | 5.89 | 5.82 | ±0.759 | B | yes | pass |
| K9 p50 | 8.58 | 7.66 | ±0.785 | B | Phase 6 | FAIL |
| K9 p90 | 11.69 | 10.54 | ±1.193 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 879.4 (season range 858.0–912.0) | 882 | ±31.1 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 8.200 (season range 5.000–14.000) | 5 | ±5.721 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 64.8 (season range 49.0–85.0) | 57 | ±19.9 | A | yes | pass |
| Teams with ERA < 4.00 | 16.8 (season range 11.0–25.0) | 12 | ±8.1 | A | yes | pass |
| Best team ERA | 2.880 (season range 2.250–3.342) | 3.2 | ±0.560 | A | yes | pass |
| Best team BA | 0.348 (season range 0.333–0.370) | 0.356 | ±0.021 | A | yes | pass |
| Most team HR per game | 2.797 (season range 2.339–3.500) | 2.672 | ±0.702 | A | yes | pass |
| Top qualified BA | 0.438 (season range 0.415–0.454) | — | ±0.022 | D |  | n/a (no full-population source) |
| Most HR, individual | 43.4 (season range 35.0–75.0) | — | ±18.1 | D |  | n/a (no full-population source) |

## Diagnostics

- Earned share of runs 0.8828 (data 0.8824); pitchers per team-game 4.59 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.23 (data 6.48)
- Innings of a team's three busiest pitchers 70.5, 60.1, 52.5 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
