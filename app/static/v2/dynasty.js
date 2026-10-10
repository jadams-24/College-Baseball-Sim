/* Dynasty mode (2026-10-08): the hub and its screens on top of app/dynasty_api.py. Sims run as background jobs on
   the server; the page polls progress. A game of the user's team opens the manager screen (v2.js) and comes back
   here when it is over. The dynasty is saved on the server after every step and mirrored to this browser. */
(() => {
  "use strict";
  const V = window.v2, $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const { raw, toast, esc, mark, chip, venueLine, setMine, badge, show, busy } = V;
  const LD = window.cbsLoad;
  const dateText = (d, o) => window.cbsDate(d, o);
  const CARD_LABELS = { program_tradition: "Program Tradition", conference_prestige: "Conference Prestige", omaha_contender: "Omaha Contender", academic_prestige: "Academic Prestige", campus_life: "Campus Life", climate: "Climate", money: "Money", facilities: "Facilities", ballpark_atmosphere: "Ballpark Atmosphere", brand_exposure: "Brand Exposure", draft_development: "Draft Development", coach_prestige: "Coach Prestige", coach_stability: "Coach Stability" };
  const CARD_SHORT = { program_tradition: "Trad", conference_prestige: "Conf", omaha_contender: "Omaha", academic_prestige: "Acad", campus_life: "Campus", climate: "Climate", money: "Money", facilities: "Facil", ballpark_atmosphere: "Atmos", brand_exposure: "Brand", draft_development: "Draft", coach_prestige: "Coach", coach_stability: "Stab" };
  const D = { id: null, hub: null, screen: "hub", cache: {}, poll: null };
  const STAGE = { regular: "Regular season", conf: "Conference tournaments", selection: "Selection Monday", ncaa: "NCAA tournament", done: "Season over" };

  // ---- open and refresh ----
  async function open(id, hub) {
    const h = hub ? null : LD.panel({ title: "Loading the dynasty" });
    try { D.id = id; D.hub = hub || (await raw(`/api/dynasties/${id}`)); D.cache = {}; }
    catch (e) { if (h) h.fail(e.message || String(e), () => busy(() => open(id))); else throw e; return; }
    finally { if (h) h.done(); }
    if (D.hub.stage === "pick") { toast("Pick a team first."); return show("main"); }
    show("dyn"); setScreen("hub");
    if (D.hub.running) pollProgress();
  }
  async function refresh() { D.hub = await raw(`/api/dynasties/${D.id}`); D.cache = {}; render(); }
  async function mirror() {
    try { const sv = await raw(`/api/dynasties/${D.id}/save`); await window.cbsMirror.put(D.id, sv.save, sv.meta); } catch (e) { /* a sim may be running */ }
  }
  function setScreen(name) { D.screen = name; render(); }
  // the top bar's tabs group the screens: Hub (and the year in review), Roster (roster, stats), Schedule (schedule, standings, postseason)
  const GROUPS = { hub: ["hub"], roster: ["roster", "stats"], schedule: ["schedule", "standings", "postseason"] };
  const LABEL = { hub: "Hub", roster: "Roster", stats: "Stats", schedule: "Schedule", standings: "Standings", postseason: "Postseason", summary: "Year in review" };
  function tabOf(screen) { for (const [tab, scs] of Object.entries(GROUPS)) if (scs.includes(screen)) return tab; return "hub"; }
  function renderSubnav() {
    const tab = tabOf(D.screen), screens = GROUPS[tab].slice();
    if (tab === "hub" && D.hub.stage === "done") screens.push("summary");
    const el = $("#dyn-subnav");
    el.classList.toggle("hidden", screens.length < 2);
    el.innerHTML = screens.map((sc) => `<button data-screen="${sc}" class="${sc === D.screen ? "on" : ""}">${LABEL[sc]}</button>`).join("");
    $$("#dyn-subnav button").forEach((b) => b.addEventListener("click", () => setScreen(b.dataset.screen)));
  }
  function topbar(where) {
    const h = D.hub, sch = h.school;
    V.setTopbar({ school: h.team, sub: `${h.conference} · ${h.tier.toUpperCase()}${sch ? ` · ${sch.location}` : ""}`, dynasty: true,
                  active: where === "dyn" ? tabOf(D.screen) : null, date: dateText(h.date, { weekday: true }), phase: `Year ${h.year} · ${STAGE[h.stage] || h.stage}`,
                  advance: where === "dyn" && h.stage !== "done" && !h.running });
  }
  function goto(tab) { if (!D.id) return; const target = tab === "hub" ? "hub" : GROUPS[tab] ? GROUPS[tab][0] : "hub"; show("dyn"); if (D.screen !== target) setScreen(target); else { refresh(); } }
  function advance() { if (D.id && !LD.locked()) busy(async () => { if (D.hub.pending) { await playPending($("#tb-advance")); return; } await simTo("game", $("#tb-advance")); }); }

  // ---- the season strip at the top of the hub: record, conference record, RPI rank, week, games ----
  function seasonStrip() {
    const h = D.hub, sch = h.school;
    const f = (k, v) => `<div><span class="k">${k}</span><b class="mono">${v}</b></div>`;
    setMine({ tid: h.tid });
    return `<div class="panel season"><div class="body facts">${mark({ tid: h.tid, name: h.team, abbr: h.team_abbr, engine_name: h.engine_name })}<div class="who"><div class="name">${esc(h.team)}</div><div class="muted">${esc(h.name)}${sch ? ` · ${esc(sch.location)}` : ""} · Year ${h.year}</div></div>${f("Record", `${h.record[0]}-${h.record[1]}`)}${f("Conf", `${h.conf_record[0]}-${h.conf_record[1]}`)}${f("RPI", h.rpi_rank ? "#" + h.rpi_rank : "—")}${f("Week", h.week)}${f("Games", `${h.games_played}/${h.games_total}`)}</div></div>`;
  }

  // ---- sims: background jobs with progress ----
  function pauseFlags() { const s = window.cbsSettings(); return s.autoPause; }
  // what a sim target is doing, for the button and the loading panel ("Advancing to Tue Mar 4" for a day or a week)
  function simTitle(target) {
    const d = D.hub.date;
    if (target === "day") return `Advancing to ${dateText(d + 1, { weekday: true })}`;
    if (target === "week") return `Advancing to ${dateText(d + (7 - (d % 7)), { weekday: true })}`;
    return { game: "Advancing to your next game", regular: "Simming to the end of the regular season", conf: "Simming the conference tournaments",
             selection: "Simming to Selection Monday", end: "Simming to the end of the season" }[target] || "Simming";
  }
  const SIM_LABEL = { game: "Advancing…", day: "Advancing…", week: "Advancing…", regular: "Simming…", conf: "Simming…", selection: "Simming…", end: "Simming…" };
  async function simTo(target, btn) {
    if (LD.locked()) return;
    const pause = pauseFlags();
    const stops = [["weekEnd", "week_end"], ["postseason", "postseason"], ["selection", "selection"]].filter(([k]) => pause[k]).map(([, v]) => v);
    const title = simTitle(target);
    const panel = LD.panel({ title, stop: () => raw(`/api/dynasties/${D.id}/stop`, "POST") });
    LD.simLock(true);
    try {
      await LD.act(btn || $(`#dyn-main [data-simto="${target}"]`), SIM_LABEL[target] || "Simming…", () => raw(`/api/dynasties/${D.id}/sim`, "POST", { target, pause_mine: !!pause.myGames, stops }));
    } catch (e) {
      LD.simLock(false);
      panel.fail(e.message || String(e), () => busy(() => simTo(target)));
      return;
    }
    D.hub.running = true; D.panel = panel; render();
    pollProgress();
  }
  function pollProgress() {
    clearTimeout(D.poll);
    LD.simLock(true);
    if (!D.panel) D.panel = LD.panel({ title: "Simming the D1 world", stop: () => raw(`/api/dynasties/${D.id}/stop`, "POST") });
    let misses = 0;
    const tick = async () => {
      let p;
      try { p = await raw(`/api/dynasties/${D.id}/progress`); misses = 0; }
      catch (e) {
        if (++misses >= 5) { const pn = D.panel; D.panel = null; LD.simLock(false); if (pn) pn.fail("Lost the sim's progress: " + (e.message || e), () => pollProgress()); return; }
        D.poll = setTimeout(tick, 3000); return;
      }
      if (p.running) {
        const bg = p.kind === "background";
        const text = bg ? `The rest of the league's week is simming while you play: ${p.ahead} of ${p.ahead_total} games`
                        : `${p.played} of ${p.total} games · ${dateText(p.date)} · ${STAGE[p.stage] || p.stage}${p.stopping ? " · stopping at the next pause" : ""}`;
        const el = $("#sim-progress");
        if (el) el.innerHTML = `<div class="prog"><i style="width:${bg ? (p.ahead_total ? (100 * p.ahead / p.ahead_total).toFixed(1) : 0) : (p.total ? (100 * p.played / p.total).toFixed(1) : 0)}%"></i></div><div class="muted">${text}</div>`;
        if (D.panel) { if (bg) D.panel.o.stop = null; D.panel.update(bg ? { done: p.ahead, total: p.ahead_total, text } : { done: p.played, total: p.total, text }); }
        D.poll = setTimeout(tick, 1500);
      } else {
        const pn = D.panel; D.panel = null;
        LD.simLock(false);
        if (p.error) { if (pn) pn.fail("The sim stopped: " + p.error, null); else toast("The sim stopped: " + p.error); }
        else if (pn) pn.done();
        D.hub = p.hub; D.cache = {}; render(); mirror();
      }
    };
    tick();
  }

  // ---- the user's game ----
  async function playPending(btn) {
    const ask = window.cbsSettings().askModes || {};
    const modes = Object.fromEntries(Object.keys(ask).filter((k) => ask[k]).map((k) => [k, "ask"]));
    const t = await LD.simAction(btn || $("#play-btn"), "Opening…", { title: "Opening the game", retry: true }, () => raw(`/api/dynasties/${D.id}/game/open`, "POST", { modes }));
    if (t) V.openDynastyGame(t, D.id);
  }
  async function simPending(btn) {
    const h = await LD.simAction(btn || $("#simgame-btn"), "Simming…", { title: "Simming your game", retry: true }, () => raw(`/api/dynasties/${D.id}/game/sim`, "POST"));
    if (h) { D.hub = h; D.cache = {}; render(); mirror(); }
  }
  document.addEventListener("cbs:dyn-finish", () => busy(() => LD.act($("#simbar [data-dyn-finish]"), "Back to the dynasty…", async () => { D.hub = await raw(`/api/dynasties/${D.id}/game/finish`, "POST"); D.cache = {}; show("dyn"); setScreen("hub"); mirror(); })));
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


  // ---- screens ----
  function render() {
    if (!D.hub) return;
    window.cbsCalendar.set(D.hub.calendar);          // this dynasty's year: every date on these screens maps through it
    topbar("dyn");
    renderSubnav();
    const fn = { hub: renderHub, schedule: renderSchedule, standings: renderStandings, stats: renderStats, roster: renderRoster, postseason: renderPostseason, summary: renderSummary }[D.screen] || renderHub;
    const cached = { schedule: false, standings: !!D.cache.standings, stats: !!D.cache.stats, roster: !!D.cache.roster, postseason: false, summary: false, hub: true }[D.screen];
    if (!cached) $("#dyn-main").innerHTML = LD.skeletonPanel(LABEL[D.screen] || "", D.screen === "standings" ? 12 : 14, D.screen === "roster" || D.screen === "stats" ? 8 : 5);
    const run = D.screen;
    Promise.resolve().then(fn).catch((e) => {
      console.error(e);
      if (D.screen === run) $("#dyn-main").innerHTML = LD.errorPanel(e.message || String(e), () => render(), `Couldn't load ${LABEL[run] || "the screen"}`);
    });
  }
  function resultRow(g) {
    const vs = g.side === "home" ? "vs" : "at";
    const opp = g.side === "home" ? g.away_name : g.home_name, oppTid = g.side === "home" ? g.away : g.home;
    const tag = g.stage !== "regular" ? `<span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : g.conf ? `<span class="tag">CONF</span>` : "";
    const box = g.i >= 0 ? `data-box="${g.i}"` : `data-postbox="${g.k}"`;
    return `<tr class="${g.result && g.result[0] === "W" ? "w" : "l"}"><td class="muted date">${dateText(g.date)}</td><td class="nm">${vs} <a class="tlink" data-tid="${oppTid}">${esc(opp)}</a> ${tag}${g.user ? '<span class="tag you">PLAYED</span>' : ""}</td><td class="num">${g.result ? `<span class="pill ${g.result[0] === "W" ? "success" : "loss"}">${g.result}</span>` : ""}${g.inning !== 9 ? ` <span class="muted">(${g.inning})</span>` : ""}${g.run_rule ? ' <span class="muted">RR</span>' : ""}</td><td><button class="btn-ghost" ${box}>Box</button></td></tr>`;
  }
  function renderHub() {
    const h = D.hub, p = h.pending;
    const next = p ? `<div class="panel next"><div class="hdr">Next game <span class="sub">${dateText(p.date)} · ${p.stage === "regular" ? (p.weekend ? "weekend series" : "midweek") : STAGE[p.stage] || p.stage}${p.neutral ? " · neutral site" : ""}</span></div>
        <div class="body"><div class="matchup"><div>${mark({ tid: p.away, name: p.away_name, abbr: p.away_abbr })}<b><a class="tlink" data-tid="${p.away}">${esc(p.away_name)}</a></b><span class="muted">${p.user_side === "away" ? " (you)" : ""}</span></div><div class="at">${p.neutral ? "vs" : "at"}</div><div>${mark({ tid: p.home, name: p.home_name, abbr: p.home_abbr })}<b><a class="tlink" data-tid="${p.home}">${esc(p.home_name)}</a></b><span class="muted">${p.user_side === "home" ? " (you)" : ""}</span></div></div>
        <div class="muted venue-line">${venueLine(p.venue, { neutral: p.neutral, stage: p.stage })}</div>
        ${p.probables ? `<div class="probables">${["away", "home"].map((sd) => p.probables[sd] ? `<div><span class="k">${sd === "away" ? "Away" : "Home"} starter</span><b><a class="plink" data-pid="${p.probables[sd].pid}">${esc(p.probables[sd].name)}</a></b> <span class="muted">${p.probables[sd].role}</span> ${["stuff", "control", "movement", "stamina"].map((k) => badge(k, p.probables[sd].ratings[k])).join(" ")}</div>` : "").join("")}<div class="muted">Probable starters: each AI's pick at first pitch; yours can change in the pregame.</div></div>` : `<div class="muted">Probable starters: set at first pitch.</div>`}
        <div class="row">${h.running && h.job_kind !== "background" ? "" : `<button class="go" id="play-btn">${p.open ? "Back to the game" : "Play"}</button><button id="simgame-btn">Sim game</button>`}<button class="btn-ghost" id="scout-btn" data-tid="${p.user_side === "home" ? p.away : p.home}" title="the opponent's team page">Scout opponent</button></div></div></div>`
      : `<div class="panel next"><div class="hdr">Next game</div><div class="body muted">${h.stage === "done" ? `The season is over. <button class="go" id="to-summary">Year in review</button>` : h.stage === "regular" ? "Sim ahead to reach your next game." : "No game of yours is pending in this stage; sim ahead."}</div></div>`;
    const sims = h.running ? `<div id="sim-progress"></div>` : `<div class="sims">${[["game", "Advance to next game"], ["day", "Advance day"], ["week", "Advance week"], ["regular", "End of regular season"], ["conf", "Conference tournament"], ["selection", "Selection Monday"], ["end", "End of season"]].map(([t, l]) => `<button data-simto="${t}" ${h.stage === "done" ? "disabled" : ""}>${l}</button>`).join("")}</div><div class="muted">Your games ${pauseFlags().myGames ? "pause the sim" : "are played by the AI"}; longer sims also pause ${[["weekEnd", "at each week's end"], ["postseason", "before the postseason"], ["selection", "on Selection Monday"]].filter(([k]) => pauseFlags()[k]).map(([, l]) => l).join(", ") || "nowhere else"} (Settings).</div>`;
    const recent = h.recent.length ? `<table class="tbl">${h.recent.map(resultRow).join("")}</table>` : `<div class="muted">No games yet.</div>`;
    const news = h.news.length ? h.news.map((n) => `<div class="ev"><span class="muted mono">${dateText(n.date)}</span><span>${esc(n.text)}</span></div>`).join("") : `<div class="muted">Nothing yet. News comes from the engine's results only.</div>`;
    const card = h.report_card ? `<div class="panel"><div class="hdr">Report card <span class="sub">${esc(h.school ? h.school.institution : "")}</span></div><div class="body"><div class="card-grades">${Object.entries(h.report_card.grades).map(([k, g]) => window.cbsGradeChip({ label: CARD_LABELS[k] || k, short: CARD_SHORT[k] || k }, g.grade, g.confidence)).join("")}</div><div class="muted">A+ to F, percentiles across D1 (data/schools/report_cards.csv): display and recruiting only, never read by the engine. Omaha Contender is this dynasty's own draw.</div></div></div>` : "";
    $("#dyn-main").innerHTML = `<div class="hub-grid">
      <div class="col">${seasonStrip()}${next}<div class="panel next10"><div class="hdr">Next 10 games <span class="sub">as scheduled · click a row to scout the opponent</span></div><div class="body tight scroll-x" id="next10">${LD.skeleton(10, 9)}</div></div><div class="panel"><div class="hdr">Advance${h.pause ? `<span class="sub"><span class="pill warn">paused</span> ${esc(h.pause.message)}${h.pause.link && h.pause.link !== "hub" ? ` <button class="btn-ghost" data-screen-link="${esc(h.pause.link)}">open</button>` : ""}</span>` : ""}</div><div class="body">${sims}</div></div>
        <div class="panel"><div class="hdr">Recent results</div><div class="body tight scroll-x">${recent}</div></div><div class="panel"><div class="hdr">News</div><div class="body tight">${news}</div></div></div>
      <div class="col side">${card}<div class="panel"><div class="hdr">Standings <span class="sub">${esc(h.conference_full || h.conference)}</span></div><div class="body tight scroll-x" id="hub-standings">${LD.skeleton(8, 4)}</div></div><div class="panel"><div class="hdr">RPI top 25</div><div class="body tight scroll-x" id="hub-rpi">${LD.skeleton(10, 4)}</div></div></div>
    </div>`;
    const pb = $("#play-btn"); if (pb) pb.addEventListener("click", () => busy(() => playPending(pb), { quiet: true }));
    const ts = $("#to-summary"); if (ts) ts.addEventListener("click", () => setScreen("summary"));
    const sb = $("#simgame-btn"); if (sb) sb.addEventListener("click", () => busy(() => simPending(sb), { quiet: true }));
    $$("#dyn-main [data-simto]").forEach((b) => b.addEventListener("click", () => busy(() => simTo(b.dataset.simto, b))));
    if (LD.locked() || h.running) LD.simLock(true);
    $$("#dyn-main [data-screen-link]").forEach((b) => b.addEventListener("click", () => setScreen(b.dataset.screenLink)));
    bindBoxes();
    if (h.running) pollProgress();
    fillStandingsSnippets();
    fillNext10();
  }
  // ---- the "Next 10 games" widget: the next games exactly as scheduled, grouped by series, sortable, nothing that hints at an outcome ----
  const N10_COLS = [["date", "Date", ""], ["site", "Site", ""], ["opp", "Opponent", ""], ["conf", "", ""], ["record", "W-L", "num"], ["rpi", "RPI", "num"],
                    ["rsra", "RS-RA", "num nw-x"], ["avg", "BA", "num nw-x"], ["ops", "OPS", "num nw-x"], ["era", "ERA", "num nw-x"], ["l10", "L10", "num nw-x"],
                    ["off", "Off", "num nw-x"], ["def", "Def", "num nw-x"], ["h2h", "H2H", "num nw-x"], ["sp", "Probable", "nw-x"]];
  const n10 = { sort: "date", dir: 1 };
  const n10key = (r, k) => ({ date: r.date, site: r.side, opp: r.opp.name, conf: r.conf_game ? 0 : 1, record: r.record[0] - r.record[1], rpi: r.rpi_rank,
                              rsra: r.form ? r.form.rs - r.form.ra : null, avg: r.line ? r.line.avg : null, ops: r.line ? r.line.ops : null, era: r.line ? r.line.era : null,
                              l10: r.form ? +r.form.last10.split("-")[0] : null, off: r.ratings.off, def: r.ratings.def, h2h: r.h2h ? r.h2h[0] - r.h2h[1] : null, sp: r.pending ? 0 : 1 }[k]);
  const dash = '<span class="muted">–</span>';
  async function fillNext10() {
    const el = $("#next10");
    if (!el) return;
    let j;
    try { j = await raw(`/api/dynasties/${D.id}/next_games`); }
    catch (e) { el.innerHTML = LD.errorPanel(e.message || String(e), () => fillNext10(), "Couldn't load the next games"); return; }
    D.next10 = j;
    renderNext10();
  }
  function renderNext10() {
    const el = $("#next10"), j = D.next10;
    if (!el || !j) return;
    const rb = (k, v) => badge(k, v).replace(/<span class="k">.*?<\/span>/, "");
    const games = j.rows.filter((r) => r.kind === "game"), notes = j.rows.filter((r) => r.kind !== "game");
    // series groups: consecutive weekend games of one week against one opponent share a band
    let gi = -1, prev = null;
    games.forEach((r) => { const key = r.weekend ? `${r.week}:${r.opp.tid}` : `m${r.i}`; if (key !== prev) { gi += 1; prev = key; } r._g = gi; });
    const sorted = games.slice().sort((a, b) => { const x = n10key(a, n10.sort), y = n10key(b, n10.sort); if (x == null && y == null) return a.date - b.date; if (x == null) return 1; if (y == null) return -1; return (x < y ? -1 : x > y ? 1 : a.date - b.date) * n10.dir; });
    const pend = D.hub.pending && D.hub.pending.probables ? D.hub.pending.probables : null;
    const sp = (r) => { if (!r.pending || !pend) return dash; const theirs = pend[r.side === "home" ? "away" : "home"]; const th = theirs ? (theirs.throws || String(theirs.hand || "").split("/").pop()) : ""; return theirs ? `<a class="plink" data-pid="${theirs.pid}">${esc(theirs.name)}</a> <span class="muted">${th && th !== "–" ? esc(th) + "HP" : ""}</span>` : dash; };
    const row = (r) => `<tr class="n10row g${r._g % 2} ${r.pending ? "next" : ""}" data-tid="${r.opp.tid}" title="${esc(r.opp.name)} · ${esc(r.opp.conference_full)}">
      <td class="date">${r.played && r.i >= 0 ? `<a class="muted" data-box="${r.i}">${dateText(r.date, { weekday: true })}</a>` : `<span class="muted">${dateText(r.date, { weekday: true })}</span>`}</td>
      <td class="site"><b>${r.side === "home" ? "H" : r.neutral ? "N" : "A"}</b><small class="muted" title="${r.venue ? esc(r.venue.text) : ""}">${r.venue ? esc(r.venue.name) : r.neutral ? "neutral site" : ""}</small></td>
      <td class="nm">${chip(r.opp.tid)}<a class="tlink" data-tid="${r.opp.tid}" title="${esc(r.opp.name)}">${esc(r.opp.abbr)}</a><small class="muted">${esc(r.opp.conference)}</small></td>
      <td>${r.conf_game ? '<span class="tag">CONF</span>' : ""}</td>
      <td class="num">${r.record[0]}-${r.record[1]}<small class="muted">${r.conf_record[0]}-${r.conf_record[1]}</small></td>
      <td class="num">${r.rpi_rank || dash}</td>
      <td class="num nw-x">${r.form ? `${r.form.rs.toFixed(1)}-${r.form.ra.toFixed(1)}` : dash}</td>
      <td class="num nw-x">${r.line ? f3(r.line.avg) : dash}</td><td class="num nw-x">${r.line ? f3(r.line.ops) : dash}</td><td class="num nw-x">${r.line && r.line.era != null ? r.line.era.toFixed(2) : dash}</td>
      <td class="num nw-x">${r.form ? `${r.form.last10} <span class="muted">${r.form.streak}</span>` : dash}</td>
      <td class="num nw-x">${rb("off", r.ratings.off)}</td><td class="num nw-x">${rb("def", r.ratings.def)}</td>
      <td class="num nw-x">${r.h2h ? `${r.h2h[0]}-${r.h2h[1]}` : dash}</td>
      <td class="nw-x sp">${sp(r)}</td></tr>`;
    const note = (r) => `<tr class="note"><td colspan="${N10_COLS.length}" class="muted">${esc(r.text)}</td></tr>`;
    el.innerHTML = `<table class="tbl n10"><tr>${N10_COLS.map(([k, l, cls]) => `<th class="${cls} ${k === n10.sort ? "on" : ""}" data-n10sort="${k}" title="sort">${l}${k === n10.sort ? (n10.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr>${sorted.map(row).join("")}${notes.map(note).join("")}</table>`;
    $$("#next10 [data-n10sort]").forEach((th) => th.addEventListener("click", () => { const k = th.dataset.n10sort; if (n10.sort === k) n10.dir = -n10.dir; else { n10.sort = k; n10.dir = k === "rpi" || k === "era" ? 1 : k === "date" ? 1 : -1; } renderNext10(); }));
    $$("#next10 tr.n10row").forEach((tr) => tr.addEventListener("click", (e) => { if (e.target.closest("a, button")) return; if (window.pages) busy(() => window.pages.team(+tr.dataset.tid)); }));
    bindBoxes();
  }
  async function standings() {
    if (D.cache.standings) return D.cache.standings;
    const v = await raw(`/api/dynasties/${D.id}/standings`);          // the cache may have been reset while awaiting: return the value itself
    D.cache.standings = v;
    return v;
  }
  async function fillStandingsSnippets() {
    let st;
    try { st = await standings(); }
    catch (e) { const el = $("#hub-standings"); if (el) el.innerHTML = LD.errorPanel(e.message || String(e), () => fillStandingsSnippets()); const el2 = $("#hub-rpi"); if (el2) el2.innerHTML = ""; return; }
    const rows = st.conferences[st.mine] || [];
    const el = $("#hub-standings");
    if (el) el.innerHTML = `<table class="tbl"><tr><th>Team</th><th class="num">Conf</th><th class="num">All</th><th class="num">RPI</th></tr>${rows.map((r) => `<tr class="${r.me ? "now" : ""}"><td class="nm">${chip(r.tid)}<a class="tlink" data-tid="${r.tid}">${esc(r.name)}</a></td><td class="num">${r.cw}-${r.cl}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi_rank || "—"}</td></tr>`).join("")}</table>`;
    const el2 = $("#hub-rpi");
    if (el2) el2.innerHTML = `<table class="tbl"><tr><th>#</th><th>Team</th><th class="num">W-L</th><th class="num">RPI</th></tr>${st.national.slice(0, 25).map((r) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${r.rank}</td><td class="nm">${chip(r.tid)}<a class="tlink" data-tid="${r.tid}">${esc(r.name)}</a> <span class="muted">${esc(r.conference)}</span></td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi.toFixed(3)}</td></tr>`).join("")}${st.my_rank > 25 ? `<tr class="now"><td class="muted">${st.my_rank}</td><td class="nm">${esc(D.hub.team)}</td><td class="num">${D.hub.record[0]}-${D.hub.record[1]}</td><td></td></tr>` : ""}</table>`;
  }
  async function renderSchedule() {
    const s = await raw(`/api/dynasties/${D.id}/schedule`);
    const rows = s.games.map((g) => {
      const vs = g.side === "home" ? "vs" : "at", opp = g.side === "home" ? g.away_name : g.home_name, oppTid = g.side === "home" ? g.away : g.home;
      const tag = g.stage && g.stage !== "regular" ? `<span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : g.conf ? `<span class="tag">CONF</span>` : "";
      const kind = g.stage && g.stage !== "regular" ? "postseason" : g.weekend ? "weekend" : "midweek";
      const res = g.status === "played" ? `<span class="pill ${g.result[0] === "W" ? "success" : "loss"}">${g.result}</span>${g.inning !== 9 ? ` <span class="muted">(${g.inning})</span>` : ""}${g.run_rule ? ' <span class="muted">RR</span>' : ""}` : g.status === "canceled" ? `<span class="muted">canceled</span>` : g.status === "next" ? `<span class="pill accent">NEXT</span>` : "";
      const box = g.status === "played" ? (g.i != null && g.i >= 0 ? `<button class="btn-ghost" data-box="${g.i}">Box</button>` : `<button class="btn-ghost" data-postbox="${g.k}">Box</button>`) : "";
      return `<tr class="${g.status} ${g.result ? (g.result[0] === "W" ? "w" : "l") : ""}"><td class="muted date">${dateText(g.date)}</td><td class="muted num">W${g.week}</td><td class="muted">${kind}</td><td class="nm">${chip(oppTid)}${vs} <a class="tlink" data-tid="${oppTid}">${esc(opp)}</a> ${tag}${g.user ? '<span class="tag you">PLAYED</span>' : ""}</td><td class="muted venue">${venueLine(g.venue, { bare: true, neutral: g.neutral, stage: g.stage })}</td><td class="num">${res}</td><td>${box}</td></tr>`;
    });
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">Schedule <span class="sub">${s.games.filter((g) => g.status === "played").length} played · weekend series and midweek games · CONF = conference game</span></div><div class="body tight scroll-x"><table class="tbl sched"><tr><th>Date</th><th>Wk</th><th>Slot</th><th>Opponent</th><th>Venue</th><th class="num">Result</th><th></th></tr>${rows.join("")}</table></div></div><div id="box-out"></div>`;
    bindBoxes();
  }
  function boxOut() { return $("#box-out") || (() => { const d = document.createElement("div"); d.id = "box-out"; $("#dyn-main").appendChild(d); return d; })(); }
  async function loadBox(b) {
    const el = boxOut();
    el.innerHTML = `<div class="panel boxp"><div class="hdr">Box score</div><div class="body">${LD.skeleton(10, 6)}</div></div>`;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const g = b.dataset.box != null ? await raw(`/api/dynasties/${D.id}/games/${b.dataset.box}`) : await raw(`/api/dynasties/${D.id}/postgames/${b.dataset.postbox}`);
      showBox(g);
    } catch (e) { el.innerHTML = LD.errorPanel(e.message || String(e), () => loadBox(b), "Couldn't load the box score"); }
  }
  function bindBoxes() {
    $$("#dyn-main [data-box], #dyn-main [data-postbox]").forEach((b) => b.addEventListener("click", () => busy(() => LD.act(b, "Loading…", () => loadBox(b)), { quiet: true })));
  }
  function showBox(g) {
    const b = g.box, cols = ["ab", "r", "h", "rbi", "bb", "k", "hr", "sb", "cs"], pitCols = ["ip", "h", "r", "er", "bb", "k", "pitches"];
    const sum = (rows, k) => rows.reduce((s, r) => s + (r.line[k] || 0), 0);
    const decOf = (r) => (b.decisions ? (b.decisions.W === r.pid ? "W" : b.decisions.L === r.pid ? "L" : b.decisions.SV === r.pid ? "SV" : (b.decisions.HLD || []).includes(r.pid) ? "HLD" : "") : r.line.dec || "");
    const bat = (side) => `<h3>${esc(b.teams[side])} batting</h3><table class="tbl box"><tr><th>Batter</th><th>Pos</th><th>B</th>${cols.map((c) => `<th class="num">${c.toUpperCase()}</th>`).join("")}</tr>${b.batting[side].map((r) => `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a></td><td>${r.pos}</td><td class="muted">${r.bats || "–"}</td>${cols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`).join("")}<tr class="tot"><td>Totals</td><td></td><td></td>${cols.map((c) => `<td class="num">${sum(b.batting[side], c)}</td>`).join("")}</tr></table>`;
    const pit = (side) => `<h3>${esc(b.teams[side])} pitching</h3><table class="tbl box"><tr><th>Pitcher</th><th>T</th>${pitCols.map((c) => `<th class="num">${c === "pitches" ? "P" : c.toUpperCase()}</th>`).join("")}</tr>${b.pitching[side].map((r) => { const dec = decOf(r); return `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a> <span class="muted">${r.role}</span>${dec ? ` <span class="pill ${dec === "L" ? "loss" : "success"}">${dec}</span>` : ""}</td><td class="muted">${r.throws || "–"}</td>${pitCols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`; }).join("")}</table>`;
    const line = g.line ? `<table class="linescore"><tr><th></th>${g.line.away.map((_, i) => `<th>${i + 1}</th>`).join("")}<th class="tot">R</th><th class="tot">H</th><th class="tot">E</th></tr><tr><td class="team">${chip(g.away)}${esc(g.away_name)}</td>${g.line.away.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.ar}</td><td class="tot">${g.hits.away}</td><td class="tot">${g.errors.away}</td></tr><tr><td class="team">${chip(g.home)}${esc(g.home_name)}</td>${g.line.home.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.hr}</td><td class="tot">${g.hits.home}</td><td class="tot">${g.errors.home}</td></tr></table>` : "";
    const el = $("#box-out") || (() => { const d = document.createElement("div"); d.id = "box-out"; $("#dyn-main").appendChild(d); return d; })();
    el.innerHTML = `<div class="panel boxp"><div class="hdr">${esc(g.away_name)} ${g.ar}, ${esc(g.home_name)} ${g.hr} <span class="sub">${dateText(g.date)}${(() => { const v = venueLine(g.venue, { neutral: g.neutral, stage: g.stage }); return v ? ` · ${v}` : ""; })()}${g.inning !== 9 ? ` · ${g.inning} innings` : ""}${g.run_rule ? " · run rule" : ""}${g.user ? " · played on the manager screen" : " · simmed"}</span><button class="btn-ghost" id="box-close">Close</button></div><div class="body">${line}<div class="box-grid"><div>${bat("away")}${pit("away")}</div><div>${bat("home")}${pit("home")}</div></div></div></div>`;
    $("#box-close").addEventListener("click", () => (el.innerHTML = ""));
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  // ---- standings: every conference, and the national RPI top 25 and top 64 ----
  async function renderStandings() {
    const st = await standings();
    const confs = Object.keys(st.conferences).sort((a, b) => (a === st.mine ? -1 : b === st.mine ? 1 : a.localeCompare(b)));
    const table = (rows) => `<table class="tbl"><tr><th>Team</th><th class="num">Conf</th><th class="num">All</th><th class="num">RPI</th></tr>${rows.map((r) => `<tr class="${r.me ? "now" : ""}"><td class="nm">${chip(r.tid)}<a class="tlink" data-tid="${r.tid}">${esc(r.name)}</a></td><td class="num">${r.cw}-${r.cl}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi_rank || "—"}</td></tr>`).join("")}</table>`;
    const nat = (lo, hi) => `<table class="tbl"><tr><th>#</th><th>Team</th><th>Conf</th><th class="num">W-L</th><th class="num">RPI</th></tr>${st.national.slice(lo, hi).map((r) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${r.rank}</td><td class="nm">${chip(r.tid)}<a class="tlink" data-tid="${r.tid}">${esc(r.name)}</a></td><td class="muted">${esc(r.conference)}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi.toFixed(3)}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `<div class="tabs" id="st-tabs"><button data-t="conf" class="on">Conferences</button><button data-t="top25">RPI top 25</button><button data-t="top64">RPI top 64</button></div>
      <div id="st-conf" class="st-grid">${confs.map((c) => `<div class="panel"><div class="hdr">${esc((st.conference_names || {})[c] || c)}${c === st.mine ? '<span class="you-tag">you</span>' : ""}</div><div class="body tight">${table(st.conferences[c])}</div></div>`).join("")}</div>
      <div id="st-top25" class="hidden"><div class="panel"><div class="hdr">RPI top 25 <span class="sub">your rank: ${st.my_rank || "—"}</span></div><div class="body tight">${nat(0, 25)}</div></div></div>
      <div id="st-top64" class="hidden"><div class="panel"><div class="hdr">RPI top 64 <span class="sub">your rank: ${st.my_rank || "—"}</span></div><div class="body tight">${nat(0, 64)}</div></div></div>`;
    $$("#st-tabs button").forEach((b) => b.addEventListener("click", () => { $$("#st-tabs button").forEach((x) => x.classList.toggle("on", x === b)); ["conf", "top25", "top64"].forEach((t) => $(`#st-${t}`).classList.toggle("hidden", t !== b.dataset.t)); }));
  }

  // ---- stats: the team's batting and pitching (sortable), national leaders ----
  const BCOLS = [["g", "G"], ["pa", "PA"], ["ab", "AB"], ["r", "R"], ["h", "H"], ["2b", "2B"], ["3b", "3B"], ["hr", "HR"], ["rbi", "RBI"], ["bb", "BB"], ["hbp", "HBP"], ["k", "K"], ["sb", "SB"], ["cs", "CS"], ["avg", "AVG"], ["obp", "OBP"], ["slg", "SLG"], ["ops", "OPS"]];
  const PCOLS = [["g", "G"], ["gs", "GS"], ["w", "W"], ["l", "L"], ["sv", "SV"], ["hld", "HLD"], ["ip", "IP"], ["h", "H"], ["r", "R"], ["er", "ER"], ["bb", "BB"], ["k", "K"], ["hr", "HR"], ["era", "ERA"], ["whip", "WHIP"], ["k9", "K/9"], ["bb9", "BB/9"]];
  const f3 = (v) => (typeof v === "number" ? v.toFixed(3).replace(/^0\./, ".") : v);
  const RATE = new Set(["avg", "obp", "slg", "ops"]);
  let sortBy = { b: "pa", p: "outs", dir: -1 };
  function statTable(rows, cols, which) {
    const key = sortBy[which] === "ip" ? "outs" : sortBy[which];
    const sorted = rows.slice().sort((a, b) => (a.stats[key] > b.stats[key] ? 1 : a.stats[key] < b.stats[key] ? -1 : 0) * sortBy.dir);
    return `<table class="tbl stats"><tr><th>Name</th><th>Pos</th>${cols.map(([k, l]) => `<th class="num ${sortBy[which] === k ? "on" : ""}" data-sort="${k}" data-which="${which}">${l}</th>`).join("")}</tr>${sorted.map((r) => `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a></td><td>${r.pos}</td>${cols.map(([k]) => `<td class="num">${k === "era" || k === "whip" || k === "k9" || k === "bb9" ? r.stats[k].toFixed(k === "era" || k === "whip" ? 2 : 1) : RATE.has(k) ? f3(r.stats[k]) : r.stats[k]}</td>`).join("")}</tr>`).join("")}</table>`;
  }
  async function renderStats() {
    const stats = D.cache.stats || (await raw(`/api/dynasties/${D.id}/stats`));      // the cache may be reset while awaiting: keep the value itself
    D.cache.stats = stats;
    const { team, leaders } = stats;
    const lead = (title, rows, fmt) => `<div class="panel"><div class="hdr">${title}</div><div class="body tight"><table class="tbl">${rows.length ? rows.map((r, i) => `<tr class="${r.me ? "now" : ""}"><td class="muted">${i + 1}</td><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a> <a class="tlink muted" data-tid="${r.tid}">${esc(r.team)}</a></td><td class="num">${fmt(r.value)}</td></tr>`).join("") : `<tr><td class="muted">no qualified player yet</td></tr>`}</table></div></div>`;
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${esc(team.team)} batting <span class="sub">${team.games} games · tap a column to sort${team.missing && team.missing.length ? ` · not in the engine's accumulators: ${team.missing.join(", ")}` : ""}</span></div><div class="body tight scroll-x">${statTable(team.batting, BCOLS, "b")}</div></div>
      <div class="panel"><div class="hdr">${esc(team.team)} pitching</div><div class="body tight scroll-x">${statTable(team.pitching, PCOLS, "p")}</div></div>
      <div class="hdr-line">National leaders <span class="muted">qualified: ${leaders.floors.batting} (batting), ${leaders.floors.pitching} (pitching)</span></div>
      <div class="st-grid">${lead("Batting average", leaders.batting.avg, f3)}${lead("Home runs", leaders.batting.hr, (v) => v)}${lead("OPS", leaders.batting.ops, f3)}${lead("Hits", leaders.batting.h, (v) => v)}${lead("Runs", leaders.batting.r, (v) => v)}${lead("Runs batted in", leaders.batting.rbi, (v) => v)}${lead("Stolen bases", leaders.batting.sb, (v) => v)}${lead("ERA", leaders.pitching.era, (v) => v.toFixed(2))}${lead("Strikeouts", leaders.pitching.k, (v) => v)}${lead("K/9", leaders.pitching.k9, (v) => v.toFixed(1))}${lead("WHIP", leaders.pitching.whip, (v) => v.toFixed(2))}${lead("Wins", leaders.pitching.w, (v) => v)}${lead("Saves", leaders.pitching.sv, (v) => v)}${lead("Holds", leaders.pitching.hld, (v) => v)}</div>`;
    $$("#dyn-main [data-sort]").forEach((h) => h.addEventListener("click", () => { const w = h.dataset.which; if (sortBy[w] === h.dataset.sort) sortBy.dir = -sortBy.dir; else { sortBy[w] = h.dataset.sort; sortBy.dir = h.dataset.sort === "era" || h.dataset.sort === "whip" || h.dataset.sort === "bb9" ? 1 : -1; } renderStats(); }));
  }

  // ---- roster: ratings, position, B/T, class, the season line, pitchers' rest ----
  async function renderRoster() {
    const r = D.cache.roster || (await raw(`/api/dynasties/${D.id}/roster`));
    D.cache.roster = r;
    const bk = ["contact", "gap", "power", "eye", "avoid_k", "speed", "glove", "arm"], pk = ["stuff", "control", "movement", "stamina", "hold"];
    const bat = `<table class="tbl roster"><tr><th>Pos</th><th>Name</th><th>B/T</th><th>Yr</th>${bk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">AVG</th><th class="num">OBP</th><th class="num">SLG</th><th class="num">HR</th><th class="num">R</th><th class="num">RBI</th><th class="num">SB</th><th class="num">CS</th></tr>${r.batters.map((p) => `<tr><td>${p.pos}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a> <span class="muted">${p.role}</span></td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${bk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${f3(p.stats.avg)}</td><td class="num">${f3(p.stats.obp)}</td><td class="num">${f3(p.stats.slg)}</td><td class="num">${p.stats.hr}</td><td class="num">${p.stats.r}</td><td class="num">${p.stats.rbi}</td><td class="num">${p.stats.sb}</td><td class="num">${p.stats.cs}</td></tr>`).join("")}</table>`;
    const rest = (p) => (p.last_outing ? `${p.last_outing.days_ago === 0 ? "today" : p.last_outing.days_ago === 1 ? "yesterday" : p.last_outing.days_ago + " days ago"} · ${p.last_outing.pitches} pitches` : "no outing yet");
    const pit = `<table class="tbl roster"><tr><th>Role</th><th>Name</th><th>B/T</th><th>Yr</th>${pk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">W-L</th><th class="num">SV</th><th class="num">HLD</th><th class="num">IP</th><th class="num">ERA</th><th class="num">K</th><th>Last outing</th></tr>${r.pitchers.map((p) => `<tr><td>${p.role}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${pk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${p.stats.w}-${p.stats.l}</td><td class="num">${p.stats.sv}</td><td class="num">${p.stats.hld}</td><td class="num">${p.stats.ip}</td><td class="num">${p.stats.era.toFixed(2)}</td><td class="num">${p.stats.k}</td><td class="muted">${rest(p)}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${esc(r.team)} batters <span class="sub">B/T = bats (S for a switch hitter) / throws · class arrives with the engine's roster rules, a dash until then</span></div><div class="body tight scroll-x">${bat}</div></div>
      <div class="panel"><div class="hdr">${esc(r.team)} pitchers <span class="sub">rest: the last outing's date and pitches (the AI's rest rule reads these)</span></div><div class="body tight scroll-x">${pit}</div></div>`;
  }

  // ---- the NCAA tournament as a bracket: 16 regional cards, 8 supers, the two Omaha brackets and the finals ----
  function bkTeam(t, slot) {
    if (!t) return `<div class="bk-team tbd"><span class="seed">${slot || ""}</span><span class="nm muted">TBD</span></div>`;
    return `<div class="bk-team ${t.me ? "me" : ""} ${t.out ? "out" : ""}"><span class="seed">${t.seed || ""}</span><span class="nm">${chip(t.tid)}<a class="tlink" data-tid="${t.tid}">${esc(t.name)}</a>${t.national_seed ? ` <span class="muted">#${t.national_seed}</span>` : ""}${t.host ? ' <span class="tag">HOST</span>' : ""}</span><span class="rec mono">${t.wins != null ? t.wins : `${t.w}-${t.l}`}</span></div>`;
  }
  function bkGame(g) {
    const aw = g.ar > g.hr;
    return `<div class="bk-game ${g.side ? "mine" : ""}"><span class="lbl">${g.label || ""}</span><span class="${aw ? "won" : ""}"><a class="tlink" data-tid="${g.away}">${esc(g.away_abbr || g.away_name)}</a> <b class="mono">${g.ar}</b></span><span class="muted">${g.neutral ? "vs" : "at"}</span><span class="${aw ? "" : "won"}"><a class="tlink" data-tid="${g.home}">${esc(g.home_abbr || g.home_name)}</a> <b class="mono">${g.hr}</b></span>${g.inning !== 9 ? `<span class="muted">(${g.inning})</span>` : ""}<button class="btn-ghost" data-postbox="${g.k}">Box</button></div>`;
  }
  function bkCard(title, sub, teams, games, winner, mine) {
    return `<div class="panel bk ${mine ? "mine" : ""} ${winner ? "done" : ""}"><div class="hdr">${title}${mine ? '<span class="you-tag">you</span>' : ""} <span class="sub">${sub || ""}</span></div>
      <div class="body tight"><div class="bk-teams">${teams.map((t, i) => bkTeam(t, i + 1)).join("")}</div>${games.length ? `<div class="bk-games">${games.map(bkGame).join("")}</div>` : ""}${winner ? `<div class="bk-winner"><span class="k">Winner</span> <a class="tlink" data-tid="${winner.tid}">${esc(winner.name)}</a></div>` : ""}</div></div>`;
  }
  function renderBracket(b) {
    const regs = `<div class="hdr-line">Regionals <span class="muted">16 four-team double-elimination regionals at the national seeds' parks</span></div><div class="bracket-grid">${b.regionals.map((r) => bkCard(`Regional ${r.n}`, `${esc(r.host.name)}${r.venue ? ` · ${esc(r.venue)}` : ""}`, r.teams, r.games, r.winner, r.teams.some((t) => t.me))).join("")}</div>`;
    const sups = `<div class="hdr-line">Super regionals <span class="muted">best of three · regional k against regional 17 − k · at the host's park</span></div><div class="bracket-grid supers">${b.supers.map((s) => bkCard(`Super ${s.n}`, `regionals ${s.regionals[0]} and ${s.regionals[1]}${s.venue ? ` · ${esc(s.venue)}` : ""}`, s.teams, s.games, s.winner, s.teams.some((t) => t && t.me))).join("")}</div>`;
    const cws = `<div class="hdr-line">College World Series · Omaha <span class="muted">two four-team double-elimination brackets, then a best-of-three final · ${esc(b.cws.venue || "Charles Schwab Field Omaha")}</span></div><div class="bracket-grid omaha">${b.cws.brackets.map((k) => bkCard(`Bracket ${k.n}`, `supers ${k.supers.join(", ")}`, k.teams, k.games, k.winner, k.teams.some((t) => t && t.me))).join("")}${bkCard("Finals", "best of three", b.cws.finals.teams, b.cws.finals.games, b.cws.finals.winner, b.cws.finals.teams.some((t) => t && t.me))}</div>`;
    return regs + sups + cws;
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
    const conf = (c) => { const t = ps.conference[c]; return `<div class="panel"><div class="hdr">${esc(t.full || c)} tournament${c === ps.mine_conf ? '<span class="you-tag">you</span>' : ""} <span class="sub">${t.champion_name ? "champion: " + esc(t.champion_name) : t.games.length ? "in progress" : "not started"}</span></div>
      <div class="body"><div class="muted">${esc(t.description)} · ${t.venue ? esc(t.venue) : "Conference tournament"}${t.host ? ` (${esc(t.host.name)} hosts)` : ""}</div><div class="seeds">${t.seeds.map((s) => `<span class="${s.me ? "me" : ""}">${s.seed}. ${esc(s.name)}</span>`).join("")}</div>${byDay(t.games)}</div></div>`; };
    const sel = ps.selection ? `<div class="panel"><div class="hdr">Selection Monday <span class="sub">${ps.selection.in_field ? (ps.selection.my_status.national_seed ? `you are the #${ps.selection.my_status.national_seed} national seed` : `you are in the field: a ${ps.selection.my_status.line} seed${ps.selection.my_status.auto ? " (automatic bid)" : " (at large)"}`) : `not selected · RPI rank ${ps.selection.my_status.rpi_rank || "—"}`}</span></div>
      <div class="body"><div class="k">National seeds (regional hosts)</div><div class="seeds">${ps.selection.national_seeds.map((s) => `<span class="${s.me ? "me" : ""}">${s.seed}. ${esc(s.name)} <i>RPI ${s.rpi_rank}</i></span>`).join("")}</div>
      <div class="k">The field of 64</div><table class="tbl field"><tr><th>Line</th><th>Team</th><th>Conf</th><th class="num">RPI</th><th>Bid</th></tr>${ps.selection.field.map((t) => `<tr class="${t.me ? "now" : ""}"><td>${t.national_seed ? "#" + t.national_seed : t.line}</td><td class="nm">${esc(t.name)}</td><td class="muted">${esc(t.conference)}</td><td class="num">${t.rpi_rank}</td><td class="muted">${t.auto ? "auto" : "at large"}</td></tr>`).join("")}</table></div></div>` : "";
    const regs = ps.regionals ? `<div class="hdr-line">Regionals <span class="muted">four-team double elimination at the host's park</span></div><div class="st-grid">${ps.regionals.map((r) => `<div class="panel"><div class="hdr">Regional ${r.n} · ${esc(r.host)} <span class="sub">${r.winner ? "winner: " + esc(r.winner) : ""}</span></div><div class="body"><div class="seeds">${r.teams.map((t) => `<span class="${t.me ? "me" : ""}">${t.seed}. ${esc(t.name)}</span>`).join("")}</div>${byDay(r.games)}</div></div>`).join("")}</div>` : "";
    const sups = ps.supers && (ps.supers.length || ps.super_rows) ? `<div class="panel"><div class="hdr">Super regionals <span class="sub">best of three</span></div><div class="body">${ps.super_rows ? `<div class="seeds">${ps.super_rows.map((s) => `<span>${esc(s.teams[0])} vs ${esc(s.teams[1])} <i>at ${esc(s.host)}</i> → <b>${esc(s.winner)}</b></span>`).join("")}</div>` : ""}${byDay(ps.supers)}</div></div>` : "";
    const cws = ps.cws && ps.cws.length ? `<div class="panel"><div class="hdr">College World Series · Omaha <span class="sub">${ps.champion ? `national champion: ${esc(ps.champion)} over ${esc(ps.runner_up)}` : "in progress"}</span></div><div class="body">${ps.cws_teams ? `<div class="seeds">${ps.cws_teams.map((t) => `<span>${esc(t)}</span>`).join("")}</div>` : ""}${byDay(ps.cws)}</div></div>` : "";
    $("#dyn-main").innerHTML = `<div class="tabs" id="ps-tabs"><button data-t="conf" class="on">Conference tournaments</button><button data-t="sel">Selection Monday</button><button data-t="ncaa">NCAA tournament</button></div>
      <div id="ps-conf"><div class="st-grid">${confs.map(conf).join("")}</div></div>
      <div id="ps-sel" class="hidden">${sel || '<div class="panel"><div class="body muted">The field is announced after the conference tournaments.</div></div>'}</div>
      <div id="ps-ncaa" class="hidden">${ps.bracket ? renderBracket(ps.bracket) : (regs || '<div class="panel"><div class="body muted">The bracket is set on Selection Monday.</div></div>') + sups + cws}</div>`;
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
  window.cbsCardShort = CARD_SHORT;
  window.dyn = { open, id: () => D.id, refresh, hub: () => D.hub, topbar, goto, advance, showBox: (g) => { if (D.screen !== "schedule" && D.screen !== "hub") setScreen("schedule"); showBox(g); } };
})();
