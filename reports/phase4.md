# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-01.
Ratings re-express the true rates the engine uses: 50 is the D1 average (PA- or BF-weighted), 10 points one true-talent SD, all of D1 on one scale. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip: ratings → 20 seasons → ratings estimated from the stats

Estimated from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results (engine/report4.py). The estimator is replicated in 10 folds of 2 seasons, each fitting its own priors; each statistic is the mean over folds, tolerance 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE). True ratings are measured from the simulated world's own D1 average, as the estimates are. Slope is the true rating regressed on the estimate (1 = calibrated). Bias is the mean of true − estimated. SD ratio is the residual SD over the posterior SD the estimator predicts (1 = sampling noise removed exactly, neither double-counted nor ignored). Reliability is the estimate regressed on the truth (the expected shrinkage; informational).

| Rating | Players per season | Slope | Status | Bias | Status | Resid SD / predicted | SD ratio | Status | Reliability |
|---|---|---|---|---|---|---|---|---|---|
| contact | 2311 | 0.963 ± 0.056 | pass | 0.10 ± 0.16 | pass | 7.13 / 7.29 | 0.978 ± 0.030 | pass | 0.42 |
| gap | 2150 | 0.990 ± 0.064 | pass | 0.04 ± 0.09 | pass | 7.65 / 7.60 | 1.007 ± 0.039 | pass | 0.42 |
| power | 2448 | 0.983 ± 0.025 | pass | -0.13 ± 0.12 | FAIL | 5.50 / 5.51 | 0.997 ± 0.025 | pass | 0.69 |
| eye | 2448 | 0.983 ± 0.019 | pass | 0.05 ± 0.05 | pass | 5.75 / 5.73 | 1.003 ± 0.006 | pass | 0.65 |
| avoid_k | 2448 | 1.005 ± 0.012 | pass | 0.03 ± 0.03 | FAIL | 4.24 / 4.23 | 1.003 ± 0.021 | pass | 0.80 |
| stuff | 2261 | 1.008 ± 0.014 | pass | 0.08 ± 0.04 | FAIL | 3.78 / 3.70 | 1.019 ± 0.029 | pass | 0.85 |
| control | 2261 | 0.991 ± 0.008 | FAIL | 0.17 ± 0.05 | FAIL | 4.78 / 4.77 | 1.003 ± 0.017 | pass | 0.77 |
| movement | 2261 | 0.962 ± 0.028 | FAIL | 0.33 ± 0.07 | FAIL | 7.79 / 7.72 | 1.010 ± 0.031 | pass | 0.39 |
| stamina | 3877 | 1.000 ± 0.010 | pass | -0.01 ± 0.09 | pass | 4.26 / 4.25 | 1.001 ± 0.014 | pass | 0.82 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 50.1 | 9.8 | 57.3 | 51.4 | 46.2 | pass |
| gap | 50.1 | 9.9 | 55.7 | 50.7 | 46.6 | pass |
| power | 50.2 | 9.8 | 57.5 | 50.4 | 44.4 | pass |
| eye | 50.1 | 9.9 | 54.7 | 50.0 | 46.0 | pass |
| avoid_k | 50.3 | 9.9 | 56.4 | 51.2 | 46.9 | pass |
| stuff | 50.4 | 9.9 | 60.1 | 51.7 | 45.1 | pass |
| control | 50.4 | 10.0 | 59.6 | 54.1 | 49.8 | pass |
| movement | 50.1 | 10.0 | 53.0 | 49.5 | 46.3 | pass |
| stamina | 52.0 | 10.0 | 50.4 | 49.9 | 50.2 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): G. Brebrord | Groson Sailors (p4) | regular | Contact 64, Gap 68, Power 74, Eye 68, Avoid K 46, Speed — | 56 G, 284 PA, 0.345/0.475/0.861, 32 HR, 15.5% BB, 22.9% K |
| Median mid-major regular: N. Fegawell | Trolt Coyotes (mid) | regular | Contact 62, Gap 49, Power 54, Eye 44, Avoid K 53, Speed — | 51 G, 231 PA, 0.284/0.368/0.457, 7 HR, 9.5% BB, 18.2% K |
| Median low-tier regular: ST. Seaford | Storeang Rangers (low) | regular | Contact 53, Gap 41, Power 49, Eye 47, Avoid K 54, Speed — | 50 G, 234 PA, 0.313/0.403/0.379, 1 HR, 12.0% BB, 14.1% K |
| Home-run leader: G. Grastason | Meton Voyagers (mid) | regular | Contact 47, Gap 80, Power 78, Eye 54, Avoid K 39, Speed — | 56 G, 285 PA, 0.329/0.449/0.851, 33 HR, 11.9% BB, 24.2% K |
| Highest true Contact, qualified: K. Zuns | Huthoux Cardinals (p4) | regular | Contact 80, Gap 57, Power 79, Eye 52, Avoid K 40, Speed — | 55 G, 282 PA, 0.318/0.421/0.674, 24 HR, 13.1% BB, 30.1% K |
| Bench player with most PA: T. Fas | Peaciton Falcons (mid) | bench | Contact 43, Gap 44, Power 43, Eye 66, Avoid K 53, Speed — | 33 G, 141 PA, 0.265/0.453/0.333, 0 HR, 23.4% BB, 12.8% K |
| Best P4 weekend starter (ERA, qualified): H. Lomut | Mazyng Lynx (p4) | sp_weekend | Stuff 73, Control 69, Movement 40, Stamina 52 | 13 G, 13 GS, 75.2 IP, 1.55 ERA, 11.3 K/9, 1.2 BB/9, 0.8 HR/9 |
| Median mid-major weekend starter: BR. Cusouton | Dulys Ospreys (mid) | sp_weekend | Stuff 46, Control 59, Movement 57, Stamina 53 | 13 G, 13 GS, 61.0 IP, 4.72 ERA, 6.2 K/9, 2.2 BB/9, 0.6 HR/9 |
| Low-tier reliever with most innings: V. Staiwood | Shuford Mariners (low) | rp | Stuff 50, Control 44, Movement 47, Stamina 72 | 41 G, 3 GS, 99.1 IP, 3.81 ERA, 8.2 K/9, 4.3 BB/9, 0.6 HR/9 |
| Starter with the highest true Stamina: S. Zaisaiton | Kuton Sailors (low) | sp_weekend | Stuff 41, Control 45, Movement 37, Stamina 78 | 8 G, 8 GS, 45.1 IP, 8.34 ERA, 5.6 K/9, 4.0 BB/9, 1.2 HR/9 |
