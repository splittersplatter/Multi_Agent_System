"use strict";

// Execute the shipped browser script with a deliberately delayed network step.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const {inspectAgent, estimatedPreferences} = require("../src/multi_agent_election/web/inspector.js");
const {planAgentEdit} = require("../src/multi_agent_election/web/edit.js");

class Element {
  constructor(id = "") {
    this.id = id; this.handlers = {}; this.style = {setProperty() {}}; this.dataset = {};
    this.value = ""; this.textContent = ""; this.disabled = false; this.checked = true; this.children = []; this.attributes = {};
  }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name] ?? null; }
  focus() { document.activeElement = this; }
  querySelectorAll() { return this.id === "edit" ? [editorInput] : []; }
}
const editorInput = new Element();
const elements = new Map();
function element(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); }
element("color-mode").value = "preference";
element("speed").value = "200";
const document = {
  hidden: false,
  querySelector() { return {content: "test-token"}; },
  getElementById: element,
  createElement() { return new Element(); },
  createElementNS() { return new Element(); },
  addEventListener() {},
};
const frame = round => ({round, positions: {p: [0.2, 0.3], q: [0.8, 0.3]}, groups: {p: "g", q: "g"}, preferences: {p: ["A", "B"], q: ["A", "B"]},
  ballots: {p: ["A"], q: ["A"]}, overrides: {p: {}, q: {}}, persistent_edges: [["p","q"]], proximity_edges: [["p","q"],["q","p"]], campaign_edges: [["p","q"]],
  private_channels: {}, ballot_sensors: [], delivered: [], pending: [], policy_memory: {p: null, q: null}, phase_memory: [], interventions: []});
const metric = round => ({round, shares: {A: 1, B: 0}, winner: "A", winner_margin: 1,
  public_edge_count: 0, proximity_edge_count: round + 2,
  proximity_edge_turnover: round === 0 ? null : round === 1 ? 0.5 : 0,
  intervention_count: round === 1 ? 1 : 0});
let serverState = {revision: 0, parties: ["A", "B"], group_names: ["g"], group_capabilities: {g: {}},
  proximity_radius: 0.4, group_proximity_radii: {g: 0.25},
  frames: [frame(0)], metrics: [metric(0)]};
let resolveStep, rejectStep, stepCalls = 0, timers = 0, delays = [], requests = [];
let checkpointAccepted = false, checkpointHold = false, resolveCheckpoint, checkpointRequests = [], downloads = [];
const response = data => ({ok: true, json: async () => data});
const fetch = (path, init) => {
  if (path === "/state") return Promise.resolve(response(serverState));
  if (path.startsWith("/checkpoint?")) {
    checkpointRequests.push({path, token: init.headers["X-Session-Token"]});
    if (checkpointHold) return new Promise(resolve => { resolveCheckpoint = resolve; });
    return Promise.resolve(checkpointAccepted ? response({revision_data: 3}) :
      {ok: false, json: async () => ({error: "stale revision; reload current state"})});
  }
  if (path === "/command") {
    stepCalls++;
    requests.push(JSON.parse(init.body));
    return new Promise((resolve, reject) => { resolveStep = resolve; rejectStep = reject; });
  }
  throw new Error(`unexpected request ${path}`);
};
const sandbox = {document, fetch, console, URLSearchParams, Blob, inspectAgent, estimatedPreferences, planAgentEdit,
  createDownloadManager() { return {download(blob, filename, description) { downloads.push({blob, filename, description}); }}; },
  setTimeout(callback, delay) { timers++; delays.push(delay); return timers; }, clearTimeout() {}};
vm.runInNewContext(fs.readFileSync("src/multi_agent_election/web/app.js", "utf8"), sandbox);
const flush = () => new Promise(resolve => setImmediate(resolve));

(async () => {
  await flush();
  assert.equal(element("play").disabled, false);
  assert.equal(element("campaign-spend-wrap").hidden, true);
  assert.equal(element("startup-policy").disabled, false);
  element("startup-policy").value="top_k";
  element("startup-policy").handlers.change({});
  assert.equal(JSON.parse(element("startup-parameters").value).top_k,2);
  element("startup-parameters").value="{";
  await element("voting-setup").handlers.submit({preventDefault(){}});
  assert.match(element("notice").textContent,/valid JSON/);
  assert.equal(stepCalls,0);
  const chartItems = () => element("chart").children;
  const chartItem = (attr, value) => chartItems().find(item => item.getAttribute(attr) === String(value));
  assert.deepEqual(chartItems().filter(item=>item.getAttribute("class") === "chart-label").map(item=>item.textContent),
    ["0%","50%","100%","0","Round"]);
  assert.equal(chartItem("data-party-point", "A").getAttribute("cy"), "15");
  assert.equal(chartItem("data-party-point", "B").getAttribute("cy"), "125");
  vm.runInNewContext('state.detector={target:"A",threshold:0.2}; state.metrics[0].detector_alert=true; state.metrics[0].detector_first_alert_round=0; state.metrics[0].detector_first_triple_win_round=null; render();', sandbox);
  assert.ok(chartItem("data-detector-alert", "0"));
  assert.match(element("detector-status").textContent, /not proof of attack/);
  vm.runInNewContext('state.detector=null; delete state.metrics[0].detector_alert; render();', sandbox);
  vm.runInNewContext('state.nomination = {mode:"fixed", nominees:["p"], ideals:{p:[0.2,0.8],q:[0.9,0.1]}}; render();', sandbox);
  assert.equal(element("nomination-view").hidden, false);
  assert.ok(element("network").children.some(item => item.getAttribute("data-leader-id") === "p"));
  assert.ok(element("issue-space").children.some(item => item.getAttribute("data-issue-leader") === "p"));
  assert.equal(element("issue-space").children.filter(item => item.getAttribute("data-issue-person") !== null).length, 2);
  vm.runInNewContext('state.alignment={attack:{total_budget:1}}; state.frames[0].alignment={ideals:{p:[0.6,0.7],q:[0.9,0.1]}}; state.metrics[0].alignment_attack_spend=0.2; render();', sandbox);
  assert.equal(element("alignment-spend-wrap").hidden, false);
  assert.equal(element("issue-space").children.find(item => item.getAttribute("data-issue-person") === "p").getAttribute("cx"), "192");
  assert.equal(element("issue-space").children.find(item => item.getAttribute("data-issue-leader") === "p").getAttribute("cx"), "84");
  vm.runInNewContext('state.alignment=null; delete state.frames[0].alignment; render();', sandbox);
  vm.runInNewContext('state.leaders={lifetime_budget:1,adaptors:["p"]}; state.frames[0].leaders={true:{A:[0.1,0.2],B:[0.8,0.3]},perceived:{A:[0.2,0.2],B:[0.7,0.3]}}; state.metrics[0].leader_total_spend=0; state.metrics[0].mean_leader_perception_error=0.1; render();', sandbox);
  assert.equal(element("leaders-view").hidden, false);
  assert.ok(element("issue-space").children.some(item => item.getAttribute("data-leader-true") === "A"));
  assert.ok(element("issue-space").children.some(item => item.getAttribute("data-leader-perceived") === "A"));
  vm.runInNewContext('state.leaders=null; delete state.frames[0].leaders; render();', sandbox);
  vm.runInNewContext('state.nomination = null; render();', sandbox);
  assert.equal(element("nomination-view").hidden, true);
  let radius = element("network").children.find(item => item.getAttribute("data-receiver-radius") !== null);
  assert.equal(radius.getAttribute("data-receiver-radius"), "0.25");
  assert.equal(radius.getAttribute("rx"), "130"); assert.equal(radius.getAttribute("ry"), "85");
  assert.match(element("details").textContent, /Receiver radius: 0.25/);
  element("show-radius").checked = false; element("show-radius").handlers.change({});
  assert.equal(element("network").children.some(item => item.getAttribute("data-receiver-radius") !== null), false);
  assert.equal(element("contact-chart").children.find(item => item.getAttribute("data-network-point") === "proximity_edge_count").getAttribute("cy"), "15");
  assert.ok(element("turnover-chart").children.some(item => item.textContent === "No consecutive frames"));
  // Drafts belong to one agent and one committed frame, even across redraws.
  element("preference").value = '["B","A"]'; element("ballot").value = '["B"]';
  element("overrides").value = '{"unfinished":'; element("x").value = "0.22";
  element("color-mode").handlers.change({});
  assert.equal(element("preference").value, '["B","A"]');
  assert.equal(element("ballot").value, '["B"]');
  assert.equal(element("overrides").value, '{"unfinished":');
  assert.equal(element("x").value, "0.22");
  let qNode = element("network").children.find(child => child.getAttribute("data-agent-id") === "q");
  qNode.handlers.keydown({key: "Enter", preventDefault() {}});
  assert.equal(element("ballot").value, "");
  assert.equal(element("preference").value, '["A","B"]');
  assert.equal(element("overrides").value, '{}');
  element("ballot").value = '["A"]';
  let pNode = element("network").children.find(child => child.getAttribute("data-agent-id") === "p");
  pNode.handlers.keydown({key: "Enter", preventDefault() {}});
  assert.equal(element("ballot").value, '["B"]');
  assert.equal(element("preference").value, '["B","A"]');
  assert.equal(element("overrides").value, '{"unfinished":');
  const renderedEdges = () => element("network").children.filter(child => child.getAttribute("data-layer"));
  let lines=renderedEdges();
  assert.deepEqual(lines.map(line=>[line.getAttribute("data-layer"),line.getAttribute("data-from"),line.getAttribute("data-to")]),
    [["proximity","p","q"],["proximity","q","p"],["persistent","p","q"],["campaign","p","q"]]);
  assert.equal(new Set(lines.map(line=>line.getAttribute("y1"))).size,4);
  element("show-proximity").checked=false; element("show-proximity").handlers.change({});
  lines=renderedEdges();
  assert.deepEqual(lines.map(line=>line.getAttribute("data-layer")),["persistent","campaign"]);
  assert.notEqual(lines[0].getAttribute("y1"),lines[1].getAttribute("y1"));
  element("show-proximity").checked=true; element("show-proximity").handlers.change({});
  element("play").handlers.click();
  assert.equal(stepCalls, 1);
  assert.equal(element("play").textContent, "Pause");
  assert.equal(element("next").disabled, true);
  assert.equal(element("previous").disabled, true);
  assert.equal(element("timeline").disabled, true);
  assert.equal(editorInput.disabled, true);
  const initialNode = element("network").children.find(child => child.getAttribute("data-agent-id") === "p");
  initialNode.handlers.keydown({key: "Enter", preventDefault() {}});
  assert.equal(document.activeElement.getAttribute("aria-label"), "Select agent p");
  const focusedNode = document.activeElement;
  element("play").handlers.click();
  assert.equal(element("play").textContent, "Pausing…");
  assert.equal(element("play").disabled, true);
  element("previous").handlers.click();
  assert.equal(element("round-label").textContent, "Round 0");
  serverState = {...serverState, revision: 1, frames: [frame(0), frame(1)], metrics: [metric(0), metric(1)]};
  resolveStep(response({revision: 1, frame: frame(1), metric: metric(1)}));
  await flush(); await flush();
  assert.equal(element("round-label").textContent, "Round 1");
  assert.equal(element("startup-policy").disabled, true);
  assert.equal(element("ballot").value, "");
  assert.equal(element("preference").value, '["A","B"]');
  assert.equal(chartItem("data-party", "A").getAttribute("points"), "42,15 310,15");
  assert.equal(chartItem("data-party", "B").getAttribute("points"), "42,125 310,125");
  assert.equal(chartItem("data-intervention-round", "1").getAttribute("x1"), "310");
  assert.equal(chartItem("data-current-round", "1").getAttribute("x1"), "310");
  assert.equal(element("contact-chart").children.find(item => item.getAttribute("data-network-series") === "proximity_edge_count").getAttribute("points"), "42,41.666666666666664 310,15");
  assert.equal(element("turnover-chart").children.find(item => item.getAttribute("data-network-point") === "proximity_edge_turnover").getAttribute("cy"), "55");
  assert.equal(element("turnover-chart").children.find(item => item.getAttribute("data-current-round") === "1").getAttribute("x1"), "310");
  assert.notEqual(document.activeElement, focusedNode);
  assert.equal(document.activeElement.getAttribute("aria-label"), "Select agent p");
  assert.equal(element("play").textContent, "Play");
  assert.equal(element("play").disabled, false);
  assert.equal(element("previous").disabled, false);
  assert.equal(editorInput.disabled, false);
  assert.equal(timers, 0);
  element("previous").handlers.click();
  assert.equal(element("round-label").textContent, "Round 0");
  assert.equal(element("startup-policy").disabled, true); // rewind is not a new episode
  assert.equal(element("ballot").value, '["B"]');
  assert.equal(element("preference").value, '["B","A"]');
  assert.equal(chartItem("data-current-round", "0").getAttribute("x1"), "42");
  assert.equal(chartItem("data-intervention-round", "1").getAttribute("x1"), "310");
  element("next").handlers.click();
  assert.equal(element("round-label").textContent, "Round 1");
  assert.equal(stepCalls, 1);
  element("play").handlers.click();
  rejectStep(new Error("network disconnected"));
  await flush(); await flush();
  assert.equal(element("play").textContent, "Play");
  assert.match(element("notice").textContent, /network disconnected/);
  assert.equal(timers, 0);
  for (const [round, speed] of [[2, 500], [3, 200]]) {
    element("speed").value = String(speed);
    element("play").handlers.click();
    const request = requests.at(-1);
    assert.equal(request.action, "step");
    assert.equal(request.revision, round - 1);
    assert.deepEqual(Object.keys(request).sort(), ["action", "revision"]);
    serverState = {...serverState, revision: round,
      frames: [...serverState.frames, frame(round)], metrics: [...serverState.metrics, metric(round)]};
    resolveStep(response({revision: round, frame: frame(round), metric: metric(round)}));
    await flush(); await flush();
    assert.equal(delays.at(-1), speed);
    assert.equal(element("round-label").textContent, `Round ${round}`);
    element("play").handlers.click();
    assert.equal(element("play").textContent, "Play");
  }
  await element("download").handlers.click();
  assert.deepEqual(checkpointRequests.at(-1), {path: "/checkpoint?revision=3", token: "test-token"});
  assert.match(element("notice").textContent, /stale revision/);
  assert.equal(downloads.length, 0);
  checkpointAccepted = true;
  await element("download").handlers.click();
  assert.equal(downloads.length, 1);
  assert.equal(downloads[0].filename, "eclipse-checkpoint.json");
  assert.equal(downloads[0].description, "revision 3");
  assert.deepEqual(JSON.parse(await downloads[0].blob.text()), {revision_data: 3});
  checkpointHold = true;
  const pendingCheckpoint = element("download").handlers.click();
  element("next").handlers.click();
  serverState = {...serverState, revision: 4,
    frames: [...serverState.frames, frame(4)], metrics: [...serverState.metrics, metric(4)]};
  resolveStep(response({revision: 4, frame: frame(4), metric: metric(4)}));
  await flush(); await flush();
  resolveCheckpoint(response({revision_data: 3}));
  await pendingCheckpoint;
  assert.equal(element("round-label").textContent, "Round 4");
  assert.equal(downloads.at(-1).description, "revision 3");
  assert.deepEqual(JSON.parse(await downloads.at(-1).blob.text()), {revision_data: 3});
  element("ballot").value = '["B"]';
  let pendingEdit = element("edit").handlers.submit({preventDefault() {}});
  assert.deepEqual(requests.at(-1), {action:"edit", revision:4, round:4, person:"p", changes:{ballot:["B"]}});
  rejectStep(new Error("invalid action"));
  await pendingEdit;
  assert.match(element("notice").textContent, /invalid action/);
  assert.equal(element("ballot").value, '["B"]'); // recoverable failure keeps draft
  pendingEdit = element("edit").handlers.submit({preventDefault() {}});
  serverState = {...serverState, revision:5, frames:JSON.parse(JSON.stringify(serverState.frames))};
  resolveStep(response(serverState));
  await pendingEdit;
  assert.equal(element("ballot").value, ""); // successful edit invalidates old drafts
  element("previous").handlers.click();
  element("previous").handlers.click();
  element("previous").handlers.click();
  element("previous").handlers.click();
  assert.equal(element("round-label").textContent, "Round 0");
  assert.equal(element("ballot").value, "");
  assert.equal(element("preference").value, '["A","B"]');
  element("show-radius").checked = true;
  vm.runInNewContext('state.frames[0].overrides.p.proximity_radius = 0; render();', sandbox);
  radius = element("network").children.find(item => item.getAttribute("data-receiver-radius") !== null);
  assert.equal(radius.getAttribute("data-receiver-radius"), "0");
  assert.match(element("details").textContent, /Receiver radius: 0/);
  vm.runInNewContext('state.proximity_mode = "frozen"; state.frames[0].overrides.p.proximity_radius = 0.2; state.frames[1].positions.p = [0.8,0.8]; state.frames[1].overrides.p.proximity_radius = 0.9; cursor = 1; render();', sandbox);
  radius = element("network").children.find(item => item.getAttribute("data-receiver-radius") !== null);
  assert.equal(radius.getAttribute("data-receiver-radius"), "0.2");
  assert.equal(radius.getAttribute("cx"), "144");
  assert.match(element("details").textContent, /Frozen initial receiver radius: 0.2/);
  vm.runInNewContext('state.proximity_mode = "static"; render();', sandbox);
  assert.equal(element("network").children.some(item => item.getAttribute("data-receiver-radius") !== null), false);
  assert.match(element("details").textContent, /Explicit static proximity graph \(no radius\)/);
  vm.runInNewContext(`state.coalitions = [{id:"c",members:["p"],target:"B",report_budget_per_round:1,report_budget_total:2}];
    state.frames[1].coalition_report_spend = {c:1};
    state.frames[1].deceptive_reports = [{coalition:"c",sender:"p",recipient:"q",channel:"public",ballot:["B"]}]; render();`, sandbox);
  assert.equal(JSON.parse(element("coalition-status").textContent).spent_total, 1);
  assert.equal(JSON.parse(element("coalition-status").textContent).spent_this_round, 1);
  assert.equal(JSON.parse(element("agent-inspector").textContent).researcher_deceptive_reports.length, 1);
  vm.runInNewContext(`state.coalitions[0].sight_targets = ["q"]; state.coalitions[0].sight_budget_per_round = 1; state.coalitions[0].sight_budget_total = 3;
    state.frames[1].coalition_sight_spend = {c:2};
    state.frames[1].preference_sight = [{coalition:"c",observer:"p",target:"q",round:1,preference:["B","A"]}]; render();`, sandbox);
  assert.equal(JSON.parse(element("coalition-status").textContent).sight_spent_total, 2);
  assert.equal(JSON.parse(element("coalition-status").textContent).sight_spent_this_round, 1);
  assert.equal(JSON.parse(element("agent-inspector").textContent).researcher_preference_sight[0].target,"q");
  vm.runInNewContext(`state.coalitions[0].eavesdrop_channels = ["team"]; state.coalitions[0].eavesdrop_budget_per_round = 1; state.coalitions[0].eavesdrop_budget_total = 3;
    state.frames[1].coalition_eavesdrop_spend = {c:1};
    state.frames[1].overheard_reports = [{coalition:"c",observer:"p",sender:"q",recipient:"r",channel:"team",ballot:["B"]}]; render();`, sandbox);
  assert.equal(JSON.parse(element("coalition-status").textContent).eavesdrop_spent_total,1);
  assert.equal(JSON.parse(element("coalition-status").textContent).eavesdrop_spent_this_round,1);
  assert.equal(JSON.parse(element("agent-inspector").textContent).researcher_overheard_reports[0].sender,"q");
  vm.runInNewContext(`state.campaign_controller = {target:"B",policy:"target_heuristic",lifetime_budget:2,per_round_budget:1};
    state.frames[1].campaign_controller = {spent:1,purchased:[["p","q"]],eligible:[["p","q"]],proposed:[["p","q"]],accepted:[["p","q"]]};
    state.metrics[0].campaign_controller_spend=0; state.metrics[1].campaign_controller_spend=1; state.metrics[1].campaign_controller_added_count=1; render();`, sandbox);
  assert.equal(JSON.parse(element("controller-status").textContent).current.spent,1);
  assert.deepEqual(JSON.parse(element("agent-inspector").textContent).researcher_campaign_edges,[["p","q"]]);
  assert.equal(element("campaign-spend-wrap").hidden,false);
  assert.ok(element("campaign-spend-chart").children.some(item => item.getAttribute("data-campaign-addition") === "1"));
  assert.ok(element("campaign-spend-chart").children.some(item => item.textContent === "2"));
  vm.runInNewContext(`state.signal_controller = {target:"B",policy:"target_biased",schedule:"repeated",per_broadcast_budget:1,lifetime_budget:2};
    state.frames[1].public_signal = {spend:1,broadcast_cost:1,latest:{source_round:0,broadcast_round:1,report:[0,2],source_truth:[1,1]}};
    state.metrics[0].signal_target_truth=null;state.metrics[0].signal_target_report=null;
    state.metrics[1].signal_target_truth=1;state.metrics[1].signal_target_report=2;render();`, sandbox);
  assert.equal(element("signal-charts").hidden,false);
  assert.equal(JSON.parse(element("signal-status").textContent).current.latest.report[1],2);
  assert.equal(element("signal-truth-chart").children.find(item=>item.getAttribute("data-network-point")==="signal_target_truth").getAttribute("cy"),"55");
  assert.equal(element("signal-report-chart").children.find(item=>item.getAttribute("data-network-point")==="signal_target_report").getAttribute("cy"),"15");
  // Missing observations and absent rounds must not be joined by a misleading line.
  vm.runInNewContext(`state.metrics = [
    {round:0, proximity_edge_turnover:null}, {round:1, proximity_edge_turnover:0.5},
    {round:3, proximity_edge_turnover:0.25}, {round:4, proximity_edge_turnover:0},
    {round:5, proximity_edge_turnover:null}, {round:6, proximity_edge_turnover:1}
  ]; drawNetworkSeries("turnover-chart", "proximity_edge_turnover", 1, 4);`, sandbox);
  const networkItems = element("turnover-chart").children;
  assert.equal(networkItems.filter(item => item.getAttribute("data-network-series") === "proximity_edge_turnover").length, 1);
  assert.equal(networkItems.filter(item => item.getAttribute("data-network-point") === "proximity_edge_turnover").length, 2);
  assert.equal(networkItems.find(item => item.getAttribute("data-current-round") === "4").getAttribute("x1"), String(42 + 4*268/6));
})().catch(error => {console.error(error); process.exitCode = 1;});
