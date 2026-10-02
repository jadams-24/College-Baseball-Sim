# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-02.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2229 | +0.0015 ± 0.0034 | +0.12 | pass | 0.982 ± 0.032 | pass | 1.002 ± 0.026 | pass |
| gap | XBH share of hits | 2090 | +0.0014 ± 0.0066 | +0.06 | pass | 0.999 ± 0.022 | pass | 1.010 ± 0.030 | pass |
| power | HR/PA | 2364 | -0.0004 ± 0.0058 | -0.01 | pass | 0.998 ± 0.017 | pass | 0.999 ± 0.025 | pass |
| eye | BB/PA | 2364 | +0.0010 ± 0.0037 | +0.03 | pass | 1.002 ± 0.016 | pass | 1.006 ± 0.031 | pass |
| avoid_k | K/PA | 2364 | +0.0011 ± 0.0043 | +0.03 | pass | 0.999 ± 0.008 | pass | 0.997 ± 0.028 | pass |
| stuff | K/BF | 1812 | +0.0006 ± 0.0043 | +0.01 | pass | 1.002 ± 0.007 | pass | 0.993 ± 0.038 | pass |
| control | BB/BF | 1812 | -0.0006 ± 0.0064 | -0.02 | pass | 1.002 ± 0.015 | pass | 0.995 ± 0.028 | pass |
| movement | HR/BF | 1812 | -0.0023 ± 0.0071 | -0.07 | pass | 0.992 ± 0.025 | pass | 1.004 ± 0.032 | pass |
| stamina | pull hazard (log leash) | 4171 | -0.0017 ± 0.0029 | — | pass | 1.002 ± 0.006 | pass | 0.994 ± 0.017 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | +0.0004 / 0.967 / 0.994 | -0.0005 / 0.983 / 1.007 | +0.0040 / 0.972 / 1.002 |
| gap | plate appearances | -0.0007 / 0.999 / 0.983 | +0.0033 / 1.017 / 1.008 | +0.0013 / 0.981 / 1.028 |
| power | plate appearances | +0.0050 / 0.998 / 1.006 | -0.0069 / 1.001 / 0.992 | +0.0018 / 0.994 / 1.000 |
| eye | plate appearances | -0.0013 / 1.010 / 1.019 | -0.0001 / 0.997 / 0.992 | +0.0035 / 0.997 / 1.009 |
| avoid_k | plate appearances | +0.0001 / 1.004 / 1.001 | +0.0026 / 1.002 / 0.997 | +0.0004 / 0.988 / 0.994 |
| stuff | batters faced | +0.0002 / 0.997 / 0.984 | +0.0012 / 0.998 / 1.005 | +0.0004 / 1.008 / 0.988 |
| control | batters faced | +0.0031 / 1.006 / 1.010 | +0.0015 / 1.009 / 0.969 | -0.0045 / 0.989 / 1.006 |
| movement | batters faced | +0.0014 / 0.999 / 1.009 | +0.0070 / 0.997 / 1.003 | -0.0112 / 0.975 / 1.003 |
| stamina | appearances | -0.0101 † / 1.001 / 0.998 | -0.0058 † / 1.002 / 1.004 | +0.0042 / 1.001 / 0.986 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.968 | 1.044 |
| gap | 0.990 | 1.029 |
| power | 0.949 | 1.241 |
| eye | 1.014 | 1.070 |
| avoid_k | 0.983 | 1.131 |
| stuff | 1.015 | 1.212 |
| control | 1.004 | 1.045 |
| movement | 1.016 | 1.146 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.8 | 9.8 | 57.6 | 51.3 | 46.1 | pass |
| gap | 49.8 | 9.9 | 55.6 | 50.7 | 46.4 | pass |
| power | 49.8 | 9.7 | 57.0 | 49.5 | 44.1 | pass |
| eye | 50.1 | 9.9 | 54.9 | 49.9 | 45.9 | pass |
| avoid_k | 50.0 | 9.7 | 56.1 | 51.0 | 46.5 | pass |
| stuff | 50.1 | 9.4 | 58.9 | 51.2 | 45.0 | pass |
| control | 50.8 | 9.5 | 58.6 | 53.4 | 49.5 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.2 | 46.7 | pass |
| stamina | 51.7 | 10.0 | 50.0 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): TH. Sathaiwell | Sovum Bobcats (p4) | regular | Contact 60, Gap 57, Power 64, Eye 63, Avoid K 57, Speed 55 | 54 G, 251 PA, 0.430/0.514/0.903, 24 HR, 12.0% BB, 14.3% K |
| Median mid-major regular: S. Thaigran | Shouwell Clippers (mid) | regular | Contact 56, Gap 60, Power 52, Eye 53, Avoid K 47, Speed 53 | 56 G, 276 PA, 0.263/0.361/0.475, 9 HR, 9.1% BB, 19.2% K |
| Median low-tier regular: L. Seazult | Kan Cardinals (low) | regular | Contact 50, Gap 65, Power 53, Eye 46, Avoid K 29, Speed 53 | 56 G, 268 PA, 0.274/0.382/0.429, 6 HR, 13.4% BB, 22.4% K |
| Home-run leader: M. Veamyt | Shaberg Rams (mid) | regular | Contact 55, Gap 66, Power 76, Eye 41, Avoid K 50, Speed 59 | 55 G, 255 PA, 0.344/0.417/0.902, 36 HR, 8.6% BB, 22.4% K |
| Highest true Contact, qualified: D. Tron | Traiveng Badgers (p4) | regular | Contact 80, Gap 51, Power 74, Eye 61, Avoid K 46, Speed 55 | 53 G, 239 PA, 0.348/0.416/0.628, 15 HR, 8.4% BB, 32.6% K |
| Bench player with most PA: GR. Grodouley | Claiford Cardinals (mid) | bench | Contact 38, Gap 43, Power 45, Eye 53, Avoid K 44, Speed 60 | 43 G, 147 PA, 0.227/0.367/0.336, 3 HR, 10.9% BB, 22.4% K |
| Best P4 weekend starter (ERA, qualified): K. Tritouson | Stoukouberg Coyotes (p4) | sp_weekend | Stuff 63, Control 48, Movement 58, Stamina 54 | 12 G, 10 GS, 66.1 IP, 1.63 ERA, 11.1 K/9, 2.6 BB/9, 0.3 HR/9 |
| Median mid-major weekend starter: D. Neajom | Bres Falcons (mid) | sp_weekend | Stuff 46, Control 59, Movement 40, Stamina 51 | 19 G, 14 GS, 67.0 IP, 5.64 ERA, 6.9 K/9, 2.7 BB/9, 1.6 HR/9 |
| Low-tier reliever with most innings: T. Jeck | Nawell Thunder (low) | rp | Stuff 33, Control 52, Movement 41, Stamina 65 | 25 G, 1 GS, 64.0 IP, 7.73 ERA, 5.1 K/9, 3.5 BB/9, 1.4 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 52, Control 68, Movement 45, Stamina 79 | 11 G, 11 GS, 84.0 IP, 4.50 ERA, 6.6 K/9, 1.1 BB/9, 1.5 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2229 | 1.003 ± 0.055 | 0.14 ± 0.08 | 7.10 / 7.08 | 1.003 ± 0.039 | 0.39 |
| gap | 2090 | 1.012 ± 0.065 | -0.22 ± 0.10 | 7.72 / 7.60 | 1.017 ± 0.039 | 0.41 |
| power | 2364 | 1.004 ± 0.032 | 0.28 ± 0.07 | 6.07 / 5.30 | 1.146 ± 0.032 | 0.62 |
| eye | 2364 | 0.954 ± 0.028 | 0.14 ± 0.06 | 5.83 / 5.83 | 0.999 ± 0.018 | 0.66 |
| avoid_k | 2364 | 0.991 ± 0.012 | 0.05 ± 0.06 | 4.48 / 4.31 | 1.039 ± 0.019 | 0.79 |
| stuff | 1811 | 0.961 ± 0.012 | 0.30 ± 0.06 | 3.85 / 3.63 | 1.060 ± 0.028 | 0.87 |
| control | 1811 | 0.969 ± 0.019 | 0.46 ± 0.03 | 4.86 / 4.80 | 1.014 ± 0.011 | 0.72 |
| movement | 1811 | 0.785 ± 0.031 | 0.88 ± 0.09 | 7.87 / 8.43 | 0.934 ± 0.027 | 0.47 |
| stamina | 4170 | 1.000 ± 0.009 | -0.02 ± 0.04 | 4.44 / 4.46 | 0.997 ± 0.009 | 0.80 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

