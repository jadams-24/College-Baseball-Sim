# Drift check on the calibrated maps

16 seasons of the current engine (seeds 970001-970016). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +1.0006 ± 0.0062 | +1.0000 | +0.10 | ok |
| Strength map, offense: curvature | -0.0161 ± 0.0242 | +0.0000 | -0.66 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | +0.0015 ± 0.0036 | +0.0000 | +0.40 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0041 ± 0.0025 | +0.0000 | +1.63 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0079 ± 0.0029 | +0.0000 | -2.77 | RE-SOLVE |
| Strength map, run prevention: slope of recovered on drawn | +1.0054 ± 0.0077 | +1.0000 | +0.70 | ok |
| Strength map, run prevention: curvature | +0.0174 ± 0.0179 | +0.0000 | +0.97 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0015 ± 0.0041 | +0.0000 | -0.36 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0002 ± 0.0022 | +0.0000 | +0.11 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0006 ± 0.0031 | +0.0000 | +0.20 | ok |
| Home edge: fitted home log ratio | +0.0393 ± 0.0028 | +0.0438 | -0.41 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.44 (df 72) | 1 | max cell z 2.5, p 1.000 | ok |
