/* Pages (2026-10-09): the player page and the team page, opened from any player or school name (data-pid / data-tid)
   as an overlay on the current screen. Dense OOTP-style layout in the design system. Display only: everything
   comes from the API; a dash marks what the engine does not produce. */
(() => {
  "use strict";
  const V = window.v2, $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const { raw, esc, badge, band, mark, busy, RATING } = V;
  const dateText = (d, o) => window.cbsDate(d, o);
  const f3 = (v) => (typeof v === "number" ? v.toFixed(3).replace(/^0\./, ".") : v == null ? "–" : v);
  const dash = (v) => (v == null || v === "" ? "–" : v);
  const BAT_KEYS = ["contact", "gap", "power", "eye", "avoid_k", "speed", "glove", "arm"], PIT_KEYS = ["stuff", "control", "movement", "stamina", "hold"];

  function dynId() { return window.dyn && window.dyn.id(); }
  function inDynasty() { return !!dynId() && !(V.S.game && !V.S.game.dynasty && V.S.screen === "game"); }

  // ---- the overlay ----
  function overlay() {
    let el = $("#pageover");
    if (!el) {
      el = document.createElement("div"); el.id = "pageover"; el.className = "pageover hidden";
      el.innerHTML = `<div class="page panel"><div class="page-body" id="page-body"></div></div>`;
      document.body.appendChild(el);
      el.addEventListener("click", (e) => { if (e.target === el || e.target.closest("[data-page-close]")) close(); });
      document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !el.classList.contains("hidden")) close(); });
    }
    return el;
  }
  function open(html) { const el = overlay(); $("#page-body").innerHTML = html; el.classList.remove("hidden"); el.scrollTop = 0; }
  function close() { const el = $("#pageover"); if (el) el.classList.add("hidden"); }
  const closeBtn = `<button class="btn-ghost page-close" data-page-close="1" title="close (Esc)">Close</button>`;

  // ---- rating bars: 20-80 on the rating colors ----
  function ratingBar(k, v) {
    if (v == null) return "";
    const [ab, full] = RATING[k] || [k, k];
    const pct = Math.max(0, Math.min(100, ((v - 20) / 60) * 100));
    return `<div class="rbar ${band(v)}" title="${esc(full)}: ${v} (20–80, 50 = D1 median)"><span class="k">${ab}</span><div class="track"><i style="width:${pct.toFixed(0)}%"></i></div><b class="mono">${v}</b></div>`;
  }

  // ---- the player page ----
  const BLINE = [["ab", "AB"], ["r", "R"], ["h", "H"], ["2b", "2B"], ["3b", "3B"], ["hr", "HR"], ["rbi", "RBI"], ["bb", "BB"], ["k", "K"], ["sb", "SB"], ["cs", "CS"]];
  const PLINE = [["ip", "IP"], ["h", "H"], ["r", "R"], ["er", "ER"], ["bb", "BB"], ["k", "K"], ["hr", "HR"], ["pitches", "P"]];
  const BSEASON = [["g", "G"], ["pa", "PA"], ["ab", "AB"], ["r", "R"], ["h", "H"], ["2b", "2B"], ["3b", "3B"], ["hr", "HR"], ["rbi", "RBI"], ["bb", "BB"], ["hbp", "HBP"], ["k", "K"], ["sb", "SB"], ["cs", "CS"], ["avg", "AVG"], ["obp", "OBP"], ["slg", "SLG"], ["ops", "OPS"]];
  const PSEASON = [["g", "G"], ["gs", "GS"], ["w", "W"], ["l", "L"], ["sv", "SV"], ["hld", "HLD"], ["ip", "IP"], ["h", "H"], ["r", "R"], ["er", "ER"], ["bb", "BB"], ["k", "K"], ["hr", "HR"], ["era", "ERA"], ["whip", "WHIP"], ["k9", "K/9"], ["bb9", "BB/9"]];
  const RATE = new Set(["avg", "obp", "slg", "ops"]);
  const fmt = (k, v) => (v == null ? "–" : RATE.has(k) ? f3(v) : k === "era" || k === "whip" ? v.toFixed(2) : k === "k9" || k === "bb9" ? v.toFixed(1) : v);
  const statRow = (cols, s) => `<table class="tbl stats"><tr>${cols.map(([k, l]) => `<th class="num">${l}</th>`).join("")}</tr><tr>${cols.map(([k]) => `<td class="num">${s ? fmt(k, s[k]) : "–"}</td>`).join("")}</tr></table>`;

  async function player(pid) {
    const url = inDynasty() ? `/api/dynasties/${dynId()}/players/${pid}` : `/api/players/${pid}`;
    const p = await raw(url);
    const isBat = p.side === "bat", keys = isBat ? BAT_KEYS : PIT_KEYS;
    const bars = keys.map((k) => ratingBar(k, p.ratings[k])).join("");
    const season = p.season ? statRow(isBat ? BSEASON : PSEASON, p.season) : `<div class="muted">No season: this is an exhibition.</div>`;
    const sp = p.splits;
    const splitCols = [["pa", "PA"], ["ab", "AB"], ["h", "H"], ["2b", "2B"], ["3b", "3B"], ["hr", "HR"], ["bb", "BB"], ["hbp", "HBP"], ["k", "K"], ["avg", "AVG"], ["obp", "OBP"], ["slg", "SLG"]];
    const splits = sp ? `<table class="tbl stats"><tr><th>vs</th>${splitCols.map(([k, l]) => `<th class="num">${l}</th>`).join("")}</tr>${["L", "R"].map((h) => `<tr><td class="nm">${h === "L" ? (isBat ? "LHP" : "LHB") : (isBat ? "RHP" : "RHB")}</td>${splitCols.map(([k]) => `<td class="num">${sp[h] ? fmt(k, sp[h][k]) : "–"}</td>`).join("")}</tr>`).join("")}</table><div class="muted">Counted from the game logs of every game played in this dynasty (the engine's accumulators keep season totals only).</div>`
      : `<div class="muted">Splits are counted across a dynasty's games.</div>`;
    const lineCols = isBat ? BLINE : PLINE;
    const log = p.game_log && p.game_log.length ? `<table class="tbl stats"><tr><th>Date</th><th>Opponent</th><th>Result</th>${isBat ? "" : "<th>Dec</th>"}${lineCols.map(([k, l]) => `<th class="num">${l}</th>`).join("")}<th></th></tr>${p.game_log.slice().reverse().map((g) => `<tr><td class="date">${dateText(g.date)}</td><td class="nm">${g.side === "home" ? "vs" : "at"} <a class="tlink" data-tid="${g.opp}">${esc(g.opp_name)}</a>${g.stage !== "regular" ? ` <span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : ""}</td><td><span class="pill ${g.result[0] === "W" ? "success" : "loss"}">${g.result}</span></td>${isBat ? "" : `<td>${g.line.dec ? `<span class="pill ${g.line.dec === "L" ? "loss" : "success"}">${g.line.dec}</span>` : ""}</td>`}${lineCols.map(([k]) => `<td class="num">${g.line[k]}</td>`).join("")}<td>${g.i != null && g.i >= 0 ? `<button class="btn-ghost" data-box="${g.i}">Box</button>` : g.k != null ? `<button class="btn-ghost" data-postbox="${g.k}">Box</button>` : ""}</td></tr>`).join("")}</table>`
      : `<div class="muted">${p.game_log ? "No games yet." : "A game log needs a dynasty."}</div>`;
    const outings = !isBat && p.outings ? (p.outings.length ? `<table class="tbl stats"><tr><th>Date</th><th class="num">Pitches</th></tr>${p.outings.slice().reverse().slice(0, 12).map((o) => `<tr><td class="date">${dateText(o.date, { weekday: true })}</td><td class="num">${o.pitches}</td></tr>`).join("")}</table>` : `<div class="muted">No outing yet.</div>`) : "";
    open(`<div class="page-head"><div class="who">${mark(p.team)}<div><div class="name">${esc(p.name)}</div><div class="muted">${p.pos} · ${isBat ? "bats" : "throws"} ${dash(p.hand.split("/")[isBat ? 0 : 1])} · B/T ${esc(p.hand)} · class ${esc(p.year)} · <a class="tlink" data-tid="${p.tid}">${esc(p.team.name)}</a> <span class="muted">${esc(p.team.conference || "")}</span></div></div></div>${closeBtn}</div>
      <div class="page-grid">
        <div class="panel"><div class="hdr">Ratings <span class="sub">20–80 · true ratings</span></div><div class="body bars">${bars}</div></div>
        <div class="col"><div class="panel"><div class="hdr">Season</div><div class="body tight scroll-x">${season}</div></div>
        <div class="panel"><div class="hdr">Splits <span class="sub">${sp ? sp.vs : ""}</span></div><div class="body tight scroll-x">${splits}</div></div>
        ${outings ? `<div class="panel"><div class="hdr">Last outings <span class="sub">pitch counts</span></div><div class="body tight">${outings}</div></div>` : ""}</div>
      </div>
      <div class="panel"><div class="hdr">Game log <span class="sub">${p.game_log ? p.game_log.length + " games" : ""}</span></div><div class="body tight scroll-x">${log}</div></div>`);
    bind();
  }

  // ---- the team page ----
  async function team(tid) {
    if (!inDynasty()) { const t = await raw(`/api/teams/${tid}`); return teamExhibition(t); }
    const t = await raw(`/api/dynasties/${dynId()}/teams/${tid}`);
    const bk = BAT_KEYS, pk = PIT_KEYS;
    const rb = (k, v) => (v == null ? '<span class="muted">–</span>' : badge(k, v).replace(/<span class="k">.*?<\/span>/, ""));
    const bat = `<table class="tbl roster"><tr><th>Pos</th><th>Name</th><th>B/T</th>${bk.map((k) => `<th>${RATING[k][0]}</th>`).join("")}<th class="num">AVG</th><th class="num">OBP</th><th class="num">SLG</th><th class="num">HR</th><th class="num">RBI</th><th class="num">SB</th></tr>${t.roster.batters.map((p) => `<tr><td>${p.pos}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a> <span class="muted">${p.role}</span></td><td class="muted">${p.hand}</td>${bk.map((k) => `<td>${rb(k, p.ratings[k])}</td>`).join("")}<td class="num">${f3(p.stats.avg)}</td><td class="num">${f3(p.stats.obp)}</td><td class="num">${f3(p.stats.slg)}</td><td class="num">${p.stats.hr}</td><td class="num">${p.stats.rbi}</td><td class="num">${p.stats.sb}</td></tr>`).join("")}</table>`;
    const pit = `<table class="tbl roster"><tr><th>Role</th><th>Name</th><th>B/T</th>${pk.map((k) => `<th>${RATING[k][0]}</th>`).join("")}<th class="num">W-L</th><th class="num">SV</th><th class="num">IP</th><th class="num">ERA</th><th class="num">K</th></tr>${t.roster.pitchers.map((p) => `<tr><td>${p.role}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td class="muted">${p.hand}</td>${pk.map((k) => `<td>${rb(k, p.ratings[k])}</td>`).join("")}<td class="num">${p.stats.w}-${p.stats.l}</td><td class="num">${p.stats.sv}</td><td class="num">${p.stats.ip}</td><td class="num">${p.stats.era.toFixed(2)}</td><td class="num">${p.stats.k}</td></tr>`).join("")}</table>`;
    const sched = `<table class="tbl sched"><tr><th>Date</th><th>Opponent</th><th class="num">Result</th><th></th></tr>${t.schedule.map((g) => `<tr class="${g.status}"><td class="date muted">${dateText(g.date)}</td><td class="nm">${g.side === "home" ? "vs" : "at"} <a class="tlink" data-tid="${g.side === "home" ? g.away : g.home}">${esc(g.side === "home" ? g.away_name : g.home_name)}</a>${g.conf ? ' <span class="tag">CONF</span>' : ""}${g.stage && g.stage !== "regular" ? ` <span class="tag">${{ conf: "CT", regional: "REG", super: "SUPER", cws: "CWS" }[g.stage] || g.stage}</span>` : ""}</td><td class="num">${g.status === "played" ? `<span class="pill ${g.result[0] === "W" ? "success" : "loss"}">${g.result}</span>` : g.status === "canceled" ? '<span class="muted">canceled</span>' : ""}</td><td>${g.status === "played" ? (g.i != null && g.i >= 0 ? `<button class="btn-ghost" data-box="${g.i}">Box</button>` : `<button class="btn-ghost" data-postbox="${g.k}">Box</button>`) : ""}</td></tr>`).join("")}</table>`;
    const st = t.standing;
    const standing = `<table class="tbl"><tr><th>Team</th><th class="num">Conf</th><th class="num">All</th><th class="num">RPI</th></tr>${st.rows.map((r) => `<tr class="${r.tid === tid ? "now" : ""}"><td class="nm"><a class="tlink" data-tid="${r.tid}">${esc(r.name)}</a></td><td class="num">${r.cw}-${r.cl}</td><td class="num">${r.w}-${r.l}</td><td class="num">${r.rpi_rank || "—"}</td></tr>`).join("")}</table>`;
    const card = t.report_card ? `<div class="card-grades">${Object.entries(t.report_card.grades).map(([k, g]) => window.cbsGradeChip({ label: k, short: (window.cbsCardShort || {})[k] || k }, g.grade, g.confidence)).join("")}</div>` : `<div class="muted">No report card.</div>`;
    open(`<div class="page-head"><div class="who">${mark(t.team)}<div><div class="name">${esc(t.team.name)}</div><div class="muted">${esc(t.team.conference_full || t.team.conference || "")} · ${(t.team.tier || "").toUpperCase()} · ${esc(t.team.location || "")} · ${t.record[0]}-${t.record[1]} (${t.conf_record[0]}-${t.conf_record[1]}) · RPI ${t.rpi_rank ? "#" + t.rpi_rank : "—"}</div></div></div>${closeBtn}</div>
      <div class="page-grid wide">
        <div class="col"><div class="panel"><div class="hdr">Batters</div><div class="body tight scroll-x">${bat}</div></div><div class="panel"><div class="hdr">Pitchers</div><div class="body tight scroll-x">${pit}</div></div>
          <div class="panel"><div class="hdr">Schedule and results <span class="sub">${t.schedule.filter((g) => g.status === "played").length} played</span></div><div class="body tight scroll-x">${sched}</div></div></div>
        <div class="col"><div class="panel"><div class="hdr">${esc(st.conference_full || st.conference)} <span class="sub">standings</span></div><div class="body tight">${standing}</div></div>
          <div class="panel"><div class="hdr">Report card</div><div class="body">${card}</div></div></div>
      </div>`);
    bind();
  }
  function teamExhibition(t) {
    const rb = (k, v) => (v == null ? '<span class="muted">–</span>' : badge(k, v).replace(/<span class="k">.*?<\/span>/, ""));
    const bat = `<table class="tbl roster"><tr><th>Pos</th><th>Name</th><th>B/T</th>${BAT_KEYS.map((k) => `<th>${RATING[k][0]}</th>`).join("")}</tr>${t.batters.map((p) => `<tr><td>${p.pos}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a> <span class="muted">${p.role}</span></td><td class="muted">${dash(p.bats)}/${dash(p.throws)}</td>${BAT_KEYS.map((k) => `<td>${rb(k, p.ratings[k])}</td>`).join("")}</tr>`).join("")}</table>`;
    const pit = `<table class="tbl roster"><tr><th>Role</th><th>Name</th><th>B/T</th>${PIT_KEYS.map((k) => `<th>${RATING[k][0]}</th>`).join("")}</tr>${t.pitchers.map((p) => `<tr><td>${p.role}</td><td class="nm"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></td><td class="muted">${dash(p.bats)}/${dash(p.throws)}</td>${PIT_KEYS.map((k) => `<td>${rb(k, p.ratings[k])}</td>`).join("")}</tr>`).join("")}</table>`;
    open(`<div class="page-head"><div class="who">${mark(t)}<div><div class="name">${esc(t.name)}</div><div class="muted">${esc(t.conference || "")} · ${(t.tier || "").toUpperCase()} · ${esc(t.location || "")} · exhibition: no season</div></div></div>${closeBtn}</div>
      <div class="panel"><div class="hdr">Batters</div><div class="body tight scroll-x">${bat}</div></div><div class="panel"><div class="hdr">Pitchers</div><div class="body tight scroll-x">${pit}</div></div>`);
    bind();
  }
  function bind() {
    $$("#page-body [data-box], #page-body [data-postbox]").forEach((b) => b.addEventListener("click", () => busy(async () => {
      const g = b.dataset.box != null ? await raw(`/api/dynasties/${dynId()}/games/${b.dataset.box}`) : await raw(`/api/dynasties/${dynId()}/postgames/${b.dataset.postbox}`);
      close(); if (window.dyn && window.dyn.showBox) window.dyn.showBox(g);
    })));
  }

  // every player or school name anywhere: data-pid / data-tid
  document.addEventListener("click", (e) => {
    const pl = e.target.closest("[data-pid]"), tl = e.target.closest("[data-tid]");
    if (pl && pl.dataset.pid !== "") { e.preventDefault(); busy(() => player(+pl.dataset.pid)); }
    else if (tl && tl.dataset.tid !== "") { e.preventDefault(); busy(() => team(+tl.dataset.tid)); }
  });
  window.pages = { player, team, close };
})();
