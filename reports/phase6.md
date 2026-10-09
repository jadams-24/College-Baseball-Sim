# Phase 6 realism report: fielding, parks, fatigue, bullpen, manager AI

40 simulated 56-game seasons, seeds 20251000–20251039, all mechanisms on (config.phase6.FEATURES). Generated 2026-10-08. Tolerances combine the benchmark's with 3 SE of the simulated mean at 40 seasons.

## Gate: **PASS**

Every Phase 1 and 2 row (reports/phase2.md): **pass**; Phase 4 forward ratings test (reports/phase4.md): **pass**; Phase 5 pitch-by-pitch (reports/phase5.md): **pass**.

## Fielding and base running

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Errors per team-game | 1.107 | 1.099 | ±0.151 | pass |  |
| Stolen bases per team-game | 1.039 | 1.098 | ±0.100 | pass |  |
| Steal success rate | 0.767 | 0.760 | ±0.030 | pass |  |
| PA per team-game | 40.73 | 40.31 | ±1.00 | pass | gated here, not against the Phase 4 run (base running per opportunity moves it) |
| ERA | 6.083 | 6.080 | ±0.306 | pass | gated here, not against the Phase 4 run (PR B decisions move it; owner decision 2026-10-07) |
| Earned share of runs | 0.8770 | 0.8824 | ±0.0084 | pass | gated here, not against the Phase 4 run (Phase 6 fielding moves it) |

Errors per team-game by tier: P4 0.837, mid 1.091, low 1.327 (2025 sample, raw: {'p4': 0.893, 'mid': 1.132, 'low': 1.349}). Steal attempts per team-game 1.355 (real 1.436).

## Decisions (PR B: steals before each pitch, called bunts, intentional walks)

The AI manager decides; its attempt, bunt and intentional-walk rates are the play-by-play's, by game state (data/ncaa_2025/derived/prb_steals.json, prb_inputs.json). Benchmarks: the 2025 play-by-play's games, except steal attempts (box scores, league_totals_2025).

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Steal attempts per team-game | 1.355 | 1.436 | ±0.131 | pass | box-score count: every runner in a double steal, a runner picked off while breaking charged a caught stealing |
| Bunts per team-game | 0.737 | 0.720 | ±0.038 | pass |  |
| Sacrifice hits per team-game | 0.367 | 0.362 | ±0.027 | pass |  |
| Bunt hits per team-game | 0.199 | 0.191 | ±0.020 | pass |  |
| Intentional walks per team-game | 0.093 | 0.085 | ±0.013 | pass |  |
| Steal attempts per eligible PA | 0.0759 | 0.0791 | ±0.0033 | pass |  |
| Steal success on eligible PAs | 0.847 | 0.857 | ±0.015 | pass |  |

Steal attempts and success by observed pitch path (owner decision 2026-10-07: the sample free of selection): every plate appearance that began with a lead runner able to steal and has a ball or strike, whatever base running came first; an attempt is any steal or caught stealing during it, counted in the plate appearance it happened in, success that of the first. Computed the same way on the play-by-play (scripts/build_prb_decisions.py selection_free()) and on the simulated plate appearances. Tolerance: 3 SE of the real share combined with 3 SE of the simulated mean.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Attempt per PA, 2 pitches | 0.0250 | 0.0191 | ±0.0043 | FAIL | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 3 pitches | 0.0508 | 0.0424 | ±0.0055 | FAIL | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 4 pitches | 0.0755 | 0.0663 | ±0.0065 | FAIL | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 5 pitches | 0.0975 | 0.0910 | ±0.0079 | pass | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 6 pitches | 0.1138 | 0.1378 | ±0.0110 | FAIL | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 7 pitches | 0.1190 | 0.1697 | ±0.0193 | FAIL | watch item: steal timing within the plate appearance.  |
| Attempt per PA, 8+ pitches | 0.1220 | 0.1722 | ±0.0253 | FAIL | watch item: steal timing within the plate appearance.  |
| Success, 2 pitches | 0.869 | 0.875 | ±0.075 | pass |  |
| Success, 3 pitches | 0.851 | 0.870 | ±0.045 | pass |  |
| Success, 4 pitches | 0.844 | 0.854 | ±0.036 | pass |  |
| Success, 5 pitches | 0.846 | 0.867 | ±0.030 | pass |  |
| Success, 6 pitches | 0.845 | 0.832 | ±0.032 | pass |  |
| Success, 7 pitches | 0.842 | 0.885 | ±0.040 | FAIL | watch item: steal timing within the plate appearance.  |
| Success, 8+ pitches | 0.841 | 0.839 | ±0.059 | pass |  |
| Attempt per PA, final count 0-1 | 0.0251 | 0.0228 | ±0.0068 | pass |  |
| Attempt per PA, final count 0-2 | 0.0508 | 0.0462 | ±0.0082 | pass |  |
| Attempt per PA, final count 1-0 | 0.0248 | 0.0226 | ±0.0063 | pass |  |
| Attempt per PA, final count 1-1 | 0.0507 | 0.0471 | ±0.0086 | pass |  |
| Attempt per PA, final count 1-2 | 0.0760 | 0.0724 | ±0.0079 | pass |  |
| Attempt per PA, final count 2-0 | 0.0515 | 0.0449 | ±0.0143 | pass |  |
| Attempt per PA, final count 2-1 | 0.0790 | 0.0722 | ±0.0136 | pass |  |
| Attempt per PA, final count 2-2 | 0.1020 | 0.1082 | ±0.0098 | pass |  |
| Attempt per PA, final count 3-0 | 0.0772 | 0.0634 | ±0.0171 | pass |  |
| Attempt per PA, final count 3-1 | 0.1021 | 0.0997 | ±0.0136 | pass |  |
| Attempt per PA, final count 3-2 | 0.1232 | 0.1503 | ±0.0106 | FAIL | watch item: steal timing within the plate appearance.  |

Diagnostic, not gated: the first-event sample (plate appearances whose first base-running event is a steal or none; it leaves out those in which a wild pitch, passed ball, pickoff or balk came first, more often long ones, and the engine draws those events before the pitches, so it has no such selection). Sim / real attempt per PA: all 0.0799 / 0.0844; 2 pitches 0.0263 / 0.0195; 3 pitches 0.0536 / 0.0440; 4 pitches 0.0796 / 0.0705; 5 pitches 0.1028 / 0.0996; 6 pitches 0.1199 / 0.1529; 7 pitches 0.1252 / 0.1929; 8+ pitches 0.1285 / 0.1994; final count 0-1 0.0265 / 0.0230, 0-2 0.0536 / 0.0470, 1-0 0.0262 / 0.0233, 1-1 0.0534 / 0.0494, 1-2 0.0801 / 0.0766, 2-0 0.0544 / 0.0482, 2-1 0.0834 / 0.0779, 2-2 0.1075 / 0.1193, 3-0 0.0812 / 0.0705, 3-1 0.1076 / 0.1100, 3-2 0.1296 / 0.1682.

## Pitcher usage (56-game equivalent)

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Appearances, team's busiest pitcher | 24.98 | 24.49 | ±1.22 | pass |  |
| Appearances, 5th busiest | 17.74 | 17.58 | ±0.77 | pass |  |
| Appearances, 10th busiest | 13.69 | 13.17 | ±0.72 | pass |  |
| Relief-only pitchers (≤3 GS) with 40+ IP, per team | 0.77 | 0.76 | ±0.33 | pass |  |
| Relief-only pitchers with 60+ IP, per team | 0.04 | 0.06 | ±0.10 | pass |  |
| IP, team's top pitcher | 74.72 | 75.35 | ±4.25 | pass |  |
| IP, 2nd | 62.91 | 65.25 | ±4.46 | pass | watch item: top starters' innings (re-check in Phase 7).  |
| IP, 3rd | 51.75 | 53.29 | ±3.83 | pass |  |
| Distinct batters per team-game | 10.489 | 10.420 | ±0.079 | pass |  |

Top three pitchers' innings, split (sim / real): #1: Fri-Sun starts 62.9 / 61.2, other starts 6.9 / 9.8, relief 3.7 / 4.4; #2: Fri-Sun starts 49.0 / 50.3, other starts 6.4 / 5.6, relief 6.4 / 9.3; #3: Fri-Sun starts 29.7 / 29.2, other starts 6.0 / 5.4, relief 15.2 / 18.7.

## Rows deferred from Phases 2 and 5

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| Run-rule frequency | 0.1158 | 0.1524 | ±0.0161 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Runs per team-game, 15+ bin | 0.0515 | 0.0664 | ±0.0104 | FAIL | watch item: offense extremes compressed (game-to-game variance; everything tested and ruled out in PHASE0_NOTES).  |
| Qualified K/9 p50 | 8.31 | 7.88 | ±0.92 | pass |  |
| Qualified K/9 p90 | 11.38 | 10.56 | ±1.30 | pass |  |
| P4 batting vs low pitching (R/G) | 9.49 | 9.82 | ±1.09 | pass |  |
| Midweek starter pitch count p10 (Mon-Wed) | 21.5 | 23.0 | ±2.9 | pass |  |
| Pitchers with 50+ IP | 807.5 (seasons 766–842) | 821.1 | ±31.7 (95% PI) | pass | watch item: top starters' innings (re-check in Phase 7). 56-game equivalent of the raw 882 (ratio 0.931 ± 0.0342, WMT full-season teams) |

## Team-strength recovery by tier

The scoreboard fit with parks, run on the simulated seasons, recovers each tier's mean offense and run prevention as drawn (tolerance 3 SE of the season-to-season mean). Team quality comes from player talent; there are no per-tier offsets.

| Metric | Sim | Benchmark | Tol | Status | Note |
|---|---|---|---|---|---|
| P4 offense: recovered minus drawn (park fit, tier mean) | -0.005 | 0.000 | ±0.009 | pass |  |
| P4 run prevention: recovered minus drawn (park fit, tier mean) | 0.003 | 0.000 | ±0.009 | pass |  |
| mid offense: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.004 | pass |  |
| mid run prevention: recovered minus drawn (park fit, tier mean) | -0.000 | 0.000 | ±0.004 | pass |  |
| low offense: recovered minus drawn (park fit, tier mean) | 0.001 | 0.000 | ±0.007 | pass |  |
| low run prevention: recovered minus drawn (park fit, tier mean) | -0.002 | 0.000 | ±0.007 | pass |  |

Fit without parks, simulated against real tier means (diagnostic): p4 offense +0.261 / +0.282, run prevention +0.356 / +0.334; mid offense +0.007 / +0.010, run prevention +0.002 / +0.005; low offense -0.198 / -0.220, run prevention -0.256 / -0.248.

## Schedule selection (diagnostic)

Nonconference opponents are matched by strength within tier (scripts/build_phase6_schedule.py). Mean within-tier deviation of the fitted strength (fit without parks) of the teams in each pairing, sim / real 2025 regular season: low|low -0.120 / -0.039; low|mid +0.085 / +0.088; low|p4 +0.168 / +0.154; mid|low -0.054 / -0.060; mid|mid +0.013 / +0.012; mid|p4 +0.023 / +0.028; p4|low -0.012 / -0.005; p4|mid +0.018 / +0.016; p4|p4 -0.036 / +0.018. Cross-tier covariance of opponents' deviations 0.0176 / 0.0175. Same-tier pairings are not matched: in the data the weakest low teams play part of their schedule outside D1, which the 56-game D1 schedule cannot.

## Diagnostics (CLAUDE.md watch items)

- Runs around the team-strength fit (scoreboard model without parks, as in team_talent_2025): within-game residual correlation 0.0496 (real 0.0734), dispersion 2.209 (real 2.6185); with the park term: 0.0076 (real 0.0377), 2.156 (real 2.5674).
- Strikeout leader 135.3 (seasons 116–181); real 2024-2026 leaders 191 / 180 / 169 in 57-72 team games.
- Qualified ERA: leader 1.41, #2 1.63, #5 1.95 (real 2024-2026 #2 2.01 / 1.97 / 1.98, #5 2.16 / 2.11 / 2.07).
- Reliever workloads (raw 56-game seasons; real 2024 / 2025 / 2026 national leaders in up to 72 games): most appearances 33.0 (real 38 / 37 / 39); 50th-most-used pitcher 26.7 (29 / 28 / 28); of the top 50 by appearances 1.1 have 60+ IP (6 / 5 / 12); most IP with 3 or fewer starts 70.1 (the top-50 appearance leaders' maximum: 102.2 / 74.0 / 92.0); relievers with 60+ IP 5.4; the IP leader is a reliever in 0 of 40 seasons.
- Elite run prevention (Phase 2 rows): best team ERA 3.01 (real 2024-2026 3.06–3.78), 50+ IP pitchers with ERA < 2.00 6.7 (5), < 3.00 52.9 (57), teams with ERA < 4.00 16.0 (2024-2026: 6 / 12 / 12).
