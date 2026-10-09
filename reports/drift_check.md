# Drift check on the calibrated maps

8 seasons of the current engine (seeds 970001-970008). Owner rule 2026-10-08: a row beyond 2 SE is re-solved in the same PR (strength map and home edge: scripts/solve_phase2_game_scale.py; pitch chain: scripts/solve_phase5_chain.py).

| Check | Value | Target | z | Flag |
|---|---|---|---|---|
| Strength map, offense: slope of recovered on drawn | +0.9874 ± 0.0145 | +1.0000 | -0.87 | ok |
| Strength map, offense: curvature | +0.0009 ± 0.0335 | +0.0000 | +0.03 | ok |
| Recovered minus drawn, offense, p4 (tier mean) | +0.0012 ± 0.0071 | +0.0000 | +0.16 | ok |
| Recovered minus drawn, offense, mid (tier mean) | +0.0002 ± 0.0025 | +0.0000 | +0.09 | ok |
| Recovered minus drawn, offense, low (tier mean) | -0.0012 ± 0.0045 | +0.0000 | -0.27 | ok |
| Strength map, run prevention: slope of recovered on drawn | +1.0049 ± 0.0109 | +1.0000 | +0.45 | ok |
| Strength map, run prevention: curvature | -0.0121 ± 0.0166 | +0.0000 | -0.73 | ok |
| Recovered minus drawn, run prevention, p4 (tier mean) | -0.0054 ± 0.0034 | +0.0000 | -1.58 | ok |
| Recovered minus drawn, run prevention, mid (tier mean) | +0.0014 ± 0.0023 | +0.0000 | +0.64 | ok |
| Recovered minus drawn, run prevention, low (tier mean) | +0.0014 ± 0.0040 | +0.0000 | +0.35 | ok |
| Home edge: fitted home log ratio | +0.0476 ± 0.0034 | +0.0438 | +0.34 | ok |
| Pitch chain: events by count against the data (chi-square / df, p) | 0.55 (df 72) | 1 | max cell z 2.3, p 0.999 | ok |
