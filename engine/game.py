"""One game of the Phase 1 engine: a base-out state machine driven by the single
outcome table and the empirical advancement and base-running tables."""
from __future__ import annotations

import numpy as np

from config.phase1 import IN_PLAY_OUT_CLASS, MIN_CELL_N, PRE_PA_EVENTS, RESULTS, Phase1Config
from engine.decider import Decider, Decision
from engine.state import GameState, TeamTally
from engine.tables import AdvancementTable, OutcomeTable, PrePaEventTable


class Engine:
    def __init__(self, cfg: Phase1Config):
        self.cfg = cfg
        self.outcomes = OutcomeTable(cfg.outcome_probs, RESULTS, IN_PLAY_OUT_CLASS, cfg.in_play_out_subtype)
        self.advance = AdvancementTable(cfg.pa_joint, MIN_CELL_N)
        self.pre_pa = PrePaEventTable(cfg.pre_pa_events, PRE_PA_EVENTS, MIN_CELL_N)
        self.collision_fixes = 0

    # ---- applying destinations --------------------------------------------------
    def _apply(self, st: GameState, dests: list, batter_to: str | None, errors: int, event: str | None = None) -> int:
        """Move runners/batter per destination codes; return runs scored. Updates outs."""
        new = [False, False, False]
        runs = outs = 0
        occupied_now = set()
        # lead runner first so a trailing runner can never pass him
        for origin in (3, 2, 1):
            if not st.bases[origin - 1]:
                continue
            d = dests[origin - 1]
            if d == "":
                d = str(origin)  # held (only reachable through marginal fallback)
            if d == "0":
                outs += 1
            elif d == "4":
                runs += 1
            else:
                tgt = int(d)
                while tgt in occupied_now and tgt > origin:  # collision from independent marginals
                    tgt -= 1
                    self.collision_fixes += 1
                if tgt in occupied_now:  # would pass a runner who held; the trailing runner is out instead
                    outs += 1
                    self.collision_fixes += 1
                else:
                    occupied_now.add(tgt); new[tgt - 1] = True
                    if event == "SB_ATT" and tgt > origin:
                        st.batting.sb += 1
            if d == "0" and event == "SB_ATT":
                st.batting.cs += 1
        if batter_to is not None:
            if batter_to in ("", "0"):
                outs += 1
            elif batter_to == "4":
                runs += 1
            else:
                tgt = int(batter_to)
                while tgt in occupied_now and tgt > 0:
                    tgt -= 1; self.collision_fixes += 1
                if tgt == 0:
                    outs += 1
                else:
                    occupied_now.add(tgt); new[tgt - 1] = True
        st.bases = new
        st.outs = min(3, st.outs + outs)
        st.fielding.errors_committed += errors
        st.batting.runs += runs
        return runs

    # ---- game flow ----------------------------------------------------------------
    def _check_end(self, st: GameState, mid_bottom: bool) -> None:
        r = self.cfg.rules
        m = st.margin_home
        if mid_bottom:  # a run just scored in the bottom half
            if st.inning >= r.innings and m > 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and m >= r.run_rule_margin:
                st.over = True; st.ended_by_run_rule = True
            return
        if st.half == "T":  # top half just ended
            if st.inning >= r.innings and m > 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and m >= r.run_rule_margin:
                st.over = True; st.ended_by_run_rule = True
        else:  # bottom half just ended
            if st.inning >= r.innings and m != 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and abs(m) >= r.run_rule_margin:
                st.over = True; st.ended_by_run_rule = True

    def _half_inning(self, st: GameState, dec: Decider, rng: np.random.Generator) -> None:
        st.outs = 0
        st.bases = [False, False, False]
        if self.cfg.rules.extra_innings_placed_runner and st.inning > self.cfg.rules.innings:
            st.bases[1] = True
        dec.lineup(st, "away" if st.half == "T" else "home")
        dec.pitching_change(st)
        runs_start, pa_start = st.batting.runs, st.batting.pa
        while st.outs < 3 and not st.over:
            dec.pinch_hitter(st)
            # --- pre-PA base running events (steal attempt, WP, PB, pickoff, balk): one draw per
            # opportunity, again after each event until none occurs (scripts/build_engine_tables.py)
            while any(st.bases) and st.outs < 3 and not st.over:
                steal = dec.steal_attempt(st)
                u = rng.random()
                if steal == Decision.LEAGUE_RATE:
                    ev = self.pre_pa.draw_event(st.outs, st.base_code, u)
                elif steal == Decision.YES:
                    ev = "SB_ATT"
                else:
                    ev = self.pre_pa.draw_event(st.outs, st.base_code, u)
                    if ev == "SB_ATT":
                        ev = None
                if ev is None:
                    break
                out = self.pre_pa.draw_outcome(ev, st.outs, st.base_code, rng.random())
                if out is None:
                    break
                dests, _, err = out
                runs = self._apply(st, dests, None, err, event=ev)
                if runs and st.half == "B":
                    self._check_end(st, mid_bottom=True)
            if st.outs >= 3 or st.over:
                break
            # --- the plate appearance ---------------------------------------------------
            dec.intentional_walk(st)  # LEAGUE_RATE: IBB lives inside the table's BB share
            bunt = dec.bunt(st)
            res = self.outcomes.draw(rng.random(), rng.random(), st.outs, st.bases,
                                     allow_bunt=(bunt != Decision.NO), force_bunt=(bunt == Decision.YES))
            dests, b_to, err = self.advance.draw(res, st.outs, st.base_code, rng.random(), [rng.random() for _ in range(4)])
            st.batting.record_pa(res)
            runs = self._apply(st, dests, b_to, err)
            if runs and st.half == "B":
                self._check_end(st, mid_bottom=True)
        st.batting.lob += sum(st.bases)
        st.half_innings.append((st.inning, st.half, st.batting.runs - runs_start, st.batting.pa - pa_start))

    def play(self, rng: np.random.Generator, decider: Decider) -> GameState:
        st = GameState()
        st.run_rule_in_effect = rng.random() < self.cfg.rules.p_run_rule_in_effect
        while not st.over:
            st.half = "T"
            self._half_inning(st, decider, rng)
            if st.over:
                break
            self._check_end(st, mid_bottom=False)
            if st.over:
                break
            st.half = "B"
            self._half_inning(st, decider, rng)
            if st.over:
                break
            self._check_end(st, mid_bottom=False)
            if not st.over:
                st.inning += 1
        return st
