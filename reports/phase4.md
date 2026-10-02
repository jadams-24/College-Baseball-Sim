# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-02.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2300 | +0.0020 ± 0.0032 | +0.15 | pass | 0.983 ± 0.039 | pass | 1.002 ± 0.031 | pass |
| gap | XBH share of hits | 2150 | -0.0000 ± 0.0071 | -0.00 | pass | 1.005 ± 0.023 | pass | 0.994 ± 0.030 | pass |
| power | HR/PA | 2448 | +0.0010 ± 0.0070 | +0.02 | pass | 1.002 ± 0.010 | pass | 0.997 ± 0.028 | pass |
| eye | BB/PA | 2448 | -0.0004 ± 0.0035 | -0.01 | pass | 1.007 ± 0.021 | pass | 1.000 ± 0.022 | pass |
| avoid_k | K/PA | 2448 | +0.0000 ± 0.0024 | +0.00 | pass | 1.003 ± 0.010 | pass | 1.008 ± 0.031 | pass |
| stuff | K/BF | 1819 | -0.0014 ± 0.0039 | -0.03 | pass | 0.998 ± 0.008 | pass | 1.011 ± 0.037 | pass |
| control | BB/BF | 1819 | -0.0011 ± 0.0035 | -0.03 | pass | 1.005 ± 0.014 | pass | 1.003 ± 0.046 | pass |
| movement | HR/BF | 1819 | -0.0036 ± 0.0091 | -0.12 | pass | 0.994 ± 0.021 | pass | 0.978 ± 0.015 | FAIL |
| stamina | pull hazard (log leash) | 4200 | -0.0014 ± 0.0049 | — | pass | 0.970 ± 0.008 | FAIL | 1.008 ± 0.031 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0022 / 0.993 / 0.990 | +0.0009 / 0.976 / 0.996 | +0.0058 † / 0.952 / 1.014 |
| gap | plate appearances | -0.0007 / 0.997 / 0.999 | +0.0000 / 1.006 / 0.990 | +0.0004 / 1.009 / 0.994 |
| power | plate appearances | -0.0049 / 0.999 / 0.988 | +0.0051 / 1.005 / 1.003 | +0.0011 / 0.999 / 0.997 |
| eye | plate appearances | -0.0040 / 0.999 / 0.985 | +0.0026 / 1.001 / 1.004 | -0.0004 / 1.015 / 1.007 |
| avoid_k | plate appearances | +0.0032 / 1.002 / 1.011 | -0.0025 / 1.000 / 1.006 | -0.0001 / 1.006 / 1.008 |
| stuff | batters faced | -0.0020 / 0.998 / 1.009 | -0.0005 / 1.001 / 1.003 | -0.0016 / 0.997 / 1.018 |
| control | batters faced | +0.0011 / 1.008 / 1.015 | +0.0047 / 0.998 / 1.002 | -0.0072 † / 1.000 / 0.996 |
| movement | batters faced | -0.0058 / 0.997 / 0.971 | +0.0006 / 0.986 / 0.992 | -0.0056 † / 0.998 / 0.971 † |
| stamina | appearances | -0.0097 † / 0.969 † / 1.022 | -0.0082 † / 0.954 † / 0.991 | +0.0065 / 0.977 † / 1.014 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.936 | 1.045 |
| gap | 0.980 | 1.015 |
| power | 0.931 | 1.205 |
| eye | 1.019 | 1.067 |
| avoid_k | 0.978 | 1.146 |
| stuff | 1.027 | 1.221 |
| control | 1.008 | 1.052 |
| movement | 1.036 | 1.126 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.8 | 57.6 | 51.3 | 46.1 | pass |
| gap | 49.6 | 9.9 | 55.6 | 50.7 | 46.4 | pass |
| power | 49.5 | 9.7 | 57.0 | 49.5 | 44.1 | pass |
| eye | 49.9 | 9.9 | 54.9 | 49.9 | 45.9 | pass |
| avoid_k | 49.7 | 9.9 | 56.1 | 51.0 | 46.5 | pass |
| stuff | 50.1 | 9.4 | 58.9 | 51.2 | 45.0 | pass |
| control | 50.8 | 9.5 | 58.6 | 53.4 | 49.5 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.2 | 46.7 | pass |
| stamina | 51.7 | 10.0 | 50.0 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): T. Hakung | Traijeax Owls (p4) | regular | Contact 50, Gap 63, Power 66, Eye 47, Avoid K 56, Speed 50 | 41 G, 171 PA, 0.370/0.471/0.790, 15 HR, 12.3% BB, 17.5% K |
| Median mid-major regular: J. Broux | Tutrouson Sentinels (mid) | regular | Contact 58, Gap 51, Power 48, Eye 47, Avoid K 52, Speed 68 | 51 G, 215 PA, 0.312/0.371/0.450, 5 HR, 7.9% BB, 22.3% K |
| Median low-tier regular: D. Zaing | Lealyck Pioneers (low) | regular | Contact 48, Gap 58, Power 45, Eye 61, Avoid K 32, Speed 57 | 53 G, 224 PA, 0.294/0.389/0.417, 3 HR, 11.6% BB, 25.9% K |
| Home-run leader: D. Guwell | Traiveng Badgers (p4) | regular | Contact 77, Gap 49, Power 80, Eye 60, Avoid K 56, Speed 62 | 55 G, 258 PA, 0.342/0.414/0.761, 27 HR, 10.5% BB, 20.5% K |
| Highest true Contact, qualified: D. Tron | Traiveng Badgers (p4) | regular | Contact 80, Gap 51, Power 74, Eye 61, Avoid K 46, Speed 55 | 53 G, 239 PA, 0.316/0.429/0.536, 7 HR, 13.8% BB, 25.1% K |
| Bench player with most PA: Z. Clis | Claiford Cardinals (mid) | bench | Contact 38, Gap 43, Power 46, Eye 38, Avoid K 42, Speed 53 | 44 G, 140 PA, 0.248/0.312/0.336, 2 HR, 6.4% BB, 18.6% K |
| Best P4 weekend starter (ERA, qualified): W. Stobraley | Kamut Clippers (p4) | sp_weekend | Stuff 80, Control 60, Movement 65, Stamina 62 | 14 G, 13 GS, 79.1 IP, 1.25 ERA, 15.5 K/9, 2.5 BB/9, 0.2 HR/9 |
| Median mid-major weekend starter: CL. Wiclealt | Pealt Cardinals (mid) | sp_weekend | Stuff 48, Control 59, Movement 58, Stamina 53 | 14 G, 14 GS, 77.1 IP, 5.12 ERA, 6.5 K/9, 2.6 BB/9, 0.9 HR/9 |
| Low-tier reliever with most innings: C. Shysox | Stais Sentinels (low) | rp | Stuff 68, Control 54, Movement 60, Stamina 58 | 23 G, 2 GS, 60.0 IP, 2.70 ERA, 12.6 K/9, 2.5 BB/9, 0.3 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 52, Control 68, Movement 45, Stamina 79 | 11 G, 11 GS, 77.1 IP, 2.91 ERA, 7.7 K/9, 1.4 BB/9, 0.7 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2299 | 1.068 ± 0.073 | 0.00 ± 0.14 | 7.26 / 6.97 | 1.042 ± 0.041 | 0.36 |
| gap | 2150 | 1.043 ± 0.041 | -0.47 ± 0.10 | 7.77 / 7.57 | 1.027 ± 0.035 | 0.39 |
| power | 2448 | 1.047 ± 0.033 | 0.10 ± 0.12 | 6.29 / 5.34 | 1.176 ± 0.025 | 0.59 |
| eye | 2448 | 0.952 ± 0.023 | 0.14 ± 0.08 | 5.85 / 5.87 | 0.997 ± 0.021 | 0.66 |
| avoid_k | 2448 | 0.996 ± 0.015 | 0.02 ± 0.03 | 4.55 / 4.33 | 1.049 ± 0.015 | 0.78 |
| stuff | 1818 | 0.948 ± 0.008 | 0.31 ± 0.08 | 3.81 / 3.65 | 1.043 ± 0.026 | 0.88 |
| control | 1818 | 0.969 ± 0.027 | 0.46 ± 0.08 | 4.89 / 4.82 | 1.015 ± 0.012 | 0.72 |
| movement | 1818 | 0.780 ± 0.022 | 0.90 ± 0.10 | 7.82 / 8.57 | 0.913 ± 0.010 | 0.46 |
| stamina | 4200 | 1.029 ± 0.012 | -0.03 ± 0.11 | 4.59 / 4.40 | 1.044 ± 0.010 | 0.77 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

