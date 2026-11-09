# Historical heuristic verification — 6 November 2026

Scope: all ten strategic plurality variants + three existing controls. Verify
implemented contracts, not exact paper reproduction or real-election validity.
Model source/defaults unchanged; added independent verification tests only.

Historical source/electorates only; small runs predate N>=100. No claim that
old manifests match current source. [Current status](../implementation-status-report.md).

## Correctness

- [New verification tests](../../tests/test_voting_verification.py):
  80 randomized exact-EU oracles, 2–5 parties, 0–10 other voters; independent
  stars-and-bars enumeration and factorial probabilities. Compare all ballot
  utility differences, including multiway/near ties.
- 80 additional information-set cases: independent pivotal, dominance and maximin
  winner/payoff calculations; not statistical validation of voter behavior.
- Every one of 13 policies: real startup HTTP command; three HTTP rounds exactly
  match CLI/direct frames and metrics; checkpoint resumes identically; CSV has
  every recorded round. No browser renderer involved in these HTTP tests.
- Earlier adversarial tests retained: invalid parameters, computation limits,
  atomic failure, permissions/hidden-state isolation, sensor deduplication, RNG
  isolation, variable ballot lengths, singleton electorate, rewind/replay,
  sampling frequencies and independent Poisson probability sums.
- No observed arithmetic/integration failure under the tested contracts. Source
  departures remain explicit in [voting reference](../voting-heuristics.md).

## Test-run protocol

Seeds **101, 202, 303**; same initial electorate within each scenario, matched
actor-round movement streams. Seeds vary movement and stochastic decisions, not
the electorate's initial rankings/positions. Synthetic rank utilities, 200 samples,
Top-2, L1 radius 2; simultaneous updates; retain failed runs.

| Scenario / information | Population | Policies | Rounds/run | Stability window | Completed / failed | Stable window / cutoff |
| --- | --- | --- | --- | --- | --- | --- |
| Small / native | 9 | All 13 | 100 | 20 | 39 / 0 | 35 / 4 |
| Small / common poll | 9 | Ten strategic | 100 | 20 | 30 / 0 | 30 / 0 |
| Small / reports enabled | 9 | All 13 | 100 | 20 | 39 / 0 | 32 / 7 |
| User population / native | 500 | All 13 | 20 | 10 | 39 / 0 | 9 / 30 |

Total: **147 completed runs, zero failures, 11,580 committed simulation rounds**.
Manifests identify the source at collection time; they do not match later runtime
changes. These are historical exploratory/verification runs, not qualifying studies.

Artifacts, including full parameters/scenarios, manifests, metrics, final
decisions and per-run runtime:

- [Small native](../../outputs/heuristic-verification-20261106/small-native.json)
- [Common poll](../../outputs/heuristic-verification-20261106/small-common-poll.json)
- [Reports enabled](../../outputs/heuristic-verification-20261106/small-reports-enabled.json)
- [Reports-enabled input](../../outputs/heuristic-verification-20261106/small-reports-enabled.toml)
- [500-person runs](../../outputs/heuristic-verification-20261106/population-500-native.json)

### 500-person results

Three runs/policy; winner order is seeds 101/202/303. Switches count full-ballot
changes over 20 rounds. Seconds: mean `Simulation.run` time, includes committed
history; excludes initialization, subsequent metric aggregation, JSON and browser.
Shared machine/process caches; descriptive timings, not latency guarantees.

| Policy | Stable / cutoff | Mean switches/run | Mean seconds/run | Final winners |
| --- | --- | --- | --- | --- |
| sincere | 3 / 0 | 0.0 | 0.45 | A / A / A |
| local_plurality | 3 / 0 | 0.0 | 0.45 | A / A / A |
| sensed_plurality | 0 / 3 | 995.3 | 0.52 | A / B / C |
| pivotal | 3 / 0 | 0.0 | 0.89 | A / A / A |
| expected_utility | 0 / 3 | 655.3 | 26.15 | B / A / A |
| top_k | 0 / 3 | 553.3 | 0.85 | C / A / C |
| max_m | 0 / 3 | 759.7 | 5.07 | C / A / A |
| tie_u | 0 / 3 | 874.0 | 4.88 | B / A / A |
| tie_h | 0 / 3 | 874.3 | 11.08 | B / A / A |
| tie_r | 0 / 3 | 351.3 | 67.63 | B / B / C |
| poisson | 0 / 3 | 874.0 | 10.42 | B / A / A |
| local_dominance | 0 / 3 | 246.3 | 1.05 | C / B / C |
| maximin | 0 / 3 | 108.0 | 0.93 | A / A / A |

## Observed behavior / cautions

1. **Top-2 parity artifact.** Its exact-two-way-tie model ignores one-vote near
   ties. With N=500, the 499 other ballots cannot split equally between the two
   considered candidates. Both response scores are zero; it retains its vote if
   considered, otherwise chooses its highest-ranked considered candidate.
   N=499 permits such ties. Explicit regression check confirms both cases.
   All 1,500 final Top-2 decision traces in the 500-person batch have zero active
   response scores. Its 553.3 mean switches come from consideration-set changes,
   not nonzero pivotal utility comparisons.
   This follows the implemented approximation, but materially limits policy
   comparisons. Do not interpret low switching as effective strategic reasoning.
2. **Information confounding.** Native pivotal gets an initial public poll; other
   strategic policies use local trusted sensors. Common-poll runs control this
   difference. Different winner/switching outcomes are not automatically due only
   to the response heuristic.
3. **Inactive report control.** The original scenarios disable communication;
   `local_plurality` therefore falls back to sincere voting. Enabling truthful
   reports produces 173 total switches over the three small runs, versus zero
   without reports. All 36 non-report-policy runs retain identical count histories
   and final decision traces: no unintended report-to-sensor substitution observed.
4. **Finite samples and approximations.** TieR can sample no pivotal event;
   TieH is nonuniform; Poisson uses truncated independent-count sums. Objective
   ties use inertia and a numerical tolerance. These are model choices, not
   claims of exact equivalence to every reference algorithm.
   With three parties and these electorate sizes, TieU's default 200-sample
   budget covers each enumerated pair's entire exact-tie space; it remains a
   two-way-tie approximation but has no tie-state sampling error in these runs.
5. **Observed stability is not convergence.** Windows say only what happened
   within the recorded horizon. Moving graphs, synchronous responses and stochastic
   samples can restart switching. No Nash/consensus/acyclicity guarantee.
6. **No “best” identified.** Three seeds and two fixed electorates are verification
   runs. Small-case mean winner rank-utility proxies differ only modestly and do
   not establish realism or significance. Freeze an objective, address Top-2 parity,
   vary electorates/information/sampling/uncertainty, then assess paired effects.
   The 500-person cyclic-ranking electorate is nearly balanced: mean winner
   rank-utility is .500 for A, .501 for B, .499 for C. This proxy barely separates
   winners here. Zero switching in pivotal does not establish that it is best.

## Current rechecks

Use the [active voting guide](../voting-heuristics.md) and [verification commands](../../README.md#verify).
Old nine-person outcome commands are intentionally retired; do not rerun them as
production simulations. Published-method assumptions/parity limits still apply.
