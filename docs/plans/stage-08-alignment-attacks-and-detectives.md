# 08: Alignment attacks / detective — mechanism 6

Partly implemented; acceptance open; inherits 07. [Gates](README.md).
References: survey S18, S22-S23, S29.

## Deliverables

- [x] Voter-ideal shifts toward target; per-person/round L2 cap + episode total
  realized path-length cap; clip bounds before debit; scoped target selection.
- [x] Separate natural-drift RNG; controls: no drift/attack, drift only,
  attack+drift, equal-budget random shifts. Private ideals require sight.
- [x] Passive detective: aggregate ballot history only; designated monitored party;
  no attack labels/hidden shifts/messages. Initial vote-share-change statistic.
- [x] Calibrate alert threshold on disjoint no-attack/drift seeds; freeze before evaluation.
- [x] First triple-win endpoint t3; early alert requires round < t3.
  No triple win -> timing censored.
- [x] Alert markers; hidden attack truth; episode false-alarm/recall, onset-to-alert
  delay, pre-t3 recall; denominators/censored counts.

## Acceptance

Zero/clipped/cumulative budgets; drift independence; interrupted/no win streak;
alert at t3 not early; missed attacks included; detector rewind restores memory.
No evaluation leakage or successful-attack-only sampling; alert != knowledge.
Cumulative run: nominees + earlier interventions + detective; UI/export/resume.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Scoped, budgeted ideal shifts and natural drift | [Example](../../examples/alignment-attack.toml), [contract](../simulator-guide.md#bounded-ideal-shifts), [tests](../../tests/test_alignment.py): bounds/clipping, explicit sight, independent RNG, zero controls, matched controls, failed baselines, CSV/HTTP/checkpoint tamper, cumulative mechanisms | Nominees and ordinal policies retained; fixed leader platforms, separate actor observations, campaign/coalition/signal coexist | Passive aggregate detector, calibration, early-alert metrics, shared gates and live browser check pending; no convergence claim |
| 8 Nov 2026 | Alignment integration regression | Full suite 277 pass; `python3 -S`: 274 pass + 3 optional-image skips; proof checker, playback harness and `git diff --check` pass; checkpoint v19 validates alignment histories | Prior nomination, bounded signals, campaign, coalition and certified cases retained | Detector/calibration/evaluation, adaptation, shared gates and live browser check remain open |
| 8 Nov 2026 | Aggregate detector, disjoint-seed calibration and evaluation | [Contract](../simulator-guide.md#passive-aggregate-detector), [tests](../../tests/test_detector.py): aggregate-only equivalence, interrupted streaks, exact t3, strict timing/censoring, frozen threshold, calibration failure, CLI/HTTP/CSV/replay and cumulative mechanisms | Existing alignment, signals, campaign, coalition, nomination and ordinal cases retained; attack labels evaluator-only | Formal held-out research/uncertainty, live browser check, leader adaptation and shared stage gates remain open |
| 8 Nov 2026 | Detector integration regression | Full suite 288 pass; `python3 -S`: 285 pass + 3 optional-image skips; independent proof checker, playback harness and `git diff --check` pass; checkpoint v20 validates detector history | Prior alignment, nomination, signals, campaign, coalition and certified cases retained | Formal evaluation/uncertainty, adaptation, shared gates and live browser check remain open |
