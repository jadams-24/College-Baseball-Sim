# Phase 1 realism report

League-average PA engine, 10,000 games, seed 20250101, generated 2026-10-01.
Gate rows are the Phase 1 gate (R/G, BA, OBP, SLG, runs-per-half-inning distribution, big-inning frequency, PA per half-inning); the rest are informational. The per-game run histogram and extra-innings frequency need team and pitcher variance and are the Phase 2 gate; run-rule frequency is the Phase 6 gate.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.79 | 6.75 | ±0.15 | B | yes | pass |
| Batting average | 0.2832 | 0.2800 | ±0.005 | B | yes | pass |
| On-base pct | 0.3811 | 0.3805 | ±0.005 | B | yes | pass |
| Slugging pct | 0.4420 | 0.4400 | ±0.01 | B | yes | pass |
| HR per team-game | 1.07 | 1.05 | ±0.05 | B |  | pass |
| SB per team-game | 1.22 | 1.29 | ±0.1 | B |  | pass |
| Errors per team-game | 1.12 | 1.10 | ±0.15 | B |  | pass |
| Extra-innings frequency (Phase 2 gate) | 0.0735 | 0.0546 | ±0.015 | B |  | FAIL |
| BB per PA | 0.1056 | 0.1059 | ±0.005 | B |  | pass |
| K per PA | 0.1941 | 0.1927 | ±0.005 | B |  | pass |
| HBP per PA | 0.0338 | 0.0334 | ±0.004 | B |  | pass |
| SH per team-game | 0.3810 | 0.4300 | ±0.05 | B |  | pass |
| SF per team-game | 0.4232 | 0.3680 | ±0.08 | B |  | pass |
| PA per team-game | 41.42 | 40.31 | ±1.0 | B |  | FAIL |
| SB success rate | 0.7876 | 0.7600 | ±0.03 | B |  | pass |
| Run-rule frequency (Phase 6 gate) | 0.0648 | 0.1524 | ±0.0155 | B |  | FAIL |
| Big-inning frequency (3+ runs) | 0.1034 | 0.1031 | ±0.0091 | A | yes | pass |
| PA per half-inning | 4.69 | 4.69 | ±0.053 | A | yes | pass |

## Runs per half-inning (gate; ±3 SE per bin, n_eff = 9,954 half-innings)

Sim 17.66 half-innings per game vs 17.073 in the data.  →  **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.6319 | 0.6397 | -0.0078 | ±0.0144 | pass |
| 1 | 0.1705 | 0.1625 | +0.0080 | ±0.0111 | pass |
| 2 | 0.0942 | 0.0947 | -0.0005 | ±0.0088 | pass |
| 3 | 0.0515 | 0.0491 | +0.0024 | ±0.0065 | pass |
| 4 | 0.0265 | 0.0258 | +0.0007 | ±0.0048 | pass |
| 5+ | 0.0255 | 0.0282 | -0.0027 | ±0.005 | pass |

## Runs per team-game histogram (Phase 2 gate, informational here; ±0.01 per bin, TVD ≤ 0.04)

Total variation distance: 0.1059  →  FAIL (expected without team/pitcher variance)

| Runs | Sim | Benchmark | Diff |
|---|---|---|---|
| 0 | 0.0193 | 0.0400 | -0.0207 |
| 1 | 0.0411 | 0.0606 | -0.0195 |
| 2 | 0.0617 | 0.0770 | -0.0153 |
| 3 | 0.0850 | 0.0916 | -0.0066 |
| 4 | 0.0975 | 0.0971 | +0.0004 |
| 5 | 0.1024 | 0.0916 | +0.0108 |
| 6 | 0.1065 | 0.0876 | +0.0189 |
| 7 | 0.0970 | 0.0767 | +0.0203 |
| 8 | 0.0878 | 0.0647 | +0.0231 |
| 9 | 0.0767 | 0.0579 | +0.0188 |
| 10 | 0.0609 | 0.0508 | +0.0101 |
| 11 | 0.0491 | 0.0454 | +0.0037 |
| 12 | 0.0361 | 0.0362 | -0.0001 |
| 13 | 0.0255 | 0.0302 | -0.0047 |
| 14 | 0.0171 | 0.0260 | -0.0089 |
| 15+ | 0.0364 | 0.0664 | -0.0300 |

## Gate: **PASS**

## Engine diagnostics

- Innings distribution: 7: 0.0454, 8: 0.0194, 9: 0.8617, 10: 0.0413, 11: 0.0177, 12: 0.0082, 13: 0.0032, 14: 0.0017, 15: 0.0007, 16: 0.0003, 17: 0.0003, 18: 0.0001
- Home win pct 0.4976; mean margin 4.19; LOB per team-game 8.24; ROE per team-game 0.584; FC per team-game 1.014
- CS per team-game 0.329
- Advancement cell use: {'exact': 819901, 'pooled_outs': 7808, 'marginal': 773}; runner collisions resolved by rule: 75

