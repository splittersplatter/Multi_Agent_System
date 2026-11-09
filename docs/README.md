# Project documentation

## Plan

- [Roadmap: scope, invariants, deliverables](project-roadmap.md)
- [Stage plans: dependencies, acceptance, cumulative progress](plans/README.md)
- [Implementation status and browser check commands](implementation-status-report.md)
- [Voting heuristics: startup selection, parameters, experiments](voting-heuristics.md)
- [Heuristic verification: independent checks and test-run results](heuristic-verification-report.md)
- [Heuristic evaluation plan: candidate roles, gates and experiment contract](plans/heuristic-evaluation.md)
- [Convergence dossier: full-model counterexample and scope decision](heuristic-convergence.md)
- [Confirmed-convergence foundation: proof domains and implementation prerequisites](convergence-foundations.md)
- [Evaluation metrics: formulas, eligibility and uncertainty](heuristic-evaluation-metrics.md)
- [Finite knowledge models and epistemic voting](epistemic-voting.md)
- [Scenario studies: watchdog, foreign intelligence, propaganda, echo chambers](suchit_sims/README.md)
- [MARL interface for learned movement](marl-interface.md) · [Changes on branch suchit-sims](suchit-sims-changes.md)

## Current state

9 November extension: [recent-encounter majority estimator](recent-encounter-majority.md)
implemented opt-in; passive beliefs only. Rolling unique-neighbor memory, explicit
initial poll, CLI/browser inspector and checkpoint22. [Plan/progress](plans/recent-encounter-majority.md).
Focused24/full343 tests pass; stdlib339 pass/4 skips; all31 examples replay.
[Implementation/pilot report](majority-estimation-report.md): final30 trajectories,
240 arm evaluations, zero failures; repeated traces/predictions identical. Earlier
stage acceptance/convergence limits remain unchanged; no strategic policy adopted.

Baseline checked 8 November 2026; latest extension above checked 9 November.
Stage 00 verified; Stage 01 acceptance incomplete;
Stages 02–10 implemented in part; Stage 11 formal experiments/delivery pending.
All seven mechanisms run through one engine. F1–F5 convergence certificates cover
only their declared restricted domains. Core uses the standard library; optional
image exports pin Pillow in `requirements-visualization.txt`.

[Audit/refinement report](code-audit-and-refinement-report.md) ·
[Refinement plan](plans/code-quality-refinement.md) · [Simulator guide](simulator-guide.md).
Output/replay/observation/coalition code now has focused ownership; mechanism
studies use separate modules behind the existing experiment API. Canonical scenario
validation closes a duplicate-voter bypass; browser assets enter provenance hashes.
Thirty example fingerprints and twelve comparison records match the baseline.
Baseline refinement verification: 319 tests pass; stdlib 315 pass + four optional-image skips;
proof checker/playback harness pass. Combined 10k × 100 CLI: 90.768 s; 500 × 100
HTTP: p95 104.12 ms; single workload/sample, browser rendering unmeasured.
Detailed evidence and remaining limits are maintained in the audit report.

Remaining: complete stage gates, rejected-action audit, manual browser/download
acceptance, frozen research protocol and held-out evaluation. Previous automatic
approval limits interrupted live browser verification; HTTP and JS checks do not
replace it. Older deleted source/artifacts remain absent. Dated evidence below
records history, not the current completion state.

## Research

- [Literature survey and candidate gaps](election-manipulation-literature-survey.md)
- [Paper-by-paper heuristics, metrics and simulator mappings](literature-heuristics-and-metrics.md)
- [Local reference collection / access blockers](../References/README.md)
- [Historical epistemic API reference](paper-implementation.md)

Research audit 7 November 2026: 31 works reviewed from full text. 36 PDFs including five retained versions;
original three unchanged. No simulator changes or new experiments; earlier test
evidence above remains dated 6 November. Methods/metric ambiguities are explicit.

7 November follow-up: 31-source corpus cleaned; all 36 PDFs retained. Candidate
register and metric contract documented. Analytical two-voter conformity cycle
refutes universal full-model absorption; no experiments, shortlist or simulator
changes. Scope decision required; no narrower convergence mode adopted.

Subsequent user decision, 7 November: confirmed restricted cases form the future
research basis. F1 direct response, F2 source local dominance and F3 sequential
undirected conformity have model-level proof contracts; F4 handles finite attacks
then F1 relaxation. Exhaustive independent proof checks added; existing simulator
has no newly certified mode, runtime changes or new outcome experiments.

Later 7 November implementation: F1/F2/F3 sequential modes and scheduled F4
interventions now run in the shared simulator; [commands and limits](convergence-foundations.md#3-run-and-inspect).
Certifications are scoped to scenario guards. Latest suite: 147 pass; standard-library
run 144 pass, 3 optional-image skips. Full roadmap and comparative studies remain pending.

Stage 02 now includes bounded finite knowledge models, truthful announcements and
three permission-scoped epistemic response policies, plus bounded conditional
equilibrium analysis and opt-in observation history. [Details and limitations](epistemic-voting.md).
Certified convergence applies only to the separate restricted cases. Latest full
suite: 159 pass; `python3 -S`: 156 pass, 3 optional-image skips.

8 November: report source/generation/delivery provenance is available to permitted
actors, saved frames and inspector; checkpoint v11 validates v10 migration by replay.
Full suite: 170 pass; `python3 -S`: 167 pass, 3 optional-image skips. Browser
interaction verification was interrupted by the automatic approval usage limit.

Later 8 November: directed network turnover metrics and sidebar plots added as an
early Stage 03 extension; no convergence or causal claim follows from these plots.
Full suite: 171 pass; `python3 -S`: 168 pass, 3 optional-image skips. Restricted
convergence examples and independent tiny-model checks pass; later stages remain
incomplete. Live browser interaction remains unverified because of the approval
usage limit.

Stage 02 mixed-information integration: [scenario and commands](epistemic-voting.md#run)
combine movement, reports, sincere/poll/epistemic voters and rewind. Full suite:
174 pass; `python3 -S`: 171 pass, 3 optional-image skips. This is not a matched
comparison or a convergence certificate; later research stages remain open.

Stage 03 early extension: [per-group/person receiver radii](simulator-guide.md#scenario),
directed proximity and browser radius overlay implemented. Full suite: 178 pass;
`python3 -S`: 175 pass, 3 optional-image skips. Matched network controls and the
remaining stage gates are still pending.

Stage 03 frozen-initial control and paired comparison now implemented; [usage and
limits](simulator-guide.md#scenario). Full suite: 183 pass; `python3 -S`: 180
pass, 3 optional-image skips. Degree/exposure-matched controls, broader stage
gates and the live browser check remain pending.

Stage 03 calibrated static control: disjoint calibration/evaluation seeds,
explicit replayable static proximity, and exposure/temporal mismatch reporting.
Full suite: 186 pass; `python3 -S`: 183 pass, 3 optional-image skips. This is
calibration-optimal, not guaranteed held-out exposure matching or causal proof.

Stage 04 early extension: [budgeted coalition report deception](simulator-guide.md#budgeted-report-deception)
with separate trusted sensors and replayable checkpoint v12. Full suite: 193
pass; `python3 -S`: 190 pass, 3 optional-image skips; convergence proof checker
passes. Coalition dynamics are uncertified; remaining Stage 04 capabilities and
all stage gates remain open.

Stage 04 scoped preference sight: fixed target schedule, independent budgets,
permission checks and sight-plurality control; [usage](simulator-guide.md#budgeted-preference-sight).
Full suite: 202 pass; `python3 -S`: 199 pass, 3 optional-image skips. Dynamic
coalition scenarios remain uncertified; adaptive sight and later stages remain open.

Stage 04 private-report interception: [usage](simulator-guide.md#budgeted-private-report-interception),
separate permissions/budgets and checkpoint v14. Full suite: 212 pass;
`python3 -S`: 209 pass, 3 optional-image skips; convergence proof checker passes.
Coalition cases remain uncertified; adaptive capabilities and stage gates remain open.

Stage 04 combined coalition scenario and six-arm [ablation runner](simulator-guide.md#coalition-ablations)
now retain paired runs and failures. Full suite: 216 pass; `python3 -S`: 213
pass, 3 optional-image skips. No statistical or convergence conclusion is implied.

Stage 05 early extension: [budgeted campaign controller](simulator-guide.md#budgeted-campaign-edges)
with public-ballot-only selection, unique purchase ledger and checkpoint v15.
Full suite: 223 pass; `python3 -S`: 220 pass, 3 optional-image skips. Matched
comparisons and exhaustive evaluation remain pending; controller cases are uncertified.

Stage 05 follow-up: [matched campaign comparison and restricted exact oracle](simulator-guide.md#budgeted-campaign-edges),
plus browser spend chart. Full suite: 230 pass; `python3 -S`: 227 pass, 3 image
skips. Oracle scope is one round only; multi-round optimality and convergence are unproved.

Stage 06 early extension: [bounded public signals](simulator-guide.md#bounded-public-signals),
trusting response and checkpoint v16. Full suite: 240 pass; `python3 -S`: 237 pass,
3 optional-image skips; proof checker passes. Known-bound epistemic semantics and
matched signal studies remain open; signal scenarios are uncertified.

8 November convergence extension: [F5](convergence-foundations.md#f5-finite-interventions-then-network-recovery)
proves and implements fixed-graph conformity after finite scheduled ballot/preference
changes. Independent post-event oracle covers 512 cases; dynamic graph attacks,
budgeted controllers and F2 interventions remain outside the certificate. Full
suite: 243 pass; `python3 -S`: 240 pass, 3 optional-image skips; proof checker
and playback harness pass. Live browser interaction remains unverified.

Stage 06 follow-up: [bounded-signal epistemic responses](epistemic-voting.md#bounded-public-signals)
retain compatible worlds without exposing source truth; stale reports do not
constrain current ballots. Checkpoint v17; full suite 251 pass, `python3 -S` 248
pass + 3 optional-image skips; proof checker and playback harness pass. These
policies are not convergence-certified; matched studies and later stages remain open.

Stage 06 comparison: [paired signal/response runner](simulator-guide.md#bounded-public-signals)
records a 3×3 factorial, matched movement, report divergence and failures. Full
suite: 257 pass; `python3 -S`: 254 pass + 3 optional-image skips. Proof checker
and playback harness pass. Formal research evaluation, live browser recheck and
later stage gates remain open.

Stage 07 initial implementation: [spatial nomination and controls](simulator-guide.md#spatial-nomination),
researcher issue view and representation distances. Full suite 268 pass;
`python3 -S`: 265 pass + 3 optional-image skips; proof checker and playback
harness pass. Checkpoint v18 verifies nomination records. Upstream acceptance,
live browser verification and alignment attacks/adaptation remain open.

Stage 08 early implementation: [bounded ideal shifts and drift](simulator-guide.md#bounded-ideal-shifts)
with explicit sight, separate RNG and four paired controls. Full suite 277 pass;
`python3 -S`: 274 pass + 3 optional-image skips; proof checker and playback
harness pass. Checkpoint v19 replays current ideals and costs. Aggregate detection,
calibration, adaptation and live browser verification remain open.

Stage 08 follow-up: [aggregate detector and disjoint-seed calibration](simulator-guide.md#passive-aggregate-detector)
with censored timing/recall and evaluator-only attack labels. Full suite 288 pass;
`python3 -S`: 285 pass + 3 optional-image skips; proof checker and playback
harness pass. Checkpoint v20 verifies detector history. Formal research,
leader adaptation, shared stage gates and live browser verification remain open.

Stage 09 initial implementation: [hidden leader adaptation and perceptions](simulator-guide.md#hidden-leader-adaptation),
plus an [all-enabled scenario](../examples/all-enabled.toml). Full suite 304 pass;
`python3 -S`: 300 pass + 4 optional-image skips; proof checker, playback harness,
cumulative HTTP/replay and GIF tests pass. Checkpoint v21 verifies leader history.
Formal experiments, full integration/shared gates and live browser checks remain open.

Stage 10 follow-up: [versioned 17-arm combined matrix](simulator-guide.md#combined-mechanism-matrix)
records isolated/leave-one-out controls, nominee and motion checks, exposure
residuals and failures. Full suite 308 pass; `python3 -S`: 304 pass + 4 optional
image skips; proof checker and playback harness pass. Rejection audit, combined
benchmark, formal evaluation and live browser checks remain open.

Use [README](../README.md) for current commands and [Stage 01 progress](plans/stage-01-political-simulator.md#progress) for verified scope.
