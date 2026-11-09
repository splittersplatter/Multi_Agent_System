# Stage plans

Status: Stage 00 verified; Stage 01 acceptance open; Stages 02–10 partly implemented;
Stage 11 pending. [Code refinement](code-quality-refinement.md).
Load [roadmap](../project-roadmap.md), this file, and only the active stage.
Current workspace: [current state](../README.md#current-state).

[Research roadmap](research-improvement.md): `memory_pivotal` is implemented for
exploration. Its [counterexample](../memory-voting-convergence.md) refutes the
original size-unrestricted guarantee; N>=100 remains uncertified. Proof is required
for certified claims, optional for labelled finite-horizon experiments.

[Recent-encounter majority extension](recent-encounter-majority.md): passive,
opt-in estimate; used by `memory_pivotal` and independently inspectable.

[Heuristic audit/evaluation plan](heuristic-evaluation.md): role-specific candidates,
metrics and convergence gate. Original size-unrestricted full-model absorption refuted; scope
now follows [confirmed restricted cases](../convergence-foundations.md).
F1–F3 engine certification and scheduled F4/F5 implemented; comparative experiments
and later stage gates pending. This is not a new completed stage.

[Stochastic stability](stochastic-stability.md): selected long-run occupation target;
24-work audit, finite-grid transition contract and conditional mathematical proof
draft plus [exact tiny-model checks](../stochastic-stability-verification.md).
Independent analytic review passed; [implementation](stochastic-stability-implementation.md)
completed: opt-in grid, guards, replay/browser/export and streaming diagnostics.
Current F1–F5/continuous defaults unchanged; full outcome evaluation pending.

| Stage | Plan |
| --- | --- |
| 00 | [Baseline/scope](stage-00-baseline-and-scope.md) |
| 01 | [Political simulator](stage-01-political-simulator.md) |
| 02 | [Information/epistemics](stage-02-information-and-epistemic-reasoning.md) |
| 03 | [Dynamic proximity](stage-03-dynamic-proximity-networks.md) |
| 04 | [Adversarial minorities](stage-04-adversarial-minorities.md) |
| 05 | [Strategic edges](stage-05-strategic-edge-addition.md) |
| 06 | [Public signals](stage-06-public-signal-manipulation.md) |
| 07 | [Nomination/alignment](stage-07-nomination-and-alignment.md) |
| 08 | [Alignment attacks/detectives](stage-08-alignment-attacks-and-detectives.md) |
| 09 | [Adapting leaders](stage-09-adapting-leaders.md) |
| 10 | [Combined system](stage-10-combined-system.md) |
| 11 | [Experiments/delivery](stage-11-experiments-and-delivery.md) |

## Shared gates

- All outcome simulations/demos/pilots/benchmarks N>=100; default demo200.
  [Shared population guard](minimum-population.md); tiny fixtures explicitly verification-only.
- Dependency: preceding stage; retain its APIs, scenarios, evidence and unresolved limits.
- Implement only when requested; one shared engine, not separate prototypes.
- Extend CLI, browser, metrics, exports, checkpoints and docs for new state.
- Verify hand-worked expected outputs, bounds, permissions, zero/disabled equivalence, replay/resume.
- Run new + earlier features together; preserve isolated mechanism scenarios.
- Controls share electorate/exogenous RNG streams; seed alone insufficient.
- Deliver scenario config, command/seed, expected results, artifact paths; generated data outside source.
- Correctness failures block dependents; carry limitations forward.
- Keep stage status/remaining deliverables current; link [central verification](../implementation-status-report.md#verification).
  Preserve unique findings/artifacts in [history](../history/README.md); remove superseded test-count dumps.

## Progress

9 November: population floor integrated; current engine verification centralized;
all stage plans reconciled with implemented subsets and remaining gates.
Documentation-only cleanup preserves research/proof evidence, retires broken
small-outcome commands and obsolete deleted-code APIs. No new model/experiments.
[Maintenance acceptance](code-quality-refinement.md).

Later9 November: user authorized exploratory `memory_pivotal` without requiring
convergence. Shared engine/CLI/browser/replay implemented; five-seed exploratory
comparison and [verification](../memory-pivotal-exploration.md). Proof remains
mandatory only for certified-convergence claims.

Later9 November: statistical target distinguished from ballot absorption and
per-round distributional convergence.24-work audit:22 accessible full texts
(one scanned model inspected visually),2 full-text blockers. Startup flag retained
in finite-state quotient; no runtime code, experiments or new certificate.

Later9 November: formal grid checker/exact class analysis and18 adversarial
tests added;8 declared cases complete, no resource cutoff. Independent review
still gates the separate runtime implementation plan. [Evidence](../stochastic-stability-verification.md).

Subsequent execution: independent review passed; runtime integration completed.
414 tests pass, stdlib410/4 skips;32 fixture replay checks; review defects fixed.
No infinite seeded-path guarantee or full evaluation campaign claimed.
