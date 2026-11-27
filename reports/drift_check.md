# Drift check on the calibrated maps

16 seasons of the current engine (seeds 970001-970016). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9920 ± 0.0115 | +1.0000 | -0.69 | ok |
| Strength map, offense: curvature | +0.0253 ± 0.0219 | +0.0000 | +1.16 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | -0.0009 ± 0.0033 | +0.0000 | -0.27 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0022 ± 0.0028 | +0.0000 | +0.78 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0031 ± 0.0050 | +0.0000 | -0.62 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0014 ± 0.0059 | +1.0000 | +0.24 | ok |
| Strength map, run prevention: curvature | -0.0064 ± 0.0197 | +0.0000 | -0.32 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0033 ± 0.0036 | +0.0000 | -0.93 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0018 ± 0.0021 | +0.0000 | +0.88 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | -0.0007 ± 0.0030 | +0.0000 | -0.24 | ok |
| Home edge: fitted home log ratio | +0.0449 ± 0.0024 | +0.0438 | +0.10 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.37 (df 72) | 1 | max cell z 2.1, p 1.000 | ok |
