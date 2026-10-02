# True-talent shapes (deconvolution of the 2025 play-by-play)

Built 2026-10-02 by `scripts/build_talent_shapes.py`. For each side and rate, the individual true-talent distribution (logit offset from the player's tier expectation and his team's shrunk effect, in units of the method-of-moments SD of his role group) is fitted by deconvolution: the binomial likelihood of each player-season integrated over the distribution. Fits: the Gaussian, the sinh-arcsinh family (skew eps, tail weight delta; eps 0 and delta 1 is the Gaussian), and the NPMLE (nonparametric, the likelihood's upper bound). LRT: 2 × (log-likelihood sinh-arcsinh − Gaussian), 2 degrees of freedom; a shape is used when LRT > 13.82 (p < .001). Tails: quantiles of the standardized fitted shape (Gaussian: q.001 −3.09, q.01 −2.33, q.99 +2.33, q.999 +3.09). sd/MoM: SD of the fitted distribution over the method-of-moments SD.

| Side | Rate | Players | eps | delta | LRT | NPMLE − SHASH log-lik | sd/MoM | q.001 | q.01 | q.99 | q.999 | Drawn as |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| batters | K/PA | 684 | -0.47 | 1.16 | 11.9 | 1.7 | 1.00 | -3.47 | -2.61 | +1.84 | +2.27 | Gaussian |
| batters | BB/PA | 684 | -0.18 | 1.44 | 1.3 | 1.4 | 0.96 | -2.85 | -2.26 | +2.06 | +2.54 | Gaussian |
| batters | HBP/PA | 684 | -0.11 | 1.55 | 1.9 | 3.1 | 0.93 | -2.73 | -2.19 | +2.08 | +2.56 | Gaussian |
| batters | HR/PA | 684 | -1.66 | 1.07 | 27.7 | 1.0 | 1.28 | -4.34 | -3.11 | +1.21 | +1.31 | **fitted shape** |
| batters | BABIP | 468 | -8.55 | 1.40 | 1.0 | 0.1 | 0.94 | -3.86 | -2.89 | +1.27 | +1.36 | Gaussian |
| batters | XBH share of hits | 462 | -0.65 | 0.82 | 2.4 | 0.2 | 1.01 | -4.76 | -3.24 | +1.46 | +1.79 | Gaussian |
| pitchers | K/PA | 760 | +33.99 | 4.11 | 4.7 | 1.6 | 0.94 | -1.93 | -1.71 | +2.28 | +2.78 | Gaussian |
| pitchers | BB/PA | 760 | +0.13 | 0.77 | 4.5 | 2.6 | 0.93 | -3.16 | -2.26 | +2.76 | +4.01 | Gaussian |
| pitchers | HBP/PA | 760 | +17.72 | 3.88 | 2.4 | 0.8 | 0.85 | -1.91 | -1.70 | +2.30 | +2.81 | Gaussian |
| pitchers | HR/PA | 760 | -8.34 | 2.14 | 0.2 | 0.1 | 0.67 | -3.26 | -2.57 | +1.49 | +1.63 | Gaussian |
| pitchers | BABIP | 573 | -0.50 | 1.49 | 0.0 | -0.0 | 0.00 | -3.05 | -2.39 | +1.89 | +2.27 | Gaussian |

Rates drawn from a fitted shape: bat_HR. Those are drawn from the whole fitted distribution (location, scale and shape) through a Gaussian copula on the play-by-play correlations (engine/league.py); every other rate keeps the method-of-moments Gaussian. Fits whose eps and delta run to large values (eps above 5) sit on a flat likelihood: the data do not distinguish them from the Gaussian (LRT near 0).

- bat_HR: sinh-arcsinh eps -1.659, delta 1.069; location -0.421 and scale 1.281 in method-of-moments SD units. The NPMLE puts no mass above +0.85 SD units (the fitted shape's 99.9th percentile: +1.26).
