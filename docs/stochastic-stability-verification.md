# Stochastic-stability verification

9 November2026. [Contract/proof](plans/stochastic-stability.md).
**Historical grid evidence; runtime retired9 November2026 by user decision.**
Current runtime: Gaussian `random_walk`; `examples/gaussian-memory.toml`,
checkpoint25, `frequencies --control baseline|sincere`. Streaming diagnostics,
plots and state playback retained; no Gaussian occupation/mixing certificate.
Below: dated proof/checker and former runtime evidence, not current capabilities.

## Scope and implementation

Work order: exact model → adversarial checks → reachable kernels → recurrent
classes/stationary measures → independent review → [runtime plan](plans/stochastic-stability-implementation.md).
No new dependency. Existing normal/uniform defaults unchanged; grid uses checkpoint24.

- [Checker](../scripts/verify_stochastic_stability.py): immutable normalized
  state; integer positions; boundary-stay categorical motion; exact contacts;
  rolling caches; startup/publication phase; simultaneous rational decisions.
- Exact proposal aggregation, breadth-first reachability, iterative SCCs,
  closed classes, periods, independent rational stationary linear solve/residuals.
- Explicit state/edge/solve ceilings. Incomplete graphs receive no class analysis;
  skipped stationary solves receive no invented frequencies. Output is exclusive.
- Explicit `verification_scope`; no normal small-population simulation bypass.
- Evidence: source/environment manifest, checker hash, command, fixed parameters,
  explored-state counts, kernel/stationary hashes, phase-conditioned frequencies.

## Reproduce

From repository root; choose a new output name if it already exists:

```bash
python3 scripts/verify_stochastic_stability.py \
  --max-states 2000000 --max-edges 2000000 --stationary-ceiling 256 \
  --output outputs/stochastic-stability-formal-2026-11-09.json

PYTHONPATH=src python3 -m unittest discover -s tests -p test_stochastic_stability.py -v
```

`--population 2` or `--population 3`: formal fixture selection, not outcome
electorate size. Default: both. `--max-states`, `--max-edges`: per-case reachability
ceilings; `--stationary-ceiling`: maximum class size for exact linear solving.
Without `--output`, JSON goes to stdout. A successful audit command can contain
explicit resource cutoffs; inspect case/solve statuses, not merely process exit.

## Exact results

Eight declared models: two candidates,2×2 lattice, squared radius1; one mixed
strict-ranking profile/N; truthful initial poll; all16/64 initial position states.
Each row explores every state reachable from those starts, not all valid states.

| N | K | L | Reachable | Edges | Closed class size | Period |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1 | 32 | 288 | 16 | 1 |
| 2 | 1 | 2 | 48 | 432 | 32 | 2 |
| 2 | 2 | 1 | 36 | 324 | 20 | 1 |
| 2 | 2 | 2 | 56 | 504 | 40 | 2 |
| 3 | 1 | 1 | 128 | 3456 | 64 | 1 |
| 3 | 1 | 2 | 192 | 5184 | 128 | 2 |
| 3 | 2 | 1 | 188 | 5076 | 124 | 1 |
| 3 | 2 | 2 | 312 | 8424 | 248 | 2 |

Totals992 states/23688 edges;8/8 complete,8 exact stationary solves; no cutoff.
Stationary residuals zero; phase mass exactly1/L. The first candidate wins every
state in these fixtures. Two-candidate sincere starts cannot produce beneficial
compromise flips under this rule: these results validate state/phase/cache
machinery, not strategic election performance or uniqueness in the full model.
Separate three-candidate fixtures exercise genuine simultaneous compromise flips.

## Adversarial verification

[18 focused tests](../tests/test_stochastic_stability.py):

- Independently enumerate25 proposal vectors; boundary-stay multiplicities.
- Exact6561 radius offsets; no floating-point snapping.
- Cache expiry/re-entry, unchanged-contact refresh, unique IDs, immutable frames.
- Startup versus later phase0; previous ballots versus proposed ballots.
-1620 exact decision comparisons against existing `memory_pivotal`.
- Absolute r10/r110 cache/decision agreement; default K10/L10 boundaries.
- Periodic two-cycle, multiple absorbing classes, nonuniform stationary measure;
  iterative2000-state SCC; invalid kernels/inputs; resource cutoffs/exclusive writes.

Raw formal evidence: `outputs/stochastic-stability-formal-final-2026-11-09.json`.
Final regression logs: `outputs/grid-final-tests-2026-11-09.log` and
`outputs/grid-final-stdlib-2026-11-09.log`.
Generated evidence is local/ignored; commands and source are retained in Git.

## Runtime integration and review

- User authorized independent reviewer: analytic PASS;18 formal tests and24540
  independent rational action checks. Runtime review found two defects, both fixed:
  effective-override grid detection; direct manual-queue guard. Re-review PASS,
  all16 integration tests passed. Review is not a machine-checked proof.
- Former grid runtime (removed): explicit `grid_position`,
  exact radius, categorical boundary-stay motion, strict declared-domain guards.
  One shared engine/CLI/browser/export/replay; version24; no silent snapping.
- [Streaming diagnostics](../src/multi_agent_election/occupation.py): winner/share,
  flip/winner-change, separate added/removed arcs and /N(N−1) normalization;
  all-round/retained/phase means; complete/partial batches; descriptive lag1;
  failures retain completed prefix. No independent-round confidence intervals.
- `frequencies` options: `--rounds`, `--burn-in`, `--batch-size`, `--seed`, `--rows`,
  `--output`, `--control baseline|sincere-grid|continuous-normal`.
  Default10000/1000/100; burn/batches must align to poll interval. With neither
  output flag, paired CSV/JSON files are created in `outputs/` using the UTC start
  timestamp. Custom paths remain available; exclusive creation prevents overwrite.
- Controls preserve rankings, initial physical coordinates and poll. Sincere-grid
  shares exact motion; continuous-normal shares initial conditions, not trajectories,
  and is explicitly uncertified. Configuration/source hashes and seed recorded.
-16 runtime tests: all125 initial three-voter proposal vectors;25-round formal/
  engine agreement through two publications; full1681-position proximity oracle;
  checkpoint/tamper/edit atomicity; effective overrides;200-person HTTP equivalence;
  99 rejection/100–101 acceptance; streaming/full-history equality and failures.
- Final suites414 pass; stdlib410 pass/4 optional-image skips; JS harness pass.
  Example audit32/32 replay/next-step checks pass. Historical comparison:30 old
  fixtures unchanged; recent-majority differs due earlier normal-walk update;
  stochastic-grid is new. `outputs/grid-example-audit-2026-11-09.json`.
-200-voter CLI plumbing check:30 rounds, raw CSV and JSON summary;
  `outputs/grid-cli-smoke-2026-11-09.{csv,json}`. Validation only, not outcome evidence.

## Remaining limits

- Checker remains a proof oracle, not a second production simulator. Tiny-model
  checks and runtime correspondence tests do not prove general correctness.
- Current continuous motion remains exploratory. Do not transfer ideal-independent
  draws to an infinite seeded execution or claim every seed converges.
- No default41×41/K10/L10 state enumeration; no arbitrary rankings/polls/cache
  enumeration. Directed contacts outside this common-radius baseline remain excluded.
- No held-out30-seed/10000-round campaign, mixing bound, stationary-distribution
  certificate, global uniqueness or absorption claim. Long GUI histories still grow;
  use streaming CLI for long studies. Hard process termination cannot guarantee
  a structured failure record; recoverable step/resource errors are recorded.
