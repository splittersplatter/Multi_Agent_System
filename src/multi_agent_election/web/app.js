"use strict";
const token = document.querySelector('meta[name="session-token"]').content;
const $ = id => document.getElementById(id);
const ns = "http://www.w3.org/2000/svg";
let state, cursor = 0, selected = null, playing = false, busy = false, timer = null;

function svg(tag, attrs) {
  const el = document.createElementNS(ns, tag);
  for (const [name, value] of Object.entries(attrs)) el.setAttribute(name, String(value));
  return el;
}
function option(select, value, label) {
  const el = document.createElement("option"); el.value = value; el.textContent = label; select.append(el);
}
function color(party) { return `hsl(${(150 + state.parties.indexOf(party) * 137.508) % 360}deg 55% 42%)`; }
function groupColor(group) { return `hsl(${(state.group_names.indexOf(group) * 137.508 + 20) % 360}deg 65% 30%)`; }
function parseList(value) {
  const trimmed=value.trim();
  const result=trimmed.startsWith("[") ? JSON.parse(trimmed) : trimmed.split(",").map(x=>x.trim());
  if (!Array.isArray(result) || result.some(x=>typeof x!=="string")) throw new Error("Expected a list of IDs");
  return result;
}
function showError(message) { $("notice").textContent = message; }
async function request(path, body) {
  const init = {headers: {"X-Session-Token": token}};
  if (body) { init.method = "POST"; init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function render() {
  const frame = state.frames[cursor], row = state.metrics[cursor];
  $("color-label").textContent = $("color-mode").value === "ballot" ? "Researcher view · node color: submitted vote" : "Researcher view · node color: true first preference";
  $("round-label").textContent = `Round ${frame.round}`;
  $("status").textContent = `Revision ${state.revision} · ${state.frames.length} frames`;
  $("timeline").max = state.frames.length - 1; $("timeline").value = cursor;
  const ids = Object.keys(frame.positions);
  if (!ids.includes(selected)) selected = ids[0];
  const person = $("person"); person.replaceChildren();
  for (const id of ids) option(person, id, id);
  person.value = selected;
  const group = $("group"); group.replaceChildren();
  for (const name of state.group_names) option(group, name, name);
  group.value = frame.groups[selected];
  const filter = $("group-filter"), currentFilter = filter.value;
  filter.replaceChildren(); option(filter, "", "All groups");
  for (const name of state.group_names) option(filter, name, name);
  filter.value = currentFilter;
  const node = $("network"); node.replaceChildren();
  const defs=svg("defs",{}), layerColors={proximity:"#9aa9a2",persistent:"#526f91",campaign:"#bf6636"};
  for (const [layer,shade] of Object.entries(layerColors)) {
    const marker=svg("marker",{id:`arrow-${layer}`,viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:5,markerHeight:5,orient:"auto-start-reverse"});
    marker.append(svg("path",{d:"M 0 0 L 10 5 L 0 10 z",fill:shade}));defs.append(marker);
  }
  node.append(defs);
  const point = id => [40 + frame.positions[id][0] * 520, 380 - frame.positions[id][1] * 340];
  const edges = new Map();
  for (const [layer, visible, values] of [["proximity", $("show-proximity").checked, frame.proximity_edges], ["persistent", $("show-persistent").checked, frame.persistent_edges], ["campaign", $("show-campaign").checked, frame.campaign_edges]]) {
    if (visible) for (const edge of values) edges.set(JSON.stringify(edge), layer);
  }
  for (const [raw, layer] of edges) {
    const [a,b] = JSON.parse(raw), [x1,y1] = point(a), [x2,y2] = point(b);
    if (filter.value && (frame.groups[a] !== filter.value || frame.groups[b] !== filter.value)) continue;
    const distance=Math.hypot(x2-x1,y2-y1), offset=distance ? Math.min(11,distance/2)/distance : 0;
    const line=svg("line", {x1,y1,x2:x2-(x2-x1)*offset,y2:y2-(y2-y1)*offset,"marker-end":`url(#arrow-${layer})`,"data-layer":layer});
    line.style.stroke=layerColors[layer];node.append(line);
  }
  for (const id of ids) {
    if (filter.value && frame.groups[id] !== filter.value) continue;
    const [cx,cy] = point(id);
    const visibleParty = $("color-mode").value === "ballot" ? frame.ballots[id][0] : frame.preferences[id][0];
    const circle = svg("circle", {cx,cy,r:9,fill:color(visibleParty),class:id === selected ? "selected" : "",tabindex:0,role:"button","aria-label":`Select agent ${id}`});
    circle.style.stroke = id === selected ? "#152e38" : groupColor(frame.groups[id]);
    circle.style.strokeWidth = id === selected ? "4" : "2";
    const select = () => { selected = id; render(); };
    circle.addEventListener("click", select);
    circle.addEventListener("keydown", e => {if (e.key === "Enter" || e.key === " ") {e.preventDefault(); select();}});
    node.append(circle);
  }
  const legend = $("legend"); legend.replaceChildren();
  for (const party of state.parties) { const el = document.createElement("span"); el.style.setProperty("--color", color(party)); el.textContent = party; legend.append(el); }
  const groupLegend=$("group-legend");groupLegend.replaceChildren();
  for(const name of state.group_names){const el=document.createElement("span");el.style.setProperty("--color",groupColor(name));el.textContent=`Group: ${name}`;groupLegend.append(el);}
  const chart = $("chart"); chart.replaceChildren();
  for (const party of state.parties) {
    const points = state.metrics.map((m,i) => `${15 + i * 300 / Math.max(1,state.metrics.length-1)},${145 - m.shares[party] * 130}`).join(" ");
    chart.append(svg("polyline", {points,fill:"none",stroke:color(party),"stroke-width":2.5}));
  }
  chart.append(svg("line", {x1:15 + cursor*300/Math.max(1,state.metrics.length-1),x2:15 + cursor*300/Math.max(1,state.metrics.length-1),y1:8,y2:148,stroke:"#9aaaa3","stroke-dasharray":"3 3"}));
  for(let i=0;i<state.metrics.length;i++) if(state.metrics[i].intervention_count){const x=15+i*300/Math.max(1,state.metrics.length-1);chart.append(svg("line",{x1:x,x2:x,y1:8,y2:148,stroke:"#99543e","stroke-dasharray":"4 4"}));}
  $("stats").textContent = `Winner: ${row.winner}  ·  Margin: ${row.winner_margin}  ·  Public links: ${row.public_edge_count}`;
  $("details").textContent = `Ballot: ${frame.ballots[selected].join(" › ")} · Group: ${frame.groups[selected]} · Position: ${frame.positions[selected].map(v => v.toFixed(3)).join(", ")}`;
  $("capabilities").textContent = JSON.stringify({...state.group_capabilities[frame.groups[selected]], ...frame.overrides[selected].capabilities}, null, 2);
  $("ballot-sensors").textContent = JSON.stringify(frame.ballot_sensors.filter(entry => entry[0] === selected).map(([,sender,source,round,ballot]) => ({sender,source,round,ballot})), null, 2);
  $("preference").value = JSON.stringify(frame.preferences[selected]);
  $("overrides").value = JSON.stringify(frame.overrides[selected]);
  $("neighbors").value = JSON.stringify(frame.persistent_edges.filter(e=>e[0]===selected).map(e=>e[1]));
  $("campaign-neighbors").value = JSON.stringify(frame.campaign_edges.filter(e=>e[0]===selected).map(e=>e[1]));
  $("channels").value = JSON.stringify(Object.keys(frame.private_channels).filter(name=>frame.private_channels[name].includes(selected)));
  $("x").value = frame.positions[selected][0]; $("y").value = frame.positions[selected][1];
}
async function command(payload) {
  if (busy) {showError("A step is still completing; try again when paused.");return false;}
  busy = true;
  try {
    const result = await request("/command", {...payload, revision:state.revision});
    if (result.frame) {state.revision=result.revision;state.frames.push(result.frame);state.metrics.push(result.metric);}
    else state=result;
    cursor = state.frames.length-1; render(); showError("");return true;
  }
  catch (error) { pause(); showError(error.message); try {state=await request("/state"); cursor=Math.min(cursor,state.frames.length-1);render();} catch (_) {} return false; }
  finally {busy=false;}
}
async function next() {
  if (cursor < state.frames.length-1) {cursor++;render();}
  else await command({action:"step"});
}
function setEditingDisabled(disabled) {for (const input of $("edit").querySelectorAll("input,select,button")) input.disabled=disabled;}
function pause() {playing=false;clearTimeout(timer);$("play").textContent="Play";setEditingDisabled(false);}
async function tick() {if (!playing) return;await next();if (playing) timer=setTimeout(tick,Number($("speed").value));}
$("play").addEventListener("click", () => {if (playing) pause();else {playing=true;$("play").textContent="Pause";setEditingDisabled(true);tick();}});
$("previous").addEventListener("click", () => {pause();cursor=Math.max(0,cursor-1);render();});
$("next").addEventListener("click", () => {pause();next();});
$("timeline").addEventListener("input", e => {pause();cursor=Number(e.target.value);render();});
$("person").addEventListener("change", e => {selected=e.target.value;render();});
for (const id of ["color-mode", "group-filter", "show-persistent", "show-proximity", "show-campaign"]) $(id).addEventListener("change", render);
$("edit").addEventListener("submit", async e => {
  e.preventDefault();pause();
  let overrides, neighbors, campaignNeighbors, channels;
  try {
    overrides=JSON.parse($("overrides").value);neighbors=JSON.parse($("neighbors").value);campaignNeighbors=JSON.parse($("campaign-neighbors").value);channels=JSON.parse($("channels").value);
    if (!overrides || Array.isArray(overrides) || typeof overrides !== "object" || !Array.isArray(neighbors) || !Array.isArray(campaignNeighbors) || !Array.isArray(channels)) throw new Error();
  } catch (_) {showError("Overrides must be an object; neighbors and channels must be lists");return;}
  let preference, ballot;
  try {preference=parseList($("preference").value);if ($("ballot").value.trim()) ballot=parseList($("ballot").value);} catch (_) {showError("Preference and ballot must be ID lists");return;}
  let changes;
  try {
    changes=planAgentEdit(state.frames[cursor], selected, {preference,group:$("group").value,
      position:[Number($("x").value),Number($("y").value)],overrides,neighbors,campaignNeighbors,channels,ballot});
  } catch (error) {showError(error.message);return;}
  if (!Object.keys(changes).length) {showError("No changes to apply");return;}
  if (await command({action:"edit",round:cursor,person:selected,changes})) $("ballot").value="";
});
$("download").addEventListener("click", async () => {
  try {const data=await request("/checkpoint");const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const link=document.createElement("a");link.href=url;link.download="eclipse-checkpoint.json";link.click();URL.revokeObjectURL(url);}
  catch(error){showError(error.message);}
});
document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
request("/state").then(data=>{state=data;render();}).catch(error=>{$("status").textContent="Disconnected";showError(error.message);});
