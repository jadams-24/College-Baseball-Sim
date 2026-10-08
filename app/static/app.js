/* College Baseball Sim — game prototype frontend (2026-10-08).
   Vanilla JS, no build step. The page never computes an outcome: it shows the turn the API returns and sends
   orders, answers and sim targets. The latest save of the game is mirrored to localStorage after every turn;
   when the server has forgotten the game (a restart, the free host's nap) the page reloads it from that save. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const LS_LATEST = "cbs.latest", LS_SAVES = "cbs.saves";
  const RATING_LABEL = { contact: "Con", gap: "Gap", power: "Pow", eye: "Eye", avoid_k: "AvK", speed: "Spd", glove: "Glv", arm: "Arm",
                         stuff: "Stf", control: "Ctl", movement: "Mov", stamina: "Sta" };
  const SIM_LABEL = { pitch: "pitch", pa: "at-bat", half: "half inning", inning: "inning", three_innings: "three innings", game: "end of game" };

  const S = { league: null, decisions: null, rosters: {}, game: null, events: [], pregame: null, busy: false, screen: "picker" };

  // ---- storage ---------------------------------------------------------------------------------
  const ls = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: fine */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* fine */ } },
  };

  // ---- API ---------------------------------------------------------------------------------------
  async function raw(path, method = "GET", body) {
    const r = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    if (!r.ok) {
      let msg = r.statusText;
      try { msg = (await r.json()).detail || msg; } catch (e) { /* keep */ }
      const err = new Error(msg); err.status = r.status; throw err;
    }
    return r.json();
  }
  async function gameCall(path, method, body) {
    // a game endpoint; on 404 the server forgot the game: reload the latest save and retry once
    try { return await raw(`/api/games/${S.game.id}${path}`, method, body); }
    catch (e) {
      if (e.status !== 404 || !S.game.save) throw e;
      toast("The server had forgotten the game; resuming from your save.");
      const t = await raw("/api/games/load", "POST", { save: S.game.save });
      S.game.id = t.game_id; S.events = t.events; applyTurn(t, true);
      return raw(`/api/games/${S.game.id}${path}`, method, body);
    }
  }
  async function busy(fn) {
    if (S.busy) return;
    S.busy = true; $$(".sim, .actions button, #coach").forEach((b) => (b.disabled = true));
    try { return await fn(); }
    catch (e) { console.error(e); toast(e.message || String(e)); }
    finally {
      S.busy = false;
      $$(".sim, .actions button, #coach").forEach((b) => (b.disabled = false));
      if (S.game && S.screen === "game") { try { renderGame(); } catch (e) { console.error(e); toast("Display error: " + e.message); } }
    }
  }

  // ---- turns --------------------------------------------------------------------------------------
  function applyTurn(t, replaceEvents = false) {
    S.game.turn = t; S.game.meta = t.meta;
    if (replaceEvents) S.events = t.events.slice(); else S.events = S.events.concat(t.events);
    mirrorSave();
  }
  let saveTimer = null;
  function mirrorSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        const sv = await raw(`/api/games/${S.game.id}/save`);
        S.game.save = sv.save;
        ls.set(LS_LATEST, { save: sv.save, meta: sv.meta, phase: sv.phase, title: gameTitle(), time: Date.now() });
      } catch (e) { /* the next turn tries again */ }
    }, 150);
  }
  function gameTitle() {
    const st = S.game && S.game.turn && S.game.turn.state;
    if (!st) return "game";
    return `${st.teams.away.name} at ${st.teams.home.name} — ${st.score.away}-${st.score.home}, ${st.half === "T" ? "top" : "bottom"} ${st.inning}`;
  }

  // ---- screens -------------------------------------------------------------------------------------
  function show(name) {
    S.screen = name;
    $$(".screen").forEach((s) => s.classList.add("hidden"));
    $(`#${name}`).classList.remove("hidden");
    $("#simbar").classList.toggle("hidden", name !== "game");
    $("#topnav").classList.toggle("hidden", !S.game);
    if (name === "box") renderBox();
    if (name === "picker") renderSaves();
    window.scrollTo(0, 0);
  }
  $$("[data-go]").forEach((b) => b.addEventListener("click", () => show(b.dataset.go)));
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 3500);
  }

  // ---- picker ----------------------------------------------------------------------------------------
  function fillTeams(sel, filter) {
    const f = (filter || "").toLowerCase();
    const keep = sel.value;
    sel.innerHTML = "";
    const byConf = {};
    S.league.teams.forEach((t) => { if (!f || `${t.name} ${t.conference} ${t.tier}`.toLowerCase().includes(f)) (byConf[t.conference] = byConf[t.conference] || []).push(t); });
    Object.keys(byConf).sort().forEach((c) => {
      const g = document.createElement("optgroup"); g.label = `${c} (${byConf[c][0].tier})`;
      byConf[c].forEach((t) => { const o = document.createElement("option"); o.value = t.tid; o.textContent = t.name; g.appendChild(o); });
      sel.appendChild(g);
    });
    if (keep) sel.value = keep;
  }
  async function roster(tid) {
    if (!S.rosters[tid]) S.rosters[tid] = await raw(`/api/teams/${tid}`);
    return S.rosters[tid];
  }
  function ratingChips(p) {
    return `<div class="chips">${Object.entries(p.ratings).map(([k, v]) => `<span class="chip ${v >= 70 ? "r80" : v <= 35 ? "r20" : ""}">${RATING_LABEL[k] || k} <b>${v}</b></span>`).join("")}</div>`;
  }
  function rosterTable(r) {
    const bat = r.batters.map((p) => `<tr><td>${p.name}</td><td>${p.pos}</td><td>${p.role}</td>${["contact", "gap", "power", "eye", "avoid_k", "speed", "glove", "arm"].map((k) => `<td>${p.ratings[k]}</td>`).join("")}</tr>`).join("");
    const pit = r.pitchers.map((p) => `<tr><td>${p.name}</td><td>${p.role}</td>${["stuff", "control", "movement", "stamina"].map((k) => `<td>${p.ratings[k]}</td>`).join("")}</tr>`).join("");
    return `<div class="roster"><h3>${r.name} <span class="muted small">${r.conference}, ${r.tier}</span></h3>
      <table><tr><th>Batter</th><th>Pos</th><th>Role</th><th>Con</th><th>Gap</th><th>Pow</th><th>Eye</th><th>AvK</th><th>Spd</th><th>Glv</th><th>Arm</th></tr>${bat}</table>
      <table><tr><th>Pitcher</th><th>Role</th><th>Stf</th><th>Ctl</th><th>Mov</th><th>Sta</th></tr>${pit}</table></div>`;
  }
  async function previewRosters() {
    const h = $("#home").value, a = $("#away").value;
    const out = [];
    for (const tid of [h, a]) if (tid) out.push(rosterTable(await roster(+tid)));
    $("#picker-rosters").innerHTML = out.join("");
  }
  $("#home-search").addEventListener("input", (e) => fillTeams($("#home"), e.target.value));
  $("#away-search").addEventListener("input", (e) => fillTeams($("#away"), e.target.value));
  $("#home").addEventListener("change", previewRosters);
  $("#away").addEventListener("change", previewRosters);
  $("#random-matchup").addEventListener("click", () => {
    const n = S.league.teams.length;
    let h = Math.floor(Math.random() * n), a = Math.floor(Math.random() * n);
    if (a === h) a = (a + 1) % n;
    $("#home-search").value = ""; $("#away-search").value = ""; fillTeams($("#home")); fillTeams($("#away"));
    $("#home").value = h; $("#away").value = a; previewRosters();
  });
  $("#start").addEventListener("click", () => busy(async () => {
    const home = +$("#home").value, away = +$("#away").value;
    if (!$("#home").value || !$("#away").value) return toast("Pick both teams.");
    if (home === away) return toast("Pick two different teams.");
    const side = $('input[name="side"]:checked').value;
    const seed = $("#seed").value ? +$("#seed").value : null;
    const t = await raw("/api/games", "POST", { home, away, user_side: side, seed });
    S.game = { id: t.game_id, turn: t, meta: t.meta, save: null }; S.events = [];
    applyTurn(t, true);
    await openPregame();
  }));

  // ---- pregame ---------------------------------------------------------------------------------------
  async function openPregame() {
    const st = S.game.turn.state;
    const side = S.game.turn.user_side;
    const r = await roster(st.teams[side].tid);
    const coach = await gameCall("/coach");
    const lu = coach.advice.find((a) => a.kind === "lineup");
    const sp = coach.advice.find((a) => a.kind === "starting_pitcher");
    S.pregame = { roster: r, lineup: lu ? lu.pids.slice() : r.batters.slice(0, 9).map((p) => p.pid), aiLineup: lu ? lu.pids.slice() : null,
                  sp: sp ? sp.pid : r.pitchers[0].pid, aiSp: sp ? sp.pid : null };
    $("#pregame-title").textContent = `${st.teams.away.name} at ${st.teams.home.name}. You manage the ${st.teams[side].name} (${side}). Seed ${S.game.meta.seed}.`;
    renderPregame();
    show("pregame");
  }
  function renderPregame() {
    const pg = S.pregame, byPid = {};
    pg.roster.batters.forEach((p) => (byPid[p.pid] = p));
    const bench = pg.roster.batters.filter((p) => !pg.lineup.includes(p.pid));
    $("#lineup-editor").innerHTML = pg.lineup.map((pid, i) => {
      const p = byPid[pid];
      const opts = [p].concat(bench).map((q) => `<option value="${q.pid}" ${q.pid === pid ? "selected" : ""}>${q.name} (${q.pos}) Con ${q.ratings.contact} Pow ${q.ratings.power}</option>`).join("");
      return `<li><select data-slot="${i}">${opts}</select><span class="nm"></span><button data-up="${i}" ${i === 0 ? "disabled" : ""}>▲</button><button data-down="${i}" ${i === 8 ? "disabled" : ""}>▼</button></li>`;
    }).join("");
    $$("#lineup-editor select").forEach((s) => s.addEventListener("change", (e) => { pg.lineup[+e.target.dataset.slot] = +e.target.value; renderPregame(); }));
    $$("#lineup-editor [data-up]").forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.up; [pg.lineup[i - 1], pg.lineup[i]] = [pg.lineup[i], pg.lineup[i - 1]]; renderPregame(); }));
    $$("#lineup-editor [data-down]").forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.down; [pg.lineup[i + 1], pg.lineup[i]] = [pg.lineup[i], pg.lineup[i + 1]]; renderPregame(); }));
    $("#sp-editor").innerHTML = pg.roster.pitchers.map((p) => `<button class="item ${p.pid === pg.sp ? "selected" : ""}" data-sp="${p.pid}"><span>${p.name} <span class="meta">${p.role}${p.pid === pg.aiSp ? " · AI's pick" : ""}</span></span>${ratingChips(p)}</button>`).join("");
    $$("#sp-editor [data-sp]").forEach((b) => b.addEventListener("click", () => { pg.sp = +b.dataset.sp; renderPregame(); }));
  }
  $("#lineup-reset").addEventListener("click", () => { if (S.pregame.aiLineup) { S.pregame.lineup = S.pregame.aiLineup.slice(); S.pregame.sp = S.pregame.aiSp; renderPregame(); } });
  $("#pregame-play").addEventListener("click", () => busy(async () => {
    const pg = S.pregame;
    const sameLineup = pg.aiLineup && pg.aiLineup.join() === pg.lineup.join();
    if (!sameLineup) applyTurn(await gameCall("/orders", "POST", { kind: "lineup", value: pg.lineup }));
    if (pg.sp !== pg.aiSp) applyTurn(await gameCall("/orders", "POST", { kind: "starting_pitcher", value: pg.sp }));
    await startGame();
  }));
  $("#pregame-ai").addEventListener("click", () => busy(startGame));
  async function startGame() {
    applyTurn(await gameCall("/sim", "POST", { target: "pitch" }));
    show("game"); renderGame();
  }

  // ---- the game screen ---------------------------------------------------------------------------------
  function renderGame() {
    const t = S.game.turn, st = t.state, me = t.user_side;
    // line score
    const innings = st.line_score.innings;
    const row = (side) => `<tr class="${st.batting_side === side && !st.over ? "batting" : ""}"><td class="team">${st.teams[side].name}</td>${st.line_score[side].map((r) => `<td>${r === null ? "" : r}</td>`).join("")}<td class="tot">${st.score[side]}</td><td>${st.hits[side]}</td><td>${st.errors[side]}</td></tr>`;
    $("#linescore").innerHTML = `<tr><th></th>${innings.map((i) => `<th>${i}</th>`).join("")}<th class="tot">R</th><th>H</th><th>E</th></tr>${row("away")}${row("home")}`;
    // situation
    const outs = `<span class="outs">${[0, 1, 2].map((i) => `<i class="${i < st.outs ? "on" : ""}"></i>`).join("")}</span>`;
    let text;
    if (st.over) text = `<b>Final</b>${st.ended_by_run_rule ? " (run rule)" : ""}`;
    else if (t.phase === "pregame") text = "<b>Pregame</b>";
    else text = `<b>${st.half === "T" ? "Top" : "Bot"} ${st.inning}</b> ${outs} ${st.count ? `count <b>${st.count[0]}-${st.count[1]}</b>` : `<span class="muted">between at-bats</span>`}`;
    const names = ["1B", "2B", "3B"].map((b, i) => (st.bases[i] ? st.bases[i].name : ""));
    const on = st.bases.map((b) => (b ? "on" : ""));
    $("#situation").innerHTML = `<div class="sit-text">${text}<div class="muted small">${st.bases.some((b) => b) ? "On base: " + st.bases.map((b, i) => (b ? `${b.name} (${i + 1})` : null)).filter(Boolean).join(", ") : "Bases empty"}${st.due_up.length ? " · Due up: " + st.due_up.join(", ") : ""}</div></div>
      <svg class="diamond" viewBox="0 0 120 100" aria-label="diamond">
        <rect class="field" x="0" y="0" width="120" height="100" rx="8"/>
        <polygon class="path" points="60,92 18,56 60,20 102,56"/>
        <rect class="base ${on[0]}" x="94" y="48" width="12" height="12" transform="rotate(45 100 54)"/>
        <rect class="base ${on[1]}" x="54" y="14" width="12" height="12" transform="rotate(45 60 20)"/>
        <rect class="base ${on[2]}" x="14" y="48" width="12" height="12" transform="rotate(45 20 54)"/>
        <polygon class="base" points="54,86 66,86 66,92 60,97 54,92"/>
        <text x="100" y="74" text-anchor="middle">${names[0]}</text>
        <text x="60" y="10" text-anchor="middle">${names[1]}</text>
        <text x="20" y="74" text-anchor="middle">${names[2]}</text>
      </svg>`;
    // cards
    const b = st.batter, p = st.pitcher;
    const mine = (side) => (side === me ? " (you)" : "");
    $("#batter-card").innerHTML = b ? `<div class="sub">${st.count ? "At bat" : "Due up"} · ${st.teams[st.batting_side].name}${mine(st.batting_side)}</div><div class="name">${b.name} <span class="sub">${b.pos}, bats ${(st.lineups[st.batting_side].findIndex((x) => x.pid === b.pid) + 1) || "?"}th</span></div>${ratingChips(b)}<div class="line">Today: ${b.line_text || "0-0"}</div>` : "<div class='muted'>No batter yet</div>";
    const fld = st.batting_side === "home" ? "away" : "home";
    $("#pitcher-card").innerHTML = p ? `<div class="sub">Pitching · ${st.teams[fld].name}${mine(fld)}</div><div class="name">${p.name} <span class="sub">${p.role}</span></div>${ratingChips(p)}<div class="line">Outing: <b>${p.outing ? p.outing.pitches : p.line.pitches}</b> pitches, ${p.line.ip} IP, ${p.line.h} H, ${p.line.bb} BB, ${p.line.k} K, ${p.line.r} R (${p.line.er} ER)</div>` : "<div class='muted'>No pitcher yet</div>";
    // question
    const q = $("#question");
    if (t.phase === "question") { q.classList.remove("hidden"); renderQuestion(t.pending); } else q.classList.add("hidden");
    // actions
    const hint = t.phase === "boundary" ? "before the next pitch" : t.phase === "pitch" ? "orders apply at your team's next decision" : t.phase === "over" ? "game over" : "";
    $("#decisions-hint").textContent = hint;
    $("#actions").innerHTML = t.actions.filter((a) => a.answer !== "lineup" && a.kind !== "starting_pitcher" && a.kind !== "relief_pitcher").map((a) =>
      `<button data-action="${a.kind}" class="${a.queued ? "queued" : ""} ${a.mode === "ask" ? "ask" : ""}" ${a.legal && !st.over && t.phase !== "question" ? "" : "disabled"} title="${a.legal ? "" : a.reason}">${a.label}${a.mode === "ask" ? " ?" : ""}</button>`).join("");
    $$("#actions [data-action]").forEach((btn) => btn.addEventListener("click", () => openSheet(t.actions.find((a) => a.kind === btn.dataset.action))));
    $("#orders").innerHTML = t.orders.map((o) => `<span class="order">${labelOf(o.kind)}: ${describeValue(o.kind, o.value)} <button data-clear="${o.kind}" title="cancel">×</button></span>`).join("");
    $$("#orders [data-clear]").forEach((btn) => btn.addEventListener("click", () => busy(async () => applyTurn(await gameCall("/orders", "POST", { kind: btn.dataset.clear, value: null })))));
    // sim buttons
    $$(".sim").forEach((btn) => (btn.disabled = S.busy || st.over || t.phase === "question"));
    $("#status").textContent = st.over ? "Game over — see the box score." : "";
    renderFeed();
    renderSettings();
  }
  function labelOf(kind) { const d = S.decisions.kinds.find((k) => k.kind === kind); return d ? d.label : kind; }
  function playerName(pid) {
    const st = S.game.turn.state;
    for (const side of ["away", "home"]) for (const grp of ["lineups", "bench", "bullpen", "used_pitchers"]) { const p = (st[grp][side] || []).find((x) => x.pid === pid); if (p) return p.name; }
    return `#${pid}`;
  }
  function describeValue(kind, v) {
    if (v === "auto") return "AI decides";
    if (v === null) return "no one";
    if (typeof v === "number") return playerName(v);
    if (Array.isArray(v)) return v.map((x) => (Array.isArray(x) ? `${playerName(x[1])} → slot ${x[0] + 1}` : playerName(x))).join(", ");
    if (typeof v === "object") return v.yes ? `yes, ${playerName(v.reliever)}` : "no";
    return String(v).replace("_", " ");
  }

  // ---- feed --------------------------------------------------------------------------------------------
  function renderFeed() {
    const f = $("#feed");
    const rows = S.events.slice(-400).reverse().map((e) => `<div class="e ${e.type} ${e.source || ""}">${esc(e.text)}</div>`);
    f.innerHTML = rows.join("") || "<div class='muted'>The game has not started.</div>";
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  // ---- decision sheets ---------------------------------------------------------------------------------
  function cardItem(p, selected, meta) {
    return `<button class="item ${selected ? "selected" : ""}" data-pick="${p.pid}"><span>${p.name} <span class="meta">${meta || p.pos || p.role}${p.line_text ? " · today " + p.line_text : ""}</span></span>${ratingChips(p)}</button>`;
  }
  function openSheet(a, question = false) {
    const st = S.game.turn.state, me = S.game.turn.user_side, d = S.decisions.kinds.find((k) => k.kind === a.kind);
    const sheet = $("#sheet");
    const send = question ? (value) => busy(async () => { applyTurn(await gameCall("/decide", "POST", { kind: a.kind, value })); closeSheet(); })
                          : (value) => busy(async () => { applyTurn(await gameCall("/orders", "POST", { kind: a.kind, value })); closeSheet(); });
    let body = "";
    const pick = (pool, allowNone, meta) => `<div class="list">${allowNone ? `<button class="item" data-pick="none"><span>No one</span></button>` : ""}${pool.map((p) => cardItem(p, false, meta && meta(p))).join("")}</div>`;
    if (a.answer === "choice3" || a.answer === "generic") {
      body = `<div class="row wrap"><button class="primary" data-choice="yes">Yes</button><button data-choice="no">No</button><button data-choice="league_rate">Let them play (league rate)</button></div>`;
    } else if (a.answer === "pick_batter") {
      const bench = st.bench[me].filter((p) => a.options.includes(p.pid));
      body = pick(bench, true);
    } else if (a.answer === "pitching_change") {
      const pen = st.bullpen[me].filter((p) => a.options.includes(p.pid));
      body = `<div class="help">Pick the reliever who comes in after this plate appearance (at an inning's end, when you next take the field).</div>${pick(pen, false, (p) => p.role)}<div class="row wrap"><button data-choice="no">No change</button></div>`;
    } else if (a.answer === "subs") {
      const bench = st.bench[me], lineup = st.lineups[me];
      body = `<div class="help">Bench player in, lineup slot out. Takes effect when your side next takes the field.</div>
        <div class="row wrap"><select id="sub-player">${bench.map((p) => `<option value="${p.pid}">${p.name} (${p.pos}) Glv ${p.ratings.glove}</option>`).join("")}</select>
        <select id="sub-slot">${lineup.map((p, i) => `<option value="${i}">${i + 1}. ${p.name} (${p.pos})</option>`).join("")}</select>
        <button class="primary" data-sub="1">Queue</button></div>`;
    } else if (a.answer === "pick_pitcher") {
      body = pick(st.bullpen[me].filter((p) => a.options.includes(p.pid)), false, (p) => p.role);
    } else {
      body = `<div class="muted">Set before the game.</div>`;
    }
    sheet.innerHTML = `<div class="row between"><h2>${d.label}${question ? " — the engine is asking you" : ""}</h2><button class="small secondary" data-close="1">Close</button></div><div class="help">${esc(d.effect)}</div>${body}${question ? `<div class="row wrap" style="margin-top:8px"><button data-auto="1" class="secondary small">Let the AI decide this one</button></div>` : ""}`;
    sheet.classList.remove("hidden");
    sheet.scrollIntoView({ behavior: "smooth", block: "nearest" });
    $$("#sheet [data-choice]").forEach((b) => b.addEventListener("click", () => send(b.dataset.choice)));
    $$("#sheet [data-pick]").forEach((b) => b.addEventListener("click", () => {
      const v = b.dataset.pick === "none" ? null : +b.dataset.pick;
      send(a.answer === "pitching_change" ? { yes: true, reliever: v } : v);
    }));
    const sub = $("#sheet [data-sub]");
    if (sub) sub.addEventListener("click", () => send([[+$("#sub-slot").value, +$("#sub-player").value]]));
    const auto = $("#sheet [data-auto]");
    if (auto) auto.addEventListener("click", () => send("auto"));
    $("#sheet [data-close]").addEventListener("click", closeSheet);
  }
  function closeSheet() { $("#sheet").classList.add("hidden"); $("#sheet").innerHTML = ""; }
  function renderQuestion(p) {
    const q = $("#question");
    q.innerHTML = `<h2>Your call: ${p.label}</h2><div class="help">The engine is waiting for this decision (you asked to be asked). ${p.legal ? "" : p.reason}</div><div class="row wrap"><button class="primary" id="q-open">Decide</button><button class="secondary" id="q-auto">Let the AI decide</button></div>`;
    $("#q-open").addEventListener("click", () => openSheet(Object.assign({}, S.game.turn.actions.find((a) => a.kind === p.kind), { options: p.options, legal: p.legal }), true));
    $("#q-auto").addEventListener("click", () => busy(async () => { applyTurn(await gameCall("/decide", "POST", { kind: p.kind, value: "auto" })); closeSheet(); }));
  }

  // ---- settings and coach ----------------------------------------------------------------------------------
  function renderSettings() {
    const t = S.game.turn;
    const panel = $("#settings-panel");
    panel.innerHTML = `<div class="help" style="grid-column:1/-1">Autopilot answers every decision you have not queued. Switch a decision to "ask me" to be stopped and asked each time.</div>` +
      S.decisions.kinds.filter((k) => k.when !== "pregame").map((k) => `<label><span>${k.label}</span><select data-mode="${k.kind}"><option value="auto" ${t.modes[k.kind] === "auto" ? "selected" : ""}>autopilot</option><option value="ask" ${t.modes[k.kind] === "ask" ? "selected" : ""}>ask me</option></select></label>`).join("");
    $$("#settings-panel [data-mode]").forEach((s) => s.addEventListener("change", () => busy(async () => applyTurn(await gameCall("/modes", "POST", { kind: s.dataset.mode, mode: s.value })))));
  }
  $("#settings").addEventListener("click", () => $("#settings-panel").classList.toggle("hidden"));
  $("#coach").addEventListener("click", () => busy(async () => {
    const out = $("#coach-out");
    const c = await gameCall("/coach");
    const lines = c.advice.filter((a) => !a.pids && !a.pid).map((a) => `<div>${a.label}: ${esc(a.text)}</div>`);
    out.innerHTML = `<b>Bench coach</b> (what the AI would do for your team next): ${lines.length ? lines.join("") : "<div>nothing to decide before the next pitch</div>"}`;
    out.classList.remove("hidden");
  }));

  // ---- sim -------------------------------------------------------------------------------------------------
  $$(".sim").forEach((b) => b.addEventListener("click", () => busy(async () => {
    $("#coach-out").classList.add("hidden");
    applyTurn(await gameCall("/sim", "POST", { target: b.dataset.sim }));
  })));
  document.addEventListener("keydown", (e) => {
    if (S.screen !== "game" || e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    const map = { " ": "pitch", n: "pitch", a: "pa", h: "half", i: "inning" };
    if (map[e.key]) { e.preventDefault(); const btn = $(`.sim[data-sim="${map[e.key]}"]`); if (btn && !btn.disabled) btn.click(); }
  });

  // ---- saves ------------------------------------------------------------------------------------------------
  $("#save").addEventListener("click", () => busy(async () => {
    const sv = await gameCall("/save");
    const saves = ls.get(LS_SAVES, []);
    const name = prompt("Name this save", gameTitle()) || gameTitle();
    saves.unshift({ name, time: Date.now(), save: sv.save, meta: sv.meta });
    ls.set(LS_SAVES, saves.slice(0, 20));
    toast("Saved in this browser.");
  }));
  $("#download").addEventListener("click", () => busy(async () => {
    const sv = await gameCall("/save");
    const blob = new Blob([sv.save], { type: "application/octet-stream" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `${gameTitle().replace(/[^\w-]+/g, "_")}.cbs`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }));
  async function loadSave(save) {
    const t = await raw("/api/games/load", "POST", { save });
    S.game = { id: t.game_id, turn: t, meta: t.meta, save }; S.events = [];
    applyTurn(t, true);
    if (t.phase === "pregame") await openPregame(); else { show("game"); renderGame(); }
  }
  function renderSaves() {
    const latest = ls.get(LS_LATEST, null), saves = ls.get(LS_SAVES, []);
    const rows = [];
    if (latest) rows.push(`<div class="save"><span>Latest: ${esc(latest.title || "game")} <span class="muted small">${new Date(latest.time).toLocaleString()}</span></span><span class="row"><button class="small" data-load="latest">Resume</button></span></div>`);
    saves.forEach((s, i) => rows.push(`<div class="save"><span>${esc(s.name)} <span class="muted small">${new Date(s.time).toLocaleString()}</span></span><span class="row"><button class="small" data-load="${i}">Load</button><button class="small secondary" data-del="${i}">Delete</button></span></div>`));
    $("#saves").innerHTML = rows.join("") || "<div class='muted small'>No saved games in this browser yet.</div>";
    $$("#saves [data-load]").forEach((b) => b.addEventListener("click", () => busy(async () => loadSave(b.dataset.load === "latest" ? latest.save : saves[+b.dataset.load].save))));
    $$("#saves [data-del]").forEach((b) => b.addEventListener("click", () => { saves.splice(+b.dataset.del, 1); ls.set(LS_SAVES, saves); renderSaves(); }));
  }
  $("#load-file").addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader(); rd.onload = () => busy(async () => loadSave(String(rd.result).trim())); rd.readAsText(f);
  });

  // ---- box score ------------------------------------------------------------------------------------------------
  async function renderBox() {
    const b = await gameCall("/box");
    const batCols = ["ab", "r", "h", "rbi", "bb", "k", "2b", "3b", "hr"], pitCols = ["ip", "h", "r", "er", "bb", "k", "hr", "bf", "pitches"];
    const sum = (rows, k) => rows.reduce((s, r) => s + (r.line[k] || 0), 0);
    const bat = (side) => `<h2>${b.teams[side]} batting</h2><table><tr><th>Batter</th><th>Pos</th>${batCols.map((c) => `<th>${c.toUpperCase()}</th>`).join("")}</tr>${b.batting[side].map((r) => `<tr><td>${r.starter ? "" : "&nbsp;&nbsp;"}${r.name}</td><td>${r.pos}</td>${batCols.map((c) => `<td>${r.line[c]}</td>`).join("")}</tr>`).join("")}<tr class="tot"><td>Totals</td><td></td>${batCols.map((c) => `<td>${sum(b.batting[side], c)}</td>`).join("")}</tr></table>`;
    const pit = (side) => `<h2>${b.teams[side]} pitching</h2><table><tr><th>Pitcher</th>${pitCols.map((c) => `<th>${c === "pitches" ? "P" : c.toUpperCase()}</th>`).join("")}</tr>${b.pitching[side].map((r) => `<tr><td>${r.name} <span class="muted">${r.role}</span></td>${pitCols.map((c) => `<td>${r.line[c]}</td>`).join("")}</tr>`).join("")}</table>`;
    $("#box-title").textContent = `${b.teams.away} ${b.score.away}, ${b.teams.home} ${b.score.home}${b.over ? " (final)" : " (in progress)"}`;
    $("#box-body").innerHTML = `<div class="box grid2"><div>${bat("away")}${pit("away")}</div><div>${bat("home")}${pit("home")}</div></div><h2>Play by play</h2><div class="pbp">${b.feed.map((e) => `<div class="e ${e.type}">${esc(e.text)}</div>`).join("")}</div>`;
  }

  // ---- boot ------------------------------------------------------------------------------------------------------
  async function boot() {
    try {
      [S.league, S.decisions] = await Promise.all([raw("/api/league"), raw("/api/decisions")]);
    } catch (e) { toast("The server is waking up; retrying in a few seconds."); return setTimeout(boot, 4000); }
    fillTeams($("#home")); fillTeams($("#away"));
    renderSaves();
    show("picker");
  }
  boot();
})();
