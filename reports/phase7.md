# Phase 7 realism report: season and world

40 simulated seasons, seeds 20251000–20251039, with cancellations, conference tournaments, selection and the NCAA tournament (config.phase7.FEATURES). Generated 2026-10-06. Tolerances: 3 × the combined standard error of the benchmark and of the simulated mean at 40 seasons. Mean postseason games per season 462.

## Gate: **FAIL**

Phase 1-6 rows on the same run (regular season): phase2 **pass**, phase4 **pass**, phase5 **pass**, phase6 **pass**.

## RPI

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| RPI formula vs NCAA published (2026, rank correlation) | 0.99994 | ≥ 0.999 | — | A | yes | pass | 206/308 ranks exact, 303 within 3; without site weighting 0.9929 |
| RPI of the team ranked 1 | 0.6392 | 0.6326 | ±0.0165 | B | yes | pass | 2025 / 2026: 0.6289 / 0.6363; season SD 0.0071.  |
| RPI of the team ranked 16 | 0.5928 | 0.5948 | ±0.0079 | B | yes | pass | 2025 / 2026: 0.5972 / 0.5925; season SD 0.0034.  |
| RPI of the team ranked 32 | 0.5734 | 0.5692 | ±0.0039 | B | yes | FAIL | 2025 / 2026: 0.5703 / 0.5682; season SD 0.0014.  |
| RPI of the team ranked 64 | 0.5484 | 0.5433 | ±0.0028 | B | report | outside | 2025 / 2026: 0.5444 / 0.5421; season SD 0.0011. watch item 'offense extremes compressed' |
| Mean RPI, p4 | 0.5632 | 0.5599 | ±0.0070 | B | yes | pass | 2025 / 2026: 0.5616 / 0.5583; season SD 0.0029.  |
| Mean RPI, mid | 0.4970 | 0.4941 | ±0.0050 | B | yes | pass | 2025 / 2026: 0.4946 / 0.4936; season SD 0.0021.  |
| Mean RPI, low | 0.4577 | 0.4572 | ±0.0083 | B | yes | pass | 2025 / 2026: 0.4570 / 0.4574; season SD 0.0034.  |

## Season and standings

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regular-season games canceled (share) | 0.0278 | 0.0272 | ±0.0029 | B | yes | pass |  |
| Regular-season games played per team | 52.30 | 52.25 | ±0.34 | B | yes | pass | 2025 / 2026: 52.36 / 52.14 |
| Scheduled games per team: mean / share at 56 / 10th percentile | 53.80 / 0.288 / 51.1 | 53.71 / 0.267 / 50 | — | B | report | — | real targets above 56 (0.042) are capped at the 56-game frame and below 42 (0.018) at its 42 weekend games |
| Win% SD across teams, p4 | 0.1126 | 0.1205 | ±0.0083 | B | yes | pass | 2025 / 2026: 0.1173 / 0.1236; season SD 0.0033.  |
| Win% SD across teams, mid | 0.1344 | 0.1331 | ±0.0076 | B | yes | pass | 2025 / 2026: 0.1389 / 0.1272; season SD 0.0032.  |
| Win% SD across teams, low | 0.1408 | 0.1458 | ±0.0221 | B | yes | pass | 2025 / 2026: 0.1542 / 0.1374; season SD 0.0102.  |
| Best regular-season win% | 0.862 (seasons 0.800–0.959) | 0.821–0.917 | ±0.016 | B | yes | pass | band of real seasons 2017-2025 |

## The field

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| At-large bids, p4 | 30.35 | 29.50 | ±4.87 | B | yes | pass | 2025 / 2026: 31.00 / 28.00; season SD 2.2361.  |
| At-large bids, mid | 4.15 | 5.50 | ±3.81 | B | yes | pass | 2025 / 2026: 4.00 / 7.00; season SD 1.7321.  |
| At-large bids, low | 0.50 | 0.00 | ±0.46 | B | report | outside | 2025 / 2026: 0.00 / 0.00; season SD 0.0. no low-tier at-large bid in 2022-2026: reported |
| Conferences with more than one bid | 7.85 | 7.50 | ±2.99 | B | yes | pass | 2025 / 2026: 8.00 / 7.00; season SD 1.354.  |
| Worst RPI rank given an at-large bid | 57.5 | 50.0 | ±9.4 | B | yes | pass | 2025 / 2026: 49.0 / 51.0; season SD 3.7639.  |
| Best RPI rank left out | 34.1 | 33.5 | ±7.7 | B | yes | pass | 2025 / 2026: 39.0 / 28.0; season SD 3.4157.  |
| P4 vs mid nonconference: P4 win% | 0.770 | 0.759 | ±0.049 | B | report | in range | 2025 / 2026: 0.762 / 0.756; season SD 0.0215.  |
| P4 vs mid nonconference: run margin | 3.96 | 3.97 | ±0.86 | B | report | in range | 2025 / 2026: 4.00 / 3.93; season SD 0.3859.  |
| P4 vs mid nonconference: run margin SD | 5.71 | 5.97 | ±0.30 | B | report | in range | 2025 / 2026: 5.99 / 5.95; season SD 0.1349. watch item 'offense extremes compressed' |

## Seeds and results

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regional hosts winning their regional (share) | 0.630 | 0.625 | ±0.127 | B | yes | pass |  |
| Top-8 national seeds reaching Omaha (of 8) | 3.75 | 4.10 | ±1.26 | B | yes | pass |  |
| National seeds among the 8 CWS teams (2018 on) | 5.83 | 5.43 | ±1.29 | B | yes | pass |  |
| CWS slots, p4 (share) | 0.891 | 0.912 | ±0.109 | B | yes | pass |  |
| CWS slots, mid (share) | 0.106 | 0.075 | ±0.103 | B | yes | pass |  |
| CWS slots, low (share) | 0.003 | 0.013 | ±0.038 | B | report | in range |  |
| Champion's tier (P4 / mid / low) | 0.93 / 0.07 / 0.00 | 0.90 / 0.10 / 0.00 | — | B | report | — | 2015-2025 |

## Postseason home field

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Regional host at its park (win%) | 0.728 | 0.734 | ±0.062 | B | yes | pass |  |
| Regional games without the host: better seed (win%) | 0.647 | 0.629 | ±0.079 | B | yes | pass |  |
| Super regional host at its park (win%) | 0.644 | 0.601 | ±0.121 | B | yes | pass |  |
| CWS (neutral): listed home (win%) | 0.549 | 0.442 | ±0.139 | B | report | in range | the sim lists the better seed as home; the feed's listing convention is not known |

## Conference tournaments and bracketing

| Metric | Sim | Benchmark | Tol | Conf | Gated | Status | Note |
|---|---|---|---|---|---|---|---|
| Conference tournaments won by a regular-season (co-)champion | 0.407 | 0.425 | ±0.117 | B | yes | pass |  |
| Regionals with two teams of one conference (per season) | 0.00 | 0 | — | A | yes | pass | NCAA bracketing principles (2025 manual, Section 2-3) |

## Watch items (re-checked, not gated)

- Top starters' innings, full seasons (regular + postseason, 56-game equivalent): #1 74.7, #2 62.6, #3 51.2 (real 75.351 / 65.25 ± 4.455 / 53.288); pitchers with 50+ IP 791 (real 821.1; regular season only, Phase 6 report).
- Teams under 4.00 ERA, full seasons 14.1, regular season 16.2 (2024-2026: 6–12). Same definition on both sides: the NCAA.com team ERA page counts every game of a season, conference tournaments and the NCAA tournament included (2025 data year: Northeastern 60 games, Coastal Carolina 69); the sim's full season is its regular season plus its postseason (it has no non-Division I games).
- Unearned runs, full seasons: earned share of runs allowed 0.879 (real .882, WMT play-by-play 2025); the 50 lowest-ERA teams 0.900 (real .869 / .866 / .867 in 2024 / 2025 / 2026, NCAA.com team ERA page), unearned runs per game for them 0.46 (real .67 / .65 / .65), runs allowed per game 4.58 (real 5.05 / 4.80 / 4.81).
- Game-to-game spread and postseason upsets (watch item 'offense extremes compressed'): P4 vs mid nonconference margin SD 5.71 against 5.97 real (2025-2026), ratio 0.957. With the real spread the better seed's win% in regional games without the host would be about 0.641 instead of 0.647, and the host's 0.719 instead of 0.728 (normal margin model: an upset rate higher by 0.6 and 0.9 points per game).
- Pitching against fielding, full seasons (lead from the unearned-run check, owner request 2026-10-05): correlation across teams of ERA with errors per game 0.720 (real 2025 0.655; with fielding % -0.680), of runs allowed per game with errors per game 0.795 (real 0.721). Errors per game: all teams 1.090 (real 1.150), the 50 best by runs allowed per game 0.735 (real 0.866), the 50 best by ERA 0.762 (real 0.912). Earned share (mean of team ER/R): all 0.883 (real 0.870), the 50 best by ERA 0.901 (real 0.866). Real: NCAA.com team pages, 2025, every game; scripts/build_phase7_era_fielding.py.
