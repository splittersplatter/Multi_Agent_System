# Recent-encounter majority estimation

Opt-in, passive plurality estimator. No strategic ballot changes/convergence claim.
Stages 01–03 extension; retain existing modes, replay and cumulative evidence.

## Contract

- Explicit initial poll; `memory_rounds=10`, `poll_weight=0.5`; ballot length `k` unchanged.
- Round r: moved incoming proximity observes completed ballots r−1. No remote channels.
- One latest first choice/person; retain encounters `[r−K+1,r]`. IDs expire with votes.
- Ordered map + incremental counts; reads never refresh. Atomic immutable snapshots.
- Blend initial poll/recent distinct-person shares; empty cache uses poll; retain ties.
- Active state O(U+m); updates expected O(1)/record; snapshot copying O(U).
- Shared engine/CLI/browser/export/checkpoint; version22 only for enabled estimator.

## Delivery gates

1. Core/config/round state; exact expiry, tie and information-boundary tests.
2. Replay/rewind/browser/CSV/CLI integration; disabled fingerprints unchanged.
3. Matched pilot: 200 people, 3 parties, 100 rounds, seeds101–105;
   well-mixed/clustered/shift × stationary/moving; poll sample100.
4. Poll/current/window/blend controls; K5/10/20, w.25/.5/.75 one-factor sensitivity.
5. Raw predictions/configs/manifests; source-round truth; resource/accuracy report.

Formal selection: separate held-out ≥30-seed protocol. Moving finite-memory beliefs
can oscillate; strategic adoption needs a separate full-model convergence decision.

## Progress

| Date | Work/status | Evidence | Integration/remaining |
| --- | --- | --- | --- |
| 2026-11-09 | Implementation started | Baseline fingerprints captured; sensor suite 8 pass | Core wired; broader verification/pilot pending |
| 2026-11-09 | Core and integrations verified | 24 focused tests; 343 full-suite pass; stdlib339 pass/4 skips; 31 example replay checks; 12 comparison checks; live inspector verified | Existing policies/defaults retained; checkpoint22 opt-in; final-source pilot repeat pending |
| 2026-11-09 | First exploratory pilot complete | `outputs/majority-pilot-2026-11-09`: 30 trajectories/240 arm evaluations, zero failures | [Report](../majority-estimation-report.md); validation hardening followed; final-source repeat pending; no policy/convergence selection |
| 2026-11-09 | Final-source pilot and artifact validation complete | `outputs/majority-pilot-2026-11-09-final`: 30 trajectories/240 evaluations; zero failures; all60 prediction/trace files identical to prior run; SHA-256/manifest verified | Earlier engine/CLI/browser/replay retained; [report](../majority-estimation-report.md) records mixed accuracy/resource evidence; strategic adoption, convergence gate and held-out selection remain separate |
