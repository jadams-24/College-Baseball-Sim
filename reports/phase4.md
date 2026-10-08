# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-08.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2153 | +0.0004 ± 0.0022 | +0.03 | pass | 0.991 ± 0.018 | pass | 1.000 ± 0.016 | pass |
| gap | XBH share of hits | 1993 | +0.0006 ± 0.0041 | +0.03 | pass | 1.006 ± 0.016 | pass | 0.992 ± 0.021 | pass |
| power | HR/PA | 2326 | +0.0021 ± 0.0038 | +0.03 | pass | 1.001 ± 0.010 | pass | 1.010 ± 0.021 | pass |
| eye | BB/PA | 2326 | +0.0007 ± 0.0024 | +0.02 | pass | 1.001 ± 0.011 | pass | 1.006 ± 0.017 | pass |
| avoid_k | K/PA | 2326 | -0.0013 ± 0.0022 | -0.03 | pass | 1.001 ± 0.006 | pass | 1.003 ± 0.017 | pass |
| stuff | K/BF | 1620 | -0.0012 ± 0.0027 | -0.03 | pass | 1.000 ± 0.005 | pass | 1.004 ± 0.020 | pass |
| control | BB/BF | 1620 | -0.0000 ± 0.0027 | -0.00 | pass | 1.003 ± 0.010 | pass | 0.991 ± 0.020 | pass |
| movement | HR/BF | 1620 | -0.0020 ± 0.0038 | -0.06 | pass | 0.997 ± 0.017 | pass | 1.000 ± 0.014 | pass |
| stamina | pull hazard (log leash) | 4065 | +0.0020 ± 0.0029 | — | pass | 0.999 ± 0.004 | pass | 1.001 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0007 / 0.989 / 0.993 | -0.0006 / 0.977 † / 1.012 | +0.0021 / 0.994 / 0.994 |
| gap | plate appearances | +0.0016 / 1.000 / 1.010 | -0.0018 / 1.019 / 0.985 | +0.0020 / 1.000 / 0.986 |
| power | plate appearances | +0.0087 / 1.005 / 1.003 | -0.0023 / 0.996 / 0.998 | +0.0021 / 1.003 / 1.021 |
| eye | plate appearances | -0.0005 / 1.001 / 1.000 | -0.0010 / 0.999 / 0.996 | +0.0029 / 1.001 / 1.018 |
| avoid_k | plate appearances | +0.0010 / 1.004 / 0.992 | -0.0020 / 0.998 / 1.009 | -0.0024 / 0.999 / 1.005 |
| stuff | batters faced | -0.0025 / 0.999 / 0.992 | -0.0021 / 1.003 / 1.016 | +0.0002 / 0.998 / 1.002 |
| control | batters faced | +0.0030 / 0.996 / 0.997 | +0.0029 / 1.002 / 0.979 | -0.0043 † / 1.002 / 0.997 |
| movement | batters faced | -0.0008 / 1.000 / 1.003 | +0.0003 / 0.998 / 1.011 | -0.0043 / 0.989 / 0.989 |
| stamina | appearances | -0.0058 † / 1.001 / 0.988 | -0.0028 / 0.999 / 1.005 | +0.0084 † / 0.997 / 1.004 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.932 | 1.039 |
| gap | 0.979 | 1.015 |
| power | 0.928 | 1.197 |
| eye | 1.012 | 1.071 |
| avoid_k | 0.979 | 1.125 |
| stuff | 1.007 | 1.208 |
| control | 1.008 | 1.040 |
| movement | 1.006 | 1.146 |

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
| Best P4 hitter (OPS, qualified): SH. Stailey | Grokealt Gulls (p4) | regular | Contact 71, Gap 52, Power 69, Eye 64, Avoid K 50, Speed 50 | 53 G, 256 PA, 0.409/0.506/0.889, 27 HR, 15.2% BB, 16.8% K |
| Median mid-major regular: C. Vawood | Stafaiwood Mustangs (mid) | regular | Contact 57, Gap 47, Power 35, Eye 56, Avoid K 56, Speed 25 | 50 G, 216 PA, 0.322/0.396/0.426, 0 HR, 10.6% BB, 11.6% K |
| Median low-tier regular: L. Tang | Hetiberg Hawks (low) | regular | Contact 59, Gap 49, Power 56, Eye 55, Avoid K 39, Speed 50 | 46 G, 177 PA, 0.236/0.384/0.429, 4 HR, 14.1% BB, 22.6% K |
| Home-run leader: G. Vealey | Saiberg Lynx (mid) | regular | Contact 60, Gap 75, Power 70, Eye 55, Avoid K 50, Speed 72 | 53 G, 276 PA, 0.405/0.504/0.881, 28 HR, 9.8% BB, 16.3% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 253 PA, 0.373/0.451/0.627, 12 HR, 11.9% BB, 20.6% K |
| Bench player with most PA: C. Duford | Shaford Pioneers (mid) | bench | Contact 42, Gap 43, Power 45, Eye 56, Avoid K 37, Speed 44 | 38 G, 140 PA, 0.181/0.267/0.310, 4 HR, 9.3% BB, 25.7% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 13 G, 13 GS, 74.2 IP, 1.57 ERA, 16.6 K/9, 2.9 BB/9, 0.5 HR/9 |
| Median mid-major weekend starter: W. Taiford | Douleley Owls (mid) | sp_weekend | Stuff 65, Control 70, Movement 37, Stamina 43 | 16 G, 13 GS, 59.1 IP, 5.31 ERA, 12.1 K/9, 2.3 BB/9, 1.7 HR/9 |
| Low-tier reliever with most innings: N. Teton | Zusyt Lancers (low) | rp | Stuff 38, Control 46, Movement 46, Stamina 62 | 27 G, 1 GS, 64.2 IP, 6.68 ERA, 7.8 K/9, 5.3 BB/9, 0.7 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 15 G, 11 GS, 92.0 IP, 5.48 ERA, 8.7 K/9, 2.2 BB/9, 1.4 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2152 | 1.061 ± 0.036 | 0.16 ± 0.10 | 7.29 / 6.96 | 1.048 ± 0.018 | 0.35 |
| gap | 1993 | 1.048 ± 0.035 | -0.46 ± 0.10 | 7.81 / 7.57 | 1.033 ± 0.018 | 0.38 |
| power | 2326 | 1.041 ± 0.017 | 0.21 ± 0.06 | 6.24 / 5.33 | 1.170 ± 0.013 | 0.59 |
| eye | 2326 | 0.956 ± 0.014 | 0.20 ± 0.04 | 5.94 / 5.92 | 1.002 ± 0.011 | 0.65 |
| avoid_k | 2326 | 0.997 ± 0.009 | -0.00 ± 0.02 | 4.59 / 4.42 | 1.039 ± 0.008 | 0.78 |
| stuff | 1620 | 0.967 ± 0.007 | 0.28 ± 0.04 | 3.94 / 3.69 | 1.068 ± 0.017 | 0.86 |
| control | 1620 | 0.963 ± 0.013 | 0.35 ± 0.05 | 4.99 / 4.88 | 1.023 ± 0.012 | 0.72 |
| movement | 1620 | 0.768 ± 0.018 | 0.97 ± 0.09 | 7.87 / 8.38 | 0.939 ± 0.015 | 0.45 |
| stamina | 4064 | 1.003 ± 0.008 | 0.04 ± 0.05 | 4.66 / 4.66 | 1.001 ± 0.007 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

