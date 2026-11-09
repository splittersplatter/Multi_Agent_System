// Shared interaction core for the design drafts (inlined by build_drafts.py).
// Real data: window.D (people, frames). Everything here is draft-only, not the product code.
const D = JSON.parse(document.getElementById("demo-data").textContent);
const N = D.people.length, PARTIES = D.parties, T = D.frames.length - 1;
const R = D.people.map(p => p.radius);
const SHAPE = { copycats: "circle", committed: "square", poll_watchers: "diamond", team_A: "tri", team_B: "tri", team_C: "tri" };
const GROUP_LABEL = { copycats: "Copycat", committed: "Committed", poll_watchers: "Poll-watcher", team_A: "Campaigner A", team_B: "Campaigner B", team_C: "Campaigner C" };

// ---------- derived data ----------
const proxCache = [];
function prox(t) {               // incoming proximity: sender s is heard by receiver r if within r's radius
  if (proxCache[t]) return proxCache[t];
  const xy = D.frames[t].xy, edges = [];
  for (let r = 0; r < N; r++) for (let s = 0; s < N; s++) {
    if (s === r) continue;
    const dx = xy[s][0] - xy[r][0], dy = xy[s][1] - xy[r][1];
    if (dx * dx + dy * dy <= R[r] * R[r]) edges.push([s, r]);
  }
  return (proxCache[t] = edges);
}
function links(t, i) {
  const f = D.frames[t], inc = { prox: [], follow: [], campaign: [] }, out = { prox: [], follow: [], campaign: [] };
  for (const [s, r] of prox(t)) { if (r === i) inc.prox.push(s); if (s === i) out.prox.push(r); }
  for (const [s, r] of f.follow) { if (r === i) inc.follow.push(s); if (s === i) out.follow.push(r); }
  for (const [s, r] of f.campaign) { if (r === i) inc.campaign.push(s); if (s === i) out.campaign.push(r); }
  return { inc, out };
}
function heardVotes(t, i) {
  const l = links(t, i), prev = D.frames[Math.max(0, t - 1)].v, tally = {};
  for (const p of PARTIES) tally[p] = 0;
  const seen = new Set([...l.inc.prox, ...l.inc.follow, ...l.inc.campaign]);
  for (const s of seen) tally[prev[s]]++;
  return { tally, n: seen.size };
}
const S = (() => {               // per-round series for the plots
  const out = { share: {}, switches: [], turnover: [], follow: [], campaign: [], pollGap: [], det: [], exposure: [], heard: [], margin: [] };
  for (const p of PARTIES) out.share[p] = [];
  let prevSet = null;
  for (let t = 0; t <= T; t++) {
    const f = D.frames[t], c = f.counts;
    for (const p of PARTIES) out.share[p].push(c[p] / N);
    out.switches.push(t ? [...f.v].filter((x, i) => x !== D.frames[t - 1].v[i]).length / N : 0);
    const set = new Set(prox(t).map(e => e.join(",")));
    if (prevSet) { let ch = 0; for (const e of set) if (!prevSet.has(e)) ch++; for (const e of prevSet) if (!set.has(e)) ch++; out.turnover.push(ch / Math.max(1, set.size + prevSet.size)); } else out.turnover.push(0);
    prevSet = set;
    out.follow.push(f.follow.length); out.campaign.push(f.campaign.length);
    out.pollGap.push(f.signal ? (f.signal.report[2] - f.signal.truth[2]) / N : 0);
    out.det.push(f.det && f.det.change !== null ? f.det.change : 0);
    const inc = Array.from({ length: N }, () => new Set());
    for (const [s, r] of prox(t)) inc[r].add(s);
    for (const [s, r] of f.follow) inc[r].add(s);
    let exposed = 0, heard = 0;
    for (let i = 0; i < N; i++) { heard += inc[i].size; for (const s of inc[i]) if (f.v[s] !== f.v[i]) { exposed++; break; } }
    out.exposure.push(exposed / N); out.heard.push(heard / N);
    const sorted = PARTIES.map(p => c[p]).sort((a, b) => b - a); out.margin.push((sorted[0] - sorted[1]) / N);
  }
  return out;
})();

// ---------- state ----------
const state = { t: 24, hover: -1, sel: new Set(), layers: { prox: true, follow: true, campaign: true }, playing: false, listeners: [] };
function emit() { for (const f of state.listeners) f(); }
function setRound(t) { state.t = Math.max(0, Math.min(T, t)); emit(); }

// ---------- drawing ----------
function shapePath(ctx, kind, x, y, s) {
  ctx.beginPath();
  if (kind === "square") ctx.rect(x - s * .85, y - s * .85, s * 1.7, s * 1.7);
  else if (kind === "diamond") { ctx.moveTo(x, y - s * 1.2); ctx.lineTo(x + s * 1.2, y); ctx.lineTo(x, y + s * 1.2); ctx.lineTo(x - s * 1.2, y); ctx.closePath(); }
  else if (kind === "tri") { ctx.moveTo(x, y - s * 1.45); ctx.lineTo(x + s * 1.3, y + s * .9); ctx.lineTo(x - s * 1.3, y + s * .9); ctx.closePath(); }
  else ctx.arc(x, y, s, 0, Math.PI * 2);
}
function arrow(ctx, x1, y1, x2, y2, head) {
  const a = Math.atan2(y2 - y1, x2 - x1), back = 7;
  const ex = x2 - Math.cos(a) * back, ey = y2 - Math.sin(a) * back;
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(ex, ey); ctx.stroke();
  if (head) { ctx.beginPath(); ctx.moveTo(ex + Math.cos(a) * head, ey + Math.sin(a) * head); ctx.lineTo(ex - Math.cos(a - .5) * head, ey - Math.sin(a - .5) * head); ctx.lineTo(ex - Math.cos(a + .5) * head, ey - Math.sin(a + .5) * head); ctx.closePath(); ctx.fill(); }
}
function makeNetwork(canvas, theme) {
  const ctx = canvas.getContext("2d"); let W = 0, H = 0, pad = theme.pad || 24, drag = null;
  const toPx = ([x, y]) => [pad + x * (W - 2 * pad), pad + (1 - y) * (H - 2 * pad)];
  function resize() { const r = canvas.getBoundingClientRect(), d = devicePixelRatio || 1; W = r.width; H = r.height; canvas.width = W * d; canvas.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); emit(); }   // emit so overlays re-place too
  function draw() {
    if (W <= 2 * pad) return;                      // not laid out yet
    const t = state.t, f = D.frames[t], xy = f.xy.map(toPx), h = state.hover;
    ctx.clearRect(0, 0, W, H);
    if (theme.background) theme.background(ctx, W, H, pad);
    const focus = h >= 0 ? links(t, h) : null;
    const near = focus ? new Set([h, ...focus.inc.prox, ...focus.inc.follow, ...focus.inc.campaign, ...focus.out.prox, ...focus.out.follow, ...focus.out.campaign]) : null;
    const scale = (W - 2 * pad);
    if (h >= 0) theme.halo(ctx, xy[h], R[h] * scale, D.people[h]);
    ctx.lineWidth = 1;
    if (state.layers.prox) { ctx.strokeStyle = theme.edge.prox; ctx.globalAlpha = focus ? .12 : theme.proxAlpha ?? .35;
      for (const [s, r] of prox(t)) { if (s < r) { ctx.beginPath(); ctx.moveTo(...xy[s]); ctx.lineTo(...xy[r]); ctx.stroke(); } } ctx.globalAlpha = 1; }
    for (const kind of ["follow", "campaign"]) if (state.layers[kind]) {
      ctx.strokeStyle = ctx.fillStyle = theme.edge[kind]; ctx.lineWidth = kind === "campaign" ? 1.6 : 1.1; ctx.globalAlpha = focus ? .15 : theme.linkAlpha ?? .55;
      for (const [s, r] of f[kind]) arrow(ctx, ...xy[s], ...xy[r], 0);
      ctx.globalAlpha = 1;
    }
    if (focus) {                                    // ego network: incoming solid, outgoing dashed
      const draws = [["inc", "prox"], ["inc", "follow"], ["inc", "campaign"], ["out", "prox"], ["out", "follow"], ["out", "campaign"]];
      for (const [dir, kind] of draws) {
        ctx.strokeStyle = ctx.fillStyle = dir === "inc" ? theme.ego.inc[kind] : theme.ego.out; ctx.lineWidth = dir === "inc" ? 1.8 : 1.2;
        ctx.setLineDash(dir === "inc" ? [] : [4, 4]);
        for (const j of focus[dir][kind]) dir === "inc" ? arrow(ctx, ...xy[j], ...xy[h], 6) : arrow(ctx, ...xy[h], ...xy[j], 5);
      }
      ctx.setLineDash([]);
    }
    for (let i = 0; i < N; i++) {
      const p = D.people[i], camp = p.group.startsWith("team"), s = (camp ? theme.size * 1.5 : theme.size);
      ctx.globalAlpha = near && !near.has(i) ? theme.dim : 1;
      shapePath(ctx, SHAPE[p.group], ...xy[i], s);
      ctx.fillStyle = theme.party[f.v[i]]; ctx.fill();
      ctx.lineWidth = camp ? theme.stroke * 1.6 : theme.stroke; ctx.strokeStyle = camp ? theme.campStroke : theme.agentStroke; ctx.stroke();
      if (state.sel.has(i)) { ctx.lineWidth = 2; ctx.strokeStyle = theme.select; shapePath(ctx, SHAPE[p.group], ...xy[i], s + 4.5); ctx.stroke(); }
    }
    ctx.globalAlpha = 1;
    if (h >= 0) { ctx.lineWidth = 2.5; ctx.strokeStyle = theme.focusStroke; shapePath(ctx, SHAPE[D.people[h].group], ...xy[h], theme.size * 1.9); ctx.stroke(); }
    if (drag && drag.lasso) { ctx.strokeStyle = theme.select; ctx.setLineDash([5, 4]); ctx.lineWidth = 1.2; ctx.strokeRect(drag.x0, drag.y0, drag.x1 - drag.x0, drag.y1 - drag.y0); ctx.setLineDash([]); }
    if (theme.after) theme.after(ctx, W, H, xy);
  }
  function pick(mx, my) {
    const xy = D.frames[state.t].xy.map(toPx); let best = -1, bd = 14 * 14;
    for (let i = 0; i < N; i++) { const d = (xy[i][0] - mx) ** 2 + (xy[i][1] - my) ** 2; if (d < bd) { bd = d; best = i; } }
    return best;
  }
  const at = e => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  canvas.addEventListener("mousemove", e => {
    const [x, y] = at(e);
    if (drag) { drag.x1 = x; drag.y1 = y; drag.lasso = Math.abs(x - drag.x0) + Math.abs(y - drag.y0) > 6; draw(); return; }
    const h = pick(x, y); if (h !== state.hover) { state.hover = h; canvas.style.cursor = h >= 0 ? "pointer" : "crosshair"; emit(); }
  });
  canvas.addEventListener("mouseleave", () => { if (!drag) { state.hover = -1; emit(); } });
  canvas.addEventListener("mousedown", e => { const [x, y] = at(e); drag = { x0: x, y0: y, x1: x, y1: y, lasso: false, add: e.shiftKey }; });
  window.addEventListener("mouseup", () => {
    if (!drag) return;
    const d = drag; drag = null;
    if (d.lasso) {
      const xy = D.frames[state.t].xy.map(toPx), [x0, x1] = [Math.min(d.x0, d.x1), Math.max(d.x0, d.x1)], [y0, y1] = [Math.min(d.y0, d.y1), Math.max(d.y0, d.y1)];
      if (!d.add) state.sel.clear();
      xy.forEach(([x, y], i) => { if (x >= x0 && x <= x1 && y >= y0 && y <= y1) state.sel.add(i); });
    } else {
      const i = pick(d.x0, d.y0);
      if (i >= 0) { if (!d.add) { const only = state.sel.size === 1 && state.sel.has(i); state.sel.clear(); if (!only) state.sel.add(i); } else state.sel.has(i) ? state.sel.delete(i) : state.sel.add(i); }
      else if (!d.add) state.sel.clear();
    }
    emit();
  });
  window.addEventListener("keydown", e => { if (e.key === "Escape") { state.sel.clear(); emit(); } });
  new ResizeObserver(resize).observe(canvas);
  state.listeners.push(draw);
  return { draw, toPx };
}

function lineChart(canvas, series, opt) {      // series: [{data, color, fill?, width?, dash?}]
  const ctx = canvas.getContext("2d");
  function draw() {
    const r = canvas.getBoundingClientRect(), d = devicePixelRatio || 1, W = r.width, H = r.height;
    if (W <= 2 * opt.pad || H <= 2 * opt.padY) return;
    canvas.width = W * d; canvas.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); ctx.clearRect(0, 0, W, H);
    const [lo, hi] = opt.range || [Math.min(...series.flatMap(s => s.data)), Math.max(...series.flatMap(s => s.data)) || 1];
    const px = i => opt.pad + i / T * (W - 2 * opt.pad), py = v => H - opt.padY - (v - lo) / ((hi - lo) || 1) * (H - 2 * opt.padY);
    if (opt.grid) { ctx.strokeStyle = opt.grid; ctx.lineWidth = 1; for (const g of opt.gridAt || [lo, hi]) { ctx.beginPath(); ctx.moveTo(opt.pad, py(g)); ctx.lineTo(W - opt.pad, py(g)); ctx.stroke(); } }
    for (const s of series) {
      ctx.beginPath(); s.data.forEach((v, i) => i ? ctx.lineTo(px(i), py(v)) : ctx.moveTo(px(i), py(v)));
      if (s.fill) { ctx.lineTo(px(T), py(lo)); ctx.lineTo(px(0), py(lo)); ctx.closePath(); ctx.fillStyle = s.fill; ctx.fill(); ctx.beginPath(); s.data.forEach((v, i) => i ? ctx.lineTo(px(i), py(v)) : ctx.moveTo(px(i), py(v))); }
      ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.6; ctx.setLineDash(s.dash || []); ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.strokeStyle = opt.playhead; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(px(state.t), 2); ctx.lineTo(px(state.t), H - 2); ctx.stroke();
    for (const s of series) { ctx.fillStyle = s.color; ctx.beginPath(); ctx.arc(px(state.t), py(s.data[state.t]), 2.6, 0, 7); ctx.fill(); }
  }
  canvas.addEventListener("click", e => { const r = canvas.getBoundingClientRect(); setRound(Math.round((e.clientX - r.left - opt.pad) / (r.width - 2 * opt.pad) * T)); });
  new ResizeObserver(draw).observe(canvas); state.listeners.push(draw);
  return draw;
}

function play(button) {
  state.playing = !state.playing;
  if (button) button.dataset.playing = state.playing;
  const tick = () => { if (!state.playing) return; setRound(state.t >= T ? 0 : state.t + 1); setTimeout(tick, 420); };
  tick();
}
const pct = x => (x * 100).toFixed(0) + "%";
