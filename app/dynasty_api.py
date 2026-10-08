"""Dynasty endpoints (app/dynasty.py), mounted by app/api.py.

    GET  /api/saves                        server-side dynasty saves (newest first) and the latest one
    POST /api/dynasties                    {seed?, name?} -> {id, teams: [...with offense and defense on the 20-80 scale]}
                                           (the D1 world of this seed is built here: about 6 s on this machine, a minute on the free tier)
    POST /api/dynasties/{id}/start         {tid} -> hub (the season is built; Year 1 begins)
    GET  /api/dynasties/{id}               hub
    POST /api/dynasties/{id}/sim           {target, pause_mine} -> {job} (a background job; poll progress)
    GET  /api/dynasties/{id}/progress      {running, played, total, stage, date, hub when idle}
    POST /api/dynasties/{id}/game/open     {modes?} -> the pending game's turn (then the /api/games/{gid} endpoints)
    POST /api/dynasties/{id}/game/sim      hub (the AI plays the pending game)
    POST /api/dynasties/{id}/game/finish   hub (the opened game is over)
    GET  /api/dynasties/{id}/schedule      the user's team's schedule and results
    GET  /api/dynasties/{id}/games/{i}     a regular-season game's box score; /postgames/{k} a postseason game's
    GET  /api/dynasties/{id}/standings     conferences and the national RPI list
    GET  /api/dynasties/{id}/stats         the team's batting and pitching, national leaders; /teams/{tid}/stats any team's
    GET  /api/dynasties/{id}/roster        ratings, season lines, pitchers' last outings
    GET  /api/dynasties/{id}/postseason    conference tournaments, the field, regionals, supers, the CWS
    GET  /api/dynasties/{id}/summary       the end-of-year summary and the offseason placeholder
    GET  /api/dynasties/{id}/save          {save} (signed, compressed; the browser mirrors it)
    POST /api/dynasties/load               {save} -> {id, hub}
    DELETE /api/dynasties/{id}             forget the dynasty and delete its server save

Sim jobs run in a thread holding the engine lock (one engine runs at a time); the page polls progress. A finished
step autosaves to the server's save directory (CBS_SAVE_DIR, default saves/ next to app/; the free host's disk is
ephemeral, which is why the browser keeps a mirror). At most two dynasties stay loaded; the least recently used is
saved and dropped, and the engine's table caches (engine.tables, keyed by object id) are cleared so a later engine
never meets a stale entry.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import dynasty as dyn_mod
from engine import tables as engine_tables

router = APIRouter()
SAVE_DIR = Path(os.environ.get("CBS_SAVE_DIR", str(Path(__file__).resolve().parent.parent / "saves")))
MAX_LOADED = 2
_store = None       # set by app.api (the Store: world, games, lock, sign/verify)


def bind(store, sign, verify):
    global _store, _sign, _verify
    _store, _sign, _verify = store, sign, verify
    store.dynasties = {}
    store.dyn_touched = {}
    store.jobs = {}


class NewDynasty(BaseModel):
    seed: int | None = None
    name: str = ""


class Start(BaseModel):
    tid: int


class SimIn(BaseModel):
    target: str = "game"
    pause_mine: bool = True


class OpenIn(BaseModel):
    modes: dict | None = None


class SaveIn(BaseModel):
    save: str


# ---- store helpers ----------------------------------------------------------------------------------
def _get(did: str) -> dyn_mod.Dynasty:
    d = _store.dynasties.get(did)
    if d is None:
        d = _load_server_save(did)
        if d is None:
            raise HTTPException(404, "unknown dynasty (the server may have restarted: load your mirror)")
    _store.dyn_touched[did] = time.time()
    return d


def _put(d: dyn_mod.Dynasty, did: str | None = None) -> str:
    did = did or secrets.token_urlsafe(8)
    _evict(keep=did)
    _store.dynasties[did] = d
    _store.dyn_touched[did] = time.time()
    return did


def _evict(keep: str | None = None) -> None:
    while len(_store.dynasties) >= MAX_LOADED:
        cands = [k for k in _store.dynasties if k != keep and not _running(k)]
        if not cands:
            return
        old = min(cands, key=lambda k: _store.dyn_touched.get(k, 0))
        d = _store.dynasties.pop(old)
        _store.dyn_touched.pop(old, None)
        try:
            _autosave(old, d)
        except Exception:
            pass
        for g in [g for g, r in _store.games.items() if r is d.runner]:
            _store.games.pop(g, None)
        del d
        engine_tables._SPLITS.clear(); engine_tables._OK.clear(); engine_tables._EXTRA.clear()


def _running(did: str) -> bool:
    j = _store.jobs.get(did)
    return bool(j and j["running"])


def _meta(did: str, d: dyn_mod.Dynasty) -> dict:
    h = d.hub() if d.tid is not None else {"team": None, "record": [0, 0], "date": 0, "stage": "pick"}
    return {"id": did, "name": d.name, "team": h.get("team"), "tid": d.tid, "record": h.get("record"), "conf_record": h.get("conf_record"),
            "date": h.get("date"), "week": h.get("week"), "stage": h.get("stage"), "year": d.year, "seed": d.seed, "saved": time.time(),
            "rpi_rank": h.get("rpi_rank")}


def _autosave(did: str, d: dyn_mod.Dynasty) -> dict:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    blob = dyn_mod.save_bytes(d)
    (SAVE_DIR / f"dyn_{did}.cbs").write_bytes(blob)
    meta = _meta(did, d)
    (SAVE_DIR / f"dyn_{did}.json").write_text(json.dumps(meta))
    return meta


def _load_server_save(did: str):
    p = SAVE_DIR / f"dyn_{did}.cbs"
    if not p.exists():
        return None
    with _store.lock:
        d = dyn_mod.load_bytes(_store.ready().cfg, p.read_bytes())
    _put(d, did)
    if d.runner is not None:
        _store.put(d.runner)
    return d


def _hub(did: str, d: dyn_mod.Dynasty) -> dict:
    h = d.hub()
    h["id"] = did
    h["running"] = _running(did)
    h["game_id"] = next((g for g, r in _store.games.items() if r is d.runner), None) if d.runner is not None else None
    h["recent"] = dyn_mod.recent_json(d)
    return h


def _strength(d: dyn_mod.Dynasty) -> list:
    """Teams with offense and defense on the 20-80 scale: z-scores of the drawn team talent (log runs) across D1,
    10 points per SD, 50 the D1 median. Derived for display; the engine's own numbers are o and d."""
    teams = d.league.teams
    o = np.array([t.o for t in teams]); dd = np.array([t.d for t in teams])
    zo = (o - o.mean()) / o.std(); zd = (dd - dd.mean()) / dd.std()
    return [{"tid": t.tid, "name": t.name, "conference": d.real_conf[t.tid], "tier": t.tier,
             "off": int(round(50 + 10 * zo[i])), "def": int(round(50 + 10 * zd[i])), "overall": int(round(50 + 10 * (zo[i] + zd[i]) / np.sqrt(2)))}
            for i, t in enumerate(teams)]


# ---- routes -----------------------------------------------------------------------------------------
@router.get("/api/saves")
def saves():
    out = []
    if SAVE_DIR.exists():
        for p in SAVE_DIR.glob("dyn_*.json"):
            try:
                out.append(json.loads(p.read_text()))
            except Exception:
                continue
    out.sort(key=lambda m: -m.get("saved", 0))
    return {"dynasties": out, "latest": out[0] if out else None}


@router.post("/api/dynasties")
def new_dynasty(body: NewDynasty):
    w = _store.ready()
    seed = body.seed if body.seed is not None else secrets.randbelow(2 ** 31)
    with _store.lock:
        d = dyn_mod.Dynasty(w.cfg, seed, body.name)
        did = _put(d)
    return {"id": did, "seed": seed, "teams": _strength(d)}


@router.post("/api/dynasties/{did}/start")
def start(did: str, body: Start):
    d = _get(did)
    try:
        with _store.lock:
            d.start(body.tid)
    except (ValueError, IndexError) as e:
        raise HTTPException(400, str(e))
    if not d.name:
        d.name = f"{d.team.name} dynasty"
    _autosave(did, d)
    return _hub(did, d)


@router.get("/api/dynasties/{did}")
def hub(did: str):
    d = _get(did)
    if d.tid is None:
        return {"id": did, "stage": "pick", "teams": _strength(d), "seed": d.seed}
    return _hub(did, d)


@router.post("/api/dynasties/{did}/sim")
def sim(did: str, body: SimIn):
    d = _get(did)
    if d.tid is None:
        raise HTTPException(400, "pick a team first")
    if _running(did):
        raise HTTPException(409, "a sim is running")
    if body.target not in dyn_mod.SIM_TARGETS:
        raise HTTPException(400, f"target is one of {dyn_mod.SIM_TARGETS}")
    if d.runner is not None and not d.runner.over:
        raise HTTPException(409, "finish or sim the open game first")
    job = {"running": True, "played": len(d.reg_games) + len(d.post_calls), "total": int((~d.skip).sum()), "stage": d.stage,
           "date": d.date_now(), "error": None, "started": time.time()}
    _store.jobs[did] = job

    def progress(dd):
        job["played"] = len(dd.reg_games) + len(dd.post_calls); job["stage"] = dd.stage; job["date"] = dd.date_now()

    def run():
        try:
            with _store.lock:
                if d.runner is not None and d.runner.over:
                    d.finish_game()
                d.advance(body.target, body.pause_mine, progress)
            _autosave(did, d)
        except Exception as e:          # reported to the page
            job["error"] = str(e)
        finally:
            job["running"] = False
            job["finished"] = time.time()
    threading.Thread(target=run, daemon=True).start()
    return {"job": job}


@router.get("/api/dynasties/{did}/progress")
def progress(did: str):
    d = _get(did)
    j = _store.jobs.get(did) or {"running": False}
    out = {"running": j.get("running", False), "played": j.get("played"), "total": j.get("total"), "stage": j.get("stage"), "date": j.get("date"),
           "error": j.get("error")}
    if not out["running"]:
        out["hub"] = _hub(did, d)
    return out


@router.post("/api/dynasties/{did}/game/open")
def open_game(did: str, body: OpenIn | None = None):
    from app.api import _turn
    d = _get(did)
    if _running(did):
        raise HTTPException(409, "a sim is running")
    try:
        with _store.lock:
            r = d.open_game(body.modes if body else None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    gid = next((g for g, rr in _store.games.items() if rr is r), None) or _store.put(r)
    t = _turn(gid, r, full=True)
    t["dynasty"] = did
    return t


@router.post("/api/dynasties/{did}/game/sim")
def sim_game(did: str):
    d = _get(did)
    if _running(did):
        raise HTTPException(409, "a sim is running")
    try:
        with _store.lock:
            d.sim_game()
    except ValueError as e:
        raise HTTPException(400, str(e))
    _autosave(did, d)
    return _hub(did, d)


@router.post("/api/dynasties/{did}/game/finish")
def finish_game(did: str):
    d = _get(did)
    try:
        with _store.lock:
            d.finish_game()
    except ValueError as e:
        raise HTTPException(400, str(e))
    _autosave(did, d)
    return _hub(did, d)


@router.get("/api/dynasties/{did}/schedule")
def schedule(did: str):
    d = _get(did)
    return {"games": dyn_mod.schedule_json(d), "tid": d.tid}


@router.get("/api/dynasties/{did}/games/{i}")
def game_box(did: str, i: int):
    d = _get(did)
    rec = dyn_mod.find_game(d, i, None)
    if rec is None:
        raise HTTPException(404, "no such game")
    return dyn_mod.game_json(d, rec, full=True)


@router.get("/api/dynasties/{did}/postgames/{k}")
def post_box(did: str, k: int):
    d = _get(did)
    rec = dyn_mod.find_game(d, None, k)
    if rec is None:
        raise HTTPException(404, "no such game")
    return dyn_mod.game_json(d, rec, full=True)


@router.get("/api/dynasties/{did}/standings")
def standings(did: str):
    return dyn_mod.standings_json(_get(did))


@router.get("/api/dynasties/{did}/stats")
def stats(did: str):
    d = _get(did)
    return {"team": dyn_mod.team_stats_json(d), "leaders": dyn_mod.leaders_json(d)}


@router.get("/api/dynasties/{did}/teams/{tid}/stats")
def team_stats(did: str, tid: int):
    d = _get(did)
    if not 0 <= tid < len(d.league.teams):
        raise HTTPException(404, "unknown team")
    return dyn_mod.team_stats_json(d, tid)


@router.get("/api/dynasties/{did}/roster")
def roster(did: str):
    return dyn_mod.roster_json(_get(did))


@router.get("/api/dynasties/{did}/postseason")
def postseason(did: str):
    return dyn_mod.postseason_json(_get(did))


@router.get("/api/dynasties/{did}/summary")
def summary(did: str):
    return dyn_mod.summary_json(_get(did))


@router.get("/api/dynasties/{did}/save")
def save(did: str):
    d = _get(did)
    if _running(did):
        raise HTTPException(409, "a sim is running")
    with _store.lock:
        blob = dyn_mod.save_bytes(d)
    return {"save": _sign(blob), "meta": _meta(did, d)}


@router.post("/api/dynasties/load")
def load(body: SaveIn):
    w = _store.ready()
    data = _verify(body.save)
    try:
        with _store.lock:
            d = dyn_mod.load_bytes(w.cfg, data)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, f"not a dynasty save: {e}")
    did = _put(d)
    if d.runner is not None:
        _store.put(d.runner)
    _autosave(did, d)
    return _hub(did, d) if d.tid is not None else {"id": did, "stage": "pick", "teams": _strength(d), "seed": d.seed}


@router.delete("/api/dynasties/{did}")
def delete(did: str):
    if _running(did):
        raise HTTPException(409, "a sim is running")
    d = _store.dynasties.pop(did, None)
    _store.dyn_touched.pop(did, None)
    if d is not None and d.runner is not None:
        for g in [g for g, r in _store.games.items() if r is d.runner]:
            _store.games.pop(g, None)
    for ext in ("cbs", "json"):
        p = SAVE_DIR / f"dyn_{did}.{ext}"
        if p.exists():
            p.unlink()
    engine_tables._SPLITS.clear(); engine_tables._OK.clear(); engine_tables._EXTRA.clear()
    return {"ok": True}
