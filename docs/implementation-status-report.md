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
- Current checkpoints use25, with explicit resolved Gaussian group parameters.
  Legacy non-grid group kernels are pinned before replay; ambiguous implicit
  overrides require the archived runtime. Retired grid inputs fail explicitly.
  Earlier supported schemas require successful replay; reviewed environment/source
  changes require explicit migration approval. No fabricated legacy compatibility.
- Estimates alone do not manipulate ballots. Opt-in `memory_pivotal` uses them
  for exploratory simultaneous response and records decision traces.
  F1–F5 guarantees apply only inside guarded proof domains; moving/mixed/continuing
  attacker compositions are not certified by a quiet winner/ballot window.
- Default random-walk kernel is Gaussian (mean=cap/2, std=cap/8 unless configured).
  Grid runtime removed; Gaussian memory-pivotal preset replaces it. Streaming
  frequencies/phase summaries, plots, states and playback remain available.
  [Historical grid proof](plans/stochastic-stability.md) does not certify this model.

## Verification

Latest Gaussian-default update,9 November:427 full-suite tests pass
(`/tmp/eclipse-gaussian-final.log`);20 Gaussian integration tests pass under
stdlib-only Python (`/tmp/eclipse-gaussian-stdlib.log`); JS playback harness and
`git diff --check` pass. Retired grid correspondence tests replaced with Gaussian
runtime/replay/bounds/HTTP/rejection checks; standalone historical proof tests retained.
New checkpoint25 and diagnostics2 distinguish current contracts. Legacy uniform
group replay, implicit normal parameters, ambiguous overrides, control matching,
99/100/101 boundary, rewind/tamper and state playback covered.

200-voter/30-round CLI smoke, seed2000, completed; JSON/CSV/SVG plus31 saved frames
validated through playback loader:
`outputs/frequencies-20261109T085404-432726Z*`.
Command: `PYTHONPATH=src python3 -m multi_agent_election.cli frequencies examples/gaussian-memory.toml --rounds 30 --burn-in 0 --batch-size 10 --seed 2000 --save-plots --save-states`.
Validation only, not mixing evidence or a research comparison. Prior plot/state/
browser integration preserved; cache10, poll10 and ballot policy unchanged.

Historical state-recording/playback extension,9 November:427 tests pass;8 focused
state tests pass under stdlib-only Python; JS playback harness passes. Streamed
frames match engine outcomes, browser rewinds replace future records, I/O failure
blocks round commit, malformed recordings fail validation. Actual200-node saved
timeline inspected in-browser across rounds0/12/11. See
[recording contract and commands](simulator-guide.md#setup-and-commands).

Earlier recorded code checks,9 November2026:

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
- Gaussian mixing/occupation guarantees: open; retired grid theorem cannot apply.
  Measure contact coverage, autocorrelation and seed sensitivity before claiming
  improved mixing. Finite-window agreement is not a convergence certificate.
- Frozen calibration/evaluation protocol,>=30 held-out seeds/cell, run-level
  uncertainty; native intervention costs; failures/censoring retained.
- Bounded dense-graph/history resources, expensive-policy limits, trusted-plugin
  dependency/environment closure. No current universal performance guarantee.
