/* Manager screen v2 (mockup stage): every panel renders from a `turn` object of the API's shape
   ({state, actions, orders, phase, user_side, events}). In the mockup the turn comes from window.MOCK
   (?mode=batting|pitching, ?callout=TEXT, ?theme=light); wiring replaces `load()` with API calls. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const q = new URLSearchParams(location.search);
  if (q.get("theme") === "light") document.documentElement.dataset.theme = "light";

  const RATING = { contact: ["Con", "Contact"], gap: ["Gap", "Gap power (doubles, triples)"], power: ["Pow", "Power (home runs)"], eye: ["Eye", "Eye (walks)"],
                   avoid_k: ["AvK", "Avoid K (strikeouts)"], speed: ["Spd", "Speed (steals, extra bases)"], glove: ["Glv", "Glove (errors at his position)"],
                   arm: ["Arm", "Arm (runners held, steals cut down)"], stuff: ["Stf", "Stuff (strikeouts)"], control: ["Ctl", "Control (walks)"],
                   movement: ["Mov", "Movement (home runs allowed)"], stamina: ["Sta", "Stamina (how long he stays in)"], hold: ["Hld", "Hold (time to the plate: runners attempt less)"] };
  const PITCH_SCALE = 120;        // the pull tables' range of outing pitch counts (engine.manager); display only
  const ORD = (n) => n + (["th", "st", "nd", "rd"][((n % 100) > 10 && (n % 100) < 14) ? 0 : (n % 10 < 4 ? n % 10 : 0)]);
  const RES = { "1B": ["1B", "hit"], "2B": ["2B", "hit"], "3B": ["3B", "hit"], "HR": ["HR", "hr"], "BB": ["BB", "walk"], "HBP": ["HBP", "walk"], "K": ["K", "k"],
                "ROE": ["E", "walk"], "IP_OUT": ["OUT", "out"], "SF": ["SF", "out"], "SH": ["SAC", "out"], "FC": ["FC", "out"], "BUNT": ["BNT", "out"] };

  // ---- team marks: initials in a color from the team's name (original, fictional teams) ----
  function colorOf(name) {
    let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const hue = h % 360, sat = 55 + (h % 20), light = 36 + ((h >> 4) % 10);
    return `hsl(${hue} ${sat}% ${light}%)`;
  }
  function initials(name) { return name.split(/\s+/).map((w) => w[0]).join("").slice(0, 3).toUpperCase(); }
  function mark(team) { return `<span class="mark" style="background:${colorOf(team.name)}" title="${team.name}">${initials(team.name)}</span>`; }
  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  // ---- 1. scoreboard bar ----
  function renderScorebar(t) {
    const st = t.state, inns = st.line_score.innings;
    const row = (side) => `<tr class="${st.batting_side === side && !st.over ? "batting" : ""}"><td class="team">${mark(st.teams[side])}${esc(st.teams[side].name)}</td>${st.line_score[side].map((r) => `<td>${r === null ? "" : r}</td>`).join("")}<td class="tot r">${st.score[side]}</td><td class="tot">${st.hits[side]}</td><td class="tot">${st.errors[side]}</td></tr>`;
    $("#linescore").innerHTML = `<tr><th></th>${inns.map((i) => `<th>${i}</th>`).join("")}<th>R</th><th>H</th><th>E</th></tr>${row("away")}${row("home")}`;
    $("#sb-inning").innerHTML = st.over ? `<div class="half">Final</div><div class="inn">${st.inning > 9 ? st.inning + " inn" : ""}</div>`
      : `<div class="half">${st.half === "T" ? "Top" : "Bottom"} of the</div><div class="inn"><span class="arrow">${st.half === "T" ? "▲" : "▼"}</span>${ORD(st.inning)}</div>`;
    const c = st.count || [0, 0];
    const counter = (lbl, n, max, cls) => `<div class="counter ${cls}"><div class="lbl">${lbl}</div><div class="num">${n}</div><div class="dots">${Array.from({ length: max }, (_, i) => `<i class="${i < n ? "on" : ""}"></i>`).join("")}</div></div>`;
    $("#sb-counts").innerHTML = counter("Balls", c[0], 3, "balls") + counter("Strikes", c[1], 2, "strikes") + counter("Outs", st.outs, 3, "outs");
  }

  // ---- 2. matchup banner ----
  function chips(p) {
    return `<div class="chips">${Object.entries(p.ratings).map(([k, v]) => `<span class="chip ${v >= 70 ? "hi" : v <= 35 ? "lo" : ""}" title="${(RATING[k] || [k, k])[1]}: ${v}">${(RATING[k] || [k])[0]} <b>${v}</b></span>`).join("")}</div>`;
  }
  function stat(k, v) { return `<span><span class="k">${k}</span><b>${v}</b></span>`; }
  function stamColor(f) { return f < .55 ? "var(--stam-hi)" : f < .8 ? "var(--stam-mid)" : "var(--stam-lo)"; }
  function renderBanner(t) {
    const st = t.state, me = t.user_side, b = st.batter, p = st.pitcher;
    const bside = st.batting_side, pside = bside === "home" ? "away" : "home";
    const order = b ? st.lineups[bside].findIndex((x) => x.pid === b.pid) + 1 : 0;
    $("#batter").innerHTML = b ? `${mark(st.teams[bside])}<div class="role">${st.count ? "At bat" : "Due up"} · ${esc(st.teams[bside].name)}${bside === me ? " (you)" : ""}</div>
      <div class="name">${esc(b.name)}<small>${b.pos} · bats ${b.hand || "–"} · bats ${ORD(order)}</small></div>
      <div class="today">${stat("AB", b.line.ab)}${stat("H", b.line.h)}${stat("RBI", b.line.rbi)}${stat("BB", b.line.bb)}${stat("K", b.line.k)}<span class="season">${stat("AVG", "")}${stat("HR", "")}${stat("SB", "")}</span></div>
      ${chips(b)}` : "<div class='role'>No batter yet</div>";
    const pitches = p && p.outing ? p.outing.pitches : (p ? p.line.pitches : 0);
    const f = Math.min(1, pitches / PITCH_SCALE);
    $("#pitcher").innerHTML = p ? `<div class="role">Pitching · ${esc(st.teams[pside].name)}${pside === me ? " (you)" : ""}</div>${mark(st.teams[pside])}
      <div class="name">${esc(p.name)}<small>${p.role} · throws ${p.hand || "–"}</small></div>
      <div class="today">${stat("IP", p.line.ip)}${stat("H", p.line.h)}${stat("R", p.line.r)}${stat("BB", p.line.bb)}${stat("K", p.line.k)}${stat("P", pitches)}<span class="season">${stat("W-L", "")}${stat("ERA", "")}${stat("IP", "")}</span></div>
      <div class="stamina" title="Pitches thrown this outing on the pull tables' 0–${PITCH_SCALE} range; Stamina ${p.ratings.stamina}. Not the AI's pull odds."><span>Outing</span><div class="bar"><i style="width:${(f * 100).toFixed(0)}%;background:${stamColor(f)}"></i>${[25, 50, 75, 100].map((x) => `<s style="left:${x / PITCH_SCALE * 100}%"></s>`).join("")}</div><span>${pitches} pitches${p.outing ? `, ${p.outing.runs} R` : ""}</span></div>
      ${chips(p)}` : "<div class='role'>No pitcher yet</div>";
  }

  // ---- 3. field ----
  const BASES = { 1: [250, 160], 2: [160, 70], 3: [70, 160] };
  function renderField(t) {
    const st = t.state, me = t.user_side, bside = st.batting_side;
    const runner = (i, b) => {
      if (!b) return "";
      const [x, y] = BASES[i + 1];
      const p = st.lineups[bside].find((x_) => x_.pid === b.pid) || {};
      return `<g class="runner" data-pid="${b.pid}" data-name="${esc(b.name)}" data-spd="${p.ratings ? p.ratings.speed : "–"}" data-pos="${p.pos || ""}" data-line="${p.line_text || ""}" data-glv="${p.ratings ? p.ratings.glove : "–"}">
        <circle cx="${x}" cy="${y}" r="13"/><text x="${x}" y="${y + 4}">${i + 1}</text><text class="tag" x="${x}" y="${y - 20}">${esc(b.name)}</text></g>`;
    };
    const fielders = [["P", 160, 150], ["C", 160, 260], ["1B", 240, 125], ["2B", 190, 85], ["SS", 125, 85], ["3B", 78, 125], ["LF", 60, 40], ["CF", 160, 18], ["RF", 260, 40]];
    $("#field").innerHTML = `<h2>Field <span class="sub">${st.bases.some(Boolean) ? "tap a runner for his ratings" : "bases empty"}</span></h2>
      <svg class="diamond" viewBox="0 0 320 290" aria-label="diamond">
        <rect class="turf" x="0" y="0" width="320" height="290" rx="14"/>
        <path class="turf2" d="M160 250 L0 90 Q160 -70 320 90 Z"/>
        <polygon class="path" points="160,250 70,160 160,70 250,160"/>
        <circle class="path" cx="160" cy="150" r="14"/>
        ${fielders.map(([n, x, y]) => `<text class="pos" x="${x}" y="${y}" text-anchor="middle">${n}</text>`).join("")}
        <rect class="base" x="241" y="151" width="18" height="18" transform="rotate(45 250 160)"/>
        <rect class="base" x="151" y="61" width="18" height="18" transform="rotate(45 160 70)"/>
        <rect class="base" x="61" y="151" width="18" height="18" transform="rotate(45 70 160)"/>
        <polygon class="base" points="151,243 169,243 169,251 160,259 151,251"/>
        <circle class="batterbox" cx="160" cy="268" r="5"><title>${st.batter ? esc(st.batter.name) : ""}</title></circle>
        ${st.bases.map((b, i) => runner(i, b)).join("")}
      </svg>
      <div class="legend-line">${st.due_up.length ? "Due up: " + st.due_up.map(esc).join(", ") : ""}</div>`;
    $$("#field .runner").forEach((g) => {
      const show = (e) => {
        const d = g.dataset;
        const tip = $("#tip");
        tip.innerHTML = `<b>${d.name}</b> ${d.pos}<br>Speed <b>${d.spd}</b> · Glove ${d.glv}<br>Today ${d.line || "0-0"}`;
        tip.classList.remove("hidden");
        const r = g.getBoundingClientRect();
        tip.style.left = Math.min(window.innerWidth - 280, r.left) + "px"; tip.style.top = (r.bottom + 6) + "px";
      };
      g.addEventListener("mouseenter", show); g.addEventListener("click", show);
      g.addEventListener("mouseleave", () => $("#tip").classList.add("hidden"));
    });
  }

  // ---- 4. action menu: only the calls legal now, for the side you are on ----
  function menuItems(t) {
    const st = t.state, me = t.user_side, acts = Object.fromEntries(t.actions.map((a) => [a.kind, a]));
    const batting = st.batting_side === me && !st.over;
    const items = [];
    const pre = acts.pre_pitch, def = acts.pre_pitch_defense;
    const queued = (k) => t.orders.some((o) => o.kind === k);
    if (batting) {
      const picks = (pre && pre.picks) || {};
      items.push({ k: "pre_pitch", v: "swing", label: "Swing away", dflt: true, on: !!pre && pre.legal });
      items.push({ k: "pre_pitch", v: "bunt", label: "Bunt", on: !!pre && pre.legal });
      if (picks.steal_base) items.push({ k: "pre_pitch", v: "steal", label: `Steal ${ORD(picks.steal_base)}`, on: true });
      if (picks.steal_base) items.push({ k: "pre_pitch", v: "hit_and_run", label: "Hit & run", on: true });
      if (acts.pinch_hit) items.push({ k: "pinch_hit", label: st.count ? "Pinch hit (next batter)" : "Pinch hit", on: acts.pinch_hit.legal, why: acts.pinch_hit.reason });
      (picks.runners || []).forEach((r) => items.push({ k: "pre_pitch", v: { pinch_runner: null, slot: r.slot }, label: `Pinch run ${ORD(r.base)}`, on: (picks.bench || []).length > 0, why: (picks.bench || []).length ? "" : "no bench player left" }));
    } else if (!st.over) {
      const picks = (def && def.picks) || {};
      items.push({ k: "pre_pitch_defense", v: "none", label: "Pitch", dflt: true, on: !!def && def.legal });
      items.push({ k: "pre_pitch_defense", v: "ibb", label: "Intentional walk", on: !!def && def.legal });
      items.push({ k: "pre_pitch_defense", v: "pitchout", label: "Pitchout", on: !!def && def.legal && st.bases.some(Boolean), why: st.bases.some(Boolean) ? "" : "no runner on" });
      const m = st.mound || {};
      let why = "";
      if (m.same_batter) why = "no second trip with the same batter at bat (9-4-c)";
      else if (m.visited_this_pitcher_inning) why = "a second trip this inning removes him (9-4-b)";
      else if (m.free_used >= m.free_limit) why = `no free trips left (${m.free_used} of ${m.free_limit}): a trip removes him`;
      items.push({ k: "pre_pitch_defense", v: "mound_visit", label: "Mound visit", on: !!def && def.legal && !m.same_batter, why });
      items.push({ k: "pitching_change", label: st.count ? "Pitching change (now)" : "Pitching change", on: (picks.bullpen || []).length > 0, why: (picks.bullpen || []).length ? "" : "no pitcher left" });
      items.push({ k: "defensive_subs", label: "Defensive change", on: acts.defensive_subs && acts.defensive_subs.legal, why: acts.defensive_subs ? acts.defensive_subs.reason : "" });
    }
    return items.map((i) => Object.assign(i, { queued: queued(i.k) }));
  }
  function renderActions(t) {
    const items = menuItems(t);
    const st = t.state;
    const side = st.batting_side === t.user_side ? "You bat" : "You pitch";
    $("#actions").innerHTML = `<h2>Calls <span class="sub">${side} · ${st.over ? "final" : st.count ? "before the next pitch" : "before the at-bat"}</span></h2>
      <div class="menu">${items.map((i) => `<button data-k="${i.k}" class="${i.dflt ? "default" : ""} ${i.queued ? "queued" : ""}" ${i.on ? "" : "disabled"}><span>${i.label}</span>${i.why ? `<span class="why">${esc(i.why)}</span>` : i.dflt ? `<span class="key">default</span>` : ""}</button>`).join("")}
      <div class="group">Sim</div>
      <div class="sims"><button class="go" data-sim="pitch">Next pitch</button><button data-sim="pa">At-bat</button><button data-sim="half">Half inning</button><button data-sim="inning">Inning</button><button data-sim="three_innings">3 innings</button><button data-sim="game">End of game</button></div>
      <div class="coach"><button class="btn-ghost" id="coach">Ask bench coach</button> <button class="btn-ghost" id="legend-btn">Rating legend</button></div></div>`;
    $("#legend-btn").addEventListener("click", () => $("#legend").classList.toggle("hidden"));
  }

  // ---- 5. lineup panel ----
  function resChips(list) { return `<span class="res">${(list || []).map((r) => { const [lab, cls] = RES[r] || [r, "out"]; return `<i class="${cls}">${lab}</i>`; }).join("")}</span>`; }
  function renderLineup(t, tab) {
    const st = t.state, me = t.user_side, opp = me === "home" ? "away" : "home";
    tab = tab || "mine";
    const side = tab === "opp" ? opp : me;
    let body;
    if (tab === "pen") {
      const rows = st.bullpen[me].map((p) => `<tr><td class="nm">${esc(p.name)}</td><td>${p.role}</td><td class="hand">${p.hand || "–"}</td><td class="avail">available</td><td><span class="stam-mini" title="Stamina ${p.ratings.stamina}"><i style="width:${Math.max(8, Math.min(100, (p.ratings.stamina - 20) / 60 * 100))}%"></i></span> ${p.ratings.stamina}</td></tr>`)
        .concat(st.used_pitchers[me].map((p) => `<tr class="bp"><td class="nm">${esc(p.name)}</td><td>${p.role}</td><td class="hand">${p.hand || "–"}</td><td class="avail used">${st.pitcher && st.pitcher.pid === p.pid ? "pitching" : "used"}</td><td>${p.line.ip} IP, ${p.line.pitches} P</td></tr>`));
      body = `<table class="lu bp"><tr><th>Pitcher</th><th>Role</th><th>T</th><th>Status</th><th>Stamina</th></tr>${rows.join("")}</table>`;
    } else {
      const lu = st.lineups[side];
      const cur = st.batter && st.batting_side === side ? st.batter.pid : null;
      const curIdx = cur ? lu.findIndex((p) => p.pid === cur) : -1;
      body = `<table class="lu"><tr><th>#</th><th>Batter</th><th>Pos</th><th>B</th><th>Today</th><th>H-AB</th></tr>${lu.map((p, i) => `<tr class="${p.pid === cur ? "now" : ""} ${curIdx >= 0 && i === (curIdx + 1) % 9 ? "deck" : ""}"><td class="n">${i + 1}</td><td class="nm">${esc(p.name)}</td><td>${p.pos}</td><td class="hand">${p.hand || "–"}</td><td>${resChips(st.pa_results[String(p.pid)])}</td><td class="hab">${p.line.h}-${p.line.ab}</td></tr>`).join("")}</table>`;
    }
    $("#lineup").innerHTML = `<h2>Lineup</h2><div class="tabs"><button data-tab="mine" class="${tab === "mine" ? "on" : ""}">${esc(st.teams[me].name)}</button><button data-tab="opp" class="${tab === "opp" ? "on" : ""}">${esc(st.teams[opp].name)}</button><button data-tab="pen" class="${tab === "pen" ? "on" : ""}">Bullpen</button></div>${body}`;
    $$("#lineup .tabs button").forEach((b) => b.addEventListener("click", () => renderLineup(t, b.dataset.tab)));
  }

  // ---- 6. play-by-play ----
  const HIDE = /no change|lineup set|no bunt|held off|runners may go|^Note:/i;
  function renderFeed(events, me, teams) {
    const rows = events.filter((e) => !(e.type === "decision" && HIDE.test(e.text))).slice(-300).reverse().map((e) => {
      let badge = "";
      let text = e.text;
      if (e.type === "decision") {
        const src = e.source;
        text = text.replace(/^(You|AUTO \(AI ran your team\)|.+? \(AI\)|Note): /, "");
        badge = src === "auto" ? `<span class="badge ai">AI</span>` : src === "order" ? `<span class="badge you">YOU</span>` : src === "ai" ? `<span class="badge opp">OPP</span>` : "";
      }
      return `<div class="ev ${e.type}">${badge}<span>${esc(text)}</span></div>`;
    });
    $("#feed-body").innerHTML = rows.join("") || "<div class='ev'>Nothing yet.</div>";
    $("#drawer-title").textContent = `Play by play (${events.length})`;
  }

  // ---- 7. callouts ----
  function callout(big, sub) {
    const c = $("#callout");
    c.innerHTML = `<div class="box"><div class="big">${esc(big)}</div>${sub ? `<div class="sub">${esc(sub)}</div>` : ""}<div class="hint">tap to skip</div></div>`;
    c.classList.remove("hidden");
    clearTimeout(c._h); c._h = setTimeout(() => c.classList.add("hidden"), 1800);
    c.onclick = () => c.classList.add("hidden");
  }
  function calloutFor(events) {
    // the last play, if it is a big moment: used by the wiring after each turn
    const last = [...events].reverse().find((e) => e.type === "pa" || e.type === "run" || e.type === "decision");
    if (!last) return;
    if (last.type === "pa" && last.runs >= 2) return callout(`${last.runs} RUNS SCORE`, last.text);
    if (last.type === "pa" && last.res === "HR") return callout("HOME RUN", last.text);
    if (last.type === "pa" && last.res === "K") return callout("STRIKEOUT", last.text);
    if (last.type === "pa" && /double play/i.test(last.text)) return callout("DOUBLE PLAY", last.text);
    if (last.type === "decision" && /comes in to pitch/.test(last.text)) return callout("PITCHING CHANGE", last.text);
  }

  // ---- legend ----
  function renderLegend() {
    $("#legend").innerHTML = `<b>Ratings (20–80, 50 = D1 median)</b><dl>${Object.values(RATING).map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("")}</dl><div style="margin-top:6px;color:var(--muted);font-size:12px">B = bats, T = throws: L/R/S once handedness is in the engine (Phase 3).</div>`;
  }

  // ---- phone tabs and drawer ----
  $$("#phone-tabs button").forEach((b) => b.addEventListener("click", () => {
    $$("#phone-tabs button").forEach((x) => x.classList.toggle("on", x === b));
    const tab = b.dataset.tab;
    $("#feed").classList.toggle("on", tab === "feed");
    document.body.dataset.tab = tab;
    window.scrollTo(0, 0);
  }));
  $("#drawer-toggle").addEventListener("click", () => { const d = $("#feed"); if (d.hasAttribute("open")) d.removeAttribute("open"); else d.setAttribute("open", ""); });

  // ---- render a turn ----
  function render(t) {
    renderScorebar(t); renderBanner(t); renderField(t); renderActions(t); renderLineup(t); renderFeed(t.events || [], t.user_side, t.state.teams); renderLegend();
  }
  function load() {
    const mode = q.get("mode") || "batting";
    const m = window.MOCK[mode];
    const t = Object.assign({}, m.turn, { state: m.state, events: m.feed });
    render(t);
    if (q.get("tab")) $(`#phone-tabs [data-tab="${q.get("tab")}"]`).click();
    if (q.get("drawer")) $("#feed").setAttribute("open", "");
    if (q.get("callout")) callout(q.get("callout"), q.get("sub") || "");
  }
  window.v2 = { render, callout, calloutFor, menuItems };
  load();
})();
