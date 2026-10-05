# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

40 simulated 56-game seasons, seeds 20251000–20251039, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-05. Tolerances combine the benchmark's with 3 SE of the simulated mean at 40 seasons.

## Gate: **PASS**

Every Phase 1 and 2 row (reports/phase2.md): **pass**; Phase 4 forward ratings test (reports/phase4.md): **pass**; Phase 5 pitch-by-pitch (reports/phase5.md): **pass**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.087 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.006 | 1.098 | ±0.100 | pass |  |
| Steal success rate | 0.770 | 0.760 | ±0.030 | pass |  |
| PA per team-game | 40.66 | 40.31 | ±1.00 | pass | gated here, not against the Phase 4 run (base running per opportunity moves it) |
| Earned share of runs | 0.8788 | 0.8824 | ±0.0083 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.810, mid 1.070, low 1.314 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.307 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 25.08 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.80 | 17.58 | ±0.77 | pass |  |
| Appearances, 10th busiest | 13.79 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.79 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.04 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 74.33 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 62.57 | 65.25 | ±4.46 | pass | watch item: top starters' innings (re-check in Phase 7).  |
| IP, 3rd | 51.64 | 53.29 | ±3.83 | pass |  |
| Distinct batters per team-game | 10.479 | 10.420 | ±0.078 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 62.7 / 61.2, other starts 6.8 / 9.8, relief 3.6 / 4.4; #2: Fri-Sun starts 48.5 / 50.3, other starts 6.3 / 5.6, relief 6.7 / 9.3; #3: Fri-Sun starts 29.5 / 29.2, other starts 6.1 / 5.4, relief 15.1 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1201 | 0.1524 | ±0.0161 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0533 | 0.0664 | ±0.0103 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.30 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.35 | 10.56 | ±1.30 | pass |  |
| P4 batting vs low pitching (R/G) | 9.61 | 9.82 | ±1.11 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.5 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 804.0 (seasons 767–837) | 821.1 | ±34.3 (95% PI) | pass | watch item: top starters' innings (re-check in Phase 7). 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.009 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | -0.001 | 0.000 | ±0.008 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.003 | 0.000 | ±0.005 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.004 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | -0.006 | 0.000 | ±0.008 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.006 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.265 / +0.282, run prevention +0.354 / +0.334; mid offense +0.009 / +0.010, run prevention +0.002 / +0.005; low offense -0.204 / -0.220, run prevention -0.256 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.121 / -0.039; low|mid +0.087 / +0.088; low|p4 +0.167 / +0.154; mid|low -0.057 / -0.060; mid|mid +0.014 / +0.012; mid|p4 +0.024 / +0.028; p4|low -0.014 / -0.005; p4|mid +0.019 / +0.016; p4|p4 -0.033 / +0.018. Cross-tier covariance of opponents' deviations 0.0179 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0463 (real 0.0734), dispersion 2.224 (real 2.6185); with the park term: 0.0052 (real 0.0377), 2.171 (real 2.5674).
- Strikeout leader 136.9 (seasons 115–183); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.45, #2 1.66, #5 2.03 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 33.0 (real 38 / 37 / 39); 50th-most-used pitcher 26.8 (29 / 28 / 28); of the top 50 by appearances 0.7 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 68.9 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 5.6; the IP leader is a reliever in 0 of 40 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 3.06 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 6.0 (5), < 3.00 48.6 (57), teams with ERA < 4.00 13.8 (2024-2026: 6 / 12 / 12).
