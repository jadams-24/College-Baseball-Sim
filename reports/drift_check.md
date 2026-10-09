# Drift check on the calibrated maps

8 seasons of the current engine (seeds 970001-970008). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9844 ± 0.0184 | +1.0000 | -0.85 | ok |
| Strength map, offense: curvature | +0.0329 ± 0.0385 | +0.0000 | +0.86 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | -0.0023 ± 0.0086 | +0.0000 | -0.27 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0002 ± 0.0038 | +0.0000 | +0.06 | ok |
| Recovered minus drawn, offense, low (tier mean) | +0.0013 ± 0.0047 | +0.0000 | +0.27 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0009 ± 0.0092 | +1.0000 | +0.10 | ok |
| Strength map, run prevention: curvature | -0.0236 ± 0.0167 | +0.0000 | -1.41 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0101 ± 0.0042 | +0.0000 | -2.40 | RE-SOLVE |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0026 ± 0.0032 | +0.0000 | +0.82 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0027 ± 0.0049 | +0.0000 | +0.56 | ok |
| Home edge: fitted home log ratio | +0.0451 ± 0.0035 | +0.0438 | +0.12 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.76 (df 72) | 1 | max cell z 2.8, p 0.932 | ok |
