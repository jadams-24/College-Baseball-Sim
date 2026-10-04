# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-04. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **PASS**

Every Phase 1 and 2 row (reports/phase2.md): **pass**; Phase 4 forward ratings test (reports/phase4.md): **pass**; Phase 5 pitch-by-pitch (reports/phase5.md): **pass**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.104 | 1.099 | ±0.152 | pass |  |
| Stolen bases per team-game | 1.146 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.770 | 0.760 | ±0.030 | pass |  |
| Earned share of runs | 0.8790 | 0.8824 | ±0.0086 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.836, mid 1.084, low 1.329 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.488 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 25.04 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.76 | 17.58 | ±0.78 | pass |  |
| Appearances, 10th busiest | 13.84 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.81 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.03 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.45 | 75.35 | ±4.26 | pass |  |
| IP, 2nd | 60.79 | 65.25 | ±4.48 | pass |  |
| IP, 3rd | 50.81 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.475 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.4 / 61.2, other starts 6.9 / 9.8, relief 3.8 / 4.4; #2: Fri-Sun starts 46.1 / 50.3, other starts 6.5 / 5.6, relief 7.0 / 9.3; #3: Fri-Sun starts 28.1 / 29.2, other starts 6.4 / 5.4, relief 15.3 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1211 | 0.1524 | ±0.0170 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0532 | 0.0664 | ±0.0108 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.32 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.33 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 9.55 | 9.82 | ±1.22 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.6 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 789.0 (seasons 747–831) | 821.1 | ±41.8 (95% PI) | pass | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | 0.006 | 0.000 | ±0.013 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | -0.003 | 0.000 | ±0.011 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.006 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.005 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | -0.006 | 0.000 | ±0.010 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | -0.000 | 0.000 | ±0.009 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.276 / +0.282, run prevention +0.345 / +0.334; mid offense +0.007 / +0.010, run prevention +0.004 / +0.005; low offense -0.209 / -0.220, run prevention -0.252 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.123 / -0.039; low|mid +0.090 / +0.088; low|p4 +0.179 / +0.154; mid|low -0.054 / -0.060; mid|mid +0.015 / +0.012; mid|p4 +0.023 / +0.028; p4|low -0.013 / -0.005; p4|mid +0.021 / +0.016; p4|p4 -0.035 / +0.018. Cross-tier covariance of opponents' deviations 0.0179 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0476 (real 0.0734), dispersion 2.217 (real 2.6185); with the park term: 0.0068 (real 0.0377), 2.163 (real 2.5674).
- Strikeout leader 137.8 (seasons 118–151); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.50, #2 1.76, #5 2.11 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 34.7 (real 38 / 37 / 39); 50th-most-used pitcher 28.1 (29 / 28 / 28); of the top 50 by appearances 1.1 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 73.7 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 10.7; the IP leader is a reliever in 0 of 20 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 3.08 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 4.7 (5), < 3.00 42.8 (57), teams with ERA < 4.00 13.6 (2024-2026: 6 / 12 / 12).
