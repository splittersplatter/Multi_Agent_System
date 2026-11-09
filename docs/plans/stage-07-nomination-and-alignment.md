# 07: Nomination / alignment — mechanism 5

Partly implemented; acceptance open; inherits 06. [Gates](README.md).
References: survey S22-S23, S29-S30.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [x] Issue vectors in [0,1]^d; physical positions separate.
  Euclidean distance -> full ranking; party-order ties; ordinal-input adapter.
- [x] Implemented nomination: each person chooses closest eligible public neighbor/self;
  top m nomination counts win; stable ID ties including zero-count fill.
  Validate k <= m <= eligible population.
- [x] Nominate before round 0; stable leader/party mapping; fixed membership.
  Leaders remain single-vote people. Baseline leader positions public/fixed;
  voter ideals private.
- [x] Endogenous, identical-nominee exogenous, equal-size random-nominee controls; track composition.
- [x] Nomination ballots/counts/winners; leader badges; physical/issue views; representation-distance metrics.

## Acceptance

Dimensions/bounds/ties; self/isolated nomination; insufficient eligible people;
m=k; valid length-k ballots; stable IDs/replay; manual edits logged.
Same nominees + no nomination information effect -> equivalent voting.
Report selected IDs, representation distances and winner effects; representativeness measured.
Cumulative run: nominees + earlier network/coalition/edge/poll mechanisms;
CLI/browser/plots/checkpoints.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Nomination, spatial rankings, controls and representation metrics implemented
(`test_nomination.py`). Later stages separately implement voter shifts/leader
adaptation. Remaining: broader composition studies, manual acceptance and scientific gates.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
