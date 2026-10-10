"""Dynasty endpoints (app/dynasty.py), mounted by app/api.py.

    GET  /api/saves                        server-side dynasty saves (newest first) and the latest one
    POST /api/dynasties                    {seed?, name?} -> {id, teams: [...with offense and defense on the 20-80 scale]}
                                           (the D1 world of this seed is built here: about 6 s on this machine, a minute on the free tier)
    POST /api/dynasties/{id}/start         {tid} -> hub (the season is built; Year 1 begins)
    GET  /api/dynasties/{id}               hub
    POST /api/dynasties/{id}/sim           {target, pause_mine, stops} -> {job} (a background job; poll progress)
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

Sim jobs run in a thread holding the engine lock (one engine runs at a time); the page polls progress. While the user plays
a game, a background job sims the rest of that week's other games one at a time under the lock, so the user's pitches
interleave (owner decision 2026-10-08, option 2 of reports/dynasty_latency.md). A finished
step autosaves to the server's save directory (CBS_SAVE_DIR, default saves/ next to app/; the free host's disk is
ephemeral, which is why the browser keeps a mirror). One dynasty stays loaded; the one in memory is
saved and dropped when another is opened (the engine caches its base-running splits on the table cells since main's f226d44, so a
dropped engine leaves nothing stale behind).
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
from app.dynasty import game_venue
from app import identity, schools

router = APIRouter()
SAVE_DIR = Path(os.environ.get("CBS_SAVE_DIR", str(Path(__file__).resolve().parent.parent / "saves")))
MAX_LOADED = 1          # a season's engine state is a few hundred MB: one dynasty in memory on the 512 MB host
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
    stops: list[str] = []            # dynasty.STOPS: week_end, postseason, selection (the Settings' auto-pauses)


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


def _running(did: str) -> bool:
    j = _store.jobs.get(did)
    return bool(j and j["running"])


def _meta(did: str, d: dyn_mod.Dynasty) -> dict:
    h = d.hub() if d.tid is not None else {"team": None, "record": [0, 0], "date": 0, "stage": "pick"}
    return {"id": did, "name": d.name, "team": h.get("team"), "tid": d.tid, "record": h.get("record"), "conf_record": h.get("conf_record"),
            "date": h.get("date"), "week": h.get("week"), "stage": h.get("stage"), "year": d.year, "seed": d.seed, "saved": time.time(),
            "rpi_rank": h.get("rpi_rank")}


def _autosave(did: str, d: dyn_mod.Dynasty) -> dict:
    """Under the engine lock (re-entrant): the background job changes the dynasty between games."""
    with _store.lock:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        blob = dyn_mod.save_bytes(d)
        meta = _meta(did, d)
    (SAVE_DIR / f"dyn_{did}.cbs").write_bytes(blob)
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


def _read(fn):
    """A reader under the engine lock: the background job changes the dynasty's results between games."""
    with _store.lock:
        return fn()


def _hub(did: str, d: dyn_mod.Dynasty) -> dict:
    return _read(lambda: _hub_unlocked(did, d))


def _hub_unlocked(did: str, d: dyn_mod.Dynasty) -> dict:
    h = d.hub()
    h["id"] = did
    j = _store.jobs.get(did)
    h["running"] = _running(did)
    h["job_kind"] = j.get("kind", "sim") if j and j["running"] else None
    h["game_id"] = next((g for g, r in _store.games.items() if r is d.runner), None) if d.runner is not None else None
    h["recent"] = dyn_mod.recent_json(d)
    if schools.available() and d.tid is not None:
        h["school"] = schools.school(d.tid)
        h["report_card"] = schools.report_card(d.tid, schools.omaha_grades(d.league.teams).get(d.tid))
    return h


def _strength(d: dyn_mod.Dynasty) -> list:
    """Teams with offense and defense on the 20-80 scale: z-scores of the drawn team talent (log runs) across D1,
    10 points per SD, 50 the D1 median. Derived for display; the engine's own numbers are o and d. With the real
    school identity (name, conference, tier, location) and the report card, Omaha Contender regraded from this
    dynasty's draw (app/schools.py; data only, never read by the engine)."""
    teams = d.league.teams
    o = np.array([t.o for t in teams]); dd = np.array([t.d for t in teams])
    zo = (o - o.mean()) / o.std(); zd = (dd - dd.mean()) / dd.std()
    omaha = schools.omaha_grades(teams) if schools.available() else {}
    out = []
    for i, t in enumerate(teams):
        row = {"tid": t.tid, "name": schools.team_name(t.tid, t.name), "engine_name": t.name, "abbr": d.tabbr(t.tid), "conference": schools.conference_of(t.tid, d.real_conf[t.tid]), "tier": t.tier,
               "off": int(round(50 + 10 * zo[i])), "def": int(round(50 + 10 * zd[i])), "overall": int(round(50 + 10 * (zo[i] + zd[i]) / np.sqrt(2)))}
        sch = schools.school(t.tid) if schools.available() else None
        if sch is not None:
            row.update(school=sch["school"], institution=sch["institution"], location=sch["location"], city=sch["city"], state=sch["state"])
            card = schools.report_card(t.tid, omaha.get(t.tid))
            row["grades"] = {k: v["grade"] for k, v in card["grades"].items()} if card else None
        out.append(row)
    return out


# ---- routes -----------------------------------------------------------------------------------------
@router.get("/api/saves")
def saves():
    out = []
    if SAVE_DIR.exists():
        for p in SAVE_DIR.glob("dyn_*.json"):
            try:
                m = json.loads(p.read_text())
            except Exception:
                continue
            if m.get("tid") is not None and schools.available():            # saves written before the real names show them too
                old_team, school = m.get("team") or "", schools.team_name(m["tid"], m.get("team") or "")
                if old_team and m.get("name") == f"{old_team} dynasty":
                    m["name"] = f"{school} dynasty"
                m["team"] = school
            out.append(m)
    out.sort(key=lambda m: -m.get("saved", 0))
    return {"dynasties": out, "latest": out[0] if out else None}


@router.get("/api/schools")
def schools_route():
    """Every sim team's real school identity and report card categories (static data; the Omaha Contender grade
    in a dynasty's picker and hub is regraded from that dynasty's draw)."""
    if not schools.available():
        return {"schools": [], "categories": schools.categories(), "available": False}
    w = _store.ready()
    return {"schools": [schools.school(t) for t in range(len(w.league.teams)) if schools.school(t)],
            "categories": schools.categories(), "available": True,
            "conference_check": schools.conference_check(w.league, {tid: c for tid, (_, c, _) in enumerate(w.cfg.teams)}),
            "abbreviation_guesses": schools.abbreviation_guesses()}


@router.get("/api/identity")
def identity_table():
    """Every school's display colors (primary, secondary, alt; chip/text/border/ink after the contrast rules) and
    home ballpark, for the screens' chips, stripes, header bands and venue lines. Display only (app/identity.py)."""
    return {"available": identity.available(), "schools": identity.all_json(), "background": "#" + identity.BACKGROUND,
            "omaha": identity.OMAHA, "d_rows": [{"tid": int(r["tid"]), "school": r["school"], "note": r["note"]} for r in identity.d_rows()]}


@router.post("/api/dynasties")
def new_dynasty(body: NewDynasty):
    w = _store.ready()
    seed = body.seed if body.seed is not None else secrets.randbelow(2 ** 31)
    with _store.lock:
        d = dyn_mod.Dynasty(w.cfg, seed, body.name)
        did = _put(d)
    return {"id": did, "seed": seed, "teams": _strength(d), "categories": schools.categories()}


@router.post("/api/dynasties/{did}/start")
def start(did: str, body: Start):
    d = _get(did)
    try:
        with _store.lock:
            d.start(body.tid)
    except (ValueError, IndexError) as e:
        raise HTTPException(400, str(e))
    if not d.name:
        d.name = f"{d.tname(d.tid)} dynasty"
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
    job = {"running": True, "kind": "sim", "played": len(d.reg_games) + len(d.post_calls), "total": int((~d.skip).sum()), "stage": d.stage,
           "date": d.date_now(), "error": None, "started": time.time()}
    _store.jobs[did] = job

    def progress(dd):
        job["played"] = len(dd.reg_games) + len(dd.post_calls); job["stage"] = dd.stage; job["date"] = dd.date_now()

    def run():
        try:
            with _store.lock:
                if d.runner is not None and d.runner.over:
                    d.finish_game()
                d.advance(body.target, body.pause_mine, progress, body.stops)
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
    out = {"running": j.get("running", False), "kind": j.get("kind", "sim"), "played": j.get("played"), "total": j.get("total"), "stage": j.get("stage"),
           "date": j.get("date"), "error": j.get("error"), "ahead": j.get("ahead"), "ahead_total": j.get("ahead_total")}
    if not out["running"]:
        out["hub"] = _hub(did, d)
    return out


def _start_background(did: str, d: dyn_mod.Dynasty) -> None:
    """While the user plays the pending game, sim the rest of the week's other games (dynasty.background_plan),
    taking the engine lock one game at a time so the user's pitches interleave; autosave when done."""
    plan = d.background_plan()
    if not plan or _running(did):
        return
    job = {"running": True, "kind": "background", "played": len(d.reg_games), "total": int((~d.skip).sum()), "stage": d.stage,
           "date": d.date_now(), "error": None, "started": time.time(), "ahead": 0, "ahead_total": len(plan)}
    _store.jobs[did] = job

    def run():
        try:
            for i in plan:
                if job.get("cancel"):
                    break
                with _store.lock:
                    if i in d.results:
                        continue
                    d._play(i)
                job["ahead"] += 1; job["played"] = len(d.reg_games); job["date"] = int(d.schedule[i].date)
            with _store.lock:
                _autosave(did, d)
        except Exception as e:
            job["error"] = str(e)
        finally:
            job["running"] = False
            job["finished"] = time.time()
    threading.Thread(target=run, daemon=True).start()


@router.post("/api/dynasties/{did}/game/open")
def open_game(did: str, body: OpenIn | None = None):
    from app.api import _turn
    d = _get(did)
    j = _store.jobs.get(did)
    if j and j["running"] and j.get("kind") != "background":
        raise HTTPException(409, "a sim is running")
    try:
        with _store.lock:
            r = d.open_game(body.modes if body else None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    gid = next((g for g, rr in _store.games.items() if rr is r), None) or _store.put(r)
    t = _turn(gid, r, full=True)
    t["dynasty"] = did
    if d.pending:
        p = d.pending
        t["venue"] = game_venue(d, p["stage"], p["home"], p["away"], bool(p["neutral"]))
    _start_background(did, d)
    return t


@router.post("/api/dynasties/{did}/game/sim")
def sim_game(did: str):
    d = _get(did)
    j = _store.jobs.get(did)
    if j and j["running"] and j.get("kind") != "background":
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
    return _read(lambda: {"games": dyn_mod.schedule_json(d), "tid": d.tid})


@router.get("/api/dynasties/{did}/games/{i}")
def game_box(did: str, i: int):
    d = _get(did)
    rec = dyn_mod.find_game(d, i, None)
    if rec is None:
        raise HTTPException(404, "no such game")
    return _read(lambda: dyn_mod.game_json(d, rec, full=True))


@router.get("/api/dynasties/{did}/postgames/{k}")
def post_box(did: str, k: int):
    d = _get(did)
    rec = dyn_mod.find_game(d, None, k)
    if rec is None:
        raise HTTPException(404, "no such game")
    return _read(lambda: dyn_mod.game_json(d, rec, full=True))


@router.get("/api/dynasties/{did}/standings")
def standings(did: str):
    return _read(lambda: dyn_mod.standings_json(_get(did)))


@router.get("/api/dynasties/{did}/stats")
def stats(did: str):
    d = _get(did)
    return _read(lambda: {"team": dyn_mod.team_stats_json(d), "leaders": dyn_mod.leaders_json(d)})


@router.get("/api/dynasties/{did}/teams/{tid}/stats")
def team_stats(did: str, tid: int):
    d = _get(did)
    if not 0 <= tid < len(d.league.teams):
        raise HTTPException(404, "unknown team")
    return _read(lambda: dyn_mod.team_stats_json(d, tid))


@router.get("/api/dynasties/{did}/roster")
def roster(did: str):
    return _read(lambda: dyn_mod.roster_json(_get(did)))


@router.get("/api/dynasties/{did}/teams/{tid}")
def team_page(did: str, tid: int):
    d = _get(did)
    out = _read(lambda: dyn_mod.team_page_json(d, tid))
    if out is None:
        raise HTTPException(404, "unknown team")
    return out


@router.get("/api/dynasties/{did}/players/{pid}")
def player_page(did: str, pid: int):
    d = _get(did)
    out = _read(lambda: dyn_mod.player_page_json(d, pid))
    if out is None:
        raise HTTPException(404, "unknown player")
    return out


@router.get("/api/dynasties/{did}/postseason")
def postseason(did: str):
    return _read(lambda: dyn_mod.postseason_json(_get(did)))


@router.get("/api/dynasties/{did}/summary")
def summary(did: str):
    return _read(lambda: dyn_mod.summary_json(_get(did)))


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
    return {"ok": True}
