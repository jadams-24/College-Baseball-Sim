# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-01.
Ratings re-express the true rates the engine uses: 50 is the D1 average (PA- or BF-weighted), 10 points one true-talent SD, all of D1 on one scale. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2311 | +0.0013 ± 0.0016 | +0.10 | pass | 1.002 ± 0.020 | pass | 1.016 ± 0.029 | pass |
| gap | XBH share of hits | 2150 | -0.0020 ± 0.0053 | -0.08 | pass | 1.004 ± 0.035 | pass | 1.002 ± 0.031 | pass |
| power | HR/PA | 2449 | +0.0018 ± 0.0061 | +0.03 | pass | 1.004 ± 0.012 | pass | 1.000 ± 0.023 | pass |
| eye | BB/PA | 2449 | +0.0013 ± 0.0040 | +0.04 | pass | 0.994 ± 0.008 | pass | 1.003 ± 0.029 | pass |
| avoid_k | K/PA | 2449 | +0.0001 ± 0.0042 | +0.00 | pass | 1.003 ± 0.008 | pass | 0.998 ± 0.025 | pass |
| stuff | K/BF | 2262 | -0.0007 ± 0.0032 | -0.02 | pass | 0.997 ± 0.007 | pass | 1.000 ± 0.022 | pass |
| control | BB/BF | 2262 | +0.0009 ± 0.0032 | +0.02 | pass | 1.000 ± 0.009 | pass | 1.002 ± 0.029 | pass |
| movement | HR/BF | 2262 | -0.0023 ± 0.0063 | -0.07 | pass | 0.991 ± 0.021 | pass | 1.005 ± 0.021 | pass |
| stamina | pull hazard (log leash) | 3878 | -0.0011 ± 0.0040 | — | pass | 0.999 ± 0.008 | pass | 1.006 ± 0.029 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0002 / 1.007 / 1.013 | -0.0019 / 0.981 / 1.007 | +0.0051 † / 0.999 / 1.026 |
| gap | plate appearances | -0.0008 / 0.979 / 0.997 | -0.0033 / 0.996 / 1.014 | -0.0017 / 1.025 / 0.995 |
| power | plate appearances | -0.0034 / 1.011 / 0.991 | -0.0012 / 0.990 / 1.008 | +0.0055 / 1.003 / 0.999 |
| eye | plate appearances | +0.0016 / 0.999 / 0.995 | -0.0007 / 0.998 / 1.012 | +0.0027 / 0.988 / 1.002 |
| avoid_k | plate appearances | +0.0029 / 1.003 / 1.001 | +0.0006 / 1.006 / 1.000 | -0.0022 / 0.999 / 0.995 |
| stuff | batters faced | +0.0009 / 1.000 / 0.986 | -0.0016 / 0.994 / 1.009 | -0.0008 / 0.998 / 1.000 |
| control | batters faced | +0.0004 / 1.000 / 0.983 | -0.0010 / 1.004 / 1.010 | +0.0027 / 0.999 / 1.008 |
| movement | batters faced | +0.0020 / 0.985 / 0.992 | -0.0018 / 0.990 / 1.021 | -0.0051 / 0.996 / 1.001 |
| stamina | appearances | +0.0003 / 1.005 / 1.010 | -0.0011 / 0.996 / 1.016 | -0.0014 / 0.999 / 0.999 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 1.003 | 1.025 |
| gap | 1.003 | 1.011 |
| power | 1.004 | 1.022 |
| eye | 1.005 | 1.028 |
| avoid_k | 0.994 | 1.028 |
| stuff | 0.988 | 1.056 |
| control | 1.001 | 1.018 |
| movement | 0.994 | 1.014 |

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

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2311 | 0.963 ± 0.056 | 0.10 ± 0.16 | 7.13 / 7.29 | 0.978 ± 0.030 | 0.42 |
| gap | 2150 | 0.990 ± 0.064 | 0.04 ± 0.09 | 7.65 / 7.60 | 1.007 ± 0.039 | 0.42 |
| power | 2448 | 0.983 ± 0.025 | -0.13 ± 0.12 | 5.50 / 5.51 | 0.997 ± 0.025 | 0.69 |
| eye | 2448 | 0.983 ± 0.019 | 0.05 ± 0.05 | 5.75 / 5.73 | 1.003 ± 0.006 | 0.65 |
| avoid_k | 2448 | 1.005 ± 0.012 | 0.03 ± 0.03 | 4.24 / 4.23 | 1.003 ± 0.021 | 0.80 |
| stuff | 2261 | 1.008 ± 0.014 | 0.08 ± 0.04 | 3.78 / 3.70 | 1.019 ± 0.029 | 0.85 |
| control | 2261 | 0.991 ± 0.008 | 0.17 ± 0.05 | 4.78 / 4.77 | 1.003 ± 0.017 | 0.77 |
| movement | 2261 | 0.962 ± 0.028 | 0.33 ± 0.07 | 7.79 / 7.72 | 1.010 ± 0.031 | 0.39 |
| stamina | 3877 | 1.000 ± 0.010 | -0.01 ± 0.09 | 4.26 / 4.25 | 1.001 ± 0.014 | 0.82 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

