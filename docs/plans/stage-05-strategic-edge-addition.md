# 05: Strategic edges — mechanism 3

Partly implemented; acceptance open; inherits 04. [Gates](README.md).
References: survey S11, S15-S16.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [ ] Controller access matrix; target-win/share objective; observable edge-selection inputs.
- [ ] Persistent campaign overlay; lifetime budget of unique directed edges;
  symmetric link costs two. Reject self/already-effective edges; no duplicate cost/weight.
- [ ] No-addition, random eligible additions, bounded target heuristic.
  Exhaustive tiny-case edge search: evaluator-only upper bound under matching dynamics.
- [ ] Static then moving-network comparisons; log eligible/proposed/accepted edges and realized costs.
- [ ] Layer/budget inspector; annotated plots; target/share/exposure/switching/cycle metrics.

## Acceptance

Zero-budget equivalence; exhaustion/infeasible actions; layer overlap/deduplicated
observations; campaign link survives proximity expiry; deterministic selection/replay.
Convergence/target victory measured, not guaranteed.
Cumulative run: moving graph + coalition + campaign links; scoped permissions;
Inspector distinguishes inserted versus proximity edges.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Budgeted controller, none/random/outdegree heuristic, paired comparisons and
spend chart implemented (`test_campaign_*.py`). Exact one-round oracle is <=8-voter
verification-only; no normal N>=100 oracle workload. Remaining: source algorithms,
multi-round bounds, manual acceptance and approved comparative research.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
