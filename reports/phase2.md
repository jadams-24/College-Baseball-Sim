# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-01.
Leaderboard rows pass if the real value lies within ±2 SD (prediction interval) of the simulated seasons.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.8134 | 6.7500 | ±0.15 | B | yes | pass |
| Batting average | 0.2836 | 0.2800 | ±0.005 | B | yes | pass |
| On-base pct | 0.3813 | 0.3850 | ±0.005 | B | yes | pass |
| Slugging pct | 0.4425 | 0.4400 | ±0.01 | B | yes | pass |
| HR per team-game | 1.0593 | 1.0500 | ±0.05 | B |  | pass |
| BB per PA | 0.1058 | 0.1059 | ±0.005 | B |  | pass |
| K per PA | 0.1921 | 0.1927 | ±0.005 | B |  | pass |
| HBP per PA | 0.0335 | 0.0334 | ±0.004 | B |  | pass |
| Errors per team-game | 1.1046 | 1.0990 | ±0.15 | B |  | pass |
| PA per team-game | 41.1348 | 40.3100 | ±1.0 | B |  | pass |
| ERA | 6.3842 | 6.0800 | ±0.3 | B |  | FAIL |
| Big-inning frequency (3+ runs) | 0.1045 | 0.1031 | ±0.0091 | A | yes | pass |
| PA per half-inning | 4.695 | 4.694 | ±0.053 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6321, 0.1697, 0.0937, 0.0509, 0.0266, 0.0270 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0680 | 0.0546 | ±0.015 | B | yes | pass |
| Run-rule frequency | 0.0959 | 0.1524 | ±0.0155 | B | yes | FAIL |
| Games decided by 10+ runs | 0.1347 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.143 | 4.676 | — | A |  | n/a |

### Runs per team-game histogram (±0.01 per bin, TVD ≤ 0.04): TVD 0.0653 → **FAIL**

| Runs | Sim | Benchmark | Diff | Status |
|---|---|---|---|---|
| 0 | 0.0249 | 0.0400 | -0.0151 | FAIL |
| 1 | 0.0496 | 0.0606 | -0.0110 | FAIL |
| 2 | 0.0698 | 0.0770 | -0.0072 | pass |
| 3 | 0.0861 | 0.0916 | -0.0055 | pass |
| 4 | 0.0961 | 0.0971 | -0.0010 | pass |
| 5 | 0.0994 | 0.0916 | +0.0078 | pass |
| 6 | 0.0970 | 0.0876 | +0.0094 | pass |
| 7 | 0.0896 | 0.0767 | +0.0129 | FAIL |
| 8 | 0.0792 | 0.0647 | +0.0145 | FAIL |
| 9 | 0.0682 | 0.0579 | +0.0103 | FAIL |
| 10 | 0.0576 | 0.0508 | +0.0068 | pass |
| 11 | 0.0478 | 0.0454 | +0.0024 | pass |
| 12 | 0.0376 | 0.0362 | +0.0014 | pass |
| 13 | 0.0286 | 0.0302 | -0.0016 | pass |
| 14 | 0.0211 | 0.0260 | -0.0049 | pass |
| 15+ | 0.0474 | 0.0664 | -0.0190 | FAIL |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.813 | 6.747 | ±0.199 | A | yes | pass |
| Team R/G SD across teams (all) | 0.931 | 1.162 | ±0.141 | A | yes | FAIL |
| Team RA/G mean (all) | 6.814 | 6.841 | ±0.274 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.105 | 1.596 | ±0.194 | A | yes | FAIL |
| Team R/G mean (p4) | 7.671 | 7.207 | ±0.297 | A | yes | FAIL |
| Team R/G SD across teams (p4) | 0.897 | 0.793 | ±0.212 | A | yes | pass |
| Team RA/G mean (p4) | 5.883 | 5.767 | ±0.417 | A | yes | pass |
| Team RA/G SD across teams (p4) | 0.882 | 1.112 | ±0.297 | A | yes | pass |
| Team R/G mean (mid) | 6.703 | 6.668 | ±0.304 | A | yes | pass |
| Team R/G SD across teams (mid) | 0.790 | 1.255 | ±0.216 | A | yes | FAIL |
| Team RA/G mean (mid) | 6.803 | 6.871 | ±0.334 | A | yes | pass |
| Team RA/G SD across teams (mid) | 0.931 | 1.377 | ±0.237 | A | yes | FAIL |
| Team R/G mean (low) | 6.392 | 6.553 | ±0.363 | A | yes | pass |
| Team R/G SD across teams (low) | 0.774 | 1.141 | ±0.258 | A | yes | FAIL |
| Team RA/G mean (low) | 7.492 | 7.560 | ±0.578 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.031 | 1.819 | ±0.411 | A | yes | FAIL |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 6.60 vs data 7.56; pitchers sim 2.60 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2425 | 0.2370 | ±0.0185 | B | yes | pass |
| BA p50 | 0.2943 | 0.2953 | ±0.0148 | B | yes | pass |
| BA p90 | 0.3456 | 0.3505 | ±0.0168 | B | yes | pass |
| OBP p10 | 0.3354 | 0.3363 | ±0.0088 | B | yes | pass |
| OBP p50 | 0.3896 | 0.3880 | ±0.0114 | B | yes | pass |
| OBP p90 | 0.4440 | 0.4477 | ±0.0125 | B | yes | pass |
| ISO p10 | 0.0911 | 0.0755 | ±0.0174 | B | yes | pass |
| ISO p50 | 0.1624 | 0.1632 | ±0.0178 | B | yes | pass |
| ISO p90 | 0.2683 | 0.2746 | ±0.0394 | B | yes | pass |
| K_pct p10 | 0.1173 | 0.1064 | ±0.0273 | B | yes | pass |
| K_pct p50 | 0.1789 | 0.1831 | ±0.0163 | B | yes | pass |
| K_pct p90 | 0.2578 | 0.2691 | ±0.0451 | B | yes | pass |
| BB_pct p10 | 0.0662 | 0.0663 | ±0.0098 | B | yes | pass |
| BB_pct p50 | 0.1030 | 0.1077 | ±0.0151 | B | yes | pass |
| BB_pct p90 | 0.1496 | 0.1544 | ±0.0146 | B | yes | pass |
| ERA p10 | 3.77 | 3.41 | ±0.6754 | B | yes | pass |
| ERA p50 | 5.50 | 5.09 | ±0.6533 | B | yes | pass |
| ERA p90 | 7.49 | 7.69 | ±1.3645 | B | yes | pass |
| K9 p10 | 5.72 | 5.82 | ±0.751 | B | yes | pass |
| K9 p50 | 8.15 | 7.66 | ±0.7711 | B | yes | pass |
| K9 p90 | 11.05 | 10.54 | ±1.1748 | B | yes | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 1055.1 (season range 1040.0–1078.0) | 882 | ±21.4 | A | yes | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 2.150 (season range 0.000–4.000) | 5 | ±2.423 | A | yes | FAIL |
| 50+ IP pitchers with ERA < 3.00 | 26.3 (season range 17.0–35.0) | 57 | ±8.8 | A | yes | FAIL |
| Teams with ERA < 4.00 | 1.700 (season range 0.000–5.000) | 12 | ±2.829 | A | yes | FAIL |
| Best team ERA | 3.763 (season range 3.239–4.164) | 3.2 | ±0.577 | A | yes | pass |
| Best team BA | 0.335 (season range 0.323–0.344) | 0.356 | ±0.013 | A | yes | FAIL |
| Most team HR per game | 2.643 (season range 2.250–3.214) | 2.672 | ±0.549 | A | yes | pass |
| Top qualified BA | 0.437 (season range 0.404–0.472) | — | ±0.035 | D |  | n/a (no full-population source) |
| Most HR, individual | 41.1 (season range 30.0–55.0) | — | ±13.1 | D |  | n/a (no full-population source) |

## Diagnostics

- Home win pct 0.4991 (real 0.5876; no home advantage is modeled)
- Pitchers per team-game 4.67 (data 4.298); earned share of runs 0.909 (data 0.8824)
