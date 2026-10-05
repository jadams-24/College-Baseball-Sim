# Phase 7 realism report: season and world

40 simulated seasons, seeds 20251000–20251039, with cancellations, conference tournaments, selection and the NCAA tournament (config.phase7.FEATURES). Generated 2026-10-05. Tolerances: 3 × the combined standard error of the benchmark and of the simulated mean at 40 seasons. Mean postseason games per season 462.

## Gate: **FAIL**

Phase 1-6 rows on the same run (regular season): phase2 **pass**, phase4 **pass**, phase5 **pass**, phase6 **pass**.

## RPI

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| RPI formula vs NCAA published (2026, rank correlation) | 0.99994 | ≥ 0.999 | — | A | yes | pass | 206/308 ranks exact, 303 within 3; without site weighting 0.9929 |
| RPI of the team ranked 1 | 0.6387 | 0.6257 | ±0.0095 | B | yes | FAIL |  |
| RPI of the team ranked 16 | 0.5916 | 0.5840 | ±0.0070 | B | yes | FAIL |  |
| RPI of the team ranked 32 | 0.5739 | 0.5668 | ±0.0047 | B | yes | FAIL |  |
| RPI of the team ranked 64 | 0.5489 | 0.5426 | ±0.0047 | B | yes | FAIL |  |
| Mean RPI, p4 | 0.5640 | 0.5521 | ±0.0084 | B | yes | FAIL |  |
| Mean RPI, mid | 0.4969 | 0.4966 | ±0.0033 | B | yes | pass |  |
| Mean RPI, low | 0.4571 | 0.4579 | ±0.0064 | B | yes | pass |  |

## Season and standings

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regular-season games canceled (share) | 0.0279 | 0.0272 | ±0.0029 | B | yes | pass |  |
| Regular-season games per team | 54.26 | 52.25 | — | B | report | — | real teams schedule 53.7 (the sim 56, the NCAA maximum; no shortened schedules by owner decision) and lose 1.46 to cancellations |
| Win% SD across teams, p4 | 0.1108 | 0.1210 | ±0.0088 | B | yes | FAIL |  |
| Win% SD across teams, mid | 0.1332 | 0.1360 | ±0.0081 | B | yes | pass |  |
| Win% SD across teams, low | 0.1386 | 0.1473 | ±0.0124 | B | yes | pass |  |
| Best regular-season win% | 0.851 (seasons 0.786–0.923) | 0.821–0.917 | ±0.014 | B | yes | pass | band of real seasons |

## The field

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| At-large bids, p4 | 30.18 | 26.00 | ±2.66 | B | yes | FAIL |  |
| At-large bids, mid | 4.20 | 7.10 | ±2.18 | B | yes | FAIL |  |
| At-large bids, low | 0.62 | 0.40 | ±0.73 | B | yes | pass |  |
| Conferences with more than one bid | 7.45 | 10.60 | ±1.71 | B | yes | FAIL |  |
| Worst RPI rank given an at-large bid | 60.9 | 56.9 | ±12.7 | B | yes | pass |  |
| Best RPI rank left out | 31.4 | 30.2 | ±5.1 | B | yes | pass |  |

## Seeds and results

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regional hosts winning their regional (share) | 0.592 | 0.625 | ±0.130 | B | yes | pass |  |
| Top-8 national seeds reaching Omaha (of 8) | 3.45 | 4.10 | ±1.25 | B | yes | pass |  |
| National seeds among the 8 CWS teams (2018 on) | 5.30 | 5.43 | ±1.27 | B | yes | pass |  |
| CWS slots, p4 (share) | 0.894 | 0.912 | ±0.108 | B | yes | pass |  |
| CWS slots, mid (share) | 0.100 | 0.075 | ±0.101 | B | yes | pass |  |
| CWS slots, low (share) | 0.006 | 0.013 | ±0.039 | B | report | in range |  |
| Champion's tier (P4 / mid / low) | 0.97 / 0.03 / 0.00 | 0.90 / 0.10 / 0.00 | — | B | report | — | 2015-2025 |

## Postseason home field

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regional host at its park (win%) | 0.705 | 0.734 | ±0.064 | B | yes | pass |  |
| Regional games without the host: better seed (win%) | 0.659 | 0.629 | ±0.078 | B | yes | pass |  |
| Super regional host at its park (win%) | 0.595 | 0.601 | ±0.120 | B | yes | pass |  |
| CWS (neutral): listed home (win%) | 0.580 | 0.442 | ±0.136 | B | report | outside | the sim lists the better seed as home; the feed's listing convention is not known |

## Conference tournaments and bracketing

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Conference tournaments won by a regular-season (co-)champion | 0.392 | 0.425 | ±0.119 | B | yes | pass |  |
| Regionals with two teams of one conference (per season) | 0.00 | 0 | — | A | yes | pass | NCAA bracketing principles (2025 manual, Section 2-3) |

## Watch items (re-checked, not gated)

- Top starters' innings, full seasons (regular + postseason, 56-game equivalent): #1 72.6, #2 61.1, #3 50.8 (real 75.351 / 65.25 ± 4.455 / 53.288); pitchers with 50+ IP 781 (real 821.1; regular season only, Phase 6 report).
- Teams under 4.00 ERA, full seasons 13.5, regular season 16.0 (2024-2026: 6–12, real seasons include the postseason).
