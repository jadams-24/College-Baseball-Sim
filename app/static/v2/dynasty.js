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
  const GROUPS = { hub: ["hub"], roster: ["roster", "stats"], schedule: ["schedule", "standings", "postseason"], lineup: ["lineup"], draft: ["prospects", "mock", "program"] };
  const LABEL = { hub: "Hub", roster: "Roster", stats: "Stats", schedule: "Schedule", standings: "Standings", postseason: "Postseason", summary: "Year in review", lineup: "Lineup",
                  prospects: "Top 100 prospects", mock: "Mock draft", program: "Your program" };
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
    return `<div class="panel season"><div class="body facts">${mark({ tid: h.tid, name: h.team, abbr: h.team_abbr, engine_name: h.engine_name })}<div class="who"><div class="name">${esc(h.team)}</div><div class="muted">${esc(h.name)}${sch ? ` · ${esc(sch.location)}` : ""} · Year ${h.year}</div></div>${f("Record", `${h.record[0]}-${h.record[1]}`)}${f("Conf", `${h.conf_record[0]}-${h.conf_record[1]}`)}${f("RPI", h.rpi_rank ? "#" + h.rpi_rank : "—")}${f("Week", h.week)}</div></div>`;
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
        // a simple percent to completion (owner request 2026-11-26): no game counts; outside the regular season the
        // job's size is not known ahead, so the panel shows the working spinner with the stage
        const has = p.pct != null, stopping = p.stopping ? " · stopping at the next pause" : "";
        const text = bg ? `The rest of the league's week is simming while you play${has ? `: ${p.pct}% complete` : ""}`
                        : has ? `${p.pct}% complete${stopping}` : `${STAGE[p.stage] || p.stage || "Working"}${stopping}`;
        const el = $("#sim-progress");
        if (el) el.innerHTML = `${has ? `<div class="prog"><i style="width:${p.pct}%"></i></div>` : ""}<div class="muted">${text}</div>`;
        if (D.panel) { if (bg) D.panel.o.stop = null; D.panel.update(has ? { done: p.pct, total: 100, text } : { text }); }
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
    if (h) {
      const seen = new Set((D.hub.recent || []).map((g) => `${g.i}:${g.k}`));
      D.hub = h; D.cache = {}; render(); mirror();
      // the simmed game's final and box score as a pop-up: the result that was not in the recent list before the sim
      const g = (h.recent || []).find((x) => !seen.has(`${x.i}:${x.k}`));
      if (g) {
        try { showBox(g.i != null && g.i >= 0 ? await raw(`/api/dynasties/${D.id}/games/${g.i}`) : await raw(`/api/dynasties/${D.id}/postgames/${g.k}`), true); }
        catch (e) { toast("The game is in; its box score is on the Schedule screen."); }
      }
    }
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
        el.textContent = p.running && p.kind === "background" ? `League: this week's other games ${p.pct != null ? `${p.pct}% simmed` : "simming"}` : p.running ? "League sim running" : "League: this week's other games are in";
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
    const fn = { hub: renderHub, schedule: renderSchedule, standings: renderStandings, stats: renderStats, roster: renderRoster, lineup: renderLineup, postseason: renderPostseason, summary: renderSummary,
                 prospects: renderProspects, mock: renderMock, program: renderProgram }[D.screen] || renderHub;
    const cached = { schedule: false, standings: !!D.cache.standings, stats: !!D.cache.stats, roster: !!D.cache.roster, lineup: !!D.cache.lineup, postseason: false, summary: false, hub: true,
                     prospects: !!D.cache.draft, mock: !!D.cache.draft, program: !!D.cache.draft }[D.screen];
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
  // ---- the Next game card: always the user's next scheduled game, with the advance controls ----
  const ADV = [["day", "Next day"], ["week", "End of week"], ["regular", "End of regular season"], ["conf", "Conference tournament"], ["selection", "Selection Monday"], ["end", "End of season"]];
  function pauseTip() {
    const f = pauseFlags();
    const stops = [["weekEnd", "the end of each week"], ["selection", "Selection Monday"], ["postseason", "the start of the postseason"]].filter(([k]) => f[k]).map(([, l]) => l);
    return `${f.myGames ? "Your games pause the sim before they start" : "The AI plays your games (Settings)"}; longer advances also pause at ${stops.length ? stops.join(", ") : "no other moment"} (Settings).`;
  }
  const rbk = (k, v) => (v == null ? '<span class="muted">–</span>' : badge(k, v));
  function teamSide(t, right) {
    return `<div class="side ${t.me ? "me" : ""} ${right ? "right" : ""}">${mark({ tid: t.tid, name: t.name, abbr: t.abbr })}<div class="tname"><a class="tlink" data-tid="${t.tid}">${esc(t.name)}</a>${t.me ? ' <span class="muted">(you)</span>' : ""}</div>
      <div class="facts mono"><span title="overall record">${t.record[0]}-${t.record[1]}</span><span class="muted" title="conference record">${t.conf_record[0]}-${t.conf_record[1]} ${esc(t.conference)}</span><span title="RPI rank">RPI ${t.rpi_rank ? "#" + t.rpi_rank : "–"}</span></div>
      <div class="rt-row">${rbk("off", t.ratings.off)}${rbk("def", t.ratings.def)}</div></div>`;
  }
  function starterBlock(sp, label) {
    if (!sp) return `<div class="starter"><div class="k">${label}</div><div class="muted">–</div></div>`;
    const st = sp.stats, keys = ["stuff", "control", "movement", "stamina"];
    return `<div class="starter"><div class="k">${label}${sp.projected ? ' <span class="pill warn" title="the next starter in the rotation order; the engine names starters on game day">Projected</span>' : ""}</div>
      <div class="who"><b><a class="plink" data-pid="${sp.pid}">${esc(sp.name)}</a></b> <span class="muted">${sp.throws ? esc(sp.throws) + "HP" : ""} · ${esc(sp.role)}</span></div>
      <div class="mono line">${st.g ? `${st.w}-${st.l} · ${st.era.toFixed(2)} ERA · ${st.ip} IP · ${st.k}/${st.bb} K/BB` : '<span class="muted">no outing yet</span>'}</div>
      <div class="rt-row">${keys.map((k) => rbk(k, sp.ratings[k])).join("")}</div></div>`;
  }
  function nextCard(h) {
    const g = h.next_game, tip = esc(pauseTip());
    const paused = h.pause ? `<span class="pill warn">paused</span> <span class="muted">${esc(h.pause.message)}</span>${h.pause.link && h.pause.link !== "hub" ? ` <button class="btn-ghost" data-screen-link="${esc(h.pause.link)}">open</button>` : ""}` : "";
    const dropdown = `<select id="adv-select" class="adv" title="${tip}"><option value="">Advance to…</option>${ADV.map(([t, l]) => `<option value="${t}">${l}</option>`).join("")}</select>`;
    const progress = h.running && h.job_kind !== "background" ? `<div id="sim-progress"></div>` : "";
    if (!g) {
      const text = h.stage === "done" ? "The season is over." : h.stage === "regular" ? "No game of yours is left on the schedule." : `${STAGE[h.stage] || h.stage}: no game of yours is pending; advance to reach the next one.`;
      return `<div class="panel next"><div class="hdr">Next game <span class="sub">${paused}</span></div><div class="body"><div class="muted">${text}</div>${progress}<div class="row actions">${h.stage === "done" ? `<button class="go" id="to-summary">Year in review</button>` : h.running ? "" : `<button class="go" data-simto="game" title="${tip}">Advance to next game</button>${dropdown}`}</div></div></div>`;
    }
    const when = dateText(g.date, { weekday: true });
    const site = g.neutral ? "N · neutral site" : g.side === "home" ? "H" : "A";
    const venue = g.venue ? esc(g.venue.text) : g.neutral ? "" : "";
    const series = g.stage !== "regular" ? (STAGE[g.stage] || g.stage) : g.series ? `Game ${g.series.game} of ${g.series.of}` : "Midweek game";
    const sub = [when, site, venue, g.conf_game ? '<span class="tag">CONF</span>' : "", series, g.h2h ? `season series ${g.h2h[0]}-${g.h2h[1]}` : ""].filter(Boolean).join(" · ");
    const opp = g.side === "home" ? g.away : g.home;
    const primary = g.pending
      ? (h.running && h.job_kind !== "background" ? "" : `<button class="go" id="play-btn">${g.open ? "Back to the game" : "Play"}</button><button id="simgame-btn">Sim game</button>`)
      : (h.running ? "" : `<button class="go" data-simto="game" title="${tip}">${pauseFlags().myGames ? `Advance to ${when}` : `Sim to ${when} (AI plays)`}</button>`);
    return `<div class="panel next"><div class="hdr">${g.pending ? "Game day" : "Next game"} <span class="sub">${sub}</span>${paused ? `<span class="sub right">${paused}</span>` : ""}</div>
      <div class="body"><div class="teams">${teamSide(g.teams.away, false)}<div class="at">${g.neutral ? "vs" : "at"}</div>${teamSide(g.teams.home, true)}</div>
      <div class="starters">${starterBlock(g.probables.away, "Away starter")}${starterBlock(g.probables.home, "Home starter")}</div>
      ${progress}<div class="row actions">${primary}${h.running ? "" : dropdown}<button class="btn-ghost" id="scout-btn" data-tid="${opp}" title="the opponent's team page">Scout opponent</button></div></div></div>`;
  }
  function renderHub() {
    const h = D.hub;
    const recent = h.recent.length ? `<table class="tbl">${h.recent.map(resultRow).join("")}</table>` : `<div class="muted">No games yet.</div>`;
    const news = h.news.length ? h.news.map((n) => `<div class="ev"><span class="muted mono">${dateText(n.date)}</span><span>${esc(n.text)}</span></div>`).join("") : `<div class="muted">Nothing yet. News comes from the engine's results only.</div>`;
    const card = h.report_card ? `<div class="panel"><div class="hdr">Report card <span class="sub">${esc(h.school ? h.school.institution : "")}</span></div><div class="body"><div class="card-grades">${Object.entries(h.report_card.grades).map(([k, g]) => window.cbsGradeChip({ label: CARD_LABELS[k] || k, short: CARD_SHORT[k] || k }, g.grade, g.confidence)).join("")}</div></div></div>` : "";
    $("#dyn-main").innerHTML = `<div class="hub-grid">
      <div class="col">${seasonStrip()}${nextCard(h)}<div class="panel next10"><div class="hdr">Next 10 games <span class="sub">as scheduled · click a row to scout the opponent</span></div><div class="body tight scroll-x" id="next10">${LD.skeleton(10, 9)}</div></div>
        <div class="panel"><div class="hdr">Recent results</div><div class="body tight scroll-x">${recent}</div></div><div class="panel"><div class="hdr">News</div><div class="body tight">${news}</div></div></div>
      <div class="col side">${card}<div class="panel"><div class="hdr">Standings <span class="sub">${esc(h.conference_full || h.conference)}</span></div><div class="body tight scroll-x" id="hub-standings">${LD.skeleton(8, 4)}</div></div><div class="panel"><div class="hdr">RPI top 25</div><div class="body tight scroll-x" id="hub-rpi">${LD.skeleton(10, 4)}</div></div></div>
    </div>`;
    const pb = $("#play-btn"); if (pb) pb.addEventListener("click", () => busy(() => playPending(pb), { quiet: true }));
    const ts = $("#to-summary"); if (ts) ts.addEventListener("click", () => setScreen("summary"));
    const sb = $("#simgame-btn"); if (sb) sb.addEventListener("click", () => busy(() => simPending(sb), { quiet: true }));
    $$("#dyn-main [data-simto]").forEach((b) => b.addEventListener("click", () => busy(() => simTo(b.dataset.simto, b))));
    const sel = $("#adv-select"); if (sel) sel.addEventListener("change", () => { const t = sel.value; sel.value = ""; if (t && !LD.locked()) busy(() => simTo(t, $("#dyn-main [data-simto]") || null)); });
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
      <td class="site" title="${r.venue ? esc(r.venue.text) : r.neutral ? "neutral site" : ""}"><b>${r.side === "home" ? "H" : r.neutral ? "N" : "A"}</b></td>
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
  function showBox(g, popup) {
    const b = g.box, cols = ["ab", "r", "h", "rbi", "bb", "k", "hr", "sb", "cs"], pitCols = ["ip", "h", "r", "er", "bb", "k", "pitches"];
    const sum = (rows, k) => rows.reduce((s, r) => s + (r.line[k] || 0), 0);
    const decOf = (r) => (b.decisions ? (b.decisions.W === r.pid ? "W" : b.decisions.L === r.pid ? "L" : b.decisions.SV === r.pid ? "SV" : (b.decisions.HLD || []).includes(r.pid) ? "HLD" : "") : r.line.dec || "");
    const bat = (side) => `<h3>${esc(b.teams[side])} batting</h3><table class="tbl box"><tr><th>Batter</th><th>Pos</th><th>B</th>${cols.map((c) => `<th class="num">${c.toUpperCase()}</th>`).join("")}</tr>${b.batting[side].map((r) => `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a></td><td>${r.pos}</td><td class="muted">${r.bats || "–"}</td>${cols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`).join("")}<tr class="tot"><td>Totals</td><td></td><td></td>${cols.map((c) => `<td class="num">${sum(b.batting[side], c)}</td>`).join("")}</tr></table>`;
    const pit = (side) => `<h3>${esc(b.teams[side])} pitching</h3><table class="tbl box"><tr><th>Pitcher</th><th>T</th>${pitCols.map((c) => `<th class="num">${c === "pitches" ? "P" : c.toUpperCase()}</th>`).join("")}</tr>${b.pitching[side].map((r) => { const dec = decOf(r); return `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a> <span class="muted">${r.role}</span>${dec ? ` <span class="pill ${dec === "L" ? "loss" : "success"}">${dec}</span>` : ""}</td><td class="muted">${r.throws || "–"}</td>${pitCols.map((c) => `<td class="num">${r.line[c]}</td>`).join("")}</tr>`; }).join("")}</table>`;
    const line = g.line ? `<table class="linescore"><tr><th></th>${g.line.away.map((_, i) => `<th>${i + 1}</th>`).join("")}<th class="tot">R</th><th class="tot">H</th><th class="tot">E</th></tr><tr><td class="team">${chip(g.away)}${esc(g.away_name)}</td>${g.line.away.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.ar}</td><td class="tot">${g.hits.away}</td><td class="tot">${g.errors.away}</td></tr><tr><td class="team">${chip(g.home)}${esc(g.home_name)}</td>${g.line.home.map((r) => `<td>${r}</td>`).join("")}<td class="tot r">${g.hr}</td><td class="tot">${g.hits.home}</td><td class="tot">${g.errors.home}</td></tr></table>` : "";
    const html = `<div class="panel boxp"><div class="hdr">${esc(g.away_name)} ${g.ar}, ${esc(g.home_name)} ${g.hr} <span class="sub">${dateText(g.date)}${(() => { const v = venueLine(g.venue, { neutral: g.neutral, stage: g.stage }); return v ? ` · ${v}` : ""; })()}${g.inning !== 9 ? ` · ${g.inning} innings` : ""}${g.run_rule ? " · run rule" : ""}${g.user ? " · played on the manager screen" : " · simmed"}</span><button class="btn-ghost" id="box-close">Close</button></div><div class="body">${line}<div class="box-grid"><div>${bat("away")}${pit("away")}</div><div>${bat("home")}${pit("home")}</div></div></div></div>`;
    if (popup) {
      // the pop-up after "Sim game" (owner request 2026-11-26): the final and the box score over the hub
      document.querySelectorAll(".box-shade").forEach((x) => x.remove());
      const sh = document.createElement("div"); sh.className = "dialog-shade box-shade"; sh.setAttribute("role", "dialog"); sh.setAttribute("aria-modal", "true"); sh.setAttribute("aria-label", "Final score and box score");
      const won = g.result && g.result[0] === "W";
      sh.innerHTML = `<div class="box-pop">${g.result ? `<div class="final ${won ? "w" : "l"}"><span class="k">Final</span><b>${esc(g.result)}</b><span class="muted">${g.side === "home" ? "vs" : "at"} ${esc(g.side === "home" ? g.away_name : g.home_name)}</span></div>` : ""}${html}</div>`;
      const shut = () => { sh.remove(); document.removeEventListener("keydown", onKey, true); };
      const onKey = (e) => { if (e.key === "Escape" || e.key === "Enter") { e.preventDefault(); e.stopPropagation(); shut(); } };
      document.addEventListener("keydown", onKey, true);
      sh.addEventListener("mousedown", (e) => { if (e.target === sh) shut(); });
      sh.addEventListener("click", (e) => { if (e.target.closest("#box-close") || e.target.closest("[data-pid]")) shut(); });
      document.body.appendChild(sh);
      const cb = sh.querySelector("#box-close"); if (cb) { cb.textContent = "Continue"; cb.className = "go"; cb.focus(); }
      return;
    }
    const el = $("#box-out") || (() => { const d = document.createElement("div"); d.id = "box-out"; $("#dyn-main").appendChild(d); return d; })();
    el.innerHTML = html;
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
    const riskCell = (p) => (p.risk ? `<td><span class="pill ${{ Low: "success", Medium: "warn", High: "loss" }[p.risk.level] || "plain"}" title="${p.risk.level === "Final year" ? "His five years are up after this season" : `${p.risk.stay}% to return next year on this season's playing time (${p.risk.playing_time}). If he leaves: ${p.risk.reason}`}">${p.risk.level}</span></td>` : `<td class="muted">–</td>`);
    const devCells = (p) => {
      const d = p.dev;
      if (!d) return `<td class="muted">–</td><td class="muted">–</td>`;
      const nm = (k) => V.RATING[k][0];
      const lastTip = d.last ? Object.keys(d.last).map((k) => `${nm(k)} ${d.last[k] > 0 ? "+" : ""}${d.last[k]}`).join(", ") : "No offseason with this program yet";
      const potTip = Object.keys(d.pot).map((k) => `${nm(k)} ${p.ratings[k]} now, ${d.pot[k][0]}–${d.pot[k][1]} projected`).join(" · ");
      const chg = d.last_total == null ? `<span class="muted">new</span>` : `<span class="${d.last_total >= 1 ? "up" : d.last_total <= -1 ? "down" : "muted"}">${d.last_total > 0 ? "+" : ""}${Math.round(d.last_total)}</span>`;
      return `<td class="ctr" title="Last offseason: ${lastTip}">${chg}</td><td title="${potTip}"><span class="pill ${{ High: "success", Medium: "warn" }[d.level] || "plain"}">${d.level}</span></td>`;
    };
    const bat = `<table class="tbl roster"><tr><th>Pos</th><th>Name</th><th>B/T</th><th>Yr</th><th>Risk</th><th title="Rating points gained or lost last offseason">Chg</th><th title="How much he is projected to improve before he leaves">Upside</th>${bk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">AVG</th><th class="num">OBP</th><th class="num">SLG</th><th class="num">HR</th><th class="num">R</th><th class="num">RBI</th><th class="num">SB</th><th class="num">CS</th></tr>${r.batters.map((p) => `<tr><td>${p.pos}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a> <span class="muted">${p.role}</span></td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${riskCell(p)}${devCells(p)}${bk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${f3(p.stats.avg)}</td><td class="num">${f3(p.stats.obp)}</td><td class="num">${f3(p.stats.slg)}</td><td class="num">${p.stats.hr}</td><td class="num">${p.stats.r}</td><td class="num">${p.stats.rbi}</td><td class="num">${p.stats.sb}</td><td class="num">${p.stats.cs}</td></tr>`).join("")}</table>`;
    const rest = (p) => (p.last_outing ? `${p.last_outing.days_ago === 0 ? "today" : p.last_outing.days_ago === 1 ? "yesterday" : p.last_outing.days_ago + " days ago"} · ${p.last_outing.pitches} pitches` : "no outing yet");
    const pit = `<table class="tbl roster"><tr><th>Role</th><th>Name</th><th>B/T</th><th>Yr</th><th>Risk</th><th title="Rating points gained or lost last offseason">Chg</th><th title="How much he is projected to improve before he leaves">Upside</th>${pk.map((k) => `<th>${V.RATING[k][0]}</th>`).join("")}<th class="num">W-L</th><th class="num">SV</th><th class="num">HLD</th><th class="num">IP</th><th class="num">ERA</th><th class="num">K</th><th>Last outing</th></tr>${r.pitchers.map((p) => `<tr><td>${p.role}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td class="muted">${p.hand}</td><td class="muted">${p.year}</td>${riskCell(p)}${devCells(p)}${pk.map((k) => `<td>${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("")}<td class="num">${p.stats.w}-${p.stats.l}</td><td class="num">${p.stats.sv}</td><td class="num">${p.stats.hld}</td><td class="num">${p.stats.ip}</td><td class="num">${p.stats.era.toFixed(2)}</td><td class="num">${p.stats.k}</td><td class="muted">${rest(p)}</td></tr>`).join("")}</table>`;
    const off = D.hub.offseason && D.hub.offseason.year === D.hub.year ? D.hub.offseason : null;
    const mv = (x) => `<tr><td>${x[2]}</td><td class="nm">${esc(x[1])}</td><td class="muted">${{ regular: "regular", bench: "bench", sp_weekend: "weekend starter", sp_midweek: "midweek starter", rp: "reliever" }[x[3]] || x[3]}</td><td>${(x[4] || "P").toUpperCase()}</td>${x[5] ? `<td class="muted">${esc(x[5])}</td>` : ""}</tr>`;
    const offPanel = off ? `<div class="panel"><div class="hdr">Year ${off.year} offseason <span class="sub">${off.left.length} left · ${off.arrived.length} arrived${off.persuaded ? ` · ${off.persuaded} persuaded to stay` : ""} · class shown as of each list (departures: last season's class)</span></div><div class="body tight"><div class="off-grid"><div><h3>Departures</h3><table class="tbl"><tr><th>Class</th><th>Name</th><th>Role</th><th>Pos</th><th>Reason</th></tr>${off.left.map(mv).join("")}</table></div><div><h3>Newcomers</h3><table class="tbl"><tr><th>Class</th><th>Name</th><th>Role</th><th>Pos</th></tr>${off.arrived.map(mv).join("")}</table></div></div></div></div>` : "";
    $("#dyn-main").innerHTML = `${offPanel}<div class="panel"><div class="hdr">${esc(r.team)} batters <span class="sub">B/T = bats (S for a switch hitter) / throws · Yr = class on the five-year clock (Fr, So, Jr, Sr, 5th) · Risk = risk of leaving after the season, from his class and playing time (hover for the odds and the reason) · Chg = rating points gained last offseason · Upside = projected improvement before he leaves (hover for each rating's range)</span></div><div class="body tight scroll-x">${bat}</div></div>
      <div class="panel"><div class="hdr">${esc(r.team)} pitchers <span class="sub">rest: the last outing's date and pitches (the AI's rest rule reads these)</span></div><div class="body tight scroll-x">${pit}</div></div>`;
  }

  // ---- the Lineup tab (owner request 2026-11-26): the preferred starting nine in batting order. Used when the AI
  // plays the user's games (Sim game, longer sims) and prefilled on the manager screen. Click two players to swap
  // them (order or bench), or move a batter up and down; every change saves. ----
  const LU = { sel: null };
  async function saveLineup(pids) {
    const r = await raw(`/api/dynasties/${D.id}/lineup`, "POST", { pids });
    D.cache.lineup = r; LU.sel = null; renderLineup();
  }
  async function renderLineup() {
    const r = D.cache.lineup || (await raw(`/api/dynasties/${D.id}/lineup`));
    D.cache.lineup = r;
    const by = Object.fromEntries(r.batters.map((p) => [p.pid, p]));
    const rk = ["contact", "gap", "power", "eye", "avoid_k", "speed", "glove"];
    const rate = (p) => rk.map((k) => `<td class="ctr">${p.ratings[k] == null ? '<span class="muted">–</span>' : badge(k, p.ratings[k]).replace(/<span class="k">.*?<\/span>/, "")}</td>`).join("");
    // the next opponent's probable starter: his throwing hand marks who has the platoon edge (a batter hitting from
    // the opposite side; a switch hitter always), the same rule the manager screen's matchup banner shows
    const nx = r.next, sp = nx && nx.starter, th = sp && sp.throws ? sp.throws : null;
    const edge = (p) => { if (!th) return ""; const b = (p.hand || "").split("/")[0]; return `<td class="ctr">${b && (b === "S" || b !== th) ? '<span class="pill success">Edge</span>' : '<span class="muted">–</span>'}</td>`; };
    const cells = (p) => `<td>${p.pos}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td class="muted">${p.hand}</td><td class="muted">${p.year || "–"}</td>${edge(p)}${rate(p)}<td class="num">${f3(p.stats.avg)}</td><td class="num">${p.stats.hr}</td><td class="num">${p.stats.rbi}</td>`;
    const head = `<th>Pos</th><th>Name</th><th>B/T</th><th>Yr</th>${th ? `<th class="ctr" title="Platoon edge against the probable starter: the batter hits from the opposite side (a switch hitter always does)">vs ${th}HP</th>` : ""}${rk.map((k) => `<th class="ctr">${V.RATING[k][0]}</th>`).join("")}<th class="num">AVG</th><th class="num">HR</th><th class="num">RBI</th>`;
    const order = r.lineup.map((pid, i) => `<tr class="pickable ${LU.sel === pid ? "sel" : ""}" data-lu="${pid}"><td class="slot num">${i + 1}</td>${cells(by[pid])}<td class="act"><button class="btn-ghost" data-up="${i}" ${i === 0 ? "disabled" : ""}>Up</button> <button class="btn-ghost" data-down="${i}" ${i === 8 ? "disabled" : ""}>Down</button></td></tr>`).join("");
    const bench = r.batters.filter((p) => !r.lineup.includes(p.pid)).map((p) => `<tr class="pickable ${LU.sel === p.pid ? "sel" : ""}" data-lu="${p.pid}">${cells(p)}</tr>`).join("");
    // the nine's positions: a note when a field position has nobody or two men (information; the choice is the user's)
    const FIELD = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"], count = {};
    r.lineup.forEach((pid) => { const k = by[pid].pos; count[k] = (count[k] || 0) + 1; });
    const missing = FIELD.filter((k) => !count[k]), twice = Object.keys(count).filter((k) => count[k] > 1);
    const posNote = missing.length || twice.length ? `<span class="pill warn">${missing.length ? `No ${missing.join(", ")}` : ""}${missing.length && twice.length ? " · " : ""}${twice.length ? `Two at ${twice.join(", ")}` : ""}</span>` : "";
    const pr = (k) => (sp.ratings[k] == null ? "" : badge(k, sp.ratings[k]));
    const nextCard = nx ? `<div class="panel lu-next"><div class="hdr">Next game <span class="sub">${dateText(nx.date, { weekday: true })}${nx.series ? ` · game ${nx.series.game} of ${nx.series.of}` : ""}${nx.conf_game ? " · conference" : ""}</span></div>
        <div class="body"><div class="opp"><span class="k">${nx.side === "home" ? "vs" : "at"}</span>${chip(nx.opp_tid)}<a class="tlink" data-tid="${nx.opp_tid}">${esc(nx.opp.name)}</a><span class="muted">${nx.opp.record[0]}-${nx.opp.record[1]}${nx.opp.rpi_rank ? ` · RPI #${nx.opp.rpi_rank}` : ""}</span></div>
          ${sp ? `<div class="sp"><span class="k">${sp.projected ? "Projected starter" : "Probable starter"}</span><a class="plink" data-pid="${sp.pid}">${esc(sp.name)}</a><span class="pill ${sp.throws === "L" ? "warn" : "plain"}">${sp.throws === "L" ? "Left-hander" : sp.throws === "R" ? "Right-hander" : "Throws –"}</span>
            <span class="stat">${sp.stats.w}-${sp.stats.l}</span><span class="muted">W-L</span><span class="stat">${sp.stats.g ? Number(sp.stats.era).toFixed(2) : "–"}</span><span class="muted">ERA</span><span class="stat">${sp.stats.ip}</span><span class="muted">IP</span>
            <span class="chips">${["stuff", "control", "movement", "stamina"].map(pr).join(" ")}</span></div>
            <div class="muted">${sp.projected ? "Projected from their rotation order; their coach names his starter on game day and it can change. " : "Their coach's pick for this game. "}Edge marks your batters who hit from the opposite side of his throwing hand.</div>`
          : `<div class="muted">No probable starter is known yet.</div>`}</div></div>` : "";
    $("#dyn-main").innerHTML = `${nextCard}<div class="lu-grid"><div class="panel"><div class="hdr">Batting order <span class="sub">${r.custom ? "your lineup" : "the coach's everyday nine (the AI rests players game to game)"}</span></div>
        <div class="body lu-note"><span class="pill ${r.custom ? "accent" : "plain"}">${r.custom ? "Your lineup" : "Coach's lineup"}</span> ${posNote}<span class="muted">${LU.sel != null ? `Now click the player to swap with ${esc(by[LU.sel].name)}.` : "Click a player, then another player (in the order or on the bench) to swap them."}</span>${r.custom ? '<button class="btn-ghost" id="lu-reset">Give the lineup back to the coach</button>' : ""}</div>
        <div class="body tight scroll-x"><table class="tbl lu"><tr><th class="num">#</th>${head}<th></th></tr>${order}</table></div></div>
      <div class="panel"><div class="hdr">Bench <span class="sub">${r.batters.length - 9} batters</span></div><div class="body tight scroll-x"><table class="tbl lu"><tr>${head}</tr>${bench}</table></div>
        <div class="body muted">Your lineup starts every game the AI plays for you (Sim game and longer sims) and is prefilled when you play on the manager screen, where you can still change it for that game.</div></div></div>`;
    const swap = (a, b) => {
      const l = r.lineup.slice(), ia = l.indexOf(a), ib = l.indexOf(b);
      if (ia < 0 && ib < 0) { LU.sel = b; return renderLineup(); }           // two bench players: the second becomes the selection
      if (ia >= 0 && ib >= 0) { l[ia] = b; l[ib] = a; } else if (ia >= 0) l[ia] = b; else l[ib] = a;
      busy(() => saveLineup(l));
    };
    $$("#dyn-main tr[data-lu]").forEach((tr) => tr.addEventListener("click", (e) => {
      if (e.target.closest("button, a")) return;
      const pid = +tr.dataset.lu;
      if (LU.sel == null) { LU.sel = pid; renderLineup(); } else if (LU.sel === pid) { LU.sel = null; renderLineup(); } else swap(LU.sel, pid);
    }));
    const move = (i, d) => { const l = r.lineup.slice(); [l[i], l[i + d]] = [l[i + d], l[i]]; busy(() => saveLineup(l)); };
    $$("#dyn-main [data-up]").forEach((b) => b.addEventListener("click", () => move(+b.dataset.up, -1)));
    $$("#dyn-main [data-down]").forEach((b) => b.addEventListener("click", () => move(+b.dataset.down, 1)));
    const rs = $("#lu-reset"); if (rs) rs.addEventListener("click", () => busy(() => saveLineup(null)));
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

  // ---- the Draft tab (display only, app/prospects.py): the Top 100 board, the Round 1 mock, the user's program ----
  async function draftData() {
    const v = D.cache.draft || (await raw(`/api/dynasties/${D.id}/draft`));
    D.cache.draft = v;
    return v;
  }
  const dfilter = { group: "", conf: "", tier: "" };
  const draftBanner = (j) => `<div class="banner-note">${esc(j.banner)}</div>`;
  const change = (c) => (c === null ? '<span class="muted">–</span>' : c === "new" ? '<span class="pill accent">NEW</span>' : c > 0 ? `<span class="up">▲${c}</span>` : c < 0 ? `<span class="down">▼${-c}</span>` : '<span class="muted">·</span>');
  const nameCell = (r) => `<a class="plink" data-pid="${r.pid}">${esc(r.name)}</a> <span class="muted">${r.pos} · ${esc(r.hand)}</span>`;
  const schoolCell = (r) => `${chip(r.tid)}<a class="tlink" data-tid="${r.tid}" title="${esc(r.school)}">${esc(r.abbr)}</a> <span class="muted">${esc(r.conference)}</span>`;
  const rb = (k, v) => (v == null ? '<span class="muted">–</span>' : badge(k, v).replace(/<span class="k">.*?<\/span>/, `<span class="k">${V.RATING[k] ? V.RATING[k][0] : k}</span>`));
  const lineCell = (r) => (r.line ? (r.side === "bat" ? `${f3(r.line.avg)}/${f3(r.line.obp)}/${f3(r.line.slg)} · ${r.line.hr} HR` : `${r.line.era.toFixed(2)} ERA · ${r.line.ip} IP · ${r.line.k}-${r.line.bb} K-BB`) : '<span class="muted">– no games yet</span>');
  async function renderProspects() {
    const j = await draftData();
    const confs = Array.from(new Set(j.board.map((r) => r.conference))).sort();
    const rows = j.board.filter((r) => (!dfilter.group || r.group === dfilter.group) && (!dfilter.conf || r.conference === dfilter.conf) && (!dfilter.tier || r.tier === dfilter.tier));
    const table = `<table class="tbl board"><tr><th class="num">#</th><th>Wk</th><th>Player</th><th>School</th><th>Key ratings</th><th>Season</th><th class="num" title="${esc(j.unit.bat)}; ${esc(j.unit.pit)}">Value</th></tr>${rows.map((r) => `<tr class="${r.mine ? "now" : ""}"><td class="num">${r.rank}</td><td>${change(r.change)}</td><td class="nm">${nameCell(r)}</td><td class="nm">${schoolCell(r)}</td><td class="kr">${r.key_ratings.map(([k, v]) => rb(k, v)).join("")}</td><td class="mono line">${lineCell(r)}</td><td class="num" title="${r.side === "bat" ? esc(j.unit.bat) : esc(j.unit.pit)}">${r.value > 0 ? "+" : ""}${r.value.toFixed(1)}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `${draftBanner(j)}<div class="panel"><div class="hdr">Top 100 prospects <span class="sub">week ${j.week} · hitters: ${esc(j.unit.bat)} · pitchers: ${esc(j.unit.pit)} · ranks update weekly${j.prev_week ? ` · change since week ${j.prev_week}` : ""}</span></div>
      <div class="body row filters"><select id="df-group"><option value="">every position</option>${["C", "IF", "OF", "DH", "SP", "RP"].map((g) => `<option value="${g}" ${dfilter.group === g ? "selected" : ""}>${g}</option>`).join("")}</select>
        <select id="df-conf"><option value="">every conference</option>${confs.map((c) => `<option value="${esc(c)}" ${dfilter.conf === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
        <select id="df-tier"><option value="">every tier</option>${["p4", "mid", "low"].map((t) => `<option value="${t}" ${dfilter.tier === t ? "selected" : ""}>${t.toUpperCase()}</option>`).join("")}</select>
        <span class="muted">${rows.length} of ${j.board.length} · your players highlighted</span></div>
      <div class="body tight scroll-x">${rows.length ? table : '<div class="muted">No prospect matches.</div>'}</div></div>`;
    ["group", "conf", "tier"].forEach((k) => $(`#df-${k}`).addEventListener("change", (e) => { dfilter[k] = e.target.value; renderProspects(); }));
  }
  async function renderMock() {
    const j = await draftData(), m = j.mock;
    const table = `<table class="tbl mock"><tr><th class="num">Pick</th><th>Round</th><th>Team</th><th>Player</th><th>School</th><th class="num" title="board rank">Board</th></tr>${m.picks.map((p) => `<tr class="${p.mine ? "now" : ""}"><td class="num">${p.pick}</td><td class="muted">${esc(p.round)}</td><td><b>${esc(p.team)}</b>${p.note ? ` <span class="muted" title="${esc(p.note)}">*</span>` : ""}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a> <span class="muted">${p.pos}</span></td><td class="nm">${chip(p.tid)}<a class="tlink" data-tid="${p.tid}">${esc(p.school)}</a></td><td class="num">${p.board_rank}</td></tr>`).join("")}</table>`;
    $("#dyn-main").innerHTML = `${draftBanner(j)}<div class="panel"><div class="hdr">${esc(m.label)} <span class="sub">week ${j.week} · refreshes weekly · ${esc(m.randomness)}</span></div>
      <div class="body muted">Round 1 of the 2025 MLB draft order (the dynasty's season) with the Prospect Promotion Incentive, compensatory and Competitive Balance Round A picks: ${m.slots} slots. Source: <a href="${esc(m.source)}" target="_blank" rel="noopener">Wikipedia, 2025 Major League Baseball draft</a> (fetched ${esc(m.fetch_date)}); real MLB team names only. * = a traded or compensation pick (hover).</div>
      <div class="body tight scroll-x">${table}</div></div>`;
  }
  async function renderProgram() {
    const j = await draftData(), pr = j.program;
    const mine = pr.players.length ? `<table class="tbl board"><tr><th class="num">#</th><th>Player</th><th>Key ratings</th><th>Season</th><th>Projected round</th></tr>${pr.players.map((r) => `<tr><td class="num">${r.rank}</td><td class="nm">${nameCell(r)}</td><td class="kr">${r.key_ratings.map(([k, v]) => rb(k, v)).join("")}</td><td class="mono line">${lineCell(r)}</td><td>${esc(r.round_range)}</td></tr>`).join("")}</table>` : `<div class="muted">None of your players is in the Top 100 this week.</div>`;
    $("#dyn-main").innerHTML = `${draftBanner(j)}<div class="hub-grid"><div class="col">
      <div class="panel"><div class="hdr">Your players in the Top 100 <span class="sub">week ${j.week} · projected round range from the board rank</span></div><div class="body tight scroll-x">${mine}</div></div>
      <div class="panel"><div class="hdr">Draft history</div><div class="body muted">${esc(pr.history_note)}</div></div></div>
      <div class="col side"><div class="panel tile locked"><div class="hdr">Draft day</div><div class="body muted">${esc(j.live.text)}</div></div></div></div>`;
  }

  // ---- the end of a year: the season summary, then the offseason (Phase 8: the turnover into the next year) ----
  async function renderSummary() {
    const s = await raw(`/api/dynasties/${D.id}/summary`);
    let lv = null;
    if (s.can_advance) { try { lv = await raw(`/api/dynasties/${D.id}/leaving`); } catch (e) { lv = null; } }
    const lvLine = (p) => (p.side === "bat" ? `${p.line.pa} PA · ${p.line.avg.toFixed(3).replace(/^0/, "")} · ${p.line.hr} HR` : `${p.line.ip} IP · ${p.line.era.toFixed(2)} ERA`);
    const lvAct = (p) => (p.status === "staying" ? `<span class="pill success">Staying</span>` : p.status === "refused" ? `<span class="pill loss">Said no</span>` : p.status === "final" ? `<span class="muted">five years are up</span>`
      : `<button class="btn-sm" data-ask="${p.pid}" ${p.can_ask ? "" : "disabled"}>Persuade</button>`);
    const lvPanel = lv ? `<div class="panel leaving"><div class="hdr">Players leaving <span class="sub">${lv.players.filter((p) => p.status !== "staying").length} of ${lv.roster} leaving · ${lv.returning} returning · persuasion attempts left: <b>${lv.attempts_left} of ${lv.attempts}</b> · one per player</span></div><div class="body tight scroll-x">
        ${lv.players.length ? `<table class="tbl"><tr><th>Yr</th><th>Name</th><th>Pos</th><th>Role</th><th>This season</th><th>Reason</th><th class="num">Chance to stay</th><th></th></tr>${lv.players.map((p) => `<tr class="${p.status === "staying" ? "now" : ""}"><td>${p.year}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td>${p.pos}</td><td class="muted">${p.role}</td><td class="muted">${lvLine(p)}</td><td>${esc(p.reason)}</td><td class="num">${p.status === "final" ? "–" : p.chance + "%"}</td><td>${lvAct(p)}</td></tr>`).join("")}</table>` : `<div class="body muted">Everyone is coming back.</div>`}
        <div class="body muted">Who leaves follows real return rates by class and playing time. An attempt works with the chance shown and is final either way. More attempts (up to ${lv.attempts_max}) will come with coaching attributes.</div></div></div>` : "";
    const L = s.leaders, line = (k, who, v) => (who ? `<div><span class="k">${k}</span><b>${esc(who.name)}</b> <span class="muted">${v}</span></div>` : "");
    $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">Year ${s.year} in review · ${esc(s.team)}</div><div class="body summary">
        <div class="big">${s.record[0]}-${s.record[1]} <span class="muted">(${s.conf_record[0]}-${s.conf_record[1]} conference)</span></div>
        <div class="facts"><div><span class="k">Postseason</span><b>${esc(s.result)}</b></div><div><span class="k">RPI</span><b>${s.rpi_rank ? "#" + s.rpi_rank : "—"}</b></div>${s.conference_champion ? `<div><span class="k">Conference tournament</span><b>champions</b></div>` : ""}<div><span class="k">National champion</span><b>${esc(s.champion || "—")}</b>${s.runner_up ? ` <span class="muted">over ${esc(s.runner_up)}</span>` : ""}</div></div>
        <div class="k">Team leaders</div><div class="leaders">${line("AVG", L.avg, L.avg && L.avg.stats.avg.toFixed(3))}${line("HR", L.hr, L.hr && L.hr.stats.hr)}${line("OPS", L.ops, L.ops && L.ops.stats.ops.toFixed(3))}${line("ERA", L.era, L.era && L.era.stats.era.toFixed(2))}${line("K", L.k, L.k && L.k.stats.k)}</div></div></div>
      ${lvPanel}
      <div class="panel offseason"><div class="hdr">Offseason <span class="sub">into Year ${s.next_year}</span></div><div class="body">
        ${s.can_advance ? `<div class="muted">Advancing runs the roster turnover: every player who stays moves up a class on the five-year clock, the players listed above leave, and newcomers take their places. Returning players keep their ratings for now (development is the next build). Still to come here, in this order: ${s.offseason.map(esc).join(", ")}.</div>
          <div class="row"><button class="go" id="next-year">Advance to Year ${s.next_year}</button><button class="btn-ghost" id="to-main">Back to the main screen</button></div>`
        : `<div class="muted">${s.done ? "This dynasty was started before class years existed, so it ends here. Start a new dynasty to play on into Year 2." : "The offseason opens when the season is over."}</div><div class="row"><button class="btn-ghost" id="to-main">Back to the main screen</button></div>`}</div></div>
      ${s.history && s.history.length ? `<div class="panel"><div class="hdr">Program history</div><div class="body tight"><table class="tbl"><tr><th>Year</th><th class="num">Record</th><th class="num">Conf</th><th class="num">RPI</th><th>Postseason</th><th>National champion</th></tr>${s.history.map((y) => `<tr><td class="num">${y.year}</td><td class="num">${y.record[0]}-${y.record[1]}</td><td class="num">${y.conf_record[0]}-${y.conf_record[1]}</td><td class="num">${y.rpi_rank ? "#" + y.rpi_rank : "–"}</td><td>${esc(y.result)}</td><td>${esc(y.champion || "–")}</td></tr>`).join("")}</table></div></div>` : ""}`;
    const ny = $("#next-year");
    if (ny) ny.addEventListener("click", () => busy(async () => {
      if (!(await window.cbsDialog.confirm({ title: "Offseason", text: `Advance to Year ${s.next_year}?`, detail: "Players move up a class, some leave and newcomers arrive. This season's games and stats are closed out.", ok: `Start Year ${s.next_year}` }))) return;
      const h = await LD.simAction(ny, "Running the offseason…", { title: `Offseason: into Year ${s.next_year}`, sub: "Roster turnover for all 307 programs, then the new schedule." }, () => raw(`/api/dynasties/${D.id}/next_year`, "POST"));
      if (h) { D.hub = h; D.cache = {}; LU.sel = null; setScreen("roster"); mirror(); }
    }, { quiet: true }));
    $$("#dyn-main [data-ask]").forEach((b) => b.addEventListener("click", () => busy(async () => {
      const p = lv.players.find((x) => x.pid === +b.dataset.ask);
      if (!(await window.cbsDialog.confirm({ title: "Persuade to stay", text: `Ask ${p.name} to stay?`, detail: `${p.chance}% chance. It uses one of your ${lv.attempts_left} remaining attempts, and you cannot ask him twice.`, ok: "Ask him" }))) return;
      const r = await raw(`/api/dynasties/${D.id}/persuade`, "POST", { pid: p.pid });
      await window.cbsDialog.confirm({ title: r.stayed ? "He is staying" : "He is leaving", text: r.stayed ? `${p.name} will be back next year.` : `${p.name} heard you out and is still leaving.`, ok: "OK", cancel: null });
      D.cache = {}; renderSummary();
    }, { quiet: true })));
    $("#to-main").addEventListener("click", () => show("main"));
  }

  function renderSoon() { $("#dyn-main").innerHTML = `<div class="panel"><div class="hdr">${D.screen}</div><div class="body muted">This screen arrives in a later push.</div></div>`; }

  document.addEventListener("cbs:ready", () => { const id = new URLSearchParams(location.search).get("dyn"); if (id) busy(() => open(id)); });
  window.cbsCardShort = CARD_SHORT;
  window.dyn = { open, id: () => D.id, refresh, hub: () => D.hub, topbar, goto, advance, showBox: (g) => { if (D.screen !== "schedule" && D.screen !== "hub") setScreen("schedule"); showBox(g); }, showBoxPop: (g) => showBox(g, true) };
})();
