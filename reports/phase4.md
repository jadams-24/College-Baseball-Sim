# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-08.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2154 | -0.0002 ± 0.0027 | -0.02 | pass | 0.994 ± 0.016 | pass | 0.986 ± 0.019 | pass |
| gap | XBH share of hits | 1992 | +0.0017 ± 0.0042 | +0.07 | pass | 0.997 ± 0.014 | pass | 1.004 ± 0.014 | pass |
| power | HR/PA | 2327 | +0.0028 ± 0.0035 | +0.04 | pass | 0.997 ± 0.011 | pass | 0.998 ± 0.019 | pass |
| eye | BB/PA | 2327 | -0.0003 ± 0.0026 | -0.01 | pass | 1.003 ± 0.009 | pass | 0.999 ± 0.013 | pass |
| avoid_k | K/PA | 2327 | -0.0009 ± 0.0018 | -0.02 | pass | 1.000 ± 0.007 | pass | 0.990 ± 0.015 | pass |
| stuff | K/BF | 1619 | -0.0015 ± 0.0022 | -0.03 | pass | 0.998 ± 0.006 | pass | 0.995 ± 0.026 | pass |
| control | BB/BF | 1619 | -0.0004 ± 0.0026 | -0.01 | pass | 1.000 ± 0.009 | pass | 0.987 ± 0.023 | pass |
| movement | HR/BF | 1619 | +0.0008 ± 0.0046 | +0.03 | pass | 0.998 ± 0.020 | pass | 1.000 ± 0.023 | pass |
| stamina | pull hazard (log leash) | 4070 | +0.0006 ± 0.0022 | — | pass | 1.001 ± 0.004 | pass | 1.004 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0009 / 0.985 / 0.997 | -0.0015 / 0.999 / 0.988 | +0.0014 / 0.988 / 0.978 |
| gap | plate appearances | +0.0031 / 0.995 / 1.011 | +0.0006 / 1.002 / 1.009 | +0.0016 / 0.996 / 0.995 |
| power | plate appearances | +0.0005 / 0.995 / 0.994 | +0.0006 / 0.995 / 0.998 | +0.0053 / 0.998 / 0.998 |
| eye | plate appearances | -0.0015 / 0.998 / 0.994 | -0.0007 / 1.008 / 1.007 | +0.0009 / 1.000 / 0.995 |
| avoid_k | plate appearances | +0.0014 / 1.001 / 0.993 | -0.0011 / 0.995 / 0.992 | -0.0023 / 1.004 / 0.986 |
| stuff | batters faced | -0.0021 / 1.001 / 0.996 | -0.0027 / 1.001 / 0.998 | -0.0003 / 0.993 / 0.993 |
| control | batters faced | +0.0002 / 0.995 / 0.992 | +0.0033 / 1.003 / 0.992 | -0.0037 / 0.998 / 0.979 |
| movement | batters faced | -0.0035 / 1.003 / 0.991 | +0.0087 / 0.998 / 1.025 | -0.0027 / 0.991 / 0.987 |
| stamina | appearances | -0.0083 † / 1.007 / 1.007 | -0.0047 † / 1.004 / 1.002 | +0.0083 † / 0.995 † / 1.005 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.927 | 1.033 |
| gap | 0.972 | 1.027 |
| power | 0.918 | 1.198 |
| eye | 1.031 | 1.278 |
| avoid_k | 0.982 | 1.179 |
| stuff | 1.008 | 1.258 |
| control | 1.005 | 1.037 |
| movement | 1.002 | 1.155 |

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
| Best P4 hitter (OPS, qualified): TR. Graigyley | Thyryn Owls (p4) | regular | Contact 61, Gap 52, Power 67, Eye 61, Avoid K 45, Speed 51 | 27 G, 105 PA, 0.420/0.533/0.827, 7 HR, 19.0% BB, 13.3% K |
| Median mid-major regular: W. Rord | Stouvaifield Badgers (mid) | regular | Contact 36, Gap 54, Power 50, Eye 69, Avoid K 48, Speed 56 | 40 G, 157 PA, 0.299/0.395/0.425, 3 HR, 12.1% BB, 20.4% K |
| Median low-tier regular: BR. Wysewood | Vaimoux Voyagers (low) | regular | Contact 49, Gap 52, Power 46, Eye 34, Avoid K 57, Speed 47 | 53 G, 249 PA, 0.291/0.346/0.475, 9 HR, 6.8% BB, 18.1% K |
| Home-run leader: TH. Stojeafield | Season Wolves (p4) | regular | Contact 71, Gap 58, Power 68, Eye 67, Avoid K 38, Speed 20 | 50 G, 234 PA, 0.315/0.402/0.764, 27 HR, 10.7% BB, 31.6% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 258 PA, 0.373/0.450/0.795, 26 HR, 12.8% BB, 20.9% K |
| Bench player with most PA: Z. Woson | Wicot Gulls (p4) | bench | Contact 45, Gap 50, Power 49, Eye 69, Avoid K 56, Speed 53 | 39 G, 134 PA, 0.211/0.348/0.376, 5 HR, 11.9% BB, 17.9% K |
| Best P4 weekend starter (ERA, qualified): N. Stouvuwell | Nythaberg Bluejays (p4) | sp_weekend | Stuff 62, Control 66, Movement 51, Stamina 47 | 12 G, 9 GS, 57.0 IP, 1.89 ERA, 9.5 K/9, 1.3 BB/9, 0.8 HR/9 |
| Median mid-major weekend starter: R. Teashout | Rair Otters (mid) | sp_weekend | Stuff 49, Control 54, Movement 52, Stamina 46 | 17 G, 12 GS, 57.2 IP, 5.31 ERA, 7.8 K/9, 3.3 BB/9, 0.9 HR/9 |
| Low-tier reliever with most innings: R. Ter | Weazeal Bobcats (low) | rp | Stuff 60, Control 57, Movement 51, Stamina 78 | 23 G, 0 GS, 65.1 IP, 4.41 ERA, 10.6 K/9, 2.8 BB/9, 0.8 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 14 G, 11 GS, 83.2 IP, 5.06 ERA, 9.1 K/9, 2.4 BB/9, 1.1 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2153 | 1.082 ± 0.039 | 0.22 ± 0.07 | 7.29 / 6.90 | 1.057 ± 0.021 | 0.34 |
| gap | 1991 | 1.037 ± 0.038 | -0.41 ± 0.08 | 7.84 / 7.56 | 1.037 ± 0.018 | 0.38 |
| power | 2327 | 1.059 ± 0.024 | 0.29 ± 0.06 | 6.26 / 5.30 | 1.181 ± 0.019 | 0.58 |
| eye | 2327 | 0.851 ± 0.008 | 0.17 ± 0.03 | 6.29 / 6.10 | 1.032 ± 0.009 | 0.69 |
| avoid_k | 2327 | 0.979 ± 0.008 | 0.00 ± 0.02 | 4.67 / 4.43 | 1.055 ± 0.010 | 0.78 |
| stuff | 1619 | 0.959 ± 0.009 | 0.29 ± 0.03 | 4.00 / 3.69 | 1.085 ± 0.016 | 0.87 |
| control | 1619 | 0.967 ± 0.012 | 0.34 ± 0.05 | 5.00 / 4.87 | 1.028 ± 0.013 | 0.72 |
| movement | 1619 | 0.768 ± 0.021 | 1.00 ± 0.09 | 7.87 / 8.40 | 0.938 ± 0.015 | 0.44 |
| stamina | 4070 | 0.999 ± 0.006 | 0.00 ± 0.05 | 4.67 / 4.68 | 0.998 ± 0.006 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

