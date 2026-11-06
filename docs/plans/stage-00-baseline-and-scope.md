# 00: Baseline / scope

Verified 2026-11-05; inherits existing repository. [Gates](README.md).
Evidence and handoff: [research contract](stage-00-research-contract.md).

## Deliverables

- [x] Inventory retained plans/references/metadata; record absent source/tests.
- [x] Define hand-worked baseline inputs, expected ballots/winner and replay criteria.
- [x] Assess legacy interfaces; compatibility needs actual schemas/artifacts.
- [x] Record confirmed requirements and adopted implementation defaults.
- [x] Seven falsifiable questions: sources, actions, observations, controls, metrics.
- [x] Fix round phases, permissions, budgets, matched randomness and progress protocol.
- [x] Record environment/future test command; lock dependencies when introduced.

## Acceptance

Baseline specification and missing-feature inventory complete; future test/setup
commands defined. Historical code/test results are not current validation.
Stage 01's runnable baseline is in verification; Stage 02 adds finite epistemic integration.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 2026-11-03 | Historical baseline recheck | Previously 18 passing tests; source/tests and evidence file subsequently removed | Not reproducible in current workspace | Rebuild and verify when requested |
| 2026-11-03 | Current-state synchronization | Source/tests and four support docs absent; references updated | Plans/research retained; nothing restored | Stage 00 deliverables pending |
| 2026-11-05 | Research contract verified | Hand-worked plurality independently checked: counts 2/2/0, tie winner A, mean rank 0.75; edited ballot -> B; seven-source/control register | Retained roadmap and 32-source survey | At that point no current code/tests or old checkpoints; see Stage 01 for subsequent work |
