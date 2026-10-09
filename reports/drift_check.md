# Drift check on the calibrated maps

8 seasons of the current engine (seeds 970001-970008). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9765 ± 0.0177 | +1.0000 | -1.33 | ok |
| Strength map, offense: curvature | +0.0134 ± 0.0340 | +0.0000 | +0.39 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | -0.0058 ± 0.0058 | +0.0000 | -0.99 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0020 ± 0.0036 | +0.0000 | +0.54 | ok |
| Recovered minus drawn, offense, low (tier mean) | +0.0008 ± 0.0051 | +0.0000 | +0.15 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0202 ± 0.0126 | +1.0000 | +1.60 | ok |
| Strength map, run prevention: curvature | +0.0100 ± 0.0226 | +0.0000 | +0.44 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | +0.0040 ± 0.0062 | +0.0000 | +0.64 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | -0.0018 ± 0.0026 | +0.0000 | -0.71 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0003 ± 0.0058 | +0.0000 | +0.06 | ok |
| Home edge: fitted home log ratio | +0.0475 ± 0.0035 | +0.0438 | +0.33 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.50 (df 72) | 1 | max cell z 2.4, p 1.000 | ok |
