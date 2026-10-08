# Phase 3 realism report: handedness and platoon splits

Generated 2026-10-08, 40 seasons (seeds 20251000-20251039), the same run as the Phase 2, 4, 5, 6 and 7 reports. Gate: FAIL.

Hands are drawn per player from his talent and role (pitchers) or position (batters), never from his tier (owner rule 2026-10-08); matchups shift by the batter's side and the pitcher's hand (fitted net of who faced whom, centred on the league mix); the AI's pitching changes and pinch hitters use the hands of the batter due up and of the pitcher (scripts/build_phase3_*.py). Tolerances: the benchmark's (benchmarks.json handedness_platoon_2025) combined with 3 SE of the simulated mean.

## Handedness shares

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| Left-handed pitchers, starters (D1) | 0.247 | 0.264 | ±0.045 | yes | pass |  |
| Left-handed pitchers, relievers (D1) | 0.258 | 0.251 | ±0.020 | yes | pass |  |
| Throws L, C | 0.002 | 0.003 | ±0.003 | yes | pass |  |
| Throws L, 1B | 0.321 | 0.320 | ±0.057 | yes | pass |  |
| Throws L, IF | 0.029 | 0.030 | ±0.009 | yes | pass |  |
| Throws L, OF | 0.270 | 0.269 | ±0.026 | yes | pass |  |
| Throws L, UT/DH | 0.060 | 0.059 | ±0.027 | yes | pass |  |
| Bats L, C | 0.167 | 0.167 | ±0.026 | yes | pass |  |
| Bats R, C | 0.782 | 0.782 | ±0.036 | yes | pass |  |
| Bats S, C | 0.051 | 0.051 | ±0.014 | yes | pass |  |
| Bats L, 1B | 0.530 | 0.531 | ±0.084 | yes | pass |  |
| Bats R, 1B | 0.443 | 0.442 | ±0.082 | yes | pass |  |
| Bats S, 1B | 0.027 | 0.027 | ±0.025 | yes | pass |  |
| Bats L, IF | 0.276 | 0.278 | ±0.027 | yes | pass |  |
| Bats R, IF | 0.668 | 0.667 | ±0.029 | yes | pass |  |
| Bats S, IF | 0.056 | 0.055 | ±0.012 | yes | pass |  |
| Bats L, OF | 0.464 | 0.462 | ±0.033 | yes | pass |  |
| Bats R, OF | 0.512 | 0.514 | ±0.034 | yes | pass |  |
| Bats S, OF | 0.024 | 0.023 | ±0.008 | yes | pass |  |
| Bats L, UT/DH | 0.320 | 0.312 | ±0.056 | yes | pass |  |
| Bats R, UT/DH | 0.649 | 0.653 | ±0.067 | yes | pass |  |
| Bats S, UT/DH | 0.031 | 0.035 | ±0.026 | yes | pass |  |

## Tier gradient (check: not fitted)

The real gradient (P4 more left-handed) has to come from where the talent is. Tolerance: the conference-clustered 95% interval.

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| Left-handed starters, p4 (real interval 0.225-0.475) | 0.276 | 0.350 | ±0.126 | yes | pass |  |
| Left-handed relievers, p4 (real interval 0.276-0.337) | 0.230 | 0.306 | ±0.032 | yes | FAIL |  |
| Left-handed starters, mid (real interval 0.204-0.305) | 0.246 | 0.255 | ±0.051 | yes | pass |  |
| Left-handed relievers, mid (real interval 0.223-0.281) | 0.257 | 0.252 | ±0.030 | yes | pass |  |
| Left-handed starters, low (real interval 0.116-0.293) | 0.227 | 0.204 | ±0.089 | yes | pass |  |
| Left-handed relievers, low (real interval 0.154-0.240) | 0.279 | 0.197 | ±0.043 | yes | FAIL |  |
| Batters bats L, p4, at the tier's position mix (real interval 0.359-0.385) | 0.370 | 0.372 | ±0.015 | yes | pass |  |
| Batters bats L, mid, at the tier's position mix (real interval 0.293-0.340) | 0.322 | 0.317 | ±0.024 | yes | pass |  |
| Batters bats L, low, at the tier's position mix (real interval 0.247-0.335) | 0.289 | 0.291 | ±0.044 | yes | pass |  |

Fit behind the draw (scripts/build_phase3_hands.py; deconvolved through the noise of the observed talent bins):

- Pitchers, P(throws L) = expit(a + b s), s the true K-BB per BF against an average batter, standardized within role: b = +0.202 ± 0.159 (starters), -0.226 ± 0.172 (relievers) per SD; a = -1.072 / -1.093 (set so the D1 shares match).
- Same fit with a tier term (the effect of tier at equal talent, mid the reference): P4 +0.483 ± 0.188, low -0.710 ± 0.479 log-odds; P4 against low +1.192 ± 0.501 (at a .25 base share: 0.351 P4, .250 mid, 0.141 low).
- Run-value index instead of K-BB (sensitivity check, owner adjustment 1): b = +0.346 ± 0.207 / +0.067 ± 0.197; predicted LHP shares by tier starters 0.321 / 0.263 / 0.215; relievers 0.265 / 0.251 / 0.238 (K-BB: starters 0.295 / 0.263 / 0.237; relievers 0.224 / 0.251 / 0.275); P4 against low at equal talent +1.066 ± 0.562.
- Batters: bats L against R +0.282 ± 0.084, S against R +0.198 ± 0.170 per SD of true run value per PA.

Plate appearances against left-handers by tier (reported): p4 0.270, mid 0.257, low 0.253, all 0.259.

## Platoon splits

Splits (rate against left-handed pitchers minus against right-handed) within each batting tier, the tiers weighted by their hand-known plate appearances in the real data (the engine's shift is one number for every tier). Batters hitting left or right count switch hitters on the side they used; the switch-hitter rows are by listed bats.

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| K% vs LHP minus vs RHP, batters hitting left | 0.0248 | 0.0279 | ±0.0103 | yes | pass |  |
| BB% vs LHP minus vs RHP, batters hitting left | -0.0088 | -0.0092 | ±0.0081 | yes | pass |  |
| HR% vs LHP minus vs RHP, batters hitting left | -0.0143 | -0.0116 | ±0.0038 | yes | pass |  |
| BABIP vs LHP minus vs RHP, batters hitting left | 0.0002 | -0.0003 | ±0.0153 | yes | pass |  |
| on base / PA vs LHP minus vs RHP, batters hitting left | -0.0158 | -0.0159 | ±0.0122 | yes | pass |  |
| K% vs LHP minus vs RHP, batters hitting right | 0.0027 | 0.0035 | ±0.0088 | yes | pass |  |
| BB% vs LHP minus vs RHP, batters hitting right | 0.0019 | 0.0033 | ±0.0064 | yes | pass |  |
| HR% vs LHP minus vs RHP, batters hitting right | 0.0069 | 0.0059 | ±0.0036 | yes | pass |  |
| BABIP vs LHP minus vs RHP, batters hitting right | -0.0134 | -0.0121 | ±0.0127 | yes | pass |  |
| on base / PA vs LHP minus vs RHP, batters hitting right | -0.0074 | -0.0054 | ±0.0102 | yes | pass |  |
| K% vs LHP minus vs RHP, switch hitters | 0.0210 | 0.0163 | ±0.0297 | yes | pass |  |
| BB% vs LHP minus vs RHP, switch hitters | -0.0184 | -0.0316 | ±0.0220 | yes | pass |  |
| HR% vs LHP minus vs RHP, switch hitters | 0.0048 | 0.0047 | ±0.0124 | yes | pass |  |
| BABIP vs LHP minus vs RHP, switch hitters | -0.0024 | -0.0169 | ±0.0431 | yes | pass |  |
| on base / PA vs LHP minus vs RHP, switch hitters | -0.0190 | -0.0426 | ±0.0349 | yes | pass |  |

Plate-appearance mix (reported, not gated: the plan gated the platoon-advantage share; its real sampling error needs a clustering unit the aggregates do not have, so it waits for a by-conference platoon table):

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| Plate appearances by batters hitting left | 0.410 | 0.405 | ±0.007 | report | in range | reported: binomial tolerance on plate appearances, too small (they cluster by player) |
| Plate appearances against left-handed pitchers | 0.259 | 0.252 | ±0.006 | report | outside | reported: binomial tolerance on plate appearances, too small (they cluster by player) |
| Platoon advantage above random pairing (within tier) | 0.0080 | 0.0220 | ±0.0056 | report | outside | reported: binomial tolerance on plate appearances, too small (they cluster by player); lineups, bullpens and pinch hitters make it |
| Plate appearances with the platoon advantage | 0.464 | 0.480 | ±0.006 | report | outside |  |

Levels (reported, not gated): the hand-known plate appearances of a tier are not a sample of that tier (low-tier batters in the play-by-play face mostly P4 pitching, the schedules of the teams it covers), so the real levels, tier-weighted, carry their opponents; the league's levels are gated in Phase 2.

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| K%, batters hitting left vs LHP | 0.2021 | 0.2274 | ±0.0158 | report | outside |  |
| BB%, batters hitting left vs LHP | 0.1110 | 0.1075 | ±0.0110 | report | in range |  |
| HR%, batters hitting left vs LHP | 0.0172 | 0.0118 | ±0.0023 | report | outside |  |
| BABIP, batters hitting left vs LHP | 0.3347 | 0.3454 | ±0.0233 | report | in range |  |
| on base / PA, batters hitting left vs LHP | 0.3765 | 0.3715 | ±0.0184 | report | in range |  |
| K%, batters hitting left vs RHP | 0.1783 | 0.2170 | ±0.0093 | report | outside |  |
| BB%, batters hitting left vs RHP | 0.1186 | 0.1186 | ±0.0069 | report | in range |  |
| HR%, batters hitting left vs RHP | 0.0292 | 0.0249 | ±0.0029 | report | outside |  |
| BABIP, batters hitting left vs RHP | 0.3349 | 0.3164 | ±0.0130 | report | outside |  |
| on base / PA, batters hitting left vs RHP | 0.3896 | 0.3635 | ±0.0101 | report | outside |  |
| K%, batters hitting right vs LHP | 0.2031 | 0.2353 | ±0.0113 | report | outside |  |
| BB%, batters hitting right vs LHP | 0.0983 | 0.1013 | ±0.0079 | report | in range |  |
| HR%, batters hitting right vs LHP | 0.0295 | 0.0250 | ±0.0036 | report | outside |  |
| BABIP, batters hitting right vs LHP | 0.3286 | 0.3162 | ±0.0157 | report | in range |  |
| on base / PA, batters hitting right vs LHP | 0.3626 | 0.3415 | ±0.0123 | report | outside |  |
| K%, batters hitting right vs RHP | 0.2006 | 0.2341 | ±0.0075 | report | outside |  |
| BB%, batters hitting right vs RHP | 0.0953 | 0.0947 | ±0.0050 | report | in range |  |
| HR%, batters hitting right vs RHP | 0.0236 | 0.0200 | ±0.0020 | report | outside |  |
| BABIP, batters hitting right vs RHP | 0.3417 | 0.3277 | ±0.0103 | report | outside |  |
| on base / PA, batters hitting right vs RHP | 0.3696 | 0.3453 | ±0.0080 | report | outside |  |
| K%, switch hitters vs LHP | 0.1991 | 0.2613 | ±0.0569 | report | outside |  |
| BB%, switch hitters vs LHP | 0.0999 | 0.0743 | ±0.0278 | report | in range |  |
| HR%, switch hitters vs LHP | 0.0318 | 0.0290 | ±0.0231 | report | in range |  |
| BABIP, switch hitters vs LHP | 0.3295 | 0.3233 | ±0.0747 | report | in range |  |
| on base / PA, switch hitters vs LHP | 0.3678 | 0.3143 | ±0.0550 | report | in range |  |
| K%, switch hitters vs RHP | 0.1793 | 0.2086 | ±0.0293 | report | in range |  |
| BB%, switch hitters vs RHP | 0.1182 | 0.1286 | ±0.0234 | report | in range |  |
| HR%, switch hitters vs RHP | 0.0286 | 0.0201 | ±0.0099 | report | in range |  |
| BABIP, switch hitters vs RHP | 0.3334 | 0.2797 | ±0.0388 | report | outside |  |
| on base / PA, switch hitters vs RHP | 0.3879 | 0.3546 | ±0.0326 | report | outside |  |

## Usage by hand (AI manager)

| Row | Sim | Real | Tolerance | Gated | Verdict | Note |
|---|---|---|---|---|---|---|
| Pitching changes per PA, left-hander pitching: RHB due up over LHB | 1.776 | 1.765 | ±0.181 | yes | pass |  |
| Pitching changes per PA, right-hander pitching: LHB due up over RHB | 1.170 | 1.159 | ±0.068 | yes | pass |  |
| Relief entries by left-handers: LHB due up minus RHB due up | 0.226 | 0.236 | ±0.024 | yes | pass |  |
| Pinch hitters per opportunity: batter due up of the pitcher's hand over the other | 2.305 | 2.296 | ±0.237 | yes | pass |  |
| Pinch hitters with the platoon advantage | 0.675 | 0.678 | ±0.022 | yes | pass |  |

## Earlier phases on the same run

| Phase | Gate |
|---|---|
| phase2 | PASS |
| phase4 | PASS |
| phase5 | FAIL |
| phase6 | FAIL |
| phase7 | FAIL |

## Individual platoon spread (reported, not gated)

SD of the true logit split (vs L minus vs R) across qualified players (50+ trials against each hand), noise variance subtracted. The engine has league-level shifts only (GUESSES.md: individual spread zero), so its spread is what the shifts and the opponents' mix leave. Real: platoon_spread.csv (play-by-play, permutation null in true_sd_net).

| Side | Rate | Sim players / season | Sim true SD | Real players | Real true SD (net of null) | Real true SD | Real obs. var |
|---|---|---|---|---|---|---|---|
| batter | K | 1427 | 0.083 | 86 | 0.175 | 0.191 | 0.231 ± 0.035 |
| batter | BB | 1427 | 0.137 | 86 | 0.000 | 0.000 | 0.236 ± 0.036 |
| batter | HR | 1427 | 0.000 | 86 | 0.381 | 0.390 | 0.817 ± 0.125 |
| batter | OB | 1427 | 0.040 | 86 | 0.000 | 0.111 | 0.119 ± 0.018 |
| batter | BABIP | 1427 | 0.000 | 86 | 0.000 | 0.115 | 0.208 ± 0.032 |
| pitcher | K | 2191 | 0.108 | 141 | 0.319 | 0.333 | 0.263 ± 0.031 |
| pitcher | BB | 2191 | 0.097 | 141 | 0.275 | 0.287 | 0.434 ± 0.052 |
| pitcher | HR | 2191 | 0.000 | 141 | 0.218 | 0.325 | 0.929 ± 0.111 |
| pitcher | OB | 2191 | 0.026 | 141 | 0.126 | 0.130 | 0.130 ± 0.016 |
| pitcher | BABIP | 2191 | 0.015 | 141 | 0.000 | 0.000 | 0.198 ± 0.024 |

## Platoon effects and the watch item 'offense extremes compressed' (owner adjustment 5)

Against PR B's 40-season run (reports/phase3_baseline_prb.json). Gap closed: (this run - PR B) / (real - PR B).

| Row | Real | PR B | Phase 3 | Change | Gap closed |
|---|---|---|---|---|---|
| P4 vs mid nonconference margin SD | 5.9702 | 5.6139 | 5.6373 | +0.0235 ± 0.0390 | 7% ± 11% |
| Regional upset rate (games without the host) | 0.3705 | 0.3425 | 0.3562 | +0.0137 ± 0.0174 | 49% ± 62% |
| Runs per team-game, 15+ bin | 0.0664 | 0.0509 | 0.0499 | -0.0010 ± 0.0011 | -7% ± 7% |
| Run-rule frequency | 0.1524 | 0.1164 | 0.1142 | -0.0023 ± 0.0020 | -6% ± 5% |

