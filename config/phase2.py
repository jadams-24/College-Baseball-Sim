"""Phase 2 constants. Rates and distributions come from benchmarks.json and
data/ncaa_2025/derived/phase2_inputs_2025.json (built by
scripts/build_phase2_benchmarks.py and scripts/build_phase2_gate.py). Roster shape
and schedule length follow the project owner's Phase 2 spec and game_structure in
benchmarks.json. Anything else is marked # GUESS and listed in GUESSES.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config import phase1

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data/ncaa_2025/derived/phase2_inputs_2025.json"
TEAMS = ROOT / "data/ncaa_2025/pbp/teams_2025.csv"
TIERS = ("p4", "mid", "low")
RATES = ("K", "BB", "HBP", "HR", "BABIP", "XBH")
PA_RATES = ("K", "BB", "HBP", "HR")

# Roster shape: owner's Phase 2 spec ("about 9 regulars plus bench, a weekend rotation
# of 3 starters, midweek starters, about 8 relievers").
N_REGULARS = 9
N_BENCH = 5
N_WEEKEND_SP = 3
N_MIDWEEK_SP = 2
N_RELIEVERS = 8

# Season: 56 games (benchmarks game_structure.regular_season_game_limit) as 14 weeks of a
# Fri-Sun series plus one midweek game; conference weekends from the scoreboard share of
# conference games (schedule_mix.conference_games_share x 56 / 3).
WEEKS = 14
GAMES_PER_WEEKEND = 3
SEASON_GAMES = 56

# Qualification for the percentile and leaderboard gates: NCAA statistics rules
# (batting: 2.0 PA per team game and 75% of team games; pitching: 1 IP per team game)
# and the FanGraphs 50-IP cut used for pitching_distribution_2025.
QUAL_PA_PER_TEAM_GAME = 2.0
QUAL_GAMES_SHARE = 0.75
QUAL_IP_PER_TEAM_GAME = 1.0
LEADERBOARD_MIN_IP = 50

# Home site of a nonconference series or midweek game: a fair coin. No home-field effect
# is modeled in Phase 2 (real home win pct .588 is reported as a diagnostic).
P_FIRST_TEAM_HOSTS = 0.5  # GUESS

# Starter/reliever choice weights and lineup start rates come from usage tables; when a
# hazard cell has fewer than this many batters faced it backs off to the coarser table.
MIN_HAZARD_N = 30  # GUESS (statistical threshold)


@dataclass(frozen=True)
class Phase2Config:
    base: phase1.Phase1Config
    league_rates: dict          # per-rate league values implied by the outcome table
    roe_share_of_bip: float     # reached on error as a share of balls in play (league)
    triple_share_of_xbh: float  # 3B / (2B + 3B) (league)
    tier_effects: dict          # logit tier effects, batting and pitching
    talent: dict                # mu / sd by side, rate and role group; team SDs
    correlation: dict           # batter and pitcher correlation matrices
    usage: dict                 # pull hazards, pitches per PA, start shares, reliever shares
    schedule_mix: dict          # nonconference opponent-tier mix by own tier and day type
    conference_weekends: int
    teams: list                 # (ncaa_team_id, conference, tier) for the real D1 structure


def load() -> Phase2Config:
    import csv
    base = phase1.load()
    inp = json.loads(INPUTS.read_text())
    t = base.outcome_probs
    hits = t["1B"] + t["2B"] + t["3B"]
    out_class = t["IP_OUT"] + t["SF"] + t["SH"] + t["FC"]
    bip_total = 1 - t["K"] - t["BB"] - t["HBP"] - t["HR"]
    league_rates = {"K": t["K"], "BB": t["BB"], "HBP": t["HBP"], "HR": t["HR"],
                    "BABIP": hits / (hits + out_class), "XBH": (t["2B"] + t["3B"]) / hits}
    teams = [(int(r["ncaa_team_id"]), r["conference"], r["tier"]) for r in csv.DictReader(TEAMS.open()) if r["tier"]]
    mix = inp["schedule_mix"]
    return Phase2Config(
        base=base, league_rates=league_rates, roe_share_of_bip=t["ROE"] / bip_total,
        triple_share_of_xbh=t["3B"] / (t["2B"] + t["3B"]),
        tier_effects=inp["tier_effects_logit"], talent=inp["talent"], correlation=inp["correlation"],
        usage=inp["usage"], schedule_mix=mix,
        conference_weekends=round(mix["conference_games_share"] * SEASON_GAMES / GAMES_PER_WEEKEND),
        teams=teams,
    )
