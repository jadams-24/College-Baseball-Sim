/* Main screen (2026-10-08; the menu stack of the Console look 2026-11-26): continue, load, new dynasty (team
   picker), quick game, saved dynasties and settings as panels beside the menu. Settings live in this browser (localStorage); dynasty saves live on the server with
   a mirror in this browser's IndexedDB (a dynasty is a few MB: too big for localStorage). */
(() => {
  "use strict";
  const V = window.v2, $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const { raw, toast, esc, badge, ls, show, busy } = V;
  const LS_SETTINGS = "cbs.settings";
  const DEFAULTS = { simDefault: "pitch", askModes: {}, autoPause: { myGames: true, weekEnd: false, selection: true, postseason: true }, legendOpen: false };
  let settings = Object.assign({}, DEFAULTS, ls.get(LS_SETTINGS, {}));
  settings.autoPause = Object.assign({}, DEFAULTS.autoPause, settings.autoPause || {});
  window.cbsSettings = () => settings;
  const saveSettings = () => ls.set(LS_SETTINGS, settings);

  // ---- the browser's mirror of dynasty saves (IndexedDB) ----
  const DB = { name: "cbs", store: "dynasties" };
  function db() {
    return new Promise((res, rej) => {
      try {
        const r = indexedDB.open(DB.name, 1);
        r.onupgradeneeded = () => r.result.createObjectStore(DB.store, { keyPath: "id" });
        r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
      } catch (e) { rej(e); }
    });
  }
  async function mirrorPut(id, save, meta) {
    try { const d = await db(); const tx = d.transaction(DB.store, "readwrite"); tx.objectStore(DB.store).put({ id, save, meta, time: Date.now() }); await new Promise((r) => (tx.oncomplete = r)); } catch (e) { /* private mode: fine */ }
  }
  async function mirrorAll() {
    try { const d = await db(); const tx = d.transaction(DB.store, "readonly"); const q = tx.objectStore(DB.store).getAll(); return await new Promise((r) => (q.onsuccess = () => r(q.result || []))); } catch (e) { return []; }
  }
  async function mirrorDel(id) {
    try { const d = await db(); const tx = d.transaction(DB.store, "readwrite"); tx.objectStore(DB.store).delete(id); await new Promise((r) => (tx.oncomplete = r)); } catch (e) { /* fine */ }
  }
  window.cbsMirror = { put: mirrorPut, all: mirrorAll, del: mirrorDel };

  // ---- dates: one calendar, the server's (app/calendar.py): date 0 is the Monday of the opening week ----
  const CAL = { date0: null };                      // ISO date of engine date 0; set from /api/league, a dynasty's hub overrides it (its year)
  const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  function realDate(day) { const base = CAL.date0 ? Date.parse(CAL.date0 + "T00:00:00Z") : (V.S.league && V.S.league.calendar ? Date.parse(V.S.league.calendar.date0 + "T00:00:00Z") : null); return base == null ? null : new Date(base + day * 86400000); }
  function dateText(day, opts) {
    if (day == null) return "";
    const d = realDate(day);
    if (d == null) return `day ${day}`;
    const s = d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
    return opts && opts.weekday ? `${WD[d.getUTCDay()]} ${s}` : s;
  }
  window.cbsDate = dateText;
  window.cbsCalendar = { set: (c) => { CAL.date0 = c && c.date0 ? c.date0 : null; }, get: () => CAL.date0 };
  const STAGE = { regular: "regular season", conf: "conference tournament", selection: "Selection Monday", ncaa: "NCAA tournament", done: "season over", pick: "pick a team" };
  const LD = window.cbsLoad;

  // ---- continue and saved dynasties ----
  const metaText = (m) => `${m.team || "no team yet"}${m.record ? ` · ${m.record[0]}-${m.record[1]}` : ""}${m.stage ? ` · ${STAGE[m.stage] || m.stage}` : ""}`;
  // the menu's Load Dynasty and Game Preferences open a panel beside the menu; a second click closes it
  function openPanel(name) {
    ["saves", "settings"].forEach((n) => { const el = $(`#panel-${n}`), on = n === name && el.classList.contains("hidden"); el.classList.toggle("hidden", !on); $(`.menu-btn[data-open="${n}"]`).classList.toggle("on", on); });
  }
  $$(".menu-btn[data-open]").forEach((b) => b.addEventListener("click", () => openPanel(b.dataset.open)));
  async function renderMain() {
    let server = { dynasties: [], latest: null };
    $("#dyn-saves").innerHTML = LD.skeleton(3, 3);
    try { server = await raw("/api/saves"); } catch (e) { /* the server may be waking */ }
    const mirrors = await mirrorAll();
    const latestGame = ls.get("cbs.latest", null);
    // continue: the newest of the server's dynasties, the mirrors and the latest quick game
    const cands = [];
    if (server.latest) cands.push({ kind: "dynasty", id: server.latest.id, meta: server.latest, time: server.latest.saved * 1000, where: "server" });
    mirrors.forEach((m) => { if (!cands.some((c) => c.id === m.id)) cands.push({ kind: "dynasty", id: m.id, meta: m.meta, time: m.time, where: "mirror", save: m.save }); });
    if (latestGame) cands.push({ kind: "game", meta: latestGame, time: latestGame.time });
    cands.sort((a, b) => b.time - a.time);
    const c = cands[0];
    // the Continue button at the top of the menu: the newest dynasty or game, named under the label
    const btn = $("#menu-continue");
    btn.disabled = !c;
    $("#continue-sub").textContent = c ? (c.kind === "dynasty" ? `${c.meta.name || "Dynasty"} · Year ${c.meta.year || 1} · ${metaText(c.meta)}` : `Quick game · ${c.meta.title || "game"}`) : "No dynasty or game yet";
    btn.onclick = c ? () => busy(() => LD.act(btn, "Loading…", () => (c.kind === "dynasty" ? openDynasty(c) : V.loadSave(c.meta.save)))) : null;
    // saved dynasties
    const rows = [];
    const seen = new Set();
    server.dynasties.forEach((m) => { seen.add(m.id); rows.push({ id: m.id, meta: m, where: "server", time: m.saved * 1000 }); });
    mirrors.forEach((m) => { if (!seen.has(m.id)) rows.push({ id: m.id, meta: m.meta, where: "mirror", time: m.time, save: m.save }); });
    rows.sort((a, b) => b.time - a.time);
    $("#dyn-saves").innerHTML = rows.length ? `<table class="tbl"><tr><th>Dynasty</th><th>Team</th><th>Record</th><th>Stage</th><th>Saved</th><th></th></tr>${rows.map((r, i) => `<tr><td class="nm">${esc(r.meta.name || "Dynasty")} <span class="muted">Y${r.meta.year || 1}</span></td><td>${esc(r.meta.team || "—")}</td><td>${r.meta.record ? `${r.meta.record[0]}-${r.meta.record[1]}` : ""}</td><td>${STAGE[r.meta.stage] || ""} <span class="muted">${r.where === "mirror" ? "browser mirror" : ""}</span></td><td class="muted">${new Date(r.time).toLocaleString()}</td><td><button class="btn-ghost" data-load="${i}">Load</button> <button class="btn-ghost" data-dl="${i}">Download</button> <button class="btn-ghost" data-del="${i}">Delete</button></td></tr>`).join("")}</table>`
      : `<div class="muted">None yet.</div>`;
    $$("#dyn-saves [data-load]").forEach((b) => b.addEventListener("click", () => busy(() => LD.act(b, "Loading…", () => openDynasty(rows[+b.dataset.load])))));
    $$("#dyn-saves [data-dl]").forEach((b) => b.addEventListener("click", () => busy(() => downloadDynasty(rows[+b.dataset.dl]))));
    $$("#dyn-saves [data-del]").forEach((b) => b.addEventListener("click", () => busy(async () => {
      const r = rows[+b.dataset.del];
      if (!confirm(`Delete ${r.meta.name || "this dynasty"}? The server save and this browser's mirror are removed.`)) return;
      try { await raw(`/api/dynasties/${r.id}`, "DELETE"); } catch (e) { /* not on the server */ }
      await mirrorDel(r.id); renderMain();
    })));
    renderSettings();
  }
  async function openDynasty(c) {
    // the server's copy first; when the server has forgotten it, the browser's mirror restores it
    try { await raw(`/api/dynasties/${c.id}`); return window.dyn.open(c.id); }
    catch (e) {
      const m = c.save ? c : (await mirrorAll()).find((x) => x.id === c.id);
      if (!m) return toast("The server has no copy of this dynasty and this browser holds no mirror.");
      toast("Restoring the dynasty from this browser's mirror…");
      const pn = LD.panel({ title: "Restoring the dynasty", sub: "From this browser's mirror." });
      let h;
      try { h = await raw("/api/dynasties/load", "POST", { save: m.save }); } finally { pn.done(); }
      await mirrorDel(c.id); await mirrorPut(h.id, m.save, m.meta);
      return window.dyn.open(h.id, h);
    }
  }
  async function downloadDynasty(r) {
    let save = r.save;
    if (!save) save = (await raw(`/api/dynasties/${r.id}/save`)).save;
    const blob = new Blob([save], { type: "application/octet-stream" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `${(r.meta.name || "dynasty").replace(/[^\\w-]+/g, "_")}_Y${r.meta.year || 1}.cbsd`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  $("#dyn-file").addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => busy(async () => { const pn = LD.panel({ title: "Loading the dynasty file" }); let h; try { h = await raw("/api/dynasties/load", "POST", { save: String(rd.result).trim() }); } finally { pn.done(); } await mirrorPut(h.id, String(rd.result).trim(), h); window.dyn.open(h.id, h); });
    rd.readAsText(f);
  });

  // ---- settings ----
  const KINDS = () => (V.S.decisions ? V.S.decisions.kinds.filter((k) => k.when !== "pregame") : []);
  function renderSettings() {
    const sp = ["pitch", "pa", "half", "inning", "three_innings", "game"], spl = { pitch: "Next pitch", pa: "At-bat", half: "Half inning", inning: "Inning", three_innings: "3 innings", game: "End of game" };
    $("#settings-body").innerHTML = `<div class="set"><div class="k">Default sim step</div><select id="set-sim">${sp.map((x) => `<option value="${x}" ${settings.simDefault === x ? "selected" : ""}>${spl[x]}</option>`).join("")}</select></div>
      <div class="set"><div class="k">Ask me before deciding</div><div class="muted">Autopilot answers everything else; these stop the game with the question.</div><div class="asks">${KINDS().map((k) => `<label class="ask"><input type="checkbox" data-ask="${k.kind}" ${settings.askModes[k.kind] ? "checked" : ""}> ${esc(k.label)}</label>`).join("")}</div></div>
      <div class="set"><div class="k">Dynasty sims pause</div><div class="asks">${[["myGames", "before my games"], ["weekEnd", "at the end of each week"], ["selection", "on Selection Monday"], ["postseason", "before the postseason"]].map(([k, l]) => `<label class="ask"><input type="checkbox" data-pause="${k}" ${settings.autoPause[k] ? "checked" : ""}> ${l}</label>`).join("")}</div></div>
      <div class="set"><div class="muted">Your games pause the sim before they start when "before my games" is ticked; otherwise the AI plays them. The hub's "Advance to…" menu stops at the next day, the end of the week, the end of the regular season, the conference tournament, Selection Monday or the end of the season, and at every auto-pause ticked above on the way.</div></div>
      <div class="set"><div class="k">Debug</div><div class="muted" id="set-debug">${(() => { const h = window.dyn && window.dyn.hub(); return h ? `Current dynasty: ${h.games_played} of ${h.games_total} D1 games simmed · engine date ${h.date} · ${h.stage}` : "No dynasty loaded."; })()}</div></div>
      <div class="set"><div class="k">Rating colors</div><div class="scale">${[["r20", "20–39"], ["r40", "40–49"], ["r50", "50–59"], ["r60", "60–69"], ["r70", "70+"]].map(([c, l]) => `<span class="rt ${c}"><b>${l}</b></span>`).join("")}</div><div class="muted">20–80, 50 is the D1 median, 10 points per SD. Blue at 70 and up, green 60s, plain 50s, orange 40s, red below 40. The number always shows; the color never carries the meaning alone. Tap a rating anywhere for its meaning.</div></div>`;
    $("#set-sim").addEventListener("change", (e) => { settings.simDefault = e.target.value; saveSettings(); });
    $$("#settings-body [data-ask]").forEach((c) => c.addEventListener("change", () => { settings.askModes[c.dataset.ask] = c.checked; saveSettings(); }));
    $$("#settings-body [data-pause]").forEach((c) => c.addEventListener("change", () => { settings.autoPause[c.dataset.pause] = c.checked; saveSettings(); }));
  }

  // ---- new dynasty: the team picker ----
  let pick = { id: null, teams: [] };
  async function startPicker() {
    show("picker");
    $("#picker-sub").textContent = "building the D1 world for this dynasty (a few seconds here, about a minute on the free host)…";
    $("#pick-list").innerHTML = LD.skeleton(14, 7);
    const seed = $("#dyn-seed").value ? +$("#dyn-seed").value : null;
    const h = LD.panel({ title: "Building the D1 world", sub: "307 programs drawn from the engine's talent distributions. A few seconds here, about a minute on the free host." });
    let r;
    try { r = await raw("/api/dynasties", "POST", { seed }); }
    catch (e) { $("#pick-list").innerHTML = LD.errorPanel(e.message || String(e), () => busy(startPicker), "Couldn't build the world"); h.fail(e.message || String(e), () => busy(startPicker)); return; }
    finally { if (!h.failed) h.done(); }
    pick = { id: r.id, teams: r.teams, seed: r.seed, categories: r.categories || [], sort: { key: "overall", dir: -1 } };
    $("#picker-sub").textContent = `seed ${r.seed} · pick your program`;
    renderPicker();
  }
  const GRADE_CLASS = (g) => (!g ? "" : g[0] === "A" ? "gA" : g[0] === "B" ? "gB" : g[0] === "C" ? "gC" : g[0] === "D" ? "gD" : "gF");
  const gradeChip = (cat, g, conf) => `<span class="grade ${GRADE_CLASS(g)}" title="${esc(cat.label)}${conf ? ` · confidence ${esc(conf)}` : ""}"><i>${esc(cat.short)}</i><b>${esc(g || "–")}</b></span>`;
  window.cbsGradeChip = gradeChip;
  // the picker table (2026-11-26): one column per report-card grade (all 13), every column sortable from its header.
  // Grades sort A+ down to F; a missing grade sorts last either way; ties fall back to Overall, then the name.
  const GRADE_RANK = (g) => { if (!g) return null; const base = { A: 4, B: 3, C: 2, D: 1, F: 0 }[g[0]]; return base == null ? null : base * 3 + (g[1] === "+" ? 1 : g[1] === "-" ? -1 : 0); };
  const TIER_RANK = { p4: 3, mid: 2, low: 1 };
  const SORT_TEXT = { name: (t) => t.name, conference: (t) => t.conference };                       // text columns: A to Z first
  const SORT_NUM = { tier: (t) => TIER_RANK[t.tier] || 0, off: (t) => t.off, def: (t) => t.def, overall: (t) => t.overall };   // numbers and grades: best first
  function sortRows(rows) {
    const { key, dir } = pick.sort || { key: "overall", dir: -1 };
    const val = SORT_TEXT[key] || SORT_NUM[key] || ((t) => (t.grades ? GRADE_RANK(t.grades[key]) : null));
    const text = !!SORT_TEXT[key];
    rows.sort((a, b) => {
      const x = val(a), y = val(b);
      if (x == null || y == null) { if (x != y) return x == null ? 1 : -1; }
      else if (x !== y) return (text ? String(x).localeCompare(String(y)) : x - y) * dir;
      return b.overall - a.overall || a.name.localeCompare(b.name);
    });
    return rows;
  }
  function renderPicker() {
    const f = ($("#pick-search").value || "").toLowerCase(), tier = $("#pick-tier").value;
    const rows = sortRows(pick.teams.filter((t) => (!f || `${t.name} ${t.abbr || ""} ${t.conference} ${t.tier} ${t.location || ""}`.toLowerCase().includes(f)) && (!tier || t.tier === tier)));
    const cats = pick.categories;
    const real = pick.teams.some((t) => t.school);
    const so = pick.sort || { key: "overall", dir: -1 };
    const th = (key, label, cls, title) => `<th class="sortable ${cls || ""} ${so.key === key ? (so.dir > 0 ? "asc" : "desc") : ""}" data-sort="${key}" tabindex="0" role="button" ${so.key === key ? `aria-sort="${so.dir > 0 ? "ascending" : "descending"}"` : ""} title="${esc(title || label)} · click to sort">${esc(label)}</th>`;
    const grade = (c, t) => { const g = t.grades && t.grades[c.key]; return `<td class="g ${GRADE_CLASS(g)}" title="${esc(c.label)}">${esc(g || "–")}</td>`; };
    const keep = $("#pick-list").scrollLeft;
    $("#pick-list").innerHTML = rows.length ? `<table class="tbl pick"><tr>${th("name", real ? "School" : "Team", "stick")}${th("conference", "Conference", "ph-hide")}${th("tier", "Tier")}${th("off", "Off", "ph-hide ctr", "Team offense")}${th("def", "Def", "ph-hide ctr", "Team run prevention")}${th("overall", "Ovr", "ctr", "Overall")}${real ? cats.map((c) => th(c.key, c.short, "g", c.label)).join("") : ""}<th class="act"></th></tr>${rows.map((t) => `<tr data-row="${t.tid}"><td class="nm stick" title="${esc(t.name)}${t.engine_name ? ` · engine id: ${esc(t.engine_name)}` : ""}">${V.chip ? V.chip(t.tid) : ""}${esc(t.name)}${t.location ? `<small class="muted">${esc(t.location)}</small>` : ""}</td><td class="ph-hide conf" title="${esc(t.conference)}">${esc(t.conference)}</td><td>${t.tier.toUpperCase()}</td><td class="ph-hide ctr">${badge("off", t.off)}</td><td class="ph-hide ctr">${badge("def", t.def)}</td><td class="ctr">${badge("ovr", t.overall)}</td>${real ? cats.map((c) => grade(c, t)).join("") : ""}<td class="act"><button data-pick="${t.tid}">Take over</button></td></tr>`).join("")}</table>${real ? '<div class="muted pick-note">Grades compare every D1 program. Omaha Contender reflects this dynasty. Click a column header to sort; click again to reverse.</div>' : ""}` : `<div class="muted">No team matches.</div>`;
    $("#pick-list").scrollLeft = keep;
    const sortBy = (key) => { pick.sort = { key, dir: so.key === key ? -so.dir : (SORT_TEXT[key] ? 1 : -1) }; renderPicker(); };
    $$("#pick-list th[data-sort]").forEach((h) => { h.addEventListener("click", () => sortBy(h.dataset.sort)); h.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sortBy(h.dataset.sort); } }); });
    $$("#pick-list [data-pick]").forEach((b) => b.addEventListener("click", () => busy(async () => {
      const t = pick.teams.find((x) => x.tid === +b.dataset.pick);
      if (!confirm(`Take over ${t.name} (${t.conference}, ${t.tier.toUpperCase()})? Year 1 starts now.`)) return;
      await startDynasty(b, t);
    }, { quiet: true })));
  }
  // the dynasty's start builds its engine: the button works, the panel shows after 2 s with the elapsed time (no measurable progress)
  async function startDynasty(b, t) {
    const h = LD.panel({ title: `Starting your ${t.name} dynasty`, sub: "Building the season's engine and schedule." });
    try {
      const hub = await LD.act(b, "Starting…", () => raw(`/api/dynasties/${pick.id}/start`, "POST", { tid: t.tid }));
      h.done();
      window.dyn.open(hub.id, hub);
    } catch (e) { h.fail(e.message || String(e), () => busy(() => startDynasty(b, t), { quiet: true })); }
  }
  $("#pick-search").addEventListener("input", renderPicker);
  $("#pick-tier").addEventListener("change", renderPicker);
  $("#picker-back").addEventListener("click", () => show("main"));
  $("#tile-dynasty").addEventListener("click", () => busy(startPicker));
  $("#tile-quick").addEventListener("click", () => { show("lobby"); V.renderSaves(); });

  // team strength badges reuse the rating scale: label them
  V.RATING.off = ["Off", "Team offense: the drawn offensive talent on the 20–80 scale across D1 (50 = median)"];
  V.RATING.def = ["Def", "Team run prevention on the 20–80 scale across D1"];
  V.RATING.ovr = ["Ovr", "Offense and run prevention together, 20–80 across D1"];

  document.addEventListener("cbs:ready", renderMain);
  document.addEventListener("cbs:screen", (e) => { if (e.detail === "main") renderMain(); });
  window.cbsMain = { render: renderMain, settings: () => settings };
})();
