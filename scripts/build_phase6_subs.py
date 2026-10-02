"""Phase 6 substitution inputs from the 2025 play-by-play: pinch hitters, pinch runners and
defensive (including blowout) substitutions.

Every non-pitcher who enters a game is classified by how he first entered (subs_2025, from
scripts/build_phase6_events.py): 'ph' pinch hitter, 'pr' pinch runner, anything else (a fielding
position or dh) a defensive substitution. Hazards, by inning bin x margin bin (margin from the
substituting team's side, at the substitution):
  ph   per plate appearance of the team                 (opportunities: the team's PAs in the cell)
  pr   per batter reaching base (not on a home run)      (opportunities: such batters in the cell)
  def  per defensive half-inning of the team             (opportunities: half-innings in the field)
Cells with fewer than MIN_SUB_CELL opportunities back off to the inning bin alone.
Also: the lineup spot a pinch hitter or defensive substitute replaces (share of entries over
share of opportunities, by spot), and a tier multiplier on all three hazards (substitutions per
team-game by tier over the pooled rate, from the same cells).
Gate value: distinct batters per team-game (batters with a plate appearance).
Writes the "subs6" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/build_phase6_subs.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.phase6 import INNING_BINS, INPUTS6, MARGIN_BINS, MIN_SUB_CELL  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"


def ibin(inning) -> np.ndarray:
    return np.searchsorted(np.array(INNING_BINS), np.asarray(inning), side="right") - 1


def mbin(margin) -> np.ndarray:
    return np.searchsorted(np.array(MARGIN_BINS), np.asarray(margin), side="right") - 1


def main() -> None:
    meta = pd.read_csv(P / "games_meta_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.ncaa_team_id, teams.tier))
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False)
    pa = pa[pa.game_id.isin(meta.game_id)].copy()
    home = dict(zip(meta.game_id, meta.home_team_id))
    # the batting team's margin before the plate appearance
    bat_home = pa.bat_team_id.values == pa.game_id.map(home).values
    pa["margin"] = np.where(bat_home, pa.home_score - pa.away_score, pa.away_score - pa.home_score)
    pa["ib"], pa["mb"] = ibin(pa.inning), mbin(pa.margin)
    pa["slot"] = pa.groupby(["game_id", "bat_team_id"]).cumcount() % 9 + 1
    pa["reach"] = pa.batter_to.isin([1, 2, 3]) | pa.batter_to.isin(["1", "2", "3"])
    # defensive half-innings: first PA of each half-inning, from the fielding team's side
    hi = pa.drop_duplicates(["game_id", "inning", "half"]).copy()
    hi["margin_f"] = -hi.margin
    hi["ib"], hi["mb"] = ibin(hi.inning), mbin(hi.margin_f)

    s = pd.read_csv(P / "subs_2025.csv.gz")
    s = s[(s.kind == "in") & (s.position != "p") & s.game_id.isin(meta.game_id)].copy()
    s = s.drop_duplicates(["game_id", "team_id", "game_player_id"])      # first entry of each player
    s["home"] = s.team_id.values == s.game_id.map(home).values
    s["margin"] = np.where(s.home, s.home_score - s.visitor_score, s.visitor_score - s.home_score)
    s["kind6"] = np.where(s.position == "ph", "ph", np.where(s.position == "pr", "pr", "def"))
    s["ib"], s["mb"] = ibin(s.inning), mbin(s.margin)
    opp = {"ph": pa.groupby(["ib", "mb"]).size(), "pr": pa[pa.reach].groupby(["ib", "mb"]).size(),
           "def": hi.groupby(["ib", "mb"]).size()}
    opp_i = {k: v.groupby(level=0).sum() for k, v in opp.items()}
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "inning_bins": list(INNING_BINS), "margin_bins": list(MARGIN_BINS),
           "n_games": int(meta.shape[0]), "hazard": {}}
    for k in ("ph", "pr", "def"):
        ev = s[s.kind6 == k].groupby(["ib", "mb"]).size()
        ev_i = ev.groupby(level=0).sum()
        tab = {}
        for (i, m), n in opp[k].items():
            if n >= MIN_SUB_CELL:
                tab[f"{i}|{m}"] = round(float(ev.get((i, m), 0)) / n, 5)
            else:
                tab[f"{i}|{m}"] = round(float(ev_i.get(i, 0)) / opp_i[k][i], 5)
        out["hazard"][k] = tab
    # lineup spot of a pinch hitter / defensive substitute: entry share over opportunity share
    pa_slot = pa.slot.value_counts(normalize=True)
    for k in ("ph", "def"):
        sp = s[(s.kind6 == k) & s.lineup_spot.between(1, 9)].lineup_spot.value_counts(normalize=True)
        rel = (sp / (pa_slot if k == "ph" else 1 / 9)).reindex(range(1, 10)).fillna(0)
        out[f"{k}_slot_factor"] = {str(int(i)): round(float(v / rel.mean()), 4) for i, v in rel.items()}
    # tier multiplier: substitutions per team-game by tier over the pooled rate
    tg = pd.concat([meta.home_team_id, meta.away_team_id]).map(tier).value_counts()
    per = s.team_id.map(tier).value_counts() / tg
    pooled = len(s) / tg.sum()
    out["tier_multiplier"] = {t: round(float(per.get(t, pooled) / pooled), 4) for t in ("p4", "mid", "low")}
    out["subs_per_team_game"] = round(float(pooled), 4)
    out["subs_per_team_game_by_kind"] = {k: round(float((s.kind6 == k).sum() / tg.sum()), 4) for k in ("ph", "pr", "def")}
    # gate value: distinct batters with a plate appearance per team-game, with a bootstrap SE over games
    nb = pa.groupby(["game_id", "bat_team_id"]).batter_id.nunique()
    g = nb.groupby(level=0).mean()
    rng = np.random.default_rng(6)
    bs = [g.values[rng.integers(0, len(g), len(g))].mean() for _ in range(400)]
    out["batters_per_team_game"] = {"value": round(float(nb.mean()), 4), "se": round(float(np.std(bs, ddof=1)), 4)}
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["subs6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("_note", "hazard")}, indent=1))
    print({k: dict(list(v.items())[:12]) for k, v in out["hazard"].items()})


if __name__ == "__main__":
    main()
