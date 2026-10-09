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
    const stops = [["weekEnd", "week_end"], ["postseason", "postseason"], ["selection", "selection"]].filter(([k]) => pause[k]).map(([, v]) => v);
    await raw(`/api/dynasties/${D.id}/sim`, "POST", { target, pause_mine: !!pause.myGames, stops });
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
        if (el) el.innerHTML = p.kind === "background"
          ? `<div class="prog"><i style="width:${p.ahead_total ? (100 * p.ahead / p.ahead_total).toFixed(1) : 0}%"></i></div><div class="muted">The rest of the league's week is simming while you play: ${p.ahead} of ${p.ahead_total} games</div>`
          : `<div class="prog"><i style="width:${p.total ? (100 * p.played / p.total).toFixed(1) : 0}%"></i></div><div class="muted">Simming the D1 world: ${p.played} of ${p.total} games · ${dateText(p.date)} · ${STAGE[p.stage] || p.stage}</div>`;
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
  // while a dynasty game is on the manager screen, the league's background sim shows its progress in the sim bar
  let gamePoll = null;
  document.addEventListener("cbs:screen", (e) => {
    clearTimeout(gamePoll);
    if (e.detail !== "game" || !V.S.game || !V.S.game.dynasty) return;
    const tick = async () => {
      if (V.S.screen !== "game") return;
      try {
        const p = await raw(`/api/dynasties/${V.S.game.dynasty}/progress`);
        let el = $("#league-sim");
        if (!el) { el = document.createElement("span"); el.id = "league-sim"; el.className = "muted"; $("#simbar").appendChild(el); }
        el.textContent = p.running && p.kind === "background" ? `League: ${p.ahead} of ${p.ahead_total} other games this week simmed` : p.running ? "League sim running" : "League: this week's other games are in";
      } catch (err) { /* the next tick */ }
      gamePoll = setTimeout(tick, 2500);
    };
    tick();
  });
  $("#nav-dyn").addEventListener("click", () => { if (D.id) { show("dyn"); refresh(); } });

  // ---- screens ----
  function render() {
    if (!D.hub) return;
    renderHead();
    const nav = $("#dyn-nav");
    if (D.hub.stage === "done" && !nav.querySelector("[data-screen='summary']")) { const b = document.createElement("button"); b.dataset.screen = "summary"; b.textContent = "Year in review"; b.addEventListener("click", () => setScreen("summary")); nav.appendChild(b); }
    const fn = { hub: renderHub, schedule: renderSchedule, standings: renderStandings, stats: renderStats, roster: renderRoster, postseason: renderPostseason, summary: renderSummary }[D.screen] || renderHub;
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
        ${p.probables ? `<div class="probables">${["away", "home"].map((sd) => p.probables[sd] ? `<div><span class="k">${sd === "away" ? "Away" : "Home"} starter</span><b>${esc(p.probables[sd].name)}</b> <span class="muted">${p.probables[sd].role}</span> ${["stuff", "control", "movement", "stamina"].map((k) => badge(k, p.probables[sd].ratings[k])).join(" ")}</div>` : "").join("")}<div class="muted">Probable starters: each AI's pick at first pitch; yours can change in the pregame.</div></div>` : `<div class="muted">Probable starters: set at first pitch.</div>`}
        <div class="row">${h.running && h.job_kind !== "background" ? "" : `<button class="go" id="play-btn">${p.open ? "Back to the game" : "Play"}</button><button id="simgame-btn">Sim game</button>`}</div></div></div>`
      : `<div class="panel next"><div class="hdr">Next game</div><div class="body muted">${h.stage === "done" ? `The season is over. <button class="go" id="to-summary">Year in review</button>` : h.stage === "regular" ? "Sim ahead to reach your next game." : "No game of yours is pending in this stage; sim ahead."}</div></div>`;
    const sims = h.running ? `<div id="sim-progress"></div>` : `<div class="sims">${[["game", "Advance to next game"], ["day", "Advance day"], ["week", "Advance week"], ["regular", "End of regular season"], ["conf", "Conference tournament"], ["selection", "Selection Monday"], ["end", "End of season"]].map(([t, l]) => `<button data-simto="${t}" ${h.stage === "done" ? "disabled" : ""}>${l}</button>`).join("")}</div><div class="muted">Your games ${pauseFlags().myGames ? "pause the sim" : "are played by the AI"}; longer sims also pause ${[["weekEnd", "at each week's end"], ["postseason", "before the postseason"], ["selection", "on Selection Monday"]].filter(([k]) => pauseFlags()[k]).map(([, l]) => l).join(", ") || "nowhere else"} (Settings).</div>`;
    const recent = h.recent.length ? `<table class="tbl">${h.recent.map(resultRow).join("")}</table>` : `<div class="muted">No games yet.</div>`;
    const news = h.news.length ? h.news.map((n) => `<div class="ev"><span class="muted">${dateText(n.date)}</span><span>${esc(n.text)}</span></div>`).join("") : `<div class="muted">Nothing yet. News comes from the engine's results only.</div>`;
    $("#dyn-main").innerHTML = `<div class="hub-grid">
      <div class="col">${next}<div class="panel"><div class="hdr">Advance</div><div class="body">${sims}</div></div></div>
      <div class="col"><div class="panel"><div class="hdr">Recent results</div><div class="body tight">${recent}</div></div><div class="panel"><div class="hdr">News</div><div class="body tight">${news}</div></div></div>
      <div class="col"><div class="panel"><div class="hdr">Standings <span class="sub">${esc(h.conference)}</span></div><div class="body" id="hub-standings"><div class="muted">Loading…</div></div></div><div class="panel"><div class="hdr">RPI top 25</div><div class="body" id="hub-rpi"><div class="muted">Loading…</div></div></div></div>
    </div>`;
    const pb = $("#play-btn"); if (pb) pb.addEventListener("click", () => busy(playPending));
    const ts = $("#to-summary"); if (ts) ts.addEventListener("click", () => setScreen("summary"));
    const sb = $("#simgame-btn"); if (sb) sb.addEventListener("click", () => busy(simPending));
    $$("#dyn-main [data-simto]").forEach((b) => b.addEventListener("click", () => busy(() => simTo(b.dataset.simto))));
    bindBoxes();
    if (h.running) pollProgress();
    fillStandingsSnippets();
  }
  async function standings() {
    if (D.cache.standings) return D.cache.standings;
    const v = await raw(`/api/dynasties/${D.id}/standings`);          // the cache may have been reset while awaiting: return the value itself
    D.cache.standings = v;
    return v;
  }
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
  // ---- standings: every conference, and the national RPI top 25 and top 64 ----
  async function renderStandings() {
    const st = await standings();
    const confs = Object.keys(st.conferences).sort((a, b) => (a === st.mine ? -1 : b === st.mine ? 1 : a.localeCompare(b)));
    const table = (rows) => `<table class="tbl"><tr><th>Team</th><th class="num">Conf</th><th class="num">All</th><th class="num">RPI</th></tr>${rows.map((r) => `<tr class="${r.me ? "now" : ""}"><td class="nm">${esc(r.name)}</td><td class="num">${r.cw}-${r.cl}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi_rank || "—"}</td></tr>`).join("")}</table>`;
    const nat = (lo, hi) => `<table class="tbl"><tr><th>#</th><th>Team</th><th>Conf</th><th class="num">W-L</th><th class="num">RPI</th></tr>${st.national.slice(lo, hi).map((r) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${r.rank}</td><td class="nm">${esc(r.name)}</td><td class="muted">${esc(r.conference)}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi.toFixed(3)}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `<div class="tabs" id="st-tabs"><button data-t="conf" class="on">Conferences</button><button data-t="top25">RPI top 25</button><button data-t="top64">RPI top 64</button></div>
      <div id="st-conf" class="st-grid">${confs.map((c) => `<div class="panel"><div class="hdr">${esc(c)}${c === st.mine ? '<span class="you-tag">you</span>' : ""}</div><div class="body tight">${table(st.conferences[c])}</div></div>`).join("")}</div>
      <div id="st-top25" class="hidden"><div class="panel"><div class="hdr">RPI top 25 <span class="sub">your rank: ${st.my_rank || "—"}</span></div><div class="body tight">${nat(0, 25)}</div></div></div>
      <div id="st-top64" class="hidden"><div class="panel"><div class="hdr">RPI top 64 <span class="sub">your rank: ${st.my_rank || "—"}</span></div><div class="body tight">${nat(0, 64)}</div></div></div>`;
    $$("#st-tabs button").forEach((b) => b.addEventListener("click", () => { $$("#st-tabs button").forEach((x) => x.classList.toggle("on", x === b)); ["conf", "top25", "top64"].forEach((t) => $(`#st-${t}`).classList.toggle("hidden", t !== b.dataset.t)); }));
  }

  // ---- stats: the team's batting and pitching (sortable), national leaders ----
  const BCOLS = [["g", "G"], ["pa", "PA"], ["ab", "AB"], ["h", "H"], ["2b", "2B"], ["3b", "3B"], ["hr", "HR"], ["bb", "BB"], ["hbp", "HBP"], ["k", "K"], ["avg", "AVG"], ["obp", "OBP"], ["slg", "SLG"], ["ops", "OPS"]];
  const PCOLS = [["g", "G"], ["gs", "GS"], ["ip", "IP"], ["h", "H"], ["r", "R"], ["er", "ER"], ["bb", "BB"], ["k", "K"], ["hr", "HR"], ["era", "ERA"], ["whip", "WHIP"], ["k9", "K/9"], ["bb9", "BB/9"]];
  const f3 = (v) => (typeof v === "number" ? v.toFixed(3).replace(/^0\./, ".") : v);
  const RATE = new Set(["avg", "obp", "slg", "ops"]);
  let sortBy = { b: "pa", p: "outs", dir: -1 };
  function statTable(rows, cols, which) {
    const key = sortBy[which] === "ip" ? "outs" : sortBy[which];
    const sorted = rows.slice().sort((a, b) => (a.stats[key] > b.stats[key] ? 1 : a.stats[key] < b.stats[key] ? -1 : 0) * sortBy.dir);
    return `<table class="tbl stats"><tr><th>Name</th><th>Pos</th>${cols.map(([k, l]) => `<th class="num ${sortBy[which] === k ? "on" : ""}" data-sort="${k}" data-which="${which}">${l}</th>`).join("")}</tr>${sorted.map((r) => `<tr><td class="nm">${esc(r.name)}</td><td>${r.pos}</td>${cols.map(([k]) => `<td class="num">${k === "era" || k === "whip" || k === "k9" || k === "bb9" ? r.stats[k].toFixed(k === "era" || k === "whip" ? 2 : 1) : RATE.has(k) ? f3(r.stats[k]) : r.stats[k]}</td>`).join("")}</tr>`).join("")}</table>`;
  }
  async function renderStats() {
    if (!D.cache.stats) D.cache.stats = await raw(`/api/dynasties/${D.id}/stats`);
    const { team, leaders } = D.cache.stats;
    const lead = (title, rows, fmt) => `<div class="panel"><div class="hdr">${title}</div><div class="body tight"><table class="tbl">${rows.length ? rows.map((r, i) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${i + 1}</td><td class="nm">${esc(r.name)} <span class="muted">${esc(r.team)}</span></td><td class="num">${fmt(r.value)}</td></tr>`).join("") : `<tr><td class="muted">no qualified player yet</td></tr>`}</table></div></div>`;
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${esc(team.team)} batting <span class="sub">${team.games} games · tap a column to sort · not in the engine's accumulators: ${team.missing.join(", ")}</span></div><div class="body tight scroll-x">${statTable(team.batting, BCOLS, "b")}</div></div>
      <div class="panel"><div class="hdr">${esc(team.team)} pitching</div><div class="body tight scroll-x">${statTable(team.pitching, PCOLS, "p")}</div></div>
      <div class="hdr-line">National leaders <span class="muted">qualified: ${leaders.floors.batting} (batting), ${leaders.floors.pitching} (pitching)</span></div>
      <div class="st-grid">${lead("Batting average", leaders.batting.avg, f3)}${lead("Home runs", leaders.batting.hr, (v) => v)}${lead("OPS", leaders.batting.ops, f3)}${lead("Hits", leaders.batting.h, (v) => v)}${lead("ERA", leaders.pitching.era, (v) => v.toFixed(2))}${lead("Strikeouts", leaders.pitching.k, (v) => v)}${lead("K/9", leaders.pitching.k9, (v) => v.toFixed(1))}${lead("WHIP", leaders.pitching.whip, (v) => v.toFixed(2))}</div>`;
    $$("#dyn-main [data-sort]").forEach((h) => h.addEventListener("click", () => { const w = h.dataset.which; if (sortBy[w] === h.dataset.sort) sortBy.dir = -sortBy.dir; else { sortBy[w] = h.dataset.sort; sortBy.dir = h.dataset.sort === "era" || h.dataset.sort === "whip" || h.dataset.sort === "bb9" ? 1 : -1; } renderStats(); }));
  }

  // ---- roster: ratings, position, B/T, class, the season line, pitchers' rest ----
  async function renderRoster() {
    if (!D.cache.roster) D.cache.roster = await raw(`/api/dynasties/${D.id}/roster`);
    const r = D.cache.roster;
    const bk = ["contact", "gap", "power", "eye", "avoid_k", "speed", "glove", "arm"], pk = ["stuff", "control", "movement", "stamina", "hold"];
    const bat = `<table class="tbl roster"><tr><th>Pos</th><th>Name</th><th>B/T</th><th>Yr</th>${bk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">AVG</th><th class="num">OBP</th><th class="num">SLG</th><th class="num">HR</th></tr>${r.batters.map((p) => `<tr><td>${p.pos}</td><td class="nm">${esc(p.name)} <span class="muted">${p.role}</span></td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${bk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${f3(p.stats.avg)}</td><td class="num">${f3(p.stats.obp)}</td><td class="num">${f3(p.stats.slg)}</td><td class="num">${p.stats.hr}</td></tr>`).join("")}</table>`;
    const rest = (p) => (p.last_outing ? `${p.last_outing.days_ago === 0 ? "today" : p.last_outing.days_ago === 1 ? "yesterday" : p.last_outing.days_ago + " days ago"} · ${p.last_outing.pitches} pitches` : "no outing yet");
    const pit = `<table class="tbl roster"><tr><th>Role</th><th>Name</th><th>B/T</th><th>Yr</th>${pk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">IP</th><th class="num">ERA</th><th class="num">K</th><th>Last outing</th></tr>${r.pitchers.map((p) => `<tr><td>${p.role}</td><td class="nm">${esc(p.name)}</td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${pk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${p.stats.ip}</td><td class="num">${p.stats.era.toFixed(2)}</td><td class="num">${p.stats.k}</td><td class="muted">${rest(p)}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${esc(r.team)} batters <span class="sub">B/T = bats (S for a switch hitter) / throws · class arrives with the engine's roster rules, a dash until then</span></div><div class="body tight scroll-x">${bat}</div></div>
      <div class="panel"><div class="hdr">${esc(r.team)} pitchers <span class="sub">rest: the last outing's date and pitches (the AI's rest rule reads these)</span></div><div class="body tight scroll-x">${pit}</div></div>`;
  }

  // ---- postseason: conference tournaments in their formats, Selection Monday, regionals, supers, Omaha ----
  function gameLine(g) {
    const w = g.hr > g.ar ? "home" : "away";
    return `<div class="pg ${g.side ? "mine" : ""}"><span class="muted">${dateText(g.date)}</span><span class="${w === "away" ? "won" : ""}">${esc(g.away_name)} ${g.ar}</span><span class="muted">${g.neutral ? "vs" : "at"}</span><span class="${w === "home" ? "won" : ""}">${esc(g.home_name)} ${g.hr}</span>${g.inning !== 9 ? `<span class="muted">(${g.inning})</span>` : ""}${g.user ? '<span class="tag you">PLAYED</span>' : ""}<button class="btn-ghost" data-postbox="${g.k}">Box</button></div>`;
  }
  function byDay(games) {
    const days = {};
    games.forEach((g) => (days[g.date] = days[g.date] || []).push(g));
    return Object.keys(days).sort((a, b) => a - b).map((d, i) => `<div class="round"><div class="k">Day ${i + 1} · ${dateText(+d)}</div>${days[d].map(gameLine).join("")}</div>`).join("");
  }
  async function renderPostseason() {
    const ps = await raw(`/api/dynasties/${D.id}/postseason`);
    if (ps.note) { $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">Postseason</div><div class="body muted">${esc(ps.note)}</div></div>`; return; }
    const confs = Object.keys(ps.conference).sort((a, b) => (a === ps.mine_conf ? -1 : b === ps.mine_conf ? 1 : a.localeCompare(b)));
    const conf = (c) => { const t = ps.conference[c]; return `<div class="panel"><div class="hdr">${esc(c)} tournament${c === ps.mine_conf ? '<span class="you-tag">you</span>' : ""} <span class="sub">${t.champion_name ? "champion: " + esc(t.champion_name) : t.games.length ? "in progress" : "not started"}</span></div>
      <div class="body"><div class="muted">${esc(t.description)}${t.venue ? " · " + esc(t.venue) : ""}</div><div class="seeds">${t.seeds.map((s) => `<span class="${s.me ? "me" : ""}">${s.seed}. ${esc(s.name)}</span>`).join("")}</div>${byDay(t.games)}</div></div>`; };
    const sel = ps.selection ? `<div class="panel"><div class="hdr">Selection Monday <span class="sub">${ps.selection.in_field ? (ps.selection.my_status.national_seed ? `you are the #${ps.selection.my_status.national_seed} national seed` : `you are in the field: a ${ps.selection.my_status.line} seed${ps.selection.my_status.auto ? " (automatic bid)" : " (at large)"}`) : `not selected · RPI rank ${ps.selection.my_status.rpi_rank || "—"}`}</span></div>
      <div class="body"><div class="k">National seeds (regional hosts)</div><div class="seeds">${ps.selection.national_seeds.map((s) => `<span class="${s.me ? "me" : ""}">${s.seed}. ${esc(s.name)} <i>RPI ${s.rpi_rank}</i></span>`).join("")}</div>
      <div class="k">The field of 64</div><table class="tbl field"><tr><th>Line</th><th>Team</th><th>Conf</th><th class="num">RPI</th><th>Bid</th></tr>${ps.selection.field.map((t) => `<tr class="${t.me ? "now" : ""}"><td>${t.national_seed ? "#" + t.national_seed : t.line}</td><td class="nm">${esc(t.name)}</td><td class="muted">${esc(t.conference)}</td><td class="num">${t.rpi_rank}</td><td class="muted">${t.auto ? "auto" : "at large"}</td></tr>`).join("")}</table></div></div>` : "";
    const regs = ps.regionals ? `<div class="hdr-line">Regionals <span class="muted">four-team double elimination at the host's park</span></div><div class="st-grid">${ps.regionals.map((r) => `<div class="panel"><div class="hdr">Regional ${r.n} · ${esc(r.host)} <span class="sub">${r.winner ? "winner: " + esc(r.winner) : ""}</span></div><div class="body"><div class="seeds">${r.teams.map((t) => `<span class="${t.me ? "me" : ""}">${t.seed}. ${esc(t.name)}</span>`).join("")}</div>${byDay(r.games)}</div></div>`).join("")}</div>` : "";
    const sups = ps.supers && (ps.supers.length || ps.super_rows) ? `<div class="panel"><div class="hdr">Super regionals <span class="sub">best of three</span></div><div class="body">${ps.super_rows ? `<div class="seeds">${ps.super_rows.map((s) => `<span>${esc(s.teams[0])} vs ${esc(s.teams[1])} <i>at ${esc(s.host)}</i> → <b>${esc(s.winner)}</b></span>`).join("")}</div>` : ""}${byDay(ps.supers)}</div></div>` : "";
    const cws = ps.cws && ps.cws.length ? `<div class="panel"><div class="hdr">College World Series · Omaha <span class="sub">${ps.champion ? `national champion: ${esc(ps.champion)} over ${esc(ps.runner_up)}` : "in progress"}</span></div><div class="body">${ps.cws_teams ? `<div class="seeds">${ps.cws_teams.map((t) => `<span>${esc(t)}</span>`).join("")}</div>` : ""}${byDay(ps.cws)}</div></div>` : "";
    $("#dyn-main").innerHTML = `<div class="tabs" id="ps-tabs"><button data-t="conf" class="on">Conference tournaments</button><button data-t="sel">Selection Monday</button><button data-t="ncaa">NCAA tournament</button></div>
      <div id="ps-conf"><div class="st-grid">${confs.map(conf).join("")}</div></div>
      <div id="ps-sel" class="hidden">${sel || '<div class="panel"><div class="body muted">The field is announced after the conference tournaments.</div></div>'}</div>
      <div id="ps-ncaa" class="hidden">${regs || '<div class="panel"><div class="body muted">The bracket is set on Selection Monday.</div></div>'}${sups}${cws}</div>`;
    $$("#ps-tabs button").forEach((b) => b.addEventListener("click", () => { $$("#ps-tabs button").forEach((x) => x.classList.toggle("on", x === b)); ["conf", "sel", "ncaa"].forEach((t) => $(`#ps-${t}`).classList.toggle("hidden", t !== b.dataset.t)); }));
    if (ps.stage === "ncaa" || ps.stage === "done") $("#ps-tabs [data-t='ncaa']").click(); else if (ps.stage === "selection") $("#ps-tabs [data-t='sel']").click();
    bindBoxes();
  }

  // ---- end of Year 1: the season summary, then the offseason placeholder ----
  async function renderSummary() {
    const s = await raw(`/api/dynasties/${D.id}/summary`);
    const L = s.leaders, line = (k, who, v) => (who ? `<div><span class="k">${k}</span><b>${esc(who.name)}</b> <span class="muted">${v}</span></div>` : "");
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">Year ${s.year} in review · ${esc(s.team)}</div><div class="body summary">
        <div class="big">${s.record[0]}-${s.record[1]} <span class="muted">(${s.conf_record[0]}-${s.conf_record[1]} conference)</span></div>
        <div class="facts"><div><span class="k">Postseason</span><b>${esc(s.result)}</b></div><div><span class="k">RPI</span><b>${s.rpi_rank ? "#" + s.rpi_rank : "—"}</b></div>${s.conference_champion ? `<div><span class="k">Conference tournament</span><b>champions</b></div>` : ""}<div><span class="k">National champion</span><b>${esc(s.champion || "—")}</b>${s.runner_up ? ` <span class="muted">over ${esc(s.runner_up)}</span>` : ""}</div></div>
        <div class="k">Team leaders</div><div class="leaders">${line("AVG", L.avg, L.avg && L.avg.stats.avg.toFixed(3))}${line("HR", L.hr, L.hr && L.hr.stats.hr)}${line("OPS", L.ops, L.ops && L.ops.stats.ops.toFixed(3))}${line("ERA", L.era, L.era && L.era.stats.era.toFixed(2))}${line("K", L.k, L.k && L.k.stats.k)}</div></div></div>
      <div class="panel offseason"><div class="hdr">Offseason <span class="sub">coming next · not playable yet</span></div><div class="body"><div class="muted">Year ${s.year} ends after Omaha. These phases plug in here, in this order, and lead into Year ${s.year + 1}:</div><ol>${s.offseason.map((x) => `<li>${esc(x)}</li>`).join("")}</ol><div class="row"><button class="btn-ghost" id="to-main">Back to the main screen</button></div></div></div>`;
    $("#to-main").addEventListener("click", () => show("main"));
  }

  function renderSoon() { $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${D.screen}</div><div class="body muted">This screen arrives in a later push.</div></div>`; }

  document.addEventListener("cbs:ready", () => { const id = new URLSearchParams(location.search).get("dyn"); if (id) busy(() => open(id)); });
  window.dyn = { open, id: () => D.id, refresh };
})();
