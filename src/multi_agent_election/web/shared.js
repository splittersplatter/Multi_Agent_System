"use strict";
// Shared pieces for /setup and /sim: API client, colours, shapes, the town canvas and line charts.

const TOKEN = document.querySelector('meta[name="session-token"]')?.content || "";

async function api(path, body) {
  const init = { headers: { "X-Session-Token": TOKEN }, cache: "no-store" };
  if (body !== undefined) {
    init.method = "POST";
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const response = await fetch(path, init);
  let data = null;
  try { data = await response.json(); } catch { /* non-JSON error page */ }
  if (!response.ok) throw new Error(data?.error || `${path} failed (${response.status})`);
  return data;
}

const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = x => (x == null || !isFinite(x)) ? "–" : Math.round(x * 100) + "%";
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// Party colours: distinct, colour-blind-aware first eight, then evenly spaced hues.
const PALETTE = ["#2f7df6", "#ff7433", "#21ad6b", "#a35be8", "#d99a00", "#e8336d", "#13a0b2", "#7d6a52"];
function partyColors(parties) {
  return Object.fromEntries(parties.map((p, i) => [p, PALETTE[i] || `hsl(${(i * 137.5) % 360} 62% 48%)`]));
}

// Group shapes, assigned by group order so a config always looks the same.
const SHAPES = ["circle", "square", "diamond", "tri", "hex", "star", "pent", "cross"];
const SHAPE_NAME = { circle: "circle", square: "square", diamond: "diamond", tri: "triangle", hex: "hexagon", star: "star", pent: "pentagon", cross: "cross" };
function groupShapes(groups) { return Object.fromEntries(groups.map((g, i) => [g, SHAPES[i % SHAPES.length]])); }

function polygon(ctx, x, y, r, n, rot, inner) {
  const pts = inner ? n * 2 : n;
  for (let k = 0; k < pts; k++) {
    const a = rot + (k * Math.PI * 2) / pts, rr = inner && k % 2 ? r * inner : r;
    const px = x + Math.cos(a) * rr, py = y + Math.sin(a) * rr;
    k ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.closePath();
}
function shapePath(ctx, kind, x, y, s) {
  ctx.beginPath();
  switch (kind) {
    case "square": ctx.rect(x - s * .86, y - s * .86, s * 1.72, s * 1.72); break;
    case "diamond": polygon(ctx, x, y, s * 1.22, 4, -Math.PI / 2); break;
    case "tri": polygon(ctx, x, y + s * .2, s * 1.38, 3, -Math.PI / 2); break;
    case "hex": polygon(ctx, x, y, s * 1.08, 6, 0); break;
    case "star": polygon(ctx, x, y, s * 1.4, 5, -Math.PI / 2, .5); break;
    case "pent": polygon(ctx, x, y, s * 1.12, 5, -Math.PI / 2); break;
    case "cross": {
      const a = s * .38, b = s * 1.1;
      ctx.moveTo(x - a, y - b); ctx.lineTo(x + a, y - b); ctx.lineTo(x + a, y - a); ctx.lineTo(x + b, y - a); ctx.lineTo(x + b, y + a);
      ctx.lineTo(x + a, y + a); ctx.lineTo(x + a, y + b); ctx.lineTo(x - a, y + b); ctx.lineTo(x - a, y + a); ctx.lineTo(x - b, y + a);
      ctx.lineTo(x - b, y - a); ctx.lineTo(x - a, y - a); ctx.closePath(); break;
    }
    default: ctx.arc(x, y, s, 0, Math.PI * 2);
  }
}
// The same shapes as inline SVG for legends and buttons.
function glyph(kind, fill = "#20232c", stroke = "none") {
  const pts = (n, r, rot, inner) => Array.from({ length: inner ? n * 2 : n }, (_, k) => {
    const a = rot + (k * Math.PI * 2) / (inner ? n * 2 : n), rr = inner && k % 2 ? r * inner : r;
    return `${(10 + Math.cos(a) * rr).toFixed(2)},${(10 + Math.sin(a) * rr).toFixed(2)}`;
  }).join(" ");
  const body = {
    circle: '<circle cx="10" cy="10" r="7"/>',
    square: '<rect x="3.5" y="3.5" width="13" height="13"/>',
    diamond: `<polygon points="${pts(4, 8.5, -Math.PI / 2)}"/>`,
    tri: `<polygon points="${pts(3, 9, -Math.PI / 2).replace(/,(\S+)/g, (m, y) => "," + (+y + 1.5).toFixed(2))}"/>`,
    hex: `<polygon points="${pts(6, 8, 0)}"/>`,
    star: `<polygon points="${pts(5, 9.5, -Math.PI / 2, .5)}"/>`,
    pent: `<polygon points="${pts(5, 8.5, -Math.PI / 2)}"/>`,
    cross: '<path d="M7.5 2.5h5v5h5v5h-5v5h-5v-5h-5v-5h5z"/>',
  }[kind] || '<circle cx="10" cy="10" r="7"/>';
  return `<svg class="glyph" viewBox="0 0 20 20" aria-hidden="true" fill="${fill}" stroke="${stroke}" stroke-width="1.6">${body}</svg>`;
}

let toastTimer = null;
function toast(message, kind = "") {
  let el = document.querySelector(".toast");
  if (!el) { el = document.createElement("div"); el.setAttribute("role", "status"); document.body.appendChild(el); }
  el.className = "toast " + kind; el.textContent = message; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, kind === "bad" ? 7000 : 3200);
}

// Seeded generator (mulberry32) so "scatter with seed" is reproducible.
function rng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  const next = () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  next.normal = () => { const u = Math.max(next(), 1e-12), v = next(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  next.pick = list => list[Math.floor(next() * list.length)];
  return next;
}

// Directed adjacency for one round: index pairs [sender, receiver] by edge kind.
function adjacency(edges) {
  const out = {};
  for (const kind of Object.keys(edges)) {
    const inc = new Map(), outs = new Map(), keys = new Set();
    for (const [s, r] of edges[kind]) {
      if (!inc.has(r)) inc.set(r, []); inc.get(r).push(s);
      if (!outs.has(s)) outs.set(s, []); outs.get(s).push(r);
      keys.add(s * 100003 + r);
    }
    out[kind] = { inc, out: outs, keys };
  }
  return out;
}

// ---------- the town canvas ----------
// view: { nodes() -> [{x,y,fill,shape,big}], radius(i), edges() -> {prox,follow,campaign},
//         prevEdges() -> same|null, layers, state:{hover,sel,twoHop,changes}, movable, onMove(ids,dx,dy), onChange() }
const EDGE_COLORS = { prox: "#9aa3b5", follow: "#8a4fe6", campaign: "#e8336d" };
function makeTown(canvas, view) {
  const ctx = canvas.getContext("2d");
  const st = view.state;
  let W = 0, H = 0, pad = 22, gesture = null, frame = 0, cache = { edges: null, adj: null, prev: null, padj: null };
  const toPx = ([x, y]) => [pad + x * (W - 2 * pad), pad + (1 - y) * (H - 2 * pad)];
  const toUnit = (px, py) => [(px - pad) / (W - 2 * pad), 1 - (py - pad) / (H - 2 * pad)];
  const focus = () => st.hover >= 0 ? st.hover : (st.sel.size === 1 ? [...st.sel][0] : -1);

  function adj() {
    const e = view.edges();
    if (cache.edges !== e) { cache.edges = e; cache.adj = adjacency(e); }
    const p = view.prevEdges ? view.prevEdges() : null;
    if (cache.prev !== p) { cache.prev = p; cache.padj = p ? adjacency(p) : null; }
    return { now: cache.adj, prev: cache.padj };
  }
  // Ego network of i: who they hear (inc), who hears them (out), what changed since last round, and 2 steps out.
  function ego(i) {
    const { now, prev } = adj(), r = { inc: {}, out: {}, fresh: { inc: {}, out: {} }, gone: { inc: {}, out: {} }, second: new Set() };
    for (const kind of ["prox", "follow", "campaign"]) {
      const a = now[kind];
      r.inc[kind] = a ? (a.inc.get(i) || []) : []; r.out[kind] = a ? (a.out.get(i) || []) : [];
      const b = prev && prev[kind];
      r.fresh.inc[kind] = b ? r.inc[kind].filter(s => !b.keys.has(s * 100003 + i)) : [];
      r.fresh.out[kind] = b ? r.out[kind].filter(t => !b.keys.has(i * 100003 + t)) : [];
      r.gone.inc[kind] = b ? (b.inc.get(i) || []).filter(s => !a || !a.keys.has(s * 100003 + i)) : [];
      r.gone.out[kind] = b ? (b.out.get(i) || []).filter(t => !a || !a.keys.has(i * 100003 + t)) : [];
    }
    for (const kind of ["prox", "follow", "campaign"]) for (const s of r.inc[kind])
      for (const k2 of ["prox", "follow", "campaign"]) for (const s2 of (now[k2]?.inc.get(s) || [])) if (s2 !== i) r.second.add(s2);
    return r;
  }

  function arrow(x1, y1, x2, y2, head, back = 8) {
    const a = Math.atan2(y2 - y1, x2 - x1), ex = x2 - Math.cos(a) * back, ey = y2 - Math.sin(a) * back;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(ex, ey); ctx.stroke();
    if (head) {
      ctx.beginPath(); ctx.moveTo(ex + Math.cos(a) * head * .4, ey + Math.sin(a) * head * .4);
      ctx.lineTo(ex - Math.cos(a - .45) * head, ey - Math.sin(a - .45) * head);
      ctx.lineTo(ex - Math.cos(a + .45) * head, ey - Math.sin(a + .45) * head); ctx.closePath(); ctx.fill();
    }
  }

  function draw() {
    frame = 0;
    const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (rect.width < 2 * pad + 10) return;
    if (canvas.width !== Math.round(rect.width * dpr) || canvas.height !== Math.round(rect.height * dpr)) {
      canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
    }
    W = rect.width; H = rect.height; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const nodes = view.nodes(), N = nodes.length;
    let xy = nodes.map(n => toPx([n.x, n.y]));
    if (gesture?.type === "move" && gesture.moved) {
      const [dx, dy] = gesture.delta;
      xy = xy.map((p, i) => gesture.ids.has(i) ? toPx([clamp(nodes[i].x + dx, 0, 1), clamp(nodes[i].y + dy, 0, 1)]) : p);
    }
    // field
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.roundRect(pad / 2, pad / 2, W - pad, H - pad, 14); ctx.fill();
    ctx.strokeStyle = "#e8ecf3"; ctx.lineWidth = 1;
    for (const g of [.25, .5, .75]) { const [gx] = toPx([g, 0]), [, gy] = toPx([0, g]); ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, H - pad); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke(); }

    const f = focus(), { now } = adj(), e = f >= 0 && f < N ? ego(f) : null;
    const scale = W - 2 * pad;
    const near = e ? new Set([f, ...Object.values(e.inc).flat(), ...Object.values(e.out).flat()]) : null;
    if (e) {                                             // hearing range
      const r = view.radius(f);
      if (r != null && r > 0) {
        ctx.fillStyle = "rgba(47,125,246,.09)"; ctx.beginPath(); ctx.arc(...xy[f], r * scale, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#20232c"; ctx.lineWidth = 2; ctx.setLineDash([6, 6]); ctx.stroke(); ctx.setLineDash([]);
      }
    }
    // background layers
    const edges = view.edges();
    if (view.layers.prox && edges.prox.length) {
      ctx.strokeStyle = EDGE_COLORS.prox; ctx.lineWidth = 1; ctx.globalAlpha = e ? .1 : .35; ctx.beginPath();
      for (const [s, r] of edges.prox) if (s < r || !now.prox.keys.has(r * 100003 + s)) { ctx.moveTo(...xy[s]); ctx.lineTo(...xy[r]); }
      ctx.stroke(); ctx.globalAlpha = 1;
    }
    for (const kind of ["follow", "campaign"]) if (view.layers[kind]) {
      ctx.strokeStyle = ctx.fillStyle = EDGE_COLORS[kind]; ctx.lineWidth = kind === "campaign" ? 1.6 : 1.2; ctx.globalAlpha = e ? .12 : .6;
      for (const [s, r] of edges[kind]) arrow(...xy[s], ...xy[r], 6, 7);
      ctx.globalAlpha = 1;
    }
    if (e) {
      if (st.twoHop) {                                   // 2 steps out: who reaches the people this agent hears
        ctx.strokeStyle = "#20232c"; ctx.globalAlpha = .22; ctx.lineWidth = 1;
        for (const kind of ["prox", "follow", "campaign"]) for (const s of e.inc[kind])
          for (const k2 of ["prox", "follow", "campaign"]) if (view.layers[k2]) for (const s2 of (now[k2]?.inc.get(s) || [])) if (s2 !== f) { ctx.beginPath(); ctx.moveTo(...xy[s2]); ctx.lineTo(...xy[s]); ctx.stroke(); }
        ctx.globalAlpha = 1;
      }
      if (st.changes) {                                  // lost links: dotted ghosts
        ctx.setLineDash([2, 5]); ctx.lineWidth = 2;
        for (const kind of ["prox", "follow", "campaign"]) if (view.layers[kind]) {
          ctx.strokeStyle = kind === "prox" ? "#8b90a0" : EDGE_COLORS[kind];
          for (const s of e.gone.inc[kind]) if (s < N) { ctx.beginPath(); ctx.moveTo(...xy[s]); ctx.lineTo(...xy[f]); ctx.stroke(); }
          for (const t of e.gone.out[kind]) if (t < N) { ctx.beginPath(); ctx.moveTo(...xy[f]); ctx.lineTo(...xy[t]); ctx.stroke(); }
        }
        ctx.setLineDash([]);
      }
      for (const dir of ["out", "inc"]) for (const kind of ["prox", "follow", "campaign"]) if (view.layers[kind]) {
        const color = dir === "inc" ? (kind === "prox" ? "#20232c" : EDGE_COLORS[kind]) : (kind === "prox" ? "#8b90a0" : EDGE_COLORS[kind]);
        const fresh = new Set(e.fresh[dir][kind]);
        for (const j of e[dir][kind]) {
          const [a, b] = dir === "inc" ? [xy[j], xy[f]] : [xy[f], xy[j]];
          if (st.changes && fresh.has(j)) {              // new this round: glow underlay
            ctx.strokeStyle = "rgba(255,196,0,.55)"; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
          }
          ctx.strokeStyle = ctx.fillStyle = color; ctx.lineWidth = dir === "inc" ? (kind === "prox" ? 1.8 : 2.4) : 1.4;
          ctx.setLineDash(dir === "inc" ? [] : [5, 4]);
          arrow(...a, ...b, dir === "inc" ? 8 : 6, 9);
        }
      }
      ctx.setLineDash([]);
    }
    // people
    const second = e && st.twoHop ? e.second : null;
    for (let i = 0; i < N; i++) {
      const n = nodes[i], s = n.big ? 9 : 6;
      ctx.globalAlpha = near && !near.has(i) ? (second && second.has(i) ? .6 : .2) : 1;
      shapePath(ctx, n.shape, ...xy[i], s);
      ctx.fillStyle = n.fill; ctx.fill();
      ctx.lineWidth = n.big ? 2.2 : 1.4; ctx.strokeStyle = "#20232c"; ctx.stroke();
      if (st.sel.has(i)) { ctx.lineWidth = 2.4; ctx.strokeStyle = "#20232c"; shapePath(ctx, n.shape, ...xy[i], s + 4.5); ctx.stroke(); }
    }
    ctx.globalAlpha = 1;
    if (f >= 0 && f < N) {
      ctx.lineWidth = 3; ctx.strokeStyle = "#20232c"; shapePath(ctx, nodes[f].shape, ...xy[f], (nodes[f].big ? 9 : 6) + 7); ctx.stroke();
      ctx.lineWidth = 2; ctx.strokeStyle = "#fff"; shapePath(ctx, nodes[f].shape, ...xy[f], (nodes[f].big ? 9 : 6) + 5); ctx.stroke();
    }
    if (gesture?.type === "lasso" && gesture.moved) {
      ctx.fillStyle = "rgba(47,125,246,.08)"; ctx.strokeStyle = "#20232c"; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5;
      const { x0, y0, x1, y1 } = gesture; ctx.fillRect(x0, y0, x1 - x0, y1 - y0); ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.setLineDash([]);
    }
  }
  const redraw = () => { if (!frame) frame = requestAnimationFrame(draw); };

  function pick(mx, my) {
    const nodes = view.nodes(); let best = -1, bd = 15 * 15;
    nodes.forEach((n, i) => { const [x, y] = toPx([n.x, n.y]), d = (x - mx) ** 2 + (y - my) ** 2; if (d < bd) { bd = d; best = i; } });
    return best;
  }
  const at = ev => { const r = canvas.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  const changed = () => { redraw(); view.onChange && view.onChange(); };

  canvas.addEventListener("pointerdown", ev => {
    if (ev.button !== 0) return;
    const [x, y] = at(ev), i = pick(x, y), add = ev.shiftKey || ev.ctrlKey || ev.metaKey;
    try { canvas.setPointerCapture(ev.pointerId); } catch { /* synthetic events */ }
    if (view.movable && i >= 0 && !add) gesture = { type: "move", ids: new Set(st.sel.has(i) ? st.sel : [i]), i, x0: x, y0: y, moved: false, delta: [0, 0] };
    else gesture = { type: "lasso", i, add, x0: x, y0: y, x1: x, y1: y, moved: false };
  });
  canvas.addEventListener("pointermove", ev => {
    const [x, y] = at(ev);
    if (gesture) {
      gesture.moved = gesture.moved || Math.abs(x - gesture.x0) + Math.abs(y - gesture.y0) > 5;
      if (gesture.type === "move") { const [u0, v0] = toUnit(gesture.x0, gesture.y0), [u1, v1] = toUnit(x, y); gesture.delta = [u1 - u0, v1 - v0]; }
      else { gesture.x1 = x; gesture.y1 = y; }
      redraw(); return;
    }
    const h = pick(x, y);
    if (h !== st.hover) { st.hover = h; canvas.style.cursor = h >= 0 ? (view.movable ? "grab" : "pointer") : "crosshair"; changed(); }
  });
  canvas.addEventListener("pointerup", ev => {
    const g = gesture; gesture = null;
    if (!g) return;
    if (g.type === "move" && g.moved) { view.onMove([...g.ids], ...g.delta); changed(); return; }
    if (g.type === "lasso" && g.moved) {
      const nodes = view.nodes(), [x0, x1] = [Math.min(g.x0, g.x1), Math.max(g.x0, g.x1)], [y0, y1] = [Math.min(g.y0, g.y1), Math.max(g.y0, g.y1)];
      if (!g.add) st.sel.clear();
      nodes.forEach((n, i) => { const [x, y] = toPx([n.x, n.y]); if (x >= x0 && x <= x1 && y >= y0 && y <= y1) st.sel.add(i); });
      changed(); return;
    }
    const i = g.i, add = g.add;                        // a click
    if (i >= 0) {
      if (add) st.sel.has(i) ? st.sel.delete(i) : st.sel.add(i);
      else { const only = st.sel.size === 1 && st.sel.has(i); st.sel.clear(); if (!only) st.sel.add(i); }
    } else if (!add) st.sel.clear();
    changed();
  });
  canvas.addEventListener("pointerleave", () => { if (!gesture && st.hover !== -1) { st.hover = -1; changed(); } });
  window.addEventListener("keydown", ev => {
    if (ev.key === "Escape" && st.sel.size && !document.querySelector("dialog[open]")) { st.sel.clear(); changed(); }
  });
  new ResizeObserver(redraw).observe(canvas);
  return { redraw, ego, focus };
}

// ---------- line charts ----------
// opt: { series() -> [{data, color, width?, dash?, fill?}], range?: [lo,hi] | () => [lo,hi], guides?: [{value,color,dash}],
//        t() -> current index, span() -> last index on the x axis, onSeek(t) }
function lineChart(canvas, opt) {
  const ctx = canvas.getContext("2d"); let frame = 0;
  function draw() {
    frame = 0;
    const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1, W = rect.width, H = rect.height;
    if (W < 40 || H < 30) return;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const series = opt.series().filter(s => s.data.length), span = Math.max(1, opt.span());
    const values = series.flatMap(s => s.data).filter(v => v != null && isFinite(v));
    let [lo, hi] = typeof opt.range === "function" ? opt.range() : opt.range || [Math.min(0, ...values), Math.max(1e-9, ...values)];
    if (hi - lo < 1e-9) hi = lo + 1;
    const px = i => 6 + (i / span) * (W - 12), py = v => H - 8 - ((v - lo) / (hi - lo)) * (H - 16);
    ctx.lineWidth = 1; ctx.strokeStyle = "#d9dfea";
    ctx.beginPath(); ctx.moveTo(6, py(lo)); ctx.lineTo(W - 6, py(lo)); ctx.stroke();
    for (const g of opt.guides || []) { ctx.strokeStyle = g.color || "#b9c0cf"; ctx.setLineDash(g.dash || [4, 4]); ctx.beginPath(); ctx.moveTo(6, py(g.value)); ctx.lineTo(W - 6, py(g.value)); ctx.stroke(); ctx.setLineDash([]); }
    for (const s of series) {
      const pts = s.data.map((v, i) => v == null || !isFinite(v) ? null : [px(i), py(clamp(v, lo, hi))]);
      const path = () => { ctx.beginPath(); let open = false; for (const p of pts) { if (!p) { open = false; continue; } open ? ctx.lineTo(...p) : ctx.moveTo(...p); open = true; } };
      if (s.fill) { path(); const last = pts.filter(Boolean); if (last.length) { ctx.lineTo(last[last.length - 1][0], py(lo)); ctx.lineTo(last[0][0], py(lo)); ctx.closePath(); ctx.fillStyle = s.fill; ctx.fill(); } }
      path(); ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 2.4; ctx.setLineDash(s.dash || []); ctx.lineJoin = "round"; ctx.stroke(); ctx.setLineDash([]);
    }
    const t = opt.t();
    ctx.strokeStyle = "#20232c"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(px(t), 2); ctx.lineTo(px(t), H - 2); ctx.stroke();
    for (const s of series) { const v = s.data[t]; if (v == null || !isFinite(v)) continue; ctx.fillStyle = s.color; ctx.beginPath(); ctx.arc(px(t), py(clamp(v, lo, hi)), 3.6, 0, 7); ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke(); }
  }
  const seek = ev => { const r = canvas.getBoundingClientRect(); opt.onSeek(clamp(Math.round(((ev.clientX - r.left - 6) / (r.width - 12)) * Math.max(1, opt.span())), 0, Infinity)); };
  canvas.addEventListener("pointerdown", ev => { try { canvas.setPointerCapture(ev.pointerId); } catch { /* synthetic events */ } seek(ev); });
  canvas.addEventListener("pointermove", ev => { if (ev.buttons & 1) seek(ev); });
  const redraw = () => { if (!frame) frame = requestAnimationFrame(draw); };
  new ResizeObserver(redraw).observe(canvas);
  return { redraw };
}

// Plain-English names for voting rules and powers.
const RULES = {
  sincere: "always vote for their favourite",
  sensed_plurality: "copy the most common vote they hear",
  signal_confident: "trust the published poll",
  local_plurality: "back whoever is most popular among their neighbours",
  memory_pivotal: "remember past polls and vote where their ballot could tip the race",
  pivotal: "vote where their ballot could tip the race",
  expected_utility: "pick the ballot with the best expected outcome",
  top_k: "spread their ballot over their top choices",
  max_m: "maximise the chance their side wins",
  tie_u: "break near-ties toward their favourite",
  tie_h: "break near-ties using what they heard",
  tie_r: "break near-ties at random",
  poisson: "treat turnout as uncertain and vote to matter",
  local_dominance: "drop ballots that can never help them",
  maximin: "protect against the worst likely result",
  sight_plurality: "vote with the bloc they can see (coalition)",
  overheard_plurality: "vote with what they overheard (coalition)",
  coalition_fusion: "pool coalition intel, then vote together",
  source_local_dominance: "certified: drop dominated ballots",
  certified_conformity: "certified: conform to the local majority",
  epistemic_dere: "reason about what others know (de re)",
  epistemic_dominant: "pick ballots good in every world they can't rule out",
  epistemic_pessimistic: "assume the worst world they can't rule out",
};
const ruleText = rule => RULES[rule] || (rule.startsWith("python:") ? `follow a custom rule (${rule.slice(7)})` : rule.replace(/_/g, " "));
const POWERS = {
  observe_public_neighbors: ["sees public neighbours", true], observe_private_channels: ["reads private channels", true],
  observe_electorate: ["sees the whole town", false], sense_public_ballots: ["senses nearby ballots", false],
  sense_private_ballots: ["senses private ballots", false], observe_target_preferences: ["reads true preferences", false],
  intercept_private_reports: ["intercepts private reports", false], observe_public_signal: ["reads the published poll", false],
  receive_public_reports: ["hears public reports", true], receive_private_reports: ["hears private reports", true],
  send_public_reports: ["speaks publicly", true], send_private_reports: ["speaks privately", true],
  modify_persistent_edges: ["can make follow links", true], modify_private_channels: ["can change private channels", true],
  move: ["can move", true],
};
// Powers worth showing: anything switched away from its everyday default.
function notablePowers(capabilities) {
  return Object.entries(capabilities || {}).filter(([k, v]) => POWERS[k] && v !== POWERS[k][1])
    .map(([k, v]) => (v ? "" : "can't: ") + POWERS[k][0].replace(/^can /, ""));
}
