"""Phase 2 game: the Phase 1 base-out state machine with real batters and pitchers.

Outcome of each plate appearance: odds-ratio matchup of batter and pitcher true rates
(engine.matchup) for K/BB/HBP/HR/1B/2B/3B/ROE/in-play out; the in-play out is subtyped
(plain out, SF, SH, FC) by base-out state from the league tables, and runners move by
the same empirical joint advancement and pre-PA base-running tables as Phase 1.
Runners carry the pitcher responsible for them; a run is unearned if the runner reached
on an error or scored on a play with an error or a passed ball.
"""
from __future__ import annotations

import numpy as np

from config.phase1 import IN_PLAY_OUT_CLASS, MIN_CELL_N, PRE_PA_EVENTS, RESULTS
from config.phase2 import Phase2Config
from engine.decider import Decision
from engine.matchup import OUTCOMES, matchup_probs
from engine.rng import Categorical
from engine.tables import AdvancementTable, OutcomeTable, PrePaEventTable

# batter stat columns and pitcher stat columns
B_G, B_PA, B_AB, B_H, B_2B, B_3B, B_HR, B_BB, B_HBP, B_K, B_SF, B_SH = range(12)
P_G, P_GS, P_BF, P_OUTS, P_H, P_HR, P_BB, P_HBP, P_K, P_R, P_ER, P_PITCH = range(12)
PITCH_MAP = {"IP_OUT": ("FO", "GO", "GIDP", "DP")}


class GameState2:
    __slots__ = ("rng", "inning", "half", "outs", "bases", "score", "over", "run_rule_in_effect", "ended_by_run_rule",
                 "team_obj", "lineup", "slot", "pitcher", "outing", "used", "weekend", "scheduled_starter", "inning_end",
                 "half_innings", "pa", "errors", "hits", "hr", "ab", "outs_pitched", "er_allowed")

    def __init__(self, rng, home, away, weekend):
        self.rng = rng
        self.inning, self.half, self.outs = 1, "T", 0
        self.bases = [None, None, None]
        self.score = {"away": 0, "home": 0}
        self.over = False
        self.run_rule_in_effect = False
        self.ended_by_run_rule = False
        self.team_obj = {"home": home, "away": away}
        self.lineup, self.slot, self.pitcher, self.outing, self.used = {}, {"away": 0, "home": 0}, {}, {}, {"away": set(), "home": set()}
        self.weekend = weekend
        self.scheduled_starter = {}
        self.inning_end = False
        self.half_innings = []
        self.pa = {"away": 0, "home": 0}
        self.errors = {"away": 0, "home": 0}     # committed by that team's fielders
        self.hits = {"away": 0, "home": 0}
        self.hr = {"away": 0, "home": 0}
        self.ab = {"away": 0, "home": 0}
        self.outs_pitched = {"away": 0, "home": 0}
        self.er_allowed = {"away": 0, "home": 0}

    @property
    def batting_side(self):
        return "away" if self.half == "T" else "home"

    @property
    def fielding_side(self):
        return "home" if self.half == "T" else "away"

    @property
    def base_code(self):
        return "".join("0" if b is None else "1" for b in self.bases)

    def bullpen_left(self, side):
        return any(p.pid not in self.used[side] for p in self.team_obj[side].relievers)


class PlayerGameEngine:
    def __init__(self, cfg: Phase2Config, league, bstats, pstats):
        b = cfg.base
        self.cfg, self.league = cfg, league
        self.subtypes = OutcomeTable(b.outcome_probs, RESULTS, IN_PLAY_OUT_CLASS, b.in_play_out_subtype)
        self._sub_counts = b.in_play_out_subtype
        self.advance = AdvancementTable(b.pa_joint, MIN_CELL_N)
        self.pre_pa = PrePaEventTable(b.pre_pa_events, PRE_PA_EVENTS, MIN_CELL_N)
        self.rules = b.rules
        self.bstats, self.pstats = bstats, pstats
        self.cache: dict = {}
        self.roe_count = 0
        pr = cfg.usage["pitches_per_pa_by_result"]
        self.pitch_cat = {}
        for res in ("K", "BB", "HBP", "1B", "2B", "3B", "HR", "SF", "SH", "ROE", "FC", "IP_OUT"):
            keys = PITCH_MAP.get(res, (res,))
            counts: dict = {}
            for k in keys:
                for n, c in pr.get(k, {}).items():
                    counts[int(n)] = counts.get(int(n), 0) + c
            self.pitch_cat[res] = Categorical.from_counts(counts)

    def _probs(self, batter, pitcher) -> Categorical:
        key = (batter.pid, pitcher.pid)
        cat = self.cache.get(key)
        if cat is None:
            p = matchup_probs(self.cfg, batter.z, pitcher.z, self.league.location)
            cat = Categorical(list(OUTCOMES), [p[o] for o in OUTCOMES])
            self.cache[key] = cat
        return cat

    # ---- runner movement ----------------------------------------------------------------
    def _apply(self, st, dests, batter_runner, batter_to, errors, event=None):
        new = [None, None, None]
        scored, outs, occupied = [], 0, set()
        bat_side, fld_side = st.batting_side, st.fielding_side
        for origin in (3, 2, 1):
            r = st.bases[origin - 1]
            if r is None:
                continue
            d = dests[origin - 1] or str(origin)
            if d == "0":
                outs += 1
            elif d == "4":
                scored.append(r)
            else:
                tgt = int(d)
                while tgt in occupied and tgt > origin:
                    tgt -= 1
                if tgt in occupied:
                    outs += 1
                else:
                    occupied.add(tgt); new[tgt - 1] = r
        if batter_runner is not None:
            if batter_to in ("", "0"):
                outs += 1
            elif batter_to == "4":
                scored.append(batter_runner)
            else:
                tgt = int(batter_to)
                while tgt in occupied and tgt > 0:
                    tgt -= 1
                if tgt == 0:
                    outs += 1
                else:
                    occupied.add(tgt); new[tgt - 1] = batter_runner
        st.bases = new
        outs = min(outs, 3 - st.outs)
        st.outs += outs
        st.outs_pitched[fld_side] += outs
        self.pstats[st.pitcher[fld_side].pid][P_OUTS] += outs
        st.errors[fld_side] += errors
        for pid, unearned in scored:
            self.pstats[pid][P_R] += 1
            if not (unearned or errors or event == "PB"):
                self.pstats[pid][P_ER] += 1
                st.er_allowed[fld_side] += 1
        st.score[bat_side] += len(scored)
        return len(scored)

    def _end_check(self, st, mid_bottom):
        r, m = self.rules, st.score["home"] - st.score["away"]
        if mid_bottom:
            if st.inning >= r.innings and m > 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and m >= r.run_rule_margin:
                st.over = st.ended_by_run_rule = True
            return
        if st.half == "T":
            if st.inning >= r.innings and m > 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and m >= r.run_rule_margin:
                st.over = st.ended_by_run_rule = True
        else:
            if st.inning >= r.innings and m != 0:
                st.over = True
            elif st.run_rule_in_effect and st.inning >= r.run_rule_after_inning and abs(m) >= r.run_rule_margin:
                st.over = st.ended_by_run_rule = True

    def _bring_in(self, st, side, pitcher, starter):
        st.pitcher[side] = pitcher
        st.used[side].add(pitcher.pid)
        st.outing[side] = {"starter": starter, "pitches": 0, "runs": 0}
        ps = self.pstats[pitcher.pid]
        ps[P_G] += 1
        if starter:
            ps[P_GS] += 1

    def _half(self, st, dec):
        rng = st.rng
        st.outs, st.bases = 0, [None, None, None]
        bat, fld = st.batting_side, st.fielding_side
        runs0, pa0 = st.score[bat], st.pa[bat]
        while st.outs < 3 and not st.over:
            if any(b is not None for b in st.bases):
                steal = dec.steal_attempt(st)
                ev = self.pre_pa.draw_event(st.outs, st.base_code, rng.random())
                if steal == Decision.NO and ev == "SB_ATT":
                    ev = None
                if ev is not None:
                    out = self.pre_pa.draw_outcome(ev, st.outs, st.base_code, rng.random())
                    if out is not None:
                        dests, _, err = out
                        if self._apply(st, dests, None, None, err, event=ev) and st.half == "B":
                            self._end_check(st, True)
                        if st.outs >= 3 or st.over:
                            break
            batter = st.lineup[bat][st.slot[bat] % 9]
            st.slot[bat] += 1
            pitcher = st.pitcher[fld]
            dec.intentional_walk(st)
            bunt = dec.bunt(st)
            res = self._probs(batter, pitcher).draw(rng.random())
            if res == "OUT":
                res = self._subtype(st, rng, bunt)
            dests, b_to, err = self.advance.draw(res, st.outs, st.base_code, rng.random(), [rng.random() for _ in range(4)])
            self._record(st, batter, pitcher, res, rng)
            scored = self._apply(st, dests, (pitcher.pid, res == "ROE"), b_to, err)
            st.outing[fld]["runs"] += scored
            if scored and st.half == "B":
                self._end_check(st, True)
            if st.over:
                break
            st.inning_end = st.outs >= 3
            if dec.pitching_change(st) == Decision.YES:
                nxt = dec.relief_pitcher(st, fld)
                if nxt is not None:
                    self._bring_in(st, fld, nxt, False)
        st.half_innings.append((st.inning, st.half, st.score[bat] - runs0, st.pa[bat] - pa0))

    def _subtype(self, st, rng, bunt):
        cls = self.subtypes.feasibility_class(st.outs, [b is not None for b in st.bases])
        sub = self.subtypes.subtype[cls]
        if bunt == Decision.YES and cls in ("on3_lt2", "on_lt2"):
            return "SH"
        s = sub.draw(rng.random())
        if s == "SH" and bunt == Decision.NO:
            others = {k: c for k, c in self._sub_counts[cls].items() if k != "SH"}
            s = Categorical.from_counts(others).draw(rng.random())
        return s

    def _record(self, st, batter, pitcher, res, rng):
        bs, ps = self.bstats[batter.pid], self.pstats[pitcher.pid]
        bat = st.batting_side
        bs[B_PA] += 1; ps[P_BF] += 1; st.pa[bat] += 1
        n = self.pitch_cat[res].draw(rng.random())
        ps[P_PITCH] += n
        st.outing[st.fielding_side]["pitches"] += n
        if res == "BB":
            bs[B_BB] += 1; ps[P_BB] += 1
        elif res == "HBP":
            bs[B_HBP] += 1; ps[P_HBP] += 1
        elif res == "SF":
            bs[B_SF] += 1
        elif res == "SH":
            bs[B_SH] += 1
        else:
            if res == "ROE":
                self.roe_count += 1
            bs[B_AB] += 1; st.ab[bat] += 1
            if res == "K":
                bs[B_K] += 1; ps[P_K] += 1
            elif res in ("1B", "2B", "3B", "HR"):
                bs[B_H] += 1; ps[P_H] += 1; st.hits[bat] += 1
                if res == "2B":
                    bs[B_2B] += 1
                elif res == "3B":
                    bs[B_3B] += 1
                elif res == "HR":
                    bs[B_HR] += 1; ps[P_HR] += 1; st.hr[bat] += 1

    def play(self, rng, home, away, weekend, starters, dec) -> GameState2:
        st = GameState2(rng, home, away, weekend)
        st.run_rule_in_effect = rng.random() < self.rules.p_run_rule_in_effect
        st.scheduled_starter = starters
        for side in ("away", "home"):
            st.lineup[side] = dec.lineup(st, side)
            for p in st.lineup[side]:
                self.bstats[p.pid][B_G] += 1
            self._bring_in(st, side, dec.starting_pitcher(st, side), True)
        while not st.over:
            st.half = "T"
            self._half(st, dec)
            if st.over:
                break
            self._end_check(st, False)
            if st.over:
                break
            st.half = "B"
            self._half(st, dec)
            if st.over:
                break
            self._end_check(st, False)
            if not st.over:
                st.inning += 1
        return st
