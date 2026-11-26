"""Phase 8 constants: roster rules (the container). Plan: plans/phase8_plan_2026-11-26.md; yardstick:
benchmarks_phase8_11.json, PHASE8_NOTES.md. Anything not traced there is marked # GUESS and listed in GUESSES.md.

Individual bench batters (owner decision 2026-11-26, "every player is an individual"). The Phase 2 talent fit
(scripts/build_phase2_benchmarks.py: method of moments on player-season rates) leaves the individual spread of bench
batters unidentified for three rates: with their few plate appearances the observed variance is no larger than the
binomial noise, so the estimate is 0 for BABIP and the extra-base share and .089 for HR, against .098, .225 and .456
for regulars. The engine then drew eight bench batters per team with the same Contact and Gap and nearly the same Power.
From Phase 8 on a bench batter is a future regular and a pinch-hitting choice, so he needs his own talent: for those
rates a bench batter's individual SD is the regulars' (the mean stays the bench group's own fitted mean). The fitted
values are kept beside the ones used (`sd_ind_logit_fitted`).
"""
from __future__ import annotations

import copy

FEATURES = {"individual_bench": True}

# Rates for which a bench batter's individual SD is taken from the regulars' fit.
BENCH_SD_FROM_REGULARS = ("HR", "BABIP", "XBH")     # GUESS (the bench spread is not identified by the data; grade C)


def on(feature: str) -> bool:
    return bool(FEATURES.get(feature))


def individual_bench(talent: dict) -> dict:
    """The talent table with the bench batters' individual SDs of BENCH_SD_FROM_REGULARS replaced by the regulars'
    (a copy; the input is untouched). With the feature off, the table as fitted."""
    if not on("individual_bench"):
        return talent
    out = copy.deepcopy(talent)
    for r in BENCH_SD_FROM_REGULARS:
        g = out["batter"][r]["groups"]
        g["bench"]["sd_ind_logit_fitted"] = g["bench"]["sd_ind_logit"]
        g["bench"]["sd_ind_logit"] = g["regular"]["sd_ind_logit"]
    return out
