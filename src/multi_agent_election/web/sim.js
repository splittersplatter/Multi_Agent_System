"use strict";
// /sim: watch a run, see who hears whom, and change people mid-run.

const $ = id => document.getElementById(id);
const S = {
  revision: 0, cfg: null, ids: [], idx: new Map(), parties: [], pi: {}, pc: {}, groups: [], shapes: {},
  frames: [], compact: [], metrics: [], t: 0, rounds: 0, k: 1, playing: false, timer: null, busy: false,
  color: "vote", layers: { prox: true, follow: true, campaign: true }, charts: [],
};
const ABSTAIN = "#c9cfdb";

// ---------- data ----------
function compact(f) {
  const pairs = list => (list || []).filter(([a, b]) => S.idx.has(a) && S.idx.has(b)).map(([a, b]) => [S.idx.get(a), S.idx.get(b)]);
  return {
    round: f.round, raw: f,
    xy: S.ids.map(id => f.positions[id] || [.5, .5]),
    vote: S.ids.map(id => { const b = f.ballots[id]; return b && b.length ? S.pi[b[0]] : -1; }),
    fav: S.ids.map(id => { const p = f.preferences?.[id]; return p && p.length ? S.pi[p[0]] : -1; }),
    group: S.ids.map((id, i) => f.groups?.[id] ?? S.cfg.people[i].group),
    overrides: f.overrides || {},
    edges: { prox: pairs(f.proximity_edges), follow: pairs(f.persistent_edges), campaign: pairs(f.campaign_edges) },
  };
}
function metricsAt(t) {
  const c = S.compact[t], p = t ? S.compact[t - 1] : null, N = S.ids.length, P = S.parties.length;
  const counts = Array(P).fill(0); let voted = 0;
  c.vote.forEach(v => { if (v >= 0) { counts[v]++; voted++; } });
  const share = counts.map(x => voted ? x / voted : 0), sorted = [...share].sort((a, b) => b - a);
  const senders = Array.from({ length: N }, () => new Set());
  for (const kind of ["prox", "follow", "campaign"]) for (const [s, r] of c.edges[kind]) senders[r].add(s);
  let heard = 0, other = 0, same = 0, pairsN = 0;
  senders.forEach((set, i) => {
    heard += set.size; let saw = false;
    for (const s of set) if (c.vote[s] >= 0 && c.vote[i] >= 0) { pairsN++; if (c.vote[s] === c.vote[i]) same++; else saw = true; }
    if (saw) other++;
  });
  let turnover = null, switching = null, moved = null;
  if (p) {
    const a = new Set(p.edges.prox.map(([s, r]) => s * 100003 + r)), b = new Set(c.edges.prox.map(([s, r]) => s * 100003 + r));
    let inter = 0; for (const x of b) if (a.has(x)) inter++;
    const union = a.size + b.size - inter; turnover = union ? 1 - inter / union : 0;
    switching = c.vote.filter((v, i) => v !== p.vote[i]).length / N;
    moved = c.xy.reduce((s, [x, y], i) => s + Math.hypot(x - p.xy[i][0], y - p.xy[i][1]), 0) / N;
  }
  const sig = c.raw.public_signal?.latest;
  const det = c.raw.detector;
  return {
    counts, share, margin: sorted[0] - (sorted[1] || 0), switching, turnover, moved,
    heard: heard / N, other: other / N, echo: pairsN ? same / pairsN : null,
    follow: c.edges.follow.length, paid: c.edges.campaign.length,
    poll: sig ? S.parties.map((_, k) => (sig.report[k] - sig.source_truth[k]) / N) : null,
    det: det ? det.share_change : null, alert: det ? !!det.alert : false,
  };
}
const series = key => S.metrics.map(m => m[key]);

function load(snap) {
  S.revision = snap.revision;
  S.frames = snap.frames;
  S.compact = S.frames.map(compact);
  S.metrics = S.compact.map((_, t) => metricsAt(t));
  S.t = clamp(S.t, 0, S.frames.length - 1);
}
function appendFrame(frame, revision) {
  S.revision = revision;
  S.frames.push(frame); S.compact.push(compact(frame)); S.metrics.push(metricsAt(S.frames.length - 1));
}
async function boot() {
  const [snap, scen] = await Promise.all([api("/state"), api("/scenario")]);
  S.cfg = scen.config;
  S.parties = snap.parties; S.pi = Object.fromEntries(S.parties.map((p, i) => [p, i])); S.pc = partyColors(S.parties);
  S.ids = S.cfg.people.map(p => p.id); S.idx = new Map(S.ids.map((id, i) => [id, i]));
  S.groups = Object.keys(S.cfg.groups); S.shapes = groupShapes(S.groups);
  S.rounds = S.cfg.rounds; S.k = S.cfg.k;
  load(snap);
  S.t = S.frames.length - 1;
  readHash();
  $("meta").innerHTML = `<b>${S.ids.length}</b> people · <b>${S.parties.length}</b> parties · seed <b>${S.cfg.seed}</b>`;
  buildCharts(); buildLegend(); render();
}

// ---------- town ----------
const view = {
  state: { hover: -1, sel: new Set(), twoHop: false, changes: true },
  layers: S.layers, movable: false,
  nodes() {
    const c = S.compact[S.t];
    if (!c) return [];
    return c.xy.map(([x, y], i) => {
      const k = S.color === "vote" ? c.vote[i] : c.fav[i], g = c.group[i];
      return { x, y, fill: k >= 0 ? S.pc[S.parties[k]] : ABSTAIN, shape: S.shapes[g] || "circle", big: isCampaigner(g) };
    });
  },
  radius(i) {
    const c = S.compact[S.t], g = c.group[i], o = c.overrides[S.ids[i]];
    const own = o && typeof o === "object" ? o.proximity_radius : undefined;
    return own ?? S.cfg.groups[g]?.proximity_radius ?? S.cfg.network?.radius ?? null;
  },
  edges() { return S.compact[S.t]?.edges || { prox: [], follow: [], campaign: [] }; },
  prevEdges() { return S.t > 0 ? S.compact[S.t - 1].edges : null; },
  onChange() { renderSide(); },
};
// Campaigners: groups that make links or move by a plugin get drawn larger.
function isCampaigner(g) { const d = S.cfg.groups[g]; return !!d && (d.graph !== "none" || String(d.movement).startsWith("python:")); }
const town = makeTown($("town"), view);

// ---------- side panel ----------
const tag = p => `<span class="tag" style="background:${S.pc[p]}">${esc(p)}</span>`;
const gname = g => `${glyph(S.shapes[g] || "circle")} ${esc(g.replace(/_/g, " "))}`;
function describeMovement(d) {
  if (!d) return "–";
  if (d.movement === "stationary") return "stays put";
  if (d.movement === "random_walk") return `wanders (≤ ${d.max_step} per round)`;
  if (d.movement === "external") return "moved by a learner";
  return `custom (${d.movement.replace("python:", "")})`;
}
function renderSide() {
  const c = S.compact[S.t], m = S.metrics[S.t];
  if (!c) return;
  const f = town.focus(), sel = view.state.sel;
  $("picked").hidden = sel.size === 0; $("seln").textContent = sel.size;
  if (f >= 0) {
    const id = S.ids[f], g = c.group[f], d = S.cfg.groups[g], e = town.ego(f);
    const inc = new Set([...e.inc.prox, ...e.inc.follow, ...e.inc.campaign]);
    const out = new Set([...e.out.prox, ...e.out.follow, ...e.out.campaign]);
    const tally = S.parties.map(() => 0); for (const s of inc) if (c.vote[s] >= 0) tally[c.vote[s]]++;
    const top = tally.some(x => x) ? S.parties[tally.indexOf(Math.max(...tally))] : null;
    const fresh = Object.values(e.fresh.inc).flat().length, gone = Object.values(e.gone.inc).flat().length;
    const vote = c.vote[f] >= 0 ? tag(S.parties[c.vote[f]]) : "nobody (abstains)";
    const parts = [];
    if (e.inc.follow.length) parts.push(`${e.inc.follow.length} they follow`);
    if (e.inc.campaign.length) parts.push(`${e.inc.campaign.length} by paid link`);
    $("now-title").textContent = id;
    $("say").innerHTML = `<b>${esc(id)}</b> is one of the ${gname(g)}: they ${esc(ruleText(d?.voting || ""))}. ` +
      `They hear <b>${inc.size}</b> ${inc.size === 1 ? "person" : "people"}${parts.length ? ` (${parts.join(", ")})` : ""}` +
      (top ? `; most of what they hear is ${tag(top)}` : "") + `, and they vote ${vote}. ` +
      (c.fav[f] >= 0 ? `Their favourite is ${tag(S.parties[c.fav[f]])}. ` : "") +
      (S.t > 0 && (fresh || gone) ? `This round <b>${fresh}</b> new ${fresh === 1 ? "voice" : "voices"} reached them and <b>${gone}</b> dropped away.` : "");
    $("tally").innerHTML = S.parties.map((p, k) => `<div style="background:${S.pc[p]}"><span>${tally[k]}</span>hear ${esc(p)}</div>`).join("");
    const r = view.radius(f);
    $("kv").innerHTML = [
      ["Hearing range", r == null ? "only links" : r.toFixed(2)],
      ["Moves", describeMovement(d)],
      ["Voices in", `${e.inc.prox.length} near · ${e.inc.follow.length} follow · ${e.inc.campaign.length} paid`],
      ["Heard by", `${out.size} ${out.size === 1 ? "person" : "people"}`],
      ["Standing at", `(${c.xy[f][0].toFixed(2)}, ${c.xy[f][1].toFixed(2)})`],
    ].map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("");
    const powers = notablePowers(d?.capabilities);
    if (d && d.graph !== "none") powers.unshift(`makes links (${d.graph.replace("python:", "")})`);
    if (d && d.communication !== "none") powers.push(`talks: ${d.communication.replace("python:", "")}`);
    $("powers").innerHTML = powers.map(p => `<span class="chip power">${esc(p)}</span>`).join("");
    return;
  }
  $("now-title").textContent = sel.size > 1 ? `${sel.size} people picked` : "Right now";
  const lead = S.parties.map((p, k) => [p, m.share[k]]).sort((a, b) => b[1] - a[1]);
  if (sel.size > 1) {
    const tally = S.parties.map(() => 0); for (const i of sel) if (c.vote[i] >= 0) tally[c.vote[i]]++;
    const groups = {}; for (const i of sel) groups[c.group[i]] = (groups[c.group[i]] || 0) + 1;
    $("say").innerHTML = `Your crowd: ${Object.entries(groups).map(([g, n]) => `<b>${n}</b> ${gname(g)}`).join(", ")}. Use <b>Change them…</b> to rewrite their beliefs, group or position from this round on.`;
    $("tally").innerHTML = S.parties.map((p, k) => `<div style="background:${S.pc[p]}"><span>${tally[k]}</span>vote ${esc(p)}</div>`).join("");
  } else {
    $("say").innerHTML = `In round <b>${S.t}</b>, ${tag(lead[0][0])} leads with <b>${pct(lead[0][1])}</b> of first choices` +
      (lead[1] ? `, ahead of ${tag(lead[1][0])} on ${pct(lead[1][1])}` : "") + ". " +
      (m.switching != null ? `<b>${Math.round(m.switching * S.ids.length)}</b> people changed their vote this round. ` : "") +
      `Point at anyone to see who they hear.`;
    $("tally").innerHTML = S.parties.map((p, k) => `<div style="background:${S.pc[p]}"><span>${m.counts[k]}</span>vote ${esc(p)}</div>`).join("");
  }
  $("kv").innerHTML = ""; $("powers").innerHTML = "";
}
function renderGroups() {
  const c = S.compact[S.t];
  $("groups").innerHTML = S.groups.map(g => {
    const members = c.group.map((x, i) => x === g ? i : -1).filter(i => i >= 0);
    if (!members.length) return "";
    const tally = S.parties.map(() => 0); members.forEach(i => { if (c.vote[i] >= 0) tally[c.vote[i]]++; });
    const bar = S.parties.map((p, k) => tally[k] ? `<span title="${esc(p)} ${tally[k]}" style="flex:${tally[k]};background:${S.pc[p]}"></span>` : "").join("");
    return `<div style="display:grid;grid-template-columns:1fr auto;gap:4px 12px;align-items:center">
      <div><b>${gname(g)}</b> <span class="mute small">· ${members.length} · ${esc(ruleText(S.cfg.groups[g].voting))}</span></div>
      <button class="btn ghost" data-pick="${esc(g)}" style="min-height:36px">Pick all</button>
      <div style="grid-column:1/-1;display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--line)">${bar}</div></div>`;
  }).join("");
  $("groups").querySelectorAll("[data-pick]").forEach(b => b.onclick = () => {
    view.state.sel.clear(); c.group.forEach((x, i) => { if (x === b.dataset.pick) view.state.sel.add(i); }); render();
  });
}

// ---------- charts ----------
function buildLegend() {
  $("share-legend").innerHTML = S.parties.map(p => `<span><span class="dot" style="background:${S.pc[p]}"></span> ${esc(p)}</span>`).join("") +
    `<span class="small">dashed line: an even split</span>`;
}
function buildCharts() {
  const share = lineChart($("c-share"), {
    series: () => S.parties.map((p, k) => ({ data: S.metrics.map(m => m.share[k]), color: S.pc[p], width: 3 })),
    range: () => { const v = S.metrics.flatMap(m => m.share); return [Math.max(0, Math.min(...v) - .05), Math.min(1, Math.max(...v) + .05)]; },
    guides: [{ value: 1 / S.parties.length }], t: () => S.t, span, onSeek: setT,
  });
  const defs = [
    { title: "Lead margin", note: "leader minus runner-up", val: m => pct(m.margin), s: () => [{ data: series("margin"), color: "#20232c", fill: "rgba(32,35,44,.08)" }], range: [0, null] },
    { title: "Voters switching", note: "changed their vote this round", val: m => pct(m.switching), s: () => [{ data: series("switching"), color: "#20232c" }], range: [0, null] },
    { title: "Contacts changing", note: "nearby links that appeared or broke", val: m => pct(m.turnover), s: () => [{ data: series("turnover"), color: "#5b6275" }], range: [0, null] },
    { title: "People heard", note: "average voices reaching each voter", val: m => m.heard.toFixed(1), s: () => [{ data: series("heard"), color: "#2f7df6" }], range: [0, null] },
    { title: "Hearing the other side", note: "voters who hear at least one different vote", val: m => pct(m.other), s: () => [{ data: series("other"), color: "#21ad6b" }], range: [0, 1] },
    { title: "Echo chamber", note: "voices that agree with the listener", val: m => pct(m.echo), s: () => [{ data: series("echo"), color: "#a35be8" }], range: [0, 1] },
    { title: "Follow links", note: "people following someone", val: m => m.follow, s: () => [{ data: series("follow"), color: "#8a4fe6" }], range: [0, null] },
    { title: "Paid links", note: "links bought by a campaign", val: m => m.paid, s: () => [{ data: series("paid"), color: "#e8336d" }], range: [0, null], show: () => S.cfg.campaign_controller || S.metrics.some(m => m.paid) },
    { title: "How far people walk", note: "average distance moved this round", val: m => m.moved == null ? "–" : m.moved.toFixed(3), s: () => [{ data: series("moved"), color: "#d99a00" }], range: [0, null] },
    { title: "Poll vs truth", note: "published minus true share, by party", val: m => m.poll ? S.parties.map((p, k) => `${p} ${m.poll[k] >= 0 ? "+" : ""}${Math.round(m.poll[k] * 100)}`).join(" ") : "no poll yet",
      s: () => S.parties.map((p, k) => ({ data: S.metrics.map(m => m.poll ? m.poll[k] : null), color: S.pc[p] })), range: null, guides: [{ value: 0 }], show: () => !!S.cfg.signal_controller },
    { title: "Watchdog", note: "target's share change; alarm past the dashed line", val: m => m.alert ? "Alarm!" : (m.det == null ? "–" : (m.det >= 0 ? "+" : "") + Math.round(m.det * 100) + " pts"),
      s: () => [{ data: series("det"), color: "#c2263c" }], range: null, guides: () => S.cfg.detector ? [{ value: S.cfg.detector.threshold, color: "#c2263c" }, { value: 0 }] : [], show: () => !!S.cfg.detector },
  ].filter(d => !d.show || d.show());
  $("charts").innerHTML = defs.map((d, i) => `<div class="chart-card"><h3>${esc(d.title)}</h3><div class="big" id="cv-${i}"></div><canvas class="chart" id="cc-${i}" aria-label="${esc(d.title)} over time"></canvas><p class="note">${esc(d.note)}</p></div>`).join("");
  S.charts = [share, ...defs.map((d, i) => lineChart($(`cc-${i}`), {
    series: d.s, t: () => S.t, span, onSeek: setT,
    range: d.range === null ? undefined : () => { const v = d.s().flatMap(x => x.data).filter(x => x != null); return [d.range[0], d.range[1] ?? Math.max(1e-6, ...v) * 1.1]; },
    get guides() { return typeof d.guides === "function" ? d.guides() : d.guides; },
  }))];
  S.chartVals = defs.map((d, i) => () => { $(`cv-${i}`).textContent = d.val(S.metrics[S.t]); });
}
const span = () => Math.max(S.frames.length - 1, 1);

// Deep links: #round=24&focus=r12&pick=r03,r17 (focus pins one person; pick selects a crowd).
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.has("round")) S.t = clamp(+h.get("round") || 0, 0, S.frames.length - 1);
  for (const id of (h.get("pick") || "").split(",")) if (S.idx.has(id)) view.state.sel.add(S.idx.get(id));
  if (S.idx.has(h.get("focus"))) { if (!h.has("pick")) view.state.sel.clear(); view.state.hover = S.idx.get(h.get("focus")); }
}

// ---------- timeline ----------
function setT(t) { S.t = clamp(t, 0, S.frames.length - 1); render(); }
function render() {
  const m = S.metrics[S.t];
  if (!m) return;
  $("rnum").textContent = S.t; $("rof").textContent = `of ${S.frames.length - 1} run · ${S.rounds} planned`;
  $("slider").max = S.frames.length - 1; $("slider").value = S.t;
  $("share-big").innerHTML = S.parties.map((p, k) => `<span style="color:${S.pc[p]}">${esc(p)} ${pct(m.share[k])}</span>`).join("");
  town.redraw(); S.charts.forEach(c => c.redraw()); (S.chartVals || []).forEach(f => f());
  renderSide(); renderGroups();
}
async function stepOnce() {
  if (S.busy) return false;
  S.busy = true;
  try {
    const r = await api("/command", { action: "step", revision: S.revision });
    appendFrame(r.frame, r.revision); return true;
  } catch (err) { toast(err.message, "bad"); stop(); return false; }
  finally { S.busy = false; }
}
async function forward() {
  if (S.t < S.frames.length - 1) { setT(S.t + 1); return true; }
  if (S.frames.length - 1 >= S.rounds) { toast(`That's all ${S.rounds} planned rounds. Set more rounds on the Set up page.`); return false; }
  if (await stepOnce()) { setT(S.frames.length - 1); return true; }
  return false;
}
function stop() { S.playing = false; clearTimeout(S.timer); $("play").textContent = "▶"; $("play").setAttribute("aria-label", "Play"); }
async function tick() {
  if (!S.playing) return;
  if (!(await forward())) { stop(); return; }
  S.timer = setTimeout(tick, +$("speed").value);
}
$("play").onclick = () => {
  if (S.playing) { stop(); return; }
  S.playing = true; $("play").textContent = "❚❚"; $("play").setAttribute("aria-label", "Pause"); tick();
};
$("back").onclick = () => setT(S.t - 1);
$("fwd").onclick = () => forward();
$("slider").oninput = e => setT(+e.target.value);
window.addEventListener("keydown", e => {
  if (e.target.closest("input,select,textarea,dialog")) return;
  if (e.key === "ArrowRight") { forward(); e.preventDefault(); }
  if (e.key === "ArrowLeft") { setT(S.t - 1); e.preventDefault(); }
  if (e.key === " " && e.target === document.body) { $("play").click(); e.preventDefault(); }
});
document.querySelectorAll("[data-layer]").forEach(b => b.onclick = () => {
  S.layers[b.dataset.layer] = !S.layers[b.dataset.layer]; b.setAttribute("aria-pressed", S.layers[b.dataset.layer]); town.redraw();
});
document.querySelectorAll("[data-color]").forEach(b => b.onclick = () => {
  S.color = b.dataset.color; document.querySelectorAll("[data-color]").forEach(x => x.setAttribute("aria-pressed", x === b)); town.redraw();
});
for (const [id, key] of [["two-hop", "twoHop"], ["changes", "changes"]]) $(id).onclick = () => {
  view.state[key] = !view.state[key]; $(id).setAttribute("aria-pressed", view.state[key]); town.redraw();
};
$("clear").onclick = () => { view.state.sel.clear(); render(); };

// ---------- bulk edit ----------
const B = { pref: "keep", ballot: "keep", pos: "keep", rank: [] };
function seg(attr, key) {
  document.querySelectorAll(`[data-${attr}]`).forEach(b => b.onclick = () => {
    B[key] = b.dataset[attr]; document.querySelectorAll(`[data-${attr}]`).forEach(x => x.setAttribute("aria-pressed", x === b));
    $("b-rank").hidden = B.pref === "keep" && B.ballot === "keep"; $("b-spot").hidden = B.pos !== "spot"; drawRank();
  });
}
seg("pref", "pref"); seg("ballot", "ballot"); seg("pos", "pos");
function drawRank() {
  const left = S.parties.filter(p => !B.rank.includes(p));
  $("b-rank").innerHTML = B.rank.map((p, i) => `${i ? '<span class="sep">›</span>' : ""}<button type="button" data-unrank="${i}" style="background:${S.pc[p]}" title="Remove">${esc(p)}</button>`).join("") +
    (left.length ? `<span class="sep">${B.rank.length ? "then" : "pick"}</span>` + left.map(p => `<button type="button" data-rank="${esc(p)}" style="background:${S.pc[p]};opacity:.55">${esc(p)}</button>`).join("") : "");
  $("b-rank").querySelectorAll("[data-rank]").forEach(b => b.onclick = () => { B.rank.push(b.dataset.rank); drawRank(); });
  $("b-rank").querySelectorAll("[data-unrank]").forEach(b => b.onclick = () => { B.rank.splice(+b.dataset.unrank); drawRank(); });
}
$("bulk").onclick = () => {
  const n = view.state.sel.size, last = S.frames.length - 1;
  $("bulk-title").textContent = `Change ${n} ${n === 1 ? "person" : "people"}`;
  $("bulk-note").textContent = `Takes effect from round ${S.t + 1}.` + (S.t < last ? ` Rounds ${S.t + 1}–${last} will be thrown away and re-run.` : "");
  $("b-group").innerHTML = `<option value="">Keep their groups</option>` + S.groups.map(g => `<option value="${esc(g)}">${esc(g.replace(/_/g, " "))}</option>`).join("");
  $("b-k").textContent = S.k; B.rank = []; drawRank();
  $("bulk-dialog").showModal();
};
$("bulk-form").addEventListener("submit", async ev => {
  if (ev.submitter?.value !== "apply") return;
  ev.preventDefault();
  const sel = [...view.state.sel], c = S.compact[S.t], shared = {};
  if ($("b-group").value) shared.group = $("b-group").value;
  if (B.pref === "set") { if (B.rank.length !== S.parties.length) { toast("Rank every party to set their beliefs.", "bad"); return; } shared.preference = [...B.rank]; }
  if (B.ballot === "set") { if (B.rank.length < S.k) { toast(`Pick at least ${S.k} parties for the ballot.`, "bad"); return; } shared.ballot = B.rank.slice(0, S.k); }
  const edits = sel.map(i => ({ person: S.ids[i], changes: { ...shared } }));
  if (B.pos !== "keep") {
    const r = rng(S.t * 7919 + sel.length);
    const cx = B.pos === "spot" ? clamp(+$("b-x").value, 0, 1) : sel.reduce((s, i) => s + c.xy[i][0], 0) / sel.length;
    const cy = B.pos === "spot" ? clamp(+$("b-y").value, 0, 1) : sel.reduce((s, i) => s + c.xy[i][1], 0) / sel.length;
    const spread = clamp(+$("b-spread").value || 0, 0, .5);
    edits.forEach((e, n) => {
      const [x, y] = c.xy[sel[n]];
      e.changes.position = B.pos === "gather" ? [cx + (x - cx) * .25, cy + (y - cy) * .25] : [cx + r.normal() * spread, cy + r.normal() * spread];
      e.changes.position = e.changes.position.map(v => +clamp(v, 0, 1).toFixed(4));
    });
  }
  if (!Object.keys(edits[0].changes).length) { toast("Nothing to change yet: pick a group, beliefs, ballot or position.", "bad"); return; }
  $("b-apply").disabled = true;
  try {
    stop();
    const snap = await api("/command", { action: "bulk_edit", revision: S.revision, round: S.t, edits });
    load(snap); $("bulk-dialog").close();
    if (await stepOnce()) S.t = S.frames.length - 1;
    render(); toast(`Changed ${sel.length} ${sel.length === 1 ? "person" : "people"} from round ${S.t}.`, "ok");
  } catch (err) { toast(err.message, "bad"); }
  finally { $("b-apply").disabled = false; }
});

// Hand the crowd to /setup as a new group, starting from this round's positions and beliefs.
$("fork").onclick = () => {
  try { sessionStorage.setItem("eclipse-fork", JSON.stringify({ round: S.t, persons: [...view.state.sel].map(i => S.ids[i]) })); }
  catch { toast("Your browser blocked storage, so the crowd can't be handed over.", "bad"); return; }
  location.href = "/setup#fork";
};

boot().catch(err => { $("meta").textContent = "Couldn't load"; toast(err.message, "bad"); });
