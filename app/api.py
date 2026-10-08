"""The web API around the connector (prototype, 2026-10-08): FastAPI, JSON, one process, games in memory.

    GET  /api/league                 teams
    GET  /api/teams/{tid}            roster with 20-80 ratings
    GET  /api/decisions              the decision catalogue (engine.control.DECISIONS through app.catalogue)
    POST /api/games                  {home, away, user_side, seed?} -> the pregame turn
    GET  /api/games/{id}             the current turn
    POST /api/games/{id}/sim         {target} -> turn (pitch | pa | half | inning | three_innings | game)
    POST /api/games/{id}/orders      {kind, value} -> turn (queue an order; value "auto" or null clears it)
    POST /api/games/{id}/decide      {kind, value} -> turn (answer the pending question; "auto" lets the AI decide)
    POST /api/games/{id}/modes       {kind, mode} -> turn (auto | ask)
    GET  /api/games/{id}/coach       what the AI would do for the user's team next (the bench coach)
    GET  /api/games/{id}/box         box score and the whole feed
    GET  /api/games/{id}/save        {save: base64} (signed; the browser keeps it)
    POST /api/games/load             {save} -> a game id and its turn
    GET  /                           the frontend (app/static/v2; the first page at /static/index.html)

A turn carries the state (app.timeline.state_json), the feed entries since the client's cursor, the pending
question or boundary, the queued orders, the modes and the decision buttons. Saves are pickles signed with
HMAC-SHA256 under CBS_SAVE_SECRET (an unsigned or foreign save is refused: unpickling untrusted bytes runs code).
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager
import hashlib
import hmac
import os
import secrets
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import catalogue as cat
from app.connector import GameRunner
from app.timeline import Narrator, box_score, state_json
from app.world import World
from engine.game2 import STOPS

STATIC = Path(__file__).resolve().parent / "static"
MAX_GAMES = 200                      # games kept in memory (oldest dropped; the browser holds the save)
SECRET = os.environ.get("CBS_SAVE_SECRET", "").encode() or hashlib.sha256(b"college-baseball-sim prototype").digest()


class Store:
    def __init__(self):
        self.world: World | None = None
        self.games: dict = {}
        self.cursors: dict = {}
        self.touched: dict = {}
        self.lock = threading.Lock()         # one engine per process: one game steps at a time

    def ready(self) -> World:
        if self.world is None:
            self.world = World()
        return self.world

    def put(self, runner: GameRunner) -> str:
        gid = secrets.token_urlsafe(9)
        self.games[gid] = runner
        self.cursors[gid] = 0
        self.touched[gid] = time.time()
        while len(self.games) > MAX_GAMES:
            old = min(self.touched, key=self.touched.get)
            for d in (self.games, self.cursors, self.touched):
                d.pop(old, None)
        return gid

    def get(self, gid: str) -> GameRunner:
        r = self.games.get(gid)
        if r is None:
            raise HTTPException(404, "unknown game (the server may have restarted: load your save)")
        self.touched[gid] = time.time()
        return r


store = Store()


@asynccontextmanager
async def _lifespan(app):
    store.ready()
    yield


app = FastAPI(title="College Baseball Sim — game prototype", lifespan=_lifespan)


# ---- models -------------------------------------------------------------------------------
class NewGame(BaseModel):
    home: int
    away: int
    user_side: str = "home"
    seed: int | None = None


class Sim(BaseModel):
    target: str


class OrderIn(BaseModel):
    kind: str
    value: object = None


class ModeIn(BaseModel):
    kind: str
    mode: str


class SaveIn(BaseModel):
    save: str


# ---- helpers ------------------------------------------------------------------------------
def _sign(data: bytes) -> str:
    mac = hmac.new(SECRET, data, hashlib.sha256).digest()
    return base64.b64encode(mac + data).decode()


def _verify(text: str) -> bytes:
    try:
        raw = base64.b64decode(text)
    except Exception:
        raise HTTPException(400, "not a save")
    mac, data = raw[:32], raw[32:]
    if not hmac.compare_digest(mac, hmac.new(SECRET, data, hashlib.sha256).digest()):
        raise HTTPException(400, "this save was not made by this server")
    return data


def _turn(gid: str, runner: GameRunner, full: bool = False) -> dict:
    t = runner.turn()
    t["game_id"] = gid
    t["state"] = state_json(runner)
    nar = Narrator(runner)
    entries = nar.build()
    cur = 0 if full else store.cursors.get(gid, 0)
    t["events"] = entries[cur:]
    t["feed_cursor"] = store.cursors[gid] = len(entries)
    t["meta"] = runner.meta
    return t


def _call(fn):
    """Run a connector call under the engine lock, turning its ValueErrors into 400s."""
    with store.lock:
        try:
            return fn()
        except ValueError as e:
            raise HTTPException(400, str(e))


# ---- routes -------------------------------------------------------------------------------
@app.get("/api/league")
def league():
    w = store.ready()
    return {"teams": w.teams(), "league_seed": w.seed}


@app.get("/api/teams/{tid}")
def team(tid: int):
    w = store.ready()
    try:
        return w.roster(tid)
    except KeyError:
        raise HTTPException(404, "unknown team")


@app.get("/api/decisions")
def decisions():
    return {"kinds": cat.catalogue_json(), "stops": list(STOPS)}


@app.post("/api/games")
def new_game(body: NewGame):
    w = store.ready()
    seed = body.seed if body.seed is not None else secrets.randbelow(2 ** 31)
    try:
        runner = _call(lambda: GameRunner.new(w, body.home, body.away, body.user_side, seed))
    except KeyError:
        raise HTTPException(404, "unknown team")
    gid = store.put(runner)
    return _turn(gid, runner, full=True)


@app.get("/api/games/{gid}")
def get_game(gid: str, full: bool = False):
    return _turn(gid, store.get(gid), full=full)


@app.post("/api/games/{gid}/sim")
def sim(gid: str, body: Sim):
    r = store.get(gid)
    if r.raised is not None and not r.raised.soft:
        raise HTTPException(409, "answer the pending question first")
    _call(lambda: r.step(body.target))
    return _turn(gid, r)


@app.post("/api/games/{gid}/orders")
def order(gid: str, body: OrderIn):
    r = store.get(gid)
    if body.value is None:
        _call(lambda: r.clear(body.kind))
    else:
        _call(lambda: r.queue(body.kind, body.value))
    return _turn(gid, r)


@app.post("/api/games/{gid}/decide")
def decide(gid: str, body: OrderIn):
    r = store.get(gid)
    _call(lambda: r.answer(body.kind, body.value))         # "auto" hands it to the AI; null is "no one" for a pick
    return _turn(gid, r)


@app.post("/api/games/{gid}/modes")
def modes(gid: str, body: ModeIn):
    r = store.get(gid)
    _call(lambda: r.set_mode(body.kind, body.mode))
    return _turn(gid, r)


@app.get("/api/games/{gid}/coach")
def coach(gid: str):
    r = store.get(gid)
    if r.over:
        return {"advice": []}
    advice = _call(lambda: r.recommend())
    w = store.ready()
    names = {p.pid: p.name for t in r.base.st.team_obj.values() for p in t.batters + t.weekend_sp + t.midweek_sp + t.relievers}
    for a in advice:
        if "pids" in a:
            a["names"] = [names.get(p, str(p)) for p in a["pids"]]
        if "pid" in a:
            a["name"] = names.get(a["pid"], str(a["pid"]))
        a["label"] = cat.CATALOGUE[a["kind"]].label if a["kind"] in cat.CATALOGUE else a["kind"]
    return {"advice": advice, "league_seed": w.seed}


@app.get("/api/games/{gid}/box")
def box(gid: str):
    r = store.get(gid)
    with store.lock:
        return box_score(r)


@app.get("/api/games/{gid}/save")
def save(gid: str):
    r = store.get(gid)
    with store.lock:
        data = r.save_bytes()
    return {"save": _sign(data), "meta": r.meta, "phase": r.turn()["phase"]}


@app.post("/api/games/load")
def load(body: SaveIn):
    w = store.ready()
    data = _verify(body.save)
    runner = _call(lambda: GameRunner.load_bytes(w, data))
    gid = store.put(runner)
    return _turn(gid, runner, full=True)


@app.get("/api/health")
def health():
    return {"ok": True, "games": len(store.games)}


# ---- the frontend --------------------------------------------------------------------------
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC / "v2" / "index.html"))      # the manager screen (v2); v1 stays at /static/index.html
