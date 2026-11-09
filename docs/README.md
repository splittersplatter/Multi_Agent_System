# Documentation

Updated 9 November 2026. [Quickstart](../README.md#run).

## Current state

- Shared engine: ranked ballots/plurality; strategic and bounded epistemic policies;
  movement/graphs; coalition abilities; campaign edges; public signals; nomination;
  voter/leader shifts; aggregate detector; browser editing; exports/replay.
- `--save-states`: streamed per-round node/graph/inspector snapshots; `view --latest`
  opens read-only browser playback with timeline scrubbing and agent details.
- Normal simulations **N>=100**; demo200. Tiny formal/unit/regression fixtures
  require explicit verification scope. No silent electorate padding.
- Rolling-majority estimator: unique recent contacts; demo K10, public completed
  tally every10 rounds and linear 1.0→0.1 poll weight between updates. Estimates
  are beliefs; `memory_pivotal` can use them to choose a ballot.
- Default random-walk motion: Gaussian lengths, demo mean0.025/std0.00625/cap0.05;
  stationary remains explicit; uniform is an explicit compatibility option.
- Grid runtime retired; use `examples/gaussian-memory.toml`. Frequency diagnostics,
  CLI/browser/replay/plots/state recording retained. Checkpoint25 records resolved
  defaults; retired grid inputs fail explicitly. Grid proof/checker is historical,
  not applicable to Gaussian motion. Quietness/mixing/occupation remain uncertified.
- Stage00 baseline contract complete; Stage01 acceptance open; Stages02–10 partly
  implemented; Stage11 formal evaluation/delivery pending. Source presence != stage acceptance.
- F1–F5 certify restricted compositions only. `memory_pivotal` is implemented for
  exploratory runs; its original unrestricted-size contract has a cycle and the
  N>=100 domain remains uncertified. Certification is optional for labelled
  finite-horizon studies and mandatory for convergence claims.
- Latest code checks and exploratory200-person CLI/HTTP/replay evidence:
  [status](implementation-status-report.md). Manual200-node rendering/performance
  remains unmeasured.

## Use and engineering

| Document | Purpose |
| --- | --- |
| [Simulator guide](simulator-guide.md) | Commands, configuration, phase order, capabilities, mechanisms, plugins, UI |
| [Voting policies](voting-heuristics.md) | Exact implemented rules, parameters, source departures, limitations |
| [Epistemic voting](epistemic-voting.md) | Finite worlds, knowledge, conditional equilibrium, computation limits |
| [Majority estimator](recent-encounter-majority.md) | Observation/cache semantics and pilot commands |
| [Architecture](code-audit-and-refinement-report.md) | Ownership, invariants, unresolved engineering risks |
| [Estimator results](majority-estimation-report.md) | Dated exploratory200-person pilot; no superiority/convergence claim |
| [Memory-pivotal exploration](memory-pivotal-exploration.md) | Exact response contract, five-seed pilot, tests and limitations |
| [Gaussian long-horizon study](gaussian-long-horizon-study.md) | Three initializations, matched controls, figures and exploratory results |
| [Historical evidence](history/README.md) | Prior heuristic checks and workload measurements; not current-source claims |
| [Scenario studies (suchit-sims)](suchit_sims/README.md) | Watchdog, foreign intelligence, long-term propaganda, echo-chamber campaigns: reports, figures, GIFs, slides |
| [MARL interface](marl-interface.md) | `movement = "external"`, `Simulation.step(external_moves=...)`, `MovementEnv` |
| [suchit-sims change log](suchit-sims-changes.md) | Everything added on the branch, merge notes and caveats |
| [Set up and Watch pages](frontend-redesign/README.md) | Click-to-build experiments with exact import/export, and the new watch view (hearing ranges, ego networks, many charts, bulk edits) |

## Research and planning

| Document | Purpose |
| --- | --- |
| [Roadmap](project-roadmap.md) / [stage plans](plans/README.md) | Scope, dependencies, deliverables and remaining gates |
| [Research plan](plans/research-improvement.md) | Exploratory/certified tracks and strategic-voter contract |
| [Memory-voting dossier](memory-voting-convergence.md) | Candidate contract, original counterexample and domain limits |
| [Convergence foundation](convergence-foundations.md) | Guarded F1–F5 proofs and implementation obligations |
| [Moving-network stability](dynamic-network-stability.md) | Normal walk;24-work evidence matrix; future-contact proof limits |
| [Historical grid contract](plans/stochastic-stability.md) | Retired model/proof; not a Gaussian guarantee |
| [Stochastic verification](stochastic-stability-verification.md) | Formal/runtime checks, reviews, streaming commands and remaining limits |
| [Full-model dossier](heuristic-convergence.md) | Why unrestricted guarantees fail |
| [Candidate/evaluation plan](plans/heuristic-evaluation.md) | Role-specific eligibility and experiment contract |
| [Metric dictionary](heuristic-evaluation-metrics.md) | Formulas/undefined cases; specification, not all runtime metrics |
| [Literature survey](election-manipulation-literature-survey.md) | Seven-mechanism coverage/gaps; targeted, not systematic |
| [Full-text method audit](literature-heuristics-and-metrics.md) |31 works/36 PDFs; page evidence, algorithms and metrics |
| [Local references](../References/README.md) | Version inventory, hashes, access/interpretation limits |

References and generated `outputs/` are local/ignored; sharing this repository
does not include them. Historical source hashes identify collection-time code only.

Maintenance: obsolete deleted-code API map removed; useful verification/benchmark
records moved to history; stale small-outcome commands and repeated status dumps retired.
[Cleanup evidence](plans/code-quality-refinement.md#progress).
