# Drift check on the calibrated maps

16 seasons of the current engine (seeds 970001-970016). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +1.0061 ± 0.0064 | +1.0000 | +0.95 | ok |
| Strength map, offense: curvature | +0.0172 ± 0.0175 | +0.0000 | +0.98 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | +0.0037 ± 0.0040 | +0.0000 | +0.93 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0032 ± 0.0019 | +0.0000 | +1.65 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0080 ± 0.0023 | +0.0000 | -3.50 | RE-SOLVE |
| Strength map, run prevention: slope of recovered on drawn | +1.0235 ± 0.0056 | +1.0000 | +4.22 | RE-SOLVE |
| Strength map, run prevention: curvature | +0.0152 ± 0.0141 | +0.0000 | +1.08 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | +0.0036 ± 0.0042 | +0.0000 | +0.85 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0010 ± 0.0019 | +0.0000 | +0.53 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | -0.0042 ± 0.0021 | +0.0000 | -2.00 | ok |
| Home edge: fitted home log ratio | +0.0418 ± 0.0023 | +0.0438 | -0.18 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.55 (df 72) | 1 | max cell z 2.7, p 0.999 | ok |
