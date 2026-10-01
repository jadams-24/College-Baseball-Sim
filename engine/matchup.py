"""Batter vs pitcher outcome probabilities by the odds-ratio (generalized log5) method.

For each rate r, logit p = logit b + logit q - logit L, where b and q are the batter's
and pitcher's true rates and L the league rate. With b = expit(logit L + zb) and
q = expit(logit L + zp) this is logit p = logit L + zb + zp (+ c, the league location).
Per-PA rates: K, BB, HBP, HR. Balls in play split into reached-on-error (league share),
hits (BABIP) and the in-play out class (IP_OUT/SF/SH/FC, subtyped by base-out state in
the engine). Hits split into extra-base (XBH, batter-driven) and singles; triples are
the league share of extra-base hits.
"""
from __future__ import annotations

import math

OUTCOMES = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")


def _expit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def matchup_probs(cfg, zb, zp, location: dict) -> dict:
    L = cfg.league_rates
    rates = ("K", "BB", "HBP", "HR", "BABIP", "XBH")
    p = {r: _expit(_logit(L[r]) + location[r] + float(zb[i]) + float(zp[i])) for i, r in enumerate(rates)}
    per_pa = p["K"] + p["BB"] + p["HBP"] + p["HR"]
    bip = 1.0 - per_pa
    roe = bip * cfg.roe_share_of_bip
    hits = (bip - roe) * p["BABIP"]
    xb = hits * p["XBH"]
    tri = xb * cfg.triple_share_of_xbh
    return {"K": p["K"], "BB": p["BB"], "HBP": p["HBP"], "HR": p["HR"], "1B": hits - xb, "2B": xb - tri, "3B": tri,
            "ROE": roe, "OUT": bip - roe - hits}
