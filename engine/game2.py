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
from config.phase5 import EVENTS as PITCH_EVENTS, MAX_PITCHES_HIST
from config.phase5 import load as load_pitch, load_solved
from engine.control import AIController, KIND as _KIND
from engine.decider import Decision
from engine.matchup import OUTCOMES, matchup_probs
from engine.pitch import N_SLOTS, SLOT_SYM, PitchModel, _DEST as SLOT_DEST_ARR
from engine.rng import Categorical
from engine.tables import AdvancementTable, OutcomeTable, PrePaEventTable, _ok_split

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
                 "err_or", "catcher_arm", "of_arm", "pending_change", "sb_att", "sb_ok", "tournament",
                 "ibb", "cur_slot", "mound")

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
        self.ibb = {"away": 0, "home": 0}                # PR B: intentional walks received by the batting side
        self.cur_slot = 1                                # PR B: lineup slot (1-9) of the batter at the plate
        self.mound = {"free": {"away": 0, "home": 0}, "trips": {}, "batter": {}}   # PR B: coach trips (NCAA 9-4)
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
        # PR B: decisions that change outcomes (config.decisions)
        from config import decisions as cdec
        self.dec_on = cdec.on("decisions")
        self.dec_steal, self.dec_bunt, self.dec_ibb = cdec.on("steals"), cdec.on("bunts"), cdec.on("ibb")
        self.ibb_count, self.bunt_rec, self.path_rec, self.path_all_rec = 0, {"bunts": 0, "SH": 0, "hits": 0}, [], []
        if self.dec_on:
            from engine.decisions import DecisionModels
            d_in = cdec.load()
            self.dm = DecisionModels(d_in)
            self.po_cs_share = d_in["pickoff_scoring"]["cs_share"]
            hold = d_in["pitcher_hold"]
            self.sd_hold_att, self.sd_hold_suc = hold["sd_attempt_logit"], hold["sd_success_logit"]
            smp = d_in["steals"]["sample"]
            if f6:
                sp = f6["speed"]
                # the runner and hold offsets on the per-pitch hazard, centred so the league rate is kept (Jensen)
                self.delta["att_pitch"] = _centre(smp["attempts"] / smp["eligible_pitches"], float(np.hypot(sp["attempt"]["sd_logit"], self.sd_hold_att)))
                self.delta["ok_pitch"] = self._centre_success(smp["steals"] / smp["attempts"], f6["arm_c"]["sd_logit"])
            else:
                self.delta["att_pitch"] = self.delta["ok_pitch"] = 0.0
        zs = f6.get("of_zone_share", {"lf": 1 / 3, "cf": 1 / 3, "rf": 1 / 3})
        self.of_zone = list(zs)
        self.of_zone_cum = np.cumsum([zs[k] for k in self.of_zone]) / sum(zs.values())

    def _centre_success(self, p: float, sd_arm: float) -> float:
        """PR B: the success offset's centring. The fitted success rate is the attempting runners' (the play-by-play
        pools the attempts), and a runner's attempt and success propensities are correlated (engine.league: one
        speed factor), so the shift d keeps the attempt-weighted success at p: sum_i w_i E[expit(logit p + s_i - arm
        + d)] / sum_i w_i = p, w_i the runner's attempt odds factor, the catcher's arm N(0, sd_arm)."""
        runs = np.array([pl.run for pl in self.league.players if getattr(pl, "run", None) is not None], float)
        if len(runs) == 0 or not (0 < p < 1):
            return 0.0
        w = np.exp(runs[:, 0])
        x, gw = np.polynomial.hermite_e.hermegauss(20)
        gw = gw / gw.sum()
        base = np.log(p / (1 - p))
        d = 0.0
        for _ in range(50):
            q = 1 / (1 + np.exp(-(base + d + runs[:, 1][:, None] - sd_arm * x[None, :])))
            f = float((w[:, None] * gw[None, :] * q).sum() / w.sum()) - p
            g = float((w[:, None] * gw[None, :] * q * (1 - q)).sum() / w.sum())
            d -= f / g
            if abs(f) < 1e-12:
                break
        return d

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

    def _forward(self, batter, pitcher, home_batting: bool, eo: float, adj=None) -> list:
        """The matchup's forward pitch table against a defense with error odds eo (cached per game: a side's
        error odds are set at the start of the game).
        adj (PR B): the batter's lineup slot. The matchup law m is the batter's season law over every plate
        appearance, bunts and intentional walks included, so when he swings away he plays
        m_sw = (m - b law_bunt - i e_BB) / (1 - b - i), with b and i his slot's average shares of called bunts and
        intentional walks (engine.decisions slot_shares) and law_bunt a called bunt's law pooled over the states
        bunts happen in. Over a season his totals are m again (the AI's calls average b and i in his slot); in a given
        state they are not, as in the data (more outs where teams bunt, more walks where they walk the batter). A
        human who swings away faces the same m_sw."""
        fk = (self._key(batter, pitcher, home_batting), eo, adj)
        hit = self.fwd_cache.get(fk)
        if hit is not None:
            self.last_law = hit[1]
            return hit[0]
        if True:
            m = self._pa_law(batter, pitcher, home_batting, eo)        # fills the matchup caches
            if adj is not None:
                b, i = self.dm.slot_shares(adj)
                b, i = (b if self.dec_bunt else 0.0), (i if self.dec_ibb else 0.0)
                m = m - b * self.dm.bunt_law("*", "*")[0]
                m[OUTCOMES.index("BB")] -= i
                m = np.maximum(m, 0.0) / max(1.0 - b - i, 1e-9)
                m = m / m.sum()
            qs, h = self._matchup_chain(batter, pitcher, home_batting)
            cum = self.pitch.forward(qs, h, m)
            self.fwd_cache[fk] = (cum, m)
            self.last_law = m                  # the law this plate appearance plays (the Phase 4 test's expectation)
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

    def _record(self, st, batter, pitcher, res, seq, skip_pitches=0, pitch_to=None, law=None):
        """Record a plate appearance. seq None: an intentional walk awarded without pitches (NCAA 8-2-b), no pitch
        statistics. skip_pitches: pitches already charged to an earlier pitcher at a mid-PA change; the rest go to
        `pitch_to` (the pitcher who threw them; `pitcher` is charged with the plate appearance, NCAA 10-22-b)."""
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
        if law is not None:
            rp = _rates_of(law)                # PR B: the law the plate appearance played (decisions taken into account)
        else:
            rp = self.rate_cache.get(self._key(batter, pitcher, bool(h)))
        if rp is not None:
            ex = self.exp_trials
            ex[batter.pid, :3, 0] += rp[:3]; ex[batter.pid, :3, 1] += rp[:3] * (1 - rp[:3])
            ex[pitcher.pid, :3, 0] += rp[:3]; ex[pitcher.pid, :3, 1] += rp[:3] * (1 - rp[:3])
        if ci in _HITS or ci == _OUT:
            if rp is None:
                b = None
            elif law is not None:
                b = rp[3]                      # the law is already against this defense (_pa_law)
            else:
                b = self._babip_vs(batter, pitcher, bool(h), st.err_or[st.fielding_side])
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
        if seq is not None:
            thrower = pitch_to or pitcher
            n = self._record_pitches(batter, thrower, seq, res) - skip_pitches
            self.pstats[thrower.pid][P_PITCH] += n
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


_O_BB, _O_K, _O_HBP = OUTCOMES.index("BB"), OUTCOMES.index("K"), OUTCOMES.index("HBP")
_WALK_TO_PRIOR = ((2, 0), (2, 1), (3, 0), (3, 1), (3, 2))        # config.decisions.WALK_TO_PRIOR (NCAA 10-22-b)
_SWING = tuple(k for k, sym in enumerate(SLOT_SYM) if sym in "SFP")


def _forced_dest(sym: str, b: int, s: int) -> int:
    """Next count (index) or -1 - outcome for a pitch event drawn outside the matchup chain (a called bunt). A bunt
    in play ends the plate appearance (the bunt table's result)."""
    i = b * 3 + s
    if sym == "B":
        return i + 3 if b < 3 else -1 - _O_BB
    if sym in "KS":
        return i + 1 if s < 2 else -1 - _O_K
    if sym == "F":
        return i + 1 if s < 2 else (-1 - _O_K)        # a foul bunt with two strikes is a strikeout (NCAA 10-23)
    if sym == "H":
        return -1 - _O_HBP
    if sym == "P":
        return -1 - OUTCOMES.index("OUT")
    return i                                           # N


def _swing_draw(row: list, u: float) -> int:
    """A hit-and-run pitch: the slots of a swing (swinging strike, foul, ball in play), renormalised."""
    w = [row[k] - (row[k - 1] if k else 0.0) for k in range(N_SLOTS)]
    sw = [(k, w[k]) for k in _SWING if w[k] > 0]
    tot = sum(x for _, x in sw)
    acc, t = 0.0, u * tot
    for k, x in sw:
        acc += x
        if t < acc:
            return k
    return sw[-1][0]


def _hit_and_run(res: str, dests: list) -> list:
    """GUESS (config.decisions.HIT_AND_RUN_RUNNER_EXTRA): the runner from first, running on the pitch, takes third on
    a single and is safe at second on an out (no double play)."""
    d = list(dests)
    if res == "1B" and d[0] in ("2",):
        d[0] = "3"
    elif res in ("IP_OUT", "FC") and d[0] == "0":
        d[0] = "2"
    return d


_E_BB = np.eye(len(OUTCOMES))[OUTCOMES.index("BB")]
_I_K, _I_BB, _I_HR = OUTCOMES.index("K"), OUTCOMES.index("BB"), OUTCOMES.index("HR")
_I_1B, _I_2B, _I_3B, _I_OUT = OUTCOMES.index("1B"), OUTCOMES.index("2B"), OUTCOMES.index("3B"), OUTCOMES.index("OUT")


def _rates_of(law) -> np.ndarray:
    """K, BB, HR per PA, BABIP (hits over hits and in-play outs) and the extra-base share of hits of an outcome law
    (OUTCOMES order), as rate_cache holds them for a matchup."""
    hits = law[_I_1B] + law[_I_2B] + law[_I_3B]
    return np.array([law[_I_K], law[_I_BB], law[_I_HR], hits / max(hits + law[_I_OUT], 1e-12), (law[_I_2B] + law[_I_3B]) / max(hits, 1e-12)])


def _n_eligible(seq: list, res: str) -> int:
    """Balls and strikes in a sequence (a steal's possible pitches), the last pitch not counted on a hit batsman."""
    n = sum(c in "BKS" for c in seq)
    return n - (res == "HBP" and bool(seq) and seq[-1] in "BKS")


def _final_count(seq: list) -> str:
    b = s = 0
    for c in seq[:-1]:
        if c == "B":
            b += 1
        elif c in "KS":
            s += 1
        elif c == "F" and s < 2:
            s += 1
    return f"{min(b, 3)}-{min(s, 2)}"


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
                    r = self._pitch()
                else:
                    r = self._pitch()
                    while not r:
                        r = self._pitch()
                if r:
                    self.phase = self._finish_pa() if r is True else self._abort_pa()
            elif ph == "pa_end":
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
        """The start of a plate appearance: the pinch hitter, the intentional walk and the bunt are decided in the
        base-out state as it begins (as the play-by-play's models are fitted), then the base running during it that is
        not a pitch-level steal (wild pitches, passed balls, pickoffs, balks; drawn here, before the pitches), then its
        setup. Returns 'pitch' when it starts, 'pa_end' for an intentional walk (awarded without pitches), 'half_end'
        if the half ends first (the batter then leads off the next inning)."""
        eng, st = self.eng, self.st
        if st.outs >= 3 or st.over:
            return "half_end"
        self.pa_serial += 1
        self.calls = {}
        rng = st.rng = self.engine_stream.at(1, self.pa_serial)
        bat, fld = st.batting_side, st.fielding_side
        dec_on = eng.dec_on
        steal_base0 = self._steal_base()
        eng._sub(st, bat, self.ask(bat, "pinch_hit", bat, st.slot[bat] % 9), st.slot[bat] % 9)
        batter = st.lineup[bat][st.slot[bat] % 9]
        st.cur_slot = st.slot[bat] % 9 + 1
        st.slot[bat] += 1
        self.pa = {"batter": batter, "pitcher": st.pitcher[fld], "bunt": Decision.NO, "cum": None, "b": 0, "s": 0, "seq": [],
                   "res": None, "ibb": False, "charge_to": None, "hnr": False, "attempt": False, "stole": False, "known_last": False,
                   "path": False, "path_all": steal_base0 > 0, "adj": None}
        ibb = self.ask(fld, "intentional_walk")
        if eng.dec_ibb and ibb == Decision.YES:
            self.pa.update(res="BB", ibb=True)          # NCAA 8-2-b: awarded on the coach's notification, no pitches
            return "pa_end"
        self.pa["bunt"] = self.pa["bunt0"] = self.ask(bat, "bunt")
        clean = True                   # no base running other than steals before the pitches (path statistics)
        # base running events: one draw per opportunity, again after each event until none occurs
        # (scripts/build_engine_tables.py). PR B: steals are decided before each pitch instead (_pitch); the table
        # keeps the wild pitches, passed balls, pickoffs and balks at their league rates (a steal draw is "none").
        while any(b is not None for b in st.bases) and st.outs < 3 and not st.over:
            steal = Decision.NO if eng.dec_steal else self.ask(bat, "steal_attempt")
            runner = eng._lead_stealer(st, bat)
            ta = to_ = 0.0
            if eng.sb_tier:
                cell = f"{st.team_obj[bat].tier}|{st.team_obj[fld].tier}"
                ta, to_ = eng.sb_tier["attempt"]["cell"][cell], eng.sb_tier["success"]["cell"][cell]
            sb_or = np.exp(runner.run[0] + eng.delta["att"] + ta) if (runner is not None and not eng.dec_steal) else 1.0
            ev = eng.pre_pa.draw_event(st.outs, st.base_code, rng.random(), sb_or)
            if eng.dec_steal and ev == "SB_ATT":
                # the steal is decided before a pitch instead; in the data the opportunity that held it was followed by
                # another (a wild pitch, passed ball, pickoff or balk can come next), so it is taken out and the draw goes on
                continue
            if steal == Decision.NO and ev == "SB_ATT":
                ev = None
            if ev is None:
                break
            clean = False
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
            elif ev == "PO" and eng.dec_steal and "0" in dests and rng.random() < eng.po_cs_share:
                # scoring only: the runner was breaking for the next base, a caught stealing in the box score
                eng.sb[0] += 1
                st.sb_att[bat] += 1
            if self.log is not None:
                self.log.append(("run", self.pa_serial, ev, tuple(dests)))
            if eng._apply(st, dests, None, None, err, event=ev) and st.half == "B":
                eng._end_check(st, True)
        if st.outs >= 3 or st.over:
            st.slot[bat] -= 1                           # the third out on the bases: he leads off the next inning
            self.pa = None
            return "half_end"
        self.pa["path"] = steal_base0 > 0 and clean
        adj = st.cur_slot if dec_on else None
        self.pa["adj"] = adj
        self.pa["cum"] = eng._forward(batter, st.pitcher[fld], bat == "home", st.err_or[fld], adj)
        self.pa["law"] = eng.last_law
        return "pitch"

    # ---- PR B: before each pitch -----------------------------------------------------------------------
    def _steal_base(self) -> int:
        """The base the lead runner would steal: second (runner on first, second open), third (runner on second,
        third open), else 0 (engine.game2 _lead_stealer)."""
        b = self.st.bases
        if b[0] is not None and b[1] is None:
            return 2
        if b[1] is not None and b[2] is None:
            return 3
        return 0

    def _steal_info(self, steal_base: int) -> dict:
        """What the batting side sees before a pitch, and the league's steal model for it: the attempt logit (the
        fitted hazard for the count and game state, the runner's speed, the pitcher's hold, the tier cell) and the
        success logit (count, outs, base, speed, the catcher's arm, the pitcher's hold, the tier cell)."""
        eng, st, pa = self.eng, self.st, self.pa
        bat, fld = st.batting_side, st.fielding_side
        info = {"count": (pa["b"], pa["s"]), "steal_base": steal_base, "pitcher": st.pitcher[fld], "runner": None}
        if not steal_base or not eng.dec_steal:
            return info
        runner = eng._lead_stealer(st, bat)
        a, s_ = eng.dm.steal_logits(st, (pa["b"], pa["s"]), steal_base)
        ta = to_ = 0.0
        if eng.sb_tier:
            cell = f"{st.team_obj[bat].tier}|{st.team_obj[fld].tier}"
            ta, to_ = eng.sb_tier["attempt"]["cell"][cell], eng.sb_tier["success"]["cell"][cell]
        hold = st.pitcher[fld].hold
        if runner is not None:
            a += runner.run[0] + eng.delta["att_pitch"] + ta
            s_ += runner.run[1] + eng.delta["ok_pitch"] + to_
        a -= eng.sd_hold_att * hold
        s_ += -eng.sd_hold_suc * hold - st.catcher_arm[fld]
        info.update(runner=runner, attempt_logit=float(a), success_logit=float(s_))
        return info

    def _defense_call(self, act, info) -> str | None:
        """A fielding-side call before a pitch. Returns the forced pitch ('B') for a pitchout or an intentional ball,
        'ibb' for an intentional walk, else None."""
        eng, st, pa = self.eng, self.st, self.pa
        fld = st.fielding_side
        if act in (None, "none"):
            return None
        if act in ("pitchout", "intentional_ball"):
            pa["pitchout"] = act == "pitchout"
            return "B"
        if act == "ibb":
            return "ibb"
        if act == "mound_visit":
            from config.decisions import FREE_TRIPS, FREE_TRIPS_EXTRA
            m = st.mound
            pid = st.pitcher[fld].pid
            key = (fld, st.inning, pid)
            if m["batter"].get(fld) == (st.inning, self.pa_serial):
                raise ValueError("NCAA 9-4-c: no second trip to the mound in an inning with the same batter at bat")
            limit = FREE_TRIPS + (FREE_TRIPS_EXTRA if st.inning > eng.rules.innings else 0)
            m["batter"][fld] = (st.inning, self.pa_serial)
            if m["trips"].get(key) or m["free"][fld] >= limit:
                # 9-4-b: a second trip to the same pitcher in the inning, or one past the free trips: he is removed
                act = ("pitching_change", self.ask(fld, "relief_pitcher", fld))
                if act[1] is None:
                    return None                               # nobody left in the bullpen: he stays in
            else:
                m["trips"][key] = 1
                m["free"][fld] += 1
                if self.log is not None:
                    self.log.append(("visit", self.pa_serial, fld))
                return None                                   # no effect on any probability (GUESS: no data)
        if isinstance(act, tuple) and act[0] == "pitching_change" and act[1] is not None:
            prior = st.pitcher[fld]
            if (pa["b"], pa["s"]) in _WALK_TO_PRIOR and pa["charge_to"] is None:
                pa["charge_to"] = prior                       # NCAA 10-22-b: a walk to this batter is the prior pitcher's
            st.outing[fld]["pitches"] += len(pa["seq"]) - pa.get("pitches_charged", 0)
            eng.pstats[prior.pid][P_PITCH] += len(pa["seq"]) - pa.get("pitches_charged", 0)
            pa["pitches_charged"] = len(pa["seq"])
            eng._bring_in(st, fld, act[1], False)
            pa["pitcher"] = act[1]
            pa["cum"] = eng._forward(pa["batter"], act[1], st.batting_side == "home", st.err_or[fld], pa["adj"])
            pa["law"] = eng.last_law
            if self.log is not None:
                self.log.append(("pit", self.pa_serial, fld, act[1].pid))
            return None
        if isinstance(act, tuple) and act[0] == "defensive_sub":
            eng._sub(st, fld, act[2], act[1])
            return None
        raise ValueError(f"unknown defensive call {act!r}")

    def _pitch(self):
        """One pitch, with the calls before it. Returns False (the plate appearance goes on), True (it ended), or
        'abort' (the third out was made on the bases during it: the half ends, the batter leads off next time)."""
        eng, st, pa = self.eng, self.st, self.pa
        bat, fld = st.batting_side, st.fielding_side
        dec_on = eng.dec_on
        attempt = forced = None
        hnr = False
        if dec_on:
            steal_base = self._steal_base() if st.outs < 3 else 0
            info = None
            if steal_base or self.ctrl[bat].per_pitch:
                info = self._steal_info(steal_base)
                act = self.ask(bat, "pre_pitch", info)
                if isinstance(act, tuple) and act[0] == "pinch_runner":
                    eng._sub(st, bat, act[2], act[1])
                    act = None
                if act == "bunt":
                    pa["bunt"] = Decision.YES
                elif act == "swing":
                    pa["bunt"] = Decision.NO
                elif act in ("steal", "hit_and_run") and steal_base:
                    attempt, hnr = steal_base, act == "hit_and_run"
            if self.ctrl[fld].per_pitch:
                info = info or self._steal_info(steal_base)
                forced = self._defense_call(self.ask(fld, "pre_pitch_defense", info), info)
                if forced == "ibb":
                    pa.update(res="BB", ibb=True)
                    return True
                pa = self.pa
        b, s_ = pa["b"], pa["s"]
        i = b * 3 + s_
        u = st.rng.random()
        bunting = eng.dec_bunt and pa["bunt"] == Decision.YES and s_ < 2 and not attempt
        if forced == "B":
            sym, d = "B", (i + 3 if b < 3 else -1 - _O_BB)
        elif bunting and i in eng.dm.bunt_pitch:
            sym = eng.dm.bunt_pitch[i].draw(u)
            d = _forced_dest(sym, b, s_)
        else:
            row = pa["cum"][i]
            if hnr:
                # the batter swings (GUESS: the hit-and-run takes the balls and called strikes out of the pitch)
                k = _swing_draw(row, u)
            else:
                k = bisect_right(row, u * row[-1])
                if k >= N_SLOTS:
                    k = N_SLOTS - 1
            sym, d = SLOT_SYM[k], SLOT_DEST[i][k]
        pa["seq"].append(sym)
        if self.log is not None:
            self.log.append(("p", self.pa_serial, sym))
        ends = d < 0
        if attempt and sym in "BKS":
            res_out = self._resolve_steal(attempt, sym, ends)
            if res_out == "abort":
                pa["b"], pa["s"] = divmod(d, 3)          # the count it was cut off at (the Phase 4 test's correction)
                return "abort"
        if hnr and sym == "P":
            pa["hnr"] = True
        if not ends:
            pa["b"], pa["s"] = divmod(d, 3)
            return False
        pa["res"] = "BUNT" if (bunting and sym == "P") else OUTCOMES[-1 - d]
        return True

    def _resolve_steal(self, steal_base: int, sym: str, ends: bool):
        """A steal attempt on a ball or strike (on a foul the runner goes back; on a ball in play he was running)."""
        eng, st, pa = self.eng, self.st, self.pa
        bat = st.batting_side
        b, s_ = pa["b"], pa["s"]
        strike_three = ends and sym in "KS"
        ball_four = ends and sym == "B"
        if strike_three and st.outs == 2:
            return None                                       # the strikeout ends the inning first
        if ball_four and steal_base == 2:
            return None                                       # forced to second by the walk
        info = self._steal_info(steal_base)
        s_logit = info["success_logit"]
        if pa.get("pitchout"):
            from config.decisions import PITCHOUT_SUCCESS_LOGIT
            s_logit += PITCHOUT_SUCCESS_LOGIT
        ok = st.rng.random() < 1.0 / (1.0 + np.exp(-s_logit))
        u = st.rng.random()
        # every runner's destination and any error: the play-by-play's steal plays in this base-out state, split
        # into those with no runner out and those with one (scripts/build_engine_tables.py)
        cat = eng.pre_pa.outcome.get((f"{st.outs}|{st.base_code}", "SB_ATT")) or eng.pre_pa.outcome.get((f"*|{st.base_code}", "SB_ATT"))
        sp = _ok_split(cat) if cat is not None else None
        if sp is not None:
            r1, r2, r3, _o, err = (sp[1] if ok else sp[2]).draw(u).split(",")
            dests, err = [r1, r2, r3], int(err)
        else:
            dests, err = ["" if x is None else str(k + 1) for k, x in enumerate(st.bases)], 0
            dests[steal_base - 2] = str(steal_base) if ok else "0"
        ok = dests[steal_base - 2] not in ("0", "")
        # the box score counts every runner who tries (a double steal is two attempts)
        n_att = n_ok = 0
        for k in range(3):
            if st.bases[k] is not None and dests[k] != str(k + 1):
                n_att += 1
                n_ok += dests[k] != "0"
        eng.sb[0] += n_att
        eng.sb[1] += n_ok
        st.sb_att[bat] += n_att
        st.sb_ok[bat] += n_ok
        if not pa["attempt"]:
            pa["attempt"], pa["stole"], pa["known_last"] = True, ok, ends
        if self.log is not None:
            self.log.append(("steal", self.pa_serial, steal_base, bool(ok), (b, s_)))
        if eng._apply(st, dests, None, None, err, event="SB_ATT") and st.half == "B":
            eng._end_check(st, True)
        if st.outs >= 3 and not ends:
            return "abort"
        return None

    def _abort_pa(self) -> str:
        """The third out on the bases during a plate appearance: its pitches count for the pitcher, the batter leads
        off the next inning with a new count (no plate appearance is recorded)."""
        eng, st, pa = self.eng, self.st, self.pa
        bat, fld = st.batting_side, st.fielding_side
        n = len(pa["seq"]) - pa.get("pitches_charged", 0)
        st.outing[fld]["pitches"] += n
        eng.pstats[pa["pitcher"].pid][P_PITCH] += n
        law = pa.get("law")
        if eng.dec_on and law is not None and not pa["ibb"]:
            # The Phase 4 forward test counts completed plate appearances only. A plate appearance cut off here is
            # more often one headed for a strikeout (steals are tried more at two strikes), so the completed ones are
            # selected. The expectation over completed plate appearances is exact when each cut-off one adds its
            # ex-ante K, BB and HR minus their probabilities from the count it was cut off at (the forward chain's
            # outcome law at that count averages to the ex-ante law).
            qs, h = eng._matchup_chain(pa["batter"], pa["pitcher"], bat == "home")
            w = np.divide(law, h[0], out=np.zeros_like(law), where=h[0] > 0)
            c = pa["b"] * 3 + pa["s"]
            cond = w * h[c]
            cond = cond / cond.sum()
            adj = _rates_of(law)[:3] - _rates_of(cond)[:3]
            eng.exp_trials[pa["batter"].pid, :3, 0] += adj
            eng.exp_trials[pa["pitcher"].pid, :3, 0] += adj
        st.slot[bat] -= 1
        self.pa = None
        return "half_end"

    def _finish_pa(self) -> str:
        eng, st, pa = self.eng, self.st, self.pa
        rng = st.rng
        bat, fld = st.batting_side, st.fielding_side
        batter, pitcher, res = pa["batter"], pa["pitcher"], pa["res"]
        if res == "BB" and pa["charge_to"] is not None:
            pitcher = pa["charge_to"]                         # NCAA 10-22-b
        eo = st.err_or[fld]
        bases0 = list(st.bases)
        bunted = eng.dec_bunt and pa.get("bunt0") == Decision.YES      # called as the plate appearance began (ex ante)
        outs_b, base_b = st.outs, st.base_code
        if res == "BUNT":
            res, dests, b_to, err = eng.dm.bunt_outcome(st.outs, st.base_code, rng.random())
            eng.bunt_rec["bunts"] += 1
            eng.bunt_rec["SH"] += res == "SH"
            eng.bunt_rec["hits"] += res in ("1B", "2B")
        else:
            if res == "OUT":
                res = eng._subtype(st, rng, Decision.NO if eng.dec_bunt else pa["bunt"])
            dests, b_to, err = eng.advance.draw(res, st.outs, st.base_code, rng.random(), [rng.random() for _ in range(4)], eo)
            if res in ("1B", "2B") and eng.speed_on:
                dests = eng._extra_bases(st, bat, fld, res, dests, bases0, rng)
            if pa["hnr"] and bases0[0] is not None:
                dests = _hit_and_run(res, dests)
        if pa["ibb"]:
            eng.ibb_count += 1
            st.ibb[bat] += 1
        n_charged = pa.get("pitches_charged", 0)
        law = None
        if eng.dec_on:
            if pa["ibb"]:
                law = _E_BB
            elif bunted:
                law = eng.dm.bunt_law(outs_b, base_b)[0]
            else:
                law = pa.get("law")
        eng._record(st, batter, pitcher, res, None if (pa["ibb"] and not pa["seq"]) else "".join(pa["seq"]),
                    skip_pitches=n_charged, pitch_to=pa["pitcher"], law=law)
        if pa.get("path_all") and not pa["ibb"] and _n_eligible(pa["seq"], res):
            eng.path_all_rec.append((sum(c != "N" for c in pa["seq"]), _final_count(pa["seq"]), int(pa["attempt"]), int(pa["stole"])))
        if pa["path"] and not pa["ibb"] and _n_eligible(pa["seq"], res):
            # the play-by-play's sample (scripts/build_prb_steals.py eligible()): a plate appearance that began with
            # a lead runner able to steal, no other base running first, and at least one ball or strike
            eng.path_rec.append((sum(c != "N" for c in pa["seq"]), _final_count(pa["seq"]), int(pa["attempt"]), int(pa["stole"]), int(pa["known_last"])))
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
