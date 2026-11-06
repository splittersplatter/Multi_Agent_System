"use strict";
const token = document.querySelector('meta[name="session-token"]').content;
const $ = id => document.getElementById(id);
const ns = "http://www.w3.org/2000/svg";
const downloads = createDownloadManager($("ready-download"));
let state, cursor = 0, selected = null, playing = false, busy = false, timer = null;
const drafts = new WeakMap(), draftFields = ["preference", "ballot", "group", "overrides", "neighbors", "campaign-neighbors", "channels", "x", "y"];
let displayedDraft = null;

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
function showError(message) { $("notice").textContent = message; $("notice").dataset.kind = "error"; }
function showInfo(message) { $("notice").textContent = message; $("notice").dataset.kind = "info"; }
async function request(path, body) {
  const init = {headers: {"X-Session-Token": token}};
  if (body) { init.method = "POST"; init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function render(focusPerson = null) {
  if (displayedDraft) {
    let people = drafts.get(displayedDraft.frame);
    if (!people) {people = new Map(); drafts.set(displayedDraft.frame, people);}
    people.set(displayedDraft.person, Object.fromEntries(draftFields.map(id => [id, $(id).value])));
  }
  if (typeof focusPerson !== "string") focusPerson = null;
  if (focusPerson === null) focusPerson = document.activeElement?.getAttribute("data-agent-id");
  const frame = state.frames[cursor], row = state.metrics[cursor];
  $("round-label").textContent = `Round ${frame.round}`;
  $("status").textContent = `Revision ${state.revision} · ${state.frames.length} frames`;
  $("active-voting").textContent = Object.entries(state.startup_voting || {}).map(([group, value]) => `${group}: ${value.policy}`).join(" · ");
  const selector = $("startup-policy");
  if (!selector.dataset.populated) {
    for (const policy of state.voting_policies || []) if (!policy.startsWith("python:")) option(selector, policy, policy);
    selector.dataset.populated = "true";
  }
  $("timeline").max = state.frames.length - 1; $("timeline").value = cursor;
  const ids = Object.keys(frame.positions);
  if (!ids.includes(selected)) selected = ids[0];
  const mode = $("color-mode").value;
  const estimates = mode === "estimate" ? estimatedPreferences(frame, selected) : null;
  $("color-label").textContent = mode === "estimate" ? `Agent ${selected} · vote-based preference proxy, not knowledge · gray: unknown or conflicting` : mode === "ballot" ? "Researcher view · node color: submitted vote" : "Researcher view · node color: true first preference";
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
    if (visible) for (const [a,b] of values) {
      const key=JSON.stringify([a,b].sort());
      if (!edges.has(key)) edges.set(key, []);
      edges.get(key).push({a,b,layer});
    }
  }
  for (const [raw, layers] of edges) {
    const [first,second] = JSON.parse(raw);
    if (filter.value && (frame.groups[first] !== filter.value || frame.groups[second] !== filter.value)) continue;
    const [ax,ay]=point(first), [bx,by]=point(second), length=Math.hypot(bx-ax,by-ay);
    const nx=length ? -(by-ay)/length : 0, ny=length ? (bx-ax)/length : 1;
    for (const [index,{a,b,layer}] of layers.entries()) {
      const [x1,y1]=point(a), [x2,y2]=point(b), offset=(index-(layers.length-1)/2)*6;
      const trim=length ? Math.min(11,length/2)/length : 0, ox=nx*offset, oy=ny*offset;
      const line=svg("line", {x1:x1+ox,y1:y1+oy,x2:x2-(x2-x1)*trim+ox,y2:y2-(y2-y1)*trim+oy,"marker-end":`url(#arrow-${layer})`,"data-layer":layer,"data-from":a,"data-to":b});
      line.style.stroke=layerColors[layer];node.append(line);
    }
  }
  let focusTarget = null;
  for (const id of ids) {
    if (filter.value && frame.groups[id] !== filter.value) continue;
    const [cx,cy] = point(id);
    const visibleParty = mode === "estimate" ? estimates.get(id) : mode === "ballot" ? frame.ballots[id][0] : frame.preferences[id][0];
    const circle = svg("circle", {cx,cy,r:9,fill:visibleParty === undefined ? "#8a9694" : color(visibleParty),class:id === selected ? "selected" : "",tabindex:0,role:"button","data-agent-id":id,"aria-label":`Select agent ${id}`});
    circle.style.stroke = id === selected ? "#152e38" : groupColor(frame.groups[id]);
    circle.style.strokeWidth = id === selected ? "4" : "2";
    circle.addEventListener("click", () => {selected = id; render();});
    circle.addEventListener("keydown", e => {if (e.key === "Enter" || e.key === " ") {e.preventDefault(); selected = id; render(id);}});
    node.append(circle);
    if (id === focusPerson) focusTarget = circle;
  }
  const legend = $("legend"); legend.replaceChildren();
  for (const party of state.parties) { const el = document.createElement("span"); el.style.setProperty("--color", color(party)); el.textContent = party; legend.append(el); }
  if (mode === "estimate") {const el=document.createElement("span");el.style.setProperty("--color", "#8a9694");el.textContent="Unknown / conflicting";legend.append(el);}
  const groupLegend=$("group-legend");groupLegend.replaceChildren();
  for(const name of state.group_names){const el=document.createElement("span");el.style.setProperty("--color",groupColor(name));el.textContent=`Group: ${name}`;groupLegend.append(el);}
  const chart = $("chart"); chart.replaceChildren();
  const firstRound=state.metrics[0].round, lastRound=state.metrics.at(-1).round;
  const chartX=round => 42 + (round-firstRound)*268/Math.max(1,lastRound-firstRound);
  const chartY=share => 125-share*110;
  const label=(text,attrs) => {const el=svg("text",attrs);el.textContent=text;chart.append(el);};
  for (const value of [0,0.5,1]) {
    const y=chartY(value);
    chart.append(svg("line",{x1:42,x2:310,y1:y,y2:y,stroke:"#dce7e3"}));
    label(`${value*100}%`,{x:36,y:y+4,"text-anchor":"end",class:"chart-label"});
  }
  label(String(firstRound),{x:42,y:140,"text-anchor":"middle",class:"chart-label"});
  if(lastRound!==firstRound) label(String(lastRound),{x:310,y:140,"text-anchor":"middle",class:"chart-label"});
  label("Round",{x:176,y:155,"text-anchor":"middle",class:"chart-label"});
  for (const party of state.parties) {
    const points = state.metrics.map(m => `${chartX(m.round)},${chartY(m.shares[party])}`).join(" ");
    chart.append(svg("polyline", {points,fill:"none",stroke:color(party),"stroke-width":2.5,"data-party":party}));
    if(state.metrics.length===1) chart.append(svg("circle",{cx:chartX(firstRound),cy:chartY(state.metrics[0].shares[party]),r:3,fill:color(party),"data-party-point":party}));
  }
  for(const metric of state.metrics) if(metric.intervention_count){const x=chartX(metric.round);chart.append(svg("line",{x1:x,x2:x,y1:15,y2:125,stroke:"#99543e","stroke-dasharray":"4 4","data-intervention-round":metric.round}));}
  const currentX=chartX(frame.round);
  chart.append(svg("line", {x1:currentX,x2:currentX,y1:15,y2:125,stroke:"#637c73","stroke-dasharray":"3 3","data-current-round":frame.round}));
  $("stats").textContent = `Winner: ${row.winner}  ·  Margin: ${row.winner_margin}  ·  Public links: ${row.public_edge_count}`;
  $("round-metrics").textContent = JSON.stringify(row, null, 2);
  $("details").textContent = `Ballot: ${frame.ballots[selected].join(" › ")} · Group: ${frame.groups[selected]} · Position: ${frame.positions[selected].map(v => v.toFixed(3)).join(", ")}`;
  $("capabilities").textContent = JSON.stringify({...state.group_capabilities[frame.groups[selected]], ...frame.overrides[selected].capabilities}, null, 2);
  $("ballot-sensors").textContent = JSON.stringify(frame.ballot_sensors.filter(entry => entry[0] === selected).map(([,sender,source,round,ballot]) => ({sender,source,round,ballot})), null, 2);
  $("agent-inspector").textContent = JSON.stringify(inspectAgent(frame, selected), null, 2);
  const defaults = {preference:JSON.stringify(frame.preferences[selected]),ballot:"",group:frame.groups[selected],
    overrides:JSON.stringify(frame.overrides[selected]),neighbors:JSON.stringify(frame.persistent_edges.filter(e=>e[0]===selected).map(e=>e[1])),
    "campaign-neighbors":JSON.stringify(frame.campaign_edges.filter(e=>e[0]===selected).map(e=>e[1])),
    channels:JSON.stringify(Object.keys(frame.private_channels).filter(name=>frame.private_channels[name].includes(selected))),
    x:frame.positions[selected][0],y:frame.positions[selected][1]};
  const draft = drafts.get(frame)?.get(selected) ?? defaults;
  for (const id of draftFields) $(id).value = draft[id];
  displayedDraft = {frame, person:selected};
  if (focusTarget) focusTarget.focus();
}
async function command(payload) {
  if (busy) {showError("A step is still completing; try again when paused.");return false;}
  busy = true;syncControls();
  try {
    const result = await request("/command", {...payload, revision:state.revision});
    if (result.frame) {state.revision=result.revision;state.frames.push(result.frame);state.metrics.push(result.metric);}
    else state=result;
    cursor = state.frames.length-1; render(); showError("");return true;
  }
  catch (error) { pause(); showError(error.message); try {const refreshed=await request("/state");if(refreshed.revision===state.revision)refreshed.frames=state.frames;state=refreshed; cursor=Math.min(cursor,state.frames.length-1);render();} catch (_) {} return false; }
  finally {busy=false;syncControls();}
}
async function next() {
  if (cursor < state.frames.length-1) {cursor++;render();}
  else await command({action:"step"});
}
function setEditingDisabled(disabled) {for (const input of $("edit").querySelectorAll("input,select,button")) input.disabled=disabled;}
function syncControls() {
  const unavailable=!state;
  for (const id of ["previous", "next", "timeline", "download", "export"]) $(id).disabled=unavailable || busy;
  $("play").disabled=unavailable || (busy && !playing);
  $("play").textContent=playing ? "Pause" : busy ? "Pausing…" : "Play";
  setEditingDisabled(unavailable || playing || busy);
  for (const id of ["startup-policy", "startup-parameters", "apply-voting"])
    $(id).disabled = unavailable || playing || busy || state.startup_voting_locked || state.frames.at(-1).round !== 0;
}
function pause() {playing=false;clearTimeout(timer);syncControls();}
$("startup-policy").addEventListener("change", () => {
  const baseline = ["", "sincere", "local_plurality", "sensed_plurality"].includes($("startup-policy").value);
  $("startup-parameters").value = baseline ? "{}" : JSON.stringify({utility_mode:"rank",top_k:2,samples:200,uncertainty_radius:2,max_states:200000,poll:"initial_truthful",information_source:"native"});
});
$("voting-setup").addEventListener("submit", async event => {
  event.preventDefault();
  if (!$("startup-policy").value) {showInfo("Keeping scenario voting policies.");return;}
  let parameters;
  try {parameters=JSON.parse($("startup-parameters").value);} catch (_) {showError("Voting parameters must be valid JSON.");return;}
  if (await command({action:"configure_voting",policy:$("startup-policy").value,parameters}))
    showInfo("Voting choice applied to all agents; movement and permissions preserved.");
});
async function tick() {if (!playing) return;await next();if (playing) timer=setTimeout(tick,Number($("speed").value));}
$("play").addEventListener("click", () => {if (playing) pause();else if (!busy && state) {playing=true;syncControls();tick();}});
$("previous").addEventListener("click", () => {if(busy || !state)return;pause();cursor=Math.max(0,cursor-1);render();});
$("next").addEventListener("click", () => {if(busy || !state)return;pause();next();});
$("timeline").addEventListener("input", e => {if(busy || !state)return;pause();cursor=Number(e.target.value);render();});
$("person").addEventListener("change", e => {selected=e.target.value;render();});
for (const id of ["color-mode", "group-filter", "show-persistent", "show-proximity", "show-campaign"]) $(id).addEventListener("change", render);
$("edit").addEventListener("submit", async e => {
  e.preventDefault();if (busy || !state) {pause();showError("A step is still completing; try again when paused.");return;} pause();
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
  pause();if (busy) {showError("A step is still completing; try again when paused.");return;}
  const revision=state.revision;
  try {const data=await request(`/checkpoint?revision=${revision}`);downloads.download(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}),"eclipse-checkpoint.json",`revision ${revision}`);showInfo("Checkpoint download requested. Use the save link if needed.");}
  catch(error){showError(error.message);}
});
$("export").addEventListener("click", async () => {
  pause();if (busy) {showError("A step is still completing; try again when paused.");return;}
  const kind=$("export-format").value, revision=state.revision, frame=cursor, round=state.frames[cursor].round;
  const names={"csv":"eclipse-metrics.csv","plot-svg":"eclipse-shares.svg","plot-png":"eclipse-shares.png","network-png":"eclipse-network.png","gif":"eclipse-evolution.gif"};
  try {
    const query=new URLSearchParams({format:kind,revision:String(revision),frame:String(frame)});
    const response=await fetch(`/export?${query}`,{headers:{"X-Session-Token":token}});
    if(!response.ok){const data=await response.json();throw new Error(data.error || `Export failed (${response.status})`);}
    downloads.download(await response.blob(),names[kind],`revision ${revision}, displayed round ${round}`);showInfo(`Download requested: ${names[kind]}. Use the save link if needed.`);
  } catch(error) {showError(error.message);}
});
document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
syncControls();
request("/state").then(data=>{state=data;render();syncControls();}).catch(error=>{$("status").textContent="Disconnected";showError(error.message);syncControls();});
