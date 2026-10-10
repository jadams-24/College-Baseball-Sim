/* Loading feedback (owner play-test feedback 2026-10-10), the design system's one place for it:
   - request(): every fetch counts as in flight; a thin accent progress bar runs across the top of the page for
     anything over 200 ms; when the server gives no answer within 4 s after a quiet spell it is probably waking
     (the free host naps), so a "Waking up the server" panel shows and the request is retried until it answers;
   - act(): a clicked button (or the button a key maps to) responds within the frame: pressed state, a small spinner,
     a label that says what is happening ("Simming…"), disabled until the request finishes;
   - simLock(): while any sim or advance request is in flight every other sim or advance control is disabled, so a
     second click or key press never queues a second sim (the server refuses one too: 409);
   - start(): a loading panel over a dimmed page for anything over 2 s (sims, dynasty start and load) with what is
     running, real progress when the job reports it (games done of total, the current date), the elapsed time, and
     "Stop at next pause" when the job can stop cleanly; never fake progress: no measurable progress means a working
     indicator and the elapsed time; an error replaces the panel with a short message and Retry;
   - skeleton(): gray placeholder rows at the real row height while a table or card loads;
   - errorPanel(): a request that fails or times out ends in a short message and a Retry button, never a spinner. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const L = { inflight: 0, barTimer: null, lastResponse: 0, waking: null, wakeCancel: null, modal: null, retries: {}, retryId: 0, simLock: false };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const SHOW_BAR_MS = 200, SHOW_PANEL_MS = 2000, WAKE_MS = 4000, QUIET_MS = 45000, RETRY_MS = 3000;

  // ---- the top progress bar ----
  function bar() {
    let el = $("#topprog");
    if (!el) { el = document.createElement("div"); el.id = "topprog"; el.className = "topprog hidden"; el.setAttribute("aria-hidden", "true"); el.innerHTML = "<i></i>"; document.body.appendChild(el); }
    return el;
  }
  function begin() {
    L.inflight += 1;
    if (!L.barTimer) L.barTimer = setTimeout(() => { L.barTimer = null; if (L.inflight > 0) bar().classList.remove("hidden"); }, SHOW_BAR_MS);
  }
  function end() {
    L.inflight = Math.max(0, L.inflight - 1);
    if (L.inflight === 0) { clearTimeout(L.barTimer); L.barTimer = null; bar().classList.add("hidden"); }
  }

  // ---- waking up the server ----
  function waking(on) {
    if (on && !L.waking) {
      L.waking = panel({ title: "Waking up the server", sub: "This can take up to a minute on the free plan.", kind: "wake", cancel: true, immediate: true });
    } else if (!on && L.waking) { L.waking.done(); L.waking = null; }
  }
  async function serverUp() {
    try { const r = await fetch("/api/ping", { cache: "no-store" }); return r.ok; } catch (e) { return false; }
  }

  // ---- request: fetch with the bar, wake detection and the retry-until-it-answers ----
  async function request(path, opts) {
    begin();
    const quiet = !L.lastResponse || Date.now() - L.lastResponse > QUIET_MS;
    const wakeTimer = setTimeout(() => { if (quiet) waking(true); }, WAKE_MS);
    try {
      for (let attempt = 0; ; attempt++) {
        if (L.wakeCancel) { L.wakeCancel = null; throw new Error("Cancelled while the server was waking."); }
        try {
          const r = await fetch(path, opts);
          L.lastResponse = Date.now();
          waking(false);
          return r;
        } catch (e) {                                   // a network error: the server is asleep, down, or unreachable
          if (await serverUp()) {                       // the server is up: the request itself failed (a GET is retried once)
            L.lastResponse = Date.now();
            if (attempt === 0 && (!opts || !opts.method || opts.method === "GET")) continue;
            throw new Error("The server didn't answer this request. Check the connection and retry.");
          }
          waking(true);
          await sleep(RETRY_MS);
        }
      }
    } finally { clearTimeout(wakeTimer); end(); }
  }

  // ---- the loading panel (a centered modal over a dimmed page) ----
  function panel(o) {
    const h = { o, el: null, shown: false, startedAt: Date.now(), timer: null, tick: null, progress: null, failed: false, done() {}, update() {}, fail() {} };
    const render = () => {
      if (!h.el) {
        h.el = document.createElement("div"); h.el.className = "loading-shade"; h.el.setAttribute("role", "status");
        document.body.appendChild(h.el);
      }
      const el = Math.round((Date.now() - h.startedAt) / 1000);
      const elapsed = el >= 60 ? `${Math.floor(el / 60)}m ${String(el % 60).padStart(2, "0")}s` : `${el}s`;
      const p = h.progress;
      let prog = "";
      if (h.failed) prog = "";
      else if (p && p.total) prog = `<div class="prog"><i style="width:${(100 * p.done / p.total).toFixed(1)}%"></i></div><div class="muted">${p.text ? esc(p.text) : `${p.done} of ${p.total}`}</div>`;
      else prog = `<div class="working"><i class="spin"></i><span class="muted">${p && p.text ? esc(p.text) : "Working"}</span></div>`;
      const stop = o.stop && !h.failed ? `<button class="btn-ghost" data-ld-stop ${h.stopping ? "disabled" : ""}>${h.stopping ? "Stopping…" : "Stop at next pause"}</button>` : "";
      const cancel = o.cancel && !h.failed ? `<button class="btn-ghost" data-ld-cancel>Cancel</button>` : "";
      const fail = h.failed ? `<div class="err"><b>${esc(h.failMsg || "Something went wrong.")}</b></div><div class="row">${h.retry ? `<button class="go" data-ld-retry>Retry</button>` : ""}<button class="btn-ghost" data-ld-close>Close</button></div>` : "";
      h.el.innerHTML = `<div class="loading-modal panel ${h.failed ? "failed" : ""}"><div class="hdr">${esc(h.failed ? "Couldn't finish" : o.title)}<span class="sub mono">${elapsed}</span></div><div class="body">${o.sub ? `<div class="muted">${esc(o.sub)}</div>` : ""}${prog}${fail}${stop || cancel ? `<div class="row">${stop}${cancel}</div>` : ""}</div></div>`;
      const s = h.el.querySelector("[data-ld-stop]"); if (s) s.addEventListener("click", () => { h.stopping = true; render(); Promise.resolve(o.stop()).catch(() => {}); });
      const c = h.el.querySelector("[data-ld-cancel]"); if (c) c.addEventListener("click", () => { L.wakeCancel = true; h.done(); });
      const r = h.el.querySelector("[data-ld-retry]"); if (r) r.addEventListener("click", () => { const fn = h.retry; h.done(); fn(); });
      const x = h.el.querySelector("[data-ld-close]"); if (x) x.addEventListener("click", () => h.done());
    };
    const show = () => { if (h.shown) return; h.shown = true; render(); h.tick = setInterval(render, 1000); };
    if (o.immediate) show(); else h.timer = setTimeout(show, SHOW_PANEL_MS);
    h.update = (p) => { h.progress = p; if (h.shown && !h.failed) render(); };
    h.done = () => { clearTimeout(h.timer); clearInterval(h.tick); if (h.el) h.el.remove(); h.el = null; h.shown = false; };
    h.fail = (msg, retry) => { clearTimeout(h.timer); h.failed = true; h.failMsg = msg; h.retry = retry || null; show(); render(); };
    return h;
  }

  // ---- a button's working state ----
  async function act(btn, label, fn) {
    if (!btn) return fn();
    const prev = { html: btn.innerHTML, disabled: btn.disabled, width: btn.offsetWidth };
    btn.classList.add("working"); btn.disabled = true; btn.setAttribute("aria-busy", "true");
    btn.style.minWidth = prev.width ? prev.width + "px" : "";
    btn.innerHTML = `<i class="spin"></i>${esc(label)}`;
    try { return await fn(); }
    finally {
      if (btn.isConnected) { btn.classList.remove("working"); btn.removeAttribute("aria-busy"); btn.innerHTML = prev.html; btn.disabled = prev.disabled; btn.style.minWidth = ""; }
    }
  }
  // every sim and advance control: disabled while any sim or advance request is in flight
  const SIM_CONTROLS = "[data-sim], [data-simto], #tb-advance, #play-btn, #simgame-btn";
  function simLock(on) {
    L.simLock = !!on;
    document.body.classList.toggle("sim-lock", L.simLock);
    document.querySelectorAll(SIM_CONTROLS).forEach((b) => { if (on) { if (!b.disabled) { b.dataset.lockDisabled = "1"; b.disabled = true; } } else if (b.dataset.lockDisabled) { delete b.dataset.lockDisabled; b.disabled = false; } });
  }
  // a sim or advance action: the lock around the request, the button's working state, the panel for anything long
  async function simAction(btn, label, o, fn) {
    if (L.simLock) return;                        // a second click or key press never queues a second sim
    simLock(true);
    const h = panel(o);
    try { return await act(btn, label, () => fn(h)); }
    catch (e) {
      if (o.retry) { h.fail(e.message || String(e), () => { simAction(btn, label, o, fn); }); }
      else h.fail(e.message || String(e), null);
      throw e;
    } finally { simLock(false); if (!h.failed) h.done(); }
  }

  // ---- skeletons and error panels ----
  function skeleton(rows, cols) {
    rows = rows || 8; cols = cols || 4;
    const widths = [34, 12, 12, 10, 14, 10];
    return `<div class="skel" aria-hidden="true">${Array.from({ length: rows }, () => `<div class="skel-row">${Array.from({ length: cols }, (_, c) => `<i style="width:${widths[c % widths.length]}%"></i>`).join("")}</div>`).join("")}</div>`;
  }
  function skeletonPanel(title, rows, cols) { return `<div class="panel"><div class="hdr">${esc(title || "")}</div><div class="body tight">${skeleton(rows, cols)}</div></div>`; }
  function errorPanel(msg, retry, title) {
    const id = ++L.retryId; L.retries[id] = retry;
    return `<div class="panel err"><div class="hdr">${esc(title || "Couldn't load")}</div><div class="body"><div class="muted">${esc(msg || "The request failed.")}</div><div class="row">${retry ? `<button class="go" data-retry="${id}">Retry</button>` : ""}</div></div></div>`;
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-retry]");
    if (b) { const fn = L.retries[b.dataset.retry]; if (fn) { delete L.retries[b.dataset.retry]; fn(); } }
  });

  window.cbsLoad = { request, panel, act, simLock, simAction, skeleton, skeletonPanel, errorPanel, locked: () => L.simLock, inflight: () => L.inflight, waking: () => !!L.waking,
                     _quiet: () => { L.lastResponse = 0; } };          // tests and screenshots: pretend the server has been idle
})();
