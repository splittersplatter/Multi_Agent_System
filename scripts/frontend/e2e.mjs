// End-to-end smoke test: drive headless Edge over CDP through /setup and /sim.
// Start a fresh server first (it launches scenarios into it), e.g.
//   PYTHONPATH="src;scripts/suchit_sims/plugins" python -m multi_agent_election.cli visual scripts/suchit_sims/showcase100.toml --port 8767
//   node scripts/frontend/e2e.mjs http://127.0.0.1:8767 <screenshot dir>
// Needs Node 22+ (built-in WebSocket) and Microsoft Edge; checks assume the showcase100 scenario.
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.argv[2] || "http://127.0.0.1:8766";
const OUT = process.argv[3] || ".";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const profile = mkdtempSync(join(tmpdir(), "edge-e2e-"));
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--remote-debugging-port=9333", `--user-data-dir=${profile}`, "--window-size=1440,1000", "about:blank"], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map(), errors = [], log = [];
async function connect() {
  for (let i = 0; i < 50; i++) {
    try { const list = await (await fetch("http://127.0.0.1:9333/json/list")).json(); const page = list.find(t => t.type === "page"); if (page) return page.webSocketDebuggerUrl; } catch { }
    await sleep(200);
  }
  throw new Error("no edge");
}
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
async function ev(expr) {
  const r = await send("Runtime.evaluate", { expression: `(async () => { ${expr} })()`, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error("eval: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}
async function go(url) { await send("Page.navigate", { url }); await sleep(2500); }
async function shot(name) { const r = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, name), Buffer.from(r.data, "base64")); }
async function mouse(type, x, y, mods = 0) { await send("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mouseReleased" ? 0 : 1, clickCount: 1, modifiers: mods }); }
const check = (name, ok, detail = "") => { log.push(`${ok ? "PASS" : "FAIL"} ${name}${detail ? " · " + detail : ""}`); };

try {
  ws = new WebSocket(await connect());
  await new Promise(r => ws.onopen = r);
  ws.onmessage = m => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
    if (d.method === "Runtime.exceptionThrown") errors.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
    if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") errors.push("console: " + d.params.args.map(a => a.value ?? a.description).join(" "));
  };
  await send("Runtime.enable"); await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

  // ---------- setup ----------
  await go(BASE + "/setup");
  await ev(`localStorage.clear()`);
  await go(BASE + "/setup");
  await sleep(1200);
  check("setup loads running scenario", await ev(`return cfg.people.length`) === 100);
  check("auto-check ready", (await ev(`return $("check").textContent`)).startsWith("Ready"), await ev(`return $("check").textContent`));
  check("toml export shown", (await ev(`return $("code").textContent`)).includes("[[people]]"));

  // hover + lasso + drag on the map with real pointer events
  await ev(`$("town").scrollIntoView({block:"center"})`); await sleep(300);
  const geo = await ev(`const r=$("town").getBoundingClientRect(), p=cfg.people[10].position, pad=22; return {x:r.left+pad+p[0]*(r.width-2*pad), y:r.top+pad+(1-p[1])*(r.height-2*pad), r:{l:r.left,t:r.top,w:r.width,h:r.height}, id:cfg.people[10].id, pos:p}`);
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: geo.x, y: geo.y, buttons: 0 }); await sleep(150);
  check("hover shows person", (await ev(`return $("person-title").textContent`)) === geo.id, await ev(`return $("person-title").textContent`));
  await mouse("mousePressed", geo.x, geo.y); await mouse("mouseMoved", geo.x + 40, geo.y + 20); await mouse("mouseMoved", geo.x + 60, geo.y + 30); await mouse("mouseReleased", geo.x + 60, geo.y + 30); await sleep(200);
  const moved = await ev(`return cfg.people[10].position`);
  check("drag moves a person", Math.abs(moved[0] - geo.pos[0]) > 0.03, JSON.stringify(geo.pos) + " -> " + JSON.stringify(moved));
  check("undo restores position", (await ev(`undo(); return JSON.stringify(cfg.people[10].position)`)) === JSON.stringify(geo.pos));
  const L = geo.r.l + 30, T = geo.r.t + geo.r.h * 0.55;
  await mouse("mousePressed", L, T); await mouse("mouseMoved", L + 120, T + 80); await mouse("mouseMoved", L + 260, T + 200); await mouse("mouseReleased", L + 260, T + 200); await sleep(200);
  const lasso = await ev(`return view.state.sel.size`);
  check("box select picks a crowd", lasso > 3, `${lasso} picked`);
  check("selection bar visible", await ev(`return !$("picked").hidden`));
  await shot("e2e-setup-lasso.png");

  // make group from the crowd
  await ev(`$("make-group").click()`); await sleep(200);
  await ev(`$("g-name").value="crowd"; document.querySelector('#group-form [value=make]').click()`); await sleep(300);
  check("make group", await ev(`return !!cfg.groups.crowd && cfg.people.filter(p=>p.group==="crowd").length`) === lasso);

  // bulk change: everyone ranks C>B>A, gather, hearing 0.2
  await ev(`$("bulk").click()`); await sleep(150);
  await ev(`document.querySelector('[data-mpref=set]').click(); for (const p of ["C","B","A"]) document.querySelector('#m-rank [data-rank="'+p+'"]').click();
    document.querySelector('[data-mpos=gather]').click(); document.querySelector('[data-mrad=set]').click(); $("m-rad").value="0.2";
    document.querySelector('#bulk-form [value=apply]').click()`); await sleep(300);
  check("bulk edit beliefs", await ev(`return cfg.people.filter(p=>p.group==="crowd").every(p=>p.preference.join()==="C,B,A" && p.overrides.proximity_radius===0.2)`));

  // add people via the dialog
  await ev(`openAdd("committed"); $("a-n").value="12"; document.querySelector('#add-form [value=add]').click()`); await sleep(300);
  check("add people", await ev(`return cfg.people.length`) === 112);
  check("added ids unique", await ev(`return new Set(cfg.people.map(p=>p.id)).size === cfg.people.length`));

  // group card edits
  await ev(`const card=document.querySelector('.gcard[data-g=committed]'); card.querySelector('[data-move=stationary]').click()`); await sleep(100);
  check("movement toggle", await ev(`return cfg.groups.committed.movement`) === "stationary");
  await ev(`const card=document.querySelector('.gcard[data-g=committed]'); card.querySelector('[data-cap=observe_electorate]').click()`);
  check("power toggle", await ev(`return cfg.groups.committed.capabilities.observe_electorate`) === true);
  await ev(`const i=document.querySelector('.gcard[data-g=committed] input[data-f=name]'); i.value="steady"; i.dispatchEvent(new Event("change"))`); await sleep(100);
  check("rename group", await ev(`return !cfg.groups.committed && cfg.people.some(p=>p.group==="steady")`));

  // parties
  await ev(`$("add-party").click()`); await sleep(100);
  check("add party", await ev(`return cfg.parties.join() + "|" + cfg.people[0].preference.length`) === "A,B,C,D|4");
  await ev(`document.querySelector('[data-drop="3"]').click()`); await sleep(100);
  check("drop party", await ev(`return cfg.parties.join()`) === "A,B,C");
  await sleep(1200);
  check("edited config still valid", (await ev(`return $("check").textContent`)).startsWith("Ready"), await ev(`return $("check").textContent`));

  // export -> paste round trip in both formats
  const toml = await ev(`return tomlText`);
  const before = await ev(`const canon = v => Array.isArray(v) ? "[" + v.map(canon).join(",") + "]" : v && typeof v === "object" ? "{" + Object.keys(v).sort().map(k => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}" : JSON.stringify(v); return canon(cfg)`);
  await ev(`setConfig(freshTown(99))`);
  check("fresh town", await ev(`return cfg.people.length + "|" + cfg.seed`) === "100|99");
  await ev(`$("paste").click(); $("paste-text").value = ${JSON.stringify(toml)}; document.querySelector('#paste-form [value=load]').click()`); await sleep(800);
  check("paste TOML round-trips exactly", (await ev(`const canon = v => Array.isArray(v) ? "[" + v.map(canon).join(",") + "]" : v && typeof v === "object" ? "{" + Object.keys(v).sort().map(k => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}" : JSON.stringify(v); return canon(cfg)`)) === before);
  await ev(`$("paste").click(); $("paste-text").value = JSON.stringify(cfg); document.querySelector('#paste-form [value=load]').click()`); await sleep(600);
  check("paste JSON round-trips exactly", (await ev(`const canon = v => Array.isArray(v) ? "[" + v.map(canon).join(",") + "]" : v && typeof v === "object" ? "{" + Object.keys(v).sort().map(k => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}" : JSON.stringify(v); return canon(cfg)`)) === before);
  await ev(`$("paste").click(); $("paste-text").value = "parties = [oops"; document.querySelector('#paste-form [value=load]').click()`); await sleep(500);
  check("bad paste reports error", (await ev(`return document.querySelector(".toast").textContent`)).includes("TOML"), await ev(`return document.querySelector(".toast").textContent`));
  await ev(`$("paste-dialog").close()`);

  // too few people blocks running
  await ev(`view.state.sel = new Set([0,1,2,3,4,5,6,7,8,9,10,11,12,13]); $("remove").click()`); await sleep(1300);
  check("under 100 blocked", (await ev(`return $("check").textContent + "|" + $("launch").disabled`)).includes("|true"), await ev(`return $("check").textContent`));
  await ev(`undo()`); await sleep(1300);
  await ev(`window.scrollTo(0, 0)`); await shot("e2e-setup-top.png");

  // launch
  const seed = await ev(`return cfg.seed`);
  await ev(`$("launch").click()`); await sleep(3500);
  check("launch goes to /sim", (await ev(`return location.pathname`)) === "/sim");

  // ---------- sim ----------
  await sleep(500);
  check("sim shows launched scenario", (await ev(`return S.ids.length + "|" + S.cfg.seed + "|" + ("crowd" in S.cfg.groups)`)) === `112|${seed}|true`, await ev(`return S.ids.length + "|" + S.cfg.seed`));
  for (let k = 0; k < 6; k++) { await ev(`await forward()`); }
  check("stepping", await ev(`return S.frames.length`) === 7);
  await ev(`setT(3)`);
  await ev(`view.state.sel = new Set([0,1,2,3]); render(); $("bulk").click()`); await sleep(150);
  await ev(`$("b-group").value = "crowd"; document.querySelector('[data-pos=spot]').click(); $("b-x").value="0.9"; $("b-y").value="0.9"; document.querySelector('#bulk-form [value=apply]').click()`); await sleep(2500);
  const after = await ev(`const c=S.compact[S.t]; return {t:S.t, n:S.frames.length, g:[0,1,2,3].map(i=>c.group[i]), x:[0,1,2,3].map(i=>c.xy[i])}`);
  check("sim bulk edit rewinds + applies", after.t === 4 && after.n === 5 && after.g.every(g => g === "crowd") && after.x.every(([x, y]) => x > .7 && y > .7), JSON.stringify(after));
  // hover via pointer
  await ev(`window.scrollTo(0,0)`); await sleep(200);
  const g2 = await ev(`const r=$("town").getBoundingClientRect(), p=S.compact[S.t].xy[20], pad=22; return {x:r.left+pad+p[0]*(r.width-2*pad), y:r.top+pad+(1-p[1])*(r.height-2*pad), id:S.ids[20]}`);
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: g2.x, y: g2.y, buttons: 0 }); await sleep(200);
  check("sim hover explains person", (await ev(`return $("now-title").textContent`)) === g2.id);
  await shot("e2e-sim-hover.png");
  await ev(`document.querySelector('#charts canvas').dispatchEvent(new PointerEvent("pointerdown",{clientX:document.querySelector('#charts canvas').getBoundingClientRect().left+8,pointerId:1}))`).catch(() => {});
  check("chart click seeks", await ev(`return S.t`) === 0, String(await ev(`return S.t`)));
  await ev(`$("two-hop").click(); view.state.hover = 20; town.redraw()`); await sleep(200); await shot("e2e-sim-twohop.png");

  // fork the crowd back into setup
  await ev(`view.state.sel = new Set([30,31,32]); $("fork").click()`); await sleep(3500);
  check("fork lands on setup", (await ev(`return location.pathname + location.hash`)) === "/setup#fork");
  check("fork banner + new group", await ev(`return $("banner").textContent.includes("picked") && cfg.people.filter(p=>p.group.startsWith("picked")).length`) === 3);
  await ev(`window.scrollTo(0,0)`); await shot("e2e-fork.png");
} catch (err) { log.push("CRASH " + err.stack); }
finally {
  console.log(log.join("\n"));
  console.log(errors.length ? "PAGE ERRORS:\n" + errors.join("\n") : "no page errors");
  try { ws?.close(); } catch { }
  edge.kill();
  setTimeout(() => process.exit(0), 300);
}
