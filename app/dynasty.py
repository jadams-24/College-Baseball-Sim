"""Dynasty mode (2026-10-08): one full season of the engine's Phase 7 world, driven game by game so the user's
games can go through the manager screen while every other game is simmed, and the result equals the engine's own
season run (engine.season.simulate_season) for the same seed and decisions.

What makes that possible without touching the engine:
  * simulate_season spawns one seed per scheduled game from the season seed, independent of play order, and plays
    the schedule in date order; the dynasty plays the same list in the same order with the same seeds, each game
    through PlayerGameEngine.play (AI both sides) or, for the user's games, through app.connector.GameRunner on
    the same engine, Decider and seed (the connector's game equals the engine's: tests/test_app_connector.py);
  * the postseason (engine.world.World: conference tournaments, selection, bracket, NCAA tournament) calls a
    synchronous play_game; the dynasty runs that pipeline with a play_game that returns recorded results for the
    games already played, plays new games with the engine, and raises when it reaches a game of the user's team
    that the user wants to play. After that game ends, the pipeline is re-run from the start (same World seed,
    same call order, so the same committee draws) and continues from the recorded results: snapshot and replay at
    the tournament level, the same idea as the connector's.

Not exposed by the engine (listed, not reimplemented): per-batter runs and RBI outside a logged game (the simmed
games' box scores have no R/RBI columns; the user's games, narrated from the log, do), stolen bases per player,
pitcher wins/losses/saves, a player's class or year, handedness (Phase 3), an availability verdict for a pitcher
(the AI's rest rule is internal: the roster shows the last outing's date and pitches), fielder positioning.
"""
from __future__ import annotations

import pickle
import time
import zlib
from collections import Counter

import numpy as np

from app.connector import GameRunner, MANAGER_STATIC, _Pickler, _Unpickler
from app.timeline import box_score as runner_box, pitching_line, batting_line
from app.world import player_json, staff
from config import phase7
from engine.game2 import B_NCOL, P_NCOL, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.rpi import rpi as rpi_of
from engine.schedule import make_schedule
from engine.world import World as SeasonWorld, cancel_mask, schedule_mask

SAVE_VERSION = 1
STAGES = ("regular", "conf", "selection", "ncaa", "done")
from app import calendar, world_steps
from app.world_steps import PauseEvent, StepContext

SIM_TARGETS = ("game", "day", "week", "regular", "conf", "selection", "end")
STOPS = ("week_end", "postseason", "selection")      # the auto-pause moments (Settings): stop there on a longer sim
POST_OFF = phase7.POST_OFFSETS


def _copy_seq(seq: np.random.SeedSequence) -> np.random.SeedSequence:
    """A fresh copy of a SeedSequence: its spawn counter restarts, so the k-th spawn is the same every run."""
    return np.random.SeedSequence(seq.entropy, spawn_key=seq.spawn_key, pool_size=seq.pool_size)


def _child(seq: np.random.SeedSequence, k: int) -> np.random.SeedSequence:
    """The (k+1)-th child seq.spawn would give: spawn_key extended by k."""
    return np.random.SeedSequence(seq.entropy, spawn_key=tuple(seq.spawn_key) + (k,), pool_size=seq.pool_size)


class UserGame(Exception):
    """The postseason pipeline reached a game of the user's team: (call index, home, away, date, neutral, stage)."""

    def __init__(self, k, h, a, date, neutral, stage):
        super().__init__("user game")
        self.k, self.h, self.a, self.date, self.neutral, self.stage = k, h, a, date, neutral, stage


class StopAt(Exception):
    """The pipeline reached the stage the sim target stops before."""


class _Adapter:
    """What GameRunner needs from a world: the engine, the config, team lookup, the players of a game."""

    def __init__(self, dyn: "Dynasty"):
        self.dyn = dyn

    @property
    def eng(self):
        return self.dyn.eng

    @property
    def cfg(self):
        return self.dyn.cfg

    @property
    def seed(self):
        return self.dyn.seed

    @property
    def league(self):
        return self.dyn.league

    def team(self, tid: int):
        return self.dyn.league.teams[tid]

    def game_pids(self, home, away) -> list:
        return [p.pid for t in (home, away) for p in t.batters + staff(t)]

    def season_stats(self, p, rows) -> dict | None:
        """The player's season line before the game in progress (the accumulator rows at the game's creation)."""
        if rows is None:
            return None
        b, pr = rows
        return _bat_stats(b) if p.side == "bat" else _pit_stats(pr)


def _game_record(g, st, i, box, user_played: bool) -> dict:
    line = {"away": [], "home": []}
    for inn, half, runs, _ in st.half_innings:
        line["away" if half == "T" else "home"].append(int(runs))
    return {"i": i, "date": int(g.date), "week": int(g.week), "day": int(g.day), "weekend": bool(g.weekend),
            "home": int(g.home), "away": int(g.away), "hr": int(st.score["home"]), "ar": int(st.score["away"]),
            "inning": int(st.inning), "run_rule": bool(st.ended_by_run_rule), "line": line,
            "hits": {s: int(st.hits[s]) for s in ("away", "home")}, "errors": {s: int(st.errors[s]) for s in ("away", "home")},
            "box": box, "user": user_played, "stage": "regular", "neutral": False}


class Dynasty:
    """One dynasty: the D1 world of a seed, the user's team, the season in progress, its results and the saves."""

    def __init__(self, cfg, seed: int, name: str = ""):
        self.cfg, self.seed, self.name = cfg, int(seed), name
        ss = np.random.SeedSequence(self.seed)
        s_league, s_sched, s_games = ss.spawn(3)
        self.league = build_league(cfg, np.random.Generator(np.random.PCG64(s_league)))
        self._s_sched, self._s_games = s_sched, s_games
        self._s_cancel, self._s_post, self._s_len = ss.spawn(3)
        self.real_conf = {tid: c for tid, (_, c, _) in enumerate(cfg.teams)}
        self.tid: int | None = None
        self.year = 1
        self.created = time.time()
        self.schedule = []
        self.skip = np.zeros(0, bool)
        self.seeds: list = []
        self.pos = 0
        self.results: dict = {}          # schedule index -> game record
        self.reg_games: list = []        # (date, home, away, hr, ar, False, "regular") in play order (engine.world.World)
        self.post_calls: list = []       # recorded postseason play_game results, in call order
        self.post: dict = {}             # the postseason's computed pieces as they become known
        self.stage = "regular"
        self.today = 0                   # the world's date (days since the opening week's Monday): the day loop's position
        self.steps_done: list = []       # world steps finished today (a paused step is not; it resumes on the next call)
        self.last_pause: dict | None = None   # the auto-pause event the last advance stopped on
        self.pending: dict | None = None # the user's game waiting to be played or simmed
        self.runner: GameRunner | None = None
        self.news: list = []
        self.eng = self.mgr = None
        self.bstats = self.pstats = None
        self.adapter = _Adapter(self)

    # ---- construction ------------------------------------------------------------------------
    def start(self, tid: int) -> None:
        """The user's team is picked: build the season (schedule, the games each team drops, cancellations)."""
        if self.tid is not None:
            raise ValueError("the dynasty has started")
        self.tid = int(tid)
        cfg, league = self.cfg, self.league
        self.schedule = make_schedule(cfg, league, np.random.Generator(np.random.PCG64(self._s_sched)))
        dropped = schedule_mask(self.schedule, len(league.teams), np.random.Generator(np.random.PCG64(self._s_len)))
        canceled = cancel_mask(self.schedule, np.random.Generator(np.random.PCG64(self._s_cancel))) & ~dropped
        self.skip = canceled | dropped
        self.seeds = self._s_games.spawn(len(self.schedule))
        self.today = int(self.schedule[0].date) if self.schedule else 0
        self._build_engine()

    def _build_engine(self) -> None:
        n = len(self.league.players)
        if self.bstats is None:
            self.bstats = [[0] * B_NCOL for _ in range(n)]
            self.pstats = [[0] * P_NCOL for _ in range(n)]
        self.eng = PlayerGameEngine(self.cfg, self.league, self.bstats, self.pstats)
        # The engine's per-player-per-opponent trial counts (the Phase 4 report's opponent adjustment) are a
        # preallocated 80 MB array that a season pages in entirely; play only increments it, nothing reads it. A
        # dynasty does not report, so it hands the engine a zero-strided view over one cell: every increment lands
        # there and the memory stays out (the 512 MB host). Not an engine change: the engine's own attribute, replaced.
        ot = self.eng.opp_trials
        self.eng.opp_trials = np.lib.stride_tricks.as_strided(np.zeros(1, dtype=ot.dtype), shape=ot.shape, strides=(0, 0, 0, 0), writeable=True)
        if self.mgr is None:
            self.mgr = Manager(self.cfg)

    # ---- the regular season ------------------------------------------------------------------
    @property
    def team(self):
        return self.league.teams[self.tid]

    def mine(self, g) -> bool:
        return self.tid in (g.home, g.away)

    def last_date(self) -> int:
        return max(g.date for g in self.schedule)

    def _rows(self, home, away) -> dict:
        return {p.pid: (list(self.bstats[p.pid]), list(self.pstats[p.pid])) for t in (home, away) for p in t.batters + staff(t)}

    def _box_from_rows(self, before: dict, home, away) -> dict:
        """The game's lines as row differences (the engine's accumulators), int16 arrays: compact for 8,000 games."""
        out = {}
        for side, t in (("home", home), ("away", away)):
            bat, pit = [], []
            for p in t.batters + staff(t):
                b0, p0 = before[p.pid]
                db = [x - y for x, y in zip(self.bstats[p.pid], b0)]
                dp = [x - y for x, y in zip(self.pstats[p.pid], p0)]
                if any(db):
                    bat.append([p.pid] + db)
                if any(dp):
                    pit.append([p.pid] + dp)
            out[side] = {"bat": np.array(bat, dtype=np.int32).reshape(-1, 1 + B_NCOL), "pit": np.array(pit, dtype=np.int32).reshape(-1, 1 + P_NCOL)}
        return out

    def _play(self, i: int, runner: GameRunner | None = None) -> dict:
        """Play scheduled game i: with the engine (AI both sides) or from the user's finished runner."""
        g = self.schedule[i]
        home, away = self.league.teams[g.home], self.league.teams[g.away]
        if runner is None:
            before = self._rows(home, away)
            rng = np.random.Generator(np.random.PCG64(self.seeds[i]))
            st = self.eng.play(rng, home, away, g.weekend, self.mgr, week=g.week, day=g.day, date=g.date)
            box = self._box_from_rows(before, home, away)
            rec = _game_record(g, st, i, box, False)
        else:
            if not runner.over:
                raise ValueError("the game is not over")
            st = runner.base.st
            box = self._box_from_rows(runner.base_rows, home, away)
            rec = _game_record(g, st, i, box, True)
            rec["full_box"] = runner_box(runner)        # narrated: R, RBI and the play-by-play
        self.results[i] = rec
        self.reg_games.append((g.date, g.home, g.away, rec["hr"], rec["ar"], False, "regular"))
        if self.mine(g):
            self._news_for(rec)
        return rec

    def next_index(self) -> int | None:
        """The next scheduled game not yet played (skipping dropped and canceled ones, and games the background
        sim played ahead of the user's), or None."""
        i = self.pos
        while i < len(self.schedule) and (self.skip[i] or i in self.results):
            i += 1
        return i if i < len(self.schedule) else None

    def background_plan(self) -> list:
        """The games to sim while the user plays the pending one: the rest of that week's games that follow it in
        schedule order and do not depend on it. A game depends on the pending game when one of its teams plays in
        the pending game, or in any earlier game that is itself deferred (the chain: the opponent's next game, the
        opponent of that game's next game, and so on). Everything else involves teams whose state the pending game
        cannot touch (per-game seeds; the engine's accumulators and the Decider's rest history, rotation plans and
        counters are per player or per team), so playing it ahead gives the engine's results
        (tests/test_app_dynasty.py plays the user's games with the background sim running). Postseason games are
        never simmed ahead: a bracket's later games depend on its earlier ones."""
        if self.pending is None or self.pending["stage"] != "regular" or self.stage != "regular":
            return []
        i0 = self.pending["i"]
        g0 = self.schedule[i0]
        week = self._week_of(g0.date)
        waiting = {g0.home, g0.away}            # teams with a deferred game behind them
        out = []
        for i in range(i0 + 1, len(self.schedule)):
            g = self.schedule[i]
            if self._week_of(g.date) != week:
                break
            if self.skip[i] or i in self.results:
                continue
            if g.home in waiting or g.away in waiting:
                waiting.update((g.home, g.away))
                continue
            out.append(i)
        return out

    def my_games(self) -> list:
        return [i for i, g in enumerate(self.schedule) if self.mine(g) and not self.skip[i]]

    def _week_of(self, date: int) -> int:
        return int(date) // 7

    LONG_TARGETS = ("regular", "conf", "selection", "end")

    def advance(self, target: str, pause_mine: bool = True, progress=None, stops=()) -> dict:
        """Sim toward `target` (SIM_TARGETS): the next game of the user's team, the end of this day, the end of this
        week, the end of the regular season, the conference tournaments, Selection Monday, the end of the season.
        The regular season runs as a loop over calendar days, each day running the registered world steps in order
        (`app/world_steps.py`; today the D1 games). The user's games pause the loop (pause_mine) so the user plays or
        sims them; otherwise the AI plays them. `stops` (STOPS) are the auto-pause moments a longer sim stops at: the
        end of each week, the start of the postseason, Selection Monday; a stop already reached when the call starts
        does not stop it again. The pause the call stopped on is in the hub (`pause`). Returns the hub state."""
        if target not in SIM_TARGETS:
            raise ValueError(f"target is one of {SIM_TARGETS}")
        if self.pending is not None and self.runner is not None:
            raise ValueError("finish or sim the pending game first")
        if self.pending is not None and pause_mine:
            return self.hub()
        self.pending = None
        self.last_pause = None
        long = target in self.LONG_TARGETS
        enabled = (set(stops) & set(STOPS)) if long else set()
        if pause_mine:
            enabled.add("my_game")
        elif target == "game":
            enabled.add("my_game_done")
        if target == "week":
            enabled.add("week_end")
        start_stage = self.stage
        while self.stage == "regular":
            ctx = StepContext(self.today, enabled, target, progress)
            hit = self._run_day(ctx)
            if hit is not None:
                self.last_pause = hit.as_dict()
                break
            if self.stage != "regular":
                break
            week_end = self.today % 7 == 6
            self.today += 1
            self.steps_done = []
            if progress:
                progress(self)
            if target == "day" and ctx.worked:
                break
            if week_end and "week_end" in enabled:
                self.last_pause = PauseEvent("week_end", "The week is over.", "schedule").as_dict()
                break
        if self.last_pause is not None:
            return self.hub()
        if self.stage not in ("regular", "done") and target != "regular":
            post_target = "game" if target in ("day", "week") else target
            if post_target == "end" and "selection" in stops and start_stage in ("regular", "conf"):
                post_target = "selection"           # auto-pause: Selection Monday
            self._run_post(post_target, pause_mine, progress)
            if self.stage == "selection" and post_target == "selection" and target == "end":
                self.last_pause = PauseEvent("selection", "Selection Monday: the field of 64 is set.", "postseason").as_dict()
        return self.hub()

    def _run_day(self, ctx: StepContext):
        """Run today's world steps in order; returns the pause event that stopped the day, or None when it is over."""
        for step in world_steps.steps():
            if step.name in self.steps_done or not step.due(ctx.today, self.year):
                continue
            events = step.run(self, ctx)
            hit = next((e for e in events if e.type in ctx.enabled), None)
            if hit is not None:
                return hit
            self.steps_done.append(step.name)
        return None

    # ---- the user's game -------------------------------------------------------------------------
    def open_game(self, modes: dict | None = None) -> GameRunner:
        """The pending game as a GameRunner on this dynasty's engine, Decider and seed (the manager screen)."""
        if self.pending is None:
            raise ValueError("no game is pending")
        if self.runner is not None:
            return self.runner
        p = self.pending
        user_side = "home" if p["home"] == self.tid else "away"
        if p["stage"] == "regular":
            g = self.schedule[p["i"]]
            seed = self.seeds[p["i"]]
            ex = {"weekend": bool(g.weekend), "week": int(g.week), "day": int(g.day), "date": int(g.date)}
            r = GameRunner.new(self.adapter, p["home"], p["away"], user_side, seed, exhibition=ex, mgr=self.mgr)
        else:
            ex = {"weekend": True, "week": int(p["date"]) // 7, "day": 0, "date": int(p["date"])}
            r = GameRunner.new(self.adapter, p["home"], p["away"], user_side, p["seed"], exhibition=ex, mgr=self.mgr,
                               neutral=bool(p["neutral"]), tournament=True)
        if modes:
            for k, m in modes.items():
                r.set_mode(k, m)
        self.runner = r
        return r

    def probables(self) -> dict | None:
        """The pending game's probable starters: both AIs' picks at first pitch, from the bench coach's dry run on a
        throwaway runner (a copy of the session; the live season's engine rows and Decider state are untouched)."""
        if self.pending is None:
            return None
        r = self.runner if self.runner is not None else self._throwaway_runner()
        if r.base.phase != "pregame":
            st = r.current.st
            return {s: player_json(st.pitcher[s]) for s in ("home", "away") if st.pitcher.get(s) is not None}
        adv = r.recommend()
        user = r.user
        opp = "home" if user == "away" else "away"
        out = {}
        for a in adv:
            if a["kind"] == "starting_pitcher":
                out[user] = player_json(self._player(a["pid"]))
            if a["kind"] == "opponent_starter":
                out[opp] = player_json(self._player(a["pid"]))
        return out

    def _player(self, pid: int):
        return self.league.players[pid]

    def _throwaway_runner(self) -> GameRunner:
        """A runner for the pending game that is not kept (probables); the Decider is a copy so its season state
        (series plans, midweek counts) is not moved by the dry run."""
        import copy
        p = self.pending
        user_side = "home" if p["home"] == self.tid else "away"
        mgr = copy.copy(self.mgr)
        for k, v in list(vars(mgr).items()):
            if k not in MANAGER_STATIC:
                setattr(mgr, k, copy.deepcopy(v))
        if p["stage"] == "regular":
            g = self.schedule[p["i"]]
            ex = {"weekend": bool(g.weekend), "week": int(g.week), "day": int(g.day), "date": int(g.date)}
            return GameRunner.new(self.adapter, p["home"], p["away"], user_side, self.seeds[p["i"]], exhibition=ex, mgr=mgr)
        ex = {"weekend": True, "week": int(p["date"]) // 7, "day": 0, "date": int(p["date"])}
        return GameRunner.new(self.adapter, p["home"], p["away"], user_side, p["seed"], exhibition=ex, mgr=mgr, neutral=bool(p["neutral"]), tournament=True)

    def finish_game(self) -> dict:
        """The pending game is over (played on the manager screen): record it and move on."""
        if self.runner is None or not self.runner.over:
            raise ValueError("the game is not over")
        rec = self._record_pending(self.runner)
        self.runner = None
        return rec

    def sim_game(self) -> dict:
        """The AI plays the pending game (the same result the engine's season would give)."""
        if self.pending is None:
            raise ValueError("no game is pending")
        if self.runner is not None:
            if self.runner.over:
                return self.finish_game()
            self.runner.step("game")
            return self.finish_game()
        return self._record_pending(None)

    def _record_pending(self, runner) -> dict:
        p = self.pending
        if p["stage"] == "regular":
            rec = self._play(p["i"], runner)
            self.pos = p["i"] + 1
            self.pending = None
            return rec
        # a postseason game: play it now (or take the runner's result) and record it in call order
        home, away = self.league.teams[p["home"]], self.league.teams[p["away"]]
        before = self._rows(home, away)
        if runner is None:
            rng = np.random.Generator(np.random.PCG64(p["seed"]))
            st = self.eng.play(rng, home, away, True, self.mgr, week=p["date"] // 7, day=0, date=p["date"], neutral=p["neutral"], tournament=True)
            box = self._box_from_rows(before, home, away)
            user = False
        else:
            st = runner.base.st
            box = self._box_from_rows(runner.base_rows, home, away)
            user = True
        rec = self._post_record(p, st, box, user)
        if user:
            rec["full_box"] = runner_box(runner)
        assert p["k"] == len(self.post_calls)
        self.post_calls.append(rec)
        self.pending = None
        self._news_for(rec)
        return rec

    def _post_record(self, p: dict, st, box, user: bool) -> dict:
        class _G:
            pass
        g = _G()
        g.date, g.week, g.day, g.weekend, g.home, g.away = p["date"], p["date"] // 7, 0, True, p["home"], p["away"]
        rec = _game_record(g, st, -1, box, user)
        rec["stage"], rec["neutral"], rec["k"] = p["stage"], bool(p["neutral"]), p["k"]
        return rec

    # ---- the postseason: run the pipeline from the start over the recorded results ----------------
    def _run_post(self, target: str, pause_mine: bool, progress=None) -> None:
        """Conference tournaments, selection, bracket and the NCAA tournament (engine.world.World), the user's
        games pausing the run when pause_mine. Re-run from the start each time: the recorded results answer the
        games already played, so the World's own draws repeat exactly."""
        cfg, league = self.cfg, self.league
        s_world, s_play = (_child(self._s_post, 0), _child(self._s_post, 1))      # what s_post.spawn(2) gives the season run
        w = SeasonWorld(cfg, league, np.random.Generator(np.random.PCG64(s_world)))
        k = [0]
        stop_before = {"conf": "conf", "selection": "regional", "end": None, "game": None}[target]
        dyn = self

        def play_game(h, a, date, neutral, stage):
            idx = k[0]
            k[0] += 1
            if idx < len(dyn.post_calls):
                rec = dyn.post_calls[idx]
                return rec["hr"], rec["ar"]
            if stop_before == stage:
                raise StopAt()
            if stage == "regional":
                dyn.stage = "ncaa"
            if dyn.tid in (h, a) and pause_mine:
                raise UserGame(idx, h, a, date, neutral, stage)
            seed = _child(s_play, idx)                                 # the (idx+1)-th s_play.spawn(1)[0] of the season run
            home, away = league.teams[h], league.teams[a]
            before = dyn._rows(home, away)
            rng = np.random.Generator(np.random.PCG64(seed))
            st = dyn.eng.play(rng, home, away, True, dyn.mgr, week=date // 7, day=0, date=date, neutral=neutral, tournament=True)
            p = {"home": h, "away": a, "date": date, "neutral": neutral, "stage": stage, "k": idx}
            rec = dyn._post_record(p, st, dyn._box_from_rows(before, home, away), False)
            dyn.post_calls.append(rec)
            if progress:
                progress(dyn)
            return rec["hr"], rec["ar"]

        last = self.last_date()
        try:
            conf = w.conference_tournaments(self.reg_games, last + POST_OFF["conf"], play_game)
            self.post["conference"] = conf
            if self.stage == "conf":
                self.stage = "selection"
            autos = {c: v["champion"] for c, v in conf.items()}
            all_games = self.reg_games + [(r["date"], r["home"], r["away"], r["hr"], r["ar"], r["neutral"], "conf") for r in self.post_calls if r["stage"] == "conf"]
            f = w.field(all_games, autos)
            regs = w.bracket(f)
            self.post["field"] = {"auto": f["auto"], "at_large": f["at_large"], "field": f["field"], "seed_order": f["seed_order"],
                                  "national_seeds": f["national_seeds"], "rank": f["rank"], "rpi": {t: f["rpi"][t]["rpi"] for t in f["rpi"]}}
            self.post["regionals"] = regs
            dates = {kk: last + v for kk, v in POST_OFF.items()}
            ncaa = w.ncaa(f, regs, dates, play_game)
            self.post["ncaa"] = ncaa
            self.stage = "done"
            self.news.append({"date": last + POST_OFF["cws"] + 10, "text": f"{league.teams[ncaa['champion']].name} win the national championship over {league.teams[ncaa['runner_up']].name}."})
        except StopAt:
            pass
        except UserGame as ug:
            self.pending = {"home": ug.h, "away": ug.a, "date": int(ug.date), "weekend": True, "stage": ug.stage, "neutral": bool(ug.neutral),
                            "k": ug.k, "seed": _child(s_play, ug.k)}

    # ---- standings, RPI, news ------------------------------------------------------------------------
    def all_games(self) -> list:
        return self.reg_games + [(r["date"], r["home"], r["away"], r["hr"], r["ar"], r["neutral"], r["stage"]) for r in self.post_calls]

    def records(self, conf_only: bool = False) -> dict:
        return SeasonWorld.records(self.reg_games, self.real_conf if conf_only else None)

    def rpi(self) -> dict:
        games = [(h, a, hr > ar, n) for _, h, a, hr, ar, n, *_ in self.all_games()]
        return rpi_of(games) if games else {}

    def rpi_rank(self) -> dict:
        r = self.rpi()
        order = sorted(r, key=lambda t: -r[t]["rpi"])
        return {t: i + 1 for i, t in enumerate(order)}

    def _news_for(self, rec: dict) -> None:
        me = self.tid
        side = "home" if rec["home"] == me else "away"
        opp = rec["away"] if side == "home" else rec["home"]
        mine, theirs = (rec["hr"], rec["ar"]) if side == "home" else (rec["ar"], rec["hr"])
        won = mine > theirs
        opp_name = self.league.teams[opp].name
        if rec["stage"] != "regular":
            stage = {"conf": "conference tournament", "regional": "regional", "super": "super regional", "cws": "College World Series"}.get(rec["stage"], rec["stage"])
            self.news.append({"date": rec["date"], "text": f"{'Won' if won else 'Lost'} {mine}-{theirs} {'against' if won else 'to'} {opp_name} in the {stage}."})
        elif won and mine - theirs >= 8:
            self.news.append({"date": rec["date"], "text": f"Rout: {mine}-{theirs} over {opp_name}{' by run rule' if rec['run_rule'] else ''}."})
        elif rec["inning"] > 9:
            self.news.append({"date": rec["date"], "text": f"{'Won' if won else 'Lost'} {mine}-{theirs} {'against' if won else 'to'} {opp_name} in {rec['inning']} innings."})
        rec_all = self.records().get(me, [0, 0])
        w, l = rec_all
        if (w + l) % 10 == 0 and w + l:
            rk = self.rpi_rank().get(me)
            self.news.append({"date": rec["date"], "text": f"{w}-{l} after {w + l} games; RPI rank {rk}."})

    # ---- what the screens read ---------------------------------------------------------------------------
    def date_now(self) -> int:
        if self.pending is not None:
            return int(self.pending["date"])
        if self.stage == "regular":
            return int(self.today)
        if self.post_calls:
            return int(self.post_calls[-1]["date"])
        return self.last_date()

    def hub(self) -> dict:
        me = self.tid
        rec = self.records().get(me, [0, 0])
        crec = self.records(True).get(me, [0, 0])
        rank = self.rpi_rank().get(me)
        pend = None
        if self.pending is not None:
            p = self.pending
            pend = dict(p, home_name=self.league.teams[p["home"]].name, away_name=self.league.teams[p["away"]].name,
                        user_side="home" if p["home"] == me else "away", seed=None, open=self.runner is not None)
            try:
                pend["probables"] = self.probables()
            except Exception:                 # display only: never blocks the hub
                pend["probables"] = None
        return {"id": None, "name": self.name, "seed": self.seed, "year": self.year, "tid": me, "team": self.league.teams[me].name,
                "conference": self.real_conf[me], "tier": self.league.teams[me].tier, "record": rec, "conf_record": crec, "rpi_rank": rank,
                "date": self.date_now(), "week": self._week_of(self.date_now()) + 1, "stage": self.stage, "pending": pend,
                "games_played": len(self.reg_games), "games_total": int((~self.skip).sum()), "news": self.news[-12:][::-1],
                "pause": self.last_pause, "world_steps": world_steps.steps_json(self.year),
                "calendar": calendar.calendar_json(self.schedule, self.year)}


# ---- saves ---------------------------------------------------------------------------------------------
def save_bytes(d: Dynasty) -> bytes:
    """The whole dynasty: league, season, results, the manager's rest history, the pending game. zlib-compressed."""
    import io
    ext = {id(getattr(d.mgr, k)): f"mgr:{k}" for k in MANAGER_STATIC if hasattr(d.mgr, k) and getattr(d.mgr, k) is not None}
    ext[id(d.cfg)] = "cfg"
    buf = io.BytesIO()
    state = {"version": SAVE_VERSION, "seed": d.seed, "name": d.name, "tid": d.tid, "year": d.year, "created": d.created,
             "league": d.league, "schedule": d.schedule, "skip": d.skip, "seeds": d.seeds, "pos": d.pos, "results": d.results,
             "reg_games": d.reg_games, "post_calls": d.post_calls, "post": d.post, "stage": d.stage, "pending": d.pending,
             "news": d.news, "bstats": d.bstats, "pstats": d.pstats,
             "today": d.today, "steps_done": d.steps_done, "last_pause": d.last_pause,
             # the Decider's season state (rest history, series plans, midweek counts, rankings, last lineups, its generator):
             # everything but the fitted tables, which the live Manager of the loading process supplies
             "mgr_state": {k: v for k, v in vars(d.mgr).items() if k not in MANAGER_STATIC} if d.mgr else {},
             "s": (d._s_sched, d._s_games, d._s_cancel, d._s_post, d._s_len),
             "runner": d.runner.save_bytes() if d.runner is not None else None}
    _Pickler(buf, ext).dump(state)
    return zlib.compress(buf.getvalue(), 6)


def load_bytes(cfg, data: bytes) -> Dynasty:
    import io
    mgr = Manager(cfg)
    objs = {f"mgr:{k}": getattr(mgr, k) for k in MANAGER_STATIC if hasattr(mgr, k)}
    objs["cfg"] = cfg
    st = _Unpickler(io.BytesIO(zlib.decompress(data)), objs).load()
    if st.get("version") != SAVE_VERSION:
        raise ValueError("unknown dynasty save version")
    d = Dynasty.__new__(Dynasty)
    d.cfg, d.seed, d.name, d.tid, d.year, d.created = cfg, st["seed"], st["name"], st["tid"], st["year"], st["created"]
    d.league = st["league"]
    d._s_sched, d._s_games, d._s_cancel, d._s_post, d._s_len = st["s"]
    d.real_conf = {tid: c for tid, (_, c, _) in enumerate(cfg.teams)}
    d.schedule, d.skip, d.seeds, d.pos = st["schedule"], st["skip"], st["seeds"], st["pos"]
    d.results, d.reg_games, d.post_calls, d.post, d.stage, d.pending, d.news = (st["results"], st["reg_games"], st["post_calls"], st["post"],
                                                                                 st["stage"], st["pending"], st["news"])
    d.bstats, d.pstats = st["bstats"], st["pstats"]
    d.steps_done, d.last_pause = st.get("steps_done", []), st.get("last_pause")
    d.today = st.get("today")
    if d.today is None:                 # a save from before the day loop: the next game's date
        i = next((j for j in range(d.pos, len(d.schedule)) if not d.skip[j] and j not in d.results), None)
        d.today = int(d.schedule[i].date) if i is not None else (int(max(g.date for g in d.schedule)) if d.schedule else 0)
    d.mgr = mgr
    for k, v in st["mgr_state"].items():
        setattr(mgr, k, v)
    d.eng = None
    d.adapter = _Adapter(d)
    d.runner = None
    if d.tid is not None:
        d._build_engine()
    if st.get("runner") is not None:
        d.runner = GameRunner.load_bytes(d.adapter, st["runner"], mgr=mgr)
    return d


# ---- what the screens read (JSON) --------------------------------------------------------------------
def _ip(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def game_json(d: Dynasty, rec: dict, full: bool = False) -> dict:
    """A game for the schedule and results lists; with `full`, its box score (the engine's accumulator lines for
    a simmed game; the narrated box with R, RBI and the play-by-play for a game the user played)."""
    me = d.tid
    side = "home" if rec["home"] == me else "away" if rec["away"] == me else None
    out = {"i": rec["i"], "k": rec.get("k"), "stage": rec["stage"], "date": rec["date"], "week": rec["week"] + 1, "weekend": rec["weekend"],
           "neutral": rec["neutral"], "home": rec["home"], "away": rec["away"], "home_name": d.league.teams[rec["home"]].name,
           "away_name": d.league.teams[rec["away"]].name, "hr": rec["hr"], "ar": rec["ar"], "inning": rec["inning"], "run_rule": rec["run_rule"],
           "conf": d.real_conf[rec["home"]] == d.real_conf[rec["away"]], "user": rec["user"], "side": side}
    if side:
        mine, theirs = (rec["hr"], rec["ar"]) if side == "home" else (rec["ar"], rec["hr"])
        out["result"] = f"{'W' if mine > theirs else 'L'} {mine}-{theirs}"
    if full:
        out["line"] = rec["line"]; out["hits"] = rec["hits"]; out["errors"] = rec["errors"]
        if "full_box" in rec:
            out["box"] = rec["full_box"]
        else:
            box = {}
            for s in ("away", "home"):
                t = d.league.teams[rec[s]]
                byp = {p.pid: p for p in t.batters + staff(t)}
                bat = [dict(player_json(byp[int(r[0])]), line=batting_line([int(x) for x in r[1:]])) for r in rec["box"][s]["bat"]]
                pit = [dict(player_json(byp[int(r[0])]), line=pitching_line([int(x) for x in r[1:]])) for r in rec["box"][s]["pit"]]
                order = {p.pid: i for i, p in enumerate(t.batters)}
                bat.sort(key=lambda x: order.get(x["pid"], 99))
                box[s] = {"batting": bat, "pitching": pit}
            out["box"] = {"teams": {s: d.league.teams[rec[s]].name for s in ("away", "home")}, "score": {"home": rec["hr"], "away": rec["ar"]},
                          "batting": {s: box[s]["batting"] for s in box}, "pitching": {s: box[s]["pitching"] for s in box}, "no_rbi": True}
    return out


def schedule_json(d: Dynasty) -> list:
    """The user's team's season: every scheduled game with its result when played; dropped and canceled games
    marked; postseason games appended as they are played."""
    out = []
    for i, g in enumerate(d.schedule):
        if not d.mine(g):
            continue
        row = {"i": i, "date": int(g.date), "week": int(g.week) + 1, "weekend": bool(g.weekend), "home": int(g.home), "away": int(g.away),
               "home_name": d.league.teams[g.home].name, "away_name": d.league.teams[g.away].name,
               "conf": d.real_conf[g.home] == d.real_conf[g.away], "side": "home" if g.home == d.tid else "away",
               "status": "canceled" if d.skip[i] else ("played" if i in d.results else ("next" if d.pending and d.pending.get("i") == i else "upcoming"))}
        if i in d.results:
            row.update({k: v for k, v in game_json(d, d.results[i]).items() if k in ("hr", "ar", "inning", "run_rule", "result", "user")})
        out.append(row)
    for rec in d.post_calls:
        if d.tid in (rec["home"], rec["away"]):
            out.append(dict(game_json(d, rec), status="played"))
    if d.pending and d.pending["stage"] != "regular":
        p = d.pending
        out.append({"k": p["k"], "stage": p["stage"], "date": p["date"], "week": p["date"] // 7 + 1, "weekend": True, "neutral": p["neutral"],
                    "home": p["home"], "away": p["away"], "home_name": d.league.teams[p["home"]].name, "away_name": d.league.teams[p["away"]].name,
                    "conf": False, "side": "home" if p["home"] == d.tid else "away", "status": "next"})
    return out


def find_game(d: Dynasty, i: int | None, k: int | None) -> dict | None:
    if i is not None and i >= 0:
        return d.results.get(i)
    if k is not None and 0 <= k < len(d.post_calls):
        return d.post_calls[k]
    return None


def recent_json(d: Dynasty, n: int = 6) -> list:
    mine = [r for r in list(d.results.values()) if d.mine(d.schedule[r["i"]])] + [r for r in list(d.post_calls) if d.tid in (r["home"], r["away"])]
    mine.sort(key=lambda r: (r["date"], r.get("k", -1), r["i"]))
    return [game_json(d, r) for r in mine[-n:]][::-1]


def standings_json(d: Dynasty, top: int = 25) -> dict:
    """Every conference's standings (conference record, overall, RPI rank) and the national RPI list."""
    rec, crec, rank = d.records(), d.records(True), d.rpi_rank()
    rp = d.rpi()
    confs: dict = {}
    for tid, c in d.real_conf.items():
        confs.setdefault(c, []).append(tid)
    out = {}
    for c, tids in confs.items():
        rows = []
        for t in tids:
            w, l = rec.get(t, [0, 0]); cw, cl = crec.get(t, [0, 0])
            rows.append({"tid": t, "name": d.league.teams[t].name, "w": w, "l": l, "cw": cw, "cl": cl, "rpi_rank": rank.get(t),
                         "rpi": round(rp[t]["rpi"], 4) if t in rp else None, "me": t == d.tid})
        rows.sort(key=lambda r: (-(r["cw"] / (r["cw"] + r["cl"]) if r["cw"] + r["cl"] else 0), -(r["w"] / (r["w"] + r["l"]) if r["w"] + r["l"] else 0), r["name"]))
        out[c] = rows
    nat = sorted(rp, key=lambda t: -rp[t]["rpi"])
    national = [{"rank": i + 1, "tid": t, "name": d.league.teams[t].name, "conference": d.real_conf[t], "w": rec.get(t, [0, 0])[0], "l": rec.get(t, [0, 0])[1],
                 "rpi": round(rp[t]["rpi"], 4), "me": t == d.tid} for i, t in enumerate(nat[:max(top, 64)])]
    return {"conferences": out, "mine": d.real_conf[d.tid], "national": national, "my_rank": rank.get(d.tid)}


# ---- stats, roster, postseason, the season summary ----------------------------------------------------
def _bat_stats(row) -> dict:
    from engine.game2 import B_2B, B_3B, B_AB, B_BB, B_G, B_H, B_HBP, B_HR, B_K, B_PA, B_SF, B_SH, B_ROE
    ab, h, bb, hbp, sf = row[B_AB], row[B_H], row[B_BB], row[B_HBP], row[B_SF]
    tb = h + row[B_2B] + 2 * row[B_3B] + 3 * row[B_HR]
    obp_den = ab + bb + hbp + sf
    avg = h / ab if ab else 0.0
    obp = (h + bb + hbp) / obp_den if obp_den else 0.0
    slg = tb / ab if ab else 0.0
    return {"g": int(row[B_G]), "pa": int(row[B_PA]), "ab": int(ab), "h": int(h), "2b": int(row[B_2B]), "3b": int(row[B_3B]), "hr": int(row[B_HR]),
            "bb": int(bb), "hbp": int(hbp), "k": int(row[B_K]), "sf": int(sf), "sh": int(row[B_SH]), "roe": int(row[B_ROE]),
            "avg": round(avg, 3), "obp": round(obp, 3), "slg": round(slg, 3), "ops": round(obp + slg, 3)}


def _pit_stats(row) -> dict:
    from engine.game2 import P_BB, P_BF, P_ER, P_G, P_GS, P_H, P_HBP, P_HR, P_K, P_OUTS, P_PITCH, P_R
    outs = row[P_OUTS]
    ip = outs / 3
    era = 9 * row[P_ER] / ip if ip else 0.0
    return {"g": int(row[P_G]), "gs": int(row[P_GS]), "ip": _ip(int(outs)), "outs": int(outs), "bf": int(row[P_BF]), "h": int(row[P_H]), "r": int(row[P_R]),
            "er": int(row[P_ER]), "bb": int(row[P_BB]), "hbp": int(row[P_HBP]), "k": int(row[P_K]), "hr": int(row[P_HR]), "pitches": int(row[P_PITCH]),
            "era": round(era, 2), "whip": round((row[P_H] + row[P_BB]) / ip, 2) if ip else 0.0, "k9": round(9 * row[P_K] / ip, 1) if ip else 0.0,
            "bb9": round(9 * row[P_BB] / ip, 1) if ip else 0.0}


def team_stats_json(d: Dynasty, tid: int | None = None) -> dict:
    """The team's batting and pitching lines (regular season through today's games, postseason included: the
    accumulators run across the season). No per-player runs, RBI, stolen bases or decisions: not in the engine's
    accumulators."""
    tid = d.tid if tid is None else tid
    t = d.league.teams[tid]
    games = d.records().get(tid, [0, 0])
    bat = [dict(player_json(p), stats=_bat_stats(d.bstats[p.pid])) for p in t.batters if d.bstats[p.pid][1] > 0]
    pit = [dict(player_json(p), stats=_pit_stats(d.pstats[p.pid])) for p in staff(t) if d.pstats[p.pid][0] > 0]
    bat.sort(key=lambda x: -x["stats"]["pa"])
    pit.sort(key=lambda x: -x["stats"]["outs"])
    return {"tid": tid, "team": t.name, "games": sum(games), "batting": bat, "pitching": pit, "missing": ["R", "RBI", "SB", "W-L", "SV"]}


def leaders_json(d: Dynasty, n: int = 10) -> dict:
    """National leaders among qualified players: batters with at least 2 plate appearances per team game, pitchers
    with at least 1 inning per team game (the NCAA's qualifying floors), counting stats among everyone."""
    rec = d.records()
    tg = {t: sum(v) for t, v in rec.items()}
    rows_b, rows_p = [], []
    for t in d.league.teams:
        g = tg.get(t.tid, 0)
        for p in t.batters:
            row = d.bstats[p.pid]
            if row[1] > 0:
                rows_b.append((p, t, _bat_stats(row), row[1] >= 2 * g and g > 0))
        for p in staff(t):
            row = d.pstats[p.pid]
            if row[0] > 0:
                rows_p.append((p, t, _pit_stats(row), row[3] >= 3 * g and g > 0))
    me = d.tid

    def top(rows, key, qualified, reverse=True):
        pool = [r for r in rows if (r[3] or not qualified)]
        pool.sort(key=lambda r: -key(r[2]) if reverse else key(r[2]))
        return [dict(player_json(r[0]), team=r[1].name, tid=r[1].tid, me=r[1].tid == me, value=key(r[2]), stats=r[2]) for r in pool[:n]]
    return {"batting": {"avg": top(rows_b, lambda s: s["avg"], True), "hr": top(rows_b, lambda s: s["hr"], False), "ops": top(rows_b, lambda s: s["ops"], True),
                        "h": top(rows_b, lambda s: s["h"], False), "bb": top(rows_b, lambda s: s["bb"], False)},
            "pitching": {"era": top(rows_p, lambda s: s["era"], True, reverse=False), "k": top(rows_p, lambda s: s["k"], False),
                         "k9": top(rows_p, lambda s: s["k9"], True), "whip": top(rows_p, lambda s: s["whip"], True, reverse=False), "ip": top(rows_p, lambda s: s["outs"] / 3, False)},
            "floors": {"batting": "2 PA per team game", "pitching": "1 IP per team game"}}


def _hand(p) -> str:
    """B/T once the engine's Player carries handedness (Phase 3: bats, throws); a dash until then."""
    b, t = getattr(p, "bats", None), getattr(p, "throws", None)
    return f"{b or '–'}/{t or '–'}" if (b or t) else "–"


def _year(p) -> str:
    """Class or year once the engine's Player carries it (roster rules); a dash until then."""
    y = getattr(p, "year", None) or getattr(p, "class_year", None) or getattr(p, "klass", None)
    return str(y) if y else "–"


def roster_json(d: Dynasty) -> dict:
    """The user's roster with ratings, position, the season line, and each pitcher's last outing (date and pitches)
    from the Decider's rest history: the facts behind the AI's rest rule, which is internal. No class or year, no
    handedness: not in the engine."""
    t = d.team
    today = d.date_now()
    bats = [dict(player_json(p), stats=_bat_stats(d.bstats[p.pid]), hand=_hand(p), year=_year(p)) for p in t.batters]
    pits = []
    for p in staff(t):
        h = d.mgr.history.get(p.pid, [])
        last = h[-1] if h else None
        pits.append(dict(player_json(p), stats=_pit_stats(d.pstats[p.pid]), hand=_hand(p), year=_year(p),
                         last_outing={"date": int(last[0]), "pitches": int(last[1]), "days_ago": int(today - last[0])} if last else None,
                         outings=len(h)))
    return {"team": t.name, "batters": bats, "pitchers": pits, "date": today}


def _conf_seeds(d: Dynasty) -> dict:
    """The conference tournament seeds the pipeline uses: the same World seed and call order (sorted conferences)
    reproduce its tie-break draws. Only meaningful once the regular season is over."""
    w = SeasonWorld(d.cfg, d.league, np.random.Generator(np.random.PCG64(_child(d._s_post, 0))))
    out = {}
    for conf, f in sorted(w.formats.items()):
        order = w.seeds(conf, d.reg_games)
        if order:
            out[conf] = {"teams": order[:f["teams"]], "format": f["format"], "description": f["description"], "site": f["site_detail"], "venue": f.get("venue", "")}
    return out


def postseason_json(d: Dynasty) -> dict:
    """Conference tournaments (format, seeds, games), Selection Monday (the field, hosts, national seeds, the
    user's status), regionals, supers and the CWS from the recorded games."""
    name = lambda t: d.league.teams[t].name
    out = {"stage": d.stage, "tid": d.tid, "mine_conf": d.real_conf[d.tid]}
    if d.stage == "regular":
        out["note"] = "The postseason begins when the regular season ends."
        return out
    seeds = _conf_seeds(d)
    games = [r for r in d.post_calls]
    gj = lambda r, k: dict(game_json(d, r), k=k)
    conf_done = d.post.get("conference", {})
    out["conference"] = {}
    for conf, sd in seeds.items():
        cg = [gj(r, k) for k, r in enumerate(games) if r["stage"] == "conf" and r["home"] in sd["teams"] and r["away"] in sd["teams"]]
        out["conference"][conf] = {"format": sd["format"], "description": sd["description"], "site": sd["site"], "venue": sd["venue"],
                                   "seeds": [{"seed": i + 1, "tid": t, "name": name(t), "me": t == d.tid} for i, t in enumerate(sd["teams"])],
                                   "games": cg, "champion": conf_done.get(conf, {}).get("champion"),
                                   "champion_name": name(conf_done[conf]["champion"]) if conf in conf_done else None}
    f = d.post.get("field")
    if f:
        rank = f["rank"]
        national = [{"seed": i + 1, "tid": t, "name": name(t), "rpi_rank": rank.get(t), "me": t == d.tid} for i, t in enumerate(f["national_seeds"])]
        autos = set(f["auto"])
        field = [{"tid": t, "name": name(t), "conference": d.real_conf[t], "rpi_rank": rank.get(t), "auto": t in autos,
                  "national_seed": (f["national_seeds"].index(t) + 1) if t in f["national_seeds"] else None,
                  "line": f["seed_order"].index(t) // 16 + 1, "me": t == d.tid} for t in f["seed_order"]]
        mine = next((x for x in field if x["me"]), None)
        out["selection"] = {"national_seeds": national, "field": field, "my_status": mine or {"in": False, "rpi_rank": rank.get(d.tid)},
                            "in_field": mine is not None}
        regs = d.post.get("regionals", [])
        reg_games = [gj(r, k) for k, r in enumerate(games) if r["stage"] == "regional"]
        out["regionals"] = [{"n": i + 1, "host": name(reg[0]), "teams": [{"seed": j + 1, "tid": t, "name": name(t), "me": t == d.tid} for j, t in enumerate(reg)],
                             "games": [g for g in reg_games if g["home"] in reg and g["away"] in reg], "winner": None} for i, reg in enumerate(regs)]
        out["supers"] = [gj(r, k) for k, r in enumerate(games) if r["stage"] == "super"]
        out["cws"] = [gj(r, k) for k, r in enumerate(games) if r["stage"] == "cws"]
        nc = d.post.get("ncaa")
        if nc:
            for i, row in enumerate(nc["regionals"]):
                out["regionals"][i]["winner"] = name(row["winner"])
            out["super_rows"] = [{"teams": [name(t) for t in s["teams"]], "host": name(s["host"]), "winner": name(s["winner"])} for s in nc["supers"]]
            out["champion"], out["runner_up"] = name(nc["champion"]), name(nc["runner_up"])
            out["cws_teams"] = [name(t) for t in nc["cws"]]
    return out


def summary_json(d: Dynasty) -> dict:
    """End of Year 1: the final record, the postseason result, team leaders, the national champion."""
    me = d.tid
    rec, crec = d.records().get(me, [0, 0]), d.records(True).get(me, [0, 0])
    mine_post = [r for r in d.post_calls if me in (r["home"], r["away"])]
    stages = [r["stage"] for r in mine_post]
    result = "missed the postseason"
    f = d.post.get("field")
    nc = d.post.get("ncaa")
    if nc and nc["champion"] == me:
        result = "national champions"
    elif nc and nc["runner_up"] == me:
        result = "national runner-up"
    elif "cws" in stages:
        result = "reached the College World Series"
    elif "super" in stages:
        result = "reached a super regional"
    elif "regional" in stages:
        result = "played in a regional"
    elif f and me in f["field"]:
        result = "selected to the field of 64"
    elif "conf" in stages:
        result = "conference tournament"
    conf_champ = any(v.get("champion") == me for v in d.post.get("conference", {}).values())
    ts = team_stats_json(d)
    bat = [b for b in ts["batting"] if b["stats"]["pa"] >= 2 * sum(rec)]
    lead = {"avg": max(bat, key=lambda b: b["stats"]["avg"]) if bat else None, "hr": max(ts["batting"], key=lambda b: b["stats"]["hr"]) if ts["batting"] else None,
            "ops": max(bat, key=lambda b: b["stats"]["ops"]) if bat else None,
            "era": min([p for p in ts["pitching"] if p["stats"]["outs"] >= 3 * sum(rec)] or ts["pitching"], key=lambda p: p["stats"]["era"]) if ts["pitching"] else None,
            "k": max(ts["pitching"], key=lambda p: p["stats"]["k"]) if ts["pitching"] else None}
    return {"year": d.year, "team": d.team.name, "record": rec, "conf_record": crec, "rpi_rank": (f["rank"].get(me) if f else d.rpi_rank().get(me)),
            "result": result, "conference_champion": conf_champ, "leaders": lead,
            "champion": d.league.teams[nc["champion"]].name if nc else None, "runner_up": d.league.teams[nc["runner_up"]].name if nc else None,
            "done": d.stage == "done",
            "offseason": ["Transfer portal", "MLB draft", "Recruiting", "Roster cuts", "Year 2"]}
