# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-10.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: batters config.phase4.MIN_TRIALS (150 PA, 100 balls in play for Contact, 35 hits for Gap); pitchers every pitcher-season with any batters faced (Stuff, Control, Movement) or any appearance (Stamina), owner decision 2026-10-09: relief usage reacts to results (bullpen form), so a threshold on realized workload keeps the pitchers whose results earned them more work and biases the intercept (PHASE0_NOTES, Variance fix #1). With every trial counted the intercept is 0 under any usage rule. The threshold version is reported below. Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2153 | +0.0000 ± 0.0027 | +0.00 | pass | 1.002 ± 0.021 | pass | 0.992 ± 0.019 | pass |
| gap | XBH share of hits | 1993 | +0.0015 ± 0.0051 | +0.06 | pass | 0.994 ± 0.016 | pass | 1.002 ± 0.018 | pass |
| power | HR/PA | 2331 | -0.0011 ± 0.0052 | -0.02 | pass | 0.995 ± 0.008 | pass | 1.001 ± 0.016 | pass |
| eye | BB/PA | 2331 | +0.0003 ± 0.0018 | +0.01 | pass | 1.000 ± 0.011 | pass | 1.002 ± 0.016 | pass |
| avoid_k | K/PA | 2331 | +0.0001 ± 0.0021 | +0.00 | pass | 1.001 ± 0.008 | pass | 0.994 ± 0.017 | pass |
| stuff | K/BF | 5518 | -0.0001 ± 0.0015 | -0.00 | pass | 1.000 ± 0.004 | pass | 0.999 ± 0.012 | pass |
| control | BB/BF | 5518 | +0.0001 ± 0.0019 | +0.00 | pass | 0.998 ± 0.004 | pass | 0.989 ± 0.013 | pass |
| movement | HR/BF | 5518 | -0.0011 ± 0.0047 | -0.03 | pass | 1.002 ± 0.012 | pass | 1.001 ± 0.012 | pass |
| stamina | pull hazard (log leash) | 5517 | +0.0004 ± 0.0024 | — | pass | 1.000 ± 0.004 | pass | 1.000 ± 0.010 | pass |

### Pitchers at the old threshold, 150 batters faced / 8 appearances (reported, not gated)

The same regression on pitchers who reach the workload threshold. With relief usage reacting to results, this sample is selected on luck.

| Rating | Player-seasons per season | Intercept (logit) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|
| stuff | 1532 | +0.0010 ± 0.0023 | pass | 0.999 ± 0.005 | pass | 0.998 ± 0.020 | pass |
| control | 1532 | -0.0012 ± 0.0030 | pass | 0.999 ± 0.009 | pass | 0.985 ± 0.023 | pass |
| movement | 1532 | -0.0096 ± 0.0054 | outside | 1.001 ± 0.014 | pass | 0.994 ± 0.020 | pass |
| stamina | 4357 | +0.0042 ± 0.0023 | outside | 0.999 ± 0.004 | pass | 1.000 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py). Two usage rules depend on outcomes: the in-game pull hazard (outing pitch count and runs) and, from 2026-10-09, the relief choice's recent form (runs allowed in the last outing and the three before). So a pitcher's workload carries part of his luck, and the thirds (cut on qualified pitchers) are selected on it. Stamina is split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0015 / 1.006 / 1.004 | -0.0014 / 0.991 / 0.986 | +0.0024 / 1.000 / 0.987 |
| gap | plate appearances | -0.0010 / 1.003 / 0.993 | +0.0005 / 0.991 / 1.000 | +0.0040 / 0.983 / 1.010 |
| power | plate appearances | +0.0006 / 0.987 / 0.992 | -0.0045 / 0.995 / 0.990 | +0.0004 / 0.999 / 1.012 |
| eye | plate appearances | -0.0017 / 0.996 / 1.010 | +0.0016 / 1.003 / 1.006 | +0.0006 / 1.001 / 0.993 |
| avoid_k | plate appearances | +0.0023 / 1.004 / 1.001 | -0.0014 / 0.996 / 0.997 | -0.0003 / 1.002 / 0.986 |
| stuff | batters faced | +0.0014 / 0.997 / 1.000 | +0.0016 / 1.004 / 0.997 | +0.0005 / 0.998 / 0.998 |
| control | batters faced | -0.0002 / 1.001 / 0.985 | +0.0023 / 0.993 / 1.001 | -0.0045 † / 0.998 / 0.972 |
| movement | batters faced | -0.0180 † / 1.017 / 0.987 | -0.0060 / 0.992 / 0.998 | -0.0078 † / 0.994 / 0.994 |
| stamina | appearances | -0.0143 † / 1.005 / 0.998 | -0.0073 † / 0.997 / 0.998 | +0.0199 † / 0.990 † / 1.003 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.938 | 1.036 |
| gap | 0.968 | 1.027 |
| power | 0.917 | 1.206 |
| eye | 1.027 | 1.289 |
| avoid_k | 0.985 | 1.183 |
| stuff | 1.004 | 1.197 |
| control | 0.997 | 1.028 |
| movement | 1.006 | 1.109 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.7 | 57.4 | 51.3 | 46.3 | pass |
| gap | 49.6 | 9.8 | 55.6 | 50.7 | 46.8 | pass |
| power | 49.5 | 9.6 | 56.9 | 49.5 | 44.3 | pass |
| eye | 49.9 | 9.8 | 54.7 | 49.9 | 46.0 | pass |
| avoid_k | 49.8 | 9.9 | 56.2 | 51.0 | 46.7 | pass |
| stuff | 50.1 | 9.8 | 58.9 | 51.2 | 45.5 | pass |
| control | 50.6 | 9.8 | 58.5 | 53.4 | 49.8 | pass |
| movement | 50.1 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.5 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): P. Poton | Kamut Clippers (p4) | regular | Contact 74, Gap 71, Power 76, Eye 66, Avoid K 58, Speed 47 | 52 G, 252 PA, 0.411/0.492/0.826, 21 HR, 13.9% BB, 15.5% K |
| Median mid-major regular: P. Deam | Gryrd Bison (mid) | regular | Contact 44, Gap 50, Power 47, Eye 39, Avoid K 50, Speed 46 | 36 G, 143 PA, 0.303/0.390/0.434, 3 HR, 4.9% BB, 24.5% K |
| Median low-tier regular: TH. Heason | Vogeawood Falcons (low) | regular | Contact 48, Gap 40, Power 41, Eye 30, Avoid K 42, Speed 41 | 39 G, 160 PA, 0.293/0.384/0.429, 4 HR, 7.5% BB, 16.9% K |
| Home-run leader: G. Vealey | Saiberg Lynx (mid) | regular | Contact 60, Gap 75, Power 70, Eye 55, Avoid K 50, Speed 72 | 54 G, 273 PA, 0.431/0.515/0.978, 33 HR, 11.4% BB, 16.5% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 73, Eye 60, Avoid K 58, Speed 64 | 52 G, 258 PA, 0.359/0.455/0.728, 20 HR, 14.7% BB, 20.2% K |
| Bench player with most PA: Z. Seanaiwood | Sugoufield Monarchs (p4) | bench | Contact 46, Gap 51, Power 54, Eye 59, Avoid K 54, Speed 80 | 35 G, 130 PA, 0.202/0.297/0.303, 3 HR, 9.2% BB, 22.3% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 14 G, 13 GS, 74.0 IP, 1.70 ERA, 16.9 K/9, 3.5 BB/9, 0.6 HR/9 |
| Median mid-major weekend starter: BR. Moduson | Meashur Lynx (mid) | sp_weekend | Stuff 60, Control 64, Movement 55, Stamina 58 | 13 G, 13 GS, 64.2 IP, 5.29 ERA, 10.0 K/9, 2.2 BB/9, 1.1 HR/9 |
| Low-tier reliever with most innings: M. Weson | Hohaberg Ironmen (low) | rp | Stuff 45, Control 44, Movement 50, Stamina 56 | 25 G, 4 GS, 59.1 IP, 5.76 ERA, 7.6 K/9, 5.0 BB/9, 1.1 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 14 G, 11 GS, 82.1 IP, 5.68 ERA, 10.2 K/9, 2.5 BB/9, 1.3 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2152 | 1.062 ± 0.044 | 0.16 ± 0.07 | 7.24 / 6.94 | 1.043 ± 0.022 | 0.34 |
| gap | 1992 | 1.043 ± 0.031 | -0.40 ± 0.08 | 7.84 / 7.51 | 1.044 ± 0.024 | 0.37 |
| power | 2330 | 1.056 ± 0.020 | 0.32 ± 0.05 | 6.25 / 5.27 | 1.186 ± 0.014 | 0.57 |
| eye | 2330 | 0.849 ± 0.011 | 0.19 ± 0.03 | 6.30 / 6.07 | 1.038 ± 0.011 | 0.69 |
| avoid_k | 2330 | 0.975 ± 0.007 | 0.02 ± 0.02 | 4.67 / 4.43 | 1.054 ± 0.012 | 0.78 |
| stuff | 1531 | 0.959 ± 0.010 | 0.25 ± 0.04 | 4.01 / 3.70 | 1.084 ± 0.016 | 0.87 |
| control | 1531 | 0.966 ± 0.010 | 0.25 ± 0.06 | 4.98 / 4.87 | 1.022 ± 0.015 | 0.72 |
| movement | 1531 | 0.779 ± 0.013 | 0.93 ± 0.09 | 7.90 / 8.39 | 0.942 ± 0.017 | 0.45 |
| stamina | 4357 | 1.001 ± 0.007 | 0.01 ± 0.05 | 4.73 / 4.73 | 0.999 ± 0.007 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

