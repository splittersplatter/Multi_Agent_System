# 08: Alignment attacks / detective — mechanism 6

Partly implemented; acceptance open; inherits 07. [Gates](README.md).
References: survey S18, S22-S23, S29.

## Deliverables

Checked = implemented; unchecked = full acceptance pending, including implemented subsets below.

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

Consolidated9 November2026; [current verification](../implementation-status-report.md#verification).
Ideal shifts/drift, aggregate detector and disjoint calibration implemented
(`test_alignment.py`, `test_detector.py`). Remaining: held-out uncertainty,
drift/adaptation generalization, manual acceptance and composition certification.
Detector alert is not knowledge of attack.
All outcome workloads N>=100; small linked examples are verification fixtures.
Retain prior-stage APIs/evidence; no broader stage completion or convergence inferred.
