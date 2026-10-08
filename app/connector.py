"""Connector between a human at a browser and the engine's game session (prototype, 2026-10-08).

The engine asks each team's controller for its decisions synchronously, between two pause points (engine.game2.
GameSession pauses only before a pitch). A browser cannot answer a synchronous call, so this layer works by
**snapshot and replay**: the runner snapshots the session before a pitch whose aftermath could need the human;
the human's controller answers from an order book and raises AskHuman when the human must be consulted; the
runner then restores the snapshot, shows the question together with the events that preceded it, and when the
answer arrives queues it as an order and re-runs the pitch. The events shown before the question are the real
ones: with the keyed random streams (PR A) every draw before a decision point depends on the game state and the
seed only, never on who answers or how, so the replay reproduces them exactly, and the runner checks that it did.
Human and AI answers go through the same engine code with the same positioned generator: identical odds.

This is a prototype workaround (CLAUDE.md, architecture constraints): the final engine should pause natively at
decision points, a change that goes through the engine session with full gates.

Two kinds of stop, both raised by HumanController.answer:
  soft   a *boundary*: the first time the human's team is asked anything once the sim-ahead target is reached
         (a plate appearance ended, a half or inning turned). Nothing is required of the human; the UI shows the
         result and the decision buttons for the coming plate appearance, and any sim button continues.
  hard   a decision kind the human switched to "ask me": the engine waits for the answer.

Default decision flow (owner decision 2026-10-08): every decision kind is on AI autopilot; the human queues orders
at any pause and the AI answers whatever is not queued; "ask me" per kind blocks with a question.

One engine per process plays every game (app.world); a snapshot carries the session (without the engine; the
teams and the AI manager's static tables by reference) and the engine's accumulator rows of this game's players.
"""
from __future__ import annotations

import io
import pickle
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from app import catalogue as cat
from app.world import EXHIBITION, World
from engine.control import DECISIONS, AIController, Controller
from engine.game2 import SIDES, STOPS, GameSession
from engine.manager import Manager

SAVE_VERSION = 2


class AskHuman(Exception):
    """Raised inside the engine's run by the human's controller: the pitch is abandoned and replayed later."""

    def __init__(self, kind: str, args: tuple, soft: bool, window: int, index: int):
        super().__init__(kind)
        self.kind, self.args, self.soft, self.window, self.index = kind, args, soft, window, index


@dataclass
class Order:
    kind: str
    value: object
    target: int             # the window the order is meant for (orders for earlier windows expire, unless persistent)
    persistent: bool = False
    index: int | None = None   # an answer to a question: for that exact ask (window, index) only


def window_of(state) -> int:
    """The decision window: the number of completed plate appearances. Window w runs from the end of plate
    appearance w (its pitching-change and pinch-runner asks) through the pre-pitch asks of plate appearance w + 1."""
    return state.pa["away"] + state.pa["home"]


def _mark(session, side: str, kind: str, state) -> dict:
    """A compact record of the game at an ask, for the timeline (app.timeline): where in the event log it sits
    and the state a narrator needs. Lineups and pitchers are included only when they changed."""
    app = session.app
    m = {"pos": len(session.log), "side": side, "kind": kind, "inning": state.inning, "half": state.half, "outs": state.outs,
         "score": (state.score["away"], state.score["home"]), "bases": [None if b is None else b[2] for b in state.bases],
         "hits": (state.hits["away"], state.hits["home"]), "errors": (state.errors["away"], state.errors["home"]),
         "pa_serial": session.pa_serial}
    last = app.get("last")
    cur = {s: tuple(p.pid for p in state.lineup.get(s, ())) for s in SIDES}
    pit = {s: (state.pitcher[s].pid if s in state.pitcher else None) for s in SIDES}
    if last is None or cur != last[0]:
        m["lineups"] = cur
    if last is None or pit != last[1]:
        m["pitchers"] = pit
    m["pitches"] = {s: state.outing[s]["pitches"] for s in SIDES if s in state.outing}
    app["last"] = (cur, pit)
    app["marks"].append(m)
    return m


def _last_from(marks: list):
    """The (lineups, pitchers) memo of _mark after the kept marks."""
    cur, pit = None, None
    for m in marks:
        cur, pit = m.get("lineups", cur), m.get("pitchers", pit)
    return None if cur is None else (cur, pit)


class RecordingAI(Controller):
    """The AI manager of a side, recording its asks and answers for the timeline. Same answers as AIController."""

    def __init__(self, side: str, decider):
        self.side = side
        self.ai = AIController(decider)
        self.session = None

    def answer(self, kind, state, rng, *args):
        _mark(self.session, self.side, kind, state)
        ans = self.ai.answer(kind, state, rng, *args)
        text = cat.describe(kind, ans)
        if text:
            self.session.app["records"].append({"pos": len(self.session.log), "side": self.side, "kind": kind, "source": "ai", "text": text,
                                                "pa_serial": self.session.pa_serial})
        return ans


class HumanController(Controller):
    """The human's team: orders, autopilot, boundary stops and questions (module docstring). Asked before every pitch
    (PR B: `per_pitch`), so an order queued at the pause before a pitch applies to that pitch."""

    per_pitch = True
    NO_AI = ("pre_pitch_defense",)      # the AI manager has no such decision: autopilot answers "no call"

    def __init__(self, side: str, decider):
        self.side = side
        self.ai = AIController(decider)
        self.session = None
        self.modes = {k: "auto" for k in DECISIONS}      # auto | ask
        self.orders: dict = {}                            # kind -> [Order, ...] sorted by target window
        self.notes: list = []                             # orders that could not be applied, for the feed
        self.stop_rule = None                             # set per pitch by the runner: callable(state) -> bool
        self.resume = (-1, -1)                            # (window, ask index) of the last raise: no raise at or before it
        self.cur_window, self.ask_no = -1, 0
        self.record_all = False                           # the bench coach's dry run records every answer

    # ---- orders ---------------------------------------------------------------------------
    def queue(self, kind: str, value, target: int, index: int | None = None) -> None:
        """An order for `kind` in window `target`, replacing one already queued for that window; with `index`,
        the answer to the question asked at (target, index), kept beside any other order."""
        d = cat.CATALOGUE[kind]
        lst = [o for o in self.orders.get(kind, []) if o.index is not None or o.target != target or index is not None]
        lst.append(Order(kind, value, target, d.persistent, index))
        self.orders[kind] = sorted(lst, key=lambda o: (o.target, -1 if o.index is None else o.index))

    def clear(self, kind: str) -> None:
        self.orders.pop(kind, None)

    def all_orders(self) -> list:
        return [o for lst in self.orders.values() for o in lst]

    def _take(self, kind: str, w: int, i: int):
        """The order answering the ask (w, i): the answer given to that question, else the first queued order
        that applies to window w. A repeating kind's order stays for the window's later asks."""
        lst = self.orders.get(kind, [])
        for o in lst:
            if o.index is not None and (o.target, o.index) == (w, i):
                lst.remove(o)
                break
        else:
            for o in lst:
                if o.index is None and o.target <= w:
                    if not cat.CATALOGUE[kind].repeat:
                        lst.remove(o)
                    break
            else:
                return None
        if not lst:
            self.orders.pop(kind, None)
        return o

    def _expire(self, w: int) -> None:
        for k in list(self.orders):
            keep = []
            for o in self.orders[k]:
                if o.index is not None and o.target < w:
                    continue                                   # an answer to a question already passed
                if not o.persistent and o.target < w:
                    self.notes.append({"pos": len(self.session.log), "side": self.side, "kind": k, "source": "note",
                                       "text": f"{cat.CATALOGUE[k].label}: the moment passed, order dropped", "pa_serial": self.session.pa_serial})
                else:
                    keep.append(o)
            if keep:
                self.orders[k] = keep
            else:
                del self.orders[k]

    # ---- the engine's call --------------------------------------------------------------------
    def answer(self, kind, state, rng, *args):
        sess = self.session
        w = window_of(state)
        if w != self.cur_window:
            self.cur_window, self.ask_no = w, 0
            self._expire(w)
        i = self.ask_no
        self.ask_no += 1
        _mark(sess, self.side, kind, state)
        d = cat.CATALOGUE[kind]
        source, ans = None, None
        order = self._take(kind, w, i)
        if order is not None:
            if order.value == "auto":
                source = "auto"
            else:
                try:
                    ans, source = d.to_engine(order.value, state, self.side), "order"
                except ValueError as e:
                    self.notes.append({"pos": len(sess.log), "side": self.side, "kind": kind, "source": "note",
                                       "text": f"{d.label}: {e}; the AI decided instead", "pa_serial": sess.pa_serial})
        if source is None:
            if self.modes.get(kind, "auto") == "ask":
                raise AskHuman(kind, args, False, w, i)
            if self.stop_rule is not None and (w, i) > self.resume and self.stop_rule(state):
                raise AskHuman(kind, args, True, w, i)
            source = "auto"
        if source == "auto":
            ans = None if kind in self.NO_AI else self.ai.answer(kind, state, rng, *args)
        text = cat.describe(kind, ans)
        if text or source == "order" or self.record_all:
            sess.app["records"].append({"pos": len(sess.log), "side": self.side, "kind": kind, "source": source,
                                        "text": text or "no change", "pa_serial": sess.pa_serial})
        return ans


# ---- stop rules ----------------------------------------------------------------------------------
# A step's plan is (target, inning, half, window) measured where the step started; the same plan continues after
# a question is answered, so a target set before the question is still the one being run to.
def plan_of(target: str, state) -> tuple:
    return (target, state.inning, state.half, window_of(state))


def soft_rule(plan: tuple):
    """When a step with this plan should pause at the human's next ask (evaluated on the state at the ask)."""
    target, i0, h0, w0 = plan
    if target in ("pitch", "pa"):
        return lambda st: window_of(st) != w0
    if target == "half":
        return lambda st: (st.inning, st.half) != (i0, h0)
    if target in ("inning", "three_innings"):
        k = 1 if target == "inning" else 3
        return lambda st: st.inning > i0 + k or (st.inning == i0 + k and (st.half == h0 or h0 == "T"))
    if target == "game":
        return None
    raise ValueError(target)


def pause_rule(plan: tuple):
    """When a step with this plan stops at a pause before a pitch (the engine's own stop points), the fallback
    behind the soft rule: the human's side is always asked something first, except when the game ends."""
    target, i0, h0, w0 = plan
    if target == "pitch":
        return lambda st: True
    if target == "pa":
        return lambda st: window_of(st) > w0
    return soft_rule(plan)


@dataclass
class Snapshot:
    blob: bytes
    rows: dict              # pid -> (batting row, pitching row) of the engine's accumulators
    app_len: tuple          # lengths of the shared marks and records lists at the snapshot


# The AI manager's tables never change during a game; the two teams' objects never change either. A snapshot
# leaves them out (pickle persistent ids) and a restore reattaches the live objects, which makes a snapshot a
# few kilobytes. A save for the browser (GameRunner.save_bytes) is a full pickle and carries them.
MANAGER_STATIC = ("start", "relw", "patterns", "pattern_w", "sp_table", "sp_back", "wr_table", "wr_back", "rp_table", "rp_back",
                  "relief_coef", "midweek_coef", "tourney_coef", "pull6", "stamina", "spm_table", "spm_back", "subs6", "start_markov",
                  "sub_ib", "sub_mb", "def_slot", "_dm_cache")      # _dm_cache: PR B's decision models, static


class _Pickler(pickle.Pickler):
    def __init__(self, f, ext: dict):
        super().__init__(f, protocol=pickle.HIGHEST_PROTOCOL)
        self.ext = ext

    def persistent_id(self, obj):
        return self.ext.get(id(obj))


class _Unpickler(pickle.Unpickler):
    def __init__(self, f, objects: dict):
        super().__init__(f)
        self.objects = objects

    def persistent_load(self, key):
        return self.objects[key]


class _Placeholder:
    """Stands in for the engine while a save is unpickled (GameSession.load insists on one)."""


class GameRunner:
    """One game: the live session, its latest snapshot, and the view of an abandoned pitch (module docstring).

    `base`: the resumable session (at a pause point: pregame or before a pitch). `view`: after a pitch raised
    AskHuman, the abandoned session object at the ask (its state is what the UI shows); None otherwise. The
    marks and records the abandoned pitch produced are kept in `view_tail` for the timeline.
    """

    def __init__(self, world: World, session: GameSession, user_side: str, meta: dict, base_rows: dict):
        self.world, self.base, self.eng, self.user, self.meta = world, session, world.eng, user_side, meta
        self.base_rows = base_rows                      # accumulator rows at the game's creation: lines are differences
        self.pids = list(base_rows)
        self.view: GameSession | None = None
        self.raised: AskHuman | None = None
        self.view_tail: tuple = ([], [])
        self.plan: tuple | None = None
        self.error: str | None = None            # the engine's refusal of the last call, reported once in the turn
        self.attach(session)

    # ---- construction -------------------------------------------------------------------------
    @classmethod
    def new(cls, world: World, home_tid: int, away_tid: int, user_side: str, seed, exhibition: dict | None = None,
            mgr=None, neutral: bool = False, tournament: bool = False) -> "GameRunner":
        """An exhibition (EXHIBITION's calendar slot, a fresh Decider) or, with `mgr`, a dynasty game: the season's
        Decider (its rest history), the schedule's calendar slot in `exhibition`, neutral site and tournament usage."""
        if user_side not in SIDES:
            raise ValueError("user_side is 'home' or 'away'")
        if home_tid == away_tid:
            raise ValueError("a team cannot play itself")
        ex = dict(EXHIBITION, **(exhibition or {}))
        home, away = world.team(home_tid), world.team(away_tid)
        mgr = mgr if mgr is not None else Manager(world.cfg)
        opp = "home" if user_side == "away" else "away"
        ctrl = {user_side: HumanController(user_side, mgr), opp: RecordingAI(opp, mgr)}
        sess = GameSession(world.eng, np.random.Generator(np.random.PCG64(seed)), home, away, ex["weekend"], mgr,
                           week=ex["week"], day=ex["day"], date=ex["date"], neutral=neutral, tournament=tournament, controllers=ctrl, log=True)
        sess.app = {"marks": [], "records": [], "last": None}
        meta = {"home_tid": home_tid, "away_tid": away_tid, "seed": seed if isinstance(seed, int) else None, "exhibition": ex,
                "league_seed": world.seed, "neutral": neutral, "tournament": tournament}
        rows = cls._rows(world.eng, world.game_pids(home, away))
        return cls(world, sess, user_side, meta, rows)

    @staticmethod
    def _rows(eng, pids) -> dict:
        return {pid: (list(eng.bstats[pid]), list(eng.pstats[pid])) for pid in pids}

    def _put_rows(self, rows: dict) -> None:
        e = self.eng
        for pid, (b, p) in rows.items():
            e.bstats[pid][:] = b
            e.pstats[pid][:] = p

    def attach(self, sess: GameSession) -> None:
        for c in sess.ctrl.values():
            c.session = sess
        sess.eng = self.eng

    @property
    def human(self) -> HumanController:
        return self.base.ctrl[self.user]

    @property
    def current(self) -> GameSession:
        """The session the UI looks at: the abandoned pitch's view when there is one, else the live base."""
        return self.view if self.view is not None else self.base

    @property
    def over(self) -> bool:
        return self.base.phase == "over"

    def marks(self) -> list:
        return self.base.app["marks"] + self.view_tail[0]

    def records(self) -> list:
        return self.base.app["records"] + self.view_tail[1]

    def lines(self) -> dict:
        """This game's accumulator rows (current minus the rows at creation), for the current view."""
        e = self.eng
        out = {}
        for pid, (b0, p0) in self.base_rows.items():
            out[pid] = ([x - y for x, y in zip(e.bstats[pid], b0)], [x - y for x, y in zip(e.pstats[pid], p0)])
        return out

    # ---- snapshots ------------------------------------------------------------------------------
    def _externals(self) -> dict:
        """key -> live object left out of snapshots: the teams, the manager's tables, the shared mark lists."""
        sess = self.base
        objs = {"home": sess.st.team_obj["home"], "away": sess.st.team_obj["away"], "app": sess.app}
        mgr = sess.book
        for name in MANAGER_STATIC:
            v = getattr(mgr, name, None)
            if v is not None and not isinstance(v, (int, float, str, bool)):
                objs["mgr." + name] = v
        return objs

    def snapshot(self) -> Snapshot:
        sess = self.base
        objs = self._externals()
        ext = {id(v): k for k, v in objs.items()}
        eng = sess.eng
        sess.eng = None
        try:
            f = io.BytesIO()
            _Pickler(f, ext).dump(sess)
        finally:
            sess.eng = eng
        app = sess.app
        return Snapshot(f.getvalue(), self._rows(self.eng, self.pids), (len(app["marks"]), len(app["records"])))

    def restore(self, snap: Snapshot) -> tuple:
        """The session at the snapshot (a new object, attached), and the marks and records cut off the shared
        lists (what the abandoned pitch had added)."""
        objs = self._externals()
        sess = _Unpickler(io.BytesIO(snap.blob), objs).load()
        self._put_rows(snap.rows)
        app = sess.app
        n_m, n_r = snap.app_len
        tail = (app["marks"][n_m:], app["records"][n_r:])
        del app["marks"][n_m:]
        del app["records"][n_r:]
        app["last"] = _last_from(app["marks"])
        self.attach(sess)
        return sess, tail

    # ---- play -------------------------------------------------------------------------------
    def step(self, target: str) -> dict:
        """Run to `target` (engine.game2.STOPS) or to the human's next stop; returns the turn."""
        if target not in STOPS:
            raise ValueError(f"target is one of {STOPS}")
        if self.over:
            self.plan = None
            return self.turn()
        self.plan = plan_of(target, self.current.st)
        return self._run()

    @staticmethod
    def _may_raise(plan: tuple, st, hc) -> bool:
        """Whether the asks after the next pitch could raise: a question (a kind on 'ask me'), or a boundary
        (the plan's condition would hold once this plate appearance, or this half-inning, ended). Otherwise
        the pitch needs no snapshot before it."""
        if any(m == "ask" for m in hc.modes.values()):
            return True
        rule = soft_rule(plan)
        if rule is None:
            return False
        if plan[0] in ("pitch", "pa"):
            return True
        nxt = SimpleNamespace(inning=st.inning, half="B", pa=st.pa) if st.half == "T" else SimpleNamespace(inning=st.inning + 1, half="T", pa=st.pa)
        return bool(rule(nxt))

    def _run(self) -> dict:
        """Pitch by pitch toward the plan, a snapshot before any pitch whose aftermath could raise, until a
        pause-point stop, a raise from the human's controller, or the end of the game."""
        plan = self.plan
        pause = pause_rule(plan)
        expected = self.view.log if self.view is not None else None
        resume = (self.raised.window, self.raised.index) if self.raised is not None else (-1, -1)
        first = True
        snap = None
        while True:
            sess = self.base
            if sess.phase == "over":
                self.view, self.raised, self.view_tail = None, None, ([], [])
                break
            if not first and pause is not None and pause(sess.st):
                break
            hc = sess.ctrl[self.user]
            if first or self._may_raise(plan, sess.st, hc):
                snap = self.snapshot()               # before the rule is set: a snapshot holds no rule
            hc.stop_rule, hc.resume = soft_rule(plan), resume
            try:
                sess.sim_ahead("pitch")
                self.view, self.raised, self.view_tail = None, None, ([], [])
            except AskHuman as ask:
                hc.stop_rule = None
                self.view, self.raised = sess, ask
                self.base, self.view_tail = self.restore(snap)
                break
            except ValueError as e:
                # the engine refused a call (NCAA rules, e.g. a second mound trip with the same batter at bat): back
                # to the pause before the pitch, the pre-pitch orders dropped, the reason reported in the turn
                hc.stop_rule = None
                if snap is None:
                    raise
                self.base, _ = self.restore(snap)
                for k in ("pre_pitch", "pre_pitch_defense"):
                    self.human.clear(k)
                self.view, self.raised, self.view_tail = None, None, ([], [])
                self.error = str(e)
                break
            finally:
                hc.stop_rule = None
            first = False
            if expected is not None:
                # the replay reproduced what the abandoned pitch had shown (keyed streams; module docstring)
                n = min(len(expected), len(sess.log))
                if sess.log[:n] != expected[:n]:
                    raise RuntimeError("replay diverged from the events already shown")
                if len(sess.log) >= len(expected):
                    expected = None
        return self.turn()

    def queue(self, kind: str, value, index: int | None = None) -> None:
        """Queue an order for the next time the engine asks the human's team `kind`. A pitching change may carry
        its reliever: {"yes": true, "reliever": pid}. Value "auto" hands the decision to the AI (answers a question).
        With `index`, the order answers the question asked at that index of the current window."""
        if kind not in cat.CATALOGUE:
            raise ValueError(f"unknown decision kind {kind}")
        d = cat.CATALOGUE[kind]
        st = self.current.st
        target = self.window_now(kind)
        hc = self.human
        if value != "auto":
            if kind == "pitching_change" and isinstance(value, dict):
                if value.get("yes") and value.get("reliever") is not None:
                    cat.CATALOGUE["relief_pitcher"].to_engine(value["reliever"], st, self.user)
                    hc.queue("relief_pitcher", value["reliever"], target)
                d.to_engine({"yes": bool(value.get("yes"))}, st, self.user)
                hc.queue(kind, "yes" if value.get("yes") else "no", target, index)
                return
            d.to_engine(value, st, self.user)          # validated now against the current state, again when asked
        hc.queue(kind, value, target, index)

    def clear(self, kind: str) -> None:
        self.human.clear(kind)

    def answer(self, kind: str, value) -> dict:
        """Answer the pending question and continue the interrupted step."""
        if self.raised is None or self.raised.soft or self.raised.kind != kind:
            raise ValueError("no such question is pending")
        self.queue(kind, value, self.raised.index)
        return self._run()

    def set_mode(self, kind: str, mode: str) -> None:
        """Switch a kind between autopilot and "ask me". Switching to autopilot while that kind's question is
        pending hands the question to the AI and leaves the game paused where it is."""
        if kind not in cat.CATALOGUE or mode not in ("auto", "ask"):
            raise ValueError("mode is auto or ask")
        self.human.modes[kind] = mode
        if mode == "auto" and self.raised is not None and not self.raised.soft and self.raised.kind == kind:
            self.queue(kind, "auto", self.raised.index)
            self.raised.soft = True

    def window_now(self, kind: str | None = None) -> int:
        """The window the human's next orders are for: the view's at a stop, else the one after the pause's. A
        pre-pitch kind (asked inside the coming pitch) targets the pause's own window."""
        if self.view is not None:
            return window_of(self.view.st)
        st = self.base.st
        if self.base.phase == "pregame":
            return window_of(st)
        if kind is not None and cat.CATALOGUE[kind].when == cat.PRE_PITCH:
            return window_of(st)
        return window_of(st) + (1 if self.base.pa is not None else 0)

    # ---- the bench coach: what the AI would do from here, by a dry run on a copy ---------------------
    def recommend(self) -> list:
        """The AI's answers for the human's team through the end of the next decision window, from a copy of the
        session (the live game is untouched; the engine's accumulator rows are restored afterwards)."""
        snap = self.snapshot()
        objs = self._externals()
        objs["app"] = {"marks": [], "records": [], "last": None}       # the dry run's own lists
        sess = _Unpickler(io.BytesIO(snap.blob), objs).load()
        sess.eng = self.eng
        for c in sess.ctrl.values():
            c.session = sess
        try:
            hc = sess.ctrl[self.user]
            hc.orders = {}
            hc.modes = {k: "auto" for k in DECISIONS}
            hc.stop_rule = None
            hc.record_all = True
            w0 = window_of(sess.st)
            pregame = sess.phase == "pregame"
            while sess.phase != "over":
                sess.sim_ahead("pitch")
                if window_of(sess.st) > w0 or pregame:
                    break
            recs = [r for r in sess.app["records"] if r["side"] == self.user]
            out = [{"kind": r["kind"], "text": r["text"]} for r in recs
                   if not (pregame and r["kind"] in ("lineup", "starting_pitcher"))
                   and not (cat.CATALOGUE[r["kind"]].when == cat.PRE_PITCH and r["text"] == "no change")]
            if pregame:
                st = sess.st
                out.append({"kind": "lineup", "pids": [p.pid for p in st.lineup[self.user]]})
                out.append({"kind": "starting_pitcher", "pid": st.pitcher[self.user].pid})
            return out
        finally:
            self._put_rows(snap.rows)   # the accumulator rows, touched by the dry run, back to the live game's
            self.attach(self.base)

    # ---- save and load -------------------------------------------------------------------------
    def save_bytes(self) -> bytes:
        """The game at its resumable point (the base), with its accumulator rows and metadata: a full pickle."""
        hc = self.base.ctrl[self.user]
        return pickle.dumps({"version": SAVE_VERSION, "blob": self.base.save(include_engine=False), "rows": self._rows(self.eng, self.pids),
                             "base_rows": self.base_rows, "user": self.user, "meta": self.meta,
                             "orders": [(o.kind, o.value, o.target, o.index) for o in hc.all_orders()],
                             "modes": dict(hc.modes)}, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load_bytes(cls, world: World, data: bytes, mgr=None) -> "GameRunner":
        """With `mgr` (a dynasty's Decider), the loaded session and its controllers are bound to it instead of the
        copy the save carries, so the game's outings land in the season's rest history."""
        d = pickle.loads(data)
        if d.get("version") != SAVE_VERSION:
            raise ValueError("unknown save version")
        sess = GameSession.load(d["blob"], engine=_Placeholder())
        if mgr is not None:
            sess.book = mgr
            for c in sess.ctrl.values():
                c.ai.dec = mgr
        r = cls(world, sess, d["user"], d["meta"], d["base_rows"])
        r._put_rows(d["rows"])
        hc = r.human
        for k, v, t, i in d.get("orders", []):
            hc.queue(k, v, t, i)
        hc.modes.update(d.get("modes", {}))
        return r

    # ---- the turn: what the UI needs -----------------------------------------------------------------
    def turn(self) -> dict:
        sess = self.current
        st = sess.st
        hc = self.human
        if self.base.phase == "over" and self.view is None:
            phase = "over"
        elif self.raised is not None:
            phase = "question" if not self.raised.soft else "boundary"
        else:
            phase = "pregame" if self.base.phase == "pregame" else "pitch"
        pending = None
        if self.raised is not None:
            d = cat.CATALOGUE[self.raised.kind]
            info = next((a for a in self.raised.args if isinstance(a, dict)), None)
            pending = {"kind": self.raised.kind, "soft": self.raised.soft, "label": d.label,
                       "args": [a for a in self.raised.args if isinstance(a, (int, str))],
                       "count": list(info["count"]) if info and "count" in info else None, **d.legal(st, self.user)}
        err, self.error = self.error, None
        return {"phase": phase, "user_side": self.user, "window": self.window_now(), "pending": pending, "error": err,
                "orders": [{"kind": o.kind, "value": o.value, "target": o.target} for o in hc.all_orders() if o.index is None],
                "modes": dict(hc.modes), "actions": self.actions(st)}

    def actions(self, st) -> list:
        """The decision buttons: every kind in the catalogue, with whether the human's team can act on it now."""
        out = []
        user = self.user
        bats_now = st.batting_side == user
        bats_next = (not bats_now) if st.outs >= 3 else bats_now        # after the third out the sides swap
        raised = self.raised.kind if self.raised is not None else None
        for k in DECISIONS:
            d = cat.CATALOGUE[k]
            leg = d.legal(st, user)
            legal, reason = leg["legal"], leg["reason"]
            if d.when == cat.PREGAME:
                if self.base.phase != "pregame":
                    legal, reason = False, "set before the game"
            elif k == raised:
                pass
            elif k == "pinch_runner":
                legal, reason = False, "only right after your batter reaches base"
            elif k == "relief_pitcher":
                legal, reason = False, "choose the reliever with the pitching change"
            elif d.when == cat.PRE_PITCH:
                # for the coming pitch: at a pause before a pitch (the plate appearance in progress) or at a boundary
                # (the next plate appearance's first pitch); the side that bats or fields that pitch
                in_pa = self.current.pa is not None or self.raised is not None
                if self.base.phase == "over" or not in_pa:
                    legal, reason = False, "no pitch is coming"
                elif (d.side == cat.BATTING) != bats_next:
                    legal, reason = False, ("your team is in the field" if d.side == cat.BATTING else "your team is batting")
            elif d.side == cat.BATTING and not bats_next:
                legal, reason = False, "your team is in the field"
            elif d.side == cat.FIELDING and bats_next and not d.persistent:
                legal, reason = False, "your team is batting"
            if k == "steal_attempt" and legal and getattr(self.eng, "dec_steal", False):
                legal, reason = False, "steals are called before a pitch (Before the pitch)"
            if k == "steal_attempt" and legal and all(b is None for b in st.bases):
                legal, reason = False, "no runner on base"
            out.append({"kind": k, "label": d.label, "legal": legal, "reason": reason, "answer": d.answer, "options": leg["options"],
                        "picks": leg.get("picks"), "mode": self.human.modes.get(k, "auto"), "queued": k in self.human.orders})
        return out
