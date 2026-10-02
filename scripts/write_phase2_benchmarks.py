"""Write the Phase 2 blocks of benchmarks.json from the derived Phase 2 files.

Reads data/ncaa_2025/derived/phase2_inputs_2025.json (scripts/build_phase2_benchmarks.py,
build_phase2_teams.py), phase2_gate_2025.json (build_phase2_gate.py, build_phase2_teams.py)
and phase2_run_scale_2025.json (build_phase2_run_scale.py). Writes player_talent_2025,
team_talent_2025, team_strength_2025, tier_matrix_2025, home_2025, usage_2025,
qualified_players_2025, leaderboards_2025, and a sampling-error tolerance for
game_structure.run_rule_freq (it had none). Values outside these Phase 2 blocks are not
changed; every write is recorded in data/ncaa_2025/derived/benchmark_changes_phase2.json.
"""
from __future__ import annotations

import datetime
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
    rs = json.loads((D / "phase2_run_scale_2025.json").read_text())
    gsc = json.loads((D / "phase2_game_scale_2025.json").read_text())["scale"]
    gate = json.loads((D / "phase2_gate_2025.json").read_text())
    # rows the project owner moved to the Phase 6 gate (PR #4 review; config.phase2.DEFERRED_TO_PHASE6)
    gate["leaderboards_2025"]["pitchers_50ip"]["gate"] = "phase6"
    gate["qualified_players_2025"]["pitchers"]["K9"]["gate_deferred"] = {"p50": "phase6", "p90": "phase6"}
    gate["tier_matrix_2025"]["matrix"]["p4"]["low"]["gate"] = "phase6"
    b = json.loads(BENCH.read_text())
    changes = []

    def setv(path, new):
        cur = b
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        if json.loads(json.dumps(cur.get(path[-1]), default=str)) != json.loads(json.dumps(new, default=str)):
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
                  "BABIP = hits / non-HR balls in play excluding reached-on-error; XBH = (2B+3B)/(1B+2B+3B). Pitcher individual XBH is not modeled (hit-type mix attributed to the batter). "
                  "Since the PR #4 review the league generator uses tier_effects_logit only for the quality directions (P4 minus low contrast) and sd_team_logit only for team style "
                  "(the part with no run value); tier means, team and conference spreads come from team_talent_2025. "
                  "Bias: the play-by-play holds only WMT client schools' games; full-season teams are "
                  f"{meta['full_season_teams_by_tier']} by tier against a D1 mix of 21% P4, 50% mid, 29% low, so team-level variances and the individual spreads rest mostly on P4 rosters. "
                  "Tier effects are fitted from all 9 batting x pitching tier cells, which every tier enters, and are less exposed. Midweek-starter estimates rest on 25 pitchers."),
        "conf": "B", "n_full_season_teams": meta["full_season_teams"], "full_season_teams_by_tier": meta["full_season_teams_by_tier"],
        "tier_effects_logit": {r: {"bat": v["bat"], "pit": v["pit"]} for r, v in inp["tier_effects_logit"].items()},
        "batter": tal["batter"], "pitcher": tal["pitcher"], "correlation": inp["correlation"],
        "groups_defined": {"regular": "top 9 by PA on the team", "bench": "rest", "sp_weekend": "starts in >=50% of appearances, >=50% of starts Fri-Sun",
                           "sp_midweek": "starts in >=50% of appearances, mostly Mon-Thu", "rp": "the rest"},
    })
    tt = inp["team_talent"]
    setv(["team_talent_2025"], {
        "_note": ("Team strength on one talent scale. Quasi-Poisson fit of runs per team-game on team offense o, run prevention d (log runs, centred over teams), the listed "
                  "home slot and (Phase 6) the listed home team's park; (o, d) = tier mean + conference effect + team effect. Estimation noise removed by method of moments using each team's covariance from the fit; "
                  "conference covariance = spread of conference means minus (team + noise)/n, per tier, projected to PSD. Hosting of nonconference games: logistic in tier pair "
                  "and strength gap, slope disattenuated for noise. Engine mapping (phase2_run_scale_2025.json): o and d become logit offsets along the batting and pitching quality "
                  "directions scaled so one unit is one log run in the engine; the home talent edge is home_log_ratio minus the engine's batting-last effect h0. " + tt["src"]),
        "conf": "A", "conf_note": "Tier means, team covariances and the home effect rest on all 306 D1 teams (conf A). Conference covariances rest on 4 (P4), 15 (mid) and 10 (low) conferences and the hosting model on 3,550 nonconference games (conf B).",
        "n_games": tt["n_games"], "n_teams": tt["n_teams"], "dispersion": tt["dispersion"], "residual_corr_within_game": tt["residual_corr_within_game"],
        # Phase 6: the fit carries a park term (the listed home team's park), so o and d are net of home parks; the
        # residual correlation and dispersion above are from the fit without it (the Phase 2 definition)
        **({"dispersion_without_parks": tt["dispersion_without_parks"], "residual_corr_within_game_with_parks": tt["residual_corr_within_game_with_parks"],
            "parks": tt["parks"]} if "parks" in tt else {}),
        "home_log_ratio": {"value": tt["home_log_ratio"], "se": tt["home_log_ratio_se"], "conf": "A"},
        "engine_home_structural_h0": rs["home_structural"]["h0_log_ratio"],
        "tiers": {t: {k: v for k, v in e.items()} for t, e in tt["tiers"].items()},
        **({"tiers_total": tt["tiers_total"]} if "tiers_total" in tt else {}),
        "conf_cov_pooled": tt["conf_cov_pooled"], "conf_sd_pooled": tt["conf_sd_pooled"],
        "hosting": {**tt["hosting"], "conf": "B"},
        "engine_scale": {"v_bat_unit": rs["v_bat_unit"], "v_pit_unit": rs["v_pit_unit"], "w_gradient_logR": rs["w_gradient_logR"], "rates": rs["rates"],
                         "linearity_quadratic_coef": rs["linearity"]["quadratic_coef"],
                         "game_map": {"offense": {"k": round(gsc["k_o"], 4), "q": round(gsc.get("q_o", 0.0), 4)},
                                      "run_prevention": {"k": round(gsc["k_d"], 4), "q": round(gsc.get("q_d", 0.0), 4)},
                                      "home_edge_engine": round(gsc["eta"], 4),
                                      "note": "engine units = k x + q x^2 of the scoreboard rating x, one map for every team; solved by scripts/solve_phase2_game_scale.py"}},
    })
    setv(["tier_matrix_2025"], gate["tier_matrix_2025"])
    setv(["home_2025"], gate["home_2025"])
    ts = gate["team_strength_2025"]
    ts["home_win_pct"] = gate["schedule_mix"]["home_win_pct"]
    setv(["team_strength_2025"], ts)
    u = inp["usage"]
    setv(["usage_2025"], {
        "_note": f"Pitcher and lineup usage from {u['_src']}. Full hazard tables (starter and reliever pull probability by outing pitch count, runs allowed and inning end) and pitches-per-PA distributions are in data/ncaa_2025/derived/phase2_inputs_2025.json.",
        "conf": "B", "starter_summary": u["starter_summary"], "starter_bf_share": u["starter_bf_share"], "pitchers_per_team_game": u["pitchers_per_team_game"],
        "batters_per_team_game": u["batters_per_team_game"], "earned_run_share": u["earned_run_share"],
        "batter_start_share_by_rank": u["batter_start_share_by_rank"], "reliever_bf_share_by_rank": u["reliever_bf_share_by_rank"],
        "weekend_start_share_by_rank": u["weekend_start_share_by_rank"], "weekend_starters_per_team": u["weekend_starters_per_team"],
        "weekend_start_note": u["weekend_start_note"], "pitcher_ip_by_team_rank": u["pitcher_ip_by_team_rank"],
        "games_per_full_season_team": u["games_per_full_season_team"],
        "pitcher_ip_split_by_team_rank": u["pitcher_ip_split_by_team_rank"], "pitcher_starts_by_team_rank": u["pitcher_starts_by_team_rank"],
        "phase6_note": "pitcher_ip_split_by_team_rank and pitcher_starts_by_team_rank are Phase 6 inputs for swingman relief and Thursday openers (CLAUDE.md, Phase 6 deferred rows).", "batter_share_hhi": u["batter_share_hhi"], "pitcher_share_hhi": u["pitcher_share_hhi"],
        "pitchers_50ip_per_team": {"value": round(b["pitching_distribution_2025"]["pitchers_50ip"] / 303, 2), "note": "FanGraphs 882 / 303 teams; WMT full-season teams give 2.90"},
    })
    setv(["qualified_players_2025"], gate["qualified_players_2025"])
    # the individual BA / HR placeholders are superseded by individual_leaders_2023_2026 (scripts/write_leader_benchmarks.py)
    setv(["leaderboards_2025"], {k: v for k, v in gate["leaderboards_2025"].items() if k not in ("individual_ba_top", "individual_hr_top")})
    rr = b["game_structure"]["run_rule_freq"]
    if "tol" not in rr:
        pb, pe = rr["p_margin_10plus_season"], rr["p_ended_early_given_margin_10plus_wmt"]
        n_big = round(pb * b["game_structure"]["extra_innings_freq"]["n_games"])
        var = pe ** 2 * pb * (1 - pb) / b["game_structure"]["run_distribution_per_team_game"]["n_games"] + pb ** 2 * pe * (1 - pe) / n_big
        new = dict(rr); new["tol"] = round(3 * math.sqrt(var), 4)
        new["tol_note"] = "3 SE of the product estimator (scoreboard share of 10-run margins x WMT conditional share ended early)"
        setv(["game_structure", "run_rule_freq"], new)
    import copy
    gs = b["game_structure"]
    rr = copy.deepcopy(gs["run_rule_freq"]); rr["gate"] = "phase6"
    setv(["game_structure", "run_rule_freq"], rr)
    rd = copy.deepcopy(gs["run_distribution_per_team_game"]); rd["gate_deferred_bins"] = {"15+": "phase6"}
    setv(["game_structure", "run_distribution_per_team_game"], rd)
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:  # append to the change record; a rerun with nothing new leaves it as is
        log = D / "benchmark_changes_phase2.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        stamp = datetime.date.today().isoformat()
        log.write_text(json.dumps(prior + [{**c, "date": stamp} for c in changes], indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
