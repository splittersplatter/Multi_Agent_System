# Implementation audit / structural refinement

Date: 8 November 2026. Scope: current repository, roadmap 00–11.
Baseline: `ffaabed7b97b5351028bb8fe76d5d1a9b5e7105f`.
[Execution plan](plans/code-quality-refinement.md).

## Assessment

The project is a functioning cumulative research simulator. All seven proposed
mechanisms have executable implementations; stage acceptance and scientific
validation remain incomplete. Strongest areas: deterministic state, permission
boundaries, budget checks, independent voting oracles and replay. Main remaining
risks: orchestration complexity, partial UI acceptance, restricted scalability
evidence and unfinished research evaluation.

Passing tests establish the checked contracts, not complete correctness, model
realism, statistical superiority or unrestricted convergence. No line/branch
coverage percentage was measured.

## What exists and how well it is checked

| Roadmap area | Implemented | Evidence / assessment | Remaining |
| --- | --- | --- | --- |
| 00 baseline | Explicit model, source register, phase/control contracts | Hand-worked plurality and replay tests; specification verified | Earlier deleted implementation/checkpoints remain unavailable |
| 01 simulator | Ranked ballots; group/person policies; movement; four graph/channel layers; CLI/HTTP; edits; recording; plots/GIF | Extensive unit/integration tests; one shared engine; strongest implementation coverage | Browser download/manual acceptance; comprehensive performance gates; counting-rule adapter |
| 02 information | Scoped observations; finite knowledge worlds; truthful announcements; de re/de dicto, pessimistic/dominance responses; conditional equilibrium; provenance/history | Enumerated independent checks; factivity/leakage/cap/replay tests | General temporal belief dynamics and broad attacker epistemics |
| 03 proximity | Receiver-specific radii; dynamic/frozen/static contacts; calibration/evaluation controls; turnover/exposure metrics | Brute-force graph oracle and matched movement tests | Held-out degree/exposure equivalence is not guaranteed; broader sensitivity |
| 04 coalition | Budgeted sight, private coordination, deceptive reports, interception; six-arm controls | Permission/budget/timing/replay and capability ablation tests | Adaptive capability selection; complete rejected-action audit |
| 05 campaign | Directed purchased edges; zero/random/target heuristics; purchase ledger; one-round exact oracle | Budget/no-repurchase and exhaustive tiny-case checks | Multi-round optimality and broader campaign strategies |
| 06 public signal | Truthful/random/targeted bounded reports; trusting and known-bound epistemic responses; 3×3 controls | Conservation/bounds, information isolation and control tests | Temporal signal models; formal comparisons |
| 07 nomination | Spatial ideals; endogenous/fixed/random nominee sets; stable candidate IDs; representation distances | Hand-worked nomination, identical-nominee controls and replay | Broader electorate/topology/composition studies |
| 08 alignment/detector | Bounded directed/random voter shifts; natural drift; passive aggregate detector; disjoint-seed calibration | Path-cost/permission/censoring/false-alarm tests | Detector generalization; drift/adaptation sensitivity; final evaluation |
| 09 leaders | Bounded hidden leader adaptation; noisy public signals; perceived positions; four controls | No-signal noninterference, budget, hidden-state and replay tests | More realistic adaptive strategies; broad sensitivity |
| 10 combination | All-enabled scenario; 17-arm isolated/leave-one-out/detector-off matrix | Joint phase/budget tests; CLI/HTTP/CSV/GIF/replay checks | Comprehensive rejection/conflict ledger; manual browser acceptance |
| 11 research delivery | Plans, metric contracts and runnable comparison utilities | Infrastructure exists | Freeze hypotheses/seeds; pilots; held-out runs; uncertainty; publication/report package |

## Convergence foundation

F1 direct best response, F2 homogeneous source local dominance, F3 sequential
undirected conformity, and finite scheduled F4/F5 recovery protocols are
implemented under explicit guards. The independent proof checker exercises
111,490 F1 states, 4,704 F2 profile/radius cases and 127,758 F3 changing transitions.
It also checks negative controls. These finite checks support implementation
verification; the guarantee comes from each declared proof domain.

Mixed policies, simultaneous response, moving graphs and continuing adversarial
actions remain outside these certificates. Quiet ballots/winners do not certify
absorption. [Proof domains and commands](convergence-foundations.md).

## Findings and changes

| Finding | Effect | Resolution |
| --- | --- | --- |
| Ordinary `Scenario` dataclass replacements bypassed parser validation | Duplicate IDs silently reduced electorate size; invalid seeds/horizons/policies reached runtime; unknown groups could raise `KeyError` | All scenarios canonically revalidated before plugins or initial state; invalid input raises `ElectionError` |
| HTTP CSV export imported private CLI code | Serving/exporting pulled in command orchestration; duplicated ownership | Shared `exports.py`; CLI compatibility aliases retained |
| Large experiment module repeated run/failure handling | Provenance and partial-failure behavior could drift across studies | Focused spatial/signal/network modules; shared runner for seven comparison families |
| Source change during final comparison arm could become an ordinary failed arm | Mixed implementation identity could escape a subsequent-arm check | Shared runner checks identity before/after execution; mismatch terminates comparison |
| Browser JS/HTML/CSS absent from source identity | Changed interaction/rendering code retained the same provenance | Browser assets included in pipeline hash; extracted modules explicitly fingerprinted |
| Zero-radius proximity used one grid cell | Unrelated positions incurred quadratic pair checks despite zero reach | Exact-position grouping; preserve coincident directed contacts and disabled receivers |
| Heuristic switch counting reconstructed next ballots for each voter | Quadratic dictionary work per round | Construct one next-ballot map per transition |
| Tiny movement limits stalled floating-point correction | Valid combined workload failed after 64.299 s | Preserve successful fast-path results; finite bisection between feasible/infeasible scales handles rounding thresholds while enforcing realized path cost |
| Positional `Frame` construction had many adjacent tuple fields | Adding/reordering fields risked silently misassigned state | Keyword construction at initialization and commit |
| Roadmap headers/status reports lagged source | Implemented mechanisms appeared wholly absent | Current summary corrected; dated history retained |

Regression caught a removed `csv` import still needed by batch CSV output.
It was restored; assertions and expected outputs were retained.

## Refined module ownership

| Layer | Files / responsibility |
| --- | --- |
| Configuration/state | `model.py`: immutable schemas and canonical parsing; `nomination.py`, `alignment.py`, `leaders.py`: spatial configuration |
| Round coordinator | `engine.py`: phase order, candidate state, validation, atomic frame commit, rewind/resume |
| Observations | `observations.py`: trusted sensing; `coalitions.py`: scoped sight/interception and proposed spend; `policies.py`: plugin observations/memory/RNG |
| Decisions/mechanisms | `voting.py`, `epistemic.py`, `network.py`, `campaign.py`, `signals.py`, `alignment.py`, `leaders.py`, `detector.py` |
| Replay/provenance | `records.py`: intervention encoding/legacy frame projection; `provenance.py`: runtime/core/pipeline identity |
| Evaluation | `metrics.py`; `experiment_support.py`: retained prefixes/source consistency; `*_experiments.py`: mechanism controls; `combined.py`: integration matrix |
| Stable API | `experiments.py`: existing imports plus general batch/heuristic entry points; package `__init__.py` public names retained |
| Delivery | `cli.py`, `visual.py`, shared `exports.py`, `render.py`, `web/*`; adapters use the same engine |

`experiments.py`: 989 → 112 lines; focused study modules: 316/118/372 lines.
`cli.py`: 568 → 455. `engine.py`: 796 → 741; `step` remains 447 lines and
`make_scenario` 292. Smaller coordination/validation phases remain worthwhile;
moving code alone does not eliminate complexity.

Checkpoint schema stays v21. Source hashes intentionally change; earlier
checkpoints require explicit environment migration and successful full replay.
No automatic mismatch acceptance or fabricated compatibility data was introduced.

## Verification

- Baseline: 311 tests pass; 29.609 s.
- Thirty TOML examples: bounded horizon `min(configured_rounds, 6)`; full frame
  and metric fingerprints, checkpoint replay and one additional resumed round.
  All match the pre-refactor results. This is not a complete-horizon stress test.
- Twelve comparison entry points: baseline functions versus current functions,
  using the same current engine; exact records match after excluding only measured
  `runtime_seconds`. Includes two evaluation seeds, disjoint calibration seeds,
  the 17-arm matrix, detector calibration and one-round campaign oracle.
- Eight adversarial regression tests: dataclass bypass, residual movement budgets, zero-radius work,
  retained failure prefixes, final-arm source changes, extracted/web provenance,
  complete-horizon pairing and changed/missing audit records.
- Final full suite: 319 tests pass in 31.987 s. Standard-library-only run:
  315 pass + four optional-image skips, 31.513 s.
- Independent convergence checker and JS playback harness exit successfully.
  Local Markdown targets and `git diff --check` pass.

Diagnostic artifacts: [directory](../outputs/code-audit-2026-11-08/).
Generated outputs remain ignored; preserve this directory when sharing evidence.
Final records: `verified-final.json`, `comparisons-verified-final.json`,
`unittest.log`, `unittest-stdlib.log`, `convergence.json`; successful playback
harness emits no text (`playback.log` is empty).

## Resource checks

Linux x86-64, Python 3.14.4, Intel i7-12700H, 20 logical CPUs. Sequential isolated
workers; one repetition each; seed 2026. Timing includes other uncontrolled
machine activity; these are workload samples, not service guarantees.

| Workload | Result | Time | Linux peak RSS |
| --- | --- | --- | --- |
| Combined CLI, 1,000 × 10 | Completed | 0.757 s total | 44,108 KiB child |
| Combined CLI, 10,000 × 100, before numeric repair | Failed: movement rounding limit | 64.299 s worker lifetime | Unavailable on failure |
| Same 10,000 × 100 after repair | Completed | 90.768 s CLI; ~11,017 agent-rounds/s | 217,372 KiB child |
| Combined HTTP, 500 × 100 after repair | Completed | Mean 76.81 ms / p95 104.12 ms / max 115.93 ms per step | 263,932 KiB process |

CLI uses summary recording; HTTP retains all frames and includes loopback,
engine, metrics and JSON encoding/decoding. HTTP mean response size: 3,355,812
bytes (~3.20 MiB). Browser rendering, browser memory and interactive usability
are unmeasured; the large payload/history cost deserves optimization before
claiming a responsive visual workload.

Generator: two nominees, `k=2`, near-Alice added ideals, directed star links,
moving sparse proximity, ~10% added voters sense public ballots. Initial mean
public out-degree: 12.793 at 10k; 11.904 at 500. One fixed coalition, leader and
alignment target; adversarial population does not scale with electorate size.
This differs from Stage 01's proposed three-party/full-ballot workload.

10k realized activity: 10,569,302 proximity arc additions/removals; 1,290,334
trusted observations; 100 sight events; 99 interceptions; 100 false reports;
100 campaign purchases; signal spend 100; ideal-shift spend ~0.5; leader spend
~0.1. Zero ballot switches/alerts in this lopsided electorate: execution evidence,
not evidence that interventions are effective or that convergence is guaranteed.

Raw measurements retain generator/template/scenario hashes, manifests, per-round
metrics and the original failure: `combined-*-fixed.json`,
`combined-cli-10000x100.json` in the artifact directory.

## Recheck commands

Run from the repository root. Output paths must be new; original audit artifacts
remain available under `outputs/code-audit-2026-11-08/`.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -S -m unittest discover -s tests -q
python3 scripts/verify_convergence_foundations.py
node tests/playback_harness.js
mkdir -p outputs/recheck
python3 scripts/audit_implementation.py --compare outputs/code-audit-2026-11-08/before.json --output outputs/recheck/examples.json
python3 scripts/audit_comparisons.py --baseline-ref ffaabed7b97b5351028bb8fe76d5d1a9b5e7105f --output outputs/recheck/comparisons.json
python3 scripts/benchmark_combined.py cli --agents 10000 --rounds 100 --seed 2026 --repetitions 1 --timeout-seconds 120 --output outputs/recheck/cli.json
python3 scripts/benchmark_combined.py http --agents 500 --rounds 100 --seed 2026 --repetitions 1 --timeout-seconds 120 --output outputs/recheck/http.json
```

The comparison audit executes functions from the explicitly selected trusted
Git revision with the current engine. The separate example audit compares engine
outputs captured before/after refinement. Neither script substitutes for an
independent voting oracle or frozen scientific experiment.

## Remaining engineering priorities

| Priority | Work | Required acceptance |
| --- | --- | --- |
| P1 | Complete cross-feature rejection/conflict audit trail | Rejected actor/action/phase/reason recorded without corrupting committed state; rewind/export parity |
| P1 | Finish manual browser/download acceptance | Actual saved bytes, edit/rewind, interaction under load; HTTP/harness tests alone insufficient |
| P1 | Freeze research protocol after convergence scope | Controls, observability, calibration/held-out seeds, failures/censoring and run-level uncertainty |
| P2 | Extract remaining round and parser phases incrementally | Independent phase tests plus unchanged example/comparison records |
| P2 | Extend shared lifecycle to specialized calibration/network/batch paths | Retain their schemas, failure labels, partial histories and manifest guards |
| P2 | Record plugin dependency/environment closure | Current hashes validate configured source modules; arbitrary helper imports, external resources and side effects are not hermetic |
| P2 | Bound retained-history and dense-graph resources | Memory/latency curves; explicit limits/failures; never silently sample observations |

This refinement preserves implemented features and proof restrictions. It does
not close all roadmap gates or establish which heuristic performs best.
