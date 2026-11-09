# Finite-grid implementation

**Retired9 November2026:** grid runtime/preset removed by user request. Replacement:
`examples/gaussian-memory.toml`; Gaussian default; checkpoint25; frequency summaries
and state playback retained without a stability/mixing certificate. Below is the
historical implementation/review record; do not execute it as a current work order.

Gaussian replacement acceptance:427 tests pass;20 focused integration tests pass
under stdlib-only Python; JS playback harness/diff checks pass.200-person30-round
CLI smoke saved JSON/CSV/SVG and31 state frames, loaded without rerunning dynamics.
[Current evidence](../implementation-status-report.md#verification). No Gaussian
mixing/occupation guarantee; voter/poll/cache semantics unchanged.

9 November2026. User approved implementation and independent review.
Dependency: [analytic contract](stochastic-stability.md); independent reviewer
passed A–D, timestamp quotient and direct-winner rule. This does not certify code.

## Work order / acceptance

1. Grid contract: opt-in `grid_walk`; explicit integer initial coordinates;
   boundary-stay five-way proposals; exact proximity; unchanged normal/uniform modes.
2. Domain: explicit `stochastic_stability` declaration; fixed41×41/K10/L10,
   radius.12/k1/homogeneous memory-pivotal; reject excluded features and edits.
   Label IID-theorem assumption separately from seeded finite replay.
3. Integration: shared engine, checkpoint24, browser/inspector/export;
   no quiet-window equilibrium shortcut; deterministic resume/rewind playback.
4. Measurement: streaming CLI; raw per-round observables, cumulative/burn-prefix
   and phase-conditioned means, aligned batches; no independent-round error bars.
5. Verification: formal-model/engine tiny successor agreement;200-voter API/HTTP,
   checkpoint/tamper/domain/replay tests; unchanged legacy fingerprints; full suite.
6. Handoff: reproducible200-person preset, commands, evidence and limitations;
   no30-seed/10000-round research campaign during implementation validation.

No new dependency, model randomness in voting, timestamp migration, stationary
distribution certificate, global uniqueness, absorption or finite mixing claim.
Outcome protocol remains [predeclared separately](stochastic-stability.md#5-evaluation-specification-execution-deferred).

## Completion

Implemented1–5; [evidence/report](../stochastic-stability-verification.md).
Independent runtime review defects fixed/re-reviewed.414 tests pass;4 optional
stdlib skips;32 fixture replay checks.200-voter CLI/HTTP/browser plumbing checked.
Full research evaluation remains separate; no seeded-path convergence certificate.

9 November follow-up: `frequencies` automatically saves a timestamped CSV/JSON
pair when neither output flag is supplied. Explicit paths remain exclusive; a
collision fails without overwriting. CLI reports both paths.

Later9 November: automatic timestamped outputs extended to CLI simulations,
comparisons, pilots and orderly browser shutdown. `--save-plots` creates SVG
plots, retaining per-trajectory labels for comparisons. No model dynamics changed.
Verification:419 tests passed; browser playback harness and `git diff --check` passed.

9 November state-recording extension: `--save-states` streams every committed
frame and metrics, including initial state; rewind markers replace edited futures.
`view PATH`/`view --latest` opens read-only browser playback with timeline/agent
inspection. Source/configuration recorded; simulation outcomes unchanged by
recording. Viewer loads the timeline; disk/browser resources scale with history.
Validation:427 full-suite tests pass;8 state-recording tests also pass under
stdlib-only Python; JS playback harness and `git diff --check` pass. Actual200-node
saved browser timeline scrubbed0→12→11 with changing positions and read-only
controls. Full command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

## Independent analytic review

- PASS: finite state; relative-age/startup quotient; recurrent-class entry;
  class-conditioned state/transition occupation; phase mass1/L; continuing contacts.
-18 formal tests and24540 independent rational action checks passed by reviewer;
  reviewer checked Levin–Peres C.1 full text.
- Applies to ideal independent categorical proposals only. Seeded replay is not
  infinite IID evidence. Production correspondence/tests remain implementation gates.
