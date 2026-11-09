# 01: Political agentic simulator

In progress; inherits verified 00. [Gates](README.md).
Shared Python engine: CLI/browser/replay/exports.

## Model contracts

- Outcome simulations/browser demos/benchmarks: N>=100; default demo200.
  Shared-engine guard; tiny unit/proof fixtures require explicit verification scope.
- Person: stable ID, primary group, position, private full ranking, submitted ballot,
  policies/parameters, abilities, serializable policy memory; overlapping private channels.
- Group counts sum to population; per-agent overrides > group defaults.
  Group identity != party support. Controllers/inspectors add no extra votes.
- Parties: stable IDs, labels/colors, deterministic tie order.
- Ballot: exactly global `k` distinct eligible parties; `1 <= k <= |C|`.
  Private full ranking separate. Implemented counting: first-choice plurality;
  retain all ranks; counting-rule adapter. Change parties/`k`/rule only between episodes.
- Groups configure voting, movement, communication and graph actions independently.
  Capability registry: explicit observation/action permissions; reject unsupported abilities.
- Graph layers: persistent public, proximity public, campaign, private channels.
  Directed edges; symmetric contacts = two arcs; deduplicate public observations.
  Edge purpose/lifetime explicit; private traffic not public.
- Channel mode: trusted ballot sensor or possibly deceptive report. Default messages
  are reports; no automatic true-ballot fallback on report-only channels.
- Space default: `[0,1]^2`, reflective boundaries, bounded movement.
  View layout/panning separate from model movement.

## Interfaces / defaults

- TOML 1.0 scenario: seed/horizon, parties/`k`, groups, policies, layers,
  signals, scheduled edits, recording, metrics, exports.
- Policy: timestamped authorized observation + parameters + memory + owned RNG -> actions + serializable memory.
  Built-ins: sincere top-k, stationary/random walk, truthful report, no-op.
  Registered policies/local Python callable plugins; record plugin versions.
  Validate actions before commit; fail/pause with actor/round/phase/reason; no silent fallback.
- Step: state + boundary interventions -> next state/events/metrics; commit atomically.
- Modules: model, engine, observations, policies/validation, history, metrics,
  CLI, renderers, browser adapter. Exporters read history, never rerun strategies.
- Current stack: stdlib threaded HTTP/JSON; local JS Canvas/SVG;
  Pillow for PNG/GIF. No FastAPI/Uvicorn/WebSocket/Matplotlib dependency.

## Round phases

Round 0: initial state, graphs, top-k ballots.

1. Validate/apply boundary interventions.
2. Movement from prior observations; apply simultaneously; rebuild proximity.
3. Authorized graph/controller actions; stable conflict order.
4. Direct observations from completed ballots/current channels; deliver prior-round
   messages; enqueue reports for next round, not current voting.
5. Compute decisions from authorized observations; apply ballots simultaneously.
6. Count, metrics/detective hooks, commit frame/checkpoint.

Voter/leader shifts: phase 3; observations: phase 4.
No future-result leakage; frame = committed round.

## Deliverables, ordered and cumulative

- [x] **1A:** honest baseline + repeated engine, groups, ranked ballots, deterministic state and CLI.
- [x] **1B:** movement, graph layers, channels, policy hooks, scheduled interventions.
- [x] **1C:** `run/batch/resume/export/visual`; named RNG; versioned run manifests;
  JSON/JSONL history, CSV metrics; full/sampled/summary recording.
- [x] **1D:** party counts/shares/rank frequencies, winner/margin, switching, group/network
  metrics; timestamped interventions; paired delta plots; PNG/SVG/GIF with legends.
- [ ] **1E:** local browser: network, timeline, agent inspector, live stats sidebar;
  play/pause/step/seek/previous/next/speed, group/layer filters, save/export.
- [ ] **1F:** edit paused agent position/ranking/valid ballot/group/channels/policies/
  supported abilities; rewind + replace future; headless replay of edits.
- [ ] **1G:** runnable quickstart, config/plugin/UI/history/export references, scenario examples, benchmark report.
  Quickstart/reference refreshed; current performance/full manual acceptance still pending.

## Replay / UI invariants

- Named RNG by root seed + stable actor/process/round keys; no randomized `hash()`.
- Checkpoint: config/state, RNG, memory, budgets, pending messages, metrics, edits;
  versioned schema; legacy migration only with available artifacts.
- Current full frames + edits; periodic/delta optimization remains future work.
  Sampled/summary recording cannot supply unrecorded frames; GIF requires recorded frames.
- Stable party colors: default true first preference, labelled researcher view;
  toggles for submitted vote/observed preference; unknown stays unknown.
  Group outlines separate. UI truth never feeds policies.
- Rewind alone read-only. Edit at completed round `t`: restore state/RNG,
  log boundary edit for `t+1`, truncate future frames/edits/metrics.
  Retain messages generated <= t even if delivered later; discard future-generated ones.
  Regenerate configured future schedules; discard interactive future edits.
- Revision-tag commands/frames; reject stale revisions; invalidate derived caches.
  Keep saved exports with old revision; no automatic branches.
- Serialized commands under a session lock; acknowledge pause at boundary; disconnect pauses.
  Playback speed changes pacing/round count, not model parameters; throttle rendering separately.
- Event annotations != causal attribution; require matched controls.
  Missing metrics = unavailable, not zero.

## Acceptance / benchmarks

Ballot endpoints/duplicates/IDs; disconnected/overlapping graphs; radius equality;
persistent/proximity overlap; message timing; permissions; invalid/conflicting actions.
CLI/browser round equivalence; resume memory/messages; rewind at 0/mid-run;
future invalidation, stale-command races, speed invariance.
Check inspector/state equality, legends, sidebar/frame timestamps, GIF endpoints, keyboard controls.

Proposed workloads: 10k CLI / 500 visual agents x 100 rounds, 3 parties,
k=3, sparse mean degree ~12, simple policies. Measure hardware, wall time,
memory, throughput, UI latency; set budgets from measurements before completion.
Sparse adjacency/spatial grid/incremental counts; summary mode skips frame serialization.
No achieved scale guarantee; benchmark expensive policies separately.

Examples: static, two groups/mixed graphs, scheduled edit, matched control, rewind/edit/resume.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Engine/CLI/HTTP/history/export implemented. Tests: `test_integration.py`, `test_visual.py`,
`test_recording_contract.py`, `test_population.py`. Remaining: full manual UI/save
acceptance, current rendering/resource limits;1E–1G not complete.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
