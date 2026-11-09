# 02: Information / epistemic reasoning

Partly implemented; acceptance open; inherits 01. [Gates](README.md).
References: survey S1-S3, S6, S9-S10, S12-S13.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [ ] Actor access matrix: visible fields, local/public reports, private channels,
  timestamps/provenance; researcher truth excluded.
- [ ] Permission-scoped observation builder; explicit sight/sensing capabilities.
- [ ] Finite models: preferences, ballots, signal possibilities, history;
  actual world retained; misleading claims never factual announcements.
- [ ] Integrate de re/de dicto/pessimistic checks; log information set, candidate
  action and decision/tie criterion; unsupported improvement -> retain ballot.
- [ ] Poll-confident baseline + sincere/epistemic comparisons; paper mapping:
  reproduced assumptions versus departures.
- [ ] Inspector/trace/checkpoint support for observations, information sets and decisions.

## Acceptance

Enumeration matches exact checks; own-ranking knowledge/factivity; false-announcement
rejection; hidden changes preserving observations cannot change decisions given same
policy memory/RNG. Enforce enumeration limit; sampled/heuristic conclusions labelled approximate.
Replay information sets after rewind. Cumulative scenario: movement/channels + sincere,
poll-confident and epistemic policies; compare decisions and outcomes.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Scoped observations, report provenance, finite models, conditional equilibrium,
strategic variants and passive encounter cache implemented. Evidence: `test_epistemic.py`,
`test_epistemic_signal.py`, `test_voting_verification.py`, `test_majority.py`.
Remaining: temporal/higher-order models and scalable exact reasoning; full-world
caps prevent ordinary N>=100/m>=2 epistemic runs. `memory_pivotal` is implemented
for exploratory runs; convergence claims remain proof-gated.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
