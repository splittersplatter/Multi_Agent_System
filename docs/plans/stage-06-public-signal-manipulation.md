# 06: Public signals — mechanism 4

Partly implemented; acceptance open; inherits 05. [Gates](README.md).
References: survey S12-S14; repeated/bounded manipulated polls already studied.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [x] True poll = last completed first-choice counts.
  Report: nonnegative integer vector, same total; cost = L1(true,report)/2.
  Separate per-broadcast and episode caps.
- [x] Truthful, bounded-random, target-biased policies; controller knows true
  aggregate, not private rankings without sight.
- [x] Initial-only/repeated schedules; record source-round/report-round; no uncast-ballot access.
- [ ] Matched sincere/poll-confident/epistemic responses; known-bound epistemic
  model retains compatible possibilities; trusting heuristic != factive knowledge.
- [ ] True/reported count plots, distortion curves, decision traces;
  hand-worked literature reproduction + assumption differences.

## Acceptance

Totals/integrality/both caps; zero-distortion equivalence; timing/ties/impossible
actions; no hidden truth in voter input; false announcements rejected.
Measure target wins/share/margin, distortion response, switching/cycles, realized costs.
Cumulative run: mobility + coalition reports + campaign edges + repeated polls;
separate provenance/budgets; replay/UI/exports.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Bounded broadcasts, trusting and known-bound epistemic responses,9-arm controls
implemented (`test_public_signal.py`, `test_epistemic_signal.py`, `test_signal_comparison.py`).
Known-bound full-world policies hit current caps at N>=100/m>=2; tooling is not a
validated production comparison. Remaining: temporal semantics, replication, scalability and research gates.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
