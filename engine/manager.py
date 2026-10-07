"""AI manager for Phase 2: answers the engine's Decider calls from empirical usage.

  lineup            each regular starts with the real start share for his rank (Phase 6: by
                    his rank and whether he started the team's previous game, from the 2025
                    start persistence); empty spots go to bench players in proportion to the
                    same chances; batting order is
                    the team's talent order (best expected OBP+SLG first)
  starting_pitcher  weekend: each series draws a real three-game pattern of starter ranks
                    (the team's 1st..8th most frequent weekend starter in games 1, 2, 3 of a
                    weekend; the top three make ~79% of weekend starts); ranks map to staff
                    slots (config ROTATION_STAFF), a repeated pooled rank takes the next
                    reliever. Midweek: the two midweek starters alternate.
  pitching_change   pull hazard from the play-by-play: P(replaced before the next batter |
                    starter or reliever, weekend, outing pitch count, outing runs, inning
                    just ended); weekend starters use the table for their rotation rank
                    (1, 2, 3, spot starter), which carries the aces' longer leash; the
                    pitcher's own leash (Stamina, Phase 4) scales it: h' = 1 - (1 - h)^theta
  relief_pitcher    Phase 6: any unused pitcher on the staff but the game's starter, chosen
                    by the conditional logit fitted on the 2025 relief entries
                    (scripts/build_phase6_usage.py): role (weekend rotation rank, midweek
                    starter, bullpen rank) x leverage (late and close, blowout, other) plus
                    the pitcher's rest (days since his last outing, its pitches, back to back),
                    plus a platoon term that Phase 3 fills (platoon_utility). Without Phase 6
                    inputs: an unused reliever by the real share of relief batters faced by rank.
  Phase 6 also: the midweek starter is chosen by the same kind of logit over the whole staff;
  the pull hazard carries a multiplier by tier and, for starters, season week; pinch hitters
  (per plate appearance), pinch runners (per batter reaching base) and defensive or blowout
  substitutions (per half-inning in the field) enter at the 2025 hazards by inning x margin, with a
  tier multiplier, the lineup spot by its real share, the bench player by bench rank.
Steals, bunts and intentional walks stay at league rates.
"""
from __future__ import annotations

import numpy as np

from config.phase2 import GAMES_PER_WEEKEND, MIN_HAZARD_N, N_BENCH, N_REGULARS, ROTATION_STAFF, SPOT_STARTER_RANK, Phase2Config
from config import decisions as _cdec
from config import phase6, phase7
from config.phase6 import LEVERAGE_BLOWOUT, LEVERAGE_CLOSE, LEVERAGE_LATE_INNING, N_ROLE_RELIEVERS, PITCH_BINS, REST_SPLIT_DAYS
from engine.decider import Decision, LeagueAverageDecider


class Manager(LeagueAverageDecider):
    rng = None    # set by engine.control.AIController for each call: this team's keyed stream at the decision point

    def _r(self, state):
        """The generator for this decision: the controller's positioned stream, else the game's (scripts)."""
        return self.rng if self.rng is not None else state.rng

    # ---- PR B: decisions that change outcomes (config.decisions; engine.decisions) ----------------
    def _dm(self):
        if not hasattr(self, "_dm_cache"):
            from config import decisions
            from engine.decisions import DecisionModels
            self._dm_cache = DecisionModels(decisions.load()) if decisions.on("decisions") else None
        return self._dm_cache

    def intentional_walk(self, state):
        dm = self._dm()
        if dm is None or not _cdec.on("ibb"):
            return Decision.LEAGUE_RATE
        return Decision.YES if self._r(state).random() < dm.ibb_prob(state, state.cur_slot) else Decision.NO

    def bunt(self, state):
        dm = self._dm()
        if dm is None or not _cdec.on("bunts"):
            return Decision.LEAGUE_RATE
        return Decision.YES if self._r(state).random() < dm.bunt_call_prob(state, state.cur_slot) else Decision.NO

    def pre_pitch(self, state, info: dict):
        """Steal or not, before the coming pitch: the league's attempt rate in this count and game state for this
        runner against this pitcher (info["attempt_logit"]: the fitted hazard with the runner's speed, the
        pitcher's hold and the tier cell; engine.game2 GameSession._steal_info)."""
        if not info.get("steal_base") or self._dm() is None or not _cdec.on("steals"):
            return None
        p = 1.0 / (1.0 + np.exp(-info["attempt_logit"]))
        return "steal" if self._r(state).random() < p else None

    def __init__(self, cfg: Phase2Config):
        u = cfg.usage
        self.start = phase6.batter_start_shares(u["batter_start_share_by_rank"], N_REGULARS + N_BENCH)
        self.relw = [u["reliever_bf_share_by_rank"][str(k + 1)] for k in range(len(u["reliever_bf_share_by_rank"]))]

        def table(block):
            t = {k: v for k, v in block["table"].items()}
            b = {k: v for k, v in block["backoff"].items()}
            return t, b
        pats = u["weekend_series_rank_patterns"]
        self.patterns = [tuple(int(x) for x in k.split("|")) for k in pats]
        w = np.array([pats[k] for k in pats], float)
        self.pattern_w = w / w.sum()
        self.series_plan: dict = {}
        self.midweek_count: dict = {}
        self.sp_table, self.sp_back = table(u["starter_pull"])
        self.wr_table, self.wr_back = table(u["weekend_starter_pull_by_rank"])
        self.rank_now: dict = {}  # team id -> rotation rank class of today's weekend starter
        self.rp_table, self.rp_back = table(u["reliever_pull"])
        # pull decisions per pitcher, for estimating leash back from simulated seasons (Phase 4 round trip):
        # sum of log(1 - h) where he stayed, baseline h at each decision where he was pulled
        self.leash_survive: dict = {}
        self.leash_pulls: dict = {}
        # expected pulls and their variance under the pitcher's true leash (sum of h' and h'(1 - h'))
        self.leash_expected: dict = {}
        self.leash_var: dict = {}
        # Phase 6 (config.phase6): each pitcher's outings (date, pitches) this season; the relief and
        # midweek-start choice logits; the pull multipliers by tier and season week
        self.history: dict = {}
        u6 = phase6.load().get("usage6", {}) if phase6.on("bullpen") else {}
        self.relief_coef = u6.get("relief", {}).get("coef", {})
        self.midweek_coef = u6.get("midweek", {}).get("coef", {})
        # Phase 7: who starts a conference tournament or NCAA tournament game (scripts/build_phase7_usage.py)
        self.tourney_coef = phase7.load().get("usage7", {}).get("start", {}).get("coef", {}) if phase7.on("world") else {}
        self.pull6 = phase6.load().get("pull6", {}) if phase6.on("leash") else {}
        # Phase 6: midweek starts (Mon-Wed on the engine's calendar) use a table built on Mon-Wed starts only;
        # the Phase 2 table pools Thursday series openers, whose aces carry long leashes into its high cells
        self.mid_spread = self.pull6.get("sp_midweek", {}).get("leash_spread", {}).get("log_sd")
        if self.mid_spread:
            from config.phase4 import load_stamina
            self.stamina = load_stamina()
        mt = self.pull6.get("sp_midweek_table")
        self.spm_table, self.spm_back = (mt["table"], mt["backoff"]) if mt else (self.sp_table, self.sp_back)
        self.subs6 = phase6.load().get("subs6", {}) if phase6.on("subs") else {}
        bp = self.subs6.get("bench_pick_weight", {})
        n_b = N_REGULARS + N_BENCH
        self.start_markov = ([bp["start_after_start"][str(k + 1)] for k in range(n_b)], [bp["start_after_sit"][str(k + 1)] for k in range(n_b)]) \
            if "start_after_start" in bp else None
        self.last_lineup: dict = {}       # team id -> starters of its previous game
        if self.subs6:
            self.sub_ib, self.sub_mb = np.array(self.subs6["inning_bins"]), np.array(self.subs6["margin_bins"])
            self.def_slot = [self.subs6["def_slot_factor"][str(k + 1)] for k in range(9)]

    # ---- lineup ------------------------------------------------------------------------
    def _start_prob(self, tid: int, p) -> float:
        """Phase 6: a batter's chance to start, by his rank and whether he started the team's previous
        game (2025 start persistence, subs6); without it, or before a team's first game, his rank's share."""
        last = self.last_lineup.get(tid)
        if not self.start_markov or last is None:
            return self.start[p.order]
        ss, sn = self.start_markov
        return ss[p.order] if p.pid in last else sn[p.order]

    def lineup(self, state, team: str):
        tm = state.team_obj[team]
        rng = self._r(state)
        starters = [p for p in tm.batters[:N_REGULARS] if rng.random() < self._start_prob(tm.tid, p)]
        bench = list(tm.batters[N_REGULARS:])
        while len(starters) < N_REGULARS and bench:
            w = np.array([self._start_prob(tm.tid, p) for p in bench])
            pick = bench.pop(int(rng.choice(len(bench), p=w / w.sum())))
            starters.append(pick)
        starters += [p for p in tm.batters[:N_REGULARS] if p not in starters][: N_REGULARS - len(starters)]
        if self.start_markov:
            self.last_lineup[tm.tid] = {p.pid for p in starters}
        return sorted(starters, key=lambda p: p.bat_order)

    # ---- Phase 6: rest, roles and the choice logits ---------------------------------------
    @staticmethod
    def _staff(tm) -> list:
        """(pitcher, role) for the team's 13-man staff in the engine roles (config.phase6.ROLES)."""
        return ([(p, f"wk{k + 1}") for k, p in enumerate(tm.weekend_sp)] + [(p, f"mid{k + 1}") for k, p in enumerate(tm.midweek_sp)]
                + [(p, f"r{min(k + 1, N_ROLE_RELIEVERS)}") for k, p in enumerate(tm.relievers)])

    def _rest(self, pid: int, date: int) -> tuple:
        """Rest cell and back-to-back flag of a pitcher before a game on `date`."""
        h = self.history.get(pid)
        if not h:
            return "d6", False
        last_d, last_p = h[-1]
        days = date - last_d
        b2b = len(h) >= 2 and date - h[-1][0] == 1 and date - h[-2][0] == 2
        if days >= 6:
            return "d6", b2b
        if days in REST_SPLIT_DAYS:
            return f"d{days}p{int(np.searchsorted(PITCH_BINS, last_p, side='left'))}", b2b
        return f"d{days}", b2b

    def _utility(self, coef: dict, role: str, ctx: str, pid: int, date: int) -> float:
        cell, b2b = self._rest(pid, date)
        return coef.get(f"{role}|{ctx}", 0.0) + coef.get(f"rest|{cell}", 0.0) + coef.get("b2b", 0.0) * b2b

    def platoon_utility(self, state, pitcher) -> float:
        """Hook for Phase 3 (handedness): the extra utility of bringing in this pitcher against the
        batters due up (e.g. a left-handed specialist for a run of left-handed hitters). No
        handedness exists before Phase 3, so it adds nothing."""
        return 0.0

    def _choose(self, state, cands: list, coef: dict, ctx: str):
        u = np.array([self._utility(coef, role, ctx, p.pid, state.date) + self.platoon_utility(state, p) for p, role in cands])
        w = np.exp(u - u.max())
        return cands[int(self._r(state).choice(len(cands), p=w / w.sum()))][0]

    def record_game(self, state) -> None:
        """After a game: every pitcher's outing (date, pitches) for the rest state of later games."""
        for pid, pitches in state.pitch_log:
            self.history.setdefault(pid, []).append((state.date, pitches))

    def _leash_ctx(self, state, starter: bool) -> float:
        """Phase 6 multiplier on log theta: tier of the pitching team (not for weekend starters), for
        starters season week, and for midweek starters the starter's staff role."""
        if not self.pull6:
            return 0.0
        role = ("sp_weekend" if state.weekend else "sp_midweek") if starter else "rp"
        r = self.pull6[role]
        x = r["log_theta_tier"].get(state.team_obj[state.fielding_side].tier, 0.0)
        if starter:
            wb = int(np.searchsorted(np.array(r["week_bins"]), state.week, side="right") - 1)
            x += r["log_theta_week"].get(str(wb), 0.0)
        if "log_theta_class" in r:
            # a midweek start by a weekend-rotation arm runs longer, a reliever's (bullpen game) shorter
            tm, pid = state.team_obj[state.fielding_side], state.pitcher[state.fielding_side].pid
            cls = "wk" if any(p.pid == pid for p in tm.weekend_sp) else ("mid" if any(p.pid == pid for p in tm.midweek_sp) else "r")
            x += r["log_theta_class"].get(cls, 0.0)
        return x

    def starting_pitcher(self, state, team: str):
        tm = state.team_obj[team]
        if getattr(state, "tournament", False) and self.tourney_coef:
            staff = self._staff(tm)
            p = self._choose(state, staff, self.tourney_coef, "start")
            role = dict((x.pid, r) for x, r in staff)[p.pid]
            self.rank_now[tm.tid] = int(role[2]) if role.startswith("wk") else SPOT_STARTER_RANK
            return p
        if not state.weekend and self.midweek_coef:
            return self._choose(state, self._staff(tm), self.midweek_coef, "start")
        if not state.weekend:
            k = self.midweek_count.get(tm.tid, 0)
            self.midweek_count[tm.tid] = k + 1
            return tm.midweek_sp[k % len(tm.midweek_sp)]
        key = (tm.tid, state.week)
        if key not in self.series_plan:
            ranks = self.patterns[int(self._r(state).choice(len(self.patterns), p=self.pattern_w))]
            plan, taken = [], set()
            for r in ranks:
                grp, i = ROTATION_STAFF[r - 1]
                p = getattr(tm, grp)[i]
                if p.pid in taken:  # pooled deepest rank repeated: next unused reliever
                    p = next(x for x in tm.relievers if x.pid not in taken)
                taken.add(p.pid); plan.append((p, r))
            self.series_plan[key] = plan
        pitcher, rank = self.series_plan[key][min(state.day, GAMES_PER_WEEKEND - 1)]
        self.rank_now[tm.tid] = min(rank, SPOT_STARTER_RANK)
        return pitcher

    # ---- pitching changes ------------------------------------------------------------------
    def _hazard(self, starter: bool, weekend: int, pitches: int, runs: int, inning_end: int, rank: int | None = None) -> float:
        pb, rb = min(pitches // 10, 12), min(runs, 5)
        if starter and weekend and rank is not None:
            chain = ((self.wr_table, f"{rank}|{pb}|{rb}|{inning_end}"), (self.wr_back, f"{rank}|{pb}|{inning_end}"),
                     (self.sp_table, f"{weekend}|{pb}|{rb}|{inning_end}"), (self.sp_back, f"{weekend}|{pb}|{inning_end}"))
        elif starter and not weekend:
            chain = ((self.spm_table, f"{weekend}|{pb}|{rb}|{inning_end}"), (self.spm_back, f"{weekend}|{pb}|{inning_end}"))
        elif starter:
            chain = ((self.sp_table, f"{weekend}|{pb}|{rb}|{inning_end}"), (self.sp_back, f"{weekend}|{pb}|{inning_end}"))
        else:
            chain = ((self.rp_table, f"{pb}|{rb}|{inning_end}"), (self.rp_back, f"{pb}|{inning_end}"))
        c = None
        for tab, key in chain:
            c = tab.get(key)
            if c is not None and c[1] >= MIN_HAZARD_N:
                break
        if c is None or c[1] == 0:
            return None  # beyond the observed range
        return c[0] / c[1]

    def pitching_change(self, state):
        o = state.outing[state.fielding_side]
        if not state.bullpen_left(state.fielding_side):
            return Decision.NO
        rank = self.rank_now.get(state.team_obj[state.fielding_side].tid) if state.weekend else None
        h = self._hazard(o["starter"], int(state.weekend), o["pitches"], o["runs"], int(state.inning_end), rank)
        if h is None:  # no hazard cell has data (pitch counts past the sample's maximum): the data's maximum
            return Decision.YES if o["pitches"] >= 120 else Decision.NO
        pid = state.pitcher[state.fielding_side].pid
        # context multiplier (tier, season week) folded into the baseline, so the pitcher's own
        # leash (Stamina) is estimated against the hazard he actually faced
        ctx = self._leash_ctx(state, o["starter"])
        if ctx:
            h = -np.expm1(np.exp(ctx) * np.log1p(-min(h, 1 - 1e-9)))
        pit = state.pitcher[state.fielding_side]
        lt = pit.log_theta
        midweek_start = bool(o["starter"] and not state.weekend and self.mid_spread)
        if midweek_start:
            # midweek starts: the leash spread around the context is narrower than the Stamina scale's
            # (2025 Mon-Wed starts, pull6 sp_midweek leash_spread), so the pitcher's deviation shrinks
            g = self.stamina["reliever" if pit.group == "rp" else "starter"]
            lt = g["log_mean"] + (lt - g["log_mean"]) * self.mid_spread / g["log_sd"]
        theta = np.exp(lt)
        hp = -np.expm1(theta * np.log1p(-min(h, 1 - 1e-9)))
        pulled = self._r(state).random() < hp
        if not midweek_start:
            # the Phase 4 round trip reads the leash where the Stamina rating applies in full (midweek starts,
            # where it is shrunk to the midweek spread, stay out of it)
            self.leash_expected[pid] = self.leash_expected.get(pid, 0) + hp
            self.leash_var[pid] = self.leash_var.get(pid, 0) + hp * (1 - hp)
            if pulled:
                self.leash_pulls.setdefault(pid, []).append(h)
            else:
                self.leash_survive[pid] = self.leash_survive.get(pid, 0) + np.log1p(-min(h, 1 - 1e-9))
        return Decision.YES if pulled else Decision.NO

    # ---- Phase 6: substitutions --------------------------------------------------------------
    def _sub_rate(self, state, team: str, kind: str) -> float:
        s6 = self.subs6
        margin = state.score[team] - state.score["away" if team == "home" else "home"]
        ib = int(np.searchsorted(self.sub_ib, state.inning, side="right") - 1)
        mb = int(np.searchsorted(self.sub_mb, margin, side="right") - 1)
        return s6["hazard"][kind].get(f"{ib}|{mb}", 0.0) * s6["tier_multiplier"].get(state.team_obj[team].tier, 1.0)

    def _bench_pick(self, state, team: str, bench: list | None = None):
        """A substitute among the players not in the game, in proportion to his start rank's
        substitute entries per game not started (subs6 bench_pick_weight, 2025 play-by-play)."""
        if bench is None:
            bench = [p for p in state.team_obj[team].batters if p.pid not in state.in_game[team]]
        if not bench:
            return None
        bw = self.subs6.get("bench_pick_weight", {}).get("weight") if self.subs6 else None
        w = np.array([bw[str(p.order + 1)] if bw else self.start[p.order] for p in bench])
        return bench[int(self._r(state).choice(len(bench), p=w / w.sum()))]

    def pinch_hit(self, state, team: str, slot: int):
        if not self.subs6:
            return None
        h = self._sub_rate(state, team, "ph") * self.subs6["ph_slot_factor"][str(slot + 1)]
        return self._bench_pick(state, team) if self._r(state).random() < h else None

    def pinch_runner(self, state, team: str, slot: int):
        if not self.subs6:
            return None
        if self._r(state).random() >= self._sub_rate(state, team, "pr"):
            return None
        bench = [p for p in state.team_obj[team].batters if p.pid not in state.in_game[team]]
        # with Speed (Phase 6) only a faster player runs for him; the pick among them by rank as for any substitute
        runner = state.lineup[team][slot]
        if bench and "speed" in bench[0].ratings:
            bench = [p for p in bench if p.ratings["speed"] > runner.ratings.get("speed", 0.0)]
        return self._bench_pick(state, team, bench)

    def defensive_subs(self, state, team: str) -> list:
        if not self.subs6:
            return []
        k = int(self._r(state).poisson(self._sub_rate(state, team, "def")))
        out, slots = [], list(range(9))
        for _ in range(k):
            p = self._bench_pick(state, team)
            if p is None or not slots:
                break
            w = np.array([self.def_slot[s_] for s_ in slots])
            slot = slots.pop(int(self._r(state).choice(len(slots), p=w / w.sum())))
            state.in_game[team].add(p.pid)      # reserved now; the engine records the entry
            out.append((slot, p))
        return out

    def relief_pitcher(self, state, team: str):
        if self.relief_coef:
            tm = state.team_obj[team]
            cands = [(p, r) for p, r in self._staff(tm) if p.pid not in state.used[team]]
            if not cands:
                return None
            margin = state.score[team] - state.score["away" if team == "home" else "home"]
            if abs(margin) >= LEVERAGE_BLOWOUT:
                lev = "blowout"
            elif state.inning >= LEVERAGE_LATE_INNING and abs(margin) <= LEVERAGE_CLOSE:
                lev = "late_close"
            else:
                lev = "other"
            return self._choose(state, cands, self.relief_coef, lev)
        avail = [p for p in state.team_obj[team].relievers if p.pid not in state.used[team]]
        if not avail:
            return None
        w = np.array([self.relw[min(p.order, len(self.relw) - 1)] for p in avail])   # ranks past the table share its last rank
        return avail[int(self._r(state).choice(len(avail), p=w / w.sum()))]
