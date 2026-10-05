# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-05.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2251 | +0.0005 ± 0.0022 | +0.04 | pass | 1.000 ± 0.017 | pass | 0.991 ± 0.013 | pass |
| gap | XBH share of hits | 2092 | +0.0008 ± 0.0038 | +0.03 | pass | 1.001 ± 0.019 | pass | 1.002 ± 0.017 | pass |
| power | HR/PA | 2408 | +0.0016 ± 0.0045 | +0.02 | pass | 0.996 ± 0.009 | pass | 1.000 ± 0.023 | pass |
| eye | BB/PA | 2408 | -0.0001 ± 0.0031 | -0.00 | pass | 0.998 ± 0.007 | pass | 0.992 ± 0.019 | pass |
| avoid_k | K/PA | 2408 | -0.0001 ± 0.0025 | -0.00 | pass | 1.003 ± 0.005 | pass | 1.001 ± 0.014 | pass |
| stuff | K/BF | 1755 | -0.0003 ± 0.0029 | -0.01 | pass | 0.999 ± 0.005 | pass | 0.998 ± 0.018 | pass |
| control | BB/BF | 1755 | -0.0007 ± 0.0028 | -0.02 | pass | 1.002 ± 0.009 | pass | 1.007 ± 0.016 | pass |
| movement | HR/BF | 1755 | -0.0013 ± 0.0053 | -0.04 | pass | 1.006 ± 0.020 | pass | 1.003 ± 0.024 | pass |
| stamina | pull hazard (log leash) | 4162 | +0.0005 ± 0.0016 | — | pass | 1.000 ± 0.005 | pass | 0.994 ± 0.013 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0022 / 1.008 / 0.997 | -0.0009 / 0.978 / 0.993 | +0.0036 † / 0.998 / 0.985 |
| gap | plate appearances | +0.0002 / 1.015 / 0.997 | +0.0014 / 0.993 / 0.999 | +0.0007 / 0.997 / 1.006 |
| power | plate appearances | +0.0009 / 0.998 / 1.011 | +0.0003 / 0.998 / 1.006 | +0.0027 / 0.991 / 0.991 |
| eye | plate appearances | -0.0015 / 0.991 / 0.981 | -0.0016 / 1.001 / 0.995 | +0.0021 / 0.998 / 0.996 |
| avoid_k | plate appearances | +0.0004 / 1.007 / 1.021 | +0.0004 / 1.002 / 0.990 | -0.0008 / 0.999 / 0.996 |
| stuff | batters faced | -0.0008 / 1.000 / 0.998 | -0.0000 / 0.996 / 1.017 | -0.0003 / 1.001 / 0.984 |
| control | batters faced | +0.0033 / 1.001 / 1.011 | +0.0033 / 0.999 / 1.009 | -0.0064 † / 0.998 / 1.004 |
| movement | batters faced | +0.0030 / 1.000 / 1.013 | +0.0037 / 1.009 / 1.016 | -0.0073 † / 1.008 / 0.988 |
| stamina | appearances | -0.0091 † / 0.999 / 0.999 | -0.0056 † / 1.002 / 0.991 | +0.0081 † / 0.998 / 0.994 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.943 | 1.032 |
| gap | 0.977 | 1.024 |
| power | 0.923 | 1.197 |
| eye | 1.008 | 1.057 |
| avoid_k | 0.977 | 1.132 |
| stuff | 0.998 | 1.193 |
| control | 1.003 | 1.062 |
| movement | 1.010 | 1.143 |

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
| control | 50.8 | 9.6 | 58.4 | 53.4 | 49.8 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.7 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): G. Cleawell | Nythaberg Bluejays (p4) | regular | Contact 43, Gap 80, Power 76, Eye 64, Avoid K 62, Speed 53 | 52 G, 247 PA, 0.358/0.465/0.811, 23 HR, 13.8% BB, 15.8% K |
| Median mid-major regular: Z. Pobrom | Rutrouns Rams (mid) | regular | Contact 49, Gap 50, Power 51, Eye 43, Avoid K 45, Speed 70 | 55 G, 232 PA, 0.289/0.364/0.461, 6 HR, 6.0% BB, 18.1% K |
| Median low-tier regular: G. Gyr | Cen Mustangs (low) | regular | Contact 36, Gap 33, Power 33, Eye 31, Avoid K 58, Speed 50 | 31 G, 120 PA, 0.333/0.432/0.394, 1 HR, 10.8% BB, 11.7% K |
| Home-run leader: N. Troujeal | Shaberg Rams (mid) | regular | Contact 67, Gap 58, Power 79, Eye 48, Avoid K 56, Speed 51 | 55 G, 277 PA, 0.395/0.449/0.823, 28 HR, 8.3% BB, 14.1% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 55 G, 277 PA, 0.361/0.460/0.626, 13 HR, 15.9% BB, 17.3% K |
| Bench player with most PA: S. Kifield | Rym Lancers (mid) | bench | Contact 40, Gap 43, Power 48, Eye 64, Avoid K 50, Speed 64 | 42 G, 135 PA, 0.267/0.418/0.362, 3 HR, 17.0% BB, 14.8% K |
| Best P4 weekend starter (ERA, qualified): F. Wefofield | Vywood Stags (p4) | sp_weekend | Stuff 74, Control 64, Movement 67, Stamina 48 | 14 G, 14 GS, 75.1 IP, 1.43 ERA, 13.4 K/9, 1.9 BB/9, 0.5 HR/9 |
| Median mid-major weekend starter: L. Staberg | Clird Monarchs (mid) | sp_weekend | Stuff 55, Control 52, Movement 68, Stamina 52 | 13 G, 13 GS, 64.1 IP, 5.32 ERA, 7.8 K/9, 3.6 BB/9, 1.0 HR/9 |
| Low-tier reliever with most innings: C. Tritriton | Relom Gulls (low) | rp | Stuff 64, Control 55, Movement 52, Stamina 65 | 26 G, 3 GS, 61.1 IP, 3.82 ERA, 11.7 K/9, 5.0 BB/9, 0.4 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 11 G, 8 GS, 56.0 IP, 5.14 ERA, 8.4 K/9, 2.4 BB/9, 1.1 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2250 | 1.063 ± 0.036 | 0.08 ± 0.09 | 7.25 / 6.97 | 1.040 ± 0.017 | 0.36 |
| gap | 2092 | 1.040 ± 0.031 | -0.41 ± 0.08 | 7.82 / 7.55 | 1.036 ± 0.022 | 0.38 |
| power | 2408 | 1.057 ± 0.024 | 0.19 ± 0.05 | 6.23 / 5.27 | 1.182 ± 0.012 | 0.59 |
| eye | 2408 | 0.964 ± 0.011 | 0.14 ± 0.05 | 5.87 / 5.87 | 1.001 ± 0.010 | 0.65 |
| avoid_k | 2408 | 0.999 ± 0.007 | 0.02 ± 0.02 | 4.56 / 4.37 | 1.043 ± 0.007 | 0.78 |
| stuff | 1754 | 0.977 ± 0.008 | 0.29 ± 0.04 | 3.96 / 3.69 | 1.073 ± 0.013 | 0.85 |
| control | 1754 | 0.965 ± 0.008 | 0.47 ± 0.04 | 4.98 / 4.88 | 1.019 ± 0.009 | 0.72 |
| movement | 1754 | 0.782 ± 0.024 | 0.91 ± 0.10 | 7.87 / 8.41 | 0.936 ± 0.016 | 0.45 |
| stamina | 4162 | 0.998 ± 0.007 | 0.01 ± 0.04 | 4.62 / 4.63 | 0.997 ± 0.008 | 0.79 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

