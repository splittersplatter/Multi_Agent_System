# 06: Public signals — mechanism 4

Partly implemented; acceptance open; inherits 05. [Gates](README.md).
References: survey S12-S14; repeated/bounded manipulated polls already studied.

## Deliverables

- [x] True poll = last completed first-choice counts.
  Report: nonnegative integer vector, same total; cost = L1(true,report)/2.
  Separate per-broadcast and episode caps.
- [x] Truthful, bounded-random, target-biased policies; controller knows true
  aggregate, not private rankings without sight.
- [x] Initial-only/repeated schedules; record source-round/report-round; no uncast-ballot access.
- [ ] Matched sincere/poll-confident/epistemic responses; known-bound epistemic
  model retains compatible possibilities; trusting heuristic != factive knowledge.
- [ ] True/reported count plots, distortion curves, decision traces;
  hand-worked literature reproduction + assumption differences.

## Acceptance

Totals/integrality/both caps; zero-distortion equivalence; timing/ties/impossible
actions; no hidden truth in voter input; false announcements rejected.
Measure target wins/share/margin, distortion response, switching/cycles, realized costs.
Cumulative run: mobility + coalition reports + campaign edges + repeated polls;
separate provenance/budgets; replay/UI/exports.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Bounded public-signal controller + trusting response: initial/repeated, truthful/random/target-biased, source/broadcast timestamps, independent limits | [Example](../../examples/public-signal.toml), [tests](../../tests/test_public_signal.py): report invariants, independent plurality oracle, own-ballot inconsistency, boundary/staleness, scope, replay/v15 migration, CLI/HTTP/CSV and cumulative coalition/campaign run | Shared engine, report/ballot separation, graph/coalition budgets and researcher truth retained; certified cases reject signals | Known-bound epistemic signal semantics, matched response studies, source-paper reproduction and full upstream gates remain pending; no convergence claim |
| 8 Nov 2026 | Signal integration regression | Full suite 240 pass; `python3 -S`: 237 pass, 3 optional-image skips; JS signal chart and convergence proof checker pass | Prior campaign/coalition modes, histories and reproducible controls retained | Live browser interaction unverified; no epistemic signal interpretation, comparative research or convergence evidence |
| 8 Nov 2026 | Known-bound factive signal responses | [Example](../../examples/epistemic-public-signal.toml), [model/limits](../epistemic-voting.md#bounded-public-signals), [tests](../../tests/test_epistemic_signal.py): explicit-world oracles, stale signal, hidden-truth isolation, permissions, CLI/HTTP/CSV and v16 replay | Shared signals, scoped observations, inspector, checkpoints and actor history; prior variants unchanged | Matched response studies, source-paper reproduction, full gates and live browser check pending; no convergence claim |
| 8 Nov 2026 | Known-bound integration regression | Full suite 251 pass; `python3 -S`: 248 pass, 3 optional-image skips; independent convergence proof checker and playback harness pass | Certified cases, existing signals, historic checkpoint migration and prior stages retained | New signal policies remain uncertified; comparative studies and remaining stages open |
| 8 Nov 2026 | Paired signal/response comparison implemented | [Commands/contracts](../simulator-guide.md#bounded-public-signals), [tests](../../tests/test_signal_comparison.py): 3×3 factorial, independent replay, zero-budget, expected first-round shift, missing baselines, failure retention, cumulative coalition/campaign | Existing movement/coalition/campaign/signal engine, exact information bounds and run records retained | No formal multi-seed research conclusions, source-paper reproduction, convergence claim or live browser check |
| 8 Nov 2026 | Comparison integration regression | Full suite 257 pass; `python3 -S`: 254 pass + 3 optional-image skips; proof checker, playback harness, `git diff --check` pass | Prior signal, certified convergence, CLI/replay and cumulative mechanisms retained | Research/evaluation gate and remaining project stages stay open |
