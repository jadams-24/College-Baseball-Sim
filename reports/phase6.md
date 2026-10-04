# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

40 simulated 56-game seasons, seeds 20251000–20251039, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-04. Tolerances combine the benchmark's with 3 SE of the simulated mean at 40 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.087 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.008 | 1.098 | ±0.100 | pass |  |
| Steal success rate | 0.771 | 0.760 | ±0.030 | pass |  |
| PA per team-game | 40.66 | 40.31 | ±1.00 | pass | gated here, not against the Phase 4 run (base running per opportunity moves it) |
| Earned share of runs | 0.8789 | 0.8824 | ±0.0083 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.814, mid 1.069, low 1.315 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.308 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 25.03 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.77 | 17.58 | ±0.77 | pass |  |
| Appearances, 10th busiest | 13.83 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.79 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.03 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.48 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 60.71 | 65.25 | ±4.46 | FAIL |  |
| IP, 3rd | 50.76 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.480 | 10.420 | ±0.078 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.6 / 61.2, other starts 6.9 / 9.8, relief 3.8 / 4.4; #2: Fri-Sun starts 46.3 / 50.3, other starts 6.5 / 5.6, relief 6.9 / 9.3; #3: Fri-Sun starts 28.3 / 29.2, other starts 6.5 / 5.4, relief 15.1 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1212 | 0.1524 | ±0.0161 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0540 | 0.0664 | ±0.0103 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.33 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.39 | 10.56 | ±1.30 | pass |  |
| P4 batting vs low pitching (R/G) | 9.58 | 9.82 | ±1.11 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.6 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 785.0 (seasons 747–815) | 821.1 | ±32.1 (95% PI) | FAIL | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.007 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | -0.000 | 0.000 | ±0.008 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.003 | 0.000 | ±0.005 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | 0.002 | 0.000 | ±0.004 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | -0.004 | 0.000 | ±0.008 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | -0.003 | 0.000 | ±0.005 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.264 / +0.282, run prevention +0.353 / +0.334; mid offense +0.009 / +0.010, run prevention +0.003 / +0.005; low offense -0.203 / -0.220, run prevention -0.257 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.121 / -0.039; low|mid +0.087 / +0.088; low|p4 +0.168 / +0.154; mid|low -0.056 / -0.060; mid|mid +0.014 / +0.012; mid|p4 +0.023 / +0.028; p4|low -0.012 / -0.005; p4|mid +0.020 / +0.016; p4|p4 -0.036 / +0.018. Cross-tier covariance of opponents' deviations 0.0176 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0460 (real 0.0734), dispersion 2.225 (real 2.6185); with the park term: 0.0067 (real 0.0377), 2.173 (real 2.5674).
- Strikeout leader 138.3 (seasons 117–192); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.51, #2 1.75, #5 2.04 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 34.6 (real 38 / 37 / 39); 50th-most-used pitcher 28.2 (29 / 28 / 28); of the top 50 by appearances 1.2 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 72.4 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 10.2; the IP leader is a reliever in 0 of 40 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 2.98 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 5.1 (5), < 3.00 45.8 (57), teams with ERA < 4.00 15.5 (2024-2026: 6 / 12 / 12).
