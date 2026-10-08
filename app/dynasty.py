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
SIM_TARGETS = ("game", "week", "regular", "conf", "selection", "end")
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
        self._build_engine()

    def _build_engine(self) -> None:
        n = len(self.league.players)
        if self.bstats is None:
            self.bstats = [[0] * B_NCOL for _ in range(n)]
            self.pstats = [[0] * P_NCOL for _ in range(n)]
        self.eng = PlayerGameEngine(self.cfg, self.league, self.bstats, self.pstats)
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
        """The next scheduled game not yet played (skipping dropped and canceled ones), or None."""
        i = self.pos
        while i < len(self.schedule) and self.skip[i]:
            i += 1
        return i if i < len(self.schedule) else None

    def my_games(self) -> list:
        return [i for i, g in enumerate(self.schedule) if self.mine(g) and not self.skip[i]]

    def _week_of(self, date: int) -> int:
        return int(date) // 7

    def advance(self, target: str, pause_mine: bool = True, progress=None) -> dict:
        """Sim toward `target` (SIM_TARGETS): the next game of the user's team, the end of this week, the end of
        the regular season, the conference tournaments, Selection Monday, the end of the season. The user's games
        pause the sim (pause_mine) so the user plays or sims them; otherwise the AI plays them. Returns the hub state."""
        if target not in SIM_TARGETS:
            raise ValueError(f"target is one of {SIM_TARGETS}")
        if self.pending is not None and self.runner is not None:
            raise ValueError("finish or sim the pending game first")
        if self.pending is not None and pause_mine:
            return self.hub()
        self.pending = None
        n, week0 = 0, None
        while self.stage == "regular":
            i = self.next_index()
            if i is None:
                self.stage = "conf"
                self.pos = len(self.schedule)
                break
            g = self.schedule[i]
            if target == "week" and week0 is not None and self._week_of(g.date) != week0:
                break
            if self.mine(g) and pause_mine:
                self.pending = {"i": i, "home": g.home, "away": g.away, "date": g.date, "weekend": g.weekend, "stage": "regular", "neutral": False}
                break
            self._play(i)
            self.pos = i + 1
            n += 1
            week0 = self._week_of(g.date) if week0 is None else week0
            if progress:
                progress(self)
            if target == "game" and self.mine(g):
                break
        if self.stage not in ("regular", "done") and target != "regular":
            self._run_post("game" if target == "week" else target, pause_mine, progress)
        return self.hub()

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
        i = self.next_index()
        if self.stage == "regular" and i is not None:
            return int(self.schedule[i].date)
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
        return {"id": None, "name": self.name, "seed": self.seed, "year": self.year, "tid": me, "team": self.league.teams[me].name,
                "conference": self.real_conf[me], "tier": self.league.teams[me].tier, "record": rec, "conf_record": crec, "rpi_rank": rank,
                "date": self.date_now(), "week": self._week_of(self.date_now()) + 1, "stage": self.stage, "pending": pend,
                "games_played": len(self.reg_games), "games_total": int((~self.skip).sum()), "news": self.news[-12:][::-1]}


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
    mine = [r for r in d.results.values() if d.mine(d.schedule[r["i"]])] + [r for r in d.post_calls if d.tid in (r["home"], r["away"])]
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
