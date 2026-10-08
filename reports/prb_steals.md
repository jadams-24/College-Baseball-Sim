# Steals by count (PR B)

Fit: 56,975 plate appearances that begin with a lead runner able to steal, 4,808 attempts (4,120 stolen; 389 on the last pitch, position known), 166,423 eligible pitches; EM 24 iterations. Two outs: the attempt odds are scaled by 1.256 and the success level set to the direct rate 0.799 for the inning-ending caught stealing that has no plate appearance.

| Count | Attempt per pitch (reference state) | SE (logit) | Success (reference state) | SE (logit) |
|---|---|---|---|---|
| 0-0 | 0.0333 | 0.208 | 0.819 | 0.144 |
| 0-1 | 0.0612 | 0.209 | 0.759 | 0.150 |
| 0-2 | 0.0424 | 0.215 | 0.755 | 0.191 |
| 1-0 | 0.0395 | 0.210 | 0.828 | 0.166 |
| 1-1 | 0.0560 | 0.210 | 0.760 | 0.159 |
| 1-2 | 0.0513 | 0.212 | 0.733 | 0.170 |
| 2-0 | 0.0417 | 0.216 | 0.784 | 0.201 |
| 2-1 | 0.0578 | 0.214 | 0.769 | 0.180 |
| 2-2 | 0.0531 | 0.214 | 0.790 | 0.183 |
| 3-0 | 0.0052 | 0.319 | 0.775 | 0.334 |
| 3-1 | 0.0095 | 0.274 | 0.796 | 0.314 |
| 3-2 | 0.0643 | 0.217 | 0.745 | 0.179 |

Reference state: no outs, steal of second, score within one run, innings 1-3.

| Covariate | Attempt (logit) | SE | Success (logit) | SE |
|---|---|---|---|---|
| outs_1 | +0.390 | 0.039 | -0.128 | 0.093 |
| outs_2 | +0.424 | 0.040 | +0.067 | 0.049 |
| steal_third | -1.594 | 0.043 | +0.250 | 0.127 |
| lead_-99_-4 | -1.125 | 0.064 | — | — |
| lead_-3_-2 | -0.669 | 0.058 | — | — |
| lead_2_3 | +0.182 | 0.042 | — | — |
| lead_4_99 | +0.064 | 0.040 | — | — |
| inning_4_6 | -0.009 | 0.036 | — | — |
| inning_7_8 | -0.097 | 0.043 | — | — |
| inning_9_99 | -0.370 | 0.071 | — | — |

Out of sample: fitted on 80% of the games, predicting the other 436 games (11,206 eligible plate appearances).

| Plate appearance length (pitches) | Plate appearances | Attempts observed | Predicted |
|---|---|---|---|
| 1.0 | 2 | 1 | 0.0 |
| 2.0 | 1762 | 40 | 40.1 |
| 3.0 | 2320 | 109 | 123.9 |
| 4.0 | 2406 | 160 | 194.0 |
| 5.0 | 2226 | 234 | 238.4 |
| 6.0 | 1571 | 243 | 207.0 |
| 7.0 | 602 | 116 | 81.5 |
| 8+ | 317 | 66 | 47.3 |

Chi-square 65.6 on 8 cells (p 0.000).

| Final count | Plate appearances | Attempts observed | Predicted | Last-pitch attempts observed | Predicted |
|---|---|---|---|---|---|
| 0-0 | 2 | 1 | 0.0 | 0 | 0.0 |
| 0-1 | 843 | 17 | 18.7 | 0 | 0.0 |
| 0-2 | 1138 | 55 | 64.8 | 12 | 14.5 |
| 1-0 | 938 | 31 | 21.8 | 0 | 0.0 |
| 1-1 | 998 | 39 | 50.9 | 0 | 0.0 |
| 1-2 | 1817 | 133 | 151.2 | 12 | 25.6 |
| 2-0 | 361 | 23 | 18.6 | 0 | 0.0 |
| 2-1 | 613 | 49 | 48.0 | 0 | 0.0 |
| 2-2 | 1589 | 201 | 185.4 | 11 | 21.9 |
| 3-0 | 305 | 22 | 24.8 | 0 | 1.1 |
| 3-1 | 809 | 99 | 86.0 | 1 | 3.1 |
| 3-2 | 1793 | 299 | 261.8 | 42 | 39.8 |

By final count: chi-square 49.9 on 12 cells (p 0.000); last-pitch attempts by count: 15.7 on 7 cells (p 0.028).
