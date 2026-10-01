"""Engine invariants that do not depend on benchmark tolerances."""
from __future__ import annotations

import numpy as np

from config import phase1
from engine.decider import Decision, LeagueAverageDecider
from engine.game import Engine
from engine.rng import game_seeds
from engine.sim import simulate_league_average_games


def test_same_seed_reproduces_exactly():
    a = simulate_league_average_games(200, seed=42)
    b = simulate_league_average_games(200, seed=42)
    assert a == b


def test_different_seeds_differ():
    a = simulate_league_average_games(200, seed=1)
    b = simulate_league_average_games(200, seed=2)
    assert a["runs_per_team_game"] != b["runs_per_team_game"]


def test_game_i_is_independent_of_batch_size():
    cfg = phase1.load(); eng = Engine(cfg); dec = LeagueAverageDecider()
    s5 = game_seeds(7, 5); s50 = game_seeds(7, 50)
    g_a = eng.play(np.random.Generator(np.random.PCG64(s5[3])), dec)
    g_b = eng.play(np.random.Generator(np.random.PCG64(s50[3])), dec)
    assert (g_a.away.runs, g_a.home.runs, g_a.inning) == (g_b.away.runs, g_b.home.runs, g_b.inning)


def test_state_machine_invariants():
    cfg = phase1.load(); eng = Engine(cfg); dec = LeagueAverageDecider()
    for ss in game_seeds(3, 300):
        g = eng.play(np.random.Generator(np.random.PCG64(ss)), dec)
        assert g.over and g.inning >= cfg.rules.innings - 2  # run rule can end a game after the 7th
        assert g.home.runs != g.away.runs or g.ended_by_run_rule is False and False  # no ties
        for t in (g.away, g.home):
            assert t.pa == t.ab + t.bb + t.hbp + t.sf + t.sh
            assert t.h <= t.ab and t.k <= t.ab and t.hr <= t.h and t.tb >= t.h
            assert t.runs <= t.h + t.bb + t.hbp + t.roe + t.fc  # every run needs a baserunner


def test_decider_is_consulted_and_obeyed():
    class NoSteals(LeagueAverageDecider):
        def steal_attempt(self, state):
            return Decision.NO

    class AlwaysSteal(LeagueAverageDecider):
        def steal_attempt(self, state):
            return Decision.YES

    quiet = simulate_league_average_games(300, seed=5, decider=NoSteals())
    wild = simulate_league_average_games(300, seed=5, decider=AlwaysSteal())
    base = simulate_league_average_games(300, seed=5)
    assert quiet["sb_per_team_game"] == 0 and quiet["cs_per_team_game"] == 0
    assert wild["sb_per_team_game"] > base["sb_per_team_game"] > quiet["sb_per_team_game"]


def test_no_literal_rates_in_engine_package():
    """Every rate must come from config/; engine/ may not carry numeric constants
    other than structural integers (bases, outs, innings indices)."""
    import re
    from pathlib import Path
    bad = []
    for f in Path("engine").glob("*.py"):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split("#")[0]
            for m in re.findall(r"(?<![\w.])\d*\.\d+(?![\w.])", code):  # any decimal literal
                if m not in ("0.0", "1.0"):  # accumulator seeds and the top of a CDF are structure, not rates
                    bad.append(f"{f}:{i}: {line.strip()}")
    assert not bad, "decimal literals in engine/: " + "; ".join(bad)
