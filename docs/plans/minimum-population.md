# Minimum simulation population

Requirement: all outcome simulations/browser demos/pilots/benchmarks **N>=100**;
default demo200. Tiny mathematical/unit/regression fixtures are verification only.

## Changes / acceptance

- Shared engine minimum; covers API/CLI/browser/resume/experiment arms.
- Custom majority pilots reject undersized inputs before creating output directories.
- Raise recent-majority browser example to200 real distinct voters; preserve
  movement/cache semantics, explicit poll and immutable candidate preferences.
- Explicit scoped verification exception for tiny tests/proofs, never implicit
  environment detection. Normal CLI has no bypass. Label subprocess fixture output.
- Benchmark generators reject undersized normal workloads; real CLI/HTTP tests>=100.
- Test99 rejected/100 accepted/200 demo; API, CLI, custom pilot and checkpoint
  enforcement; scope restoration, malformed inputs, full regression and live run.
- Update agent guide, current docs/commands and progress; preserve earlier evidence.

## Progress

Implemented9 November: shared guard,200 distinct demo voters, explicit fixture
scope, benchmark minimum and entrypoint/replay checks.9 population tests pass;
[central suite evidence](../implementation-status-report.md#verification).
Manual200-node rendering/performance unmeasured; scientific gates unchanged.

## Evidence / integration

- Full suite: `outputs/population-tests-complete-2026-11-09.log`.
  Stdlib: `outputs/population-tests-stdlib-complete-2026-11-09.log`.
- Normal CLI: `run examples/recent-majority.toml --summary` ->100 rounds,
  101 metrics rows, every total200; sincere counts80/70/50 unchanged.
  `outputs/population-demo-200-summary-2026-11-09.json` includes source manifest.
- Production HTTP200: startup selector, three steps, all ballots/estimates,
  exact checkpoint replay; no verification exception (`test_population.py`).
- Explicit fixture audit: `outputs/population-audit-2026-11-09.json` ->31 pass.
  Matched three-round audit: `outputs/population-audit-matched-2026-11-09.json`;
  against prior majority audit, only deliberately enlarged `recent-majority.toml`
  differs. Other30 example inputs/frames/metrics/next-step fingerprints unchanged.
- Small fixtures retained without duplication. CLI regression helper labels stdout
  `verification_only`; HTTP test sessions retain explicit purpose across threads.
  Real subprocess CLI/HTTP benchmark checks now use100, not8.
- No new policy, outcome study or convergence claim. Earlier four-person formal
  witness concerns the prior unrestricted-size contract; N>=100 remains uncertified.
