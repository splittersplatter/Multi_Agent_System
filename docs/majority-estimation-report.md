# Recent-encounter estimator: implementation/verification

9 November 2026. [Usage/configuration](recent-encounter-majority.md) ·
[Plan/progress](plans/recent-encounter-majority.md).

Population follow-up: current demo200, normal runs N>=100. Earlier four-person
browser observations below remain dated verification evidence, not outcome studies.
Prior manifests identify the source at collection time; the later population guard
changes current source hashes. [Current checks](plans/minimum-population.md).

## Implemented

- Passive opt-in estimator; election policies, ballots and existing defaults unchanged.
- Explicit timestamped initial poll; default window10, poll weight.5.
- Incoming proximity after movement observes completed ballots r−1; no remote
  layers/messages, hidden rankings, future ballots or implicit true-count fallback.
- One latest first choice/person; encounter/source timestamps; visited IDs derived
  from cache. Refresh/expiry update counts; no lifetime history or repeated-person weight.
- Encounter-ordered map, immutable frames; exact tied-leader comparison.
- Separate voting/cache memory; rewind/edit/replay; checkpoint22 for the original
  fixed-poll mode, version21 disabled. Later periodic mode uses version23.
- CLI summary/full history, browser inspector, JSON/JSONL, CSV cache metrics;
  matched pilot/sensitivity runner, compressed raw data, configurations/hashes.

## Verification

- 24 estimator tests: independent 400-round randomized oracle, exact expiry,
  changed/unchanged refresh, stale/conflicting/malformed records, ties/endpoints,
  asymmetric/coincident contacts, hidden-ballot trap, atomic failure, policy changes,
  replay/tampering, CLI/HTTP/CSV/inspector parity, exclusive output and byte-identical
  repeated compressed predictions/traces.
- Current regression evidence is centralized in [status](implementation-status-report.md#verification).
  Original pilot/audit logs remain under `outputs/majority-*-2026-11-09*`.
  Historical four-person inspector checks are verification-only; current demo200.
- Adversarial extreme integer weight exposed `OverflowError`; fixed explicit range
  rejection. Malformed encounter records also fail with domain errors.

## Exploratory pilot

Protocol: 200 voters, three parties, 100 rounds; seeds101–105; initial poll sample100;
three cases × stationary/moving. Four base arms + four one-factor sensitivity arms;
**30 trajectories / 240 trajectory-arm evaluations**. Same observations per arm;
truth source round r−1. Recovery means first exact leader-set match, not sustained stability.

Initial artifact set: `outputs/majority-pilot-2026-11-09` (30 successful trajectories).
Final-source repeat: `outputs/majority-pilot-2026-11-09-final`: **30 successful trajectories,
zero failures**. All60 compressed prediction/trace artifacts byte-identical to first
run; artifact hashes verified at collection; manifest identifies that source, not the
later population-enforced runtime.
Raw predictions/traces/configs/sample IDs and SHA-256 manifests retained; no overwritten runs.

Confirmed final-run mean leader-set accuracy (%), equal weighting across five seeds:

| Case | Motion | Poll | Current | Window10 | Blend.5 | Blend seed range |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Well-mixed | Stationary | 80.00 | 39.90 | 39.90 | 60.90 | 43.50–70.00 |
| Well-mixed | Moving | 80.00 | 39.96 | 43.28 | 62.63 | 46.32–71.90 |
| Clustered | Stationary | 100.00 | 47.90 | 47.90 | 50.10 | 49.00–51.50 |
| Clustered | Moving | 100.00 | 46.20 | 48.11 | 50.37 | 49.80–51.09 |
| Support shift | Stationary | 40.00 | 45.45 | 45.45 | 58.10 | 51.00–61.25 |
| Support shift | Moving | 40.00 | 45.24 | 49.48 | 60.80 | 54.25–63.33 |

Ranges are observed min–max across independent seed runs, not confidence intervals;
agents/rounds within one run are not independent replicates.

- Moving well-mixed mean share error: poll .0240, current .2063, window .1669,
  blend .0847. Memory helps local estimates but does not beat the accurate poll here.
- Moving clustered error: poll .0320 vs blend .1549; local encounters remain biased.
- Moving shift error: poll .0690 vs blend .0919, despite blend's better leader accuracy.
  Leader identification and distribution error answer different questions.
- Shift unrecovered fraction: stationary poll100%/blend44.7%; moving
  poll100%/current8.9%/window13.0%/blend12.8%. First-match recovery alone is weak:
  current-contact noise can produce transient correct matches.
- Five seeds only; default parameters were not optimized. Per-seed outcomes,
  ties/censoring and sensitivities remain available; no robustness/superiority claim.
- Sensitivity, moving well-mixed: share error K5=.0913/K10=.0847/K20=.0777;
  w.25=.1255/w.5=.0847/w.75=.0464. Larger windows/poll weights helped this case,
  not a general parameter recommendation; defaults remain unchanged.

## Resource interpretation/remaining gates

- Active state O(U+m)/agent; immutable copying O(U); unordered-contact canonical
  ordering worst-case O(d log d). Expected O(1) applies to individual map operations,
  not a whole simulation round. Dense total state can still reach O(N²).
- Pilot reports per-arm median/p95 population-update time, engine round time,
  cache entries, serialized frame bytes and process high-water RSS. RSS includes
  evaluator and earlier runs; timing is observational, not a controlled benchmark.
- Final-run blended population update (200 agents): per-run medians **1.37–2.14ms**,
  p95 **1.55–3.43ms**. Maximum retained entries per trajectory: **1,514–3,610**.
  Process peak RSS **34.6MiB**; serialized frame payload **28.0–47.7MiB/trajectory**
  if saved uncompressed. JSON bytes are not Python heap measurements. Actual pilot
  streams traces/predictions and discards past frames; combined artifacts ~56MiB.
- Fixed poll can become stale; movement/window expiry can cause belief oscillation.
- Estimator itself is passive. Later `memory_pivotal` uses its estimates for
  exploratory ballot changes; it has no convergence guarantee. Frozen calibration
  and ≥30 held-out seeds/scenario precede formal heuristic selection.

Final core hash: `8e1e0d240b7ce898f64cab3b39405d927aa20c2206da4fd222412b6ce5d146b8`.
Final pipeline hash: `53f64af873db864a843e1dbe3b9b8813e1591990cb465b03e5b217993d4cf13b`.
