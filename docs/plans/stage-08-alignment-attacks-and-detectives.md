# 08: Alignment attacks / detective — mechanism 6

Proposed; inherits 07. [Gates](README.md).
References: survey S18, S22-S24, S29.

## Deliverables

- [ ] Voter-ideal shifts toward target; per-person/round L2 cap + episode total
  realized path-length cap; clip bounds before debit; scoped target selection.
- [ ] Separate natural-drift RNG; controls: no drift/attack, drift only,
  attack+drift, equal-budget random shifts. Private ideals require sight.
- [ ] Passive detective: aggregate ballot history only; designated monitored party;
  no attack labels/hidden shifts/messages. Initial vote-share-change statistic.
- [ ] Calibrate alert threshold on disjoint no-attack/drift seeds; freeze before evaluation.
- [ ] First triple-win endpoint t3; early alert requires round < t3.
  No triple win -> timing censored.
- [ ] Alert markers; hidden attack truth; episode false-alarm/recall, onset-to-alert
  delay, pre-t3 recall; denominators/censored counts.

## Acceptance

Zero/clipped/cumulative budgets; drift independence; interrupted/no win streak;
alert at t3 not early; missed attacks included; detector rewind restores memory.
No evaluation leakage or successful-attack-only sampling; alert != knowledge.
Cumulative run: nominees + earlier interventions + detective; UI/export/resume.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
