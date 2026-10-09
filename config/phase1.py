"""Phase 1 constants. Every number here traces to benchmarks.json or to a derived
table under data/ncaa_2025/derived/ whose provenance is recorded in
PHASE0_NOTES.md. Anything that does not is marked # GUESS and listed in
GUESSES.md. Nothing in engine/ may hold a literal rate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks.json"
ENGINE_TABLES = ROOT / "data/ncaa_2025/derived/engine_tables_2025.json"
RUN_RULE_SOLVED = ROOT / "data/ncaa_2025/derived/run_rule_in_effect_2025.json"

# Batter-result classes of the single outcome table, in a fixed order so that the
# categorical draw is reproducible across runs and platforms.
RESULTS = ("K", "BB", "HBP", "1B", "2B", "3B", "HR", "SF", "SH", "IP_OUT", "ROE", "FC")
# SF, SH and FC are balls in play (not hits, not errors) whose definition depends on
# the base-out state: a sacrifice fly needs a runner on third, a fielder's choice
# needs a runner to retire. The engine draws the in-play class (IP_OUT + SF + SH + FC)
# from the table and picks the subtype from the empirical conditional for the state.
IN_PLAY_OUT_CLASS = ("IP_OUT", "SF", "SH", "FC")
# Non-PA base running events sampled before each plate appearance.
PRE_PA_EVENTS = ("SB_ATT", "WP", "PB", "PO", "BK", "OTHER")
# Minimum observations for a joint advancement cell before falling back to the
# cell pooled over outs, then to independent per-runner marginals.
MIN_CELL_N = 30  # GUESS (statistical threshold, not a baseball rate)


@dataclass(frozen=True)
class Rules:
    innings: int                      # benchmarks game_structure.innings
    run_rule_margin: int              # benchmarks game_structure.run_rule: "10 runs after 7 innings"
    run_rule_after_inning: int
    p_run_rule_in_effect: float       # solved to benchmarks game_structure.run_rule_freq.p_ended_early_given_margin_10plus
                                      # (data/ncaa_2025/derived/run_rule_in_effect_2025.json, scripts/build_run_rule.py --solve)
    extra_innings_placed_runner: bool  # benchmarks game_structure.extra_innings_tiebreaker: conference-optional, not universal


@dataclass(frozen=True)
class Phase1Config:
    outcome_probs: dict[str, float]            # benchmarks pa_outcome_table_league_avg
    pa_joint: dict                              # engine_tables pa_joint
    in_play_out_subtype: dict                   # engine_tables in_play_out_subtype
    pre_pa_events: dict                         # engine_tables pre_pa_events
    rules: Rules
    sources: dict = field(default_factory=dict)


def _p_run_rule(rr: dict) -> float:
    """The solved probability that a game is under the run rule; before the solve, the WMT share of 10-run games that ended
    early, which the engine used until 2026-10-08."""
    if RUN_RULE_SOLVED.exists():
        return float(json.loads(RUN_RULE_SOLVED.read_text())["p_run_rule_in_effect"])
    return float(rr["wmt_sample"]["p_ended_early_given_margin_10plus"])


def load() -> Phase1Config:
    b = json.loads(BENCHMARKS.read_text())
    t = json.loads(ENGINE_TABLES.read_text())
    table = b["pa_outcome_table_league_avg"]
    probs = {k: float(table[k]) for k in RESULTS}
    s = sum(probs.values())
    probs = {k: v / s for k, v in probs.items()}  # table sums to 1 within rounding; normalize exactly
    gs = b["game_structure"]
    rules = Rules(
        innings=int(gs["innings"]),
        run_rule_margin=10, run_rule_after_inning=7,  # from the text of game_structure.run_rule (conf C)
        p_run_rule_in_effect=_p_run_rule(gs["run_rule_freq"]),
        extra_innings_placed_runner=False,  # see GUESSES.md: rule is conference-optional; plain extras used
    )
    return Phase1Config(
        outcome_probs=probs, pa_joint=t["pa_joint"], in_play_out_subtype=t["in_play_out_subtype"],
        pre_pa_events=t["pre_pa_events"], rules=rules,
        sources={"outcome_table": table.get("_note"), "engine_tables": t["_meta"], "run_rule": gs["run_rule"], "tiebreaker": gs["extra_innings_tiebreaker"]},
    )
