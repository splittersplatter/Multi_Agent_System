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
  public_edge_count: 0, intervention_count: round === 1 ? 1 : 0});
let serverState = {revision: 0, parties: ["A", "B"], group_names: ["g"], group_capabilities: {g: {}},
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
})().catch(error => {console.error(error); process.exitCode = 1;});
