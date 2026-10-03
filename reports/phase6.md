# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-03. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.105 | 1.099 | ±0.152 | pass |  |
| Stolen bases per team-game | 1.142 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.771 | 0.760 | ±0.030 | pass |  |
| Earned share of runs | 0.8778 | 0.8824 | ±0.0086 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.823, mid 1.081, low 1.348 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.482 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 24.87 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.69 | 17.58 | ±0.78 | pass |  |
| Appearances, 10th busiest | 13.81 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.78 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.03 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.75 | 75.35 | ±4.26 | pass |  |
| IP, 2nd | 60.83 | 65.25 | ±4.47 | pass |  |
| IP, 3rd | 50.72 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.482 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.6 / 61.2, other starts 7.0 / 9.8, relief 3.8 / 4.4; #2: Fri-Sun starts 46.8 / 50.3, other starts 6.4 / 5.6, relief 6.5 / 9.3; #3: Fri-Sun starts 28.0 / 29.2, other starts 6.6 / 5.4, relief 15.1 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1292 | 0.1524 | ±0.0173 | FAIL |  |
| Runs per team-game, 15+ bin | 0.0561 | 0.0664 | ±0.0109 | pass |  |
| Qualified K/9 p50 | 8.38 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.36 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 10.59 | 9.82 | ±1.31 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.5 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 783.1 (seasons 744–829) | 821.1 | ±41.5 (95% PI) | pass | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0491 (real 0.0734), dispersion 2.212 (real 2.6185); with the park term: 0.0091 (real 0.0377), 2.160 (real 2.5674).
- Strikeout leader 139.7 (seasons 122–164); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.45, #2 1.72, #5 2.02 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 33.8 (real 38 / 37 / 39); 50th-most-used pitcher 28.1 (29 / 28 / 28); of the top 50 by appearances 1.2 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 73.8 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 10.6; the IP leader is a reliever in 0 of 20 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 2.92 (real 3.20), 50+ IP pitchers with ERA < 2.00 6.2 (5), < 3.00 48.7 (57), teams with ERA < 4.00 19.2 (12).
