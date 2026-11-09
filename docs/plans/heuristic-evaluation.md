# Heuristic audit and evaluation

Status: F1–F5 restricted cases implemented; formal selection/evaluation pending.
Updated9 November2026. No broad stage completion.
[Evidence](../literature-heuristics-and-metrics.md) · [Convergence dossier](../heuristic-convergence.md) · [Metric dictionary](../heuristic-evaluation-metrics.md).
[Adopted foundation cases](../convergence-foundations.md): F1 direct response,
F2 source local dominance, F3 sequential undirected conformity, F4/F5 finite intervention/relaxation.

9 November scope priority: [proof-first improvements](research-improvement.md).
`memory_pivotal` is an implemented exploratory policy distinct from `pivotal`.
Its original unrestricted-size composition has an inductive
[counterexample](../memory-voting-convergence.md). Proof remains required for
certified-convergence claims; exploratory finite-horizon comparisons are allowed.

Current statistical baseline: Gaussian movement and exploratory frequency/phase
diagnostics. [Grid proof](stochastic-stability.md) retained as historical evidence;
grid runtime retired. Immediate strict response retained; no Gaussian occupation,
mixing or ballot-absorption certificate. Held-out evaluation remains required.

## 1. Scope and gates

- Separate voter, pollster, network controller, campaigner and defender tracks.
- Reproducibility mandatory; guaranteed ballot absorption mandatory only for a
  certified-convergence selection. Exploratory selection records missing guarantees.
- Original full-model guarantee is refuted. User subsequently authorized cases
  with confirmed convergence as the basis for future work: certify explicit
  restricted compositions, not arbitrary heterogeneous/mobile/attacked mixtures.
- No weighted overall score, cross-role leaderboard or predetermined five methods.
- Research scope decision resolved: see foundation proof domains. Opt-in sequential
  cases have engine guards/certificates; existing simultaneous modes remain uncertified.
- Never obtain convergence by silently locking ballots, disabling capabilities,
  truncating runs or treating a quiet window as equilibrium.

## 2. Candidate eligibility register

Page references below are PDF pages in the [full-text audit](../literature-heuristics-and-metrics.md).
Each row inherits its track contract below; listed departures override it.
I = implemented source-informed variant; N = not implemented; C = control.
**Unrestricted strategic candidates lack a full-model convergence certificate.**
Separate F1–F5 modes retain their stated guarded domains, not arbitrary compositions.
Theory for a restricted source model is not evidence for the current composition. Complexity refers to the
method, not measured runtime; explicit enumeration budgets must fail visibly.

### Track contracts

| Track | Objective / permitted inputs | Actions, memory and budget | Execution / termination |
| --- | --- | --- | --- |
| V: voter | Own outcome utility; private ranking/current ballot, authorized observations, own memory; no evaluator truth | Ranked ballot; policy-specific belief/sample state; compute cap | Current engine: simultaneous after movement/graph/messages; fixed party-order election ties, retain current objective ties then ranking except Top-K exclusions; actor-round RNG; horizon is not convergence |
| P: pollster | Constructive target win or destructive loss, separately; source-specified scores/preferences/network | Announced count vector; history for repeated polls; report distance `0.5 L1`, nonnegative counts summing to N | S13 unilateral voter response versus S14 one-shot response; not interchangeable; deterministic search ordering must be declared; source algorithms not integrated; separate bounded controller heuristics exist |
| E: network controller | Target victory/margin; explicitly declared controller knowledge | Legal supporter/seed/edge changes; cumulative intervention/cost log and residual budget | Voter/diffusion dynamics inherited from source; finite controller budget does not prove downstream voter convergence |
| C: campaigner | Target margin/win or party vote/office objective; source-specific rankings/positions/history | Seed/rank/perception/platform changes; beliefs and contact state only where specified | Diffusion, spatial response and party adaptation are separate models; no assumption they inherit V scheduling or termination |
| D: defender | Reduce expected switched voters under attack; declared channel exposure/preferences | Budgeted channel allocation; optimization iterates/mixed strategy | S18 finite optimization iterations; sampled play not ballot absorption; tie/solver settings require explicit configuration |

### Voter response candidates

| Method | Source/page | Objective / distinguishing inputs | State, parameters / complexity | Status and convergence limitation |
| --- | --- | --- | --- | --- |
| `pivotal` | S13 pp.2-3 | Preferred achievable plurality winner from maintained public poll | Poll plus observed-sender history; candidate-response scan | I; simultaneous/local-belief departure from unilateral source dynamics |
| `memory_pivotal` | S9/S12/S13 adaptation | Preferred achievable predicted winner from blended recent-contact estimate | Explicit initial poll, rolling unique-neighbor cache, public N; exact score comparisons | I; simultaneous; uncertified, known small-domain cycle |
| `expected_utility` | S9 pp.2-3 | Exact expected winner utility under inferred multinomial scores | Local sample or poll; utility vector; score space `choose(N+m-2,m-1)` | I; includes multiway/near ties, deterministic election ties; not paper Full |
| `top_k` | S10 pp.2-4 | Sum pairwise pivotal utility gains over K leaders | K; restricted score enumeration; no cross-round memory except optional poll | I; K=2 exact ties can vanish for odd other-voter total |
| `max_m` | S10 pp.2-4 | Largest pairwise pivotal utility gain | Same support model; enumerated pair states | I; distinct objective, not exact-EU optimization |
| `tie_u` | S10 pp.2-4 | Sampled sum of pairwise gains | Samples; enumerate tie states then uniform sample; corrected sum estimate | I; sampling RNG; enumeration remains; no absorption proof |
| `tie_h` | S10 pp.2-4 | Heuristic tie-state likelihood sum | Samples; nonuniform feasible tie allocations | I; stochastic approximation; not unbiased uniform sampling |
| `tie_r` | S10 pp.2-4 | Estimate tie-event probabilities | Samples; multinomial draws; workload depends on N,m,samples | I; zero observed ties possible; resampling may reactivate decisions |
| `poisson` | S10 pp.2-4 | Pairwise gain under independent Poisson scores | Numerical PMF/CDF truncation; means from authorized support | I; differs from paper asymptotic Skellam; numeric error distinct from convergence |
| `local_dominance` | S6 pp.10-14 | Strictly dominate current action over possible score worlds | Fixed-total L1 radius or explicit worlds; world enumeration and action comparisons | I; current uncertainty/scheduler differ from restricted source theorem |
| `maximin` | S2 pp.8-10, §5.1 | Maximize worst possible winner utility | Same score-world contract; enumerate actions × worlds | I; decision criterion, not full epistemic-game solver |
| k-pragmatist | S5 pp.4-5; S7 pp.4-6 | Favourite among poll top k; NOT Top-K EU | Leader count k; sort scores, apply ranking | N; source sequential/one-shot conditions; no full-model certificate |
| Attainability-Utility | S7 pp.4-6 | Utility-attainability tradeoff from poll | alpha,beta,epsilon; candidate-wise sigmoid/objective calculation | N; parameters need calibration split; prediction fit not convergence proof |
| LD + leader bias | S7 pp.4-6 | Dominance with source-defined leader-biased fallback | Radius/bias; uncertainty state; precise source tie semantics prerequisite | N; must not invent fallback or transfer basic LD theorem |
| Truth-biased LD | S6 pp.22-28 | Dominance plus source truth-bias preference | Source bias/uncertainty assumptions; world checks | N; proof domain must be mapped separately |
| Lazy-biased LD | S6 pp.22-28 | Dominance plus source laziness preference | Abstention/action semantics prerequisite; not ordinary inertia | N; current ranked nonempty ballot API may need extension |
| sincere | Existing baseline | Private ranking prefix | No strategic memory; O(k) | C; stable only while preferences/ballot overrides fixed |
| sensed/local plurality | Existing controls | Highest observed/reported support | Sensor deduplication or delivered reports; count + ranking | C; synchronous two-person cycle refutes unrestricted guarantee |

Defaults for implemented variants remain in [voting reference](../voting-heuristics.md).
Human prediction classes/learned models from S7 are optional data-dependent work,
not automatic candidate additions. Source Full is an additional decision oracle,
not an alias for implemented exact EU.

### Poll, network, campaign and defense candidates

Listed source algorithms are N (not integrated). Separate campaign/poll/ideal/leader
controller heuristics exist; they are adaptations, not these paper algorithms. Controller
knowledge is an explicit access contract, never permission for voters to read truth.
Tie-breaking/scheduling not reported in a source stays unresolved until specified
in a separately approved implementation plan; such candidates remain ineligible.

| Method / track | Source/page | Objective, inputs and action | Memory / parameters / complexity / prerequisites | Convergence evidence |
| --- | --- | --- | --- | --- |
| Ordered winner/challenger pairs / P | S13 pp.7-8 | Constructive/destructive, plurality/veto separately; poll/vector and voter responses | Rank candidate pairs; graph/preferences per source; distance/search limits | Finite report search; no full-system absorption proof; veto unsupported |
| 2PW-H / P | S14 pp.5-8 | Fix target/specter, construct two-potential-winner report | k report budget, pivotal threshold; source construction | One-shot source election; not repeated dynamics |
| Global Heuristic / P | S14 pp.5-8 | Evaluate specters for target victory | Repeat 2PW-H over specters; deterministic tie order prerequisite | Same one-shot limitation |
| Restricted 2PW-H / P | S14 pp.5-8 | Restricted report construction | Source admissible reports/culture assumptions | Analytical probability bounds, not temporal convergence |
| Supporter-edge construction / E | S11 p.3, pp.6-8 | Select useful supporter connections from poll + neighbour counts | Rank bags, edge budget; repeated stabilization dependency | Stabilization subroutine cannot be assumed convergent in mobile engine |
| MOV constructive/destructive greedy / E | S17 pp.2-3,7-8 | Expected margin change via influence surrogate; seed set | Cascade samples, seed budget; repeated marginal-gain estimation | Progressive cascade finite; strategic voter extension unproved |
| POV constructive/destructive / E | S17 pp.2-3,7-8 | Target win/loss probability via threshold surrogates | Seed budget, threshold/diffusion samples; MILP comparator on small cases | Optimization termination != voter absorption |
| Restricted influence greedy / E | S16 pp.13-24 | Margin improvement via seeds/edge actions in stated susceptibility regime | Restriction-specific prerequisites; influence oracle | Formal approximation only in stated regimes; centrality counterexamples |
| Degree / PageRank / VoteRank / E | S16 pp.19-24; S23 pp.9-13 | Structural seed/edge baseline, not guaranteed objective optimizer | Centrality state, budget; graph preprocessing, PageRank tolerance | Baselines only; theoretical counterexamples; no convergence certificate |
| SP degree/neighbour/PageRank variants / E | S23 pp.9-13 | Signed/target-position-aware influence ranking | Named positional/reverse/merged variants, influence and budget; ranking + diffusion | Repeated campaigns do not establish full-model convergence |
| Weighted influence-surrogate greedy / C | S19 pp.4-7,22-27 | Target score/margin via threshold ranking diffusion | Alpha, seed budget, edge weights, diffusion RNG; repeated influence estimates | Source diffusion not strategic ballot response |
| Representative-point / LP control / C | S22 pp.2-6 | Alter voter perceptions to elect target | Spatial geometry, perception budget, exact solver/geometry | One-shot feasibility; not repeated adaptation |
| Aggregator / Hunter / Sticker / C | S30 pp.4-9 | Party vote-seeking/platform adaptation | Prior support/platform, step settings; geometric/update scans | Fixed rounds/burn-in, not absorption theorem |
| Governator / Satisficing Governator / C | S30 pp.4-9 | Government/office-seeking party adaptation | Government formation and dissatisfaction state; coalition/response evaluation | Source simulation evidence only |
| FTPL / D | S18 pp.2-5,7 | Zero-sum expected switching; disjoint linear channels | Iterates, perturbation RNG, budgets, T, learning rate; optimization oracle | Game/optimization bounds != pathwise ballot stability |
| Gradient attacker + greedy defender / D | S18 pp.2-5,7 | Nondisjoint channel attack/defense | Exposure model, projected/exponentiated gradient, mixed iterates; oracle cost | Same limitation; requires separate voter/channel model |

Exact ILP/Presburger methods (S20/S21), participation DP (S25), shift-bribery
algorithms (S26) and MILP best responses are scoped comparators/prerequisites,
not heuristics to fill shortlist slots. S31 credibility targeting needs new
belief/turnout state; S27/S28/S29/S32 remain adjacent model inspiration.

## 3. Experiment specification — formal evaluation pending

1. **Correctness:** hand-computed/or exhaustive tiny-state oracles, permissions,
   legal ballots/budgets, source-method deviations, deterministic ordering,
   resume/rewind/RNG and CLI/browser equivalence. No weakening failed assertions.
2. **Feasibility:** use [confirmed foundation domains](../convergence-foundations.md)
   for certified claims. Other compositions may run as labelled exploratory studies,
   retaining cutoffs and possible cycles; no proof inferred from finite observations.
3. **Calibration:** seeds 1000-1029; freeze versioned parameters/objectives and
   scenario matrix before held-out evaluation. Existing defaults unchanged.
4. **Evaluation:** seeds 2000-2029 minimum per cell; independent additional blocks
   of 30 only under predeclared precision/budget extension, never selective reruns.
   Pair initial electorate/exogenous streams; isolate stochastic policy streams.
5. **Scenario cells:** certified v1 uses k=1 and eligible case settings only.
   Proposed later stress matrix: N=100,200,499,500,501; m=3,5;
   tiny enumerated cases are verification only, never outcome simulations.
   k=1 or m in separately admitted domains; sincere starts; IC and single-peaked preferences; static disconnected,
   ER, homophilous and proximity graphs; movement off/on; homogeneous and 50/50
   mixed policies. Out-of-domain cells are exploratory, not certified results.
   Record exact generators/degree/exposure settings in approved
   scenario manifests before execution; do not invent missing source parameters.
6. **Comparability:** clean voter cells use identical observations/utility/scheduler;
   local and public-poll tracks separate. Attack cells paired with no attack and
   legal equal-budget random interventions; budget fractions 0,.01,.05,.10 of
   explicitly named units (voters/edges/count transfers), never interchangeable.
   Missing attack models block their cells, not silently replaced with edits.
7. **Horizons:** no finite cutoff establishes convergence. Use proven bounds where
   available; otherwise a declared 1000-round resource cutoff labels runs censored.
   Never run unresolved candidates merely to manufacture certificates.
8. **Statistics:** report all runs, failures and paired differences; 95% run-level
   bootstrap intervals (10,000 resamples, separate saved RNG seed 9000), Wilson
   intervals for proportions, distribution/range and denominator per cell.
   No voter-level pseudo-replication or pooled cross-role rankings. Runtime isolated
   from plotting/I/O; record hardware/environment; numeric reproducibility scope explicit.

Future experiment artifact contract: config/source/dependency hashes; source
variant/proof domain; role/objective; allowed observations/actions/budget; seeds
and RNG state; command/environment; raw frames/checkpoints; per-run metrics,
status/reason/censoring; aggregate uncertainty. Extend existing comparison outputs
without changing defaults; no new CLI/API implemented by this document.

## 4. Deliverables and selection

| Step | Deliverable | Gate/status |
| --- | --- | --- |
| Corpus | 31 full-text records; 36 preserved PDFs; stable IDs/hash manifest | Complete; validation below |
| Audit | Role-specific register, implementation departures/prerequisites | Complete; no new heuristic validated |
| Convergence | Source theorems, F3 potential proof, exhaustive tiny-model checks | F1–F3 implemented with guards/certificates; F4/F5 scheduled edits supported |
| Metrics | Formula/eligibility/aggregation dictionary | Specified; not runtime implementation |
| Experiments | Frozen manifests, acceptance tests, reproducible raw/aggregate outputs | Small exploratory pilot complete; formal held-out evaluation pending |
| Shortlist | Discuss qualifying methods by behaviour; choose number afterward | Pending; no forced top five |
| Implementation | Separate plan per selected method; cumulative stage gates | `memory_pivotal` implemented for exploration; other selections pending |

## Progress

Corpus/method audit complete:31 works/36 PDFs, stable IDs. Restricted F1–F5
integrated; memory-voter implemented for exploration. Current N>=100 floor
does not certify it. Existing bounded controllers, detector and
mechanism comparison tools are not source-algorithm replications or certified
attacker/defender compositions. [Current evidence](../implementation-status-report.md).

Next deliverables: frozen experiment manifests, metric implementation gap list,
role-specific results and shortlist discussion. No forced five or cross-role score.
