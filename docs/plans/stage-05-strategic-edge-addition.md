# 05: Strategic edges — mechanism 3

Proposed; inherits 04. [Gates](README.md).
References: survey S11, S15-S16.

## Deliverables

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

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Opt-in public-ballot campaign controller: none/random/recipient-outdegree heuristic, per-round and unique-lifetime budgets | [Example](../../examples/campaign-controller.toml), [tests](../../tests/test_campaign_controller.py): hand-worked edges/sensing, zero budget, cap failure, overlap exclusion, removal ledger, seeded random, v14 migration/v15 replay, CLI/HTTP/CSV | Existing campaign layer, movement, coalition, sensors and checkpoints retained; certified cases and incompatible prior comparison commands reject controllers | Evaluator-only exhaustive upper bound, matched policy comparisons, budget plot, full prior-stage gates and convergence research pending |
| 8 Nov 2026 | Campaign-controller regression | Full suite 223 pass; `python3 -S`: 220 pass, 3 optional-image skips; JS and convergence proof checker pass | Prior cases, graph layers and source provenance retained | Live browser interaction unverified; no optimality, efficacy or convergence claim |
| 8 Nov 2026 | Paired controller comparison + bounded one-round exhaustive oracle + spend chart | [Comparison tests](../../tests/test_campaign_comparison.py): stationary/moving motion pairing, actual spend, target deltas, replay and failures; [oracle tests](../../tests/test_campaign_exhaustive.py): every candidate subset checked against independently scheduled round-one actions; JS chart/markers | Same controller budgets/eligibility, existing coalition/network state and shared engine; full researcher trajectories retained | Oracle only one-round stationary/no-plugin domain; no adaptive multi-round bound, statistical efficacy claim or convergence proof; upstream gates/live browser remain open |
| 8 Nov 2026 | Comparison/oracle integration regression | Full suite 230 pass; `python3 -S`: 227 pass, 3 optional-image skips; JS and convergence proof checker pass | Prior controllers, coalition scenarios and checkpoint histories retained | Live browser interaction, multi-round evaluator, full statistical studies and stage gates remain open |
