# Simulator guide: Stage 01

Status: implementation/verification in progress; see [checkpoint](plans/stage-01-political-simulator.md).
Research simulation only; no claim of real election prediction.

## Setup and commands

Python >=3.11; core and browser use standard library. PNG/GIF exports require
`python3 -m pip install -r requirements-visualization.txt` (Pillow 12.1.1).
From project root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/network.toml
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/network.toml --summary
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/network.toml --sample 2 --jsonl /tmp/eclipse-trace.jsonl
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/network.toml --checkpoint /tmp/eclipse-run.json
PYTHONPATH=src python3 -m multi_agent_election.cli resume /tmp/eclipse-run.json --rounds 2
PYTHONPATH=src python3 -m multi_agent_election.cli export /tmp/eclipse-run.json --csv /tmp/eclipse.csv --plot-svg /tmp/eclipse.svg --network-png /tmp/network.png --gif /tmp/eclipse.gif
PYTHONPATH=src python3 -m multi_agent_election.cli batch examples/network.toml --seeds 1 2 3 --target A --csv /tmp/paired.csv --plot-svg /tmp/paired.svg
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/network.toml --port 8000
PYTHONPATH=src:examples python3 -m multi_agent_election.cli run examples/custom.toml
```

Output paths must not exist, including dangling symlinks; parents must exist and
multiple outputs must resolve to distinct paths. Preflight catches common
conflicts before writing; exclusive creation prevents overwrites. Multi-file
output is not transactional: an I/O failure or race can leave partial files.
`--summary` keeps metrics only
and cannot create a checkpoint; `--sample N` retains every Nth frame plus the
last, and can create a separate full checkpoint. Missing frames cannot be
exported from the sampled record alone. Batch compares configured interventions
against no intervention, paired by explicit seed; its plot is mean target-share
change, not a causal claim. Images show intervention markers and recorded state.
Run JSON and JSONL headers identify `eclipse.run` record version 1; batch JSON
identifies `eclipse.batch` version 1. JSONL contains a header followed by metric
and available frame records; it is not itself a resumable checkpoint.
Network arrows point sender to recipient; campaign links take visual precedence
over persistent links, which take precedence over overlapping proximity links.
Coincident nodes cannot show direction at image scale.

## Scenario

See [baseline](../examples/baseline.toml) and [network](../examples/network.toml).
The [integrated example](../examples/integrated.toml) combines all four policy
phases, directed/proximity/campaign links, a private channel, sensors and a scheduled edit; run it
with `PYTHONPATH=src:examples`.
`parties` defines tie order; `k` is one global ballot length. Each person has a
unique ID, group, full strict private `preference` and optional `[x,y]` position
and `overrides`. Bounds: positions in `[0,1]^2`; `1 <= k <= number of parties`.
Round 0 votes sincerely; first-choice plurality counts each length-k ballot.

Group fields: `voting` (`sincere`, `local_plurality`, `sensed_plurality`, or plugin), `movement`
(`stationary`, `random_walk`, or plugin), `max_step` (0..1), `communication`
(`none`, `truthful`, or plugin), `graph` (`none` or plugin), `parameters` (table).
Person overrides replace individual fields; `{}` restores group defaults.
`local_plurality` chooses the most-reported first choice, breaking ties by own
preference; no reports means sincere voting.

Each group accepts a `capabilities` table of boolean permissions:

```
observe_public_neighbors  observe_private_channels
sense_public_ballots      sense_private_ballots
receive_public_reports    receive_private_reports
send_public_reports       send_private_reports
modify_persistent_edges   modify_private_channels   move
```

Omitted sensor permissions default to `false`; other permissions default to
`true` for compatibility with existing scenarios;
restrict them explicitly, e.g. [restricted.toml](../examples/restricted.toml).
Person `overrides.capabilities` merges individual entries over group permissions.
The inspector shows effective permissions; edit them via the JSON overrides field.
Denied plugin actions fail the whole step; built-in truthful broadcasts use only
allowed destinations. Receive permissions are checked on delivery, including
queued messages after a boundary edit; denied messages are not delivered.
Revocation does not erase knowledge already stored in policy memory. Researcher
and scheduled interventions are external controls and do not use agent permissions.
With `modify_private_channels = true`, a graph plugin may join any configured
channel; disable it when membership must remain externally controlled.

`[network]`: optional proximity `radius`; directed `persistent_edges` and
`campaign_edges` as `[[sender,recipient],...]`; `private_channels = { name = [member_ids...] }`.
Persistent and campaign edges remain until explicitly removed; proximity links
are recomputed. Overlapping public edges are deduplicated; channels remain separate. Reports use prior
ballots and arrive next round. Configured `[[interventions]]` specify `round`,
`person` and supported fields `preference`, `position`, `group`, `overrides`,
`ballot`, `add_edges`, `remove_edges`, `add_campaign_edges`, `remove_campaign_edges`,
`add_channels`, `remove_channels`.
Edge lists contain outgoing recipient IDs; channel lists contain existing names.
Ballot overrides last one round; other edits persist. Invalid changes fail.
The [campaign-layer example](../examples/campaign-layer.toml) demonstrates
proximity loss and scheduled removal. These are external researcher controls:
campaign budgets, eligible-edge checks across layers and strategic controllers
remain Stage 05; graph plugins cannot change the campaign layer.

Trusted sensors are opt-in and separate from reports. Public sensors observe the
previous completed ballot of each sender with an incoming public edge; private
sensors observe other members of the observer's current private channels and
require `observe_private_channels`. Movement sees the preceding frame's recorded
sensor observations, filtered by current permission; a new permission does not
retroactively create an observation. Policy memory is not erased by revocation.
Graph policies see the graph after boundary edits/movement; voting sees the graph
after graph actions. Sensor tuples contain `(sender, source, completed_round,
ballot)`, never private rankings or current/future ballots. No report-only
policy receives an automatic sensor fallback. `sensed_plurality` counts each
observed sender once across overlapping channels, chooses the most common first
choice, and breaks ties by own preference; no sensor readings means sincere.
The [sensor example](../examples/sensors.toml) contrasts this with report-only
voting. Deceptive reports remain unimplemented, not trusted observations.

## Local strategies

Use trusted local Python modules only: `python:module:function`; place their
directory on `PYTHONPATH`. A group or person can select each phase separately.
Each callable receives `(observation, parameters, memory, rng)`; memory is
JSON-serializable, per-person/per-phase and checkpointed. Observation is frozen:
own preference/position/previous ballot, parties/k, round, permitted received
messages, outgoing public neighbors and channel names. Parameters are the
configured group/person table. `observation.sensed_ballots` is a distinct,
immutable tuple with the trusted readings described above. Local Python is **not
a security sandbox**.

- Voting: return `{"ballot": [party_ids...], "memory": value}`.
- Movement: `{"position": [x,y], "memory": value}`; displacement <= `max_step`.
- Graph: `{"memory": value, "add_edges": [...], "remove_edges": [...],
  "add_channels": [...], "remove_channels": [...]}`; change only own edges/membership.
- Communication: `{"reports": [{"recipient": id, "channel": name,
  "ballot": previous_ballot}], "memory": value}`; only allowed channels,
  no duplicate destinations or false reports. Deception is a later capability.

See [four-phase example](../examples/custom.toml), its [voting policy](../examples/favorite_policy.py)
and [movement/graph/communication policies](../examples/phase_policies.py). Invalid plugin results fail
before committing a frame. Plugins may access process/global state despite the
scoped interface: use reviewed code, explicit RNG and no hidden information.

Checkpoints contain full frames, pending messages, phase/voting memory,
interventions, voting-phase available sensor readings, core/runtime manifest
and plugin-source hashes. Sensor counts are included in metrics/CSV. Readings
are available observations, not proof a sincere policy used them. Restore replays
and compares history. If core/runtime changes, `--allow-environment-change`
permits explicit replay-based migration; plugin source mismatches still fail.
Manifest version 1 records Python, machine, core and CLI/experiment/render
pipeline hashes, plus RNG schema `actor-round-phase-v1`. Movement and each
person's policy phase use SHA-256-derived independent streams keyed by seed,
actor and round; equal seeds alone do not guarantee pairing for arbitrary plugins.
Hashes do not capture transitive plugin dependencies or guarantee behavior across
environments. Use matching versions for reproducibility. Start a fresh process
after changing a plugin; pre-imported modules are rejected because their loaded
code cannot be verified against the source hash. The policy function must be
defined in its configured source module; source is compiled directly, bypassing
timestamp-cached bytecode. Imported dependencies are not hashed.
The core fingerprint is a filesystem snapshot at simulation initialization;
changes during a run stop further steps/edits while saved history retains its
original fingerprint. Restart the process after changing core code: the hash
alone does not prove which core bytecode Python had already loaded.

## Browser

Open the localhost URL printed by `visual`. Select a person, step/play/seek,
choose speed, filter groups/layers and toggle node color. The sidebar shows
first-choice shares. Researcher view includes true private preferences; these
are not passed to other policies. Pause to edit preferences, one-round ballot,
group, JSON overrides, position, outgoing persistent/campaign neighbors or private
channel memberships. Edits apply at the next boundary; editing a past frame
replaces later frames. Only changed fields are submitted, so untouched scheduled
actions remain effective. Download a checkpoint before editing to preserve history.
The inspector lists the selected agent's trusted ballot readings for the displayed
voting phase, including source and completed round.

Progress and measured limitations: [Stage 01](plans/stage-01-political-simulator.md#progress).
Reproducible scale workloads: [benchmark notes](stage-01-benchmarks.md).
