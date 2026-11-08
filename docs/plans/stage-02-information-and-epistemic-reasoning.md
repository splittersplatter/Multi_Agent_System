# 02: Information / epistemic reasoning

Partly implemented; acceptance open; inherits 01. [Gates](README.md).
References: survey S1-S3, S6, S9-S10, S12-S13.

## Deliverables

- [ ] Actor access matrix: visible fields, local/public reports, private channels,
  timestamps/provenance; researcher truth excluded.
- [ ] Permission-scoped observation builder; dormant sight/sensing capabilities.
- [ ] Finite models: preferences, ballots, signal possibilities, history;
  actual world retained; misleading claims never factual announcements.
- [ ] Integrate de re/de dicto/pessimistic checks; log information set, candidate
  action and decision/tie criterion; unsupported improvement -> retain ballot.
- [ ] Poll-confident baseline + sincere/epistemic comparisons; paper mapping:
  reproduced assumptions versus departures.
- [ ] Inspector/trace/checkpoint support for observations, information sets and decisions.

## Acceptance

Enumeration matches exact checks; own-ranking knowledge/factivity; false-announcement
rejection; hidden changes preserving observations cannot change decisions given same
policy memory/RNG. Enforce enumeration limit; sampled/heuristic conclusions labelled approximate.
Replay information sets after rewind. Cumulative scenario: movement/channels + sincere,
poll-confident and epistemic policies; compare decisions and outcomes.

## Progress

Recent extension: [rolling proximity-majority beliefs](recent-encounter-majority.md),
passive estimates, not knowledge or a replacement for certified policy domains.

Finite model, bounded conditional equilibrium and three actor-observation policies
implemented; broader temporal/adversarial epistemic semantics remain pending. Historical names in the
[reference map](../paper-implementation.md) are not all implemented.

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 2026-11-06 | User-requested early response-policy extension; Stage 02 remains partial | [Voting reference](../voting-heuristics.md), [tests](../../tests/test_voting.py): pivotal poll belief, local-dominance/maximin score worlds, expected/pivot response variants; 130-suite pass; source assumptions and deviations recorded | Uses Stage 01 scoped sensors, policy memory, named RNG, CLI/browser/checkpoints; optional matched poll information across strategic policies | Not full epistemic state models, factivity, de re/de dicto checks or conditional equilibria; none of the remaining Stage 02 gates declared complete |
| 2026-11-06 | Response-policy verification, not epistemic completion | [Audit](../heuristic-verification-report.md): 134 tests; 147 runs; independent EU/pivotal/dominance/maximin oracles; matched-poll and report-modality controls | Existing Stage 01 policies/history retained without model edits | Top-2 parity limitation; full finite epistemic models, knowledge checks and convergence claims remain unvalidated |
| 2026-11-07 | Literature-only method/metric audit; no stage completion | [Evidence](../literature-heuristics-and-metrics.md), [collection](../../References/README.md): 31 works full-text available; 36 PDFs/versions, SHA-256 manifest; per-paper heuristics, metrics, controls and page references | Mapped published methods to existing Stage 01/early Stage 02 policies; no simulator/test/result changes | AU/pragmatist/leader bias and attacker algorithms documented, not implemented; S7 metric-axis and S23 normalization ambiguities; previous parity/epistemic limitations retained |
| 2026-11-07 | Corpus cleanup + candidate/evaluation contract; full-model convergence gate failed | [Plan](heuristic-evaluation.md), [metrics](../heuristic-evaluation-metrics.md), [symbolic counterexample](../heuristic-convergence.md); 31 reviewed works, 36 PDFs preserved | Retains Stage 01 engine/defaults and early Stage 02 variants; no simulations or new heuristic code | User scope decision required; no universal guarantee, experiments, shortlist or additional stage completion |
| 2026-11-07 | User adopted confirmed restricted convergence cases; mathematical verification | [Foundation](../convergence-foundations.md), [proof checker](../../scripts/verify_convergence_foundations.py): source-specific sequential BR/LD, undirected conformity potential, finite-intervention protocol | Existing engine/defaults retained; variable-total source L1 distinguished from implemented fixed-total worlds | Sequential engine/observations, certificate/replay parity and experiment integration pending; no current mode newly certified, no stage completion |
| 2026-11-07 | Opt-in F1/F2/F3 modes + scheduled F4 | [Foundation](../convergence-foundations.md), [tests](../../tests/test_certified_direct.py): oracle parity, replay, unsupported cases, CSV and live browser direct-response check | Shared engine/checkpoint/browser; simultaneous default and existing LD unchanged; exact current aggregate explicitly available to F1/F2 | Epistemic models/knowledge gates, budgeted attacks, multi-seed studies and later stages pending |
| 2026-11-07 | Certified termination and checkpoint safeguards | `--until-equilibrium`, pending-event/cutoff, sampled output, forged-checkpoint and noncanonical-scenario tests | Retains scenario/replay/export contracts; certificates never precede scheduled interventions | Complete broad suite and independent stage gates; attacker budgets and true epistemic models pending |
| 2026-11-07 | Certified integration verification | Full suite: 147 pass; `python3 -S`: 144 pass + 3 optional-image skips; proof checker and browser scheduled-intervention playback pass | All three modes use existing engine/metrics/checkpoints; default simultaneous mode retained | Stage 02 finite epistemic models, factivity, information sets and later stages remain open |
| 2026-11-07 | Finite knowledge model + epistemic response integration | [Guide](../epistemic-voting.md), [tests](../../tests/test_epistemic.py): factivity, announcements, de dicto/de re, dominance, pessimism, explicit-world projection, permission/cap failures, replay and live browser; six comparison smoke runs | Extends scoped observations, group abilities, phase order, policy memory, CLI/browser, provenance and checkpoints; certified modes remain separate | Perfect recall, general higher-order actor models, conditional equilibrium, explicit signal/attacker semantics and rigorous comparative experiments pending |
| 2026-11-07 | Integrated regression verification | Full suite: 159 pass; `python3 -S`: 156 pass, 3 optional-image skips. Existing convergence proof checker passes; 59 documentation links and `git diff --check` pass | Prior certified cases, simultaneous policies, replay and visual tests retained | Stage 02 remains partial; complete signal provenance, actor knowledge history, conditional equilibrium and subsequent stages |
| 2026-11-07 | Conditional equilibrium + opt-in observation history | [Guide](../epistemic-voting.md), [tests](../../tests/test_epistemic.py): paper two-voter equilibria, independent multi-world oracle, unseen information sets, truthful update, caps, history replay/rewind and sensor revocation | Shared model/CLI and per-agent checkpoint memory; current-snapshot decisions unchanged by old readings without a transition model | Report source timestamps, modelled temporal beliefs, attacker/signal semantics, full stage acceptance and later stages pending |
| 2026-11-08 | Timestamped report provenance + checkpoint v11 | [Messages](../../tests/test_messages.py), [epistemic tests](../../tests/test_epistemic.py), inspector regression: phase-specific source/generation/delivery, permission revocation, stale-vs-sensed ballot, tamper detection and v10 replay migration | Existing report payloads and permissions retained; actor history, full frames and inspector expose provenance | In-app browser interaction blocked by automatic approval usage limit; temporal belief dynamics, attacker/signal semantics and stage acceptance remain pending |
| 2026-11-08 | Provenance integration verification | Full suite: 170 pass; `python3 -S`: 167 pass, 3 optional-image skips; JS syntax and diff checks pass | Includes prior conditional-equilibrium/history work, certified modes and all earlier tests | Live browser check remains unverified; later stages and signal/attacker semantics still pending |
| 2026-11-08 | Mixed-information cumulative scenario | [Example](../../examples/epistemic-integrated.toml), [tests](../../tests/test_epistemic.py), [HTTP](../../tests/test_integration.py): hand-worked outcomes/decisions; movement, delayed reports, CLI/session/server parity, denied/stale requests, hidden-preference/future isolation, capability revocation and rewind/replay | Sincere + pivotal-poll + epistemic voters share existing engine, sensors, channels, memory and checkpoints | Mixed information is not a matched scientific comparison; no convergence claim; temporal beliefs and signal/attacker semantics remain pending |
| 2026-11-08 | Mixed scenario full regression | 174 pass; `python3 -S`: 171 pass, 3 optional-image skips; `git diff --check` passes | Earlier stages and certified cases retained | Live browser download/interaction checks and later stages remain open |
| 2026-11-08 | F5 certified post-intervention network recovery | [Proof](../convergence-foundations.md#f5-finite-interventions-then-network-recovery); 512 exhaustive post-event cases; full suite 243 pass, `python3 -S` 240 pass + 3 optional skips | F3, pending-event guard, CLI/session, checkpoint and CSV retained | Fixed undirected graph; F2 interventions, dynamic attacks and comparative experiments excluded |
