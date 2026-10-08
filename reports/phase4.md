# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-08.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2154 | +0.0003 ± 0.0030 | +0.02 | pass | 0.996 ± 0.018 | pass | 0.995 ± 0.014 | pass |
| gap | XBH share of hits | 1991 | +0.0025 ± 0.0040 | +0.10 | pass | 0.993 ± 0.019 | pass | 0.999 ± 0.018 | pass |
| power | HR/PA | 2328 | +0.0019 ± 0.0048 | +0.03 | pass | 0.997 ± 0.011 | pass | 1.001 ± 0.016 | pass |
| eye | BB/PA | 2328 | -0.0008 ± 0.0024 | -0.03 | pass | 1.001 ± 0.009 | pass | 0.996 ± 0.013 | pass |
| avoid_k | K/PA | 2328 | -0.0004 ± 0.0019 | -0.01 | pass | 1.000 ± 0.007 | pass | 0.992 ± 0.017 | pass |
| stuff | K/BF | 1620 | -0.0014 ± 0.0023 | -0.03 | pass | 1.000 ± 0.006 | pass | 0.992 ± 0.026 | pass |
| control | BB/BF | 1620 | +0.0001 ± 0.0027 | +0.00 | pass | 1.000 ± 0.009 | pass | 0.992 ± 0.023 | pass |
| movement | HR/BF | 1620 | -0.0010 ± 0.0045 | -0.03 | pass | 0.989 ± 0.013 | pass | 0.997 ± 0.016 | pass |
| stamina | pull hazard (log leash) | 4076 | +0.0002 ± 0.0026 | — | pass | 0.999 ± 0.005 | pass | 0.999 ± 0.010 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0016 / 1.005 / 0.995 | -0.0006 / 0.987 / 0.992 | +0.0024 / 0.986 / 0.997 |
| gap | plate appearances | +0.0048 / 0.992 / 1.005 | -0.0021 / 0.996 / 0.993 | +0.0047 / 0.991 / 1.001 |
| power | plate appearances | +0.0030 / 0.996 / 0.992 | -0.0006 / 0.994 / 0.997 | +0.0032 / 1.000 / 1.008 |
| eye | plate appearances | -0.0007 / 1.000 / 1.004 | -0.0016 / 1.002 / 1.006 | -0.0003 / 1.001 / 0.983 |
| avoid_k | plate appearances | +0.0017 / 1.004 / 1.001 | -0.0007 / 0.994 / 0.996 | -0.0016 / 1.002 / 0.981 |
| stuff | batters faced | -0.0030 / 1.002 / 0.990 | -0.0019 / 1.001 / 1.000 | -0.0002 / 0.998 / 0.987 |
| control | batters faced | +0.0032 / 0.999 / 0.994 | +0.0037 / 1.001 / 1.001 | -0.0048 † / 0.995 / 0.984 |
| movement | batters faced | -0.0012 / 0.987 / 0.992 | +0.0049 / 0.984 / 1.006 | -0.0052 / 0.994 / 0.993 |
| stamina | appearances | -0.0079 † / 1.004 / 0.997 | -0.0066 † / 0.999 / 0.999 | +0.0086 † / 0.996 / 1.000 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.933 | 1.040 |
| gap | 0.970 | 1.024 |
| power | 0.918 | 1.195 |
| eye | 1.028 | 1.277 |
| avoid_k | 0.983 | 1.181 |
| stuff | 1.011 | 1.254 |
| control | 1.005 | 1.041 |
| movement | 0.993 | 1.151 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.7 | 57.4 | 51.3 | 46.3 | pass |
| gap | 49.6 | 9.8 | 55.6 | 50.7 | 46.8 | pass |
| power | 49.5 | 9.6 | 56.9 | 49.5 | 44.3 | pass |
| eye | 49.9 | 9.8 | 54.7 | 49.9 | 46.0 | pass |
| avoid_k | 49.8 | 9.9 | 56.2 | 51.0 | 46.7 | pass |
| stuff | 50.3 | 9.8 | 58.9 | 51.2 | 45.5 | pass |
| control | 50.9 | 9.7 | 58.5 | 53.4 | 49.8 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.6 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): M. Lestelt | Seatriley Clippers (p4) | regular | Contact 67, Gap 50, Power 64, Eye 50, Avoid K 59, Speed 65 | 46 G, 210 PA, 0.439/0.507/0.856, 19 HR, 11.4% BB, 11.9% K |
| Median mid-major regular: GR. Kystan | Stafaiwood Mustangs (mid) | regular | Contact 61, Gap 43, Power 38, Eye 62, Avoid K 48, Speed 50 | 47 G, 184 PA, 0.282/0.431/0.394, 3 HR, 16.8% BB, 21.2% K |
| Median low-tier regular: R. Mard | Louton Kestrels (low) | regular | Contact 40, Gap 49, Power 41, Eye 60, Avoid K 36, Speed 53 | 52 G, 244 PA, 0.270/0.422/0.402, 3 HR, 19.7% BB, 20.1% K |
| Home-run leader: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 73, Eye 60, Avoid K 58, Speed 64 | 52 G, 250 PA, 0.357/0.444/0.822, 28 HR, 12.8% BB, 22.4% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 73, Eye 60, Avoid K 58, Speed 64 | 52 G, 250 PA, 0.357/0.444/0.822, 28 HR, 12.8% BB, 22.4% K |
| Bench player with most PA: Z. Seanaiwood | Sugoufield Monarchs (p4) | bench | Contact 46, Gap 51, Power 54, Eye 59, Avoid K 54, Speed 80 | 38 G, 133 PA, 0.198/0.333/0.321, 2 HR, 15.0% BB, 21.8% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 14 G, 13 GS, 74.2 IP, 1.81 ERA, 16.5 K/9, 3.5 BB/9, 0.6 HR/9 |
| Median mid-major weekend starter: TH. Routriwell | Souclowood Otters (mid) | sp_weekend | Stuff 45, Control 66, Movement 55, Stamina 47 | 13 G, 13 GS, 62.0 IP, 5.37 ERA, 7.1 K/9, 2.3 BB/9, 0.9 HR/9 |
| Low-tier reliever with most innings: R. Ter | Weazeal Bobcats (low) | rp | Stuff 60, Control 57, Movement 51, Stamina 78 | 24 G, 0 GS, 71.2 IP, 3.64 ERA, 9.4 K/9, 2.1 BB/9, 0.6 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 13 G, 11 GS, 80.1 IP, 5.27 ERA, 9.9 K/9, 2.5 BB/9, 0.9 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2154 | 1.061 ± 0.037 | 0.16 ± 0.08 | 7.25 / 6.93 | 1.046 ± 0.020 | 0.34 |
| gap | 1990 | 1.041 ± 0.035 | -0.43 ± 0.07 | 7.82 / 7.52 | 1.041 ± 0.022 | 0.37 |
| power | 2327 | 1.058 ± 0.020 | 0.30 ± 0.06 | 6.24 / 5.28 | 1.183 ± 0.017 | 0.57 |
| eye | 2327 | 0.851 ± 0.009 | 0.17 ± 0.02 | 6.29 / 6.09 | 1.033 ± 0.008 | 0.69 |
| avoid_k | 2327 | 0.977 ± 0.009 | 0.01 ± 0.03 | 4.68 / 4.43 | 1.056 ± 0.010 | 0.78 |
| stuff | 1620 | 0.957 ± 0.009 | 0.29 ± 0.04 | 4.00 / 3.69 | 1.082 ± 0.015 | 0.87 |
| control | 1620 | 0.966 ± 0.007 | 0.35 ± 0.06 | 5.00 / 4.86 | 1.029 ± 0.015 | 0.72 |
| movement | 1620 | 0.769 ± 0.021 | 0.98 ± 0.08 | 7.89 / 8.40 | 0.940 ± 0.015 | 0.44 |
| stamina | 4076 | 1.001 ± 0.006 | 0.00 ± 0.06 | 4.67 / 4.68 | 0.999 ± 0.007 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

