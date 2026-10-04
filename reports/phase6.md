# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-04. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.087 | 1.099 | ±0.152 | pass |  |
| Stolen bases per team-game | 1.005 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.771 | 0.760 | ±0.030 | pass |  |
| Earned share of runs | 0.8789 | 0.8824 | ±0.0086 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.818, mid 1.067, low 1.313 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.304 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 25.04 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.77 | 17.58 | ±0.77 | pass |  |
| Appearances, 10th busiest | 13.84 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.79 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.03 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.55 | 75.35 | ±4.26 | pass |  |
| IP, 2nd | 60.71 | 65.25 | ±4.48 | FAIL |  |
| IP, 3rd | 50.75 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.480 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.7 / 61.2, other starts 7.0 / 9.8, relief 3.7 / 4.4; #2: Fri-Sun starts 46.1 / 50.3, other starts 6.6 / 5.6, relief 7.0 / 9.3; #3: Fri-Sun starts 28.2 / 29.2, other starts 6.4 / 5.4, relief 15.2 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1217 | 0.1524 | ±0.0170 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0537 | 0.0664 | ±0.0107 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.34 | 7.88 | ±0.93 | pass |  |
| Qualified K/9 p90 | 11.35 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 9.58 | 9.82 | ±1.23 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.6 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 787.2 (seasons 747–815) | 821.1 | ±33.9 (95% PI) | FAIL | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.010 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.011 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.002 | 0.000 | ±0.007 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | 0.000 | 0.000 | ±0.004 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | -0.001 | 0.000 | ±0.010 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.007 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.263 / +0.282, run prevention +0.350 / +0.334; mid offense +0.008 / +0.010, run prevention +0.004 / +0.005; low offense -0.201 / -0.220, run prevention -0.255 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.119 / -0.039; low|mid +0.088 / +0.088; low|p4 +0.171 / +0.154; mid|low -0.057 / -0.060; mid|mid +0.016 / +0.012; mid|p4 +0.023 / +0.028; p4|low -0.012 / -0.005; p4|mid +0.021 / +0.016; p4|p4 -0.034 / +0.018. Cross-tier covariance of opponents' deviations 0.0175 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0458 (real 0.0734), dispersion 2.232 (real 2.6185); with the park term: 0.0064 (real 0.0377), 2.179 (real 2.5674).
- Strikeout leader 138.7 (seasons 121–174); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.58, #2 1.78, #5 2.08 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 35.0 (real 38 / 37 / 39); 50th-most-used pitcher 28.2 (29 / 28 / 28); of the top 50 by appearances 0.8 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 72.3 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 10.4; the IP leader is a reliever in 0 of 20 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 3.04 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 4.2 (5), < 3.00 45.7 (57), teams with ERA < 4.00 14.6 (2024-2026: 6 / 12 / 12).
