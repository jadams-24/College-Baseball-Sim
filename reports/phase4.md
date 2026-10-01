# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-01.
Ratings re-express the true rates the engine uses: 50 is the D1 average (PA- or BF-weighted), 10 points one true-talent SD, all of D1 on one scale. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2314 | +0.0001 ± 0.0048 | +0.01 | pass | 0.991 ± 0.028 | pass | 1.011 ± 0.017 | pass |
| gap | XBH share of hits | 2156 | -0.0004 ± 0.0065 | -0.02 | pass | 1.001 ± 0.026 | pass | 1.006 ± 0.030 | pass |
| power | HR/PA | 2452 | -0.0009 ± 0.0089 | -0.01 | pass | 1.001 ± 0.015 | pass | 0.991 ± 0.032 | pass |
| eye | BB/PA | 2452 | +0.0011 ± 0.0055 | +0.04 | pass | 0.992 ± 0.018 | pass | 0.997 ± 0.039 | pass |
| avoid_k | K/PA | 2452 | +0.0004 ± 0.0016 | +0.01 | pass | 1.001 ± 0.003 | pass | 0.995 ± 0.014 | pass |
| stuff | K/BF | 2260 | -0.0004 ± 0.0026 | -0.01 | pass | 0.998 ± 0.008 | pass | 0.994 ± 0.043 | pass |
| control | BB/BF | 2260 | +0.0013 ± 0.0047 | +0.03 | pass | 1.001 ± 0.014 | pass | 0.990 ± 0.025 | pass |
| movement | HR/BF | 2260 | -0.0049 ± 0.0090 | -0.16 | pass | 0.991 ± 0.023 | pass | 1.000 ± 0.027 | pass |
| stamina | pull hazard (log leash) | 3879 | -0.0013 ± 0.0035 | — | pass | 1.001 ± 0.007 | pass | 0.993 ± 0.014 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0012 / 1.002 / 1.008 | -0.0037 / 0.975 / 1.008 | +0.0044 † / 0.973 / 1.015 |
| gap | plate appearances | +0.0009 / 1.009 / 1.012 | -0.0022 / 0.999 / 0.990 | +0.0002 / 0.999 / 1.014 |
| power | plate appearances | -0.0024 / 0.988 / 1.007 | -0.0045 / 0.989 / 0.995 | +0.0018 / 1.007 / 0.983 |
| eye | plate appearances | -0.0000 / 0.985 / 1.004 | -0.0007 / 0.995 / 0.996 | +0.0034 / 0.991 / 0.993 |
| avoid_k | plate appearances | -0.0005 / 1.004 / 0.974 | +0.0011 / 1.002 / 1.000 | +0.0004 / 0.998 / 1.004 |
| stuff | batters faced | +0.0008 / 1.001 / 0.992 | -0.0015 / 0.999 / 0.988 | -0.0002 / 0.997 / 0.999 |
| control | batters faced | +0.0033 / 0.991 / 0.981 | +0.0044 / 0.998 / 1.015 | -0.0026 / 1.007 / 0.976 |
| movement | batters faced | -0.0091 / 0.987 / 0.998 | -0.0019 / 0.971 / 1.007 | -0.0046 / 1.017 / 0.997 |
| stamina | appearances | -0.0005 / 1.000 / 0.998 | -0.0003 / 1.002 / 0.985 | -0.0022 / 1.000 / 0.995 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.987 | 1.019 |
| gap | 1.000 | 1.016 |
| power | 1.002 | 1.012 |
| eye | 1.002 | 1.020 |
| avoid_k | 0.995 | 1.021 |
| stuff | 0.991 | 1.046 |
| control | 1.001 | 1.004 |
| movement | 0.997 | 1.012 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 50.1 | 9.8 | 57.3 | 51.4 | 46.2 | pass |
| gap | 50.1 | 9.9 | 55.7 | 50.7 | 46.6 | pass |
| power | 50.2 | 9.8 | 57.5 | 50.4 | 44.4 | pass |
| eye | 50.1 | 9.9 | 54.7 | 50.0 | 46.0 | pass |
| avoid_k | 50.3 | 9.9 | 56.4 | 51.2 | 46.9 | pass |
| stuff | 50.3 | 9.9 | 60.1 | 51.7 | 45.1 | pass |
| control | 50.5 | 10.0 | 59.6 | 54.1 | 49.8 | pass |
| movement | 50.0 | 10.0 | 53.0 | 49.5 | 46.3 | pass |
| stamina | 52.0 | 10.0 | 50.4 | 49.9 | 50.2 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): GR. Mour | Heanaison Bluejays (p4) | regular | Contact 67, Gap 80, Power 77, Eye 40, Avoid K 56, Speed — | 56 G, 288 PA, 0.395/0.448/0.923, 36 HR, 7.3% BB, 15.6% K |
| Median mid-major regular: BR. Vaim | Caclym Bluejays (mid) | regular | Contact 38, Gap 58, Power 43, Eye 46, Avoid K 58, Speed — | 35 G, 142 PA, 0.284/0.390/0.431, 2 HR, 11.3% BB, 20.4% K |
| Median low-tier regular: H. Zalair | Fail Stags (low) | regular | Contact 46, Gap 71, Power 54, Eye 42, Avoid K 53, Speed — | 53 G, 250 PA, 0.272/0.361/0.419, 6 HR, 9.6% BB, 12.0% K |
| Home-run leader: GR. Mour | Heanaison Bluejays (p4) | regular | Contact 67, Gap 80, Power 77, Eye 40, Avoid K 56, Speed — | 56 G, 288 PA, 0.395/0.448/0.923, 36 HR, 7.3% BB, 15.6% K |
| Highest true Contact, qualified: K. Zuns | Huthoux Cardinals (p4) | regular | Contact 80, Gap 57, Power 79, Eye 52, Avoid K 40, Speed — | 55 G, 276 PA, 0.297/0.385/0.636, 23 HR, 10.9% BB, 30.1% K |
| Bench player with most PA: R. Thilins | Staweafield Ospreys (low) | bench | Contact 40, Gap 44, Power 43, Eye 63, Avoid K 60, Speed — | 31 G, 143 PA, 0.308/0.401/0.358, 1 HR, 13.3% BB, 15.4% K |
| Best P4 weekend starter (ERA, qualified): D. Lir | Shypult Highlanders (p4) | sp_weekend | Stuff 66, Control 68, Movement 67, Stamina 57 | 14 G, 14 GS, 90.2 IP, 1.19 ERA, 10.8 K/9, 2.1 BB/9, 0.4 HR/9 |
| Median mid-major weekend starter: CL. Louck | Cleduwell Owls (mid) | sp_weekend | Stuff 42, Control 55, Movement 54, Stamina 43 | 12 G, 12 GS, 59.2 IP, 4.98 ERA, 5.0 K/9, 2.6 BB/9, 1.1 HR/9 |
| Low-tier reliever with most innings: K. Claishuns | Keley Kestrels (low) | rp | Stuff 38, Control 44, Movement 38, Stamina 73 | 47 G, 1 GS, 104.1 IP, 10.18 ERA, 7.3 K/9, 5.3 BB/9, 1.7 HR/9 |
| Starter with the highest true Stamina: S. Zaisaiton | Kuton Sailors (low) | sp_weekend | Stuff 41, Control 45, Movement 37, Stamina 78 | 8 G, 8 GS, 46.1 IP, 7.19 ERA, 7.0 K/9, 4.5 BB/9, 0.6 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2313 | 0.969 ± 0.049 | 0.15 ± 0.14 | 7.16 / 7.23 | 0.992 ± 0.035 | 0.41 |
| gap | 2155 | 0.989 ± 0.044 | -0.02 ± 0.16 | 7.66 / 7.65 | 1.002 ± 0.022 | 0.42 |
| power | 2452 | 0.989 ± 0.022 | -0.15 ± 0.12 | 5.49 / 5.50 | 0.999 ± 0.022 | 0.69 |
| eye | 2452 | 0.991 ± 0.036 | 0.06 ± 0.05 | 5.75 / 5.73 | 1.003 ± 0.019 | 0.65 |
| avoid_k | 2452 | 1.006 ± 0.006 | 0.02 ± 0.03 | 4.24 / 4.23 | 1.001 ± 0.011 | 0.80 |
| stuff | 2259 | 1.007 ± 0.013 | 0.09 ± 0.05 | 3.76 / 3.71 | 1.015 ± 0.026 | 0.85 |
| control | 2259 | 0.998 ± 0.017 | 0.20 ± 0.06 | 4.75 / 4.77 | 0.997 ± 0.018 | 0.77 |
| movement | 2259 | 0.963 ± 0.044 | 0.31 ± 0.03 | 7.81 / 7.73 | 1.011 ± 0.023 | 0.39 |
| stamina | 3878 | 1.003 ± 0.008 | -0.02 ± 0.05 | 4.25 / 4.26 | 0.998 ± 0.009 | 0.82 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

