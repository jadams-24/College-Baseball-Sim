# Drift check on the calibrated maps

16 seasons of the current engine (seeds 970001-970016). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9986 ± 0.0093 | +1.0000 | -0.15 | ok |
| Strength map, offense: curvature | +0.0193 ± 0.0227 | +0.0000 | +0.85 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | +0.0033 ± 0.0044 | +0.0000 | +0.75 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0032 ± 0.0026 | +0.0000 | +1.22 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0078 ± 0.0037 | +0.0000 | -2.10 | RE-SOLVE |
| Strength map, run prevention: slope of recovered on drawn | +1.0151 ± 0.0088 | +1.0000 | +1.72 | ok |
| Strength map, run prevention: curvature | +0.0468 ± 0.0145 | +0.0000 | +3.23 | RE-SOLVE |
| Recovered minus drawn, run prevention, p4 (tier mean) | +0.0049 ± 0.0054 | +0.0000 | +0.90 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | -0.0029 ± 0.0019 | +0.0000 | -1.52 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0014 ± 0.0025 | +0.0000 | +0.57 | ok |
| Home edge: fitted home log ratio | +0.0419 ± 0.0024 | +0.0438 | -0.17 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.47 (df 72) | 1 | max cell z 2.4, p 1.000 | ok |
