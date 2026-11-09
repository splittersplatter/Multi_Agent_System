# Gaussian movement: long-horizon exploratory study

9 November 2026. Three 200-person configurations, including two spatial initializations;
three paired movement seeds;
1,000 rounds; memory-pivotal versus sincere control. Results are simulated
outcomes for the specified electorate, not predictions of actual elections.

## Presentation figures

- [Last 100 rounds: all scenarios and seeds](../outputs/gaussian-presentation-20261109/last-100-vote-shares.svg)
- Seed 2000 vote-share trajectories: [mixed](../outputs/gaussian-presentation-20261109/mixed-baseline-2000-vote-shares.svg), [clustered](../outputs/gaussian-presentation-20261109/clustered-baseline-2000-vote-shares.svg), [biased poll](../outputs/gaussian-presentation-20261109/biased-poll-baseline-2000-vote-shares.svg). These are selected runs, not averages.

## What the runs show

| Scenario | Strategic final winner, seeds 2000 / 2001 / 2002 | Strategic switches over 1,000 rounds | Sincere final winner |
| --- | --- | --- | --- |
| Mixed | A / B / B | 103 / 105 / 119 | A / A / A |
| Clustered | B / B / A | 135 / 117 / 152 | A / A / A |
| Biased initial poll | B / A / A | 80 / 74 / 136 | A / A / A |

- **Movement seed mattered in this close election.** The mixed strategic case
  ended with A for seed 2000 and B for 2001 and 2002. These are three outcomes,
  not estimates of election probabilities. The sincere result is an exact
  A/B tie resolved by configured party order.
- **Initial information changed paths.** The biased-poll and mixed cases share
  positions, rankings and keyed movement draws; their final winners differ for
  all three matched seeds. The biased poll is `[55,25,20]` versus `[34,33,33]`;
  both are replaced by the truthful completed round-10 tally. This demonstrates
  path dependence in this implementation, not a general causal effect size.
- **Initial geography mattered in two of three pairs.** Clustered and mixed
  scenarios share rankings, poll, and keyed motion draws but start at different
  positions. Final winners differ for seeds 2000 and 2002. Boundary reflection
  means physical trajectories and contact histories differ; this is an
  initialization comparison, not a controlled estimate of a network mechanism.
- **Ballots were quiet while contacts changed.** All nine strategic runs had
  zero flips in rounds 901–1000, with approximately 252–292 directed contact
  additions per round. This is observed quietness only: changing future contacts
  can still trigger voting changes. It proves neither mixing nor convergence.
- Several final outcomes are extremely close: seed-2000 mixed and seed-2002
  clustered finish 100–100 between their leading candidates; party order picks
  A. Strategic concentration around two candidates should be treated as a
  property to investigate, not evidence of a generally realistic election.

## Protocol and files

- Configurations: [mixed](../examples/presentation/mixed.toml),
  [clustered](../examples/presentation/clustered.toml),
  [biased poll](../examples/presentation/biased-poll.toml). Shared voter IDs,
  strict rankings and initial sincere votes: A=67, B=67, C=66. Configs use
  deterministic initialization seed 8192. Clustered assigns x-coordinates to
  party-specific thirds; mixed and biased-poll share positions exactly.
- Gaussian length mean .025, standard deviation .00625, cap .05; reflective
  boundaries; radius .12; 10-round unique-neighbour memory; truthful tally every
  10 rounds; simultaneous decisions. Seeds 2000–2002 are paired across cases and
  the sincere control. Paired strategic/control runs have identical per-round
  contact additions and removals.
- 18/18 runs completed. Each records all 1,000 per-round aggregate observations,
  a JSON summary, scenario/source hashes, command and log. The retained summaries
  use rounds 201–1000; last-100 statistics use 901–1000. Counts of switches are
  summed individual ballot changes; repeated changes by one voter count again.
  Contact additions count directed arcs, not distinct people or undirected links.
- [Protocol](../outputs/gaussian-presentation-20261109/protocol.json),
  [validated per-run summary](../outputs/gaussian-presentation-20261109/reviewed-summary.json),
  [raw artifacts directory](../outputs/gaussian-presentation-20261109/).
  Generated artifacts are local and ignored by Git; copy this directory to share it.
- A separate [200-round recording](../outputs/gaussian-presentation-20261109/outputs/frequencies-20261109T090716-172705Z-states.jsonl)
  contains all frames for mixed/strategic/seed2000. Its aggregate rows match the
  first 200 rows of the long run. The 1,000-round runs store aggregate rows, not
  per-node states. Full state histories are much larger; this recording is 111 MB
  and browser playback loads it into memory.

From the repository root, view the recording:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli view outputs/gaussian-presentation-20261109/outputs/frequencies-20261109T090716-172705Z-states.jsonl --port 8000
```

Reproduce the 18 runs to a **new** output directory and validate the raw rows:

```bash
python3 scripts/gaussian_presentation_study.py --output-dir outputs/gaussian-presentation-repeat --rounds 1000 --workers 3
python3 scripts/summarize_gaussian_presentation.py outputs/gaussian-presentation-repeat
```

The saved configuration and source hashes permit comparison, but exact replay
requires the recorded software environment. Three seeds and a single designed
electorate are insufficient for formal method selection; use the existing
held-out ≥30-seed protocol and vary electorates before generalizing.

## Validation

Complete consecutive CSV rounds, normalized shares, one winner per round,
JSON/CSV means and matched control contact counts were checked. The 200-round
recording loaded as 201 frames including round zero, and its raw aggregate prefix
matched the long run. The SVG summary was opened in the browser and its labels
checked. No stationarity or equilibrium test was performed.
