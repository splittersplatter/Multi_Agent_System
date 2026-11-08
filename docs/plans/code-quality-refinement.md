# Code audit / refinement — 8 November 2026

Scope: current implementation, all roadmap stages; preserve election semantics,
public imports, commands, recorded fields and convergence domains.

| Step | Deliverable | Acceptance | Status |
| --- | --- | --- | --- |
| 1 | Inventory, baseline tests, example trajectory fingerprints | Every TOML listed; failures retained; bounded audit horizon explicit | Done: 311 baseline tests; 30 examples |
| 2 | Isolate output serialization, replay compatibility, coalition observations | One implementation per responsibility; no CLI dependency from HTTP exports | Done; keyword frame construction |
| 3 | Centralize experiment execution / provenance checks | Preserve partial failures; source changes abort comparison; public record layouts retained | Done for seven comparison families; 12 API records equivalent |
| 4 | Fix defects demonstrated by adversarial checks | Reproduce before fix; rejection leaves committed state intact | Done: scenario bypass, missing web hashes, residual movement; two quadratic costs |
| 5 | Full regression, proof checker, playback harness, trajectory comparison | No unexplained before/after trajectory or metric differences | Done: 319 pass; stdlib 315 + 4 skips; proof/harness pass; 30 examples / 12 comparisons unchanged |
| 6 | Architecture / quality report; accurate current-state links | Implemented vs verified vs pending; findings, commands, risks, next priorities | Done: [report](../code-audit-and-refinement-report.md); 10k CLI / 500 HTTP checks recorded |

Dependencies: standard library; optional Pillow for images. No new dependencies.
Extract cohesive functions; keep one committing engine. Avoid wholesale parser/UI
rewrites without demonstrated benefit. New core/pipeline modules enter provenance
hashes. Existing checkpoint environment mismatch remains explicit; migration still
requires replay verification. Tests do not establish new convergence proofs.

Verification: full unittest suite; standard-library-only suite; independent
convergence enumerator; JS playback harness; all-example fingerprints/replay;
malformed input and atomic rejection checks; local links; `git diff --check`.

## Evidence

- Baseline: clean worktree; 311 tests pass in 29.609 s.
- Starting hotspots: `Simulation.step` 472 lines; `make_scenario` 292;
  `experiments.py` 989; CLI owns CSV/JSONL code imported by HTTP exports.
- Roadmap headers lag actual Stage 02–10 implementation. Shared gates and Stage 11
  research remain incomplete; historical logs will be preserved.
- Final: 10k × 100 combined CLI completes in 90.768 s after repairing a reproduced
  rounding failure; 500 × 100 HTTP p95 104.12 ms. One sample/workload; no browser
  rendering or scientific-performance claim. [Artifacts](../../outputs/code-audit-2026-11-08/).
