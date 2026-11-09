# 04: Adversarial minorities — mechanism 2

Partly implemented; acceptance open; inherits 03. [Gates](README.md).
References: survey S8, S11, S16-S18, S21, S27.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [ ] Coalition ID/membership/target fixed before outcome sampling; separate
  per-round/episode capability budgets.
- [ ] Sight: scoped target preferences. Coordination: private channel.
  Deception: false reports, not altered cast ballots.
  Eavesdropping: expanded private sensing, not public edges.
- [ ] Report-only channels for deception; trusted ballot sensors separate controls.
- [ ] Sincere, public-tactical and bounded coalition heuristics; no optimality claim.
- [ ] Individual capability ablations + combined case; fixed coalition/targets/
  exogenous draws; report allowed and realized costs in separate units.
- [ ] Group presets; sender/receiver/timestamp report logs; budget plots; memory checkpoints.

## Acceptance

No unauthorized sight/private traffic; sensing leaves public graph unchanged;
cast ballots remain valid; disabled-capability observation equivalence; message delay/caps;
shared policy-memory replay/rewind. Coordination does not imply common knowledge.
Cumulative case: moving network + coalition; attribute target-support changes by capability.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Deception, sight, private-report interception, fusion and six-arm ablations
implemented (`test_coalition_*.py`). Remaining: adaptive selection, complete rejected-action
ledger, budget visualization acceptance and certified/reproducible outcome studies.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
