"""Phase 2 game: the Phase 1 base-out state machine with real batters and pitchers.

Outcome of each plate appearance: odds-ratio matchup of batter and pitcher true rates
(engine.matchup) for K/BB/HBP/HR/1B/2B/3B/ROE/in-play out; the in-play out is subtyped
(plain out, SF, SH, FC) by base-out state from the league tables, and runners move by
the same empirical joint advancement and pre-PA base-running tables as Phase 1.
The home team bats with +eta/2 log runs along the batting quality direction and pitches
with eta/2 along the pitching direction (config.phase2 home_eta).

Earned runs follow the official scoring rules by reconstructing each half-inning:
  - a runner who reaches on an error is unearned; runs scoring on a play with an error
    or on a passed ball are unearned;
  - every error that prevents an out (reached on error; an out-class play with an error
    and no out recorded) adds a phantom out; once actual plus phantom outs reach three,
    every later run in the half-inning is unearned;
  - runs are charged to the pitcher responsible for the runner; a relief pitcher does
    not get the benefit of phantom outs from before he entered, so for runners charged
    to the current pitcher the count is actual outs plus phantom outs since his entry,
    and for runners left by an earlier pitcher it is the whole half-inning's count;
  - a batter who reaches on a fielder's choice that retires a runner left by an earlier
    pitcher becomes that pitcher's responsibility.
Runner advancement is not re-run without the error, so a run that would have scored
anyway on an error play is counted unearned.

Games are played by a GameSession (engine restructure, 2026-10-06): plate appearances forward, pitch by pitch,
with a pause point before every pitch; one controller per team; keyed random streams for the engine and for each
team's AI manager; save and restore at any pause point. PlayerGameEngine.play runs a session to the end.
"""
from __future__ import annotations

from bisect import bisect_right

import numpy as np

from config.phase1 import IN_PLAY_OUT_CLASS, MIN_CELL_N, PRE_PA_EVENTS, RESULTS
from config.phase2 import Phase2Config
from config.phase5 import MAX_PITCHES_HIST
from config.phase5 import load as load_pitch, load_solved
from engine.control import AIController, KIND as _KIND
from engine.decider import Decision
from engine.matchup import OUTCOMES, matchup_probs
from engine.pitch import N_SLOTS, SLOT_SYM, PitchModel, _DEST as SLOT_DEST_ARR
from engine.rng import Categorical
from engine.tables import AdvancementTable, OutcomeTable, PrePaEventTable

# batter stat columns and pitcher stat columns
B_G, B_PA, B_AB, B_H, B_2B, B_3B, B_HR, B_BB, B_HBP, B_K, B_SF, B_SH, B_ROE, B_GPA = range(14)   # B_GPA: games with a plate appearance
B_NCOL = 14
P_G, P_GS, P_BF, P_OUTS, P_H, P_HR, P_BB, P_HBP, P_K, P_R, P_ER, P_PITCH, P_WGS = range(13)  # P_WGS: weekend starts
P_NCOL = 13
_OUTING_COLS = (P_BF, P_K, P_BB, P_HBP, P_H, P_HR, P_R)
# box-score tables for the Phase 4 estimator: plate-appearance results by batting team x pitching
# team x (batting team at home), and each player's trials by opposing team x home
CELL_RESULTS = ("K", "BB", "HBP", "HR", "1B", "2B", "3B", "ROE", "OUT")
_CELL_IDX = {r: i for i, r in enumerate(CELL_RESULTS)}
TRIAL_KINDS = ("PA", "BIP", "HITS")       # BIP: balls in play other than reached on error
# per player and rate: sum over his trials of the true probability p and of p (1 - p), the expected
# count and its binomial variance given the opponents he actually faced (Phase 4 round trip): their
# pitcher, park and, for BABIP, their defense (the reached-on-error tilt moves the hit share; _babip_vs)
EXP_RATES = ("K", "BB", "HR", "BABIP", "XBH")
_HITS = frozenset(_CELL_IDX[r] for r in ("1B", "2B", "3B"))
_OUT = _CELL_IDX["OUT"]
_EV6 = {e: i for i, e in enumerate("BKSFPH")}
_EV7 = {e: i for i, e in enumerate("BKSFPHN")}            # config.phase5.EVENTS order
SLOT_DEST = SLOT_DEST_ARR.tolist()                         # per count and forward slot: next count, or -1 - outcome
_K, _BB = 0, 1                                             # rate order of the logit offsets (config.phase2.RATES)


def _centre(p: float, sd: float) -> float:
    """Logit shift d with E[expit(logit p + d + sd Z)] = p, Z standard normal (Gauss-Hermite)."""
    if not (0 < p < 1) or sd <= 0:
        return 0.0
    x, w = np.polynomial.hermite_e.hermegauss(40)
    w = w / w.sum()
    base = np.log(p / (1 - p))
    d = 0.0
    for _ in range(50):
        q = 1 / (1 + np.exp(-(base + d + sd * x)))
        f = float((w * q).sum()) - p
        g = float((w * q * (1 - q)).sum())
        d -= f / g
        if abs(f) < 1e-12:
            break
    return d


class GameState2:
    __slots__ = ("rng", "inning", "half", "outs", "bases", "score", "over", "run_rule_in_effect", "ended_by_run_rule",
                 "team_obj", "lineup", "slot", "pitcher", "outing", "used", "weekend", "inning_end",
                 "half_innings", "pa", "errors", "hits", "hr", "ab", "outs_pitched", "er_allowed",
                 "week", "day", "phantom", "p_phantom", "date", "pitch_log", "in_game", "subs", "batted",
                 "err_or", "catcher_arm", "of_arm", "pending_change", "sb_att", "sb_ok", "tournament")

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
        self.inning_end = False
        self.half_innings = []
        self.pa = {"away": 0, "home": 0}
        self.errors = {"away": 0, "home": 0}     # committed by that team's fielders
        self.hits = {"away": 0, "home": 0}
        self.hr = {"away": 0, "home": 0}
        self.ab = {"away": 0, "home": 0}
        self.outs_pitched = {"away": 0, "home": 0}
        self.er_allowed = {"away": 0, "home": 0}
        self.week, self.day, self.date = 0, 0, 0
        self.pitch_log = []   # (pitcher id, pitches) of every outing in this game
        self.in_game = {"away": set(), "home": set()}   # batters who have played (starters and substitutes)
        self.subs = {"away": 0, "home": 0}
        self.batted = {"away": set(), "home": set()}     # batters with a plate appearance
        self.err_or = {"away": 1.0, "home": 1.0}          # Phase 6: error odds of each side's defense
        self.catcher_arm = {"away": 0.0, "home": 0.0}
        self.of_arm = {"away": {}, "home": {}}
        self.sb_att = {"away": 0, "home": 0}     # steal attempts and stolen bases by the batting side
        self.sb_ok = {"away": 0, "home": 0}
        self.tournament = False                          # Phase 7: conference tournament or NCAA tournament game
        self.pending_change = {"away": False, "home": False}   # pulled at an inning's end: the reliever enters when the side next takes the field
        self.phantom = 0      # phantom outs this half-inning (errors that prevented an out)
        self.p_phantom = 0    # phantom outs since the current pitcher entered this half-inning

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
        n_teams = len(league.teams) if hasattr(league, "teams") else 2
        n_players = len(league.players) if hasattr(league, "players") else 32
        self.team_cell = np.zeros((n_teams, n_teams, 2, len(CELL_RESULTS)), dtype=np.int32)
        self.opp_trials = np.zeros((n_players, n_teams, 2, len(TRIAL_KINDS)), dtype=np.int32)
        self.exp_trials = np.zeros((n_players, len(EXP_RATES), 2))
        self.rate_cache: dict = {}
        self.neutral = False          # Phase 7: the current game is at a neutral site
        eta = cfg.home_eta / 2
        self.home_bat = eta * np.array(cfg.v_bat)
        self.home_pit = eta * np.array(cfg.v_pit)
        # Phase 5: pitch sequences from the count-state chain conditioned on the PA outcome
        self.pitch = PitchModel(load_pitch(), load_solved())
        self.tilt_cache: dict = {}
        self.q_cache: dict = {}
        self.fwd_cache: dict = {}
        self.pitch_rec = {"hist": np.zeros(MAX_PITCHES_HIST + 1, dtype=np.int64), "n_pa": 0, "pitches": 0, "fps": 0, "k2p": 0, "k2f": 0,
                          "reach": np.zeros(12, dtype=np.int64), "ab": np.zeros(12, dtype=np.int64), "h": np.zeros(12, dtype=np.int64),
                          "k": np.zeros(12, dtype=np.int64), "bb": np.zeros(12, dtype=np.int64),
                          "ev": np.zeros((12, 7), dtype=np.int64)}                  # pitch events by count before the pitch
        self.player_pitch = np.zeros((n_players, 6), dtype=np.int64)   # per player (as batter or pitcher): B, K, S, F, P, H
        self.starts: list = []                                        # (pitches, outs on his plate appearances, weekend)
        # Phase 6 fielding and base running (config.phase6)
        from config import phase6
        self.roe_cache: dict = {}
        self.sb = [0, 0]                                              # steal attempts, steals
        self.outings: list = []                                       # (pitcher, started, outs, weekday) of every outing
        self.outing_lines: list = []                                  # (pitcher, started, BF, K, BB, HBP, H, HR, R) of every outing
        self.fielding_on, self.speed_on = phase6.on("fielding"), phase6.on("speed")
        f6 = phase6.load().get("fielding6", {})
        self.err_share = f6.get("team_error", {}).get("error_share", {})
        # centring of the individual offsets: a spread on the logit scale moves the population-average
        # rate (Jensen); each component gets the logit shift delta that keeps the population average at the
        # league rate, from its base rate and total spread (scripts/build_phase6_fielding.py)
        self.delta = {"att": 0.0, "ok": 0.0, "xb": 0.0, "err": 0.0}
        if f6:
            sp, te = f6["speed"], f6["team_error"]
            self.delta = {"att": _centre(sp["attempt"]["rate"], sp["attempt"]["sd_logit"]),
                          "ok": _centre(sp["success"]["rate"], float(np.hypot(sp["success"]["sd_logit"], f6["arm_c"]["sd_logit"]))),
                          "xb": _centre(sp["extra_base"]["rate"], float(np.hypot(sp["extra_base"]["sd_logit"], f6["arm_of"]["sd_logit"]))),
                          "err": _centre(te["rate_per_chance"], te["total_sd"])}
        # steal attempt and success by the running x the fielding team's tier (logit cells, centred on
        # the play-by-play sample the league tables come from)
        self.sb_tier = f6.get("speed", {}).get("tier_logodds") if self.speed_on else None
        zs = f6.get("of_zone_share", {"lf": 1 / 3, "cf": 1 / 3, "rf": 1 / 3})
        self.of_zone = list(zs)
        self.of_zone_cum = np.cumsum([zs[k] for k in self.of_zone]) / sum(zs.values())

    def _key(self, batter, pitcher, home_batting: bool) -> tuple:
        """Cache key of a matchup: the listed home side and whether the game is at a neutral site (Phase 7:
        no home edge for either side, a league-average park)."""
        return (batter.pid, pitcher.pid, home_batting, self.neutral)

    def _probs(self, batter, pitcher, home_batting: bool) -> Categorical:
        key = self._key(batter, pitcher, home_batting)
        cat = self.cache.get(key)
        if cat is None:
            if self.neutral:
                zb, zp, park = batter.z, pitcher.z, None
            else:
                zb, zp = (batter.z + self.home_bat, pitcher.z) if home_batting else (batter.z, pitcher.z - self.home_pit)
                park = self.league.teams[(batter if home_batting else pitcher).team].park if hasattr(self.league, "teams") else None
            if park is not None:
                zb = zb + park          # the home team's park, for both teams' plate appearances
            p = matchup_probs(self.cfg, zb, zp, self.league.location)
            cat = Categorical(list(OUTCOMES), [p[o] for o in OUTCOMES])
            self.cache[key] = cat
            self.roe_cache[key] = (p["ROE"], p["OUT"])
            self.tilt_cache[key] = self.pitch.tilts(zb[_K], zb[_BB], zp[_K], zp[_BB], p["K"], p["BB"], p["HBP"])
            hits = p["1B"] + p["2B"] + p["3B"]
            self.rate_cache[key] = np.array([p["K"], p["BB"], p["HR"], hits / (hits + p["OUT"]), (p["2B"] + p["3B"]) / hits])
        return cat

    # ---- runner movement ----------------------------------------------------------------
    def _apply(self, st, dests, batter_runner, batter_to, errors, event=None, res=None):
        new = [None, None, None]
        scored, outs, occupied, retired = [], 0, set(), []
        bat_side, fld_side = st.batting_side, st.fielding_side
        cur = st.pitcher[fld_side].pid
        recon_team, recon_cur = st.outs + st.phantom, st.outs + st.p_phantom
        for origin in (3, 2, 1):
            r = st.bases[origin - 1]
            if r is None:
                continue
            d = dests[origin - 1] or str(origin)
            if d == "0":
                outs += 1; retired.append(r)
            elif d == "4":
                scored.append(r)
            else:
                tgt = int(d)
                while tgt in occupied and tgt > origin:
                    tgt -= 1
                if tgt in occupied:
                    outs += 1; retired.append(r)
                else:
                    occupied.add(tgt); new[tgt - 1] = r
        if batter_runner is not None:
            if res == "FC":
                earlier = [r for r in retired if r[0] != cur]
                if earlier:
                    batter_runner = (earlier[0][0],) + tuple(batter_runner[1:])
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
        self.pstats[cur][P_OUTS] += outs
        st.errors[fld_side] += errors
        for pid, unearned, *_ in scored:
            self.pstats[pid][P_R] += 1
            recon = recon_cur if pid == cur else recon_team
            if not (unearned or errors or event == "PB" or recon >= 3):
                self.pstats[pid][P_ER] += 1
                st.er_allowed[fld_side] += 1
        if res == "ROE" or (errors and res in ("FC", "SF", "SH", "IP_OUT", "FO", "GO", "GIDP", "DP") and outs == 0):
            st.phantom += 1; st.p_phantom += 1
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

    def _end_outing(self, st, side):
        o = st.outing.get(side)
        if o is not None:
            st.pitch_log.append((st.pitcher[side].pid, o["pitches"]))
            self.outings.append((st.pitcher[side].pid, int(o["starter"]), o["pa_outs"], st.date % 7))
            ps = self.pstats[st.pitcher[side].pid]
            self.outing_lines.append((st.pitcher[side].pid, int(o["starter"]), *(ps[c] - v for c, v in zip(_OUTING_COLS, o["ps0"]))))   # BF, K, BB, HBP, H, HR, R of the outing
        if o is not None and o["starter"]:
            self.starts.append((o["pitches"], o["pa_outs"], bool(st.weekend), st.pitcher[side].pid))

    def _bring_in(self, st, side, pitcher, starter):
        self._end_outing(st, side)
        st.pitcher[side] = pitcher
        st.used[side].add(pitcher.pid)
        st.p_phantom = 0
        ps = self.pstats[pitcher.pid]
        st.outing[side] = {"starter": starter, "pitches": 0, "runs": 0, "pa_outs": 0, "ps0": [ps[c] for c in _OUTING_COLS]}
        ps[P_G] += 1
        if starter:
            ps[P_GS] += 1
            if st.weekend:
                ps[P_WGS] += 1

    def _matchup_chain(self, batter, pitcher, home_batting: bool):
        """The matchup's pitch-chain slot weights and absorption matrix (engine.pitch), cached per game."""
        key = self._key(batter, pitcher, home_batting)
        c = self.q_cache.get(key)
        if c is None:
            qs = self.pitch.slots(self.pitch.chain(self.tilt_cache[key]))
            c = self.q_cache[key] = (qs, self.pitch.absorb_matrix(qs))
        return c

    def _forward(self, batter, pitcher, home_batting: bool, eo: float) -> list:
        """The matchup's forward pitch table against a defense with error odds eo (cached per game: a side's
        error odds are set at the start of the game)."""
        fk = (self._key(batter, pitcher, home_batting), eo)
        cum = self.fwd_cache.get(fk)
        if cum is None:
            m = self._pa_law(batter, pitcher, home_batting, eo)        # fills the matchup caches
            qs, h = self._matchup_chain(batter, pitcher, home_batting)
            cum = self.fwd_cache[fk] = self.pitch.forward(qs, h, m)
        return cum

    def _pa_law(self, batter, pitcher, home_batting: bool, eo: float) -> np.ndarray:
        """The PA outcome probabilities (OUTCOMES order) against a defense with error odds eo: the matchup's,
        with reached on error against in-play out tilted (_roe_tilt's exact marginal: P(ROE | ROE or out)
        -> odds x eo)."""
        m = np.array(self._probs(batter, pitcher, home_batting).cum)
        m = np.diff(np.concatenate([[0.0], m]))
        if eo != 1.0:
            i_roe, i_out = OUTCOMES.index("ROE"), OUTCOMES.index("OUT")
            tot = m[i_roe] + m[i_out]
            r = m[i_roe] / tot
            r2 = r * eo / (1 - r + r * eo)
            m[i_roe], m[i_out] = r2 * tot, (1 - r2) * tot
        return m

    # ---- Phase 6: base running and fielding --------------------------------------------------
    def _lead_stealer(self, st, bat):
        """The runner who would steal: on first with second open, else on second with third open."""
        if not self.speed_on:
            return None
        b = st.bases
        r = b[0] if (b[0] is not None and b[1] is None) else (b[1] if (b[1] is not None and b[2] is None) else None)
        return st.lineup[bat][r[2]] if r is not None and len(r) > 2 else None

    def _roe_tilt(self, batter, pitcher, home_batting, res, eo, rng):
        """Reached on error against an in-play out, tilted by the fielding team's error odds; each
        keeps its probability otherwise (exact marginal: P(ROE | ROE or out) -> odds x eo)."""
        p_roe, p_out = self.roe_cache[self._key(batter, pitcher, home_batting)]
        r = p_roe / (p_roe + p_out)
        r2 = r * eo / (1 - r + r * eo)
        if res == "ROE" and r2 < r:
            return "OUT" if rng.random() < 1 - r2 / r else res
        if res == "OUT" and r2 > r:
            return "ROE" if rng.random() < (r2 - r) / (1 - r) else res
        return res

    def _babip_vs(self, batter, pitcher, home_batting, eo):
        """P(hit | hit or in-play out) against a defense with error odds eo. The reached-on-error tilt
        (_roe_tilt) moves in-play outs to reached on error and back, so the hit share among hits and outs
        depends on the fielding team: an error-prone defense leaves fewer outs. Exact under the tilt."""
        key = self._key(batter, pitcher, home_batting)
        b = self.rate_cache[key][3]
        if eo == 1.0:
            return b
        p_roe, p_out = self.roe_cache[key]
        hits = p_out * b / (1 - b)
        r = p_roe / (p_roe + p_out)
        r2 = r * eo / (1 - r + r * eo)
        out = p_out * (1 - (r2 - r) / (1 - r)) if r2 > r else p_out + p_roe * (1 - r2 / r)
        return hits / (hits + out)

    def _extra_bases(self, st, bat, fld, res, dests, bases0, rng):
        """Runners' extra bases on a single (first to third/home, second to home) or double (first to
        home): the league probability of the cell, tilted on the logit scale by the runner's speed
        and the arm of the outfielder the ball went to (exact marginal per runner)."""
        cases = ((1, ("3", "4"), "2", "3"), (2, ("4",), "3", "4")) if res == "1B" else ((1, ("4",), "3", "4"),)
        zone = self.of_zone[int(np.searchsorted(self.of_zone_cum, rng.random(), side="right"))]
        arm = st.of_arm[fld].get(zone, 0.0)
        code = "".join("0" if b is None else "1" for b in bases0)
        for origin, extra, std, target in cases:
            r = bases0[origin - 1]
            if r is None or len(r) < 3:
                continue
            p0 = self.advance.extra_prob(res, st.outs, code, origin, extra, std)
            if p0 is None or p0 >= 1:
                continue
            runner = st.lineup[bat][r[2]]
            x = np.log(p0 / (1 - p0)) + runner.run[2] - arm + self.delta["xb"]
            p1 = 1 / (1 + np.exp(-x))
            d = dests[origin - 1]
            if d in extra and p1 < p0 and rng.random() < 1 - p1 / p0:
                dests[origin - 1] = std
            elif d == std and p1 > p0 and rng.random() < (p1 - p0) / (1 - p0):
                dests[origin - 1] = target
        return dests

    def _fielding_context(self, st):
        """Per side, at the start of a game: the error odds of its defense (team error log-odds plus
        each fielder's at his position, weighted by the position's share of errors), the catcher's
        arm and the outfielders' arms."""
        for side in ("away", "home"):
            tm = st.team_obj[side]
            if not self.fielding_on:
                st.err_or[side], st.catcher_arm[side], st.of_arm[side] = 1.0, 0.0, {}
                continue
            x = tm.err_team
            arms = {}
            for p in st.lineup[side]:
                x += self.err_share.get(p.pos, 0.0) * p.err
                if p.pos in ("lf", "cf", "rf", "c"):
                    arms[p.pos] = p.arm
            st.err_or[side] = float(np.exp(x + self.delta["err"]))
            st.catcher_arm[side] = arms.pop("c", 0.0)
            st.of_arm[side] = arms

    def _sub(self, st, side, player, slot):
        """A substitute takes lineup slot `slot` for the rest of the game (pinch hitter, pinch runner,
        defensive or blowout substitution); the player he replaces cannot return."""
        if player is None:
            return
        st.lineup[side] = list(st.lineup[side])
        st.lineup[side][slot] = player
        st.in_game[side].add(player.pid)
        self.bstats[player.pid][B_G] += 1
        st.subs[side] += 1

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

    def _record_pitches(self, batter, pitcher, seq: str, res: str) -> int:
        """Record the pitch-level statistics of a plate appearance's sequence (played forward, GameSession)."""
        pr = self.pitch_rec
        n = len(seq)
        pr["n_pa"] += 1; pr["pitches"] += n
        pr["hist"][min(n, MAX_PITCHES_HIST)] += 1
        first = next((c for c in seq if c != "N"), "B")
        pr["fps"] += first in "KSFP"
        b = s = 0
        seen = set()
        pp, bp = self.player_pitch[pitcher.pid], self.player_pitch[batter.pid]
        ev = pr["ev"]
        for c in seq:
            seen.add(b * 3 + s)
            ev[b * 3 + s, _EV7[c]] += 1
            if c != "N":
                ei = _EV6[c]
                pp[ei] += 1; bp[ei] += 1
                if s == 2:
                    pr["k2p"] += 1; pr["k2f"] += c == "F"
            if c == "B":
                b += 1
            elif c in "KS":
                s += 1
            elif c == "F":
                s = min(s + 1, 2)
        is_ab = res not in ("BB", "HBP", "SF", "SH")
        for i in seen:
            pr["reach"][i] += 1
            pr["ab"][i] += is_ab
            pr["h"][i] += res in ("1B", "2B", "3B", "HR")
            pr["k"][i] += res == "K"
            pr["bb"][i] += res == "BB"
        return n

    def _record(self, st, batter, pitcher, res, seq):
        bs, ps = self.bstats[batter.pid], self.pstats[pitcher.pid]
        bat = st.batting_side
        bs[B_PA] += 1; ps[P_BF] += 1; st.pa[bat] += 1
        st.batted[bat].add(batter.pid)
        ci = _CELL_IDX.get(res, _OUT)
        btid, ptid, h = st.team_obj[bat].tid, st.team_obj[st.fielding_side].tid, int(bat == "home")
        self.team_cell[btid, ptid, h, ci] += 1
        ot = self.opp_trials
        ot[batter.pid, ptid, h, 0] += 1
        ot[pitcher.pid, btid, h, 0] += 1
        rp = self.rate_cache.get(self._key(batter, pitcher, bool(h)))
        if rp is not None:
            ex = self.exp_trials
            ex[batter.pid, :3, 0] += rp[:3]; ex[batter.pid, :3, 1] += rp[:3] * (1 - rp[:3])
            ex[pitcher.pid, :3, 0] += rp[:3]; ex[pitcher.pid, :3, 1] += rp[:3] * (1 - rp[:3])
        if ci in _HITS or ci == _OUT:
            b = self._babip_vs(batter, pitcher, bool(h), st.err_or[st.fielding_side]) if rp is not None else None
        if ci in _HITS:
            ot[batter.pid, ptid, h, 1] += 1
            ot[batter.pid, ptid, h, 2] += 1
            if rp is not None:
                ex[batter.pid, 3, 0] += b; ex[batter.pid, 3, 1] += b * (1 - b)
                ex[batter.pid, 4, 0] += rp[4]; ex[batter.pid, 4, 1] += rp[4] * (1 - rp[4])
        elif ci == _OUT:             # in-play out (incl. SF, SH, FC)
            ot[batter.pid, ptid, h, 1] += 1
            if rp is not None:
                ex[batter.pid, 3, 0] += b; ex[batter.pid, 3, 1] += b * (1 - b)
        n = self._record_pitches(batter, pitcher, seq, res)
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
                self.roe_count += 1; bs[B_ROE] += 1
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

    def _half(self, st, dec):
        """One half-inning on an existing game state (scripts/build_phase2_run_scale.py measures the engine this
        way): a session over `st`, both sides managed by `dec`, played to the end of the half."""
        sess = GameSession(self, st.rng, st.team_obj["home"], st.team_obj["away"], st.weekend, dec)
        sess.st = st
        sess._begin_half()
        ph = "pre_pa"
        while ph != "half_end":
            if ph == "pre_pa":
                ph = sess._pre_pa()
            else:
                while not sess._pitch():
                    pass
                ph = sess._finish_pa()
        st.half_innings.append((st.inning, st.half, st.score[st.batting_side] - sess.half_start[0], st.pa[st.batting_side] - sess.half_start[1]))

    def play(self, rng, home, away, weekend, dec, week=0, day=0, date=0, neutral=False, tournament=False, controllers=None) -> GameState2:
        """Play a whole game: a GameSession run to the end, both sides managed by `dec` unless `controllers`
        ({side: Controller}) says otherwise."""
        sess = GameSession(self, rng, home, away, weekend, dec, week=week, day=day, date=date, neutral=neutral,
                           tournament=tournament, controllers=controllers)
        sess.run()
        return sess.st


class _Positioned:
    """A stream positioned at a decision point on first use (most decisions draw nothing)."""
    __slots__ = ("stream", "pos", "gen")

    def __init__(self, stream, pos):
        self.stream, self.pos, self.gen = stream, pos, None

    def __getattr__(self, name):
        if self.gen is None:
            self.gen = self.stream.at(*self.pos)
        return getattr(self.gen, name)


SIDES = ("away", "home")
_SALT = {"away": 0x9E3779B97F4A7C15, "home": 0xC2B2AE3D27D4EB4F}   # per-side key offsets of the AI streams
STOPS = ("pitch", "pa", "half", "inning", "three_innings", "game")


class GameSession:
    """One game played forward, pitch by pitch, with a pause point before every pitch (engine restructure,
    2026-10-06; CLAUDE.md, in-game management and sim controls).

    - Plate appearances are played forward through the matchup's transformed pitch chain (engine.pitch,
      `forward`): the same joint law of outcome and pitch sequence as drawing the outcome first.
    - Each side has its own controller (engine.control). Every decision goes to the side it belongs to, with a
      generator positioned on that side's keyed stream; the engine's own draws come from a third keyed stream,
      positioned per plate appearance. So a decision's answer never moves a draw that does not depend on it.
    - `run(stop)` plays until `stop(session)` is true at a pause point (before a pitch) or the game ends;
      `sim_ahead` stops at the next plate appearance, half inning, inning, three innings or the end, with the AI
      managing a side meanwhile; `save` / `load` pickle the session (game state, stream positions, the engine and
      its season accumulators) at a pause point.
    """

    def __init__(self, eng, rng, home, away, weekend, dec, week=0, day=0, date=0, neutral=False, tournament=False,
                 controllers=None, log=False):
        from engine.rng import KeyedStream
        self.eng, self.book = eng, dec
        k0, k1 = (int(x) for x in rng.integers(0, 2 ** 63, size=2))
        self.key = (k0, k1)
        self.engine_stream = KeyedStream([k0, k1])
        self.ai = {s: KeyedStream([k0 ^ _SALT[s], k1]) for s in SIDES}
        self.ctrl = dict(controllers) if controllers else {s: AIController(dec) for s in SIDES}
        self.neutral = neutral
        st = self.st = GameState2(None, home, away, weekend)
        st.tournament = tournament
        st.week, st.day, st.date = week, day, date
        self.pa_serial = 0
        self.calls: dict = {}
        self.phase = "pregame"
        self.log = [] if log else None
        self.pa = None            # the plate appearance in progress
        self.half_start = (0, 0)  # runs and PAs of the batting side when the half began

    # ---- decisions -------------------------------------------------------------------------
    def ask(self, side: str, kind: str, *args):
        ck = (side, kind)
        calls = self.calls
        n = calls[ck] = calls.get(ck, -1) + 1
        return self.ctrl[side].answer(kind, self.st, _Positioned(self.ai[side], (_KIND[kind], self.pa_serial, n)), *args)

    def set_controller(self, side: str, controller) -> None:
        self.ctrl[side] = controller

    # ---- pause points ----------------------------------------------------------------------
    def point(self) -> dict:
        """Where the game stands at a pause point (before a pitch)."""
        st, pa = self.st, self.pa
        return {"inning": st.inning, "half": st.half, "outs": st.outs, "bases": st.base_code, "count": (pa["b"], pa["s"]),
                "score": dict(st.score), "pa_serial": self.pa_serial, "pitch": len(pa["seq"]),
                "batter": pa["batter"].pid, "pitcher": pa["pitcher"].pid, "batting": st.batting_side}

    def _stopper(self, target: str):
        """A stop rule for sim-ahead from the current pause point."""
        st = self.st
        if target == "pitch":
            return lambda s: True
        if target == "pa":
            n0 = self.pa_serial
            return lambda s: s.pa_serial > n0
        if target == "half":
            h0 = (st.inning, st.half)
            return lambda s: (s.st.inning, s.st.half) != h0
        if target in ("inning", "three_innings"):
            k = 1 if target == "inning" else 3
            i0, h0 = st.inning, st.half
            return lambda s: s.st.inning > i0 + k or (s.st.inning == i0 + k and (s.st.half == h0 or h0 == "T"))
        if target == "game":
            return None
        raise ValueError(target)

    def sim_ahead(self, target: str, ai_side: str | None = None, ai=None):
        """Play to the next stopping point (STOPS); with `ai_side`, the AI controller `ai` manages that side
        meanwhile and the side's own controller is handed back at the stop."""
        keep = self.ctrl.get(ai_side) if ai_side else None
        if ai_side:
            self.ctrl[ai_side] = ai
        try:
            # from a pause point, "next" means the next one: leave the current pause point first
            return self.run(self._stopper(target), skip_current=self.phase == "pitch")
        finally:
            if ai_side:
                self.ctrl[ai_side] = keep

    def save(self, include_engine: bool = True) -> bytes:
        """The session at a pause point, pickled: the game state, the stream positions, both controllers and the
        manager's season state. With include_engine (the default) also the engine and its season accumulators,
        so the save is complete on its own; without it, `load` reattaches a live engine (the accumulators only
        collect statistics; play never reads them)."""
        import pickle
        eng = self.eng
        if not include_engine:
            self.eng = None
        try:
            return pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            self.eng = eng

    @staticmethod
    def load(blob: bytes, engine=None) -> "GameSession":
        import pickle
        s = pickle.loads(blob)
        if engine is not None:
            s.eng = engine
        if s.eng is None:
            raise ValueError("this save has no engine: pass engine=")
        return s

    # ---- the game loop ---------------------------------------------------------------------
    def run(self, stop=None, skip_current: bool = False):
        """Play until `stop(self)` is true at a pause point (returns `point()`), or to the end (returns None)."""
        eng = self.eng
        eng.neutral = self.neutral
        while True:
            ph = self.phase
            if ph == "pitch":
                if stop is not None:
                    if not skip_current and stop(self):
                        return self.point()
                    skip_current = False
                    if self._pitch():
                        self.phase = self._finish_pa()
                else:
                    while not self._pitch():
                        pass
                    self.phase = self._finish_pa()
            elif ph == "pre_pa":
                self.phase = self._pre_pa()
            elif ph == "half_start":
                self._begin_half()
                self.phase = "pre_pa"
            elif ph == "half_end":
                self.phase = self._end_half()
            elif ph == "pregame":
                self._pregame()
                self.phase = "half_start"
            elif ph == "final":
                self._final()
                self.phase = "over"
                return None
            else:
                return None

    def _pregame(self):
        eng, st = self.eng, self.st
        eng.q_cache.clear()          # matchup chains are rebuilt per game (memory); the tilts stay cached
        eng.fwd_cache.clear()
        rng = self.engine_stream.at(0, 0)
        st.rng = rng
        st.run_rule_in_effect = rng.random() < eng.rules.p_run_rule_in_effect
        for side in SIDES:
            st.lineup[side] = self.ask(side, "lineup", side)
            for p in st.lineup[side]:
                eng.bstats[p.pid][B_G] += 1
                st.in_game[side].add(p.pid)
            eng._bring_in(st, side, self.ask(side, "starting_pitcher", side), True)
        eng._fielding_context(st)

    def _begin_half(self):
        eng, st = self.eng, self.st
        st.outs, st.bases = 0, [None, None, None]
        st.phantom = st.p_phantom = 0
        bat, fld = st.batting_side, st.fielding_side
        self.half_start = (st.score[bat], st.pa[bat])
        if st.pending_change[fld]:
            # a pitcher pulled at the end of an inning is replaced when his side takes the field again,
            # so a reliever never appears in a game that ends first (as in the play-by-play)
            st.pending_change[fld] = False
            nxt = self.ask(fld, "relief_pitcher", fld)
            if nxt is not None:
                eng._bring_in(st, fld, nxt, False)
        for slot, player in self.ask(fld, "defensive_subs", fld):
            eng._sub(st, fld, player, slot)

    def _pre_pa(self) -> str:
        """Base running before the plate appearance, then its setup; 'pitch' when it starts, 'half_end' if the
        half ends first."""
        eng, st = self.eng, self.st
        if st.outs >= 3 or st.over:
            return "half_end"
        self.pa_serial += 1
        self.calls = {}
        rng = st.rng = self.engine_stream.at(1, self.pa_serial)
        bat, fld = st.batting_side, st.fielding_side
        # pre-PA base running events: one draw per opportunity, again after each event until none occurs
        # (scripts/build_engine_tables.py)
        while any(b is not None for b in st.bases) and st.outs < 3 and not st.over:
            steal = self.ask(bat, "steal_attempt")
            runner = eng._lead_stealer(st, bat)
            ta = to_ = 0.0
            if eng.sb_tier:
                cell = f"{st.team_obj[bat].tier}|{st.team_obj[fld].tier}"
                ta, to_ = eng.sb_tier["attempt"]["cell"][cell], eng.sb_tier["success"]["cell"][cell]
            sb_or = np.exp(runner.run[0] + eng.delta["att"] + ta) if runner is not None else 1.0
            ev = eng.pre_pa.draw_event(st.outs, st.base_code, rng.random(), sb_or)
            if steal == Decision.NO and ev == "SB_ATT":
                ev = None
            if ev is None:
                break
            ok_or = 1.0
            if ev == "SB_ATT" and runner is not None:
                ok_or = np.exp(runner.run[1] - st.catcher_arm[fld] + eng.delta["ok"] + to_)
            out = eng.pre_pa.draw_outcome(ev, st.outs, st.base_code, rng.random(), ok_or)
            if out is None:
                break
            dests, _, err = out
            if ev == "SB_ATT":
                eng.sb[0] += 1
                eng.sb[1] += "0" not in dests
                st.sb_att[bat] += 1
                st.sb_ok[bat] += "0" not in dests
            if self.log is not None:
                self.log.append(("run", self.pa_serial, ev, tuple(dests)))
            if eng._apply(st, dests, None, None, err, event=ev) and st.half == "B":
                eng._end_check(st, True)
        if st.outs >= 3 or st.over:
            return "half_end"
        eng._sub(st, bat, self.ask(bat, "pinch_hit", bat, st.slot[bat] % 9), st.slot[bat] % 9)
        batter = st.lineup[bat][st.slot[bat] % 9]
        st.slot[bat] += 1
        pitcher = st.pitcher[fld]
        self.ask(fld, "intentional_walk")
        bunt = self.ask(bat, "bunt")
        home_batting = bat == "home"
        self.pa = {"batter": batter, "pitcher": pitcher, "bunt": bunt, "cum": eng._forward(batter, pitcher, home_batting, st.err_or[fld]),
                   "b": 0, "s": 0, "seq": [], "res": None}
        return "pitch"

    def _pitch(self) -> bool:
        """One pitch; True when it ends the plate appearance."""
        pa = self.pa
        i = pa["b"] * 3 + pa["s"]
        row = pa["cum"][i]
        k = bisect_right(row, self.st.rng.random() * row[-1])
        if k >= N_SLOTS:
            k = N_SLOTS - 1
        sym, d = SLOT_SYM[k], SLOT_DEST[i][k]
        pa["seq"].append(sym)
        if self.log is not None:
            self.log.append(("p", self.pa_serial, sym))
        if d >= 0:
            pa["b"], pa["s"] = divmod(d, 3)
            return False
        pa["res"] = OUTCOMES[-1 - d]
        return True

    def _finish_pa(self) -> str:
        eng, st, pa = self.eng, self.st, self.pa
        rng = st.rng
        bat, fld = st.batting_side, st.fielding_side
        batter, pitcher, res = pa["batter"], pa["pitcher"], pa["res"]
        eo = st.err_or[fld]
        if res == "OUT":
            res = eng._subtype(st, rng, pa["bunt"])
        bases0 = list(st.bases)
        dests, b_to, err = eng.advance.draw(res, st.outs, st.base_code, rng.random(), [rng.random() for _ in range(4)], eo)
        if res in ("1B", "2B") and eng.speed_on:
            dests = eng._extra_bases(st, bat, fld, res, dests, bases0, rng)
        eng._record(st, batter, pitcher, res, "".join(pa["seq"]))
        if self.log is not None:
            self.log.append(("pa", self.pa_serial, batter.pid, pitcher.pid, res, tuple(dests), b_to))
        outs0 = st.outs
        slot = (st.slot[bat] - 1) % 9
        scored = eng._apply(st, dests, (pitcher.pid, res == "ROE", slot), b_to, err, res=res)
        if b_to in ("1", "2", "3") and not st.over:
            eng._sub(st, bat, self.ask(bat, "pinch_runner", bat, slot), slot)
        st.outing[fld]["runs"] += scored
        st.outing[fld]["pa_outs"] += st.outs - outs0
        if scored and st.half == "B":
            eng._end_check(st, True)
        self.pa = None
        if st.over:
            return "half_end"
        st.inning_end = st.outs >= 3
        if self.ask(fld, "pitching_change") == Decision.YES:
            if st.inning_end:
                st.pending_change[fld] = True
            else:
                nxt = self.ask(fld, "relief_pitcher", fld)
                if nxt is not None:
                    eng._bring_in(st, fld, nxt, False)
        return "pre_pa"

    def _end_half(self) -> str:
        eng, st = self.eng, self.st
        bat = st.batting_side
        st.half_innings.append((st.inning, st.half, st.score[bat] - self.half_start[0], st.pa[bat] - self.half_start[1]))
        if st.over:
            return "final"
        eng._end_check(st, False)
        if st.over:
            return "final"
        if st.half == "T":
            st.half = "B"
        else:
            st.inning += 1
            st.half = "T"
        return "half_start"

    def _final(self):
        eng, st = self.eng, self.st
        for side in SIDES:
            eng._end_outing(st, side)
            for pid in st.batted[side]:
                eng.bstats[pid][B_GPA] += 1
        if hasattr(self.book, "record_game"):
            self.book.record_game(st)
        if self.log is not None:
            self.log.append(("final", st.inning, st.score["away"], st.score["home"]))
