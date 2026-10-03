# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-03.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2306 | +0.0010 ± 0.0038 | +0.08 | pass | 0.982 ± 0.020 | pass | 0.992 ± 0.019 | pass |
| gap | XBH share of hits | 2153 | -0.0012 ± 0.0055 | -0.05 | pass | 1.006 ± 0.025 | pass | 0.993 ± 0.020 | pass |
| power | HR/PA | 2452 | +0.0017 ± 0.0074 | +0.02 | pass | 1.001 ± 0.014 | pass | 0.991 ± 0.034 | pass |
| eye | BB/PA | 2452 | -0.0011 ± 0.0041 | -0.04 | pass | 0.996 ± 0.013 | pass | 0.996 ± 0.029 | pass |
| avoid_k | K/PA | 2452 | -0.0003 ± 0.0027 | -0.01 | pass | 1.002 ± 0.008 | pass | 0.994 ± 0.020 | pass |
| stuff | K/BF | 1814 | -0.0012 ± 0.0040 | -0.03 | pass | 1.001 ± 0.011 | pass | 0.998 ± 0.042 | pass |
| control | BB/BF | 1814 | -0.0016 ± 0.0060 | -0.04 | pass | 1.004 ± 0.010 | pass | 0.987 ± 0.026 | pass |
| movement | HR/BF | 1814 | -0.0022 ± 0.0070 | -0.07 | pass | 0.992 ± 0.022 | pass | 0.999 ± 0.026 | pass |
| stamina | pull hazard (log leash) | 4219 | +0.0004 ± 0.0052 | — | pass | 0.999 ± 0.009 | pass | 0.990 ± 0.018 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0010 / 0.979 / 0.981 | -0.0007 / 0.979 / 1.006 | +0.0039 / 0.967 / 0.989 |
| gap | plate appearances | -0.0000 / 1.008 / 1.011 | +0.0002 / 1.010 / 0.981 | -0.0032 / 1.008 / 0.990 |
| power | plate appearances | -0.0032 / 1.002 / 1.006 | -0.0022 / 1.010 / 0.983 | +0.0062 / 0.987 / 0.991 |
| eye | plate appearances | -0.0010 / 1.003 / 0.997 | -0.0023 / 0.993 / 0.991 | -0.0003 / 0.994 / 0.999 |
| avoid_k | plate appearances | +0.0004 / 1.002 / 1.006 | +0.0002 / 1.000 / 0.997 | -0.0012 / 1.002 / 0.983 |
| stuff | batters faced | -0.0015 / 0.995 / 1.006 | -0.0031 / 1.006 / 0.993 | +0.0002 / 0.999 / 0.997 |
| control | batters faced | -0.0001 / 1.003 / 0.985 | +0.0055 / 0.999 / 0.983 | -0.0080 † / 1.003 / 0.991 |
| movement | batters faced | +0.0027 / 0.998 / 1.003 | -0.0022 / 0.994 / 0.993 | -0.0049 / 0.982 / 1.001 |
| stamina | appearances | -0.0103 † / 0.995 / 0.993 | -0.0057 / 1.002 / 0.978 † | +0.0098 † / 0.996 / 0.998 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.941 | 1.037 |
| gap | 0.980 | 1.013 |
| power | 0.928 | 1.206 |
| eye | 1.009 | 1.063 |
| avoid_k | 0.978 | 1.124 |
| stuff | 0.997 | 1.212 |
| control | 1.005 | 1.045 |
| movement | 0.991 | 1.144 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.7 | 57.4 | 51.3 | 46.4 | pass |
| gap | 49.6 | 9.8 | 55.4 | 50.7 | 46.7 | pass |
| power | 49.5 | 9.6 | 56.7 | 49.5 | 44.4 | pass |
| eye | 50.0 | 9.8 | 54.7 | 49.9 | 46.1 | pass |
| avoid_k | 49.8 | 9.9 | 55.9 | 51.1 | 46.8 | pass |
| stuff | 50.1 | 9.8 | 58.8 | 51.2 | 45.2 | pass |
| control | 50.7 | 9.7 | 58.4 | 53.4 | 49.6 | pass |
| movement | 50.1 | 9.4 | 52.3 | 49.1 | 46.7 | pass |
| stamina | 51.6 | 10.0 | 50.0 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): H. Brit | Briberg Comets (p4) | regular | Contact 59, Gap 73, Power 72, Eye 61, Avoid K 54, Speed 46 | 51 G, 230 PA, 0.370/0.437/0.800, 21 HR, 9.1% BB, 16.5% K |
| Median mid-major regular: C. Shyt | Dyn Highlanders (mid) | regular | Contact 47, Gap 42, Power 32, Eye 36, Avoid K 58, Speed 40 | 53 G, 229 PA, 0.324/0.429/0.399, 1 HR, 8.3% BB, 11.8% K |
| Median low-tier regular: L. Kuford | Grym Mariners (low) | regular | Contact 49, Gap 62, Power 49, Eye 50, Avoid K 49, Speed 39 | 52 G, 242 PA, 0.294/0.406/0.406, 2 HR, 11.2% BB, 20.2% K |
| Home-run leader: CL. Zouzyn | Kigras Otters (mid) | regular | Contact 54, Gap 58, Power 60, Eye 59, Avoid K 53, Speed 62 | 56 G, 269 PA, 0.344/0.472/0.764, 25 HR, 17.1% BB, 14.9% K |
| Highest true Contact, qualified: BR. Bruwell | Nealewood Thunder (mid) | regular | Contact 80, Gap 69, Power 67, Eye 51, Avoid K 63, Speed 63 | 54 G, 271 PA, 0.425/0.500/0.768, 14 HR, 11.8% BB, 16.2% K |
| Bench player with most PA: Z. Clis | Claiford Cardinals (mid) | bench | Contact 39, Gap 44, Power 47, Eye 39, Avoid K 43, Speed 53 | 43 G, 145 PA, 0.248/0.297/0.331, 1 HR, 5.5% BB, 28.3% K |
| Best P4 weekend starter (ERA, qualified): F. Wefofield | Vywood Stags (p4) | sp_weekend | Stuff 73, Control 63, Movement 67, Stamina 48 | 15 G, 14 GS, 78.2 IP, 1.60 ERA, 13.7 K/9, 2.1 BB/9, 0.5 HR/9 |
| Median mid-major weekend starter: P. Zaiclufield | Saikuson Thunder (mid) | sp_weekend | Stuff 48, Control 48, Movement 64, Stamina 34 | 19 G, 14 GS, 62.1 IP, 5.34 ERA, 6.6 K/9, 4.2 BB/9, 0.1 HR/9 |
| Low-tier reliever with most innings: L. Shot | Daird Sailors (low) | rp | Stuff 45, Control 42, Movement 51, Stamina 77 | 27 G, 1 GS, 70.0 IP, 8.49 ERA, 9.8 K/9, 6.3 BB/9, 0.8 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 55, Control 70, Movement 46, Stamina 79 | 15 G, 11 GS, 84.0 IP, 2.68 ERA, 10.2 K/9, 1.8 BB/9, 0.5 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2306 | 1.052 ± 0.052 | 0.03 ± 0.16 | 7.23 / 6.94 | 1.043 ± 0.038 | 0.35 |
| gap | 2153 | 1.049 ± 0.047 | -0.45 ± 0.11 | 7.76 / 7.51 | 1.034 ± 0.027 | 0.38 |
| power | 2452 | 1.051 ± 0.022 | 0.15 ± 0.13 | 6.19 / 5.25 | 1.179 ± 0.024 | 0.59 |
| eye | 2452 | 0.963 ± 0.030 | 0.13 ± 0.07 | 5.86 / 5.83 | 1.004 ± 0.013 | 0.65 |
| avoid_k | 2452 | 1.000 ± 0.013 | 0.01 ± 0.02 | 4.52 / 4.35 | 1.041 ± 0.011 | 0.78 |
| stuff | 1814 | 0.977 ± 0.011 | 0.27 ± 0.08 | 3.97 / 3.69 | 1.078 ± 0.030 | 0.86 |
| control | 1814 | 0.973 ± 0.023 | 0.44 ± 0.08 | 4.92 / 4.87 | 1.011 ± 0.014 | 0.73 |
| movement | 1814 | 0.782 ± 0.045 | 0.92 ± 0.13 | 7.97 / 8.39 | 0.950 ± 0.018 | 0.44 |
| stamina | 4219 | 1.006 ± 0.015 | -0.01 ± 0.08 | 4.59 / 4.59 | 0.999 ± 0.011 | 0.79 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

