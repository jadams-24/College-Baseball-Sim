"""Realism report: sim aggregates against benchmarks.json with tolerances."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (label, sim key, benchmark path, gate?)  gate rows are the CLAUDE.md Phase 1 gate
ROWS = [
    ("Runs per team-game", "runs_per_team_game", ("league_totals_2025", "runs_per_team_game"), True),
    ("Batting average", "ba", ("league_totals_2025", "ba"), True),
    ("On-base pct", "obp", ("league_totals_2025", "obp"), True),
    ("Slugging pct", "slg", ("league_totals_2025", "slg"), True),
    ("HR per team-game", "hr_per_team_game", ("league_totals_2025", "hr_per_team_game"), False),
    ("SB per team-game", "sb_per_team_game", ("league_totals_2025", "sb_per_team_game"), False),
    ("Errors per team-game", "errors_per_team_game", ("league_totals_2025", "errors_per_team_game"), False),
    ("Extra-innings frequency", "extra_innings_freq", ("game_structure", "extra_innings_freq"), False),
    ("BB per PA", "bb_pct", ("league_totals_2025", "bb_pct"), False),
    ("K per PA", "k_pct", ("league_totals_2025", "k_pct"), False),
    ("HBP per PA", "hbp_pct", ("league_totals_2025", "hbp_pct"), False),
    ("SH per team-game", "sh_per_team_game", ("league_totals_2025", "sh_per_team_game"), False),
    ("SF per team-game", "sf_per_team_game", ("league_totals_2025", "sf_per_team_game"), False),
    ("PA per team-game", "pa_per_team_game", ("league_totals_2025", "pa_per_team_game"), False),
    ("SB success rate", "sb_success_rate", ("league_totals_2025", "sb_success_rate"), False),
    ("Run-rule frequency", "run_rule_freq", ("game_structure", "run_rule_freq"), False),
]


def build_report(sim: dict, seed: int, bench: dict | None = None) -> tuple[str, dict]:
    bench = bench or json.loads((ROOT / "benchmarks.json").read_text())
    lines = [f"# Phase 1 realism report", "",
             f"League-average PA engine, {sim['n_games']:,} games, seed {seed}, generated {dt.date.today().isoformat()}.",
             "Gate rows are the CLAUDE.md Phase 1 gate (R/G, BA, OBP, SLG, run histogram); the rest are informational.", "",
             "| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |", "|---|---|---|---|---|---|---|"]
    status = {}
    for label, key, (blk, name), gate in ROWS:
        b = bench[blk][name]
        val, tol = b["value"], b.get("tol")
        got = sim[key]
        ok = (abs(got - val) <= tol) if tol is not None else None
        status[key] = ok
        nd = 4 if val < 1 else 2
        lines.append(f"| {label} | {got:.{nd}f} | {val:.{nd}f} | {('±' + str(tol)) if tol is not None else '—'} | {b.get('conf','?')} | {'yes' if gate else ''} | "
                     f"{'pass' if ok else ('FAIL' if ok is False else 'n/a')} |")
    # histogram
    hb = bench["game_structure"]["run_distribution_per_team_game"]
    bins, tol, tol_tvd = hb["bins"], hb["tol_per_bin"], hb["tol_total_variation"]
    tvd = sum(abs(g - b) for g, b in zip(sim["run_histogram"], bins)) / 2
    hist_ok = all(abs(g - b) <= tol for g, b in zip(sim["run_histogram"], bins)) and tvd <= tol_tvd
    status["run_histogram"] = hist_ok
    lines += ["", f"## Runs per team-game histogram (gate; ±{tol} per bin, total variation ≤ {tol_tvd})", "",
              f"Total variation distance: {tvd:.4f}  →  **{'pass' if hist_ok else 'FAIL'}**", "",
              "| Runs | Sim | Benchmark | Diff | Status |", "|---|---|---|---|---|"]
    for i, (g, b) in enumerate(zip(sim["run_histogram"], bins)):
        lines.append(f"| {i if i < 15 else '15+'} | {g:.4f} | {b:.4f} | {g-b:+.4f} | {'pass' if abs(g-b) <= tol else 'FAIL'} |")
    gate_keys = [k for _, k, _, g in ROWS if g] + ["run_histogram"]
    gate_pass = all(status[k] for k in gate_keys)
    lines += ["", f"## Gate: **{'PASS' if gate_pass else 'FAIL'}**", "",
              "## Engine diagnostics", "",
              f"- Innings distribution: {', '.join(f'{k}: {v:.4f}' for k, v in sim['innings_dist'].items())}",
              f"- Home win pct {sim['home_win_pct']:.4f}; mean margin {sim['mean_margin']:.2f}; LOB per team-game {sim['lob_per_team_game']:.2f}; ROE per team-game {sim['roe_per_team_game']:.3f}; FC per team-game {sim['fc_per_team_game']:.3f}",
              f"- CS per team-game {sim['cs_per_team_game']:.3f}",
              f"- Advancement cell use: {sim.get('advancement_fallbacks')}; runner collisions resolved by rule: {sim.get('collision_fixes')}", ""]
    return "\n".join(lines) + "\n", status
