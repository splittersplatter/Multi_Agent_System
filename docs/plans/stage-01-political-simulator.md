# 01: Political agentic simulator

In progress; inherits verified 00. [Gates](README.md).
Shared Python engine: CLI/browser/replay/exports.

## Model contracts

- Person: stable ID, primary group, position, private full ranking, submitted ballot,
  policies/parameters, abilities, serializable policy memory; overlapping private channels.
- Group counts sum to population; per-agent overrides > group defaults.
  Group identity != party support. Controllers/inspectors add no extra votes.
- Parties: stable IDs, labels/colors, deterministic tie order.
- Ballot: exactly global `k` distinct eligible parties; `1 <= k <= |C|`.
  Private full ranking separate. Proposed counting: first-choice plurality;
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
- Optional stack: FastAPI/Uvicorn, REST commands + WebSocket frames;
  local JS Canvas network + SVG stats; Matplotlib/Pillow offline plots/GIFs.
  Core CLI works without UI/render extras.

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
- [ ] **1D:** party counts/shares/rank frequencies, winner/margin, switching, group/network
  metrics; timestamped interventions; paired delta plots; PNG/SVG/GIF with legends.
- [ ] **1E:** local browser: network, timeline, agent inspector, live stats sidebar;
  play/pause/step/seek/previous/next/speed, group/layer filters, save/export.
- [ ] **1F:** edit paused agent position/ranking/valid ballot/group/channels/policies/
  supported abilities; rewind + replace future; headless replay of edits.
- [ ] **1G:** runnable quickstart, config/plugin/UI/history/export references, scenario examples, benchmark report.

## Replay / UI invariants

- Named RNG by root seed + stable actor/process/round keys; no randomized `hash()`.
- Checkpoint: config/state, RNG, memory, budgets, pending messages, metrics, edits;
  versioned schema; legacy migration only with available artifacts.
- Periodic snapshots + events/deltas; full frames acceptable initially.
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
- One worker + ordered commands; acknowledge pause at boundary; disconnect pauses.
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

Track 1A-1G evidence; cumulative CLI/browser/export demonstration required.

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 2026-11-05 | 1A verified; 1B/1C partial | `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 17 pass; baseline matches Stage 00; network brute-force, scoped delayed messages, scheduled edits, checkpoint replay/tamper checks | Same engine, CLI, baseline and moving groups | Full plugin interface, group overrides, graph edits, comprehensive recording/batch, plots/GIFs, browser and benchmarks pending |
| 2026-11-05 | Workspace recheck; Stage 01 still in progress | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v`: 40 pass; current tests cover plugins, recording, exports and browser-command parity | Retains Stage 00 oracle and existing Stage 01 tests | Full 1B–1G acceptance, cumulative demonstration and benchmarks not established by this check |
| 2026-11-05 | 1B/1C provenance hardening; still partial | Full suite: 47 pass; `PYTHONPATH=src python3 -S -m unittest discover -s tests`: 46 pass, 1 optional image test skipped; source changes, stale bytecode, package/threaded imports and failure cleanup tested | Existing four-phase policies, checkpoint replay, CLI/browser parity retained | Imported plugin dependencies/core loaded bytecode not proven by source hashes; restart after changes. 1B–1G acceptance and benchmarks remain |
| 2026-11-05 | Cumulative scenario + rewind fix; 1B–1G still open | Full suite: 49 pass; `python3 -S`: 48 pass, 1 optional-image skip. `tests/test_integration.py`: CLI/HTTP history, scheduled edit, replay, CSV/SVG/GIF endpoints; live browser confirmed preference-only rewind preserves scheduled position | [Integrated scenario](../../examples/integrated.toml): four policy phases, groups, overlapping graphs, private reports, scheduled ballot/movement | Browser checks are partial; full acceptance, capability/layer contracts, visual scale and CLI benchmark on current code remain |
| 2026-11-05 | Preliminary scale + directed export | Full suite: 53 pass; `python3 -S`: 51 pass, 2 image skips. [Benchmarks](../stage-01-benchmarks.md): 10k CLI/100 rounds 36.912 s; 500 HTTP/100 rounds p95 23.79 ms, 97,132 KiB; browser 500/124 rounds 34.213 s; network arrows regression | Existing integrated exports and replay pass; rendered network visibly labels direction and layers | One run/hardware, browser RSS unavailable; repeat, test costly policies, review provisional budgets; Stage 01 acceptance incomplete |
| 2026-11-05 | Group/agent capability registry; 1B still open | Full suite: 62 pass; `python3 -S`: 60 pass, 2 image skips; denied-action atomicity, scoped observations/revocation and legacy replay tested; live inspector edit verified | Default permissions preserve previous behavior; actual prior v7 checkpoint replay-migrated after explicit environment-change review | Plugins remain trusted code; any-channel joins allowed if enabled. Campaign/sensor layers, remaining Stage 01 acceptance and rebenchmark current core pending |
| 2026-11-05 | Opt-in trusted ballot sensors; 1B still open | Full suite: 71 pass; `python3 -S`: 69 pass, 2 image skips. [Sensor tests](../../tests/test_sensors.py): channel/direction, completed-round timing, phase order, no report fallback, duplicates, rewind and tamper. Live browser inspector + CSV verified | [Sensor example](../../examples/sensors.toml); v7 checkpoint replay-migrates to v8 after explicit environment review | Deceptive reports/campaign layer remain later stages; trusted plugins not sandboxed. Full 1B–1G acceptance and current-core benchmarks pending |
| 2026-11-05 | Sensor phase/replay + scale recheck | Full suite: 73 pass; `python3 -S`: 71 pass, 2 image skips. Movement uses prior recorded readings, not retroactive grants. Current-core [benchmarks](../stage-01-benchmarks.md): 10k CLI 36.801 s; 500 HTTP p95 23.88 ms without / 43.27 ms with sensors | Prior sensors, permissions, CLI, browser inspector and v7 migration retained | One sample; browser RSS and sensor-enabled browser scale unmeasured; remaining Stage 01 acceptance open |
| 2026-11-05 | Sensor CLI/browser parity | Full suite: 74 pass; HTTP frames, sensor traces and metrics match CLI on the sensor example | Extends cumulative CLI/browser parity without replacing earlier integration coverage | Browser RSS/scale and remaining Stage 01 acceptance open |
| 2026-11-05 | 1B verified: campaign overlay + cumulative layers | Full suite: 81 pass; `python3 -S`: 79 pass, 2 image skips. [Campaign tests](../../tests/test_campaign_layer.py): overlap deduplication, mobility, invalid/rewind edits, synthetic v8 replay; actual v7 replay after explicit environment review; live filters/edit; CLI/browser/export cumulative run | [Integrated example](../../examples/integrated.toml) combines four plugin phases, movement, all graph layers, private channels, sensors and scheduled/interactive edits | Baseline researcher-controlled overlay only; Stage 05 budgets, controller rules/strategy and Stage 04 deceptive reports remain unimplemented. Rebenchmark changed core; 1C–1G acceptance open |
| 2026-11-06 | 1C verified: recording, provenance and path safety | Full suite: 91 pass; `python3 -S`: 89 pass, 2 image skips. [Recording tests](../../tests/test_recording_contract.py): full/summary/sampled/JSONL parity, resumed integrated run, alias/symlink/collision failures, phase/actor RNG isolation, pipeline-hash migration; actual v7 replay reviewed | Retains 1A/1B scenarios, plugins, layers, sensors, checkpoints, batch, export and browser server | Preflight cannot eliminate I/O races; multi-file outputs not transactional. Plugin transitive dependencies and browser runtime not fully fingerprinted; rebenchmark current core. 1D–1G remain |
