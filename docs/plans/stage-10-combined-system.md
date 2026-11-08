# 10: Combined system

Partly implemented; acceptance open; inherits 09. [Gates](README.md).

## Deliverables

- [ ] Role/observation/action contract; one ballot/person despite overlapping roles.
- [ ] Nomination before round 0; stable >=k candidates; Stage 01 phase order.
  Conflicts: stable controller order, fixed phase-start observations,
  realized-action budgets; no intermediate private-state leakage.
- [ ] Cross-feature access/budget audit: graph layers/sensing, reports, voter/leader
  shifts, detective; rejected/conflicting actions logged.
- [x] Versioned scenario manifests: all-enabled, all-disabled, seven isolated studies,
  seven mechanism leave-one-out conditions; no exhaustive factorial requirement.
- [ ] End-to-end demo: inspect, rewind/edit/replace, resume, compare, GIF/export;
  replay edits through CLI; combined-workload benchmark.

## Controls / acceptance

- Nomination: same nominees = process-only check; different set includes composition.
- Mobility: report degree/exposure mismatch.
- Leader adaptation off: freeze initial positions, couple noise.
- Voter attack off: preserve ordinary drift.
- Passive detective off: identical election outcomes, no alerts.
- Budgets/permissions/k/IDs/phase timing; matching resumed, CLI and browser traces.
- Cross-tests: sensing+movement, deception+campaign links, voter+leader shifts,
  detector after rewind; retain all prior scenarios.
- Correctness/leakage failures block final experiments.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Initial all-enabled integration scenario | [Example](../../examples/all-enabled.toml), [tests](../../tests/test_all_enabled.py): all seven mechanisms, budgets/phase timing, attacker-perception boundary, no-signal invariant, CLI/HTTP/CSV/checkpoint/rewind and GIF | Inherits stages 01–09, one ballot per person; detector remains aggregate-only | Isolated/leave-one-out manifest matrix, rejection audit, benchmark, full shared gates and live browser validation pending |
| 8 Nov 2026 | Cumulative regression | Full suite 304 pass; `python3 -S`: 300 pass + 4 optional-image skips; proof checker and playback harness pass | Shared engine/CSV/HTTP/replay/GIF exercised with all-enabled scenario | No claim of combined-stage completion or formal experimental evidence |
| 8 Nov 2026 | Versioned 17-arm cumulative controls | [Contract](../simulator-guide.md#combined-mechanism-matrix), [tests](../../tests/test_combined_ablation.py): seven isolated/leave-one-out, no-op detector, nominee preservation, source/config hashes, independent replay, failure retention and exposure residuals | All seven engine mechanisms, prior controls and exogenous streams retained | Full cross-feature rejection audit, combined benchmark, formal experiments, remaining gates and live browser check pending |
| 8 Nov 2026 | Combined matrix regression | Full suite 308 pass; `python3 -S`: 304 pass + 4 optional-image skips; proof checker, playback harness and `git diff --check` pass | Prior stages, 17 replayable arms, HTTP/session and checkpoint/GIF tests retained | Rejection audit, combined benchmark, research protocol/experiments, stage gates and live browser check remain open |
| 8 Nov 2026 | User-requested code audit/refinement | [Plan](code-quality-refinement.md), [report](../code-audit-and-refinement-report.md): focused output/replay/observation/coalition/study modules; shared run lifecycle; canonical scenario validation; web provenance; deterministic example/comparison audits | All seven mechanisms and existing imports/record fields retained; numerical residual-movement defect reproduced and repaired | Final regression/scale evidence recorded in report; shared acceptance/research/manual browser gates stay open |
| 8 Nov 2026 | Audit regression and combined scale verified | 319 pass; stdlib 315 + 4 image skips; proof/harness pass; 30 example fingerprints and 12 comparison records unchanged; 10k × 100 CLI 90.768 s / 217,372 KiB; 500 × 100 HTTP p95 104.12 ms / 263,932 KiB | All seven configured mechanisms realized; original rounding failure retained with successful repair rerun | One lopsided two-nominee workload; no ballot switches; browser rendering/manual downloads, rejection ledger and formal research remain open |
