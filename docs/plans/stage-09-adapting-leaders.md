# 09: Adapting leaders — mechanism 7

Partly implemented; acceptance open; inherits 08. [Gates](README.md).
References: survey S22, S30.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [x] Separate true leader alignment, public behavior signal, perceived alignment,
  evaluator utility. Isolated: preselected leaders; combined: fixed nominees.
- [x] Bounded vote-seeking heuristic from permitted public history; finite local
  candidate moves + no-op; deterministic ties; no hidden voter-ideal centroid.
- [x] Per-round displacement + episode path caps; declared noise distribution
  and perception-update rule; separate signal RNG/checkpointed perceptions.
- [x] Controls: fixed leaders, adaptation+signals, adaptation without signals.
  No-signal: identical frozen perceptions, no truth-derived ranking/feedback leak.
- [x] True/perceived trajectories; perception error, support/compatibility/cost;
  detective false alarms under honest adaptation.

## Acceptance

Ordinal model retains own-ranking knowledge. Spatial adapter exposes own ideal,
not latent true distance-ranking when leader positions hidden.
Bounds, signal/perception replay, fixed-leader equivalence.
No-signal adaptation preserves ballots/outcomes with other processes fixed;
evaluator utility may differ. Voter ideals and leader adaptation remain separate.
Cumulative run: all seven available; retain isolated controls/UI/plots/checkpoints.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Hidden adaptation, noisy signals, separate perceptions/budgets and matched
fixed/no-signal controls implemented (`test_leaders.py`). Remaining: broader
strategies, manual acceptance and certified/statistically evaluated compositions.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
