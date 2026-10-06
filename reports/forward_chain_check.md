# Forward pitch-by-pitch play against outcome-first (engine restructure)

10000 matchups from a generated league (seed 7), 500 plate appearances each by both methods (5,000,000 per method). Old: outcome drawn first, reached-on-error tilt, then the sequence from the chain conditioned on the outcome. New: the transformed chain played forward one pitch at a time. See `scripts/check_forward_chain.py` and `engine/pitch.py`.

Exact (no sampling): the forward chain's outcome law equals the matchup's to 4.4e-16 (largest absolute difference over every matchup and outcome).

| Two-sample comparison | Chi-square (or z) | df (or tests) | p |
|---|---|---|---|
| PA outcome | 7.5 | 8 | 0.4801 |
| Count the PA ended at | 16.9 | 11 | 0.1104 |
| Pitches per PA | 15.4 | 11 | 0.1645 |
| Pitch events by count | 75.7 | 83 | 0.7029 |
| Outcome x pitches | 114.8 | 102 | 0.1814 |
| Counts reached (largest of 12 two-proportion z; Bonferroni p) | 1.83 | 12 | 0.8119 |

| Against the exact law, matchup by matchup (outcome counts) | Chi-square | df | p |
|---|---|---|---|
| old | 79915.7 | 79995 | 0.5779 |
| new | 79493.4 | 79995 | 0.8953 |

Pitches per PA: old 3.8620, new 3.8623.

| Outcome | Old | New |
|---|---|---|
| K | 0.20532 | 0.20536 |
| BB | 0.11753 | 0.11753 |
| HBP | 0.03882 | 0.03888 |
| HR | 0.02287 | 0.02290 |
| 1B | 0.15239 | 0.15259 |
| 2B | 0.04189 | 0.04188 |
| 3B | 0.00421 | 0.00415 |
| ROE | 0.01429 | 0.01415 |
| OUT | 0.40267 | 0.40257 |

A p-value is the chance of a difference at least this large if the two methods draw from the same distribution; small values on several rows would mean they differ.
