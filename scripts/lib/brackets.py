"""Shared helpers for the published brackets (data/ncaa_brackets) and the scoreboard feed by season."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SEASONS = ("2015", "2016", "2017", "2018", "2019", "2021", "2022", "2023", "2024", "2025")
# feed spellings that differ from the bracket names beyond the general rules below (older feeds)
FEED_ALIASES = {"NC State": ("North Carolina St.",), "Cal State Bakersfield": ("Bakersfield", "CSU Bakersfield"),
                "Coastal Carolina": ("Coastal Caro.",), "South Alabama": ("South Ala.",), "Saint Mary's (CA)": ("St. Mary's (CA)",),
                "Loyola Marymount": ("LMU",), "Miami (FL)": ("Miami (Fla.)",), "Southern": ("Southern Univ.",),
                "UC Santa Barbara": ("UC Santa Barb.",), "Central Connecticut": ("Cent. Conn. St.",), "Central Connecticut State": ("Cent. Conn. St.",),
                "UIC": ("Ill.-Chicago",), "LIU Brooklyn": ("Long Island",)}


def brackets() -> dict:
    return json.loads((ROOT / "data/ncaa_brackets/brackets_2015_2025.json").read_text())["seasons"]


def name_map() -> dict:
    return {r["bracket_name"]: r["scoreboard_name_2025"] for r in csv.DictReader(open(ROOT / "data/ncaa_brackets/team_name_map.csv"))}


def tiers() -> dict:
    t = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    return dict(zip(t.team, t.tier))


def tier_of(team: str, tier: dict, m: dict) -> str:
    """2025 tier of a bracket team (conference realignment aside, the program's 2025 conference)."""
    if team in tier:
        return tier[team]
    n = m.get(team) or team.replace("–", "-").replace(" State", " St.")
    return tier.get(n, "low")


def feed_games(season: str) -> pd.DataFrame:
    d = pd.read_csv(ROOT / f"data/ncaa_{season}/scoreboard/games_{season}.csv")
    d["date"] = pd.to_datetime(d.date)
    d["home"], d["away"] = d.home.astype(str).str.strip(), d.away.astype(str).str.strip()   # 2019 has trailing spaces
    return d


def feed_name(team: str, feed, m: dict) -> str | None:
    """The feed's spelling of a bracket team. feed: the season's team names, or {name: entries}; with
    counts the spelling with the most entries wins (older feeds spell a team one way in the regular
    season, e.g. "San Diego St.", and another in a few postseason entries, "San Diego State")."""
    base = m.get(team) or team.replace("–", "-")
    cands = [c for c in dict.fromkeys((team, base, base.replace(" State", " St."), team.replace(" State", " St."),
                                       *FEED_ALIASES.get(team, ()))) if c in feed]
    if not cands:
        return None
    return max(cands, key=lambda c: feed[c]) if isinstance(feed, dict) else cands[0]


def feed_counts(d: pd.DataFrame) -> dict:
    return pd.concat([d.home, d.away]).value_counts().to_dict()
