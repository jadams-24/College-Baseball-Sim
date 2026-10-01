"""Empirical Bayes on a grid: the noise removal shared by the real-data estimates and the
Phase 4 round trip.

Each unit i (a player, a pitcher's leash) has a latent offset z_i with prior N(mu, tau^2)
inside its group. The data likelihood L_i(z) is exact (binomial for rates, discrete-time
proportional hazards for pulls). mu and tau are fitted by marginal maximum likelihood on a
fixed grid of z, then each unit gets its posterior mean and SD. Posterior means are
calibrated: E[true | estimate] = estimate when the model holds, which is what the round
trip checks.
"""
from __future__ import annotations

import numpy as np

from config.phase4 import EB_GOLDEN_ITERS as GOLDEN_ITERS
from config.phase4 import EB_GRID_HALF_WIDTH, EB_GRID_POINTS, EB_MU_STEPS as MU_STEPS, EB_OUTER_ITERS as OUTER_ITERS, EB_TAU_START_MIN
from config.phase4 import EB_FIT_MAX_UNITS as FIT_MAX_UNITS
from config.phase4 import EB_QUAD_NODES as QUAD_NODES

GRID = np.linspace(-EB_GRID_HALF_WIDTH, EB_GRID_HALF_WIDTH, EB_GRID_POINTS)   # latent offset grid
EM_TOL = 1e-7
TAU_FLOOR = 1e-3


def _log_prior(mu: float, tau: float) -> np.ndarray:
    """Normal prior discretised on the grid and renormalised (exact even when tau < grid step)."""
    lp = -((GRID - mu) / tau) ** 2 / 2
    return lp - np.logaddexp.reduce(lp)


def _posterior(loglik: np.ndarray, mu: float, tau: float):
    lp = loglik + _log_prior(mu, tau)
    mx = lp.max(axis=1, keepdims=True)
    w = np.exp(lp - mx)
    tot = w.sum(axis=1, keepdims=True)
    w /= tot
    m = w @ GRID
    v = w @ GRID ** 2 - m ** 2
    return m, np.maximum(v, 0), float((np.log(tot) + mx).sum())


def _golden(f, lo: float, hi: float, iters: int) -> float:
    g = (np.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(iters):
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    return (a + b) / 2


def fit(loglik: np.ndarray, groups: np.ndarray, tau_groups: np.ndarray | None = None) -> dict:
    """loglik: (n_units, len(GRID)) log-likelihood of each unit's data at each grid value.
    groups: (n_units,) labels with their own prior mean; tau_groups: labels sharing one prior
    SD (default: each group its own). Priors N(mu_g, tau_t^2) maximise the marginal likelihood:
    golden-section search on log tau (summed over the groups sharing it), exact EM steps for
    each mu. With few trials per unit the likelihood in tau is flat, so sharing tau across
    groups that differ only in level (tiers within a role) is what pins it down.
    Returns posterior mean/sd per unit and the priors."""
    tau_groups = groups if tau_groups is None else tau_groups
    post_m = np.zeros(len(loglik))
    post_s = np.zeros(len(loglik))
    prior = {}
    rng = np.random.default_rng(0)
    for tg in np.unique(tau_groups):
        members = [g for g in np.unique(groups[tau_groups == tg])]
        idxs = {g: np.where((groups == g) & (tau_groups == tg))[0] for g in members}
        # the prior search runs on at most FIT_MAX_UNITS units per group (a fixed random subsample);
        # every unit then gets its posterior under the fitted prior
        sub = {g: (i if len(i) <= FIT_MAX_UNITS else np.sort(rng.choice(i, FIT_MAX_UNITS, replace=False))) for g, i in idxs.items()}
        lls = {g: loglik[i] for g, i in sub.items()}
        mus = {g: float(np.median(GRID[np.argmax(lls[g], axis=1)])) for g in members}
        tau = EB_TAU_START_MIN
        for _ in range(OUTER_ITERS):
            tau = float(np.exp(_golden(lambda lt: sum(_posterior(lls[g], mus[g], np.exp(lt))[2] for g in members),
                                       np.log(TAU_FLOOR), np.log(EB_GRID_HALF_WIDTH / 2), GOLDEN_ITERS)))
            for g in members:
                for _ in range(MU_STEPS):
                    mu_new = float(_posterior(lls[g], mus[g], tau)[0].mean())
                    done = abs(mu_new - mus[g]) < EM_TOL
                    mus[g] = mu_new
                    if done:
                        break
        for g in members:
            m, v, _ = _posterior(loglik[idxs[g]], mus[g], tau)
            post_m[idxs[g]], post_s[idxs[g]] = m, np.sqrt(v)
            prior[g] = {"mu": mus[g], "tau": tau, "n": int(len(idxs[g]))}
    return {"mean": post_m, "sd": post_s, "prior": prior}


def binomial_loglik(x: np.ndarray, n: np.ndarray, base_logit: np.ndarray) -> np.ndarray:
    """x successes in n trials with logit p = base_logit + z, on the grid."""
    eta = base_logit[:, None] + GRID[None, :]
    return x[:, None] * -np.logaddexp(0, -eta) + (n - x)[:, None] * -np.logaddexp(0, eta)


def binomial_mix_loglik(x: np.ndarray, n: np.ndarray, m: np.ndarray, v: np.ndarray) -> np.ndarray:
    """x successes in n trials whose logits are base + z with base ~ N(m, v) across the trials
    (opponents differ): p(z) = E[expit(base + z)] by Gauss-Hermite quadrature. Matching the
    expected count at every z gets the count's sensitivity to z right; a single average base
    would understate it (Jensen) and compress the estimates."""
    nodes, weights = np.polynomial.hermite_e.hermegauss(QUAD_NODES)
    weights = weights / weights.sum()
    p = np.zeros((len(x), len(GRID)))
    for t, w in zip(nodes, weights):
        p += w / (1 + np.exp(-(m[:, None] + np.sqrt(v)[:, None] * t + GRID[None, :])))
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return x[:, None] * np.log(p) + (n - x)[:, None] * np.log1p(-p)


def hazard_loglik(sum_log_survive: np.ndarray, pull_hazards: list) -> np.ndarray:
    """Discrete-time proportional hazards: at each pull decision the pitcher is pulled with
    h' = 1 - (1 - h)^theta, theta = exp(z). sum_log_survive = sum of log(1 - h) over the
    decisions where he stayed; pull_hazards[i] = baseline h at each decision where he was pulled."""
    theta = np.exp(GRID)
    ll = sum_log_survive[:, None] * theta[None, :]
    for i, hs in enumerate(pull_hazards):
        for h in hs:
            s = np.log1p(-min(h, 1 - 1e-9))
            ll[i] += np.log(-np.expm1(theta * s))
    return ll
