# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

40 simulated 56-game seasons, seeds 20251000–20251039, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-05. Tolerances combine the benchmark's with 3 SE of the simulated mean at 40 seasons.

## Gate: **PASS**

Every Phase 1 and 2 row (reports/phase2.md): **pass**; Phase 4 forward ratings test (reports/phase4.md): **pass**; Phase 5 pitch-by-pitch (reports/phase5.md): **pass**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.079 | 1.099 | ±0.153 | pass |  |
| Stolen bases per team-game | 1.010 | 1.098 | ±0.100 | pass |  |
| Steal success rate | 0.771 | 0.760 | ±0.030 | pass |  |
| PA per team-game | 40.67 | 40.31 | ±1.00 | pass | gated here, not against the Phase 4 run (base running per opportunity moves it) |
| Earned share of runs | 0.8791 | 0.8824 | ±0.0084 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.803, mid 1.061, low 1.307 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.309 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 25.26 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.88 | 17.58 | ±0.77 | pass |  |
| Appearances, 10th busiest | 13.85 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.82 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.04 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 72.10 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 61.01 | 65.25 | ±4.47 | pass | watch item: top starters' innings (re-check in Phase 7).  |
| IP, 3rd | 51.05 | 53.29 | ±3.83 | pass |  |
| Distinct batters per team-game | 10.480 | 10.420 | ±0.078 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.9 / 61.2, other starts 7.0 / 9.8, relief 4.0 / 4.4; #2: Fri-Sun starts 46.1 / 50.3, other starts 6.6 / 5.6, relief 7.2 / 9.3; #3: Fri-Sun starts 28.1 / 29.2, other starts 6.5 / 5.4, relief 15.6 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1206 | 0.1524 | ±0.0161 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0538 | 0.0664 | ±0.0103 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.31 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.37 | 10.56 | ±1.30 | pass |  |
| P4 batting vs low pitching (R/G) | 9.54 | 9.82 | ±1.11 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.6 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 789.4 (seasons 758–847) | 821.1 | ±39.8 (95% PI) | pass | watch item: top starters' innings (re-check in Phase 7). 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | -0.000 | 0.000 | ±0.009 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.008 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.003 | 0.000 | ±0.005 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.004 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | -0.004 | 0.000 | ±0.007 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | -0.000 | 0.000 | ±0.006 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.263 / +0.282, run prevention +0.353 / +0.334; mid offense +0.009 / +0.010, run prevention +0.002 / +0.005; low offense -0.203 / -0.220, run prevention -0.255 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.122 / -0.039; low|mid +0.087 / +0.088; low|p4 +0.169 / +0.154; mid|low -0.056 / -0.060; mid|mid +0.014 / +0.012; mid|p4 +0.023 / +0.028; p4|low -0.010 / -0.005; p4|mid +0.019 / +0.016; p4|p4 -0.034 / +0.018. Cross-tier covariance of opponents' deviations 0.0178 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0480 (real 0.0734), dispersion 2.222 (real 2.6185); with the park term: 0.0076 (real 0.0377), 2.169 (real 2.5674).
- Strikeout leader 138.8 (seasons 114–182); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.45, #2 1.68, #5 2.03 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 33.5 (real 38 / 37 / 39); 50th-most-used pitcher 27.8 (29 / 28 / 28); of the top 50 by appearances 1.2 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 71.6 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 8.7; the IP leader is a reliever in 0 of 40 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 2.99 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 5.4 (5), < 3.00 48.7 (57), teams with ERA < 4.00 16.0 (2024-2026: 6 / 12 / 12).
