# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-02. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.104 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.143 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.770 | 0.760 | ±0.030 | pass |  |

Errors per team-game by tier: P4 0.819, mid 1.082, low 1.345 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.484 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 24.47 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.40 | 17.58 | ±0.78 | pass |  |
| Appearances, 10th busiest | 13.56 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.74 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.03 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 72.42 | 75.35 | ±4.26 | pass |  |
| IP, 2nd | 61.44 | 65.25 | ±4.47 | pass |  |
| IP, 3rd | 51.32 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.484 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 60.5 / 61.2, other starts 7.1 / 9.8, relief 3.4 / 4.4; #2: Fri-Sun starts 47.0 / 50.3, other starts 6.9 / 5.6, relief 6.4 / 9.3; #3: Fri-Sun starts 28.7 / 29.2, other starts 7.4 / 5.4, relief 14.2 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1292 | 0.1524 | ±0.0165 | FAIL |  |
| Runs per team-game, 15+ bin | 0.0559 | 0.0664 | ±0.0104 | FAIL |  |
| Qualified K/9 p50 | 8.28 | 7.88 | ±0.93 | pass |  |
| Qualified K/9 p90 | 11.32 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 10.65 | 9.82 | ±1.11 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 22.3 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 807.4 (seasons 771–834) | 821.1 | ±38.2 (95% PI) | pass | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0511 (real 0.0734), dispersion 2.224 (real 2.5674); with the park term: 0.0097 (real 0.0377), 2.166.
- Strikeout leader 147.2 (seasons 124–183); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.35, #2 1.70, #5 2.05 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Elite run prevention (Phase 2 rows): best team ERA 2.88 (real 3.20), 50+ IP pitchers with ERA < 2.00 6.0 (5), < 3.00 44.5 (57), teams with ERA < 4.00 15.9 (12).
