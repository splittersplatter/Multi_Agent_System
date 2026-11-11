# Simulator guide: Stage 01

Status: implementation/verification in progress; see [checkpoint](plans/stage-01-political-simulator.md).
Research simulation only; no claim of real election prediction.

## Setup and commands

Architecture, verified scope and engineering limits:
[code audit](code-audit-and-refinement-report.md). Existing experiment imports and
commands remain stable after the module refinement.

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
Run JSON and JSONL headers identify `eclipse.run` record version 2; batch JSON
identifies `eclipse.batch` version 2. JSONL contains a header followed by metric
and available frame records; it is not itself a resumable checkpoint.
Network arrows point sender to recipient; overlapping public layers and reverse
directions use separate offset arrows.
Coincident nodes cannot show direction at image scale.

Metrics include party counts/shares and rank frequencies (rank counts divided
by population), zero-based mean winner rank, group sizes/counts/shares, and
per-layer and deduplicated public-edge counts. Switching compares adjacent
recorded rounds only: the first round and gaps are `null` (blank in CSV).
Proximity and public edge additions/removals count directed arcs. Public edges
are the union of persistent, proximity and campaign layers, with overlaps counted
once. Turnover is `|E_t Δ E_(t-1)| / |E_t ∪ E_(t-1)|`; an empty union gives
zero. The first round and gaps are `null`. Mean proximity in-degree is the
number of directed proximity arcs divided by population. These are descriptive
measurements, not convergence certificates or causal effects.
Empty-group shares are also `null`; their counts are zero. CSV group and rank
header IDs are percent-encoded. Intervention traces identify `scheduled`,
`interactive`, or `policy` origins; rejected actions raise errors and are not
committed. Paired plots mark scheduled treatment events only. Markers show
timing, not causal attribution.

## Scenario

See [baseline](../examples/baseline.toml) and [network](../examples/network.toml).
The [integrated example](../examples/integrated.toml) combines all four policy
phases, directed/proximity/campaign links, a private channel, sensors and a scheduled edit; run it
with `PYTHONPATH=src:examples`.
`parties` defines tie order; `k` is one global ballot length. Each person has a
unique ID, group, full strict private `preference` and optional `[x,y]` position
and `overrides`. Bounds: positions in `[0,1]^2`; `1 <= k <= number of parties`.
Round 0 votes sincerely; first-choice plurality counts each length-k ballot.

Group fields: `voting` (baseline, [strategic heuristic](voting-heuristics.md), or plugin), `movement`
(`stationary`, `random_walk`, or plugin), `max_step` (0..1), `communication`
(`none`, `truthful`, `target_report`, or plugin), `graph` (`none` or plugin), `parameters` (table).
Person overrides replace individual fields; `{}` restores group defaults.
`local_plurality` chooses the most-reported first choice, breaking ties by own
preference; no reports means sincere voting.

Ten strategic heuristics, startup selector, JSON parameters and matched-seed
`compare` command: [voting reference](voting-heuristics.md). All use the same
engine/history. Defaults are explicit modelling assumptions, not paper replications.
Three [epistemic policies](epistemic-voting.md) additionally require an explicit
electorate-roster permission and impose a logical-world limit.

Each group accepts a `capabilities` table of boolean permissions:

```
observe_public_neighbors  observe_private_channels  observe_electorate
sense_public_ballots      sense_private_ballots  observe_target_preferences  intercept_private_reports  observe_public_signal
receive_public_reports    receive_private_reports
send_public_reports       send_private_reports
modify_persistent_edges   modify_private_channels   move
```

Omitted sensor, preference-sight, interception, public-signal and electorate-roster permissions default to `false`; other permissions default to
`true` for compatibility with existing scenarios;
restrict them explicitly, e.g. [restricted.toml](../examples/restricted.toml).
Person `overrides.capabilities` merges individual entries over group permissions.
The inspector shows effective permissions; edit them via the JSON overrides field.
Denied plugin actions fail the whole step; built-in truthful broadcasts use only
allowed destinations. Receive permissions are checked on delivery, including
queued messages after a boundary edit; denied messages are not delivered.
Revocation does not erase knowledge already stored in policy memory. Researcher
and scheduled interventions are external controls and do not use agent permissions.
Delivered reports retain sender/channel and source, generation and delivery rounds
in `report_provenance`; plugin observations expose the same metadata. In the current
protocol a report generated in round t refers to completed round t-1 and is
delivered in t+1. Truthful reports copy the ballot; coalition reports can be false.
The reference timestamp does not establish that the payload was a real ballot.
Checkpoint version 21 replays prior compatible histories with explicit environment review
when runtime/source hashes changed; tampered histories are rejected.
With `modify_private_channels = true`, a graph plugin may join any configured
channel; disable it when membership must remain externally controlled.

`[network]`: optional proximity `radius`; directed `persistent_edges` and
`campaign_edges` as `[[sender,recipient],...]`; `private_channels = { name = [member_ids...] }`.
Each group may set `proximity_radius` in `[0, sqrt(2)]`; a person may override it
in their policy overrides. Otherwise that person inherits the global radius;
without either, proximity is disabled for that receiver. Radius zero includes
coincident people. For distinct people within the receiver's radius, proximity
contains `sender → receiver`; differing radii can produce a one-way link. Public
ballot sensors and messages use these directed links. Group/override changes apply
at the next edited or scheduled round; persistent, campaign and private layers
remain separate. The selected-agent browser overlay shows the receiver radius;
it does not imply symmetric links. [Example](../examples/group-radius.toml):

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/group-radius.toml --port 8008
```

Persistent and campaign edges remain until explicitly removed; proximity links
are recomputed by default. Set `[network] proximity_mode = "frozen"` to retain
the directed proximity graph calculated at round zero, even after position,
group or radius edits. Other layers and movement remain active. In this mode the
browser radius overlay is drawn at the initial position with the initial radius;
it describes graph construction, not current contact distance. Alternatively,
`proximity_mode = "static"` requires `static_proximity_edges = [[sender,receiver], ...]`;
that fixed directed layer ignores radii and positions. The browser identifies it
as an explicit graph and suppresses the radius overlay. Overlapping public
edges are deduplicated; channels remain separate. Reports use prior
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

Compare dynamic and frozen proximity using identical initial settings and keyed
movement draws (the input mode is ignored in this comparison):

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare-networks examples/group-radius.toml --seeds 11 22 33 --output /tmp/network-comparison.json
```

Requires built-in stationary/random-walk movement and no graph-policy plugins;
checks equal per-round positions. Each pair records failures, full metric series,
and each receiver's cumulative incoming proximity-arc exposure over rounds
1..T. `exposure_delta = dynamic − frozen`; `exposure_l1` sums absolute per-voter
differences. Equality of these totals does not match individual contacts or timing.
This frozen-initial control is **not** an exposure-matched network and by itself
cannot isolate a turnover effect; other graph layers or interventions can confound.

Add a one-to-one, unique and disjoint calibration seed for each evaluation seed
to include an explicit static exposure control:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare-networks examples/group-radius.toml --seeds 11 22 --calibration-seeds 101 102 --output /tmp/calibrated-networks.json
```

For each receiver, count incoming calibration arcs over rounds 1..T. Choose a
static in-degree nearest to count/T (half ties round down), then choose the most
frequent senders (ID breaks ties). This minimizes the sum of absolute per-voter
calibration exposure errors over directed simple static graphs; it is not
necessarily optimal for the held-out trajectory. The result records calibration
seed and contact frames, static scenario, degree, calibration/held-out exposure
residuals, held-out temporal arc mismatch and failed runs. Contact partners,
timing, degrees per round and public-layer overlap may differ even when cumulative
exposure matches. Separate seeds prevent the graph from encoding that evaluation
run's future movement draws; this is a calibration control, not a proof of causal
identification. Scheduled position, group or policy-override changes are excluded
from calibrated comparison because their future topology could otherwise leak into
the initial static graph. Without calibration seeds, the third control is unavailable.
None of these comparisons certifies convergence for unrestricted mixed policies.

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
  "ballot": ballot}], "memory": value}`; only allowed channels, no duplicate
  destinations. False ballots require an eligible coalition and budget.

### Budgeted report deception

Configure fixed `[[coalitions]]` entries with unique `id`, disjoint known
`members`, a known `target`, `report_budget_per_round` and `report_budget_total`
(nonnegative integers). See [coalition-report.toml](../examples/coalition-report.toml):

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/coalition-report.toml --port 8008
```

Each false report sent to an authorized `(recipient, channel)` costs one unit,
including separate channels to the same recipient. Truthful reports cost zero.
Round budgets reset; episode budgets do not. Members act in sorted ID order;
plugin report order determines allocation within a sender. A communication plugin
receives `(id, target, remaining_round, remaining_total)` as
`observation.coalition_report_budget` for its own coalition only; others and
other phases receive `None`. Shared remaining budget reveals aggregate earlier
spending, not a common-knowledge guarantee. Plugins exceeding the budget, sending
invalid ballots, duplicate destinations or unauthorized messages fail the whole
round without spending. `target_report` sends a target-first false ballot to
sorted permitted destinations until the budget is exhausted, then truthfully
reports the preceding ballot. It requires coalition membership.

Recipients receive ordinary reports without truth labels; trusted sensors remain
independent. Researcher frames/inspector show `deceptive_reports` and cumulative
`coalition_report_spend`; CSV contains per-round false counts and cumulative spend.
Spend and pending messages replay/rewind with checkpoint v14. Zero budget has the
same ballot/report dynamics as truthful broadcasting. This does not implement
strategic optimality or convergence. Certified
convergence scenarios reject coalitions; these adaptive multi-agent cases remain
uncertified. Failed proposals are reported as errors, not persisted as audit events.

### Budgeted preference sight

Add `sight_targets` (nonempty unique person IDs), `sight_budget_per_round`, and
`sight_budget_total` to a coalition; grant `observe_target_preferences = true`
only to its members. [Example](../examples/coalition-sight.toml):

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/coalition-sight.toml --port 8008
```

After boundary edits and graph actions, the engine automatically reads targets'
current private rankings, one unit per `(observer,target)` reading. Coalition
members and targets are visited in sorted-ID order; self-readings are skipped.
The shared round budget resets, episode budget persists, and repeated readings
are charged again. Exhaustion grants no further reading. Only authorized members
receive their own current readings, as `observation.sighted_preferences` tuples
`(target, round, preference)`, in communication and voting plugins—not movement
or graph plugins, reports, ballot sensors, or other agents' observations. Previously
remembered information is not erased by revocation. Existing epistemic and other
strategic built-ins do not incorporate these readings; do not grant sight to them
unless deliberate budget consumption without use is intended.

`sight_plurality` is an explicitly configured group policy: vote for the most
common sighted first preference, breaking ties by one's own ranking; with no
readings vote sincerely. It requires membership, targets and permission. It is a
simple simulation heuristic, not an optimal attacker or convergence guarantee.
Episode-wide startup selection applies to everyone and is rejected unless every
voter has the required coalition membership and permission; use group settings for
mixed populations.
Researcher frames/inspector and CSV record readings and cumulative sight spend;
only the researcher view exposes all such events. Sight and report budgets are
independent. Target selection is currently a fixed sorted schedule, not an adaptive
selection policy; full coalition ablations remain unimplemented.

### Budgeted private-report interception

Add `eavesdrop_channels` (nonempty configured private-channel names),
`eavesdrop_budget_per_round`, and `eavesdrop_budget_total` to a coalition; grant
`intercept_private_reports = true` only to its members. Example:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/coalition-eavesdrop.toml --port 8008
```

At each delivery boundary, authorized observers intercept already-sent private
reports on those channels, one budget unit per `(observer, packet)`. Observers
and pending packets are considered in sorted order. An observer cannot intercept
their own sent or addressed packet; no channel membership or public edge is
created. Interception is independent of whether the intended recipient accepts
delivery. Round budgets reset; episode budgets persist. No packet means no charge.

Communication/voting plugins receive their own `observation.overheard_reports`:
`(sender, recipient, channel, generated_round, reference_round, intercepted_round,
report)`. These are untrusted reports and may be false; they are not ballot
sensors, preferences, factual announcements or evidence of channel membership.
Other phases and agents receive no such records. Prior plugin memories survive
revocation. `overheard_plurality` counts consistent intercepted first-choice
reports once per sender, ignores a sender with conflicting first choices, and
breaks ties by own preference; with no usable reports it votes sincerely. It is
a simple heuristic, not a convergence guarantee. Existing epistemic and strategic
built-ins do not incorporate intercepted reports. The researcher view and CSV
record interception events and cumulative spending; report, sight and interception
budgets are independent. Selection is fixed-order, not adaptive.

### Coalition ablations

`coalition_fusion` combines authorized current preference-sight first choices
and intercepted report first choices. It counts each person at most once: a
sighted preference takes precedence over that person's report; conflicting
intercepted reports are ignored. These are different evidence types, not a claim
that a report is a truthful preference. Highest count wins, ties use own ranking,
and no evidence gives a sincere ballot. Both permissions and configured target
lists are required. It is a bounded simulation heuristic, not an equilibrium rule.

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/coalition-combined.toml --port 8008
PYTHONPATH=src python3 -m multi_agent_election.cli coalition-ablations examples/coalition-combined.toml --seeds 11 22 33 --output /tmp/coalition-ablations.json
```

The six arms are `none`, `sight_only`, `deception_only`, `eavesdrop_only`,
`coordination_only`, and `all`. Disabled sight/deception/interception use zero
budgets; disabled coordination removes coalition members' private-report send
and receive permissions. Channel membership, separately enabled trusted sensing,
public reports and all noncoalition behavior remain unchanged. Enabled arms use
only capabilities configured in the input; they do not grant new permissions.
Fixed sender ordering and budget allocation can create interactions between arms.

Requires built-in stationary/random-walk movement, no graph-policy plugins, and
no scheduled group/override changes; per-round positions are checked against the
control. Each arm retains its configuration, frames, metrics, source digests and
failed runs. Output is a researcher artifact and includes private preferences;
do not expose it to simulated agents. Successful matched arms report each coalition's final target-win,
share and margin differences against `none`; failed controls yield no paired
results. These horizon comparisons are descriptive, not convergence certificates
or causal claims. Freeze parameters and independent seed splits, then use enough
seeds and uncertainty analysis before drawing research conclusions.

### Budgeted campaign edges

Configure `[campaign_controller]` with `target`, `policy` (`none`, `random`, or
`target_heuristic`), `lifetime_budget`, `per_round_budget`, and optional
`max_candidates` (default 100,000; maximum 1,000,000). Example:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/campaign-controller.toml --port 8008
```

The controller explicitly observes every previous committed first-choice ballot
and the current public graph after movement and graph actions. It does not receive
private preferences. Eligible directed edges connect a target-ballot supporter to
a non-supporter and exclude self-links, already-effective public links and prior
controller purchases. `random` samples this set using its own actor/round RNG;
`target_heuristic` prioritizes recipients with highest current public out-degree,
then recipient and sender ID. This is a heuristic, not an optimality claim.

Each accepted directed edge costs one unit; reciprocal edges would cost two.
Controller links persist in the campaign layer, including after proximity changes.
A purchased edge remains charged and cannot be repurchased after external removal.
Initial and researcher-added edges are separate and consume no controller budget.
If the exact eligible set exceeds `max_candidates`, the round fails atomically;
when no selection is possible because of policy or budget, eligibility is `null`
rather than measured. Frames, CSV and researcher inspector record eligibility,
proposals, acceptances and cumulative spend; current generated proposals are
always eligible, so there are no rejected proposals. Checkpoint v15 preserves
the purchase ledger. Voting agents do not automatically gain the controller's
global view. Certified scenarios reject controllers; these dynamics are uncertified.
The existing coalition-ablation and network-control commands reject controller
scenarios until their combined-control designs are specified.

Compare policies with identical configured budgets and paired movement seeds:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare-campaign examples/campaign-controller.toml --seeds 11 22 33 --output /tmp/campaign-comparison.json
```

The no-addition control, random and target heuristic retain complete researcher
frames, metrics, source digests, failures and per-round target win/share/margin
differences. Realized spending can differ despite equal allowed budgets. Requires
built-in stationary/random-walk movement, no graph-policy plugins and no scheduled
group/override changes; positions are checked. These are descriptive comparisons,
not claims of convergence or effect. The browser campaign chart shows cumulative
spend and marks rounds with accepted additions.

For an exact **evaluator-only** one-round bound:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli campaign-exhaustive examples/campaign-exhaustive.toml --max-combinations 10000 --output /tmp/campaign-upper-bound.json
```

This enumerates every subset of initially eligible edges up to both budgets and
returns separate maximum target votes and target-win possibility with witnesses.
It requires exactly one round, at most eight voters, stationary movement, no
interventions, graph actions or plugins. Before simulation it checks the exact
combination count against `--max-combinations` (maximum 100,000); no partial
optimum is returned on failure. The evaluator preinstalls each chosen edge set;
within these restrictions, agents see it at the same decision phase as a round-one
controller addition. With zero budget eligibility is unmeasured (`null`). This
full-outcome oracle is unavailable to agents and does **not** bound later adaptive
campaigns, different edge eligibility rules or other models.

### Bounded public signals

Configure `[signal_controller]` with `target`, `policy` (`truthful`,
`bounded_random`, or `target_biased`), `schedule` (`initial` or `repeated`),
`per_broadcast_budget` and `lifetime_budget`. Grant `observe_public_signal = true`
to recipients. [Example](../examples/public-signal.toml):

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/public-signal.toml --port 8008
```

After graph actions and before communication/voting, a broadcast uses the last
completed true first-choice counts. The report is a nonnegative integer vector
with the same total; its cost is `L1(truth, report)/2`, bounded per broadcast and
over the episode. `target_biased` transfers from the largest non-target count to
the target, breaking donor ties by party order. `bounded_random` chooses one
destination uniformly and random nonempty other donors, so it is not uniform over
all feasible reports. Both stop when budget or donor votes run out. `truthful`
costs zero. `initial` broadcasts once and retains that report; `repeated`
broadcasts each round, including truthful broadcasts after budget exhaustion.

Authorized communication/voting plugins see only `(source_round, broadcast_round,
reported_counts)` as `observation.public_signal`; earlier phases and unauthorized
agents receive `None`. `signal_confident` treats the latest report as a current
plurality score vector, subtracts its own prior ballot and makes a direct strict
improvement if one exists. If the report excludes its own ballot, it retains the
full ballot; a retained initial report is marked stale. This is a trusting
heuristic, not factive knowledge or a convergence guarantee. The original
epistemic policies ignore this signal; [bounded-signal variants](epistemic-voting.md#bounded-public-signals)
use only compatible worlds. The researcher frame/CSV and browser show both
the report and its corresponding source truth, timestamps and spending; these
truth values are not agent observations. A missing broadcast cost is `null`, not
zero. Checkpoint v17 preserves the signal, its source and budget. Certified
convergence scenarios reject signal controllers.

For matched descriptive controls:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare-signals examples/epistemic-public-signal.toml --seeds 11 22 33 --groups signal_voter --signal-distortion-bound 1 --output /tmp/eclipse-signals.json
```

Nine arms: selected groups use sincere, trusting, or known-bound dominant voting;
each receives truthful, bounded-random, or target-biased signals. Each response
is paired against its truthful-signal run; each signal policy is separately paired
against its sincere-response run. The latter records whether the realized report
and source truth still match: past response differences can change both. All
arms retain the same allowed budgets, selected-group permissions and seed; no
capabilities are granted. Selected voters must already have signal/roster access,
and the explicit bound must cover all compared controller policies. Group/policy
interventions, selected-person voting/parameter overrides, graph plugins and other
plugins are rejected; stationary/random-walk movement is checked for pairing.
Other configured mechanisms may respond endogenously. Full frames, metrics,
runtime manifest, failures and unpaired runs are retained. This is an exploratory
comparison tool, not proof of causal identification, convergence or a research ranking.

### Spatial nomination

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/nomination.toml --port 8008
PYTHONPATH=src python3 -m multi_agent_election.cli compare-nominations examples/nomination.toml --seeds 11 22 33 --output /tmp/eclipse-nominations.json
```

Nomination scenarios omit `parties` and per-person `preference`; each person
provides a nonempty `ideal` vector in `[0,1]^d` and an independent physical
`position`. All dimensions must match. `[nomination]` specifies `m`, `eligible`
person IDs and `mode = "endogenous"`, `"fixed"` or `"random"`; fixed mode also
requires `nominees`. Require `1 <= k <= m <= len(eligible)`. Eligible people's
issue vectors are their public nomination platforms; all other ideals are private.

Before round zero, each person nominates the closest eligible **incoming public
neighbor or self**, with ID ties. Public neighbors are the initial union of
persistent, campaign and configured proximity layers; private channels do not
count. A noneligible person without an eligible incoming neighbor abstains.
Endogenous mode selects the highest nomination counts, ID ties, including zero
counts. Fixed mode uses the specified eligible people; random mode samples
uniformly without replacement with a separate seed-keyed stream. Every mode
records the same counterfactual nomination ballots and counts for audit; voters
do not observe that record. Parties are the selected person IDs in sorted order.
All voters' strict candidate rankings follow issue distance, ID ties. Leaders
remain ordinary single-vote people; candidate set is fixed. Platforms remain fixed
unless the optional leader-adaptation model is enabled.

Researcher view shows nominee rings, issue coordinates (first two dimensions),
ballots/counts and initial ideals. Votes use the existing ordinal interfaces;
agents receive no other voters' ideals. Without alignment dynamics, manual ordinal
preference edits remain possible and logged; they do not modify the initial ideal
or leader position.
CSV/metrics include mean winner-to-initial-ideal and nearest-nominee distances;
these are synthetic geometric measures, not validated welfare. Checkpoint v18
stores the nomination configuration and re-derives its results on replay.

`compare-nominations` pairs endogenous with identical fixed nominees and an
equal-size random set. It retains configurations, nomination records, frames,
movement checks, distance differences, failures and source manifest. The fixed
control must have identical frames when no nomination information is exposed;
random nominees can omit a configured attack target, causing a recorded failure.
Some other comparison utilities change the seed or initial graph by replacing a
scenario; nomination scenarios reject noncanonical changes instead of silently
retaining stale nominees. Use `compare-nominations` for these controls. No
stochastic or convergence claim follows from its output.

### Bounded ideal shifts

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/alignment-attack.toml --port 8008
PYTHONPATH=src python3 -m multi_agent_election.cli compare-alignment examples/alignment-attack.toml --seeds 11 22 33 --output /tmp/eclipse-alignment.json
```

Add `[alignment]` only to a spatial nomination scenario. Set `drift_max_step`;
`[alignment.attack]` requires a nominated `target`, explicit `targets` person
IDs, `policy = "none" | "toward_target" | "random"`, `per_person_round`,
`total_budget`, and boolean `observe_target_ideals`. Directed movement requires
that permission; random movement does not. Targets are fixed by configuration,
not selected by a hidden-ideal ranking. All budgets and step sizes are finite,
nonnegative L2 distances; per-person steps cannot exceed the issue-space diagonal.

Each round: independent per-person natural drift, then target-scope attack in
sorted ID order, then recompute each person's strict ranking against the applicable
leader perceptions (fixed initial platforms without leader adaptation), then run the existing simulation phases. The drift
direction comes from normalized independent uniform `[-1,1]` components with
length uniform from zero to its cap; clipping to `[0,1]^d` occurs before measuring
distance. Directed attacks move toward the target platform; random attacks use
a separately keyed direction stream. Attack movement is clipped before its
realized L2 path length is charged to the shared nonrenewable episode budget;
the per-person cap applies separately each round. Leaders' voter ideals can
move when targeted; their platforms change only through the separate leader model. Zero attack cost does not
debit budget. These are explicit research assumptions, not empirical influence models.

Alignment scenarios reject scheduled or interactive ordinal preference edits:
their rankings must remain derived from current ideals. Ballot, graph, group
and physical-position edits remain governed by existing permissions. Agents get
their own resulting ranking, not other people's ideal vectors; scoped coalition
preference sight remains distinct from ideal sight. Researcher-only frames and
issue view show ideal trajectories, before/after drift and attack, and spend;
checkpoints v19 verify these records on replay. CSV includes attack spend/cost,
drift distance, targeted count and distances to current as well as initial
voter ideals. No current-drift case is convergence-certified.

`compare-alignment` retains four paired arms: no drift/no attack, drift only,
directed attack plus drift, and random attack plus drift. Attack arms share the
same permitted scope and budgets and pair against drift-only. Random streams are
keyed independently of attack and physical movement; clipping and earlier shifts
can nevertheless change later realized drift. Random and directed attacks may
spend different amounts. Other enabled mechanisms can react endogenously;
results are descriptive, not a causal or convergence guarantee.

### Passive aggregate detector

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/detector.toml --port 8008
PYTHONPATH=src python3 -m multi_agent_election.cli evaluate-detector examples/detector.toml --calibration-seeds 100 101 102 --evaluation-seeds 200 201 202 --false-alarm-rate 0.1 --output /tmp/eclipse-detector.json
```

Optional `[detector]` specifies a known `target` party and `threshold` in `[0,1]`.
At round `t>0`, statistic = `(target_votes_t - target_votes_(t-1))/N`; alert
iff statistic **strictly exceeds** the threshold. Round 0 has no statistic or
alert, but its winner counts toward the consecutive-win streak. First triple-win
endpoint `t3` is the earliest round completing three target wins. The detector
reads only current/prior aggregate counts and its own memory; it cannot see
attack labels, ideals, messages or budgets and cannot influence the simulation.
Alerts are anomalies, not proof of attack. Red triangles mark alert rounds;
CSV and checkpoint v20 include statistics, alert and streak state. Rewind/replay
restores the exact state.

The evaluation command requires matching detector/attack targets, at least one
round, explicit alignment sight permission and disjoint unique calibration and
evaluation seeds. Calibration disables the alignment attack while retaining drift
and other configured mechanisms. For each calibration run it takes the maximum
positive one-round target-share increase. With `n` runs and requested rate `α`,
the frozen threshold is sorted maximum number `ceil((1-α)n)` (one-indexed);
strict inequality makes ties conservative. Any calibration failure blocks
threshold selection and evaluation rather than dropping that run. This controls
the **observed calibration fraction**, not a guaranteed future false-alarm rate.

Held-out evaluation retains all four alignment arms, raw frames, seeds, failures
and unpaired runs. False-alarm rates are per no-alignment-attack arm; other enabled
manipulations may still be present. Attack onset is the first round with positive
realized attack cost, determined by the evaluator only. Overall recall includes
all realized attacks whether or not `t3` occurs. Zero-cost attempts are counted
separately. Delay is first alert at/after onset minus onset; no such alert is
censored. Pre-`t3` recall uses realized attacks with `t3 > onset` and requires
`onset <= alert < t3`; no `t3` is censored and `t3 <= onset` is reported separately.
Pre-onset alerts, denominators and failures are reported. Small seed examples are
smoke checks; formal comparison still requires the frozen evaluation protocol,
adequate independent seeds and uncertainty estimates.

### Hidden leader adaptation

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/leader-adaptation.toml --port 8008
PYTHONPATH=src python3 -m multi_agent_election.cli compare-leaders examples/leader-adaptation.toml --seeds 11 22 33 --output /tmp/eclipse-leaders.json
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/all-enabled.toml --port 8008
```

Spatial nomination scenarios may add `[leaders]`: `policy = "fixed" | "feedback"`,
`adaptors` (nominated person IDs), `per_round_step`, per-adaptor `lifetime_budget`,
`signal_mode = "broadcast" | "none"`, `signal_noise` and `perception_weight`.
Initial perceived positions equal initial publicly nominated platforms. True
leader positions, public noisy signals, shared voter perceptions and evaluator
distances are separate. A leader's true position and the same person's voter
ideal are separate state variables.

At each round's start every adaptive leader independently observes the previous
committed **true aggregate vote count**, not a manipulated poll, and its own last
action/support. The finite action list is `+axis 1, -axis 1, +axis 2, -axis 2, …`,
plus no-op. First action starts at `+axis 1`; after a support increase repeat the
last direction, after a decrease reverse it, and after no change try the next
direction. Scan cyclically past infeasible boundary moves; no-op if fixed or no
movement is available. Per-round L2 and per-leader episode path limits are charged
after clipping. All leaders use the same previous frame, not one another's new
actions. This is a feedback heuristic, not an optimality or causal-inference claim.

Broadcast signals equal each new true coordinate plus independent uniform noise
in `[-signal_noise, signal_noise]`, clipped to `[0,1]`. Signal RNG is keyed by
leader and round, separately from movement, drift and attacks. All voters share
the update `perceived = (1-weight)*previous + weight*signal`. With no signal,
perceptions remain at their initial values even if hidden positions move. Voters
know their own current ideal and ranking by **perceived**, not hidden, positions;
plugin observations expose only own ideal and perceived platforms. When alignment
attacks are enabled, the directed controller aims at the **previous public
perception** of its target, not the target's hidden new position. Ordinal
preference edits are rejected in this derived-ranking mode; ballot edits remain.

Frames/checkpoint v21 retain true positions, public signals, perceptions,
feedback memory and budgets; CSV contains coordinates, perception errors and
synthetic true/perceived winner distances. The researcher issue view draws
diamonds for hidden true positions, squares for perceptions and their trajectories.
`compare-leaders` pairs adaptive vs fixed under broadcast and under no-signal;
the latter checks all non-leader frame fields for equality, including ballots,
messages and detector output. It flags failures and unpaired runs. Detector
alerts are labeled as honest-adaptation alarms only when other configured attacks
and interventions are absent. No convergence, human-behavior or real-election
claim follows. The all-enabled example is an integration demonstration, not a
validated causal study; later full-system gates remain open.

### Combined mechanism matrix

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli combined-ablation examples/all-enabled.toml --seeds 11 22 33 --target alice --output /tmp/eclipse-combined.json
```

Versioned output contains 17 arms per seed: all enabled, all disabled, seven
isolated mechanisms, seven leave-one-out arms, and a separate detector-off arm.
Each completed arm retains its normalized scenario, SHA-256, source/runtime
manifest, full frames, metrics, nominee record and paired comparisons. Failed
and unpaired arms are retained; no failures are imputed. Input must configure
all seven mechanisms, a passive detector, endogenous nomination, positive
relevant budgets, built-in policies and dynamic proximity with movement. Plugins
and scheduled interventions are excluded from this matrix; the general simulator
continues to support them.

Controls: proximity-off freezes initial proximity but preserves movement;
coalition-off zeros sight/deception/interception budgets and disables coalition
members' private send/receive while retaining membership; campaign-off adds no
controller edges; poll-off reports truth; nomination-off fixes the same nominees;
alignment-attack-off preserves natural drift; leader-adaptation-off freezes true
leader positions while preserving coupled noisy broadcasts. The detector remains
passive instrumentation in those 16 arms, including all-disabled; detector-off is
the separate 17th arm and checks equality of every non-detector frame field.
Thus all-disabled means mechanisms disabled, not absence of natural drift or
observation noise. Enabled configurations may still realize no action.

Each pair checks matching physical positions and candidate IDs. It reports
per-person cumulative proximity exposure differences and edge-round symmetric
difference; a frozen graph is not assumed exposure-matched. Identical nominee
controls test process only, not nominee-composition effects. Later reports,
signals and contacts may differ through feedback. Output is descriptive: matching
seeds does not establish causal identification, convergence or statistical significance.

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
Manifest version 1 records Python, machine, core and CLI/experiment/render/browser-adapter
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
first-choice shares with percentage/round axes and expandable metrics for the
displayed round. Separate plots show directed proximity contacts and turnover;
missing rounds break the line. Dashed markers show the selected round and intervention events;
events do not establish causality. Network
nodes support Tab and Enter/Space; focus survives playback redraws. Researcher
view includes true private preferences; these
are not passed to other policies. Pause to edit preferences, one-round ballot,
group, JSON overrides, position, outgoing persistent/campaign neighbors or private
channel memberships. Edits apply at the next boundary; editing a past frame
replaces later frames. Only changed fields are submitted, so untouched scheduled
actions remain effective. Download a checkpoint before editing to preserve history.
Unsubmitted edits are local drafts scoped to one agent and recorded frame; they
survive filters, selection and timeline navigation. Successful edits, a changed
remote revision or page reload discard drafts. A rejected edit at an unchanged
revision keeps its draft. Drafts are not checkpointed.
Browser checkpoint downloads reject stale revisions; reload if another session
changed the simulation. The legacy unversioned HTTP endpoint returns current state.
The inspector lists the selected agent's trusted ballot readings for the displayed
voting phase, including source and completed round. Expand agent reports and
memory for received/pending reports, policy memory and interventions in that frame.
The preference-estimate color mode is a visualization heuristic, not an agent
belief: selected agent's own preference is known; others use the first choice
of reports or sensed ballots available at that round's voting phase. These can
be stale or strategic. Missing or conflicting first choices are gray; pending
messages and hidden preferences are excluded. Rewind changes the evidence shown.
Overlapping directed public layers use separate offset arrows in the browser,
network PNG and GIF; coincident or near-coincident positions may obscure direction.
The export selector downloads metrics CSV, vote-share SVG/PNG, displayed-round
network PNG or a GIF of the retained timeline. PNG/GIF need Pillow. Exports use
an immutable revision-checked snapshot and do not advance or rerun the model.
Pause first; if a step is still completing, retry after it finishes. Browser
download settings control whether the requested file is actually saved. The
latest prepared file stays available as a direct save link labeled with its
source revision (and displayed round for exports); preparing another replaces it.
During an in-flight step, Pause shows `Pausing…`; timeline navigation, edits,
and downloads stay disabled until the committed round arrives. A disconnect
stops playback; already committed server-side rounds are not rolled back.

Progress and measured limitations: [Stage 01](plans/stage-01-political-simulator.md#progress).
Reproducible scale workloads: [benchmark notes](stage-01-benchmarks.md).
