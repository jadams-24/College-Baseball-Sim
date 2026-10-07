# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-07.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2152 | +0.0008 ± 0.0024 | +0.06 | pass | 0.987 ± 0.016 | pass | 1.001 ± 0.016 | pass |
| gap | XBH share of hits | 1997 | +0.0008 ± 0.0050 | +0.03 | pass | 1.006 ± 0.016 | pass | 0.998 ± 0.013 | pass |
| power | HR/PA | 2328 | +0.0030 ± 0.0045 | +0.04 | pass | 1.000 ± 0.009 | pass | 1.009 ± 0.016 | pass |
| eye | BB/PA | 2328 | +0.0160 ± 0.0030 | +0.52 | FAIL | 0.989 ± 0.010 | FAIL | 1.022 ± 0.018 | FAIL |
| avoid_k | K/PA | 2328 | -0.0017 ± 0.0023 | -0.05 | pass | 1.000 ± 0.007 | pass | 0.998 ± 0.017 | pass |
| stuff | K/BF | 1623 | -0.0020 ± 0.0020 | -0.05 | FAIL | 1.002 ± 0.005 | pass | 0.998 ± 0.018 | pass |
| control | BB/BF | 1623 | +0.0087 ± 0.0031 | +0.21 | FAIL | 1.000 ± 0.010 | pass | 1.014 ± 0.021 | pass |
| movement | HR/BF | 1623 | +0.0001 ± 0.0058 | +0.00 | pass | 0.996 ± 0.019 | pass | 1.008 ± 0.025 | pass |
| stamina | pull hazard (log leash) | 4063 | +0.0025 ± 0.0025 | — | pass | 0.999 ± 0.004 | pass | 0.993 ± 0.013 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0008 / 0.983 / 1.005 | -0.0000 / 0.985 / 0.998 | +0.0028 / 0.980 / 1.001 |
| gap | plate appearances | -0.0006 / 1.017 / 0.996 | +0.0020 / 1.004 / 1.003 | +0.0007 / 1.000 / 0.995 |
| power | plate appearances | +0.0046 / 0.998 / 1.000 | +0.0011 / 0.996 / 1.003 | +0.0035 / 1.005 / 1.017 |
| eye | plate appearances | +0.0116 † / 0.993 / 1.019 | +0.0149 † / 0.985 / 1.014 | +0.0198 † / 0.986 † / 1.031 † |
| avoid_k | plate appearances | -0.0002 / 1.004 / 0.997 | -0.0023 / 0.995 / 1.007 | -0.0023 / 1.001 / 0.992 |
| stuff | batters faced | -0.0040 / 1.002 / 1.004 | -0.0019 / 1.007 / 1.001 | -0.0011 / 0.998 / 0.993 |
| control | batters faced | +0.0199 † / 0.994 / 1.036 | +0.0116 † / 0.994 / 1.020 | -0.0006 / 0.998 / 0.996 |
| movement | batters faced | +0.0036 / 0.992 / 1.003 | +0.0012 / 1.008 / 1.025 | -0.0026 / 0.986 / 0.997 |
| stamina | appearances | -0.0054 / 0.997 / 1.001 | -0.0019 / 1.000 / 0.992 | +0.0087 † / 0.998 / 0.991 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.928 | 1.043 |
| gap | 0.977 | 1.020 |
| power | 0.928 | 1.191 |
| eye | 1.009 | 1.062 |
| avoid_k | 0.979 | 1.125 |
| stuff | 1.009 | 1.205 |
| control | 1.008 | 1.048 |
| movement | 1.003 | 1.157 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.5 | 9.8 | 57.6 | 51.3 | 46.1 | pass |
| gap | 49.6 | 9.8 | 55.7 | 50.7 | 46.6 | pass |
| power | 49.5 | 9.7 | 57.1 | 49.5 | 44.1 | pass |
| eye | 49.9 | 9.9 | 54.8 | 49.8 | 45.9 | pass |
| avoid_k | 49.7 | 10.0 | 56.4 | 51.0 | 46.5 | pass |
| stuff | 50.3 | 9.7 | 58.8 | 51.2 | 45.6 | pass |
| control | 50.9 | 9.6 | 58.4 | 53.4 | 49.8 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.7 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): BR. Judax | Stebrealt Bison (p4) | regular | Contact 55, Gap 67, Power 67, Eye 68, Avoid K 56, Speed 67 | 41 G, 177 PA, 0.365/0.500/0.766, 14 HR, 17.5% BB, 13.0% K |
| Median mid-major regular: BR. Mel | Doudim Pilots (mid) | regular | Contact 57, Gap 59, Power 55, Eye 52, Avoid K 43, Speed 50 | 45 G, 170 PA, 0.262/0.371/0.454, 6 HR, 9.4% BB, 30.0% K |
| Median low-tier regular: BR. Soviley | Mowum Quakers (low) | regular | Contact 50, Gap 34, Power 38, Eye 56, Avoid K 32, Speed 43 | 55 G, 208 PA, 0.284/0.411/0.408, 2 HR, 14.4% BB, 22.6% K |
| Home-run leader: G. Vealey | Saiberg Lynx (mid) | regular | Contact 60, Gap 75, Power 70, Eye 55, Avoid K 50, Speed 72 | 54 G, 272 PA, 0.371/0.469/0.826, 25 HR, 11.4% BB, 14.7% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 255 PA, 0.346/0.441/0.626, 14 HR, 14.9% BB, 22.0% K |
| Bench player with most PA: ST. Pason | Seatriley Clippers (p4) | bench | Contact 47, Gap 48, Power 54, Eye 60, Avoid K 50, Speed 26 | 36 G, 138 PA, 0.327/0.496/0.505, 3 HR, 17.4% BB, 13.8% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 13 G, 13 GS, 77.0 IP, 0.70 ERA, 16.5 K/9, 2.9 BB/9, 0.2 HR/9 |
| Median mid-major weekend starter: CL. Shestens | Fiseason Hawks (mid) | sp_weekend | Stuff 57, Control 44, Movement 53, Stamina 47 | 17 G, 13 GS, 57.0 IP, 5.21 ERA, 9.6 K/9, 5.2 BB/9, 0.5 HR/9 |
| Low-tier reliever with most innings: R. Ter | Weazeal Bobcats (low) | rp | Stuff 60, Control 57, Movement 51, Stamina 78 | 20 G, 0 GS, 59.2 IP, 6.79 ERA, 11.8 K/9, 2.6 BB/9, 2.0 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 16 G, 11 GS, 95.0 IP, 4.55 ERA, 8.8 K/9, 2.8 BB/9, 1.0 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2151 | 1.052 ± 0.034 | 0.13 ± 0.07 | 7.30 / 7.01 | 1.043 ± 0.023 | 0.35 |
| gap | 1997 | 1.046 ± 0.033 | -0.43 ± 0.09 | 7.81 / 7.60 | 1.029 ± 0.019 | 0.38 |
| power | 2328 | 1.045 ± 0.017 | 0.22 ± 0.08 | 6.23 / 5.32 | 1.170 ± 0.017 | 0.59 |
| eye | 2328 | 0.962 ± 0.013 | 0.22 ± 0.04 | 5.93 / 5.92 | 1.002 ± 0.009 | 0.65 |
| avoid_k | 2328 | 0.996 ± 0.009 | 0.01 ± 0.02 | 4.59 / 4.42 | 1.039 ± 0.009 | 0.78 |
| stuff | 1623 | 0.964 ± 0.006 | 0.28 ± 0.04 | 3.94 / 3.69 | 1.069 ± 0.014 | 0.87 |
| control | 1623 | 0.962 ± 0.010 | 0.33 ± 0.05 | 4.99 / 4.88 | 1.023 ± 0.012 | 0.72 |
| movement | 1623 | 0.765 ± 0.029 | 0.97 ± 0.10 | 7.89 / 8.39 | 0.941 ± 0.016 | 0.44 |
| stamina | 4062 | 1.000 ± 0.006 | 0.03 ± 0.06 | 4.66 / 4.66 | 1.000 ± 0.006 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

