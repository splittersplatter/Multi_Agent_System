"use strict";
// /setup: build a scenario by clicking, with exact people, beliefs and seed; import/export TOML or JSON.

const $ = id => document.getElementById(id);
const MIN_PEOPLE = 100;
const DRAFT_KEY = "eclipse-setup-draft";
const VOTING = ["sincere", "sensed_plurality", "local_plurality", "signal_confident", "memory_pivotal", "pivotal", "expected_utility",
  "top_k", "max_m", "tie_u", "tie_h", "tie_r", "poisson", "local_dominance", "maximin", "sight_plurality", "overheard_plurality",
  "coalition_fusion", "epistemic_dere", "epistemic_dominant", "epistemic_pessimistic"];
const CAP_GROUPS = [
  ["Sees", ["observe_public_neighbors", "observe_private_channels", "observe_electorate", "observe_public_signal", "observe_target_preferences"]],
  ["Senses", ["sense_public_ballots", "sense_private_ballots", "intercept_private_reports"]],
  ["Talks", ["send_public_reports", "send_private_reports", "receive_public_reports", "receive_private_reports"]],
  ["Acts", ["move", "modify_persistent_edges", "modify_private_channels"]],
];
const GROUP_TINTS = ["#20232c", "#6b7385", "#2a9d8f", "#c47f00", "#8a4fe6", "#d1495b", "#3d6fb6", "#7a5c3e"];

let cfg = null, last = "", undoStack = [], redoStack = [], fmt = "toml", colorBy = "fav", showLinks = true, version = 0;
const view = {
  state: { hover: -1, sel: new Set(), twoHop: false, changes: false }, layers: { prox: true, follow: true, campaign: true }, movable: true,
  nodes() {
    if (!cfg) return [];
    const pc = partyColors(cfg.parties), shapes = groupShapes(Object.keys(cfg.groups)), order = Object.keys(cfg.groups);
    return cfg.people.map(p => ({
      x: p.position?.[0] ?? .5, y: p.position?.[1] ?? .5, shape: shapes[p.group] || "circle", big: isCampaigner(p.group),
      fill: colorBy === "fav" ? (pc[p.preference[0]] || "#c9cfdb") : GROUP_TINTS[order.indexOf(p.group) % GROUP_TINTS.length],
    }));
  },
  radius(i) { return radiusOf(cfg.people[i]); },
  edges() { return startEdges(); },
  prevEdges() { return null; },
  onMove(ids, dx, dy) {
    for (const i of ids) { const p = cfg.people[i], [x, y] = p.position || [.5, .5]; p.position = [round4(clamp(x + dx, 0, 1)), round4(clamp(y + dy, 0, 1))]; }
    version++; save(); renderLight();
  },
  onChange() { renderPeoplePanel(); },
};
const round4 = v => Math.round(v * 10000) / 10000;
const isCampaigner = g => { const d = cfg.groups[g]; return !!d && ((d.graph || "none") !== "none" || String(d.movement || "").startsWith("python:")); };
function radiusOf(p) {
  const o = p.overrides?.proximity_radius;
  return o ?? cfg.groups[p.group]?.proximity_radius ?? cfg.network?.radius ?? null;
}
// Round-0 links, as the engine will compute them: receiver's range decides who reaches them.
let edgeCache = { v: -1, e: null };
function startEdges() {
  if (!cfg) return { prox: [], follow: [], campaign: [] };
  if (edgeCache.v === version) return edgeCache.e;
  const idx = new Map(cfg.people.map((p, i) => [p.id, i])), prox = [];
  if (showLinks) {
    const xy = cfg.people.map(p => p.position || [.5, .5]), rad = cfg.people.map(radiusOf);
    for (let r = 0; r < xy.length; r++) {
      const R = rad[r]; if (R == null) continue;
      for (let s = 0; s < xy.length; s++) if (s !== r && Math.hypot(xy[s][0] - xy[r][0], xy[s][1] - xy[r][1]) <= R) prox.push([s, r]);
    }
  }
  const pairs = list => (list || []).filter(([a, b]) => idx.has(a) && idx.has(b)).map(([a, b]) => [idx.get(a), idx.get(b)]);
  edgeCache = { v: version, e: { prox, follow: pairs(cfg.network?.persistent_edges), campaign: pairs(cfg.network?.campaign_edges) } };
  return edgeCache.e;
}
const town = makeTown($("town"), view);

// ---------- history ----------
function save() {
  const now = JSON.stringify(cfg);
  if (now === last) return;
  if (last) { undoStack.push(last); if (undoStack.length > 200) undoStack.shift(); }
  last = now; redoStack = []; version++;
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ at: Date.now(), cfg })); } catch { /* storage blocked: drafts just aren't kept */ }
  scheduleExport();
  $("undo").disabled = !undoStack.length; $("redo").disabled = !redoStack.length;
}
function setConfig(next, { record = true } = {}) {
  cfg = normalize(next); view.state.sel.clear(); view.state.hover = -1;
  if (record) save(); else { last = JSON.stringify(cfg); version++; scheduleExport(); }
  renderAll();
}
function undo() { if (!undoStack.length) return; redoStack.push(last); last = undoStack.pop(); cfg = JSON.parse(last); version++; view.state.sel.clear(); renderAll(); scheduleExport(); }
function redo() { if (!redoStack.length) return; undoStack.push(last); last = redoStack.pop(); cfg = JSON.parse(last); version++; view.state.sel.clear(); renderAll(); scheduleExport(); }
$("undo").onclick = undo; $("redo").onclick = redo;
window.addEventListener("keydown", e => {
  if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "z" || e.target.closest("input,textarea,select")) return;
  e.preventDefault(); e.shiftKey ? redo() : undo();
});
// Fill the fields the page edits so the rest of the code can assume they exist.
function normalize(c) {
  c = JSON.parse(JSON.stringify(c));
  c.parties = c.parties || ["A", "B", "C"]; c.k = c.k || 1; c.seed = c.seed ?? 0; c.rounds = c.rounds ?? 40;
  c.groups = c.groups || {}; c.people = c.people || []; c.network = c.network || {};
  for (const p of c.people) { p.position = p.position || [.5, .5]; p.overrides = p.overrides || {}; }
  return c;
}

// ---------- generators (seeded, so the same seed draws the same town) ----------
function uniqueIds(prefix, n) {
  const taken = new Set(cfg.people.map(p => p.id)), out = []; let k = 0;
  const width = Math.max(2, String(cfg.people.length + n).length);
  while (out.length < n) { const id = prefix + String(k++).padStart(width, "0"); if (!taken.has(id)) { out.push(id); taken.add(id); } }
  return out;
}
function ranking(fav, rest, r) {
  const others = cfg.parties.filter(p => p !== fav);
  for (let i = others.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [others[i], others[j]] = [others[j], others[i]]; }
  if (rest === "near") { const i = cfg.parties.indexOf(fav); others.sort((a, b) => Math.abs(cfg.parties.indexOf(a) - i) - Math.abs(cfg.parties.indexOf(b) - i)); }  // stable: ties stay shuffled
  return [fav, ...others];
}
function drawPeople({ group, n, mix, rest, place, x, y, spread, prefix }) {
  const r = rng(cfg.seed * 7919 + cfg.people.length * 31 + n), total = mix.reduce((a, b) => a + b, 0) || 1;
  const favs = [];                                   // exact counts per party, largest remainder
  const quotas = mix.map(w => (w / total) * n), floors = quotas.map(Math.floor);
  let left = n - floors.reduce((a, b) => a + b, 0);
  quotas.map((q, i) => [q - floors[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (left > 0) { floors[i]++; left--; } });
  floors.forEach((c, i) => { for (let k = 0; k < c; k++) favs.push(cfg.parties[i]); });
  for (let i = favs.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [favs[i], favs[j]] = [favs[j], favs[i]]; }
  return uniqueIds(prefix, n).map((id, i) => ({
    id, group, preference: ranking(favs[i], rest, r),
    position: place === "spot" ? [round4(clamp(x + r.normal() * spread, 0, 1)), round4(clamp(y + r.normal() * spread, 0, 1))] : [round4(r()), round4(r())],
    overrides: {},
  }));
}
function freshTown(seed) {
  cfg = normalize({ parties: ["A", "B", "C"], k: 1, seed, rounds: 40, network: {}, people: [], groups: {
    copycats: { voting: "sensed_plurality", movement: "random_walk", max_step: 0.02, proximity_radius: 0.12, communication: "truthful", capabilities: { sense_public_ballots: true } },
    committed: { voting: "sincere", movement: "random_walk", max_step: 0.02, proximity_radius: 0.12, communication: "truthful" },
  } });
  cfg.people.push(...drawPeople({ group: "copycats", n: 60, mix: [1, 1, 1], rest: "random", place: "any", prefix: "c" }));
  cfg.people.push(...drawPeople({ group: "committed", n: 40, mix: [1, 1, 1], rest: "random", place: "any", prefix: "k" }));
  return cfg;
}

// ---------- section 1: ballot ----------
function renderBallot() {
  const pc = partyColors(cfg.parties);
  $("parties").innerHTML = cfg.parties.map((p, i) => `<span class="party"><span class="dot" style="background:${pc[p]}"></span><input type="text" value="${esc(p)}" data-party="${i}" aria-label="Party ${i + 1} name"><button type="button" data-drop="${i}" aria-label="Remove ${esc(p)}" ${cfg.parties.length <= 2 ? "disabled" : ""}>×</button></span>`).join("") +
    `<button class="btn" id="add-party" type="button">+ Party</button>`;
  $("parties").querySelectorAll("[data-party]").forEach(inp => inp.onchange = () => renameParty(+inp.dataset.party, inp.value.trim()));
  $("parties").querySelectorAll("[data-drop]").forEach(b => b.onclick = () => dropParty(+b.dataset.drop));
  $("add-party").onclick = addParty;
  $("k").innerHTML = cfg.parties.map((_, i) => `<button type="button" aria-pressed="${cfg.k === i + 1}" data-k="${i + 1}">${i + 1}</button>`).join("");
  $("k").querySelectorAll("[data-k]").forEach(b => b.onclick = () => { cfg.k = +b.dataset.k; save(); renderBallot(); });
  $("k-hint").textContent = cfg.k === 1 ? "Each voter names one party." : `Each voter names their top ${cfg.k} parties (approval-style).`;
  $("rounds").value = cfg.rounds; $("rounds-r").value = Math.min(200, cfg.rounds); $("seed").value = cfg.seed;
}
function replaceParty(old, name) {
  const swap = v => v === old ? name : v;
  cfg.parties = cfg.parties.map(swap);
  for (const p of cfg.people) p.preference = p.preference.map(swap);
  for (const key of ["campaign_controller", "signal_controller", "detector"]) if (cfg[key]?.target === old) cfg[key].target = name;
  for (const c of cfg.coalitions || []) if (c.target === old) c.target = name;
}
function renameParty(i, name) {
  const old = cfg.parties[i];
  if (!name || name === old) return renderBallot();
  if (!/^[A-Za-z0-9_\-]+$/.test(name) || cfg.parties.includes(name)) { toast("Party names must be unique letters, digits, - or _.", "bad"); return renderBallot(); }
  replaceParty(old, name); save(); renderAll();
}
function addParty() {
  let n = cfg.parties.length, name; do name = String.fromCharCode(65 + (n % 26)) + (n >= 26 ? Math.floor(n / 26) : ""); while (cfg.parties.includes(name) && ++n);
  cfg.parties.push(name); for (const p of cfg.people) p.preference.push(name);
  save(); renderAll(); toast(`Added ${name}. Everyone ranks it last until you change their beliefs.`);
}
function dropParty(i) {
  const name = cfg.parties[i];
  cfg.parties.splice(i, 1); for (const p of cfg.people) p.preference = p.preference.filter(x => x !== name);
  cfg.k = Math.min(cfg.k, cfg.parties.length);
  const dropped = [];
  for (const key of ["campaign_controller", "signal_controller", "detector"]) if (cfg[key]?.target === name) { delete cfg[key]; dropped.push(key.replace("_", " ")); }
  save(); renderAll(); toast(`Removed ${name}` + (dropped.length ? ` and its ${dropped.join(", ")}.` : "."));
}
$("rounds-r").oninput = e => { cfg.rounds = +e.target.value; $("rounds").value = cfg.rounds; scheduleExport(); };
$("rounds-r").onchange = () => save();
$("rounds").onchange = e => { cfg.rounds = Math.max(0, Math.round(+e.target.value || 0)); $("rounds-r").value = Math.min(200, cfg.rounds); save(); };
$("seed").onchange = e => { cfg.seed = Math.max(0, Math.round(+e.target.value || 0)); save(); renderMeta(); };
$("reseed").onclick = () => { cfg.seed = Math.floor(Math.random() * 1e6); $("seed").value = cfg.seed; save(); renderMeta(); toast(`Seed is now ${cfg.seed}.`); };

// ---------- section 2: groups ----------
const counts = () => { const c = {}; for (const p of cfg.people) c[p.group] = (c[p.group] || 0) + 1; return c; };
function movementKind(d) { const m = d.movement || "stationary"; return m === "stationary" || m === "random_walk" || m === "external" ? m : "custom"; }
function renderGroups() {
  const n = counts(), shapes = groupShapes(Object.keys(cfg.groups)), names = Object.keys(cfg.groups);
  $("groups").innerHTML = names.map((g, gi) => {
    const d = cfg.groups[g], mk = movementKind(d), caps = d.capabilities || {}, rule = d.voting;
    const opts = (VOTING.includes(rule) ? VOTING : [rule, ...VOTING]).map(v => `<option value="${esc(v)}" ${v === rule ? "selected" : ""}>${esc(v.replace(/_/g, " "))}</option>`).join("");
    const uniform = d.parameters?.movement?.distribution === "uniform";
    const comm = d.communication || "none";
    return `<article class="gcard" data-g="${esc(g)}">
      <header>${glyph(shapes[g], GROUP_TINTS[gi % GROUP_TINTS.length]).replace('class="glyph"', 'class="glyph" style="width:28px;height:28px"')}
        <input type="text" value="${esc(g)}" data-f="name" aria-label="Group name"><span class="spacer"></span><span class="count">${n[g] || 0} people</span></header>
      <label class="field">How they vote <select data-f="voting">${opts}</select><small>They ${esc(ruleText(rule))}.</small></label>
      <div class="field"><span>How they move</span><div class="seg" role="group">${[["stationary", "Stay put"], ["random_walk", "Wander"], ["external", "Learner"], ["custom", "Plugin"]].map(([v, l]) => `<button type="button" data-move="${v}" aria-pressed="${mk === v}">${l}</button>`).join("")}</div>
        ${mk === "custom" ? `<input type="text" data-f="movement" value="${esc(d.movement)}" aria-label="Movement plugin">` : ""}</div>
      ${mk !== "stationary" ? `<label class="field">Longest step per round<div class="slider"><input type="range" min="0" max="0.15" step="0.002" value="${d.max_step || 0}" data-f="max_step" data-live><input type="number" min="0" max="1" step="0.001" value="${d.max_step || 0}" data-f="max_step"></div></label>` : ""}
      ${mk === "random_walk" ? `<div class="field"><span>Step lengths</span><div class="seg" role="group"><button type="button" data-steps="normal" aria-pressed="${!uniform}">Mostly small (normal)</button><button type="button" data-steps="uniform" aria-pressed="${uniform}">Any length (uniform)</button></div></div>` : ""}
      <div class="field"><span>How far they hear</span>
        <div class="row"><div class="seg" role="group"><button type="button" data-rad="own" aria-pressed="${d.proximity_radius != null}">Own range</button><button type="button" data-rad="town" aria-pressed="${d.proximity_radius == null}">Town default</button></div></div>
        ${d.proximity_radius != null ? `<div class="slider"><input type="range" min="0" max="0.6" step="0.01" value="${d.proximity_radius}" data-f="proximity_radius" data-live><input type="number" min="0" max="1.4142" step="0.01" value="${d.proximity_radius}" data-f="proximity_radius"></div>` : `<small class="hint">${cfg.network.radius != null ? `Uses the town default (${cfg.network.radius}).` : "No town default set: they only hear people linked to them."}</small>`}</div>
      <label class="field">What they say <select data-f="communication">${["none", "truthful", "target_report"].concat(comm.startsWith("python:") ? [comm] : []).map(v => `<option ${v === comm ? "selected" : ""}>${esc(v)}</option>`).join("")}</select></label>
      ${(d.graph || "none") !== "none" ? `<label class="field">Makes links with <input type="text" data-f="graph" value="${esc(d.graph)}"><small>Set to "none" to stop.</small></label>` : ""}
      <details class="field"><summary style="cursor:pointer;font-weight:700">Powers <span class="small mute">· ${esc(notablePowers(caps).join(", ") || "everyday only")}</span></summary><div style="display:grid;gap:6px;margin-top:8px">${CAP_GROUPS.map(([label, keys]) => `<div class="powers"><span class="small mute" style="min-width:56px;align-self:center">${label}</span>${keys.map(k => {
        const on = caps[k] ?? POWERS[k][1]; return `<button type="button" class="pill" data-cap="${k}" aria-pressed="${on}">${esc(POWERS[k][0])}</button>`; }).join("")}</div>`).join("")}</div></details>
      <details><summary class="small mute" style="cursor:pointer">Advanced: parameters (JSON)</summary><textarea rows="4" data-f="parameters" style="margin-top:8px">${esc(JSON.stringify(d.parameters || {}, null, 1))}</textarea></details>
      <div class="row"><button class="btn" type="button" data-act="add">+ People</button><button class="btn" type="button" data-act="pick">Pick them</button><button class="btn ghost" type="button" data-act="dup">Duplicate</button><span class="spacer"></span><button class="btn danger" type="button" data-act="del" ${names.length <= 1 ? "disabled" : ""}>Delete</button></div>
    </article>`;
  }).join("") + `<button class="new-group" id="new-group" type="button">+ New group</button>`;
  $("new-group").onclick = () => {
    const g = uniqueGroup("group");
    cfg.groups[g] = { voting: "sincere", movement: "random_walk", max_step: 0.02, proximity_radius: 0.12, communication: "truthful", capabilities: {} };
    save(); renderAll(); toast(`Made ${g}. Add people to it, or pick people on the map and move them in.`);
  };
  $("groups").querySelectorAll(".gcard").forEach(card => wireGroup(card, card.dataset.g));
}
function uniqueGroup(base) { let g = base, i = 2; while (cfg.groups[g]) g = `${base}_${i++}`; return g; }
function wireGroup(card, g) {
  const d = cfg.groups[g];
  card.querySelectorAll("[data-f]").forEach(el => {
    const f = el.dataset.f;
    const apply = live => {
      if (f === "name") return renameGroup(g, el.value.trim());
      if (f === "parameters") { try { d.parameters = JSON.parse(el.value || "{}"); } catch { toast("Parameters must be valid JSON.", "bad"); return; } }
      else if (f === "max_step" || f === "proximity_radius") {
        d[f] = Math.max(0, +el.value || 0);
        card.querySelectorAll(`[data-f="${f}"]`).forEach(o => { if (o !== el) o.value = d[f]; });
        if (live) { version++; town.redraw(); return; }
      } else d[f] = el.value;
      save(); if (f === "voting" || f === "graph" || f === "movement") renderGroups(); renderLight();
    };
    if (el.dataset.live !== undefined) { el.oninput = () => apply(true); el.onchange = () => apply(false); }
    else el.onchange = () => apply(false);
  });
  card.querySelectorAll("[data-move]").forEach(b => b.onclick = () => {
    const v = b.dataset.move;
    d.movement = v === "custom" ? (movementKind(d) === "custom" ? d.movement : "python:module:function") : v;
    if (v === "random_walk" && !d.max_step) d.max_step = 0.02;
    if (v !== "random_walk" && d.parameters?.movement) { delete d.parameters.movement; }
    save(); renderGroups();
  });
  card.querySelectorAll("[data-steps]").forEach(b => b.onclick = () => {
    d.parameters = d.parameters || {};
    if (b.dataset.steps === "uniform") d.parameters.movement = { distribution: "uniform" }; else delete d.parameters.movement;
    save(); renderGroups();
  });
  card.querySelectorAll("[data-rad]").forEach(b => b.onclick = () => {
    if (b.dataset.rad === "town") delete d.proximity_radius; else d.proximity_radius = cfg.network.radius ?? 0.12;
    save(); renderGroups(); renderLight();
  });
  card.querySelectorAll("[data-cap]").forEach(b => b.onclick = () => {
    const k = b.dataset.cap; d.capabilities = d.capabilities || {};
    const on = !(d.capabilities[k] ?? POWERS[k][1]);
    if (on === POWERS[k][1] && Object.keys(d.capabilities).length < 15) delete d.capabilities[k]; else d.capabilities[k] = on;
    b.setAttribute("aria-pressed", on); save();
    card.querySelector("details.field summary span").textContent = "· " + (notablePowers(d.capabilities).join(", ") || "everyday only");
  });
  card.querySelector('[data-act="add"]').onclick = () => openAdd(g);
  card.querySelector('[data-act="pick"]').onclick = () => {
    view.state.sel.clear(); cfg.people.forEach((p, i) => { if (p.group === g) view.state.sel.add(i); });
    renderLight(); $("town").scrollIntoView({ behavior: "smooth", block: "center" });
  };
  card.querySelector('[data-act="dup"]').onclick = () => { const n = uniqueGroup(g + "_copy"); cfg.groups[n] = JSON.parse(JSON.stringify(d)); save(); renderAll(); };
  card.querySelector('[data-act="del"]').onclick = () => {
    const members = cfg.people.filter(p => p.group === g).length, other = Object.keys(cfg.groups).find(x => x !== g);
    delete cfg.groups[g];
    for (const p of cfg.people) if (p.group === g) p.group = other;
    save(); renderAll(); toast(members ? `Deleted ${g}; its ${members} people moved to ${other}.` : `Deleted ${g}.`);
  };
}
function renameGroup(old, name) {
  if (!name || name === old) return;
  if (!/^[A-Za-z0-9_\-]+$/.test(name) || cfg.groups[name]) { toast("Group names must be unique letters, digits, - or _.", "bad"); renderGroups(); return; }
  cfg.groups = Object.fromEntries(Object.entries(cfg.groups).map(([k, v]) => [k === old ? name : k, v]));
  for (const p of cfg.people) if (p.group === old) p.group = name;
  save(); renderAll();
}

// ---------- section 3: people ----------
$("town").addEventListener("pointerup", () => setTimeout(renderPeoplePanel, 0));
document.querySelectorAll("[data-color]").forEach(b => b.onclick = () => {
  colorBy = b.dataset.color; document.querySelectorAll("[data-color]").forEach(x => x.setAttribute("aria-pressed", x === b)); town.redraw();
});
$("show-links").onclick = () => { showLinks = !showLinks; $("show-links").setAttribute("aria-pressed", showLinks); version++; town.redraw(); };
$("clear").onclick = () => { view.state.sel.clear(); renderLight(); };
$("remove").onclick = () => {
  const gone = new Set([...view.state.sel].map(i => cfg.people[i].id));
  cfg.people = cfg.people.filter(p => !gone.has(p.id));
  const keep = e => !gone.has(e[0]) && !gone.has(e[1]);
  for (const key of ["persistent_edges", "campaign_edges"]) if (cfg.network[key]) cfg.network[key] = cfg.network[key].filter(keep);
  view.state.sel.clear(); save(); renderAll(); toast(`Removed ${gone.size} ${gone.size === 1 ? "person" : "people"}.`);
};
function renderPop() {
  const n = cfg.people.length, ok = n >= MIN_PEOPLE, pc = partyColors(cfg.parties), favs = {};
  for (const p of cfg.people) favs[p.preference[0]] = (favs[p.preference[0]] || 0) + 1;
  $("pop").innerHTML = `<p class="say"><b>${n}</b> people in <b>${Object.keys(cfg.groups).length}</b> groups. ${ok ? "✓ Big enough to run." : `<span style="color:var(--bad)">Needs at least ${MIN_PEOPLE}: add ${MIN_PEOPLE - n} more.</span>`}</p>
    <p class="small mute" style="margin-top:10px">Favourite party</p>
    <div class="meter" style="height:16px;margin-top:4px">${cfg.parties.map(p => favs[p] ? `<span title="${esc(p)}: ${favs[p]}" style="flex:${favs[p]};background:${pc[p]}"></span>` : "").join("")}</div>
    <div class="legend">${cfg.parties.map(p => `<span><span class="dot" style="background:${pc[p]}"></span> ${esc(p)} ${favs[p] || 0}</span>`).join("")}</div>`;
}
function renderPeoplePanel() {
  const sel = [...view.state.sel], f = town.focus();
  $("picked").hidden = !sel.length; $("seln").textContent = sel.length;
  const i = f >= 0 && f < cfg.people.length ? f : -1;
  if (i < 0) {
    $("person-title").textContent = sel.length > 1 ? `${sel.length} people picked` : "Pick someone";
    $("person").innerHTML = sel.length > 1 ? `<p class="say">Use <b>Make them a group</b> to give them their own rules, or <b>Change them…</b> to set beliefs, spots and hearing range together.</p>`
      : `<p class="say mute">Point at a person to see who they'd hear at the start. Click one to edit their beliefs and spot.</p>`;
    return;
  }
  const p = cfg.people[i], pc = partyColors(cfg.parties), e = town.ego(i), heard = new Set([...e.inc.prox, ...e.inc.follow, ...e.inc.campaign]);
  $("person-title").textContent = p.id;
  const pinned = view.state.sel.size === 1 && view.state.sel.has(i);
  $("person").innerHTML = `<p class="say">In <b>${esc(p.group)}</b>; at the start they hear <b>${heard.size}</b> ${heard.size === 1 ? "person" : "people"} and <b>${new Set([...e.out.prox, ...e.out.follow, ...e.out.campaign]).size}</b> hear them.</p>` +
    (pinned ? `<div class="grid" style="display:grid;gap:14px;margin-top:14px">
      <label class="field">Group <select id="p-group">${Object.keys(cfg.groups).map(g => `<option ${g === p.group ? "selected" : ""}>${esc(g)}</option>`).join("")}</select></label>
      <div class="field"><span>Beliefs (favourite first): tap a party to move it up</span><div class="rank" id="p-rank">${p.preference.map((q, k) => `${k ? '<span class="sep">›</span>' : ""}<button type="button" data-up="${k}" style="background:${pc[q]}">${esc(q)}</button>`).join("")}</div></div>
      <div class="row"><label class="field" style="flex:1">x <input type="number" id="p-x" min="0" max="1" step="0.01" value="${p.position[0]}"></label><label class="field" style="flex:1">y <input type="number" id="p-y" min="0" max="1" step="0.01" value="${p.position[1]}"></label>
        <label class="field" style="flex:1">hearing <input type="number" id="p-r" min="0" max="1.4142" step="0.01" value="${p.overrides.proximity_radius ?? ""}" placeholder="group's"></label></div></div>` : `<p class="hint" style="margin-top:8px">Click to pin and edit.</p>`);
  if (!pinned) return;
  $("p-group").onchange = e => { p.group = e.target.value; save(); renderAll(); view.state.sel.add(i); renderPeoplePanel(); };
  $("p-rank").querySelectorAll("[data-up]").forEach(b => b.onclick = () => {
    const k = +b.dataset.up; if (!k) return;
    [p.preference[k - 1], p.preference[k]] = [p.preference[k], p.preference[k - 1]]; save(); renderLight();
  });
  const pos = () => { p.position = [round4(clamp(+$("p-x").value || 0, 0, 1)), round4(clamp(+$("p-y").value || 0, 0, 1))]; save(); renderLight(); };
  $("p-x").onchange = pos; $("p-y").onchange = pos;
  $("p-r").onchange = e => { if (e.target.value === "") delete p.overrides.proximity_radius; else p.overrides.proximity_radius = Math.max(0, +e.target.value); save(); renderLight(); };
}

// add people
const A = { rest: "random", place: "any" };
function segGroup(attr, obj, key, after) {
  document.querySelectorAll(`[data-${attr}]`).forEach(b => b.onclick = () => {
    obj[key] = b.dataset[attr]; document.querySelectorAll(`[data-${attr}]`).forEach(x => x.setAttribute("aria-pressed", x === b)); after && after();
  });
}
segGroup("rest", A, "rest"); segGroup("place", A, "place", () => { $("a-spot").hidden = A.place !== "spot"; });
function openAdd(group) {
  const names = Object.keys(cfg.groups);
  $("a-group").innerHTML = names.map(g => `<option ${g === group ? "selected" : ""}>${esc(g)}</option>`).join("");
  $("a-prefix").value = (group || names[0]).replace(/[^A-Za-z0-9]/g, "").slice(0, 4).toLowerCase() || "p";
  const need = Math.max(1, MIN_PEOPLE - cfg.people.length); $("a-n").value = $("a-n-r").value = Math.min(200, need > 1 ? need : 20);
  const pc = partyColors(cfg.parties);
  $("a-mix").innerHTML = cfg.parties.map((p, i) => `<span class="tag" style="background:${pc[p]}">${esc(p)}</span><input type="range" min="0" max="10" value="5" data-mix="${i}" aria-label="${esc(p)} weight"><span class="mono" id="mixv-${i}"></span>`).join("");
  const mixText = () => { const w = [...document.querySelectorAll("[data-mix]")].map(x => +x.value), t = w.reduce((a, b) => a + b, 0) || 1; w.forEach((v, i) => $(`mixv-${i}`).textContent = pct(v / t)); };
  document.querySelectorAll("[data-mix]").forEach(x => x.oninput = mixText); mixText();
  $("add-dialog").showModal();
}
$("add-people").onclick = () => openAdd(Object.keys(cfg.groups)[0]);
$("a-n-r").oninput = e => { $("a-n").value = e.target.value; };
$("a-n").oninput = e => { $("a-n-r").value = Math.min(200, +e.target.value || 1); };
$("add-form").addEventListener("submit", ev => {
  if (ev.submitter?.value !== "add") return;
  const n = clamp(Math.round(+$("a-n").value || 0), 1, 2000), mix = [...document.querySelectorAll("[data-mix]")].map(x => +x.value);
  if (!mix.some(Boolean)) { ev.preventDefault(); toast("Give at least one party some weight.", "bad"); return; }
  const prefix = ($("a-prefix").value.trim().replace(/[^A-Za-z0-9_\-]/g, "") || "p");
  const added = drawPeople({ group: $("a-group").value, n, mix, rest: A.rest, place: A.place, x: +$("a-x").value, y: +$("a-y").value, spread: +$("a-spread").value || 0, prefix });
  const start = cfg.people.length; cfg.people.push(...added);
  view.state.sel = new Set(added.map((_, k) => start + k)); save(); renderAll(); toast(`Added ${n} people to ${$("a-group").value}; they're picked on the map.`, "ok");
});

// make group
$("make-group").onclick = () => {
  const tally = {}; for (const i of view.state.sel) tally[cfg.people[i].group] = (tally[cfg.people[i].group] || 0) + 1;
  const common = Object.entries(tally).sort((a, b) => b[1] - a[1])[0][0];
  $("g-name").value = uniqueGroup("picked");
  $("g-from").innerHTML = Object.keys(cfg.groups).map(g => `<option ${g === common ? "selected" : ""}>${esc(g)}</option>`).join("");
  $("group-dialog").showModal();
};
$("group-form").addEventListener("submit", ev => {
  if (ev.submitter?.value !== "make") return;
  const name = $("g-name").value.trim();
  if (!/^[A-Za-z0-9_\-]+$/.test(name) || cfg.groups[name]) { ev.preventDefault(); toast("Pick a new name: letters, digits, - or _.", "bad"); return; }
  makeGroup(name, $("g-from").value, [...view.state.sel]);
  save(); renderAll(); toast(`Made ${name} with ${view.state.sel.size} people. Tune its settings in step 2.`, "ok");
});
function makeGroup(name, from, indices) {
  cfg.groups[name] = JSON.parse(JSON.stringify(cfg.groups[from]));
  for (const i of indices) cfg.people[i].group = name;
}

// bulk edit
const M = { pref: "keep", pos: "keep", rad: "keep", rank: [] };
segGroup("mpref", M, "pref", () => { $("m-rank").hidden = M.pref !== "set"; drawMRank(); });
segGroup("mpos", M, "pos", () => { $("m-spot").hidden = M.pos !== "spot"; });
segGroup("mrad", M, "rad", () => { $("m-rad-row").hidden = M.rad !== "set"; });
$("m-rad-r").oninput = e => { $("m-rad").value = e.target.value; };
$("m-rad").oninput = e => { $("m-rad-r").value = e.target.value; };
function drawMRank() {
  const pc = partyColors(cfg.parties), left = cfg.parties.filter(p => !M.rank.includes(p));
  $("m-rank").innerHTML = M.rank.map((p, i) => `${i ? '<span class="sep">›</span>' : ""}<button type="button" data-unrank="${i}" style="background:${pc[p]}">${esc(p)}</button>`).join("") +
    (left.length ? `<span class="sep">${M.rank.length ? "then" : "tap in order"}</span>` + left.map(p => `<button type="button" data-rank="${esc(p)}" style="background:${pc[p]};opacity:.55">${esc(p)}</button>`).join("") : "");
  $("m-rank").querySelectorAll("[data-rank]").forEach(b => b.onclick = () => { M.rank.push(b.dataset.rank); drawMRank(); });
  $("m-rank").querySelectorAll("[data-unrank]").forEach(b => b.onclick = () => { M.rank.splice(+b.dataset.unrank); drawMRank(); });
}
$("bulk").onclick = () => {
  const n = view.state.sel.size; $("bulk-title").textContent = `Change ${n} ${n === 1 ? "person" : "people"}`;
  $("m-group").innerHTML = `<option value="">Keep their groups</option>` + Object.keys(cfg.groups).map(g => `<option>${esc(g)}</option>`).join("");
  M.rank = []; drawMRank(); $("bulk-dialog").showModal();
};
$("bulk-form").addEventListener("submit", ev => {
  if (ev.submitter?.value !== "apply") return;
  const sel = [...view.state.sel], people = sel.map(i => cfg.people[i]);
  if (M.pref === "set" && M.rank.length !== cfg.parties.length) { ev.preventDefault(); toast("Tap every party to set a full ranking.", "bad"); return; }
  const r = rng(cfg.seed * 104729 + sel.reduce((a, b) => a + b, 0));
  if ($("m-group").value) for (const p of people) p.group = $("m-group").value;
  if (M.pref === "set") for (const p of people) p.preference = [...M.rank];
  if (M.pref === "shuffle") for (const p of people) p.preference = ranking(r.pick(cfg.parties), "random", r);
  if (M.pos !== "keep") {
    const cx = M.pos === "spot" ? clamp(+$("m-x").value, 0, 1) : people.reduce((s, p) => s + p.position[0], 0) / people.length;
    const cy = M.pos === "spot" ? clamp(+$("m-y").value, 0, 1) : people.reduce((s, p) => s + p.position[1], 0) / people.length;
    const spread = clamp(+$("m-spread").value || 0, 0, .5);
    for (const p of people) {
      const [x, y] = p.position;
      p.position = (M.pos === "gather" ? [cx + (x - cx) * .25, cy + (y - cy) * .25] : M.pos === "spot" ? [cx + r.normal() * spread, cy + r.normal() * spread] : [r(), r()]).map(v => round4(clamp(v, 0, 1)));
    }
  }
  if (M.rad === "set") for (const p of people) p.overrides.proximity_radius = Math.max(0, +$("m-rad").value || 0);
  if (M.rad === "clear") for (const p of people) delete p.overrides.proximity_radius;
  save(); renderAll(); sel.forEach(i => view.state.sel.add(i)); renderLight(); toast(`Changed ${sel.length} ${sel.length === 1 ? "person" : "people"}.`, "ok");
});

// ---------- section 4: extras ----------
const EXTRAS = {
  hearing: { title: "Town-wide hearing range", say: "A default range for groups without their own.", on: () => cfg.network.radius != null,
    enable: () => { cfg.network.radius = 0.12; }, disable: () => { delete cfg.network.radius; },
    body: () => `<label class="field">Range<div class="slider"><input type="range" min="0" max="0.6" step="0.01" value="${cfg.network.radius}" data-x="network.radius"><input type="number" min="0" max="1.4142" step="0.01" value="${cfg.network.radius}" data-x="network.radius"></div></label>
      <div class="field"><span>Who's nearby is…</span><div class="seg" role="group">${["dynamic", "frozen"].map(m => `<button type="button" data-mode="${m}" aria-pressed="${(cfg.network.proximity_mode || "dynamic") === m}">${m === "dynamic" ? "Recomputed each round" : "Fixed at the start"}</button>`).join("")}</div></div>` },
  campaign_controller: { title: "Paid campaign", say: "Buys links that carry voices toward voters, on a budget.", on: () => !!cfg.campaign_controller,
    enable: () => { cfg.campaign_controller = { target: cfg.parties[0], policy: "target_heuristic", lifetime_budget: 30, per_round_budget: 3 }; }, disable: () => { delete cfg.campaign_controller; },
    body: () => target("campaign_controller") + choice("campaign_controller", "policy", [["none", "Idle"], ["random", "Random links"], ["target_heuristic", "Smart targeting"]]) +
      num("campaign_controller", "per_round_budget", "Links per round") + num("campaign_controller", "lifetime_budget", "Links in total") },
  signal_controller: { title: "Rigged poll", say: "Publishes a poll that may lie about the target's support.", on: () => !!cfg.signal_controller,
    enable: () => { cfg.signal_controller = { target: cfg.parties[0], policy: "target_biased", schedule: "repeated", per_broadcast_budget: 3, lifetime_budget: 30 }; }, disable: () => { delete cfg.signal_controller; },
    body: () => target("signal_controller") + choice("signal_controller", "policy", [["truthful", "Honest"], ["bounded_random", "Noisy"], ["target_biased", "Biased to target"]]) +
      choice("signal_controller", "schedule", [["initial", "Once"], ["repeated", "Every round"]]) + num("signal_controller", "per_broadcast_budget", "Votes faked per poll") + num("signal_controller", "lifetime_budget", "Votes faked in total") },
  detector: { title: "Watchdog", say: "Raises an alarm when the target's share jumps too fast.", on: () => !!cfg.detector,
    enable: () => { cfg.detector = { target: cfg.parties[0], threshold: 0.05 }; }, disable: () => { delete cfg.detector; },
    body: () => target("detector") + `<label class="field">Alarm when one round's jump exceeds<div class="slider"><input type="range" min="0" max="0.3" step="0.005" value="${cfg.detector.threshold}" data-x="detector.threshold"><input type="number" min="0" max="1" step="0.005" value="${cfg.detector.threshold}" data-x="detector.threshold"></div></label>` },
};
const target = key => `<label class="field">Working for <select data-x="${key}.target">${cfg.parties.map(p => `<option ${cfg[key].target === p ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>`;
const choice = (key, f, opts) => `<div class="field"><span>${f === "policy" ? "Strategy" : "When"}</span><div class="seg" role="group">${opts.map(([v, l]) => `<button type="button" data-choice="${key}.${f}" data-v="${v}" aria-pressed="${cfg[key][f] === v}">${l}</button>`).join("")}</div></div>`;
const num = (key, f, label) => `<label class="field">${label}<input type="number" min="0" step="1" value="${cfg[key][f]}" data-x="${key}.${f}" data-int></label>`;
const KEPT = { coalitions: "coalitions", majority_estimation: "majority estimation", interventions: "scheduled interventions", convergence: "certified convergence", alignment: "alignment attack", leaders: "leaders", nomination: "nomination" };
function renderExtras() {
  $("extras").innerHTML = Object.entries(EXTRAS).map(([k, x]) => `<div class="extra" data-on="${x.on()}" data-extra="${k}">
      <label class="switch"><input type="checkbox" ${x.on() ? "checked" : ""}> ${x.title}</label><p class="mute small">${x.say}</p><div class="body" style="display:${x.on() ? "grid" : "none"};gap:12px">${x.on() ? x.body() : ""}</div></div>`).join("") + keptCard();
  $("extras").querySelectorAll("[data-extra]").forEach(card => {
    const x = EXTRAS[card.dataset.extra];
    card.querySelector(".switch input").onchange = e => { e.target.checked ? x.enable() : x.disable(); save(); renderExtras(); renderGroups(); renderLight(); };
  });
  $("extras").querySelectorAll("[data-x]").forEach(el => {
    const [key, f] = el.dataset.x.split("."), set = live => {
      const v = el.tagName === "SELECT" ? el.value : (el.dataset.int !== undefined ? Math.max(0, Math.round(+el.value || 0)) : Math.max(0, +el.value || 0));
      cfg[key][f] = v; $("extras").querySelectorAll(`[data-x="${el.dataset.x}"]`).forEach(o => { if (o !== el) o.value = v; });
      if (key === "network") { version++; town.redraw(); }
      if (!live) { save(); if (key === "network") renderGroups(); }
    };
    if (el.type === "range") { el.oninput = () => set(true); el.onchange = () => set(false); } else el.onchange = () => set(false);
  });
  $("extras").querySelectorAll("[data-choice]").forEach(b => b.onclick = () => { const [key, f] = b.dataset.choice.split("."); cfg[key][f] = b.dataset.v; save(); renderExtras(); });
  $("extras").querySelectorAll("[data-mode]").forEach(b => b.onclick = () => { if (b.dataset.mode === "dynamic") delete cfg.network.proximity_mode; else cfg.network.proximity_mode = b.dataset.mode; save(); renderExtras(); });
  $("extras").querySelectorAll("[data-forget]").forEach(b => b.onclick = () => {
    const [scope, key] = b.dataset.forget.split(".");
    if (scope === "net") delete cfg.network[key]; else delete cfg[key];
    save(); renderAll();
  });
}
function keptCard() {
  const items = Object.entries(KEPT).filter(([k]) => cfg[k] !== undefined && !(Array.isArray(cfg[k]) && !cfg[k].length)).map(([k, l]) => [`top.${k}`, l, Array.isArray(cfg[k]) ? cfg[k].length : null]);
  for (const [k, l] of [["persistent_edges", "follow links"], ["campaign_edges", "paid links"], ["private_channels", "private channels"], ["static_proximity_edges", "fixed nearby links"]]) {
    const v = cfg.network[k], n = Array.isArray(v) ? v.length : v ? Object.keys(v).length : 0;
    if (n) items.push([`net.${k}`, l, n]);
  }
  if (cfg.network.proximity_mode === "static") items.push(["net.proximity_mode", "static proximity", null]);
  if (!items.length) return "";
  return `<div class="extra"><h3>Kept from your file</h3><p class="mute small">The page doesn't edit these, but they stay in the scenario exactly as written.</p>
    <div style="display:grid;gap:8px">${items.map(([k, l, n]) => `<div class="row"><span class="chip">${esc(l)}${n != null ? ` · ${n}` : ""}</span><span class="spacer"></span><button class="btn ghost" type="button" data-forget="${k}">Remove</button></div>`).join("")}</div></div>`;
}

// ---------- section 5: export, check, run ----------
let exportTimer = null, checkTimer = null, tomlText = "", checkSeq = 0;
function scheduleExport() {
  clearTimeout(exportTimer); exportTimer = setTimeout(refreshExport, 250);
  clearTimeout(checkTimer); $("check").className = "status wait"; $("check").textContent = "Checking…"; checkTimer = setTimeout(check, 700);
}
async function refreshExport() {
  if (fmt === "json") { $("code").textContent = JSON.stringify(cfg, null, 2); return; }
  try { tomlText = (await api("/scenario/convert", { config: cfg })).toml; $("code").textContent = tomlText; }
  catch (err) { $("code").textContent = "# " + err.message + "\n" + JSON.stringify(cfg, null, 2); }
}
async function check() {
  const seq = ++checkSeq;
  try {
    const r = await api("/scenario/validate", { config: cfg });
    if (seq !== checkSeq) return;
    $("check").className = "status ok";
    $("check").textContent = `Ready: ${r.people} people in ${Object.keys(r.groups).length} groups, ${r.rounds} rounds, seed ${r.seed}.`;
    $("launch").disabled = false;
  } catch (err) {
    if (seq !== checkSeq) return;
    $("check").className = "status bad"; $("check").textContent = "Not yet: " + err.message; $("launch").disabled = true;
  }
}
document.querySelectorAll("[data-fmt]").forEach(b => b.onclick = () => { fmt = b.dataset.fmt; document.querySelectorAll("[data-fmt]").forEach(x => x.setAttribute("aria-pressed", x === b)); refreshExport(); });
const exportText = () => fmt === "json" ? JSON.stringify(cfg, null, 2) + "\n" : tomlText;
$("copy").onclick = async () => {
  try { await navigator.clipboard.writeText(exportText()); toast(`Copied the ${fmt.toUpperCase()} scenario.`, "ok"); }
  catch { const range = document.createRange(); range.selectNodeContents($("code")); getSelection().removeAllRanges(); getSelection().addRange(range); toast("Selected the text: press Ctrl+C to copy."); }
};
$("download").onclick = () => {
  const blob = new Blob([exportText()], { type: fmt === "json" ? "application/json" : "application/toml" }), url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = `eclipse-seed${cfg.seed}.${fmt}`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
};
$("paste").onclick = () => { $("paste-text").value = ""; $("paste-file").value = ""; $("paste-dialog").showModal(); };
$("paste-file").onchange = async e => { const f = e.target.files[0]; if (f) $("paste-text").value = await f.text(); };
$("paste-form").addEventListener("submit", async ev => {
  if (ev.submitter?.value !== "load") return;
  ev.preventDefault();
  try { const r = await api("/scenario/convert", { text: $("paste-text").value }); setConfig(r.config); $("paste-dialog").close(); toast(`Loaded ${cfg.people.length} people in ${Object.keys(cfg.groups).length} groups.`, "ok"); }
  catch (err) { toast(err.message, "bad"); }
});
// Paste anywhere on the page (outside a text field) imports too.
document.addEventListener("paste", async e => {
  if (e.target.closest("input,textarea")) return;
  const text = e.clipboardData?.getData("text"); if (!text || !text.trim()) return;
  try { const r = await api("/scenario/convert", { text }); setConfig(r.config); toast("Pasted scenario loaded (Ctrl+Z to undo).", "ok"); }
  catch (err) { toast("That paste isn't a scenario: " + err.message, "bad"); }
});
$("launch").onclick = async () => {
  $("launch").disabled = true;
  try { const r = await api("/scenario/launch", { config: cfg }); toast(`Running ${r.people} people…`, "ok"); location.href = "/sim"; }
  catch (err) { toast(err.message, "bad"); $("launch").disabled = false; }
};
$("from-running").onclick = async () => { try { setConfig((await api("/scenario")).config); toast("Loaded the running simulation's scenario."); } catch (err) { toast(err.message, "bad"); } };
$("from-fresh").onclick = () => { setConfig(freshTown(Math.floor(Math.random() * 1e6))); toast("A fresh town of 100. Ctrl+Z brings back what you had."); };

// ---------- render ----------
function renderMeta() { $("meta").innerHTML = `<b>${cfg.people.length}</b> people · seed <b>${cfg.seed}</b>`; }
function renderLight() { version++; town.redraw(); renderPop(); renderPeoplePanel(); renderMeta(); renderGroupCounts(); }
function renderGroupCounts() { const n = counts(); document.querySelectorAll(".gcard").forEach(c => { c.querySelector(".count").textContent = `${n[c.dataset.g] || 0} people`; }); }
function renderAll() { renderBallot(); renderGroups(); renderExtras(); renderLight(); $("undo").disabled = !undoStack.length; $("redo").disabled = !redoStack.length; }

// ---------- start: fork from /sim, else saved draft, else the running scenario ----------
async function start() {
  let fork = null;
  try { if (location.hash === "#fork") { fork = JSON.parse(sessionStorage.getItem("eclipse-fork") || "null"); sessionStorage.removeItem("eclipse-fork"); } } catch { fork = null; }
  if (fork) {
    const [scen, snap] = await Promise.all([api("/scenario"), api("/state")]);
    const c = scen.config, f = snap.frames[Math.min(fork.round, snap.frames.length - 1)];
    for (const p of c.people) { p.position = f.positions[p.id] || p.position; p.preference = f.preferences?.[p.id] || p.preference; p.group = f.groups?.[p.id] || p.group; }
    const dropped = (c.interventions || []).length; c.interventions = [];
    cfg = normalize(c);
    const idx = fork.persons.map(id => cfg.people.findIndex(p => p.id === id)).filter(i => i >= 0);
    const tally = {}; for (const i of idx) tally[cfg.people[i].group] = (tally[cfg.people[i].group] || 0) + 1;
    const from = Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0] || Object.keys(cfg.groups)[0], name = uniqueGroup("picked");
    makeGroup(name, from, idx);
    last = ""; save(); renderAll(); idx.forEach(i => view.state.sel.add(i)); renderLight();
    $("banner").innerHTML = `<div class="banner"><b>Started from round ${f.round} of the run.</b> Everyone begins where they stood and with what they believed then. Your ${idx.length} picked people are now the group <b>${esc(name)}</b> (settings copied from ${esc(from)}). Tune it in step 2, then run.${dropped ? ` ${dropped} scheduled interventions were dropped because they belonged to the old timeline.` : ""}</div>`;
    return;
  }
  let draft = null;
  try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); } catch { draft = null; }
  const scen = await api("/scenario").catch(() => null);
  if (draft?.cfg) {
    cfg = normalize(draft.cfg); last = ""; save(); renderAll();
    $("banner").innerHTML = `<div class="banner row"><span>Picked up your draft from ${new Date(draft.at).toLocaleString()}.</span><span class="spacer"></span><button class="btn" type="button" id="use-running">Use the running simulation instead</button></div>`;
    $("use-running").onclick = () => { if (scen) setConfig(scen.config); $("banner").innerHTML = ""; };
  } else {
    cfg = normalize(scen ? scen.config : freshTown(7)); last = ""; save(); renderAll();
  }
}
start().catch(err => { toast(err.message, "bad"); cfg = freshTown(7); last = ""; save(); renderAll(); });
