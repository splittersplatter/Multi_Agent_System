# Stage plans

Status: Stage 00 verified; Stage 01 in progress; later stages pending.
Load [roadmap](../project-roadmap.md), this file, and only the active stage.
Current workspace: [current state](../README.md#current-state).

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

- Dependency: preceding stage; retain its APIs, scenarios, evidence and unresolved limits.
- Implement only when requested; one shared engine, not separate prototypes.
- Extend CLI, browser, metrics, exports, checkpoints and docs for new state.
- Verify hand-worked expected outputs, bounds, permissions, zero/disabled equivalence, replay/resume.
- Run new + earlier features together; preserve isolated mechanism scenarios.
- Controls share electorate/exogenous RNG streams; seed alone insufficient.
- Deliver scenario config, command/seed, expected results, artifact paths; generated data outside source.
- Correctness failures block dependents; carry limitations forward.
- Store status, validation, setup and decisions in each stage's progress table;
  update [current state](../README.md#current-state); retain previous evidence.

## Progress

Unchecked = proposed. Each completed item needs command/artifact + observed result;
implemented != verified. Append dated integration evidence; preserve previous completed work.

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
