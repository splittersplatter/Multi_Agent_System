# Recent-encounter majority estimation

Opt-in, passive plurality estimator. No strategic ballot changes/convergence claim.
Stages 01–03 extension; retain existing modes, replay and cumulative evidence.

## Contract

- Explicit initial poll; `memory_rounds=10`, `poll_weight=0.5`; ballot length `k` unchanged.
- Demo: `poll_refresh_rounds=10`; publish completed tallies and use linear poll
  weights1.0→0.1, resetting after each publication. Fixed-weight mode remains.
- Round r: moved incoming proximity observes completed ballots r−1. No remote channels.
- One latest first choice/person; retain encounters `[r−K+1,r]`. IDs expire with votes.
- Ordered map + incremental counts; reads never refresh. Atomic immutable snapshots.
- Blend initial poll/recent distinct-person shares; empty cache uses poll; retain ties.
- Active state O(U+m); updates expected O(1)/record; snapshot copying O(U).
- Shared engine/CLI/browser/export/checkpoint; version23 periodic,22 fixed,21 disabled.
- `memory_pivotal` uses this state for exploratory strategic response; optional
  convergence proof applies only to certified claims.

## Delivery gates

1. Core/config/round state; exact expiry, tie and information-boundary tests.
2. Replay/rewind/browser/CSV/CLI integration; disabled fingerprints unchanged.
3. Matched pilot: 200 people, 3 parties, 100 rounds, seeds101–105;
   well-mixed/clustered/shift × stationary/moving; poll sample100.
4. Poll/current/window/blend controls; K5/10/20, w.25/.5/.75 one-factor sensitivity.
5. Raw predictions/configs/manifests; source-round truth; resource/accuracy report.

Formal selection: separate held-out ≥30-seed protocol. Moving finite-memory beliefs
can oscillate; certified adoption needs a separate full-model convergence proof.

## Progress

Implemented9 November: cache/config, shared CLI/HTTP/replay/exports and exploratory
pilot complete.24 estimator tests; current complete-suite evidence in
[status](../implementation-status-report.md#verification).
`outputs/majority-pilot-2026-11-09-final`:30 trajectories/240 arm evaluations,
zero failures; all60 trace/prediction artifacts identical to first pass.
[Results](../majority-estimation-report.md) retain accuracy/resource tradeoffs.

Current demo200; all normal runs N>=100. Later population guard changed runtime
hashes; prior pilot manifests refer to collection-time source. No convergence
selection or held-out robustness result. Later `memory_pivotal` uses
the estimate in exploratory runs; proof remains required for certified claims.

Later9 November: periodic completed-tally publications and linear poll weighting
implemented for the 200-person demo. Round10 tally first appears in round11;
checkpoint23; fixed-poll mode/old records preserved. Four adversarial schedule,
replay, validation and periodic-pilot tests; full373 pass, stdlib369 pass/4 skips.
200-person HTTP through round11, 21-round engine replay and 100-round CLI pass. Earlier
fixed-poll pilot evidence remains historical; updated simulation is uncertified.
