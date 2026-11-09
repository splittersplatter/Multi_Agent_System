# Implementation status

Updated 9 November 2026. [Quickstart](../README.md#run) · [Architecture](code-audit-and-refinement-report.md).
Implemented != accepted stage != validated scientific result.

## Scope

| Area | Implemented | Remaining |
| --- | --- | --- |
| Stage00 | Baseline/phase/information/reproducibility contracts | Maintain against adopted scope |
| Stage01 | Repeated engine; groups/capabilities; ranked ballots; motion/layers; plugins; CLI/HTTP; editing; history; plots/GIFs | Full manual browser/download acceptance; current workload/resource limits |
| Stage02 | Scoped observations/provenance; strategic variants; finite knowledge; conditional equilibria; rolling estimates; exploratory memory-pivotal voter | General temporal/higher-order/adversarial models; convergence proof for memory voter |
| Stage03 | Receiver radii; dynamic/frozen/calibrated static proximity; normal-step motion; turnover/exposure/reactivation metrics | Held-out controls; causal studies; future-contact certification |
| Stage04 | Coalition sight, private coordination, false reports/interception; capability ablations | Adaptive selection, complete rejected-action ledger, research comparisons |
| Stage05 | Budgeted campaign layer; none/random/outdegree heuristic; paired controls; exact one-round oracle | Multi-round bound and source-algorithm replications |
| Stage06 | Bounded truthful/random/target signals; trusting/known-bound epistemic responses; paired controls | Temporal signal semantics; paper replication and evaluation |
| Stage07 | Spatial nomination; fixed/random controls; representation distances | Broader composition studies |
| Stage08 | Bounded ideal shifts/drift; passive aggregate detector; disjoint calibration | Held-out uncertainty/generalization and composition certification |
| Stage09 | Hidden leader shifts; public signals/perceptions; fixed/no-signal controls | Broader strategies and certified compositions |
| Stage10 | All-enabled integration;17-arm isolated/leave-one-out/detector-off matrix | Cross-feature rejection audit/manual acceptance; factorial interactions |
| Stage11 | Plans, metric contracts, experiment utilities | Frozen protocol, approved studies, uncertainty, final report/package |

## Current contracts

- All normal simulations N>=100;200-person browser demo. Older small examples
  remain fixtures and ordinary CLI rejects them. Explicit verification scope only.
- Ballots contain exactly global k distinct candidates; tally uses first-choice
  plurality with configured party-order ties. Own rankings, cast votes, reports,
  public signals and perceived positions are separate.
- One engine powers CLI/browser/replay/export. Timeline reads do not execute
  policies; edits replace future history. Plugins are trusted, not sandboxed.
- Periodic majority polls use checkpoint23; fixed-poll estimates use22; disabled
  state retains21.
  Earlier supported schemas require successful replay; reviewed environment/source
  changes require explicit migration approval. No fabricated legacy compatibility.
- Estimates alone do not manipulate ballots. Opt-in `memory_pivotal` uses them
  for exploratory simultaneous response and records decision traces.
  F1–F5 guarantees apply only inside guarded proof domains; moving/mixed/continuing
  attacker compositions are not certified by a quiet winner/ballot window.
- Statistical follow-up is [specified, not implemented](plans/stochastic-stability.md):
  finite-grid occupation-frequency proof draft. Current continuous engine has no
  new stationary-law/absorption certificate; literature or proof text is not code acceptance.

## Verification

Latest recorded code checks,9 November2026:

| Check | Result / local evidence |
| --- | --- |
| Full unittest suite |380 pass; `outputs/normal-walk-verified-tests.log` |
| Standard-library-only suite |376 pass/4 optional-image skips; `outputs/normal-walk-verified-stdlib.log` |
| Population boundary/integration |9 tests;99 rejected,100/101 accepted; CLI/pilot/checkpoint/environment/HTTP200 checked |
| Normal CLI demo |100 rounds,101 metrics rows,200 ballots each; `outputs/population-demo-200-summary-2026-11-09.json` |
| Fixture replay/next round |31/31; `outputs/population-audit-matched-2026-11-09.json`; only deliberately enlarged demo differs from prior matched audit |
| JS playback harness |Pass; `node tests/playback_harness.js` |

Latest normal-walk update: suites above, JS harness and `git diff --check` pass.
Normal draws/bounds, legacy draw identity,
replay/overrides, matched motion and quiet-then-contact restart covered.
200-voter seed101/100-round CLI comparison:2/2 successful arms; memory-pivotal22
flips including one restart after>=10 quiet rounds; sincere0. Raw/source manifests:
`outputs/normal-walk-comparison-2026-11-09.json`.
[Motion contract, findings and conditional proof](dynamic-network-stability.md).

Memory-pivotal oracle, 200-person HTTP/replay and exploratory runs are in
[its report](memory-pivotal-exploration.md). Raw logs and manifests are ignored
local evidence, not shipped test results.
Periodic-poll checks: round1/2/10/11/20/21 weights and source tallies, empty-cache
fallback, tamper/replay/rewind, periodic pilot controls and 200-person HTTP.
Estimator pilot:30 trajectories/240 arm evaluations, five seeds, zero failures;
[findings and limitations](majority-estimation-report.md). This is not heuristic selection.

Documentation follow-up,9 November:24-work stability matrix,22 accessible full
texts/2 access blockers; finite-grid transition/relative-age/startup contract and
conditional occupation proof. This update does not rerun or extend the code checks
above. Review and finite-model/engine equivalence are still pending; no outcome study.

## Open gates

- Current manual browser interaction/download bytes and200-node rendering/memory.
- Complete rejected/conflicting-action actor/phase/reason audit without corrupting state.
- Intended memory-voter convergence scope; original four-person refutation does
  not itself certify/refute the new N>=100-only domain.
- Independent review of the separate grid occupation theorem and its implementation
  obligations; only afterward create a simulator implementation plan. Time averages
  may converge while ballots flip forever or the per-round law remains periodic.
- Frozen calibration/evaluation protocol,>=30 held-out seeds/cell, run-level
  uncertainty; native intervention costs; failures/censoring retained.
- Bounded dense-graph/history resources, expensive-policy limits, trusted-plugin
  dependency/environment closure. No current universal performance guarantee.
