"""Run-rule benchmark from the direct count of all D1-vs-D1 finals, and the engine's early-ending rate solved to it
(variance stage, item 1; owner decision 2026-10-07: benchmark and engine change together).

Benchmark (default mode): WarrenNolan's 2025 schedule pages (data/ncaa_2025/warrennolan/games_2025.csv) record the innings
of every final (blank = 9). A game counts as ended by the run rule when it ended before the 9th with a final margin of
10 or more; scheduled 7-inning games that also reach a 10-run margin are counted, as before. The innings are checked
against the WMT schedules on the games both sources have. 2026 (data/ncaa_2026/warrennolan/games_2026.csv) is reported
as a check, not pooled: the engine is calibrated to 2025. The game_structure.run_rule_freq block is replaced as text
(the rest of benchmarks.json is not reformatted); the old block is recorded in
data/ncaa_2025/derived/benchmark_changes_variance.json. The WMT fields of the old block are kept as recorded values.

Engine (--solve RUNS_DIR): the engine draws per game whether the rule is in effect (engine/game2.py). The share of
simulated games with a final margin of 10 or more that ended early is close to proportional to that probability (rule-off
games that lead by 10 after the 7th mostly stay at 10+), so one step p_new = p_old x target / sim gives the solve; the
40-season run that follows checks it. Reads the season checkpoints of scripts/run_phase5.py (season_metrics:
run_rule_freq and margin_10plus, every early ending in the engine being a run-rule ending) and writes
data/ncaa_2025/derived/run_rule_in_effect_2025.json, which config/phase1.py reads.
    python3 scripts/build_run_rule.py
    python3 scripts/build_run_rule.py --solve runs/<key>
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

BENCH = ROOT / "benchmarks.json"
D = ROOT / "data/ncaa_2025/derived"
SOLVED = D / "run_rule_in_effect_2025.json"
LOG = D / "benchmark_changes_variance.json"
SE_MULT = 3  # tolerance: 3 SE of the count, as the old product estimator's


def finals(year: int) -> pd.DataFrame:
    w = pd.read_csv(ROOT / f"data/ncaa_{year}/warrennolan/games_{year}.csv")
    w = w[(w.status == "final") & w.home_d1 & w.away_d1 & w.home_score.notna() & w.away_score.notna()].copy()
    w["inn"] = w.innings.fillna(9).astype(int)
    w["margin"] = (w.home_score - w.away_score).abs()
    w["early"] = w.inn < 9
    return w


def count(w: pd.DataFrame) -> dict:
    rr = (w.early & (w.margin >= 10)).mean()
    big = w.margin >= 10
    pe = float(w.early[big].mean())
    n10 = int(big.sum())
    return {"value": round(float(rr), 4), "se": round(math.sqrt(rr * (1 - rr) / len(w)), 4), "n_games": int(len(w)),
            "p_margin_10plus": round(float(big.mean()), 4),
            "p_ended_early_given_margin_10plus": round(pe, 4), "se_p_ended_early": round(math.sqrt(pe * (1 - pe) / n10), 4),
            "n_margin_10plus": n10,
            "short_game_not_run_rule_freq": round(float((w.early & ~big).mean()), 4),
            "innings_dist": {str(k): round(float(v), 4) for k, v in w.inn.clip(upper=15).value_counts(normalize=True).sort_index().items()}}


def innings_check(w: pd.DataFrame) -> dict:
    """WarrenNolan's innings against the WMT schedules' on the same games (date, both teams, both scores)."""
    nm = pd.read_csv(ROOT / "data/ncaa_2026/team_name_map.csv")
    slug = dict(zip(nm.ncaa_name, nm.warrennolan_slug))
    slug.update({"New Orleans": "New-Orleans", "Purdue Fort Wayne": "Purdue-Fort-Wayne"})
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    id2slug = {k: slug.get(v) for k, v in zip(t.ncaa_team_id, t.team)}
    sg = pd.read_csv(ROOT / "data/ncaa_2025/pbp/parsed/schedule_games_2025.csv")
    sg = sg[sg.innings.notna() & (sg.innings > 0)]
    wmt = {(r.game_date, frozenset([id2slug.get(r.home_team_id), id2slug.get(r.away_team_id)]),
            frozenset([int(r.home_score), int(r.away_score)])): int(r.innings) for r in sg.itertuples()}
    pairs = [(r.inn, wmt[k]) for r in w.itertuples()
             if (k := (r.date, frozenset([r.home_slug, r.away_slug]), frozenset([int(r.home_score), int(r.away_score)]))) in wmt]
    a = np.array(pairs)
    return {"n_matched": int(len(a)), "innings_agree": round(float((a[:, 0] == a[:, 1]).mean()), 4),
            "early_agree": round(float(((a[:, 0] < 9) == (a[:, 1] < 9)).mean()), 4)}


def block_span(text: str, key: str) -> tuple[int, int]:
    i = text.index(f'"{key}": {{')
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        depth += {"{": 1, "}": -1}.get(text[k], 0)
        if depth == 0:
            return i, k + 1
    raise ValueError(key)


def benchmark() -> None:
    c25, c26 = count(finals(2025)), count(finals(2026))
    chk = innings_check(finals(2025))
    text = BENCH.read_text()
    old = json.loads(text)["game_structure"]["run_rule_freq"]
    new = {"gate": old["gate"], "value": c25["value"], "tol": round(SE_MULT * c25["se"], 4),
           "tol_note": f"{SE_MULT} SE of the direct count (binomial on {c25['n_games']} games)",
           "conf": "A",
           "src": ("WarrenNolan 2025 schedule pages, every D1-vs-D1 final with its innings (data/ncaa_2025/warrennolan/games_2025.csv, "
                   "fetched 2026-10-05; scripts/build_run_rule.py)"),
           "note": ("Direct count (variance stage, owner decision 2026-10-07): share of D1-vs-D1 finals that ended before the 9th with a "
                    "final margin of 10 or more. Scheduled 7-inning games that also reach a 10-run margin are counted. Replaces the "
                    "product estimator (scoreboard share of 10-run margins x WMT share ended early, .1524): the WMT games end early more "
                    "often given a 10-run margin than the rest."),
           "n_games": c25["n_games"], "se": c25["se"],
           "p_margin_10plus": c25["p_margin_10plus"],
           "p_ended_early_given_margin_10plus": c25["p_ended_early_given_margin_10plus"],
           "se_p_ended_early": c25["se_p_ended_early"], "n_margin_10plus": c25["n_margin_10plus"],
           "short_game_not_run_rule_freq": c25["short_game_not_run_rule_freq"],
           "innings_dist": c25["innings_dist"],
           "innings_check_vs_wmt": chk,
           "check_2026": {k: c26[k] for k in ("value", "se", "n_games", "p_margin_10plus", "p_ended_early_given_margin_10plus", "se_p_ended_early")},
           "wmt_sample": {"p_ended_early_given_margin_10plus": old["p_ended_early_given_margin_10plus_wmt"],
                          "run_rule_freq": old["wmt_sample_run_rule_freq"], "product_estimator": old["value"]}}
    i, j = block_span(text, "run_rule_freq")
    pad = text[:i].rsplit("\n", 1)[1]
    level = len(pad) // 2
    new_text = text[:i] + '"run_rule_freq": ' + dumps_compact(new, indent=2, level=level) + text[j:]
    json.loads(new_text)
    BENCH.write_text(new_text)
    prior = json.loads(LOG.read_text()) if LOG.exists() else []
    LOG.write_text(json.dumps(prior + [{"path": "game_structure.run_rule_freq", "old": old, "new": new,
                                        "date": datetime.date.today().isoformat()}], indent=1) + "\n")
    print(json.dumps(new, indent=1))


def solve(runs: Path) -> None:
    rr, m10 = [], []
    for f in sorted(runs.glob("season_*.pkl")):
        m = pickle.loads(f.read_bytes())[0]
        rr.append(m["run_rule_freq"]); m10.append(m["margin_10plus"])
    rr, m10 = np.array(rr), np.array(m10)
    n = len(rr)
    c = float(rr.sum() / m10.sum())
    c_se = float(np.std(rr / m10, ddof=1) / math.sqrt(n))
    b = json.loads(BENCH.read_text())["game_structure"]["run_rule_freq"]
    target, t_se = b["p_ended_early_given_margin_10plus"], b["se_p_ended_early"]
    sys.path.insert(0, str(ROOT))
    from config.phase1 import load
    p_old = load().rules.p_run_rule_in_effect
    p = p_old * target / c
    out = {"p_run_rule_in_effect": round(p, 4),
           "se": round(p * math.sqrt((t_se / target) ** 2 + (c_se / c) ** 2), 4),
           "target_p_ended_early_given_margin_10plus": target, "target_se": t_se,
           "sim_p_ended_early_given_margin_10plus": round(c, 4), "sim_se": round(c_se, 4),
           "p_previous": p_old, "seasons": n, "runs": str(runs.relative_to(ROOT)) if runs.is_absolute() else str(runs),
           "sim_run_rule_freq": round(float(rr.mean()), 4), "sim_margin_10plus": round(float(m10.mean()), 4),
           "method": "one proportional step p x target / sim (scripts/build_run_rule.py --solve); the next 40-season run checks it",
           "date": datetime.date.today().isoformat()}
    SOLVED.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--solve", type=Path, default=None, help="season checkpoint directory (runs/<key>)")
    a = ap.parse_args()
    solve(a.solve) if a.solve else benchmark()
