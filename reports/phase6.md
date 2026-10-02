# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

20 simulated 56-game seasons, seeds 20251000–20251019, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-02. Tolerances combine the benchmark's with 3 SE of the simulated mean at 20 seasons.

## Gate: **FAIL**

Every Phase 1 and 2 row (reports/phase2.md): **FAIL**; Phase 4 forward ratings test (reports/phase4.md): **FAIL**; Phase 5 pitch-by-pitch (reports/phase5.md): **FAIL**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.100 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.144 | 1.098 | ±0.101 | pass |  |
| Steal success rate | 0.772 | 0.760 | ±0.030 | pass |  |
| Earned share of runs | 0.8781 | 0.8824 | ±0.0085 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.817, mid 1.076, low 1.343 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.483 (real 1.436).

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 24.82 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.67 | 17.58 | ±0.78 | pass |  |
| Appearances, 10th busiest | 13.74 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.78 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.04 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 71.90 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 60.96 | 65.25 | ±4.47 | pass |  |
| IP, 3rd | 50.75 | 53.29 | ±3.84 | pass |  |
| Distinct batters per team-game | 10.473 | 10.420 | ±0.078 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 59.8 / 61.2, other starts 7.0 / 9.8, relief 3.8 / 4.4; #2: Fri-Sun starts 46.6 / 50.3, other starts 6.5 / 5.6, relief 6.7 / 9.3; #3: Fri-Sun starts 28.0 / 29.2, other starts 6.5 / 5.4, relief 15.3 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1250 | 0.1524 | ±0.0165 | FAIL |  |
| Runs per team-game, 15+ bin | 0.0529 | 0.0664 | ±0.0106 | FAIL |  |
| Qualified K/9 p50 | 8.39 | 7.88 | ±0.93 | pass |  |
| Qualified K/9 p90 | 11.37 | 10.56 | ±1.31 | pass |  |
| P4 batting vs low pitching (R/G) | 10.47 | 9.82 | ±1.15 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.6 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 785.0 (seasons 768–809) | 821.1 | ±28.3 (95% PI) | FAIL | 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0538 (real 0.0734), dispersion 2.220 (real 2.6185); with the park term: 0.0115 (real 0.0377), 2.159 (real 2.5674).
- Strikeout leader 144.6 (seasons 122–178); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.47, #2 1.62, #5 1.93 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Elite run prevention (Phase 2 rows): best team ERA 2.73 (real 3.20), 50+ IP pitchers with ERA < 2.00 7.1 (5), < 3.00 55.8 (57), teams with ERA < 4.00 23.1 (12).
