"""Write the Phase 2 blocks of benchmarks.json from the derived Phase 2 files.

Reads data/ncaa_2025/derived/phase2_inputs_2025.json (scripts/build_phase2_benchmarks.py)
and phase2_gate_2025.json (scripts/build_phase2_gate.py). Adds player_talent_2025,
team_strength_2025, usage_2025, qualified_players_2025, leaderboards_2025, and a
sampling-error tolerance for game_structure.run_rule_freq (it had none). Existing
values are not changed; every change is recorded in data/ncaa_2025/derived/benchmark_changes_phase2.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

D = Path("data/ncaa_2025/derived")
BENCH = Path("benchmarks.json")


def main() -> None:
    inp = json.loads((D / "phase2_inputs_2025.json").read_text())
    gate = json.loads((D / "phase2_gate_2025.json").read_text())
    b = json.loads(BENCH.read_text())
    changes = []

    def setv(path, new):
        cur = b
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        changes.append({"path": ".".join(path), "old": cur.get(path[-1]), "new": new})
        cur[path[-1]] = new

    meta = inp["_meta"]
    tal = {}
    for side in ("batter", "pitcher"):
        tal[side] = {}
        for rate, e in inp["talent"][side].items():
            tal[side][rate] = {"sd_team_logit": e["sd_team_logit"],
                               "groups": {g: {"mu_logit": v["mu_logit"], "sd_ind_logit": v["sd_ind_logit"], "sd_total_true_logit": v["sd_total_true_logit"], "n_players": v["n_players"]}
                                          for g, v in e["groups"].items()}}
    setv(["player_talent_2025"], {
        "_note": (f"True-talent distributions on the logit scale, from {meta['src']}. logit rate = logit L + mu_group + T_tier + U_team + e_player. "
                  "Binomial noise removed by method of moments (observed variance of rate minus tier-cell expectation, less the mean q(1-q)/n); "
                  "team vs individual split from team means of full-season teams (var_team_mean = var_U + var_e / k_eff). Rates: K, BB, HBP, HR per PA; "
                  "BABIP = hits / non-HR balls in play excluding reached-on-error; XBH = (2B+3B)/(1B+2B+3B). Pitcher XBH is not modeled (hit-type mix attributed to the batter). "
                  "Bias: the play-by-play holds only WMT client schools' games; full-season teams are "
                  f"{meta['full_season_teams_by_tier']} by tier against a D1 mix of 21% P4, 50% mid, 29% low, so team-level variances and the individual spreads rest mostly on P4 rosters. "
                  "Tier effects are fitted from all 9 batting x pitching tier cells, which every tier enters, and are less exposed. Midweek-starter estimates rest on 25 pitchers."),
        "conf": "B", "n_full_season_teams": meta["full_season_teams"], "full_season_teams_by_tier": meta["full_season_teams_by_tier"],
        "tier_effects_logit": {r: {"bat": v["bat"], "pit": v["pit"]} for r, v in inp["tier_effects_logit"].items()},
        "batter": tal["batter"], "pitcher": tal["pitcher"], "correlation": inp["correlation"],
        "groups_defined": {"regular": "top 9 by PA on the team", "bench": "rest", "sp_weekend": "starts in >=50% of appearances, >=50% of starts Fri-Sun",
                           "sp_midweek": "starts in >=50% of appearances, mostly Mon-Thu", "rp": "the rest"},
    })
    ts = gate["team_strength_2025"]
    ts["home_win_pct"] = gate["schedule_mix"]["home_win_pct"]
    setv(["team_strength_2025"], ts)
    u = inp["usage"]
    setv(["usage_2025"], {
        "_note": f"Pitcher and lineup usage from {u['_src']}. Full hazard tables (starter and reliever pull probability by outing pitch count, runs allowed and inning end) and pitches-per-PA distributions are in data/ncaa_2025/derived/phase2_inputs_2025.json.",
        "conf": "B", "starter_summary": u["starter_summary"], "starter_bf_share": u["starter_bf_share"], "pitchers_per_team_game": u["pitchers_per_team_game"],
        "batters_per_team_game": u["batters_per_team_game"], "earned_run_share": u["earned_run_share"],
        "batter_start_share_by_rank": u["batter_start_share_by_rank"], "reliever_bf_share_by_rank": u["reliever_bf_share_by_rank"],
        "pitchers_50ip_per_team": {"value": round(b["pitching_distribution_2025"]["pitchers_50ip"] / 303, 2), "note": "FanGraphs 882 / 303 teams; WMT full-season teams give 2.90"},
    })
    setv(["qualified_players_2025"], gate["qualified_players_2025"])
    setv(["leaderboards_2025"], gate["leaderboards_2025"])
    rr = b["game_structure"]["run_rule_freq"]
    if "tol" not in rr:
        pb, pe = rr["p_margin_10plus_season"], rr["p_ended_early_given_margin_10plus_wmt"]
        n_big = round(pb * b["game_structure"]["extra_innings_freq"]["n_games"])
        var = pe ** 2 * pb * (1 - pb) / b["game_structure"]["run_distribution_per_team_game"]["n_games"] + pb ** 2 * pe * (1 - pe) / n_big
        new = dict(rr); new["tol"] = round(3 * math.sqrt(var), 4)
        new["tol_note"] = "3 SE of the product estimator (scoreboard share of 10-run margins x WMT conditional share ended early)"
        setv(["game_structure", "run_rule_freq"], new)
    BENCH.write_text(dumps_compact(b) + "\n")
    (D / "benchmark_changes_phase2.json").write_text(json.dumps(changes, indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
