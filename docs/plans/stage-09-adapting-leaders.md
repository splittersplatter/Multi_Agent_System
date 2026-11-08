# 09: Adapting leaders — mechanism 7

Partly implemented; acceptance open; inherits 08. [Gates](README.md).
References: survey S22, S30.

## Deliverables

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

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Bounded leader feedback, signals, perceptions and controls | [Example](../../examples/leader-adaptation.toml), [contract](../simulator-guide.md#hidden-leader-adaptation), [tests](../../tests/test_leaders.py): public-score-only feedback, signal RNG, budgets, no-signal noninterference, checkpoint/CSV, fixed controls and honest-adaptation detector calibration | Prior nomination, own ideals, scoped attacks, detector and ordinal APIs retained; attack targets prior perception, not hidden truth | Formal evaluation, confidence intervals, stage/shared gates and live browser verification pending; uncertified dynamics |
| 8 Nov 2026 | Leader integration regression | Full suite 304 pass; `python3 -S`: 300 pass + 4 optional-image skips; proof checker, playback harness and `git diff --check` pass; checkpoint v21 verifies leader history | All prior checkpoints/certified cases retained; all-enabled HTTP, replay/rewind and GIF tests pass | Formal studies, all shared gates and live browser interaction remain open |
