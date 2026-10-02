# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-02. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.100 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.140 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.771 | 0.760 | ±0.030 | pass |  |
| Earned share of runs | 0.8787 | 0.8824 | ±0.0085 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.818, mid 1.076, low 1.344 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.480 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 24.89 | 24.49 | ±1.23 | pass |  |
| Appearances, 5th busiest | 17.70 | 17.58 | ±0.78 | pass |  |
| Appearances, 10th busiest | 13.77 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.77 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.04 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.68 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 60.83 | 65.25 | ±4.47 | pass |  |
| IP, 3rd | 50.68 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.478 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.8 / 61.2, other starts 7.0 / 9.8, relief 3.6 / 4.4; #2: Fri-Sun starts 46.5 / 50.3, other starts 6.4 / 5.6, relief 6.8 / 9.3; #3: Fri-Sun starts 27.7 / 29.2, other starts 6.5 / 5.4, relief 15.4 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1282 | 0.1524 | ±0.0166 | FAIL |  |
| Runs per team-game, 15+ bin | 0.0553 | 0.0664 | ±0.0106 | FAIL |  |
| Qualified K/9 p50 | 8.36 | 7.88 | ±0.93 | pass |  |
| Qualified K/9 p90 | 11.35 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 10.56 | 9.82 | ±1.12 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.5 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 785.5 (seasons 757–819) | 821.1 | ±34.8 (95% PI) | FAIL | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0496 (real 0.0734), dispersion 2.216 (real 2.6185); with the park term: 0.0095 (real 0.0377), 2.157 (real 2.5674).
- Strikeout leader 144.6 (seasons 119–171); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.32, #2 1.64, #5 1.96 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 35.0 (real 38 / 37 / 39); 50th-most-used pitcher 28.1 (29 / 28 / 28); of the top 50 by appearances 1.1 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 72.9 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 10.9; the IP leader is a reliever in 0 of 20 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 2.75 (real 3.20), 50+ IP pitchers with ERA < 2.00 6.8 (5), < 3.00 54.6 (57), teams with ERA < 4.00 21.6 (12).
