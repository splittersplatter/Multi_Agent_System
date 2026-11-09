# 03: Dynamic proximity — mechanism 1

Partly implemented; acceptance open; inherits 02. [Gates](README.md).
References: survey S9-S12, S28-S29.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

- [ ] Extend existing mobility hooks: stationary/bounded random walk, per-group
  speed/radius, reproducible draws; physical != ideological space.
- [ ] Validate per-round proximity; preserve persistent/campaign/private layers.
- [ ] Controls: frozen initial graph, dynamic contacts, static degree/exposure-matched
  graph; report residual mismatch.
- [ ] Compare sincere/strategic outcomes, exposure and turnover:
  |E_t Δ E_previous| / |E_t ∪ E_previous|; empty union -> 0.
- [ ] Radius/layer overlays; round-indexed movement GIFs/contact plots; reproducible scheduled edits.

## Acceptance

Radius equality, reflection, coincident/isolated people; zero-movement static equivalence;
spatial-index/brute-force agreement; layer persistence; renderer matches engine.
Matched movement streams; no pure-turnover claim with uncontrolled exposure.
Cumulative run: prior policies/groups/messages + moving graph + replay/edit/export.

## Progress

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Dynamic/frozen/calibrated-static contacts, receiver radii, exposure/turnover and
radius overlays implemented (`test_network.py`). Remaining: held-out control
residuals, causal comparisons and manual UI/resource acceptance. Encounter cache
adds passive local beliefs, not a convergence or representativeness guarantee.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.

Later9 November: normal-length random walks added through shared motion parameters;
demo mean0.025/std0.00625/cap0.05. Legacy uniform walks retained. Replay/overrides,
distribution/bounds and quiet-then-contact reactivation checks added. Comparison
diagnostics/browser copy reject quietness-as-proof. [Research findings and conditional
moving-contact invariant](../dynamic-network-stability.md); no new runtime certificate.
[Verification evidence](../implementation-status-report.md#verification).

Later9 November documentation: [24-work stability audit](../dynamic-network-stability.md#24-work-evidence-matrix)
and [finite-grid occupation contract](stochastic-stability.md) added. Continuing
contacts allowed; poll-phase/startup/relative-age state retained. Analytic proof
draft only; grid implementation, independent review and code equivalence pending.
No experiment or additional implemented stage/certificate claimed.
