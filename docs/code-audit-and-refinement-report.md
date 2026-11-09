# Architecture and engineering limits

Maintained9 November2026. [Current verification](implementation-status-report.md#verification).
Historical measurements: [benchmarks](history/benchmarks.md). One committing
engine; adapters do not implement separate election dynamics.

## Ownership

| Layer | Responsibility |
| --- | --- |
| `model.py` | Immutable schemas; canonical validation, including dataclass replacements |
| `population.py` | N>=100 normal-run guard; explicit scoped tiny-fixture exception |
| `engine.py` | Phase order, proposed state, validation, atomic commit, rewind/resume |
| `observations.py`, `coalitions.py` | Scoped sensing/sight/interception; proposed capability spending |
| `policies.py`, `voting.py`, `epistemic.py` | Policy observations/memory/RNG; ballot responses; bounded knowledge |
| `majority.py` | Separate recent-encounter estimator state; no strategic ballot action |
| `network.py`, `campaign.py`, `signals.py` | Graph/motion, purchased edges, bounded public reports |
| `nomination.py`, `alignment.py`, `leaders.py`, `detector.py` | Spatial configuration/dynamics, hidden adaptation, aggregate-only alerts |
| `records.py`, `provenance.py` | Replay projections; core/pipeline/plugin identity |
| `metrics.py`, `experiment_support.py`, `*_experiments.py`, `combined.py` | Metrics, retained failures, mechanism controls and integration matrix |
| `experiments.py`, package exports | Stable public imports and general batch/heuristic entry points |
| `cli.py`, `visual.py`, `exports.py`, `render.py`, `web/*` | Shared-engine delivery, serialization and rendering |

## Invariants

- Revalidate scenarios before plugins/runtime; duplicate IDs never reduce vote count silently.
- Normal N>=100 enforced in shared engine and entrypoint preflight. No environment
  autodetection; scoped verification fixtures cannot be resumed normally when undersized.
- Immutable committed frames; per-person/per-phase memory; proposed actions validated
  before ballots, budgets, graphs or messages commit. Use keyword Frame construction.
- Source changes stop continued steps/studies. Web assets and all runtime modules
  enter provenance; identities checked before/after comparison arms.
- Checkpoint22 for enabled encounter estimator;21 otherwise. Old source/environment
  requires reviewed migration and successful replay. Plugin-source mismatch still fails.
- Exact-position grouping handles zero-radius coincidence without scanning every pair.
  One next-ballot map avoids quadratic switch-count reconstruction.
- Bounded spatial moves account for floating-point realized cost; repaired residual
  rounding failure retained in `outputs/code-audit-2026-11-08/`.
- Shared exports avoid importing CLI orchestration into HTTP. Specialized experiment
  paths retain their own schemas/validation; not all use the shared runner.

## Research and scale limits

- F1–F5 proofs certify only their guarded policy/schedule/information domains.
  Finite tests, fixed winners and quiet windows do not establish convergence.
- Full-world epistemic enumeration is exponential; with >=100 voters and >=2
  candidates its current logical-world cap prevents nontrivial production use.
  Keep tiny formal models explicit; do not silently replace exact reasoning with sampling.
- Exact campaign oracle accepts at most8 voters: verification-only, not a normal
  >=100-person campaign benchmark. One-round bound does not extend to later rounds.
- Source hashes are not hermetic dependency closure or a sandbox. Trusted plugins
  can access process/global state and arbitrary external resources.
- Dense contacts can require O(N²) active estimator records; full frame history
  multiplies storage. Summary recording discards frames, not current policy/cache state.
- Multi-file exports are exclusive but not transactional; partial artifacts may remain
  after I/O failure. HTTP/JS checks do not prove manual browser/download acceptance.

## Next engineering work

| Priority | Deliverable / acceptance |
| --- | --- |
| P1 | Rejected/conflicting action ledger: actor/phase/reason; no partial commit; rewind/export parity |
| P1 | Actual browser save bytes, edit/rewind and load testing; measure browser memory/render latency separately |
| P1 | Resolve intended voter proof domain before dependent outcome studies |
| P2 | Extract remaining parser/round phases incrementally; independent phase tests and unchanged trajectory records |
| P2 | Extend common run lifecycle without losing specialized failure/censoring schemas |
| P2 | Explicit dense-graph/history/expensive-policy limits; fail visibly, never silently sample observations |
| P2 | Dependency/environment closure for reproducibility; efficient exact reasoning needs separate source-to-engine approval |

## Rechecks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -S -m unittest discover -s tests -v
python3 scripts/verify_convergence_foundations.py
node tests/playback_harness.js
mkdir -p outputs/recheck
python3 scripts/audit_implementation.py --output outputs/recheck/examples.json
```

Audit tool is explicitly fixture-only. Before/after comparisons require same
horizon and deliberately saved baseline; changed demos are expected differences.
`audit_comparisons.py --baseline-ref <trusted-ref>` executes trusted revision
functions with the current engine; it is not a previous-engine or independent oracle.
Never copy a stale hard-coded Git hash or claim old manifests match new source.
