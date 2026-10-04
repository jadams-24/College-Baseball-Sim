# Phase 1 realism report

League-average PA engine, 10,000 games, seed 20250101, generated 2026-10-04.
Gate rows are the Phase 1 gate (R/G, BA, OBP, SLG, runs-per-half-inning distribution, big-inning frequency, PA per half-inning); the rest are informational. The per-game run histogram and extra-innings frequency need team and pitcher variance and are the Phase 2 gate; run-rule frequency is the Phase 6 gate.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.75 | 6.75 | ±0.15 | B | yes | pass |
| Batting average | 0.2829 | 0.2800 | ±0.005 | B | yes | pass |
| On-base pct | 0.3802 | 0.3805 | ±0.005 | B | yes | pass |
| Slugging pct | 0.4423 | 0.4400 | ±0.01 | B | yes | pass |
| HR per team-game | 1.07 | 1.05 | ±0.05 | B |  | pass |
| SB per team-game | 1.03 | 1.10 | ±0.1 | B |  | pass |
| Errors per team-game | 1.09 | 1.10 | ±0.15 | B |  | pass |
| Extra-innings frequency (Phase 2 gate) | 0.0703 | 0.0546 | ±0.015 | B |  | FAIL |
| BB per PA | 0.1051 | 0.1059 | ±0.005 | B |  | pass |
| K per PA | 0.1941 | 0.1927 | ±0.005 | B |  | pass |
| HBP per PA | 0.0334 | 0.0334 | ±0.004 | B |  | pass |
| SH per team-game | 0.3903 | 0.4300 | ±0.05 | B |  | pass |
| SF per team-game | 0.4274 | 0.3680 | ±0.08 | B |  | pass |
| PA per team-game | 41.34 | 40.31 | ±1.0 | B |  | FAIL |
| SB success rate | 0.7891 | 0.7600 | ±0.03 | B |  | pass |
| Run-rule frequency (Phase 6 gate) | 0.0709 | 0.1524 | ±0.0155 | B |  | FAIL |
| Big-inning frequency (3+ runs) | 0.1029 | 0.1031 | ±0.0091 | A | yes | pass |
| PA per half-inning | 4.69 | 4.69 | ±0.053 | A | yes | pass |

## Runs per half-inning (gate; ±3 SE per bin, n_eff = 9,954 half-innings)

Sim 17.61 half-innings per game vs 17.073 in the data.  →  **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.6336 | 0.6397 | -0.0061 | ±0.0144 | pass |
| 1 | 0.1687 | 0.1625 | +0.0062 | ±0.0111 | pass |
| 2 | 0.0948 | 0.0947 | +0.0001 | ±0.0088 | pass |
| 3 | 0.0506 | 0.0491 | +0.0015 | ±0.0065 | pass |
| 4 | 0.0269 | 0.0258 | +0.0011 | ±0.0048 | pass |
| 5+ | 0.0254 | 0.0282 | -0.0028 | ±0.005 | pass |

## Runs per team-game histogram (Phase 2 gate, informational here; ±0.01 per bin, TVD ≤ 0.04)

Total variation distance: 0.1009  →  FAIL (expected without team/pitcher variance)

| Runs | Sim | Benchmark | Diff |
|---|---|---|---|
| 0 | 0.0197 | 0.0400 | -0.0203 |
| 1 | 0.0457 | 0.0606 | -0.0149 |
| 2 | 0.0644 | 0.0770 | -0.0126 |
| 3 | 0.0819 | 0.0916 | -0.0097 |
| 4 | 0.0974 | 0.0971 | +0.0003 |
| 5 | 0.1011 | 0.0916 | +0.0095 |
| 6 | 0.1056 | 0.0876 | +0.0180 |
| 7 | 0.0994 | 0.0767 | +0.0227 |
| 8 | 0.0883 | 0.0647 | +0.0236 |
| 9 | 0.0727 | 0.0579 | +0.0148 |
| 10 | 0.0592 | 0.0508 | +0.0084 |
| 11 | 0.0469 | 0.0454 | +0.0015 |
| 12 | 0.0384 | 0.0362 | +0.0022 |
| 13 | 0.0260 | 0.0302 | -0.0043 |
| 14 | 0.0190 | 0.0260 | -0.0070 |
| 15+ | 0.0345 | 0.0664 | -0.0319 |

## Gate: **PASS**

## Engine diagnostics

- Innings distribution: 7: 0.0528, 8: 0.0181, 9: 0.8588, 10: 0.0398, 11: 0.0162, 12: 0.0078, 13: 0.0036, 14: 0.0016, 15: 0.0008, 16: 0.0003, 17: 0.0001, 18: 0.0001
- Home win pct 0.5045; mean margin 4.27; LOB per team-game 8.26; ROE per team-game 0.592; FC per team-game 1.012
- CS per team-game 0.276
- Advancement cell use: {'exact': 818483, 'pooled_outs': 7536, 'marginal': 804}; runner collisions resolved by rule: 76

