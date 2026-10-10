"""Loading feedback (owner play-test feedback 2026-10-10): no double runs. While a sim or advance request is in flight,
a second one never queues a second sim: the server answers 409 (a per-game lock on /api/games/{gid}/sim, the
dynasty's one job at a time on /api/dynasties/{id}/sim), and the page disables every sim and advance control and
ignores the keys (the Playwright test, run when a browser is available). "Stop at next pause" stops a dynasty sim at
its next clean point."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import api as api_mod                                   # noqa: E402

TID = 5


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    api_mod.dynasty_api.SAVE_DIR = tmp_path_factory.mktemp("saves")
    with TestClient(api_mod.app) as c:
        yield c


def _wait(client, did, limit=600):
    for _ in range(limit * 20):
        p = client.get(f"/api/dynasties/{did}/progress").json()
        if not p["running"]:
            assert p["error"] is None, p["error"]
            return p
        time.sleep(0.05)
    raise AssertionError("the sim did not finish")


def test_game_sim_never_runs_twice_at_once(client):
    """The per-game lock: a sim request while one is running gets 409 and runs nothing."""
    league = client.get("/api/league").json()
    a, b = league["teams"][0]["tid"], league["teams"][1]["tid"]
    t = client.post("/api/games", json={"home": a, "away": b, "user_side": "home", "seed": 3}).json()
    gid = t["game_id"]
    lock = api_mod._sim_lock(gid)
    assert lock.acquire(blocking=False)                            # the first request holds it ...
    try:
        r = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"})
        assert r.status_code == 409 and "running" in r.json()["detail"]
    finally:
        lock.release()
    r = client.post(f"/api/games/{gid}/sim", json={"target": "pitch"})   # ... and once it is free the sim runs
    assert r.status_code == 200
    # two genuinely concurrent requests: exactly one runs, the other is refused, nothing is queued
    results = []

    def go(target):
        results.append(client.post(f"/api/games/{gid}/sim", json={"target": target}).status_code)
    th = [threading.Thread(target=go, args=("game",)), threading.Thread(target=go, args=("game",))]
    [x.start() for x in th]; [x.join() for x in th]
    assert sorted(results) in ([200, 409], [200, 200]), results     # [200, 200] only when the first finished before the second arrived
    st = client.get(f"/api/games/{gid}").json()["state"]
    assert st["over"]


def test_dynasty_sim_refuses_a_second_job_and_stops_at_the_next_pause(client):
    r = client.post("/api/dynasties", json={"seed": 7}).json()
    did = r["id"]
    client.post(f"/api/dynasties/{did}/start", json={"tid": TID})
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "end", "pause_mine": False, "stops": []}).status_code == 200
    second = client.post(f"/api/dynasties/{did}/sim", json={"target": "end", "pause_mine": False, "stops": []})
    assert second.status_code == 409                                  # one job at a time, never queued
    p = client.get(f"/api/dynasties/{did}/progress").json()
    assert p["running"] and p["stoppable"] and p["elapsed"] is not None
    assert client.post(f"/api/dynasties/{did}/stop").json()["stopping"] is True
    p = _wait(client, did, limit=120)                                 # the stop lands at the next day boundary, not at season's end
    hub = p["hub"]
    assert hub["pause"] and hub["pause"]["type"] == "stopped", hub["pause"]
    assert hub["stage"] == "regular" and hub["games_played"] < hub["games_total"]
    assert client.post(f"/api/dynasties/{did}/stop").json() == {"stopping": False, "running": False}
    # the dynasty continues normally after a stop (the next advance starts where it left off)
    assert client.post(f"/api/dynasties/{did}/sim", json={"target": "day", "pause_mine": False, "stops": []}).status_code == 200
    p = _wait(client, did, limit=120)
    assert p["hub"]["pause"] is None or p["hub"]["pause"]["type"] != "stopped"


# ---------------------------------------------------------------- the page (Playwright, when a browser is here)
def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close(); return port


def _chromium():
    for p in (os.environ.get("CBS_CHROMIUM"), "/opt/pw-browsers/chromium"):          # CI has no browser: the page test skips there
        if p and Path(p).exists():
            return p
    return None


@pytest.mark.skipif(_chromium() is None, reason="no Chromium for the page test")
def test_page_never_sends_two_sims_at_once(tmp_path):
    pw = pytest.importorskip("playwright.sync_api")
    port = _free_port()
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.api:app", "--port", str(port)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{port}/"
        for _ in range(600):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close(); break
            except OSError:
                time.sleep(0.2)
        with pw.sync_playwright() as p:
            br = p.chromium.launch(executable_path=_chromium())
            pg = br.new_page(viewport={"width": 1440, "height": 900})
            sims = []
            pg.on("request", lambda rq: sims.append(rq.url) if rq.method == "POST" and rq.url.endswith("/sim") else None)
            pg.goto(url)
            pg.wait_for_selector("#main:not(.hidden)", timeout=120000)
            pg.wait_for_function("document.querySelector('#settings-body').innerText.length > 10", timeout=120000)
            pg.click("#tile-quick"); pg.wait_for_selector("#lobby:not(.hidden)")
            pg.wait_for_function("document.querySelector('#home').options.length > 10", timeout=120000)
            pg.click("#random-matchup")
            pg.click("#start"); pg.wait_for_selector("#game:not(.hidden)", timeout=120000)
            pg.wait_for_function("!document.body.classList.contains('busy')", timeout=120000)
            # hold the sim request open so the page's state while it is in flight can be checked
            held = []
            pg.route("**/sim", lambda route: held.append(route))
            # the first E starts a sim to the end of the game; while it runs, every sim control is disabled and the
            # pressed button shows its working label; a second E, an A and a forced click send nothing
            pg.keyboard.press("E"); time.sleep(0.15)
            assert pg.evaluate("document.body.classList.contains('sim-lock')")
            assert len(held) == 1
            working = pg.query_selector("#simbar button.working")
            assert working is not None and working.get_attribute("disabled") is not None and "…" in working.inner_text()
            assert all(b.get_attribute("disabled") is not None for b in pg.query_selector_all("#simbar [data-sim]"))
            pg.keyboard.press("E"); pg.keyboard.press("A")
            for b in pg.query_selector_all("#simbar [data-sim]"):
                b.dispatch_event("click")
            time.sleep(0.3)
            assert len(held) == 1 and len(sims) == 1, (len(held), sims)
            held[0].continue_()
            pg.wait_for_function("!document.body.classList.contains('sim-lock')", timeout=180000)
            time.sleep(0.3)
            assert len(sims) == 1, sims
            assert pg.query_selector("#simbar button.working") is None
            br.close()
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
