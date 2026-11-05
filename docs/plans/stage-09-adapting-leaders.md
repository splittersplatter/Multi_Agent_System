# 09: Adapting leaders — mechanism 7

Proposed; inherits 08. [Gates](README.md).
References: survey S22, S30.

## Deliverables

- [ ] Separate true leader alignment, public behavior signal, perceived alignment,
  evaluator utility. Isolated: preselected leaders; combined: fixed nominees.
- [ ] Bounded vote-seeking heuristic from permitted public history; finite local
  candidate moves + no-op; deterministic ties; no hidden voter-ideal centroid.
- [ ] Per-round displacement + episode path caps; declared noise distribution
  and perception-update rule; separate signal RNG/checkpointed perceptions.
- [ ] Controls: fixed leaders, adaptation+signals, adaptation without signals.
  No-signal: identical frozen perceptions, no truth-derived ranking/feedback leak.
- [ ] True/perceived trajectories; perception error, support/compatibility/cost;
  detective false alarms under honest adaptation.

## Acceptance

Ordinal model retains own-ranking knowledge. Spatial adapter exposes own ideal,
not latent true distance-ranking when leader positions hidden.
Bounds, signal/perception replay, fixed-leader equivalence.
No-signal adaptation preserves ballots/outcomes with other processes fixed;
evaluator utility may differ. Voter ideals and leader adaptation remain separate.
Cumulative run: all seven available; retain isolated controls/UI/plots/checkpoints.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
