/* Dynasty mode (2026-10-08): the hub and its screens on top of app/dynasty_api.py. Sims run as background jobs on
   the server; the page polls progress. A game of the user's team opens the manager screen (v2.js) and comes back
   here when it is over. The dynasty is saved on the server after every step and mirrored to this browser. */
(() => {
  "use strict";
  const V = window.v2, $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const { raw, toast, esc, mark, badge, show, busy } = V;
  const dateText = (d) => window.cbsDate(d);
  const D = { id: null, hub: null, screen: "hub", cache: {}, poll: null };
  const STAGE = { regular: "Regular season", conf: "Conference tournaments", selection: "Selection Monday", ncaa: "NCAA tournament", done: "Season over" };

  // ---- open and refresh ----
  async function open(id, hub) {
    D.id = id; D.hub = hub || (await raw(`/api/dynasties/${id}`)); D.cache = {};
    if (D.hub.stage === "pick") { toast("Pick a team first."); return show("main"); }
    show("dyn"); setScreen("hub");
    if (D.hub.running) pollProgress();
  }
  async function refresh() { D.hub = await raw(`/api/dynasties/${D.id}`); D.cache = {}; render(); }
  async function mirror() {
    try { const sv = await raw(`/api/dynasties/${D.id}/save`); await window.cbsMirror.put(D.id, sv.save, sv.meta); } catch (e) { /* a sim may be running */ }
  }
  function setScreen(name) { D.screen = name; $$("#dyn-nav button").forEach((b) => b.classList.toggle("on", b.dataset.screen === name)); render(); }
  $$("#dyn-nav button").forEach((b) => b.addEventListener("click", () => setScreen(b.dataset.screen)));

  // ---- the header: team mark, year, record, RPI, date and week ----
  function renderHead() {
    const h = D.hub;
    $("#dyn-head").innerHTML = `<div class="who">${mark({ name: h.team })}<div><div class="name">${esc(h.team)} <span class="muted">${esc(h.conference)} · ${h.tier.toUpperCase()}</span></div><div class="muted">${esc(h.name)} · Year ${h.year}</div></div></div>
      <div class="facts"><div><span class="k">Record</span><b>${h.record[0]}-${h.record[1]}</b></div><div><span class="k">Conf</span><b>${h.conf_record[0]}-${h.conf_record[1]}</b></div><div><span class="k">RPI</span><b>${h.rpi_rank ? "#" + h.rpi_rank : "—"}</b></div><div><span class="k">Date</span><b>${dateText(h.date)}</b></div><div><span class="k">Week</span><b>${h.week}</b></div><div><span class="k">Stage</span><b>${STAGE[h.stage] || h.stage}</b></div></div>`;
  }

  // ---- sims: background jobs with progress ----
  function pauseFlags() { const s = window.cbsSettings(); return s.autoPause; }
  async function simTo(target) {
    const pause = pauseFlags();
    await raw(`/api/dynasties/${D.id}/sim`, "POST", { target, pause_mine: !!pause.myGames });
    D.hub.running = true; render();
    pollProgress();
  }
  function pollProgress() {
    clearTimeout(D.poll);
    const tick = async () => {
      let p;
      try { p = await raw(`/api/dynasties/${D.id}/progress`); } catch (e) { D.poll = setTimeout(tick, 3000); return; }
      if (p.running) {
        const el = $("#sim-progress");
        if (el) el.innerHTML = `<div class="prog"><i style="width:${p.total ? (100 * p.played / p.total).toFixed(1) : 0}%"></i></div><div class="muted">Simming the D1 world: ${p.played} of ${p.total} games · ${dateText(p.date)} · ${STAGE[p.stage] || p.stage}</div>`;
        D.poll = setTimeout(tick, 1500);
      } else {
        if (p.error) toast("The sim stopped: " + p.error);
        D.hub = p.hub; D.cache = {}; render(); mirror();
      }
    };
    tick();
  }

  // ---- the user's game ----
  async function playPending() {
    const ask = window.cbsSettings().askModes || {};
    const modes = Object.fromEntries(Object.keys(ask).filter((k) => ask[k]).map((k) => [k, "ask"]));
    const t = await raw(`/api/dynasties/${D.id}/game/open`, "POST", { modes });
    V.openDynastyGame(t, D.id);
  }
  async function simPending() { D.hub = await raw(`/api/dynasties/${D.id}/game/sim`, "POST"); D.cache = {}; render(); mirror(); }
  document.addEventListener("cbs:dyn-finish", () => busy(async () => { D.hub = await raw(`/api/dynasties/${D.id}/game/finish`, "POST"); D.cache = {}; show("dyn"); setScreen("hub"); mirror(); }));
  document.addEventListener("cbs:dyn-back", () => { show("dyn"); render(); });
  $("#nav-dyn").addEventListener("click", () => { if (D.id) { show("dyn"); refresh(); } });

  // ---- screens ----
  function render() {
    if (!D.hub) return;
    renderHead();
    const fn = { hub: renderHub, schedule: renderSchedule, standings: renderSoon, stats: renderSoon, roster: renderSoon, postseason: renderSoon }[D.screen] || renderHub;
    fn();
  }
  function resultRow(g) {
    const vs = g.side === "home" ? "vs" : "at";
    const opp = g.side === "home" ? g.away_name : g.home_name;
    const tag = g.stage !== "regular" ? `<span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : g.conf ? `<span class="tag">CONF</span>` : "";
    const box = g.i >= 0 ? `data-box="${g.i}"` : `data-postbox="${g.k}"`;
    return `<tr class="${g.result && g.result[0] === "W" ? "w" : "l"}"><td class="muted">${dateText(g.date)}</td><td class="nm">${vs} ${esc(opp)} ${tag}${g.user ? '<span class="tag you">PLAYED</span>' : ""}</td><td class="num"><b>${g.result || ""}</b>${g.inning !== 9 ? ` <span class="muted">(${g.inning})</span>` : ""}${g.run_rule ? ' <span class="muted">RR</span>' : ""}</td><td><button class="btn-ghost" ${box}>Box</button></td></tr>`;
  }
  function renderHub() {
    const h = D.hub, p = h.pending;
    const next = p ? `<div class="panel next"><div class="hdr">Next game <span class="sub">${dateText(p.date)} · ${p.stage === "regular" ? (p.weekend ? "weekend series" : "midweek") : STAGE[p.stage] || p.stage}${p.neutral ? " · neutral site" : ""}</span></div>
        <div class="body"><div class="matchup"><div>${mark({ name: p.away_name })}<b>${esc(p.away_name)}</b><span class="muted">${p.user_side === "away" ? " (you)" : ""}</span></div><div class="at">at</div><div>${mark({ name: p.home_name })}<b>${esc(p.home_name)}</b><span class="muted">${p.user_side === "home" ? " (you)" : ""}</span></div></div>
        <div class="muted" id="probables">Probable starters: set at first pitch by each team's AI (see the manager screen's pregame).</div>
        <div class="row">${h.running ? "" : `<button class="go" id="play-btn">${p.open ? "Back to the game" : "Play"}</button><button id="simgame-btn">Sim game</button>`}</div></div></div>`
      : `<div class="panel next"><div class="hdr">Next game</div><div class="body muted">${h.stage === "done" ? "The season is over." : h.stage === "regular" ? "Sim ahead to reach your next game." : "No game of yours is pending in this stage; sim ahead."}</div></div>`;
    const sims = h.running ? `<div id="sim-progress"></div>` : `<div class="sims">${[["game", "Next game"], ["week", "Next week"], ["regular", "End of regular season"], ["conf", "Conference tournament"], ["selection", "Selection Monday"], ["end", "End of season"]].map(([t, l]) => `<button data-simto="${t}" ${h.stage === "done" ? "disabled" : ""}>${l}</button>`).join("")}</div><div class="muted">Your games ${pauseFlags().myGames ? "pause the sim (Settings)" : "are played by the AI (Settings)"}.</div>`;
    const recent = h.recent.length ? `<table class="tbl">${h.recent.map(resultRow).join("")}</table>` : `<div class="muted">No games yet.</div>`;
    const news = h.news.length ? h.news.map((n) => `<div class="ev"><span class="muted">${dateText(n.date)}</span><span>${esc(n.text)}</span></div>`).join("") : `<div class="muted">Nothing yet. News comes from the engine's results only.</div>`;
    $("#dyn-main").innerHTML = `<div class="hub-grid">
      <div class="col">${next}<div class="panel"><div class="hdr">Sim to</div><div class="body">${sims}</div></div></div>
      <div class="col"><div class="panel"><div class="hdr">Recent results</div><div class="body tight">${recent}</div></div><div class="panel"><div class="hdr">News</div><div class="body tight">${news}</div></div></div>
      <div class="col"><div class="panel"><div class="hdr">Standings <span class="sub">${esc(h.conference)}</span></div><div class="body" id="hub-standings"><div class="muted">Loading…</div></div></div><div class="panel"><div class="hdr">RPI top 25</div><div class="body" id="hub-rpi"><div class="muted">Loading…</div></div></div></div>
    </div>`;
    const pb = $("#play-btn"); if (pb) pb.addEventListener("click", () => busy(playPending));
    const sb = $("#simgame-btn"); if (sb) sb.addEventListener("click", () => busy(simPending));
    $$("#dyn-main [data-simto]").forEach((b) => b.addEventListener("click", () => busy(() => simTo(b.dataset.simto))));
    bindBoxes();
    if (h.running) pollProgress();
    fillStandingsSnippets();
  }
  async function standings() { if (!D.cache.standings) D.cache.standings = await raw(`/api/dynasties/${D.id}/standings`); return D.cache.standings; }
  async function fillStandingsSnippets() {
    const st = await standings();
    const rows = st.conferences[st.mine] || [];
    const el = $("#hub-standings");
    if (el) el.innerHTML = `<table class="tbl"><tr><th>Team</th><th class="num">Conf</th><th class="num">All</th><th class="num">RPI</th></tr>${rows.map((r) => `<tr class="${r.me ? "now" : ""}"><td class="nm">${esc(r.name)}</td><td class="num">${r.cw}-${r.cl}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi_rank || "—"}</td></tr>`).join("")}</table>`;
    const el2 = $("#hub-rpi");
    if (el2) el2.innerHTML = `<table class="tbl"><tr><th>#</th><th>Team</th><th class="num">W-L</th><th class="num">RPI</th></tr>${st.national.slice(0, 25).map((r) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${r.rank}</td><td class="nm">${esc(r.name)} <span class="muted">${esc(r.conference)}</span></td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi.toFixed(3)}</td></tr>`).join("")}${st.my_rank > 25 ? `<tr class="now"><td class="muted">${st.my_rank}</td><td class="nm">${esc(D.hub.team)}</td><td class="num">${D.hub.record[0]}-${D.hub.record[1]}</td><td></td></tr>` : ""}</table>`;
  }
  async function renderSchedule() {
    const s = await raw(`/api/dynasties/${D.id}/schedule`);
    const rows = s.games.map((g) => {
      const vs = g.side === "home" ? "vs" : "at", opp = g.side === "home" ? g.away_name : g.home_name;
      const tag = g.stage && g.stage !== "regular" ? `<span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : g.conf ? `<span class="tag">CONF</span>` : "";
      const kind = g.stage && g.stage !== "regular" ? "postseason" : g.weekend ? "weekend" : "midweek";
      const res = g.status === "played" ? `<b>${g.result}</b>${g.inning !== 9 ? ` <span class="muted">(${g.inning})</span>` : ""}${g.run_rule ? ' <span class="muted">RR</span>' : ""}` : g.status === "canceled" ? `<span class="muted">canceled</span>` : g.status === "next" ? `<span class="tag you">NEXT</span>` : "";
      const box = g.status === "played" ? (g.i != null && g.i >= 0 ? `<button class="btn-ghost" data-box="${g.i}">Box</button>` : `<button class="btn-ghost" data-postbox="${g.k}">Box</button>`) : "";
      return `<tr class="${g.status} ${g.result ? (g.result[0] === "W" ? "w" : "l") : ""}"><td class="muted">${dateText(g.date)}</td><td class="muted">W${g.week}</td><td class="muted">${kind}</td><td class="nm">${vs} ${esc(opp)} ${tag}${g.user ? '<span class="tag you">PLAYED</span>' : ""}</td><td class="num">${res}</td><td>${box}</td></tr>`;
    });
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">Schedule <span class="sub">${s.games.filter((g) => g.status === "played").length} played · weekend series and midweek games · CONF = conference game</span></div><div class="body tight"><table class="tbl sched"><tr><th>Date</th><th>Wk</th><th>Slot</th><th>Opponent</th><th class="num">Result</th><th></th></tr>${rows.join("")}</table></div></div><div id="box-out"></div>`;
    bindBoxes();
  }
  function bindBoxes() {
    $$("#dyn-main [data-box], #dyn-main [data-postbox]").forEach((b) => b.addEventListener("click", () => busy(async () => {
      const g = b.dataset.box != null ? await raw(`/api/dynasties/${D.id}/games/${b.dataset.box}`) : await raw(`/api/dynasties/${D.id}/postgames/${b.dataset.postbox}`);
      showBox(g);
    })));
  }
  function showBox(g) {
    const b = g.box, batCols = ["ab", "r", "h", "rbi", "bb", "k", "hr"], pitCols = ["ip", "h", "r", "er", "bb", "k", "pitches"];
    const noR = b.no_rbi;
    const cols = noR ? batCols.filter((c) => c !== "r" && c !== "rbi") : batCols;
    const sum = (rows, k) => rows.reduce((s, r) => s + (r.line[k] || 0), 0);
    const bat = (side) => `<h3>${esc(b.teams[side])} batting</h3><table class="tbl box"><tr><th>Batter</th><th>Pos</th>${cols.map((c) => `<th class="num">${c.toUpperCase()}</th>`).join("")}</tr>${b.batting[side].map((r) => `<tr><td class="nm">${esc(r.name)}</td><td>${r.pos}</td>${cols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`).join("")}<tr class="tot"><td>Totals</td><td></td>${cols.map((c) => `<td class="num">${sum(b.batting[side], c)}</td>`).join("")}</tr></table>`;
    const pit = (side) => `<h3>${esc(b.teams[side])} pitching</h3><table class="tbl box"><tr><th>Pitcher</th>${pitCols.map((c) => `<th class="num">${c === "pitches" ? "P" : c.toUpperCase()}</th>`).join("")}</tr>${b.pitching[side].map((r) => `<tr><td class="nm">${esc(r.name)} <span class="muted">${r.role}</span></td>${pitCols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`).join("")}</table>`;
    const line = g.line ? `<table class="linescore"><tr><th></th>${g.line.away.map((_, i) => `<th>${i + 1}</th>`).join("")}<th class="tot">R</th><th class="tot">H</th><th class="tot">E</th></tr><tr><td class="team">${esc(g.away_name)}</td>${g.line.away.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.ar}</td><td class="tot">${g.hits.away}</td><td class="tot">${g.errors.away}</td></tr><tr><td class="team">${esc(g.home_name)}</td>${g.line.home.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.hr}</td><td class="tot">${g.hits.home}</td><td class="tot">${g.errors.home}</td></tr></table>` : "";
    const el = $("#box-out") || (() => { const d = document.createElement("div"); d.id = "box-out"; $("#dyn-main").appendChild(d); return d; })();
    el.innerHTML = `<div class="panel boxp"><div class="hdr">${esc(g.away_name)} ${g.ar}, ${esc(g.home_name)} ${g.hr} <span class="sub">${dateText(g.date)}${g.inning !== 9 ? ` · ${g.inning} innings` : ""}${g.run_rule ? " · run rule" : ""}${noR ? " · simmed: runs and RBI per batter are not in the engine's accumulators" : " · played on the manager screen"}</span><button class="btn-ghost" id="box-close">Close</button></div><div class="body">${line}<div class="box-grid"><div>${bat("away")}${pit("away")}</div><div>${bat("home")}${pit("home")}</div></div></div></div>`;
    $("#box-close").addEventListener("click", () => (el.innerHTML = ""));
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function renderSoon() { $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${D.screen}</div><div class="body muted">This screen arrives in a later push.</div></div>`; }

  window.dyn = { open, id: () => D.id, refresh };
})();
