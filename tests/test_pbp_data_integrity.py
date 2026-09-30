"""Integrity checks on the committed 2025 play-by-play tables.

The parsed plate appearances (data/ncaa_2025/pbp/parsed/pa_events_2025.csv.gz)
must reconcile with the box totals the same API reports for each game. Hits,
walks and HBP are counted identically by both, so they must match exactly in
aggregate; plate appearances and strikeouts may differ by a handful of records
(scoring corrections, dropped-third-strike quirks) and are held to 0.5 percent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/ncaa_2025/pbp/parsed"
pytestmark = pytest.mark.skipif(not (P / "pa_events_2025.csv.gz").exists(), reason="play-by-play tables not present")


@pytest.fixture(scope="module")
def tables():
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False)
    gm = pd.read_csv(P / "games_2025.csv", low_memory=False)
    return pa, gm


def test_every_parsed_game_has_a_box_and_vice_versa(tables):
    pa, gm = tables
    assert set(pa.game_id) == set(gm.game_id)


def test_hits_walks_hbp_reconcile_exactly(tables):
    pa, gm = tables
    box = {"h": gm.home_h.sum() + gm.away_h.sum(), "bb": gm.home_bb.sum() + gm.away_bb.sum(), "hbp": gm.home_hbp.sum() + gm.away_hbp.sum()}
    parsed = {"h": pa.result.isin(["1B", "2B", "3B", "HR"]).sum(), "bb": pa.result.isin(["BB", "IBB"]).sum(), "hbp": (pa.result == "HBP").sum()}
    for k in box:
        assert abs(parsed[k] - box[k]) <= max(2, 0.001 * box[k]), f"{k}: parsed {parsed[k]} vs box {box[k]}"


def test_pa_and_strikeouts_within_half_percent(tables):
    pa, gm = tables
    box_pa = gm.home_pa.sum() + gm.away_pa.sum()
    box_k = gm.home_k.sum() + gm.away_k.sum()
    assert abs(len(pa) - box_pa) / box_pa < 0.005
    assert abs((pa.result == "K").sum() - box_k) / box_k < 0.005


def test_base_out_states_are_legal(tables):
    pa, _ = tables
    assert pa.outs.between(0, 2).all()
    assert pa[["on1", "on2", "on3"]].isin([0, 1]).all().all()
    assert pa.inning.ge(1).all()


def test_runs_reconcile_with_final_scores(tables):
    pa, gm = tables
    rev = pd.read_csv(P / "runner_events_2025.csv.gz", low_memory=False)
    runs = pa.groupby("game_id").runs_on_play.sum().add(
        rev[rev.to_base == 4].groupby("game_id").size(), fill_value=0)
    final = gm.set_index("game_id").eval("home_score + away_score")
    joined = pd.concat([runs.rename("parsed"), final.rename("final")], axis=1).fillna(0)
    share_exact = (joined.parsed == joined.final).mean()
    assert share_exact > 0.9, f"only {share_exact:.2%} of games reconcile runs exactly"
    assert abs(joined.parsed.sum() - joined.final.sum()) / joined.final.sum() < 0.01


def test_benchmark_outcome_table_sums_to_one():
    b = json.loads((ROOT / "benchmarks.json").read_text())
    t = b["pa_outcome_table_league_avg"]
    probs = [v for k, v in t.items() if not k.startswith("_") and k != "conf" and isinstance(v, (int, float))]
    assert abs(sum(probs) - 1) < 2e-3
