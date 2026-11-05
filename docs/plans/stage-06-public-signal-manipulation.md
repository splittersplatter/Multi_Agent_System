# 06: Public signals — mechanism 4

Proposed; inherits 05. [Gates](README.md).
References: survey S12-S14; repeated/bounded manipulated polls already studied.

## Deliverables

- [ ] True poll = last completed first-choice counts.
  Report: nonnegative integer vector, same total; cost = L1(true,report)/2.
  Separate per-broadcast and episode caps.
- [ ] Truthful, bounded-random, target-biased policies; controller knows true
  aggregate, not private rankings without sight.
- [ ] Initial-only/repeated schedules; record source-round/report-round; no uncast-ballot access.
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

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
