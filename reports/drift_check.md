# Drift check on the calibrated maps

8 seasons of the current engine (seeds 970001-970008). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9872 ± 0.0147 | +1.0000 | -0.87 | ok |
| Strength map, offense: curvature | +0.0013 ± 0.0335 | +0.0000 | +0.04 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | +0.0010 ± 0.0072 | +0.0000 | +0.14 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0002 ± 0.0025 | +0.0000 | +0.07 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0010 ± 0.0043 | +0.0000 | -0.24 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0047 ± 0.0108 | +1.0000 | +0.43 | ok |
| Strength map, run prevention: curvature | -0.0101 ± 0.0175 | +0.0000 | -0.58 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0055 ± 0.0035 | +0.0000 | -1.58 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0014 ± 0.0023 | +0.0000 | +0.60 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0016 ± 0.0040 | +0.0000 | +0.40 | ok |
| Home edge: fitted home log ratio | +0.0478 ± 0.0035 | +0.0438 | +0.35 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.55 (df 72) | 1 | max cell z 2.3, p 0.999 | ok |
