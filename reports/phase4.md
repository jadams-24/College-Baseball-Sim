# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-10.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: batters config.phase4.MIN_TRIALS (150 PA, 100 balls in play for Contact, 35 hits for Gap); pitchers every pitcher-season with any batters faced (Stuff, Control, Movement) or any appearance (Stamina), owner decision 2026-10-09: relief usage reacts to results (bullpen form), so a threshold on realized workload keeps the pitchers whose results earned them more work and biases the intercept (PHASE0_NOTES, Variance fix #1). With every trial counted the intercept is 0 under any usage rule. The threshold version is reported below. Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2161 | +0.0011 ± 0.0021 | +0.08 | pass | 0.989 ± 0.023 | pass | 1.009 ± 0.014 | pass |
| gap | XBH share of hits | 1991 | +0.0008 ± 0.0044 | +0.03 | pass | 1.001 ± 0.020 | pass | 1.013 ± 0.014 | pass |
| power | HR/PA | 2332 | -0.0003 ± 0.0048 | -0.00 | pass | 1.001 ± 0.012 | pass | 1.002 ± 0.022 | pass |
| eye | BB/PA | 2332 | -0.0002 ± 0.0021 | -0.01 | pass | 1.003 ± 0.010 | pass | 0.994 ± 0.015 | pass |
| avoid_k | K/PA | 2332 | -0.0008 ± 0.0027 | -0.02 | pass | 1.001 ± 0.005 | pass | 1.001 ± 0.018 | pass |
| stuff | K/BF | 5518 | -0.0003 ± 0.0021 | -0.01 | pass | 1.001 ± 0.006 | pass | 0.997 ± 0.012 | pass |
| control | BB/BF | 5518 | -0.0003 ± 0.0019 | -0.01 | pass | 1.005 ± 0.005 | FAIL | 1.000 ± 0.014 | pass |
| movement | HR/BF | 5518 | -0.0024 ± 0.0041 | -0.08 | pass | 1.001 ± 0.014 | pass | 0.997 ± 0.013 | pass |
| stamina | pull hazard (log leash) | 5517 | -0.0005 ± 0.0022 | — | pass | 1.000 ± 0.005 | pass | 0.997 ± 0.011 | pass |

### Pitchers at the old threshold, 150 batters faced / 8 appearances (reported, not gated)

The same regression on pitchers who reach the workload threshold. With relief usage reacting to results, this sample is selected on luck.

| Rating | Player-seasons per season | Intercept (logit) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|
| stuff | 1528 | +0.0005 ± 0.0024 | pass | 1.001 ± 0.008 | pass | 1.000 ± 0.014 | pass |
| control | 1528 | -0.0030 ± 0.0035 | pass | 1.003 ± 0.009 | pass | 0.992 ± 0.020 | pass |
| movement | 1528 | -0.0107 ± 0.0058 | outside | 1.007 ± 0.018 | pass | 0.988 ± 0.022 | pass |
| stamina | 4362 | +0.0033 ± 0.0022 | outside | 0.998 ± 0.005 | pass | 0.995 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py). Two usage rules depend on outcomes: the in-game pull hazard (outing pitch count and runs) and, from 2026-10-09, the relief choice's recent form (runs allowed in the last outing and the three before). So a pitcher's workload carries part of his luck, and the thirds (cut on qualified pitchers) are selected on it. Stamina is split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0025 / 0.990 / 1.013 | +0.0011 / 0.987 / 1.020 | +0.0036 / 0.973 / 0.998 |
| gap | plate appearances | -0.0007 / 1.005 / 1.009 | +0.0002 / 1.012 / 0.995 | +0.0024 / 0.985 / 1.030 † |
| power | plate appearances | -0.0031 / 0.997 / 1.001 | -0.0020 / 1.003 / 1.011 | +0.0021 / 1.000 / 0.996 |
| eye | plate appearances | -0.0018 / 1.006 / 0.991 | -0.0029 / 1.000 / 0.987 | +0.0031 / 1.002 / 1.001 |
| avoid_k | plate appearances | +0.0020 / 1.000 / 1.001 | +0.0005 / 1.003 / 1.004 | -0.0039 † / 0.997 / 0.997 |
| stuff | batters faced | +0.0014 / 1.006 / 0.997 | +0.0013 / 1.003 / 1.007 | -0.0004 / 0.997 / 0.996 |
| control | batters faced | -0.0017 / 1.002 / 1.003 | +0.0016 / 0.992 / 0.990 | -0.0075 † / 1.007 / 0.988 |
| movement | batters faced | -0.0194 † / 1.017 / 0.981 | -0.0047 / 1.003 / 1.001 | -0.0106 † / 0.997 / 0.982 |
| stamina | appearances | -0.0145 † / 1.005 / 1.007 | -0.0074 † / 0.996 / 0.993 | +0.0182 † / 0.990 † / 0.990 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.922 | 1.056 |
| gap | 0.976 | 1.035 |
| power | 0.920 | 1.203 |
| eye | 1.033 | 1.280 |
| avoid_k | 0.983 | 1.194 |
| stuff | 1.004 | 1.198 |
| control | 1.006 | 1.040 |
| movement | 1.001 | 1.108 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.4 | 9.8 | 57.4 | 51.2 | 46.1 | pass |
| gap | 49.5 | 9.8 | 55.6 | 50.7 | 46.5 | pass |
| power | 49.5 | 9.7 | 57.1 | 49.5 | 44.1 | pass |
| eye | 49.9 | 9.9 | 54.8 | 49.9 | 45.8 | pass |
| avoid_k | 49.7 | 9.9 | 56.3 | 50.9 | 46.6 | pass |
| stuff | 50.0 | 9.9 | 58.9 | 51.0 | 45.3 | pass |
| control | 50.6 | 9.8 | 58.3 | 53.5 | 49.7 | pass |
| movement | 50.0 | 9.5 | 52.4 | 49.2 | 46.7 | pass |
| stamina | 51.5 | 9.9 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): V. Rait | Woceberg Kestrels (p4) | regular | Contact 59, Gap 67, Power 68, Eye 59, Avoid K 55, Speed 54 | 41 G, 183 PA, 0.389/0.466/0.805, 14 HR, 11.5% BB, 18.6% K |
| Median mid-major regular: V. Neafield | Putrom Rangers (mid) | regular | Contact 52, Gap 31, Power 37, Eye 48, Avoid K 60, Speed 57 | 43 G, 186 PA, 0.326/0.462/0.361, 0 HR, 11.3% BB, 14.0% K |
| Median low-tier regular: N. Meas | Grafield Ironmen (low) | regular | Contact 56, Gap 42, Power 37, Eye 45, Avoid K 53, Speed 49 | 33 G, 122 PA, 0.336/0.393/0.418, 0 HR, 4.1% BB, 11.5% K |
| Home-run leader: D. Jon | Kax Wolves (p4) | regular | Contact 48, Gap 69, Power 69, Eye 48, Avoid K 60, Speed 49 | 55 G, 249 PA, 0.293/0.343/0.747, 30 HR, 4.4% BB, 21.3% K |
| Highest true Contact, qualified: CL. Grygrom | Tuley Kestrels (p4) | regular | Contact 80, Gap 52, Power 78, Eye 56, Avoid K 54, Speed 32 | 48 G, 220 PA, 0.350/0.418/0.609, 13 HR, 9.5% BB, 25.0% K |
| Bench player with most PA: V. Lushock | Jounywood Rangers (low) | bench | Contact 32, Gap 33, Power 39, Eye 40, Avoid K 49, Speed 37 | 35 G, 137 PA, 0.313/0.397/0.365, 1 HR, 10.9% BB, 12.4% K |
| Best P4 weekend starter (ERA, qualified): CL. Zitraifield | Gromison Stags (p4) | sp_weekend | Stuff 79, Control 66, Movement 63, Stamina 52 | 15 G, 14 GS, 75.1 IP, 1.43 ERA, 12.5 K/9, 2.5 BB/9, 0.2 HR/9 |
| Median mid-major weekend starter: TR. Fos | Fyshafield Cardinals (mid) | sp_weekend | Stuff 66, Control 56, Movement 57, Stamina 44 | 14 G, 14 GS, 60.2 IP, 5.19 ERA, 11.0 K/9, 2.4 BB/9, 1.2 HR/9 |
| Low-tier reliever with most innings: L. Shot | Clack Clippers (low) | rp | Stuff 61, Control 51, Movement 57, Stamina 77 | 18 G, 2 GS, 59.1 IP, 2.58 ERA, 10.2 K/9, 3.2 BB/9, 0.5 HR/9 |
| Starter with the highest true Stamina: T. Giton | Rarous Rapids (low) | sp_weekend | Stuff 58, Control 59, Movement 57, Stamina 79 | 12 G, 10 GS, 69.2 IP, 4.52 ERA, 11.1 K/9, 3.9 BB/9, 0.8 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2161 | 1.046 ± 0.043 | 0.15 ± 0.07 | 7.33 / 6.98 | 1.052 ± 0.033 | 0.35 |
| gap | 1991 | 1.029 ± 0.032 | -0.41 ± 0.07 | 7.82 / 7.56 | 1.035 ± 0.022 | 0.38 |
| power | 2331 | 1.047 ± 0.026 | 0.25 ± 0.05 | 6.24 / 5.32 | 1.172 ± 0.020 | 0.59 |
| eye | 2331 | 0.849 ± 0.010 | 0.21 ± 0.04 | 6.28 / 6.08 | 1.034 ± 0.008 | 0.70 |
| avoid_k | 2331 | 0.975 ± 0.008 | 0.02 ± 0.03 | 4.71 / 4.44 | 1.061 ± 0.008 | 0.78 |
| stuff | 1528 | 0.959 ± 0.010 | 0.24 ± 0.05 | 4.03 / 3.71 | 1.087 ± 0.022 | 0.87 |
| control | 1528 | 0.953 ± 0.012 | 0.21 ± 0.06 | 4.99 / 4.89 | 1.021 ± 0.011 | 0.73 |
| movement | 1528 | 0.786 ± 0.023 | 0.93 ± 0.07 | 7.89 / 8.42 | 0.938 ± 0.013 | 0.45 |
| stamina | 4361 | 1.002 ± 0.007 | 0.00 ± 0.05 | 4.73 / 4.73 | 1.000 ± 0.009 | 0.77 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

