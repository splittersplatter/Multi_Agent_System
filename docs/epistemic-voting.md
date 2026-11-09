# Finite knowledge and epistemic voting

Stage 02 partial. Two related interfaces: an explicit pointed knowledge model
and simulation policies using an actor's permitted observation. [Stage plan](plans/stage-02-information-and-epistemic-reasoning.md).

## Run

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli knowledge examples/knowledge-profile.json --agent 1
PYTHONPATH=src python3 -m multi_agent_election.cli knowledge examples/knowledge-profile.json --conditional examples/conditional-profile.json
PYTHONPATH=src python3 -m multi_agent_election.cli knowledge examples/knowledge-two-voters.json --solve-conditional
# Tiny regression only; not an outcome simulation.
PYTHONPATH=src python3 scripts/verify_fixture.py run examples/epistemic.toml --summary
```

Normal simulations require N>=100. These finite-world policies retain a
1,000,000-world ceiling and enumerate other voters' strict preferences: with
N>=100 and m>=2 they exceed that ceiling even with complete ballot sensing.
They currently serve tiny exact verification, not production-scale epistemic
voting. The standalone JSON knowledge analysis is a formal tool, not a population
simulation. Do not silently raise caps, sample worlds or claim a large run succeeded.

Fixture example: agent 1 temporarily casts C, sees completed A/B/B ballots and then votes A;
inspector **Agent reports and memory** records 216 logical worlds, one projected
ballot profile, de re A, an opt-in observation history and no other voters'
private preferences. The override is a researcher-scheduled edit, not an attacker implementation.

`epistemic-integrated.toml` combines de re, pivotal-poll and sincere voters,
movement, directed public links, a private channel and delayed truthful reports.
Its winners are A, B, A, A, A; at round 2 the reasoner changes C to A while
the poll voter retains A with score belief [1,2,1]. Information differs across
policies: this is an integration example, not a matched comparison or a certified
convergence case. `compare` replaces group voting policies; use the scenario
directly to retain its mixed groups.

## Explicit model

`KnowledgeModel.from_dict(data, max_worlds=10000)` accepts ordered parties,
ballot length k, agent IDs, worlds and `actual` world ID. Each world specifies:
strict preference and submitted ranked ballot per agent, observation label per
agent, optional public signal and public history. Equal labels for one agent
define an indistinguishability class. Distinct world IDs may share valuations.

The model checks unique IDs, valid rankings/ballots, nonempty partitions, actual
world membership, finite JSON and world cap. Indistinguishable worlds must agree
on that agent's own preference/ballot and public signal/history. Nested knowledge
is expressible by calling `knows` at each possible world. `announce(predicate)`
rejects a proposition false in the actual world, then restricts every agent's
relation and retains that world. A signal may *report* something false; observing
the signal does not make its reported claim factual.

`analyze(agent)` examines current submitted ballots and deterministic plurality:

- **de dicto:** every possible world has some strictly improving first-choice action.
- **de re:** one fixed action strictly improves every possible world.
- **dominant:** one action is never worse and strictly improves at least one world.
- **pessimistic:** action's worst possible winner is strictly preferred to the
  worst current winner. Candidate lists follow the voter's private ranking.

Unlike the paper's truthful-profile baseline, this iterated-voting extension
compares against submitted ballots. These are distinct concepts: de dicto alone
does not identify a single actionable choice. `knowledge` is a researcher-facing
JSON analysis, not a voter-facing view of the actual world.

### Conditional equilibrium

`conditional_equilibrium(profile)` checks every agent's every information set,
including sets outside the actual world. A profile maps each agent and each
observation label to a first-choice party. In each world, every opponent acts
according to their own label; the tested agent compares its worst current winner
against the worst winner for each unilateral alternative. No strictly better
worst outcome in any information set means conditional equilibrium. Preference
rankings are strict and fixed within each class; election ties use party order.

Labels represent observations before choosing a ballot. Conditional actions may
differ from the recorded baseline ballots; this is an explicit counterfactual
profile, not an update to those records. Plurality first-choice actions are an
outcome-equivalent quotient of ranked ballots, not a non-plurality solver.
`solve_conditional_equilibria()` enumerates every joint conditional profile and
returns the full set; `max_profiles` (default 10,000) and `max_evaluations`
(default 1,000,000 outcome calculations) are checked before work. Limit failures
return no partial or falsely complete result. `announce_with_profile` applies a
truthful public announcement and restricts the profile to surviving labels.

The two-voter example reproduces `{A,B}` and `{B,B}` equilibria from S2 §5.2.
The multi-world tests independently enumerate information-contingent opponents.

## Simulator information contract

| Data | Access |
| --- | --- |
| Own full preference, prior ballot, position | Always |
| Electorate IDs | Only with `observe_electorate = true`; no private preferences |
| Outgoing public neighbor IDs / own private-channel membership | Only with `observe_public_neighbors` / `observe_private_channels`, respectively |
| Public/private neighboring ballots | Only with corresponding trusted sensing permission; completed previous frame and source/timestamp recorded |
| Delivered public/private reports | Subject to corresponding receive permission; sender, channel, source/generation/delivery rounds retained; these policies do not treat reports as factual votes |
| Public aggregate poll | Only signal-aware variants with `observe_public_signal`; report and timestamps, never source truth or realized cost |
| Other true preferences, future changes | Not given to these policies |
| Possible worlds | All combinations consistent with the above observations and declared unconstrained prior; researcher-only actual world is not passed to policy |

All other preferences may be any strict ranking. Unobserved ballots may be any
valid k-permutation, independently of preferences; no prior assumption that others
vote truthfully. Observed complete ballots constrain exactly their senders.
The actual state is included when trusted readings are truthful and complete for
the prior frame. Current information is rebuilt each round: no transition model,
nested agent knowledge, probabilistic beliefs or unmodelled temporal updates are inferred.

Set `remember_observations = true` in voting parameters to retain per-agent
observation history since that policy/parameter configuration was activated.
History records observation round, own data, permitted roster/neighbors/channels,
trusted ballots with completed-round timestamps, and delivered report provenance.
For the current one-round report protocol, delivery at t means generation at t-1
with reference round t-2. A report may be fabricated. Generation and delivery timestamps establish
packet provenance; they do not turn reports into trusted ballot observations.
Direct callers that omit provenance receive null timestamps instead of guessed data.
Revoking sensing prevents new readings but does not erase earlier memory; rewind
restores the retained prefix and replay reproduces it. Changing policy or voting
parameters resets policy memory. `max_history` defaults to 1,000 when enabled;
exceeding it fails the round atomically. This is an observation log, not a claim
that current ballots are unchanged since a past observation. The reported world
count is for the **current snapshot**, not all possible historical trajectories.

The logical world count is `(m!)^(N-1) * P(m,k)^U`, where U is the number of
unobserved other ballots, **without a signal constraint**. Since plurality depends only on first choices, voting
calculations group worlds with the same other first-choice profile; this preserves
all four reported decision properties. The cap applies to the full logical count,
before grouping. `max_worlds` defaults to 10,000 and is limited to 1,000,000;
exceeding it fails the round without commit. This exponential model is intended
for explicit tiny verification, not normal N>=100/m>=2 outcome simulations.

Configure one of `epistemic_dere`, `epistemic_dominant`, or
`epistemic_pessimistic`, explicitly grant roster observation, and optionally
grant public/private trusted sensing. Candidate ties follow private ranking;
pessimistic responses first maximize the worst winner. Without a justified action,
the entire existing ballot is retained. Decisions/observations are stored in
policy memory for inspector, checkpoint replay and exports. Changing heuristic
does not grant capabilities. These simultaneous-response policies have **no
convergence certificate** and are not part of the certified shortlist.

### Bounded public signals

`epistemic_signal_dere`, `epistemic_signal_dominant` and
`epistemic_signal_pessimistic` require `observe_electorate`,
`observe_public_signal`, a configured signal controller, and integer voting
parameter `signal_distortion_bound`. The declared bound must be at least the
controller's maximum possible transfer cost: zero for truthful reports or one
party, otherwise `min(per_broadcast_budget, lifetime_budget, N)`. Validation uses
configuration, never hidden source truth or realized cost. Too-small bounds,
missing permissions and incompatible mid-run overrides fail atomically.

In voting round t, if the signal's source is the completed round t-1, retain
exactly profiles whose total counts differ from the report by at most twice the
declared bound in L1 distance. Trusted current ballot sensors and own ballot also
constrain the same profile. The report itself is not asserted truthful. If its
source is older, it adds **no current-ballot constraint**: no transition model
links the old report to now. Trace `signal.use` distinguishes the two cases;
observation history records only report, provenance and declared bound.

For U unknown other ballots, every compatible first-choice assignment represents
`(m!)^(N-1) * P(m-1,k-1)^U` logical worlds. Exact multiplicities are counted even
when multiple assignments share an outcome-equivalent score vector. The full
logical count must fit `max_worlds`; score search also has a hard 1,000,000-node
limit. Contradictory evidence, limits and malformed reports fail without a partial
decision. Neither limits nor the compatible-world model establish convergence.

## Verification and limitations

[Tests](../tests/test_epistemic.py) compare factored decisions with explicit
preference-and-ballot world enumeration, exercise de dicto without de re, false
announcements, nested knowledge, hidden-preference invariance, caps, permission
denials, verification CLI/HTTP sessions, edits and replay. Historical tiny-browser
checks predate the minimum population requirement. Conditional checking/solving is exact only for its stated finite,
ordinal plurality domain. Richer temporal knowledge, source-specific truthful
priors, other voting rules and richer adversarial temporal signal semantics remain future work;
no human-behaviour or election prediction claim.
