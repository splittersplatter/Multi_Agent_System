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
function drawNetworkSeries(id, key, fixedMaximum, selectedRound, markerKey = null) {
  const chart = $(id); chart.replaceChildren();
  const rows = state.metrics, first = rows[0].round, last = rows.at(-1).round;
  const valid = rows.filter(row => typeof row[key] === "number" && Number.isFinite(row[key]));
  const maximum = fixedMaximum ?? valid.reduce((max, row) => Math.max(max, row[key]), 1);
  const x = round => 42 + (last === first ? 0 : (round-first)*268/(last-first));
  const y = value => 95 - value * 80 / maximum;
  const label = (value, attrs) => {const text=svg("text",attrs);text.textContent=value;chart.append(text);};
  chart.append(svg("line",{x1:42,x2:310,y1:95,y2:95,stroke:"#9fb3ac"}));
  label("0",{x:35,y:98,"text-anchor":"end",class:"chart-label"});
  label(key === "proximity_edge_turnover" ? "100%" : String(maximum),{x:35,y:18,"text-anchor":"end",class:"chart-label"});
  label(String(first),{x:42,y:110,"text-anchor":"middle",class:"chart-label"});
  if (last !== first) label(String(last),{x:310,y:110,"text-anchor":"middle",class:"chart-label"});
  if (markerKey) for (const row of rows) if (row[markerKey] > 0)
    chart.append(svg("line",{x1:x(row.round),x2:x(row.round),y1:15,y2:95,stroke:"#a66a37","stroke-dasharray":"3 3","data-campaign-addition":row.round}));
  let segment = [];
  const flush = () => {
    if (segment.length === 1) chart.append(svg("circle",{cx:x(segment[0].round),cy:y(segment[0][key]),r:3,fill:"#1f7254","data-network-point":key}));
    else if (segment.length > 1) chart.append(svg("polyline",{points:segment.map(row=>`${x(row.round)},${y(row[key])}`).join(" "),fill:"none",stroke:"#1f7254","stroke-width":2,"data-network-series":key}));
    segment = [];
  };
  for (const row of rows) {
    if (typeof row[key] === "number" && Number.isFinite(row[key])) {
      if (segment.length && row.round !== segment.at(-1).round + 1) flush();
      segment.push(row);
    } else flush();
  }
  flush();
  chart.append(svg("line",{x1:x(selectedRound),x2:x(selectedRound),y1:15,y2:95,stroke:"#637c73","stroke-dasharray":"3 3","data-current-round":selectedRound}));
  if (!valid.length) label("No consecutive frames",{x:176,y:57,"text-anchor":"middle",class:"chart-label"});
}
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
  $("convergence-status").textContent = row.convergence ? `Certified model · ${row.convergence.status.replaceAll("_", " ")} · ${row.convergence.improving_voters === null ? row.convergence.reason : `${row.convergence.improving_voters} voters can change`} · next: ${row.convergence.next_actor}` : "Exploratory run · quiet ballots do not certify future stability; contacts and poll information can change.";
  if (state.stochastic_stability) $("convergence-status").textContent = "Finite-grid occupation model · long-run frequency theorem assumes ideal IID motion; seeded replay is not that proof. No ballot-absorption or mixing-time guarantee.";
  if (state.convergence_case) $("voting-description").textContent = `Certified sequential voting: one voter updates per step using ${state.convergence_case === "certified_conformity" ? "current public neighbors" : "current public counts"}. Scheduled ballot or preference changes may apply in direct-response scenarios. Interactive edits and policy changes are unavailable during this episode.`;
  if (state.stochastic_stability) $("voting-description").textContent = "Simultaneous memory-pivotal; strict predicted-winner improvement, rolling contacts and ten-round truthful polls. Fixed proof domain: edits/policy changes disabled; timeline playback remains available.";
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
  const frozenProximity = state.proximity_mode === "frozen";
  const staticProximity = state.proximity_mode === "static";
  const radiusFrame = frozenProximity ? state.frames[0] : frame;
  const receiverRadius = staticProximity ? null : (radiusFrame.overrides[selected].proximity_radius ?? state.group_proximity_radii?.[radiusFrame.groups[selected]] ?? state.proximity_radius ?? null);
  if ($("show-radius").checked && receiverRadius !== null) {
    const [px,py] = radiusFrame.positions[selected], cx = 40 + px*520, cy = 380 - py*340;
    node.append(svg("ellipse", {cx,cy,rx:receiverRadius*520,ry:receiverRadius*340,fill:"none",stroke:"#1f7254","stroke-dasharray":"5 4","pointer-events":"none","data-receiver-radius":receiverRadius}));
  }
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
    if (state.nomination?.nominees.includes(id)) node.append(svg("circle", {cx,cy,r:14,fill:"none",class:"leader-marker","pointer-events":"none","data-leader-id":id}));
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
  $("nomination-view").hidden = !state.nomination;
  const issueSpace = $("issue-space"); issueSpace.replaceChildren();
  if (state.nomination) {
    issueSpace.append(svg("rect", {x:30,y:15,width:270,height:175,fill:"none",stroke:"#9fb3ac"}));
    for (const id of ids) {
      const initial = state.nomination.ideals[id], ideal = frame.alignment?.ideals[id] ?? initial;
      const cx = 30 + ideal[0]*270, cy = 190 - (ideal[1] ?? 0.5)*175;
      if (frame.alignment && cursor > 0) {
        const points = state.frames.slice(0,cursor+1).map(f => f.alignment?.ideals[id] ?? initial)
          .map(v => `${30 + v[0]*270},${190 - (v[1] ?? 0.5)*175}`).join(" ");
        issueSpace.append(svg("polyline", {points,fill:"none",stroke:color(frame.preferences[id][0]),"stroke-width":1,"data-issue-trace":id}));
      }
      if (state.nomination.nominees.includes(id)) issueSpace.append(svg("circle", {cx:30+initial[0]*270,cy:190-(initial[1]??0.5)*175,r:11,fill:"none",stroke:"#ae7d19","stroke-width":2,"data-issue-leader":id}));
      const point = svg("circle", {cx,cy,r:6,fill:color(frame.preferences[id][0]),"data-issue-person":id});
      const title = svg("title", {}); title.textContent = `${id}: ${ideal.join(", ")}`; point.append(title); issueSpace.append(point);
    }
    if (frame.leaders) for (const party of state.parties) {
      for (const [kind, vector] of [["true",frame.leaders.true[party]],["perceived",frame.leaders.perceived[party]]]) {
        const x=30+vector[0]*270,y=190-(vector[1]??0.5)*175;
        if (cursor > 0) {
          const history=state.frames.slice(0,cursor+1).map(f=>f.leaders[kind][party]);
          const points=history.map(v=>`${30+v[0]*270},${190-(v[1]??0.5)*175}`).join(" ");
          issueSpace.append(svg("polyline",{points,fill:"none",stroke:color(party),"stroke-width":2,
            "stroke-dasharray":kind === "true" ? "5 3" : "2 3","data-leader-trace":`${kind}:${party}`}));
        }
        const marker = kind === "true" ? svg("path", {d:`M ${x} ${y-7} L ${x+7} ${y} L ${x} ${y+7} L ${x-7} ${y} Z`,fill:color(party),"data-leader-true":party}) :
          svg("rect", {x:x-4,y:y-4,width:8,height:8,fill:"white",stroke:color(party),"stroke-width":2,"data-leader-perceived":party});
        const title=svg("title",{});title.textContent=`${party} ${kind}: ${vector.join(", ")}`;marker.append(title);issueSpace.append(marker);
      }
    }
  }
  $("nomination-status").textContent = JSON.stringify(state.nomination, null, 2);
  $("alignment-status").textContent = JSON.stringify(state.alignment ? {configuration:state.alignment, current:frame.alignment} : null, null, 2);
  $("alignment-spend-wrap").hidden = !state.alignment;
  if (state.alignment) drawNetworkSeries("alignment-spend-chart", "alignment_attack_spend", Math.max(1,state.alignment.attack.total_budget), frame.round);
  $("leaders-view").hidden = !state.leaders;
  $("leader-status").textContent = JSON.stringify(state.leaders ? {configuration:state.leaders, current:frame.leaders} : null, null, 2);
  if (state.leaders) {
    drawNetworkSeries("leader-spend-chart", "leader_total_spend", Math.max(1,state.leaders.lifetime_budget * state.leaders.adaptors.length), frame.round);
    drawNetworkSeries("leader-error-chart", "mean_leader_perception_error", Math.max(1,Math.sqrt(state.nomination.ideals[ids[0]].length)), frame.round);
  }
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
  for(const metric of state.metrics) if(metric.detector_alert){const x=chartX(metric.round);chart.append(svg("path",{d:`M ${x-5} 15 L ${x+5} 15 L ${x} 24 Z`,fill:"#b42335","data-detector-alert":metric.round}));}
  const currentX=chartX(frame.round);
  chart.append(svg("line", {x1:currentX,x2:currentX,y1:15,y2:125,stroke:"#637c73","stroke-dasharray":"3 3","data-current-round":frame.round}));
  drawNetworkSeries("contact-chart", "proximity_edge_count", null, frame.round);
  drawNetworkSeries("turnover-chart", "proximity_edge_turnover", 1, frame.round);
  $("campaign-spend-wrap").hidden = !state.campaign_controller;
  if (state.campaign_controller) drawNetworkSeries("campaign-spend-chart", "campaign_controller_spend", Math.max(1,state.campaign_controller.lifetime_budget), frame.round, "campaign_controller_added_count");
  $("signal-charts").hidden = !state.signal_controller;
  if (state.signal_controller) {
    const population = Object.keys(frame.ballots).length;
    drawNetworkSeries("signal-truth-chart", "signal_target_truth", Math.max(1,population), frame.round);
    drawNetworkSeries("signal-report-chart", "signal_target_report", Math.max(1,population), frame.round);
  }
  $("stats").textContent = `Winner: ${row.winner}  ·  Margin: ${row.winner_margin}  ·  Public links: ${row.public_edge_count}`;
  $("detector-status").textContent = state.detector ? `Aggregate detector (${state.detector.target}, threshold ${state.detector.threshold}): ${row.detector_alert ? "ALERT" : "no alert"}; first alert ${row.detector_first_alert_round ?? "none"}; first three-win endpoint ${row.detector_first_triple_win_round ?? "not observed"}. Red triangles mark alerts; they are not proof of attack.` : "";
  $("round-metrics").textContent = JSON.stringify(row, null, 2);
  $("controller-status").textContent = JSON.stringify(state.campaign_controller ? {configuration:state.campaign_controller, current:frame.campaign_controller} : null, null, 2);
  $("signal-status").textContent = JSON.stringify(state.signal_controller ? {configuration:state.signal_controller, current:frame.public_signal} : null, null, 2);
  $("details").textContent = `Ballot: ${frame.ballots[selected].join(" › ")} · Group: ${frame.groups[selected]} · Position: ${frame.positions[selected].map(v => v.toFixed(3)).join(", ")} · ${staticProximity ? "Explicit static proximity graph (no radius)" : `${frozenProximity ? "Frozen initial receiver radius" : "Receiver radius"}: ${receiverRadius === null ? "disabled" : receiverRadius}`}`;
  $("capabilities").textContent = JSON.stringify({...state.group_capabilities[frame.groups[selected]], ...frame.overrides[selected].capabilities}, null, 2);
  const coalition = (state.coalitions || []).find(item => item.members.includes(selected));
  $("coalition-status").textContent = JSON.stringify(coalition ? {...coalition,
    spent_total:frame.coalition_report_spend[coalition.id],
    spent_this_round:(frame.deceptive_reports || []).filter(event => event.coalition === coalition.id).length,
    ...(coalition.sight_targets ? {sight_spent_total:frame.coalition_sight_spend[coalition.id],
      sight_spent_this_round:(frame.preference_sight || []).filter(event => event.coalition === coalition.id).length} : {}),
    ...(coalition.eavesdrop_channels ? {eavesdrop_spent_total:frame.coalition_eavesdrop_spend[coalition.id],
      eavesdrop_spent_this_round:(frame.overheard_reports || []).filter(event => event.coalition === coalition.id).length} : {})} : null, null, 2);
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
  setEditingDisabled(unavailable || playing || busy || !!state?.convergence_case || !!state?.stochastic_stability);
  for (const id of ["startup-policy", "startup-parameters", "apply-voting"])
    $(id).disabled = unavailable || playing || busy || state.startup_voting_locked || state.frames.at(-1).round !== 0;
}
function pause() {playing=false;clearTimeout(timer);syncControls();}
$("startup-policy").addEventListener("change", () => {
  const baseline = ["", "sincere", "local_plurality", "sensed_plurality", "memory_pivotal"].includes($("startup-policy").value);
  const epistemic = $("startup-policy").value.startsWith("epistemic_");
  $("startup-parameters").value = baseline ? "{}" : epistemic ? JSON.stringify({max_worlds:10000}) : JSON.stringify({utility_mode:"rank",top_k:2,samples:200,uncertainty_radius:2,max_states:200000,poll:"initial_truthful",information_source:"native"});
});
$("voting-setup").addEventListener("submit", async event => {
  event.preventDefault();
  if (!$("startup-policy").value) {showInfo("Keeping scenario voting policies.");return;}
  let parameters;
  try {parameters=JSON.parse($("startup-parameters").value);} catch (_) {showError("Voting parameters must be valid JSON.");return;}
  if (await command({action:"configure_voting",policy:$("startup-policy").value,parameters}))
    showInfo("Voting choice applied to all agents; movement and permissions preserved.");
});
async function tick() {if (!playing) return;await next();if (["certified_equilibrium", "certified_policy_equilibrium"].includes(state?.metrics[cursor]?.convergence?.status)) pause();if (playing) timer=setTimeout(tick,Number($("speed").value));}
$("play").addEventListener("click", () => {if (playing) pause();else if (!busy && state) {playing=true;syncControls();tick();}});
$("previous").addEventListener("click", () => {if(busy || !state)return;pause();cursor=Math.max(0,cursor-1);render();});
$("next").addEventListener("click", () => {if(busy || !state)return;pause();next();});
$("timeline").addEventListener("input", e => {if(busy || !state)return;pause();cursor=Number(e.target.value);render();});
$("person").addEventListener("change", e => {selected=e.target.value;render();});
for (const id of ["color-mode", "group-filter", "show-persistent", "show-proximity", "show-campaign", "show-radius"]) $(id).addEventListener("change", render);
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
