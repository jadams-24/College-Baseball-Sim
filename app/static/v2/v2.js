/* Manager screen v2 (2026-10-08): every panel renders from the turn the API returns ({state, actions, orders,
   phase, user_side, events}). The page never computes an outcome: it shows the engine's state and sends sim
   targets, orders and answers. The latest save is mirrored to localStorage after every turn; when the server has
   forgotten the game (a restart, the free host's nap) the page reloads it from that save. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const q = new URLSearchParams(location.search);
  if (q.get("theme") === "light") document.documentElement.dataset.theme = "light";
  const LS_LATEST = "cbs.latest", LS_SAVES = "cbs.saves";

  const RATING = { contact: ["Con", "Contact"], gap: ["Gap", "Gap power (doubles, triples)"], power: ["Pow", "Power (home runs)"], eye: ["Eye", "Eye (walks)"],
                   avoid_k: ["AvK", "Avoid K (strikeouts)"], speed: ["Spd", "Speed (steals, extra bases)"], glove: ["Glv", "Glove (errors at his position)"],
                   arm: ["Arm", "Arm (runners held, steals cut down)"], stuff: ["Stf", "Stuff (strikeouts)"], control: ["Ctl", "Control (walks)"],
                   movement: ["Mov", "Movement (home runs allowed)"], stamina: ["Sta", "Stamina (how long he stays in)"], hold: ["Hld", "Hold (time to the plate: runners attempt less)"] };
  const f3 = (v) => (typeof v === "number" ? v.toFixed(3).replace(/^0\./, ".") : v);
  const PITCH_SCALE = 120;        // the pull tables' range of outing pitch counts (engine.manager); display only
  const ORD = (n) => n + (["th", "st", "nd", "rd"][((n % 100) > 10 && (n % 100) < 14) ? 0 : (n % 10 < 4 ? n % 10 : 0)]);
  const RES = { "1B": ["1B", "hit"], "2B": ["2B", "hit"], "3B": ["3B", "hit"], "HR": ["HR", "hr"], "BB": ["BB", "walk"], "HBP": ["HBP", "walk"], "K": ["K", "k"],
                "ROE": ["E", "walk"], "IP_OUT": ["OUT", "out"], "SF": ["SF", "out"], "SH": ["SAC", "out"], "FC": ["FC", "out"], "BUNT": ["BNT", "out"] };

  const S = { league: null, decisions: null, game: null, events: [], busy: false };

  // ---- storage ----
  const ls = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: fine */ } },
  };

  // ---- API ----
  async function raw(path, method = "GET", body) {
    const r = await window.cbsLoad.request(path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
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
      S.game.id = t.game_id; applyTurn(t, true);
      return raw(`/api/games/${S.game.id}${path}`, method, body);
    }
  }
  async function busy(fn, o) {
    if (S.busy) return;
    S.busy = true; document.body.classList.add("busy");
    try { return await fn(); }
    catch (e) { console.error(e); if (!(o && o.quiet)) toast(e.message || String(e)); }
    finally { S.busy = false; document.body.classList.remove("busy"); if (S.game) render(S.game.turn); }
  }
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 3500);
  }

  // ---- turns ----
  function applyTurn(t, replaceEvents = false) {
    S.game.turn = t; S.game.meta = t.meta;
    if (t.error) toast("The engine refused that call: " + t.error);
    S.events = replaceEvents ? t.events.slice() : S.events.concat(t.events);
    mirrorSave();
  }
  let saveTimer = null;
  function mirrorSave() {
    if (S.game && S.game.dynasty) return;
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

  // ---- team marks: initials in a color from the team's name (original, fictional teams) ----
  function colorOf(name) {
    let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const hue = h % 360, sat = 55 + (h % 20), light = 36 + ((h >> 4) % 10);
    return `hsl(${hue} ${sat}% ${light}%)`;
  }
  function initials(name) { return name.split(/\s+/).map((w) => w[0]).join("").slice(0, 3).toUpperCase(); }
  // ---- school colors and ballparks (app/identity.py via /api/identity): accents only, never large backgrounds ----
  // colorsOf: the display colors of a team (a {colors} object from the server, or the identity table by tid); null when the row is D
  function colorsOf(team) {
    if (!team) return null;
    if (team.colors) return team.colors;
    const id = team.tid != null && S.identity ? S.identity[team.tid] : null;
    return id ? id.colors : null;
  }
  function venueOf(tid) { const id = S.identity && S.identity[tid]; return id ? id.venue : null; }
  // the chip beside a school name (standings, schedule, scoreboard, picker): the primary color, text white or near-black by contrast, a thin light border when the color is too dark for the background
  function chip(team) {
    const c = colorsOf(typeof team === "number" ? { tid: team } : team);
    if (!c) return `<i class="cchip none" aria-hidden="true"></i>`;
    return `<i class="cchip ${c.border ? "bd" : ""}" style="--c:${c.chip}" title="${esc(c.primary)}${c.secondary ? " / " + esc(c.secondary) : ""}" aria-hidden="true"></i>`;
  }
  // the team mark: the school's abbreviation on its primary color (a hashed color for fictional teams without a row); the tooltip is the one spot that names the engine id
  function mark(team) {
    const c = colorsOf(team);
    const style = c ? `--team:${c.chip};--team-ink:${c.text}${c.border ? ";--team-bd:var(--line-strong)" : ""}` : `--team:${colorOf(team.engine_name || team.name)}`;
    return `<span class="mark ${c && c.border ? "bd" : ""}" style="${style}" title="${esc(team.name)}${team.engine_name ? ` · engine id: ${esc(team.engine_name)}` : ""}">${team.abbr ? esc(team.abbr) : initials(team.name)}</span>`;
  }
  // the venue line of a game: "at <ballpark> · <city>", "Charles Schwab Field Omaha", "neutral site" when nothing is confirmed
  function venueLine(v, opts) {
    const o = opts || {};
    if (v && v.text) return `${o.bare ? "" : "at "}${esc(v.text)}`;
    if (o.stage === "conf") return "Conference tournament";
    return o.neutral ? "neutral site" : "";
  }
  // the user's own team: the highlight color every screen's "you" rows use (the school's visible ink), set once per dynasty
  function setMine(team) {
    const c = colorsOf(team);
    document.documentElement.style.setProperty("--mine", c ? c.ink : "var(--accent)");
    document.documentElement.style.setProperty("--mine-ink", c ? c.ink_text : "var(--accent-ink)");
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  // ---- 1. scoreboard strip: line score | R/H/E | bases | inning | balls, strikes, outs ----
  function basesSvg(bases, size) {
    const on = (i) => (bases[i] ? "on" : "");
    return `<svg class="bases" viewBox="0 0 40 40" width="${size}" height="${size}" aria-label="bases"><rect class="b ${on(1)}" x="14" y="4" width="12" height="12" transform="rotate(45 20 10)"/><rect class="b ${on(2)}" x="4" y="14" width="12" height="12" transform="rotate(45 10 20)"/><rect class="b ${on(0)}" x="24" y="14" width="12" height="12" transform="rotate(45 30 20)"/><polygon class="home" points="16,30 24,30 24,33 20,37 16,33"/></svg>`;
  }
  function renderScorebar(t) {
    const st = t.state, inns = st.line_score.innings;
    const stripe = (side) => { const c = colorsOf(st.teams[side]); return c ? `<i class="cstripe ${c.border ? "bd" : ""}" style="--c:${c.chip}" aria-hidden="true"></i>` : ""; };
    const row = (side) => `<tr class="${st.batting_side === side && !st.over && t.phase !== "pregame" ? "batting" : ""}"><td class="team">${stripe(side)}${mark(st.teams[side])}<span class="tn" title="${esc(st.teams[side].name)}">${esc(st.teams[side].short || st.teams[side].name)}</span></td>${st.line_score[side].map((r) => `<td>${r === null ? "" : r}</td>`).join("")}<td class="tot r">${st.score[side]}</td><td class="tot">${st.hits[side]}</td><td class="tot">${st.errors[side]}</td></tr>`;
    $("#linescore").innerHTML = `<tr><th></th>${inns.map((i) => `<th>${i}</th>`).join("")}<th class="tot">R</th><th class="tot">H</th><th class="tot">E</th></tr>${row("away")}${row("home")}`;
    $("#sb-bases").innerHTML = basesSvg(st.bases, 44);
    const v = t.venue !== undefined ? t.venue : (S.game && S.game.venue !== undefined ? S.game.venue : st.venue);
    const vl = venueLine(v, { neutral: !!(t.meta && t.meta.neutral), stage: t.meta && t.meta.tournament ? (S.game && S.game.stage) : null });
    $("#venue").innerHTML = vl; $("#venue").classList.toggle("hidden", !vl);
    $("#sb-inning").innerHTML = st.over ? `<div class="half">Final${st.ended_by_run_rule ? " · run rule" : ""}</div><div class="inn">${st.inning !== 9 ? st.inning + " inn" : "9 inn"}</div>`
      : t.phase === "pregame" ? `<div class="half">Pregame</div><div class="inn">—</div>`
      : `<div class="half on">${st.half === "T" ? "Top" : "Bot"}</div><div class="inn">${ORD(st.inning)}</div>`;
    const c = st.count || [0, 0];
    const counter = (lbl, n, max, cls) => `<div class="counter ${cls}"><div class="lbl">${lbl}</div><div class="num">${n}</div><div class="dots">${Array.from({ length: max }, (_, i) => `<i class="${i < n ? "on" : ""}"></i>`).join("")}</div></div>`;
    $("#sb-counts").innerHTML = counter("B", c[0], 3, "balls") + counter("S", c[1], 2, "strikes") + counter("O", st.outs, 3, "outs");
  }

  // ---- 2. matchup banner ----
  // 20–80 badges on one color scale (system.css --r20..--r80): 20–39 red, 40–49 orange, 50–59 amber (the D1 average
  // band), 60–69 green, 70–79 elite green, 80 blue. The legend explains the scale and each rating.
  function band(v) { return v < 40 ? "r20" : v < 50 ? "r40" : v < 60 ? "r50" : v < 70 ? "r60" : v < 80 ? "r70" : "r80"; }
  function badge(k, v) { const [ab, full] = RATING[k] || [k, k]; return `<span class="rt ${band(v)}" title="${esc(full)}: ${v} (20–80, 50 = D1 median)"><span class="k">${ab}</span><b>${v}</b></span>`; }
  function chips(p) {
    return `<div class="chips">${Object.entries(p.ratings).map(([k, v]) => badge(k, v)).join("")}</div>`;
  }
  function stat(k, v) { return `<span><span class="k">${k}</span><b>${v}</b></span>`; }
  function stamColor(f) { return f < .55 ? "var(--stam-hi)" : f < .8 ? "var(--stam-mid)" : "var(--stam-lo)"; }
  function staminaBar(p) {
    // the engine's fatigue state when it has one (state.pitcher.fatigue, 0 fresh to 1 spent); until then the
    // outing's pitch count on the pull tables' range, labeled as such. Never the AI's pull odds.
    const pitches = p.outing ? p.outing.pitches : p.line.pitches;
    const hasFatigue = typeof p.fatigue === "number";
    const f = hasFatigue ? Math.max(0, Math.min(1, p.fatigue)) : Math.min(1, pitches / PITCH_SCALE);
    const label = hasFatigue ? "Fatigue" : "Pitch count";
    const title = hasFatigue ? `The engine's fatigue state (${(f * 100).toFixed(0)}%); Stamina ${p.ratings.stamina}.`
      : `Pitches this outing on the 0–${PITCH_SCALE} range of the AI's pull tables; Stamina ${p.ratings.stamina}. The engine has no fatigue state yet; this is not the AI's pull odds.`;
    const ticks = hasFatigue ? [25, 50, 75] : [25, 50, 75, 100].map((x) => x / PITCH_SCALE * 100);
    return `<div class="stamina" title="${esc(title)}"><span>${label}</span><div class="bar"><i style="width:${(f * 100).toFixed(0)}%;background:${stamColor(f)}"></i>${ticks.map((x) => `<s style="left:${x}%"></s>`).join("")}</div><span>${hasFatigue ? (f * 100).toFixed(0) + "%" : pitches + " pitches"}${p.outing ? `, ${p.outing.runs} R` : ""}</span></div>`;
  }
  function renderBanner(t) {
    const st = t.state, me = t.user_side, b = st.batter, p = st.pitcher;
    const bside = st.batting_side, pside = bside === "home" ? "away" : "home";
    const order = b ? st.lineups[bside].findIndex((x) => x.pid === b.pid) + 1 : 0;
    const you = (side) => (side === me ? '<span class="you-tag">you</span>' : "");
    $("#batter").innerHTML = `<div class="hdr">${st.count ? "At bat" : "Due up"} · ${esc(st.teams[bside].name)}${you(bside)}</div>` + (b ? `<div class="body">${mark(st.teams[bside])}
      <div class="name"><a class="plink" data-pid="${b.pid}">${esc(b.name)}</a><small>${b.pos} · bats ${b.hand || "–"}${order ? ` · ${ORD(order)} in the order` : ""}</small>${st.platoon ? `<span class="platoon ${st.platoon.batter !== st.platoon.pitcher ? "adv" : "same"}" title="${st.platoon.batter !== st.platoon.pitcher ? "platoon advantage: the batter hits from the side opposite the pitcher's hand" : "same side: the pitcher's platoon advantage"}">${st.platoon.batter} vs ${st.platoon.pitcher}${st.platoon.batter !== st.platoon.pitcher ? " · edge" : ""}</span>` : ""}</div>
      <div class="today">${stat("AB", b.line.ab)}${stat("H", b.line.h)}${stat("RBI", b.line.rbi)}${stat("BB", b.line.bb)}${stat("K", b.line.k)}${b.season ? `<span class="season on">${stat("AVG", f3(b.season.avg))}${stat("OBP", f3(b.season.obp))}${stat("SLG", f3(b.season.slg))}${stat("HR", b.season.hr)}</span>` : `<span class="season">${stat("AVG", "")}${stat("HR", "")}${stat("SB", "")}</span>`}</div>
      ${chips(b)}</div>` : `<div class="body empty">${t.phase === "pregame" ? "Lineups are set when the game starts" : "No batter yet"}</div>`);
    const pitches = p ? (p.outing ? p.outing.pitches : p.line.pitches) : 0;
    $("#pitcher").innerHTML = `<div class="hdr">Pitching · ${esc(st.teams[pside].name)}${you(pside)}</div>` + (p ? `<div class="body">${mark(st.teams[pside])}
      <div class="name"><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a><small>${p.role} · throws ${p.hand || "–"}</small></div>
      <div class="today">${stat("IP", p.line.ip)}${stat("H", p.line.h)}${stat("R", p.line.r)}${stat("BB", p.line.bb)}${stat("K", p.line.k)}${stat("P", pitches)}${p.season ? `<span class="season on">${stat("ERA", p.season.era.toFixed(2))}${stat("IP", p.season.ip)}${stat("K", p.season.k)}</span>` : `<span class="season">${stat("W-L", "")}${stat("ERA", "")}${stat("IP", "")}</span>`}</div>
      ${staminaBar(p)}
      ${chips(p)}</div>` : `<div class="body empty">${t.phase === "pregame" ? "The starters are named when the game starts" : "No pitcher yet"}</div>`);
  }

  // ---- 3. field: an original vector diamond (mown stripes, dirt infield arc, warning track), fielders as small
  //      position badges with names, runners lit on the bases (tap or hover for ratings). The batter is in the
  //      banner, not on the grass. ----
  const BASES = { 1: [250, 160], 2: [160, 70], 3: [70, 160] };
  const TAG_AT = { 1: (x, y) => [x, y + 27, "middle"], 2: (x, y) => [x, y - 17, "middle"], 3: (x, y) => [x, y + 27, "middle"] };
  const FIELDERS = [["P", 160, 168], ["C", 160, 280], ["1B", 236, 128], ["2B", 198, 98], ["SS", 122, 98], ["3B", 84, 128], ["LF", 68, 52], ["CF", 160, 18], ["RF", 252, 52]];
  function renderField(t) {
    const st = t.state, bside = st.batting_side, fside = bside === "home" ? "away" : "home";
    const byPid = {};
    ["lineups", "bench"].forEach((g) => ["away", "home"].forEach((s) => (st[g][s] || []).forEach((p) => (byPid[p.pid] = p))));
    const runner = (i, b) => {
      if (!b) return "";
      const [x, y] = BASES[i + 1];
      const p = byPid[b.pid] || { ratings: {} };
      const r = p.ratings || {};
      return `<g class="runner" tabindex="0" data-name="${esc(b.name)}" data-pos="${p.pos || ""}" data-spd="${r.speed ?? "–"}" data-con="${r.contact ?? "–"}" data-pow="${r.power ?? "–"}" data-line="${esc(p.line_text || "0-0")}">
        <circle cx="${x}" cy="${y}" r="12"/><text x="${x}" y="${y + 4}">${i + 1}</text>${((tag) => `<text class="tag" x="${tag[0]}" y="${tag[1]}" style="text-anchor:${tag[2]}">${esc(b.name)}</text>`)(TAG_AT[i + 1](x, y))}</g>`;
    };
    const lu = st.lineups[fside] || [];
    const who = Object.fromEntries(lu.filter((p) => p.pos !== "DH").map((p) => [p.pos, p]));
    if (st.pitcher) who.P = st.pitcher;
    const fielder = ([n, x, y]) => `<g class="fielder"><rect x="${x - 13}" y="${y - 8}" width="26" height="14" rx="2"/><text class="pos" x="${x}" y="${y + 3}" text-anchor="middle">${n}</text>${who[n] ? `<text class="fname" x="${x}" y="${y + 17}" text-anchor="middle">${esc(who[n].name)}</text>` : ""}</g>`;
    const on = st.bases.some(Boolean);
    $("#field").innerHTML = `<div class="hdr">Field <span class="sub">${t.phase === "pregame" ? "" : on ? "tap a runner for his ratings" : ""}</span></div>
      <svg class="diamond" viewBox="0 0 320 300" aria-label="diamond">
        <defs>
          <clipPath id="fan"><path d="M160 262 L4 106 Q160 -70 316 106 Z"/></clipPath>
        </defs>
        <rect class="turf" x="0" y="0" width="320" height="300"/>
        <g clip-path="url(#fan)">
          <rect class="turf" x="0" y="0" width="320" height="300"/>
          ${[0, 1, 2, 3, 4, 5, 6].map((i) => `<rect class="stripe" x="0" y="${i * 40}" width="320" height="20"/>`).join("")}
          <path class="track" d="M4 106 Q160 -70 316 106 L306 114 Q160 -50 14 114 Z"/>
          <path class="fence" d="M4 106 Q160 -70 316 106" fill="none"/>
          <circle class="dirt" cx="160" cy="166" r="104"/>
          <polygon class="turf-in" points="160,228 228,160 160,92 92,160"/>
          <circle class="dirt" cx="160" cy="166" r="12"/>
          <circle class="dirt" cx="160" cy="252" r="20"/>
        </g>
        <line class="foul" x1="160" y1="252" x2="4" y2="106"/><line class="foul" x1="160" y1="252" x2="316" y2="106"/>
        <rect class="base" x="243" y="153" width="14" height="14" transform="rotate(45 250 160)"/>
        <rect class="base" x="153" y="63" width="14" height="14" transform="rotate(45 160 70)"/>
        <rect class="base" x="63" y="153" width="14" height="14" transform="rotate(45 70 160)"/>
        <polygon class="base" points="153,246 167,246 167,252 160,258 153,252"/>
        <rect class="rubber" x="156" y="164" width="8" height="3"/>
        ${FIELDERS.map(fielder).join("")}
        ${st.bases.map((b, i) => runner(i, b)).join("")}
      </svg>`;
    const due = st.due_up.map((n) => esc(n));
    $("#ondeck").innerHTML = `<span class="k">On deck</span><b>${due[0] || "—"}</b><span class="k">In the hole</span><b>${due[1] || "—"}</b>`;
    const tip = $("#tip");
    const show = (g) => {
      const d = g.dataset;
      tip.innerHTML = `<b>${d.name}</b> ${d.pos}<br>${badge("speed", +d.spd)} ${badge("contact", +d.con)} ${badge("power", +d.pow)}<br>Today ${d.line}`;
      tip.classList.remove("hidden");
      const r = g.getBoundingClientRect();
      tip.style.left = Math.max(8, Math.min(window.innerWidth - 270, r.left - 60)) + "px"; tip.style.top = (r.bottom + 6) + "px";
      tip._for = g;
    };
    $$("#field .runner").forEach((g) => {
      g.addEventListener("mouseenter", () => show(g));
      g.addEventListener("mouseleave", () => tip.classList.add("hidden"));
      g.addEventListener("click", (e) => { e.stopPropagation(); if (!tip.classList.contains("hidden") && tip._for === g) tip.classList.add("hidden"); else show(g); });
    });
  }

  // ---- 4. action menu: the calls legal now for the side you are on, built by the server (app/menu.py);
  //      tapping queues the order, the sim buttons proceed with the AI handling anything not queued ----
  function playerOf(pid) {
    const st = S.game.turn.state;
    for (const side of ["away", "home"]) for (const grp of ["lineups", "bench", "bullpen", "used_pitchers"]) { const p = (st[grp][side] || []).find((x) => x.pid === pid); if (p) return p; }
    return { pid, name: `#${pid}`, ratings: {} };
  }
  function pickCard(p) {
    const r = p.ratings || {};
    const keys = p.side === "pit" ? ["stuff", "control", "movement", "stamina"] : ["contact", "power", "speed", "glove"];
    const meta = `${p.side === "pit" ? p.role : p.pos}${p.line_text ? " · today " + p.line_text : ""}`;
    return `<button class="pick" data-pid="${p.pid}"><span>${esc(p.name)} <span class="why">${esc(meta)}</span></span><span class="chips">${keys.map((k) => (r[k] != null ? badge(k, r[k]) : "")).join("")}</span></button>`;
  }
  function orderFor(item, pid, slot) {
    // the order an item sends once its player (and slot) is picked (app/menu.py's shapes)
    const v = item.value;
    if (item.kind === "pinch_hit") return pid;
    if (item.kind === "pitching_change") return { yes: true, reliever: pid };
    if (item.kind === "defensive_subs") return [[slot, pid]];
    if (v && "pinch_runner" in v) return { pinch_runner: pid, slot: v.slot };
    if (v && "pitching_change" in v) return { pitching_change: pid };
    if (v && "defensive_sub" in v) return { defensive_sub: [slot, pid] };
    return v;
  }
  function chooser(item, question) {
    // the inline picker under an item that needs a player (a lineup slot too for a defensive change)
    const st = S.game.turn.state, me = S.game.turn.user_side;
    const pool = item.pick.options.map(playerOf);
    const slots = item.pick.what === "sub" ? `<label class="slot">For the slot <select id="pick-slot">${st.lineups[me].map((p, i) => `<option value="${i}">${i + 1}. ${esc(p.name)} (${p.pos})</option>`).join("")}</select></label>` : "";
    const html = `<div class="chooser" data-for="${item.id}">${slots}<div class="picks">${pool.map(pickCard).join("")}</div><button class="btn-ghost" data-cancel="1">Cancel</button></div>`;
    return { html, send: (pid, slot) => (question ? decide(item.kind, orderFor(item, pid, slot)) : order(item.kind, orderFor(item, pid, slot))) };
  }
  async function order(kind, value) { applyTurn(await gameCall("/orders", "POST", { kind, value })); }
  async function decide(kind, value) { applyTurn(await gameCall("/decide", "POST", { kind, value })); calloutFor(S.game.turn.events, "pa"); }
  let openPick = null;                 // the item whose picker is open
  function questionBlock(t) {
    // a kind on "ask me": the engine waits for this answer; the menu items of that kind answer it, other kinds
    // get a plain chooser from the pending question's shape (app/catalogue.py)
    const p = t.pending, st = t.state, me = t.user_side;
    let body = "";
    const inMenu = t.menu.some((i) => i.kind === p.kind);
    if (!inMenu) {
      if (p.answer === "choice3" || p.answer === "generic") body = `<div class="picks row-picks"><button data-answer='"yes"'>Yes</button><button data-answer='"no"'>No</button><button data-answer='"league_rate"'>Let them play (league rate)</button></div>`;
      else if (p.answer === "pick_batter") body = `<div class="picks"><button data-answer="null">No one</button>${p.options.map((pid) => pickCard(playerOf(pid))).join("")}</div>`;
      else if (p.answer === "pick_pitcher") body = `<div class="picks">${p.options.map((pid) => pickCard(playerOf(pid))).join("")}</div>`;
      else if (p.answer === "pitching_change") body = `<div class="picks"><button data-answer='"no"'>No change</button>${p.options.map((pid) => pickCard(playerOf(pid))).join("")}</div>`;
      else if (p.answer === "subs") body = `<label class="slot">For the slot <select id="q-slot">${st.lineups[me].map((x, i) => `<option value="${i}">${i + 1}. ${esc(x.name)} (${x.pos})</option>`).join("")}</select></label><div class="picks"><button data-answer="[]">No change</button>${p.options.map((pid) => pickCard(playerOf(pid))).join("")}</div>`;
      else body = `<div class="why">Set before the game.</div>`;
    }
    return `<div class="question" data-kind="${p.kind}" data-answer-type="${p.answer}"><b>Your call: ${esc(p.label)}</b><div class="why">${inMenu ? "Pick one of the calls below." : "The engine is waiting for this decision (you asked to be asked)."}${p.legal ? "" : " " + esc(p.reason)}</div>${body}
      <button class="btn-ghost" data-q-auto="${p.kind}">Let the AI decide this one</button></div>`;
  }
  function renderActions(t) {
    const st = t.state, question = t.phase === "question";
    const side = st.batting_side === t.user_side ? "You bat" : "You pitch";
    const when = st.over ? "final" : t.phase === "pregame" ? "pregame" : st.count ? "before the next pitch" : "before the at-bat";
    const items = t.menu.filter((i) => !question || i.kind === t.pending.kind);
    const anyQueued = t.orders.length > 0;
    const pregameNote = t.phase === "pregame" ? `<div class="why">Your batting order and starter are the AI's picks: change them in the Lineup panel${window.innerWidth <= 760 ? ' (<a href="#" data-goto="lineup">open it</a>)' : ""} before the first pitch.</div>` : "";
    const off = st.over || question || S.busy;
    $("#actions").innerHTML = `<div class="hdr">Strategy <span class="sub">${side} · ${when}</span></div>${pregameNote}${question ? questionBlock(t) : ""}
      ${["pitching", "defense", "offense"].filter((g) => items.some((i) => i.group === g)).map((g) => `<div class="group"><div class="ghdr">${{ pitching: "Pitching", defense: "Defense", offense: "Offense" }[g]}</div><div class="menu">${items.filter((i) => i.group === g).map((i) => `<button data-item="${i.id}" class="${i.default ? "default" : ""} ${i.queued ? "queued" : ""} ${openPick === i.id ? "open" : ""}" ${i.enabled ? "" : "disabled"}><span>${esc(i.label)}</span>${i.queued ? `<span class="key you">queued</span>` : i.reason ? `<span class="why">${esc(i.reason)}</span>` : i.default ? `<span class="key">default</span>` : i.pick ? `<span class="key">pick…</span>` : ""}</button>${openPick === i.id ? chooser(i, question).html : ""}`).join("")}</div></div>`).join("")}
      ${anyQueued && !question ? `<div class="orders">${t.orders.map((o) => `<span>${esc(orderText(o))}</span>`).join("")} <button class="btn-ghost" data-clear-all="1">Clear</button></div>` : ""}
      <div class="coach"><div class="tools"><button class="btn-ghost" id="coach-btn">Ask bench coach</button><button class="btn-ghost" id="ask-btn">Ask me…</button><button class="btn-ghost" id="legend-btn">Rating legend</button></div><div id="coach-out" class="hidden"></div><div id="ask-panel" class="hidden"></div></div></div>`;
    renderSims(t, off);
    const go = $("#actions [data-goto]");
    if (go) go.addEventListener("click", (e) => { e.preventDefault(); $(`#phone-tabs [data-tab="lineup"]`).click(); });
    $("#legend-btn").addEventListener("click", () => $("#legend").classList.toggle("hidden"));
    $("#coach-btn").addEventListener("click", () => busy(async () => {
      const c = await gameCall("/coach");
      const lines = c.advice.filter((a) => !a.pids).map((a) => `<div>${esc(a.label)}: ${esc(a.text || a.name || "")}</div>`);
      S.coach = `<b>Bench coach</b> (what the AI would do for your team next): ${lines.length ? lines.join("") : "<div>nothing to call before the next pitch</div>"}`;
    }));
    if (S.coach) { $("#coach-out").innerHTML = S.coach; $("#coach-out").classList.remove("hidden"); }
    $("#ask-btn").addEventListener("click", () => { const p = $("#ask-panel"); p.classList.toggle("hidden"); renderAsk(t); });
    // items
    $$("#actions [data-item]").forEach((b) => b.addEventListener("click", () => {
      const item = t.menu.find((i) => i.id === b.dataset.item);
      if (item.pick) { openPick = openPick === item.id ? null : item.id; return renderActions(t); }
      if (item.queued && !question) return busy(() => order(item.kind, null));           // tap again: cancel
      busy(() => (question ? decide(item.kind, item.value) : order(item.kind, item.value)));
    }));
    const ch = $("#actions .chooser");
    if (ch) {
      const item = t.menu.find((i) => i.id === ch.dataset.for), c = chooser(item, question);
      $$("#actions .chooser [data-pid]").forEach((b) => b.addEventListener("click", () => { openPick = null; busy(() => c.send(+b.dataset.pid, ch.querySelector("#pick-slot") ? +ch.querySelector("#pick-slot").value : 0)); }));
      ch.querySelector("[data-cancel]").addEventListener("click", () => { openPick = null; renderActions(t); });
    }
    const qb = $("#actions .question");
    if (qb) {
      $$("#actions .question [data-answer]").forEach((b) => b.addEventListener("click", () => busy(() => decide(qb.dataset.kind, JSON.parse(b.dataset.answer)))));
      $$("#actions .question [data-pid]").forEach((b) => b.addEventListener("click", () => {
        const pid = +b.dataset.pid, type = qb.dataset.answerType;
        const v = type === "pitching_change" ? { yes: true, reliever: pid } : type === "subs" ? [[+$("#q-slot").value, pid]] : pid;
        busy(() => decide(qb.dataset.kind, v));
      }));
    }
    const ca = $("#actions [data-clear-all]");
    if (ca) ca.addEventListener("click", () => busy(async () => { for (const o of t.orders) await order(o.kind, null); }));
  }
  function renderSims(t, off) {
    const sims = t.phase === "pregame"
      ? `<button class="go" data-sim="pitch" title="key: Space or N">Play ball</button>`
      : `<button class="go" data-sim="pitch" title="key: Space or N">Next pitch</button><button data-sim="pa" title="key: A">At-bat</button><button data-sim="half" title="key: H">Half inning</button><button data-sim="inning" title="key: I">Inning</button><button data-sim="three_innings" title="key: 3">3 innings</button><button data-sim="game" title="key: E">End of game</button><button class="btn-ghost" data-keys="1" title="key: ?">Keys</button>`;
    const back = S.game && S.game.dynasty ? (t.state.over ? `<button class="go" data-dyn-finish="1">Back to the dynasty</button>` : `<button class="btn-ghost" data-dyn-back="1">Dynasty</button>`) : "";
    const league = $("#league-sim") ? $("#league-sim").outerHTML : "";
    $("#simbar").innerHTML = `<span class="k">Sim</span>${t.state.over && S.game && S.game.dynasty ? "" : sims}${back}${league}`;
    $$("#simbar [data-sim]").forEach((b) => (b.disabled = off));
    if (window.cbsLoad.locked()) window.cbsLoad.simLock(true);
  }
  function orderText(o) {
    const d = S.decisions.kinds.find((k) => k.kind === o.kind), v = o.value;
    const name = (pid) => playerOf(pid).name;
    let what;
    if (v === "auto") what = "AI decides";
    else if (typeof v === "number") what = name(v);
    else if (Array.isArray(v)) what = v.map((x) => (Array.isArray(x) ? `${name(x[1])} in at ${x[0] + 1}` : name(x))).join(", ");
    else if (v && typeof v === "object") what = "pinch_runner" in v ? `${name(v.pinch_runner)} runs` : "pitching_change" in v ? `${name(v.pitching_change)} in` : "defensive_sub" in v ? `${name(v.defensive_sub[1])} in at ${v.defensive_sub[0] + 1}` : v.yes ? `yes, ${name(v.reliever)}` : "no";
    else what = String(v).replace(/_/g, " ");
    return `${d ? d.label : o.kind}: ${what}`;
  }
  function renderAsk(t) {
    const p = $("#ask-panel");
    p.innerHTML = `<div class="why">Autopilot answers every decision you have not queued. Tick a decision to be stopped and asked each time.</div>` +
      S.decisions.kinds.filter((k) => k.when !== "pregame").map((k) => `<label class="ask"><input type="checkbox" data-mode="${k.kind}" ${t.modes[k.kind] === "ask" ? "checked" : ""}> ${esc(k.label)}</label>`).join("");
    $$("#ask-panel [data-mode]").forEach((c) => c.addEventListener("change", () => busy(async () => { applyTurn(await gameCall("/modes", "POST", { kind: c.dataset.mode, mode: c.checked ? "ask" : "auto" })); S.askOpen = true; })));
  }

  // ---- 5. lineup panel: batting order with position, bats, today's results and H-AB; the opponent's lineup;
  //      the bullpen with each pitcher's status; before the game, the lineup and starter editor ----
  function resChips(list, last) {
    const all = list || [], shown = last && all.length > last ? all.slice(-last) : all;
    const title = all.length ? `today: ${all.map((r) => (RES[r] || [r])[0]).join(", ")}` : "";
    return `<span class="res" title="${esc(title)}">${shown.map((r) => { const [lab, cls] = RES[r] || [r, "out"]; return `<i class="${cls}">${lab}</i>`; }).join("")}</span>`;
  }
  let lineupTab = "mine";
  function renderLineup(t, tab) {
    const st = t.state, me = t.user_side, opp = me === "home" ? "away" : "home";
    lineupTab = tab || lineupTab;
    const side = lineupTab === "opp" ? opp : me;
    let body;
    if (t.phase === "pregame" && lineupTab === "mine") body = pregameEditor(t);
    else if (lineupTab === "pen") {
      const cur = st.pitcher && st.pitcher.pid;
      const hasSeasonP = st.bullpen[me].concat(st.used_pitchers[me]).some((p) => p.season);
      const seasonP = (p) => (hasSeasonP ? `<td class="num">${p.season ? p.season.era.toFixed(2) : ""}</td><td class="num">${p.season ? p.season.ip : ""}</td><td class="num">${p.season ? p.season.k : ""}</td>` : "");
      const who = (p) => `<td class="nm"><div><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a></div><small>${p.role} · throws ${p.hand || "–"}</small></td>`;
      const rows = st.bullpen[me].map((p) => `<tr>${who(p)}<td class="avail">${t.phase === "pregame" ? "rested" : "available"}</td><td>${badge("stamina", p.ratings.stamina).replace('<span class="k">Sta</span>', "")}</td>${seasonP(p)}</tr>`)
        .concat(st.used_pitchers[me].map((p) => `<tr class="bp ${p.pid === cur ? "now" : ""}">${who(p)}<td class="avail ${p.pid === cur ? "" : "used"}">${p.pid === cur ? "pitching" : `used · ${p.line.ip} IP, ${p.line.pitches} P`}</td><td>${badge("stamina", p.ratings.stamina).replace('<span class="k">Sta</span>', "")}</td>${seasonP(p)}</tr>`));
      body = `<table class="lu tbl bp"><tr><th>Pitcher</th><th>Status</th><th>Sta</th>${hasSeasonP ? `<th class="num">ERA</th><th class="num">IP</th><th class="num">K</th>` : ""}</tr>${rows.join("")}</table>${hasSeasonP ? "" : `<div class="muted">Every pitcher is rested: this is an exhibition.</div>`}`;
    } else {
      const lu = st.lineups[side] || [];
      const cur = st.batter && st.batting_side === side ? st.batter.pid : null;
      const curIdx = cur ? lu.findIndex((p) => p.pid === cur) : -1;
      // season columns (AVG/OBP/SLG/HR) show in dynasty games, where the players carry a season line; exhibitions keep H-AB (never faked)
      const hasSeason = lu.some((p) => p.season);
      const seasonTh = hasSeason ? `<th class="num">AVG</th><th class="num">OBP</th><th class="num">SLG</th><th class="num">HR</th>` : `<th class="num">H-AB</th>`;
      const seasonTd = (p) => (hasSeason ? `<td class="num">${f3(p.season.avg)}</td><td class="num">${f3(p.season.obp)}</td><td class="num">${f3(p.season.slg)}</td><td class="num">${p.season.hr}</td>` : `<td class="num hab">${p.line.h}-${p.line.ab}</td>`);
      body = lu.length ? `<table class="lu tbl"><tr><th>#</th><th>Batter</th><th>Today</th>${seasonTh}</tr>${lu.map((p, i) => `<tr class="${p.pid === cur ? "now" : ""} ${curIdx >= 0 && i === (curIdx + 1) % 9 ? "deck" : ""} ${p.on_base ? "onbase" : ""}"><td class="n">${i + 1}</td><td class="nm"><div><a class="plink" data-pid="${p.pid}">${esc(p.name)}</a>${p.on_base ? ' <span class="ob">on</span>' : ""}</div><small>${p.pos} · bats ${p.hand || "–"}</small></td><td class="today">${resChips(st.pa_results[String(p.pid)], 3)}</td>${seasonTd(p)}</tr>`).join("")}</table>`
        : `<div class="muted">The AI sets the ${esc(st.teams[side].name)} lineup when the game starts.</div>`;
    }
    const short = (tm) => esc(tm.abbr || tm.short || tm.name);
    $("#lineup").innerHTML = `<div class="hdr">Lineup</div><div class="tabs"><button data-tab="mine" class="${lineupTab === "mine" ? "on" : ""}" title="${esc(st.teams[me].name)}">${short(st.teams[me])}</button><button data-tab="opp" class="${lineupTab === "opp" ? "on" : ""}" title="${esc(st.teams[opp].name)}">${short(st.teams[opp])}</button><button data-tab="pen" class="${lineupTab === "pen" ? "on" : ""}">Bullpen</button></div>${body}`;
    $$("#lineup .tabs button").forEach((b) => b.addEventListener("click", () => renderLineup(t, b.dataset.tab)));
    if (t.phase === "pregame" && lineupTab === "mine") bindPregame(t);
  }
  // the pregame editor: the AI's lineup and starter prefilled (the bench coach's answer), reorder or swap with the bench
  async function preparePregame() {
    const t = S.game.turn, me = t.user_side, st = t.state;
    const coach = await gameCall("/coach");
    const lu = coach.advice.find((a) => a.kind === "lineup"), sp = coach.advice.find((a) => a.kind === "starting_pitcher");
    const batters = st.bench[me], pitchers = st.bullpen[me];
    S.pregame = { lineup: lu ? lu.pids.slice() : batters.slice(0, 9).map((p) => p.pid), aiLineup: lu ? lu.pids.slice() : null,
                  sp: sp ? sp.pid : pitchers[0].pid, aiSp: sp ? sp.pid : null };
  }
  function pregameEditor(t) {
    const pg = S.pregame, st = t.state, me = t.user_side;
    if (!pg) return `<div class="muted">Loading the AI's lineup…</div>`;
    const byPid = Object.fromEntries(st.bench[me].map((p) => [p.pid, p]));
    const bench = st.bench[me].filter((p) => !pg.lineup.includes(p.pid));
    const rows = pg.lineup.map((pid, i) => {
      const p = byPid[pid];
      const opts = [p].concat(bench).map((q) => `<option value="${q.pid}" ${q.pid === pid ? "selected" : ""}>${esc(q.name)} (${q.pos}) Con ${q.ratings.contact} Pow ${q.ratings.power} Spd ${q.ratings.speed}</option>`).join("");
      return `<tr><td class="n">${i + 1}</td><td><select data-slot="${i}">${opts}</select></td><td class="mv"><button data-up="${i}" ${i === 0 ? "disabled" : ""} title="move up">Up</button><button data-down="${i}" ${i === 8 ? "disabled" : ""} title="move down">Down</button></td></tr>`;
    }).join("");
    const sps = st.bullpen[me].map((p) => `<option value="${p.pid}" ${p.pid === pg.sp ? "selected" : ""}>${esc(p.name)} ${p.role} · Stf ${p.ratings.stuff} Ctl ${p.ratings.control} Mov ${p.ratings.movement} Sta ${p.ratings.stamina}${p.pid === pg.aiSp ? " · AI's pick" : ""}</option>`).join("");
    const changed = pg.aiLineup && (pg.aiLineup.join() !== pg.lineup.join() || pg.sp !== pg.aiSp);
    return `<div class="muted">Your batting order and starter: the AI's picks, yours to change. Play ball sends them.</div>
      <table class="lu tbl edit">${rows}</table>
      <label class="slot">Starting pitcher <select id="sp-pick">${sps}</select></label>
      ${changed ? `<button class="btn-ghost" id="lineup-reset">Back to the AI's lineup</button>` : ""}`;
  }
  function bindPregame(t) {
    const pg = S.pregame; if (!pg) return;
    $$("#lineup select[data-slot]").forEach((s) => s.addEventListener("change", (e) => { pg.lineup[+e.target.dataset.slot] = +e.target.value; renderLineup(t); }));
    $$("#lineup [data-up]").forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.up; [pg.lineup[i - 1], pg.lineup[i]] = [pg.lineup[i], pg.lineup[i - 1]]; renderLineup(t); }));
    $$("#lineup [data-down]").forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.down; [pg.lineup[i + 1], pg.lineup[i]] = [pg.lineup[i], pg.lineup[i + 1]]; renderLineup(t); }));
    $("#sp-pick").addEventListener("change", (e) => { pg.sp = +e.target.value; renderLineup(t); });
    const r = $("#lineup-reset");
    if (r) r.addEventListener("click", () => { pg.lineup = pg.aiLineup.slice(); pg.sp = pg.aiSp; renderLineup(t); });
  }
  async function sendPregame() {
    const pg = S.pregame; if (!pg) return;
    if (!pg.aiLineup || pg.aiLineup.join() !== pg.lineup.join()) await order("lineup", pg.lineup);
    if (pg.sp !== pg.aiSp) await order("starting_pitcher", pg.sp);
  }

  // ---- 6. play-by-play: newest first; non-events hidden (a call held off, a lineup set, a dropped order);
  //      moves the AI made for your team tagged AI, yours YOU, the opponent's OPP; a box score tab ----
  const HIDE = /no change|lineup set|no bunt|held off|runners may go|runners held|^Note:|the moment passed/i;
  let feedTab = "plays";
  function renderFeed(events, me, teams) {
    const rows = events.filter((e) => !(e.type === "decision" && HIDE.test(e.text))).slice(-400).reverse().map((e) => {
      let badge = "", text = e.text;
      if (e.type === "decision") {
        text = text.replace(/^(You|AUTO \(AI ran your team\)|.+? \(AI\)|Note): /, "");
        badge = e.source === "auto" ? `<span class="badge ai" title="the AI made this move for your team">AI</span>` : e.source === "order" ? `<span class="badge you">YOU</span>` : e.source === "ai" ? `<span class="badge opp">OPP</span>` : "";
      }
      return `<div class="ev ${e.type}">${badge}<span>${esc(text)}</span></div>`;
    });
    const n = rows.length;
    $("#feed-body").innerHTML = `<div class="tabs"><button data-ftab="plays" class="${feedTab === "plays" ? "on" : ""}">Plays</button><button data-ftab="box" class="${feedTab === "box" ? "on" : ""}">Box score</button></div>
      <div id="feed-plays" class="${feedTab === "plays" ? "" : "hidden"}">${rows.join("") || "<div class='ev'>Nothing yet.</div>"}</div><div id="feed-box" class="${feedTab === "box" ? "" : "hidden"}"></div>`;
    $("#drawer-title").textContent = `Play by play (${n})`;
    $$("#feed-body [data-ftab]").forEach((b) => b.addEventListener("click", () => { feedTab = b.dataset.ftab; renderFeed(events, me, teams); }));
    if (feedTab === "box") renderBox();
  }
  async function renderBox() {
    const el = $("#feed-box");
    el.innerHTML = window.cbsLoad.skeleton(8, 7);
    let b;
    try { b = await gameCall("/box"); } catch (e) { el.innerHTML = window.cbsLoad.errorPanel(e.message || String(e), () => renderBox(), "Couldn't load the box score"); return; }
    const batCols = ["ab", "r", "h", "rbi", "bb", "k", "hr", "sb", "cs"], pitCols = ["ip", "h", "r", "er", "bb", "k", "pitches"];
    const bv = venueLine(S.game && S.game.venue !== undefined ? S.game.venue : b.venue, { neutral: !!(S.game && S.game.meta && S.game.meta.neutral) });
    const decOf = (pid) => (b.decisions ? (b.decisions.W === pid ? "W" : b.decisions.L === pid ? "L" : b.decisions.SV === pid ? "SV" : (b.decisions.HLD || []).includes(pid) ? "HLD" : "") : "");
    const sum = (rows, k) => rows.reduce((s, r) => s + (r.line[k] || 0), 0);
    const bat = (side) => `<h3>${esc(b.teams[side])} batting</h3><table class="lu box"><tr><th>Batter</th><th>Pos</th><th>B</th>${batCols.map((c) => `<th>${c.toUpperCase()}</th>`).join("")}</tr>${b.batting[side].map((r) => `<tr><td class="nm">${r.starter ? "" : "&nbsp;&nbsp;"}<a class="plink" data-pid="${r.pid}">${esc(r.name)}</a></td><td>${r.pos}</td><td class="muted">${r.bats || "–"}</td>${batCols.map((c) => `<td>${r.line[c]}</td>`).join("")}</tr>`).join("")}<tr class="tot"><td>Totals</td><td></td><td></td>${batCols.map((c) => `<td>${sum(b.batting[side], c)}</td>`).join("")}</tr></table>`;
    const pit = (side) => `<h3>${esc(b.teams[side])} pitching</h3><table class="lu box"><tr><th>Pitcher</th><th>T</th>${pitCols.map((c) => `<th>${c === "pitches" ? "P" : c.toUpperCase()}</th>`).join("")}</tr>${b.pitching[side].map((r) => { const dec = decOf(r.pid) || r.line.dec; return `<tr><td class="nm"><a class="plink" data-pid="${r.pid}">${esc(r.name)}</a> <span class="muted">${r.role}</span>${dec ? ` <span class="pill ${dec === "L" ? "loss" : "success"}">${dec}</span>` : ""}</td><td class="muted">${r.throws || "–"}</td>${pitCols.map((c) => `<td>${r.line[c]}</td>`).join("")}</tr>`; }).join("")}</table>`;
    el.innerHTML = `${bv ? `<div class="muted venue-line">${bv}</div>` : ""}<div class="box-grid"><div>${bat("away")}${pit("away")}</div><div>${bat("home")}${pit("home")}</div></div>`;
  }

  // ---- 7. callouts: a brief overlay for the big moments of the events a turn brought (runs, home runs,
  //      strikeouts, double plays, pitching changes, the final), auto-dismissing, a tap skips it ----
  function callout(big, sub) {
    const c = $("#callout");
    c.innerHTML = `<div class="box"><div class="big">${esc(big)}</div>${sub ? `<div class="sub">${esc(sub)}</div>` : ""}<div class="hint">tap to skip</div></div>`;
    c.classList.remove("hidden");
    clearTimeout(c._h); c._h = setTimeout(() => c.classList.add("hidden"), 1800);
    c.onclick = () => c.classList.add("hidden");
  }
  function moment(e) {
    if (e.type === "final") return ["FINAL", e.text.replace(/^Final: /, "")];
    if (e.type === "pa" && e.runs >= 2) return [`${e.runs} RUNS SCORE`, e.text];
    if (e.type === "pa" && e.res === "HR") return ["HOME RUN", e.text];
    if (e.type === "pa" && e.runs === 1) return ["RUN SCORES", e.text];
    if (e.type === "pa" && /double play/i.test(e.text)) return ["DOUBLE PLAY", e.text];
    if (e.type === "pa" && e.res === "K") return ["STRIKEOUT", e.text];
    if (e.type === "run" && /^Stolen base/.test(e.text)) return ["STOLEN BASE", e.text];
    if (e.type === "run" && /^Caught stealing/.test(e.text)) return ["CAUGHT STEALING", e.text];
    if (e.type === "decision" && /comes in to pitch|comes in for/.test(e.text)) return ["PITCHING CHANGE", e.text.replace(/^.+?: /, "")];
    return null;
  }
  function calloutFor(events, target) {
    // one callout per turn: the final above all, else the last big moment; after a long sim only the
    // moments worth a stop (runs, the final), the rest is in the feed
    const fin = events.find((e) => e.type === "final");
    if (fin) return callout(...moment(fin));
    const short = !target || target === "pitch" || target === "pa";
    const big = [...events].reverse().map(moment).find((m) => m && (short || /RUN|FINAL/.test(m[0])));
    if (big) callout(...big);
  }

  // ---- legend ----
  function renderLegend() {
    const scale = [["r20", "20–39"], ["r40", "40–49"], ["r50", "50–59"], ["r60", "60–69"], ["r70", "70+"]];
    $("#legend").innerHTML = `<div class="hdr">Ratings <span class="sub">20–80, 50 = D1 median, 10 per SD · 70+ blue, 60s green, 50s plain, 40s orange, under 40 red</span></div>
      <div class="scale">${scale.map(([c, l]) => `<span class="rt ${c}"><b>${l}</b></span>`).join("")}</div>
      <dl>${Object.values(RATING).map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("")}</dl>
      <div class="muted">B = bats (L, R, or S for a switch hitter), T = throws. The banner's "L vs R" is the side the batter hits from today against the pitcher's hand.</div>`;
  }

  // ---- phone tabs and drawer ----
  $$("#phone-tabs button").forEach((b) => b.addEventListener("click", () => {
    $$("#phone-tabs button").forEach((x) => x.classList.toggle("on", x === b));
    const tab = b.dataset.tab;
    $("#feed").classList.toggle("on", tab === "feed");
    document.body.dataset.tab = tab;
    window.scrollTo(0, 0);
  }));
  document.addEventListener("click", () => $("#tip").classList.add("hidden"));
  $("#drawer-toggle").addEventListener("click", () => { const d = $("#feed"); if (d.hasAttribute("open")) d.removeAttribute("open"); else d.setAttribute("open", ""); });

  // ---- render a turn ----
  function render(t) {
    renderScorebar(t); renderBanner(t); renderField(t); renderActions(t); renderLineup(t); renderFeed(S.events, t.user_side, t.state.teams); renderLegend();
  }

  // ---- sim ----
  async function sim(target) {
    const t = S.game.turn;
    if (t.phase === "question") return toast("Answer the pending question first.");
    S.coach = null;
    if (t.phase === "pregame") await sendPregame();
    applyTurn(await gameCall("/sim", "POST", { target }));
    calloutFor(S.game.turn.events, target);
  }
  const SIM_LABEL = { pitch: "Pitching…", pa: "Simming the at-bat…", half: "Simming the half inning…", inning: "Simming the inning…", three_innings: "Simming 3 innings…", game: "Simming to the end…" };
  const SIM_TITLE = { pitch: "Next pitch", pa: "Simming the at-bat", half: "Simming the half inning", inning: "Simming the inning", three_innings: "Simming three innings", game: "Simming to end of game" };
  // a sim from a click or a key: the matching button lights up, every sim control locks until the answer is back
  function runSim(target, btn) {
    if (window.cbsLoad.locked() || S.busy) return;
    const t = S.game && S.game.turn;
    if (t && t.phase === "question") return toast("Answer the pending question first.");
    btn = btn || $(`#simbar [data-sim="${target}"]`) || $('#simbar [data-sim="pitch"]');      // at pregame only Play ball is there: it lights up
    const label = t && t.phase === "pregame" && target === "pitch" ? "Starting…" : SIM_LABEL[target] || "Working…";
    return busy(() => window.cbsLoad.simAction(btn, label, { title: SIM_TITLE[target] || "Simming", retry: true }, () => sim(target)), { quiet: true });
  }
  $("#simbar").addEventListener("click", (e) => {
    const b = e.target.closest("[data-sim]");
    if (b && !b.disabled) runSim(b.dataset.sim, b);
    if (e.target.closest("[data-dyn-finish]")) document.dispatchEvent(new CustomEvent("cbs:dyn-finish"));
    if (e.target.closest("[data-dyn-back]")) document.dispatchEvent(new CustomEvent("cbs:dyn-back"));
    if (e.target.closest("[data-keys]")) keysOverlay(true);
  });
  $("#actions").addEventListener("click", (e) => {
    const qa = e.target.closest("[data-q-auto]");
    if (qa) busy(() => window.cbsLoad.act(qa, "Deciding…", async () => applyTurn(await gameCall("/decide", "POST", { kind: qa.dataset.qAuto, value: "auto" }))));
  });
  // ---- keyboard controls (desktop play): the sim targets, and "?" for the key list ----
  const KEYS = [["Space / N", "Next pitch", "pitch"], ["A", "At-bat", "pa"], ["H", "Half inning", "half"], ["I", "Inning", "inning"], ["3", "Three innings", "three_innings"], ["E", "End of game", "game"], ["?", "This key list", null], ["Esc", "Close a page or this list", null]];
  const KEY_OF = { pitch: "Space / N", pa: "A", half: "H", inning: "I", three_innings: "3", game: "E" };
  function keysOverlay(show) {
    let el = $("#keys");
    if (!el) {
      el = document.createElement("div"); el.id = "keys"; el.className = "keys hidden";
      el.innerHTML = `<div class="panel"><div class="hdr">Keyboard <span class="sub">desktop play</span><button class="btn-ghost" data-keys-close="1">Close</button></div><div class="body"><table class="tbl keys-tbl">${KEYS.map(([k, l]) => `<tr><td class="mono key">${k}</td><td>${l}</td></tr>`).join("")}</table><div class="muted">Keys work on the manager screen while no input has focus.</div></div></div>`;
      document.body.appendChild(el);
      el.addEventListener("click", (e) => { if (e.target === el || e.target.closest("[data-keys-close]")) el.classList.add("hidden"); });
    }
    el.classList.toggle("hidden", show === false ? true : show === true ? false : !el.classList.contains("hidden"));
  }
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;
    if (e.key === "?") { e.preventDefault(); keysOverlay(); return; }
    if (e.key === "Escape") { keysOverlay(false); return; }
    if (!S.game || S.screen !== "game" || e.ctrlKey || e.metaKey || e.altKey) return;
    const map = { " ": "pitch", n: "pitch", N: "pitch", a: "pa", A: "pa", h: "half", H: "half", i: "inning", I: "inning", "3": "three_innings", e: "game", E: "game" };
    if (map[e.key]) { e.preventDefault(); runSim(map[e.key]); }
  });

  // ---- the one top bar: school and conference/tier, the program tabs, date and phase, Advance ----
  const BUILT_TABS = ["hub", "roster", "schedule", "draft"];
  function setTopbar(o) {
    $("#tb-school").textContent = o.school; $("#tb-sub").textContent = o.sub || "";
    $$("#tb-tabs button").forEach((b) => { b.disabled = !o.dynasty || !BUILT_TABS.includes(b.dataset.tab); b.classList.toggle("on", !!o.dynasty && b.dataset.tab === o.active); });
    $("#tb-date").classList.toggle("hidden", !o.date); $("#tb-date-text").textContent = o.date || ""; $("#tb-phase").textContent = o.phase || "";
    $("#tb-advance").classList.toggle("hidden", !o.advance);
  }
  function refreshTopbar(name) {
    const inDynasty = name === "dyn" || (name === "game" && S.game && S.game.dynasty);
    if (inDynasty && window.dyn && window.dyn.hub()) window.dyn.topbar(name);
    else setTopbar({ school: "College Baseball Sim", sub: name === "game" ? "exhibition · prototype" : name === "picker" ? "new dynasty · prototype" : "prototype", dynasty: false });
  }
  $$("#tb-tabs button").forEach((b) => b.addEventListener("click", () => { if (window.dyn) window.dyn.goto(b.dataset.tab); }));
  $("#tb-advance").addEventListener("click", () => { if (window.dyn) window.dyn.advance(); });

  // ---- screens: main, picker (new dynasty), lobby (quick game), game, dyn (the dynasty hub) ----
  function show(name) {
    if (name === true) name = "game"; if (name === false) name = "main";
    ["main", "picker", "lobby", "game", "dyn"].forEach((n) => $(`#${n}`).classList.toggle("hidden", n !== name));
    $("#phone-tabs").classList.toggle("hidden", name !== "game");
    $("#simbar").classList.toggle("hidden", name !== "game");
    $("#nav-save").classList.toggle("hidden", name !== "game");
    $("#nav-new").classList.toggle("hidden", name !== "game" || !!(S.game && S.game.dynasty));
    S.screen = name;
    refreshTopbar(name);
    window.scrollTo(0, 0);
    document.dispatchEvent(new CustomEvent("cbs:screen", { detail: name }));
  }
  function fillTeams(sel, filter) {
    const f = (filter || "").toLowerCase(), keep = sel.value;
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
  $("#home-search").addEventListener("input", (e) => fillTeams($("#home"), e.target.value));
  $("#away-search").addEventListener("input", (e) => fillTeams($("#away"), e.target.value));
  $("#random-matchup").addEventListener("click", () => {
    const n = S.league.teams.length;
    let h = Math.floor(Math.random() * n), a = Math.floor(Math.random() * n);
    if (a === h) a = (a + 1) % n;
    $("#home-search").value = ""; $("#away-search").value = ""; fillTeams($("#home")); fillTeams($("#away"));
    $("#home").value = h; $("#away").value = a;
  });
  $("#start").addEventListener("click", () => busy(async () => {
    const home = +$("#home").value, away = +$("#away").value;
    if (!$("#home").value || !$("#away").value) return toast("Pick both teams.");
    if (home === away) return toast("Pick two different teams.");
    const side = $('input[name="side"]:checked').value;
    const seed = $("#seed").value ? +$("#seed").value : null;
    let t = await raw("/api/games", "POST", { home, away, user_side: side, seed });
    S.game = { id: t.game_id, turn: t, meta: t.meta, save: null, dynasty: null };
    applyTurn(t, true);
    t = await applyAskDefaults();
    S.pregame = null; lineupTab = "mine";
    show("game"); render(t);
    if (t.phase === "pregame") { await preparePregame(); render(t); }
  }));
  async function applyAskDefaults() {
    // settings (main screen): the decision kinds switched to "ask me" for every new game
    const ask = (window.cbsSettings && window.cbsSettings().askModes) || {};
    let t = S.game.turn;
    for (const k of Object.keys(ask)) if (ask[k]) { t = await gameCall("/modes", "POST", { kind: k, mode: "ask" }); applyTurn(t); }
    return t;
  }
  // a dynasty game: opened by dynasty.js with the turn of the pending game
  function openDynastyGame(t, did) {
    S.game = { id: t.game_id, turn: t, meta: t.meta, save: null, dynasty: did, venue: t.venue, stage: t.stage || (t.meta && t.meta.exhibition && t.meta.exhibition.stage) || null };
    applyTurn(t, true);
    S.pregame = null; lineupTab = "mine";
    show("game"); render(t);
    if (t.phase === "pregame") { preparePregame().then(() => render(S.game.turn)); }
  }
  $("#nav-new").addEventListener("click", () => { show("lobby"); renderSaves(); });
  $("#nav-home").addEventListener("click", () => show("main"));

  // ---- saves ----
  $("#nav-save").addEventListener("click", () => busy(async () => {
    const sv = await gameCall("/save");
    const saves = ls.get(LS_SAVES, []);
    const name = prompt("Name this save", gameTitle()) || gameTitle();
    saves.unshift({ name, time: Date.now(), save: sv.save, meta: sv.meta });
    ls.set(LS_SAVES, saves.slice(0, 20));
    toast("Saved in this browser.");
  }));
  async function loadSave(save) {
    const t = await raw("/api/games/load", "POST", { save });
    S.game = { id: t.game_id, turn: t, meta: t.meta, save, dynasty: null };
    applyTurn(t, true);
    S.pregame = null; lineupTab = "mine";
    show("game"); render(t);
    if (t.phase === "pregame") { await preparePregame(); render(t); }
  }
  function renderSaves() {
    const latest = ls.get(LS_LATEST, null), saves = ls.get(LS_SAVES, []);
    const rows = [];
    if (latest) rows.push(`<div class="save"><span>Latest: ${esc(latest.title || "game")} <span class="muted">${new Date(latest.time).toLocaleString()}</span></span><span><button class="btn-ghost" data-load="latest">Resume</button></span></div>`);
    saves.forEach((s, i) => rows.push(`<div class="save"><span>${esc(s.name)} <span class="muted">${new Date(s.time).toLocaleString()}</span></span><span><button class="btn-ghost" data-load="${i}">Load</button> <button class="btn-ghost" data-del="${i}">Delete</button></span></div>`));
    $("#saves").innerHTML = rows.join("") || "<div class='muted'>No saved games in this browser yet.</div>";
    $$("#saves [data-load]").forEach((b) => b.addEventListener("click", () => busy(async () => loadSave(b.dataset.load === "latest" ? latest.save : saves[+b.dataset.load].save))));
    $$("#saves [data-del]").forEach((b) => b.addEventListener("click", () => { saves.splice(+b.dataset.del, 1); ls.set(LS_SAVES, saves); renderSaves(); }));
  }
  $("#load-file").addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader(); rd.onload = () => busy(async () => loadSave(String(rd.result).trim())); rd.readAsText(f);
  });

  // ---- boot ----
  async function boot() {
    try { [S.league, S.decisions] = await Promise.all([raw("/api/league"), raw("/api/decisions")]); S.identity = (await raw("/api/identity")).schools; }
    catch (e) { toast("The server is waking up; retrying in a few seconds."); return setTimeout(boot, 4000); }
    fillTeams($("#home")); fillTeams($("#away"));
    renderSaves();
    show("main");
    document.dispatchEvent(new Event("cbs:ready"));
  }
  window.v2 = { render, callout, calloutFor, raw, toast, esc, mark, chip, colorsOf, venueOf, venueLine, setMine, badge, band, ls, show, busy, runSim, openDynastyGame, S, ORD, RATING, renderSaves, loadSave, gameCall, applyTurn, setTopbar, refreshTopbar };
  boot();
})();
