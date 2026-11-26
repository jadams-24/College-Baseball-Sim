# Drift check on the calibrated maps

16 seasons of the current engine (seeds 970001-970016). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9809 ± 0.0115 | +1.0000 | -1.67 | ok |
| Strength map, offense: curvature | +0.0310 ± 0.0211 | +0.0000 | +1.46 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | -0.0019 ± 0.0047 | +0.0000 | -0.40 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0015 ± 0.0025 | +0.0000 | +0.63 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0013 ± 0.0036 | +0.0000 | -0.35 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0120 ± 0.0064 | +1.0000 | +1.87 | ok |
| Strength map, run prevention: curvature | +0.0254 ± 0.0184 | +0.0000 | +1.38 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0028 ± 0.0038 | +0.0000 | -0.74 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | -0.0007 ± 0.0021 | +0.0000 | -0.34 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0032 ± 0.0028 | +0.0000 | +1.16 | ok |
| Home edge: fitted home log ratio | +0.0442 ± 0.0025 | +0.0438 | +0.04 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.39 (df 72) | 1 | max cell z 2.0, p 1.000 | ok |
