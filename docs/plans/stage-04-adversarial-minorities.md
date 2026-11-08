# 04: Adversarial minorities — mechanism 2

Proposed; inherits 03. [Gates](README.md).
References: survey S8, S11, S16-S18, S21, S27.

## Deliverables

- [ ] Coalition ID/membership/target fixed before outcome sampling; separate
  per-round/episode capability budgets.
- [ ] Sight: scoped target preferences. Coordination: private channel.
  Deception: false reports, not altered cast ballots.
  Eavesdropping: expanded private sensing, not public edges.
- [ ] Report-only channels for deception; trusted ballot sensors separate controls.
- [ ] Sincere, public-tactical and bounded coalition heuristics; no optimality claim.
- [ ] Individual capability ablations + combined case; fixed coalition/targets/
  exogenous draws; report allowed and realized costs in separate units.
- [ ] Group presets; sender/receiver/timestamp report logs; budget plots; memory checkpoints.

## Acceptance

No unauthorized sight/private traffic; sensing leaves public graph unchanged;
cast ballots remain valid; disabled-capability observation equivalence; message delay/caps;
shared policy-memory replay/rewind. Coordination does not imply common knowledge.
Cumulative case: moving network + coalition; attribute target-support changes by capability.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Early opt-in coalition report deception: fixed disjoint membership/target, shared per-round and episode budgets, deterministic `target_report` and plugin actions | [Example](../../examples/coalition-report.toml), [tests](../../tests/test_coalition_reports.py): false-vs-sensor, epistemic factivity, caps, actor order, atomic invalid actions, zero-budget control, checkpoint v12 migration/rewind, CLI/HTTP/CSV | Delayed scoped reports and trusted sensors remain separate; graph/movement and prior epistemic APIs retained; certified modes reject coalitions | Stage 02/03 gates unfinished; sight, eavesdropping, additional coalition strategies, rejected-action audit, budget plots and ablations pending; no convergence guarantee |
| 8 Nov 2026 | Report-deception integration regression | Full suite 193 pass; `python3 -S`: 190 pass, 3 image skips; convergence proof checker and JS harness pass | Prior certified scenarios, network controls and stage tests retained | No live browser check or comparative experiments; Stage 04 and upstream gates remain open |
| 8 Nov 2026 | Budgeted scoped preference sight + simple sight-plurality policy | [Example](../../examples/coalition-sight.toml), [tests](../../tests/test_coalition_sight.py): disjoint permissions, caps, deterministic shared allocation, independent report budget, atomic failures, hidden-preference isolation, v12 migration and v13 replay/rewind, CLI/session/CSV | Movement, reports, trusted sensors and coalition histories remain separate; certified modes still reject coalitions | Fixed target schedule only; adaptive sight, eavesdropping, epistemic integration, rejected-action audit, budget plots, ablations and Stage 02/03 gates remain open |
| 8 Nov 2026 | Preference-sight integration regression | Full suite 202 pass; `python3 -S`: 199 pass, 3 optional-image skips; HTTP/JS, scoped phase and proof-checker tests pass | Existing coalition deception, certified cases, network controls and checkpoint compatibility retained | No live browser check, eavesdropping or comparative research conclusion; stage and upstream gates remain open |
| 8 Nov 2026 | Budgeted private-report interception + `overheard_plurality` | [Example](../../examples/coalition-eavesdrop.toml), [tests](../../tests/test_coalition_eavesdrop.py): scoped actual packets, false reports, delay, denied delivery, no self intercept, sender deduplication, caps, replay/migration and HTTP/CSV | No new public edges or channel membership; untrusted packets separate from trusted sensing/sight; report and sight budgets remain independent; checkpoint v14 | Fixed interception order, no adaptive target selection or epistemic integration; budget plots, rejected-action audit, ablations, upstream stage gates and convergence evidence pending |
| 8 Nov 2026 | Interception integration regression | Full suite 212 pass; `python3 -S`: 209 pass, 3 image skips; JS and convergence proof checker pass | Existing certified cases, sight, deception, topology and checkpoint histories retained | Browser interaction unverified; Stage 04 and upstream/later gates remain open |
| 8 Nov 2026 | Combined coalition policy + matched six-arm ablation runner | [Scenario](../../examples/coalition-combined.toml), [tests](../../tests/test_coalition_ablations.py): sight/report source separation, per-capability budget controls, matched movement, paired target metrics, full-frame replay and retained failures | Existing coalition mechanisms, graph layers, seeded motion and engine retained; source digests and horizon metrics exported | Fixed-order selection, budget plots, rejected-action audit, calibrated multi-seed research/uncertainty, upstream gates and convergence proof remain pending |
| 8 Nov 2026 | Combined/ablation regression | Full suite 216 pass; `python3 -S`: 213 pass, 3 optional-image skips; JS and proof checker pass | Existing certified cases, independent coalition budgets, checkpoints and other stages retained | Live browser interaction, robust comparative studies and later stages remain open; horizon outcomes are not convergence certificates |
