# 10: Combined system

Proposed; inherits 09. [Gates](README.md).

## Deliverables

- [ ] Role/observation/action contract; one ballot/person despite overlapping roles.
- [ ] Nomination before round 0; stable >=k candidates; Stage 01 phase order.
  Conflicts: stable controller order, fixed phase-start observations,
  realized-action budgets; no intermediate private-state leakage.
- [ ] Cross-feature access/budget audit: graph layers/sensing, reports, voter/leader
  shifts, detective; rejected/conflicting actions logged.
- [ ] Versioned scenario manifests: all-enabled, all-disabled, seven isolated studies,
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
