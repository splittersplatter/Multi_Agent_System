# Stochastic stability: contract and proof dossier

9 November2026. **Historical contract: grid runtime retired by user decision.**
Current baseline: Gaussian motion; exploratory frequencies only. This dossier and
standalone checker preserve the reviewed grid proof, not a current-model guarantee.
[Evidence matrix](../dynamic-network-stability.md#24-work-evidence-matrix).
F1–F5 restricted certificates remain separate. New random walks default to Gaussian.

## 1. Selected target and scope

Target: almost-sure convergence of long-run occupation frequencies while contacts
continue changing. Preserve immediate strict predicted-winner improvement,
simultaneous decisions, recent memory and periodic truthful polls. No noisy worse
choices, voter waiting probability, locks, graph freezing or sincere resets.

| Property | Meaning | Status |
| --- | --- | --- |
| Observed quietness | No flips within a finite observed interval | Diagnostic only |
| Occupation-frequency convergence | Time averages approach a stationary measure of the reached recurrent class | Derived below for the specified ideal stochastic grid kernel |
| Distributional convergence | The law at time t approaches a limiting law | Not established; periodicity matters |
| Ballot absorption | No future ballot change after some finite time | Not established; cycles remain possible |

No inference of a unique winner, Nash equilibrium, welfare improvement, rapid
mixing, known settling horizon or convergence of the current continuous simulator.
The result is a standard finite-chain application, not a new strategic-voting theorem.
The same occupation argument applies to other finite-state response rules; it
does not establish that memory-pivotal is superior, realistic or research-distinct.

## 2. Frozen transition contract

### Parameters and initialization

- Fixed N, default200, normal workloads N>=100; fixed finite m>=2 candidates,
  fixed party-order election ties, fixed strict private rankings, unit weights, k=1.
- Homogeneous existing `memory_pivotal`; K=10 memory rounds; L=10 poll interval.
  Explicit initial poll P0, nonnegative integer counts, positive total. Initial
  sample need not sum to N. All later published counts sum to N.
- Round0: sincere ballots, empty encounter caches, P0, explicit integer grid
  coordinates for every voter. No initial sensing/strategic update or automatic
  snapping of continuous positions. Initial-state sensitivity uses separately
  declared valid starting states, never hidden resets within an episode.
- Space: `{0,...,40}²`; displayed coordinates `(x/40,y/40)`. Overlap permitted;
  common radius3/25=0.12. Directed arc j→i iff j!=i and within i's radius.
  Common radii make these arcs reciprocal; no graph-connectivity requirement.
- Exact contact comparison in grid units: for squared integer distance d²,
  `25*d² <= 576`. This is inclusive radius equality without floating-point ambiguity.
- Motion: independent proposals for each voter/round from stay,N,S,E,W, each1/5.
  One grid step=0.025. Out-of-bounds proposals stay, not wrap/reflect/resample.
  This discrete kernel is not a normally distributed step or a matched continuous
  trajectory. Continuous normal motion remains an exploratory comparator.
- Exclude interventions, messages, extra observation layers, policy plugins,
  adaptive parameters, changing candidates/preferences and decision sampling.

### One round r→r+1

1. Draw all motion proposals; commit new positions; derive proximity arcs.
2. Observe completed ballots b^r through incoming proximity only. Expire records
   outside the K-round encounter window; refresh one entry per encountered ID.
   Same-round insertion order is sorted voter ID, preserving the existing contract.
3. If r>0 and r mod L=0, publish the truthful tally of b^r for the new decision;
   otherwise retain the previous poll. Thus completed round10 first informs
   decisions in round11; no extra census is exposed between publications.
4. For decision round t=r+1 let d=1+((t−1) mod L). Poll weight is
   `w=(L−d+1)/L`:1,.9,...,.1. Empty cache uses poll alone. Otherwise
   `p_i(c)=w*P(c)/sum(P)+(1−w)*cached_count_i(c)/cache_size_i`.
5. For each hypothetical ballot a, predict
   `F_i(a)=winner((N−1)*p_i+e_a)` with exact rational comparisons and fixed ties.
   Baseline is F_i(current ballot). Choose the most-preferred achievable predicted
   winner c*, and vote directly for c* iff c* is strictly preferred to that baseline;
   otherwise retain. No added inertia; every available prescribed improvement is taken.
6. Commit decisions simultaneously. Save the completed state; poll publication
   uses the previous completed tally, never the simultaneously proposed ballots.

Poll and contact updates commute because both use b^r; the order above fixes the
implementation contract. The evaluator may tally all ballots; voter decisions
receive only the permitted poll, own ranking/ballot, N and contact cache.

### Finite state and timestamp quotient

At a completed round use `X=(x,b,M,P,phi,z)`:

- x: integer positions; b: submitted candidate IDs.
- M_i: encounter-ordered records `(neighbor, choice, encounter_age, source_age)`;
  encounter_age=r−last_seen in0..K−1, source_age=r−source=encounter_age+1.
  IDs unique, self absent; counts are derived, not independent hidden state.
- P: latest poll used for decisions; either P0 or an N-vote tally.
- phi=r mod L; z indicates **r=0**, then becomes false permanently.

The startup bit is essential: r=0 and r=10 both have phi=0, but only the latter
publishes a completed tally before the next decision. A flag retained until the
first publication would not distinguish these two boundaries sufficiently.

**Timestamp-equivalence argument.** Two valid absolute states with equal X,
equal fixed parameters and the same proposal vector produce equal successor X:
movement/contact tests use x; publication uses phi/z and b; each existing age
increments by1 and expires at K; all new encounter ages become0/source ages1;
recency ties use fixed ID order; score denominators use counts, P and phase.
No remaining decision depends on the absolute round. Old policy traces, display
timestamps and prior frame history are excluded only because this policy never
reads them. Source validation comparisons translate to the same relative ages.
An extension that reads history, absolute time or seed-derived decisions needs
a new proof. This quotient is not a replay/checkpoint format migration.

For fixed N,m,K,L a loose finite upper bound is

`|S| <= 2L * 1681^N * m^N * (1+binom(N+m−1,m−1)) * B^N`,
`B = (1+mK)^(N−1) * (N−1)!`.

The bound overcounts invalid caches/orderings; source ages are determined by
encounter ages. It establishes finiteness, not feasible enumeration at N=200.

## 3. Conditional mathematical result

Assume ideal proposals independently distributed across voters and rounds as
specified above. For each proposal vector u let T(X,u) be the deterministic
transition. Then

`P(X,Y) = number of vectors u with T(X,u)=Y / 5^N`.

The transition matrix is time-homogeneous: phase and startup state are explicit.
It need not be irreducible, reversible or aperiodic. Position self-loops do not
imply self-loops of the full state; the poll phase advances every round.

### A. Almost-sure entry into a recurrent class

The finite transition graph partitions into transient states and closed irreducible
classes. From each transient state a finite positive-probability path reaches a
closed class. Choose a common finite maximum path length h and minimum path
probability epsilon>0 across the finite transient set. By the Markov property,
the probability of avoiding every closed class for kh steps is at most
`(1−epsilon)^k`, tending to0. Entry time is finite almost surely, not bounded
deterministically; after entry the selected class C cannot be left.

### B. Occupation frequencies

Within C the finite irreducible chain has a unique stationary measure pi_C,
extended by0 outside C. For every bounded state observable f,

`(1/T) sum_{t=1}^T f(X_t) -> sum_x pi_C(x)*f(x)` almost surely.

Apply the finite-chain ergodic theorem after the finite entry time; the finite
prefix contributes0 asymptotically. Periodicity does not invalidate time averages.
For transition observables g use the finite chain of allowed consecutive state
pairs; its stationary measure is `pi_C(x)*P(x,y)`.
Our application combines standard class decomposition with
[Levin–Peres, Theorem C.1](https://pages.uoregon.edu/dlevin/MARKOV/mcmt2e.pdf)
(audited PDF406–407, printed390–391; SHA-256 in the evidence matrix).

Different executions can select different C. Across-run expected limits form a
mixture weighted by class-entry probabilities; pooling runs must not conceal this
variation. Fully aligned ballots/polls/caches for different candidates supply
disjoint closed ballot regions for N>=3. This rules out assuming global uniqueness;
it does not show every such region is reachable from one fixed sincere start.

### C. Poll-phase conditioning

In each recurrent class phi advances cyclically, so stationary mass of each phase
is1/L. Consequently the time average of f restricted to destination phase q tends
to `L * sum_{x:phi=q} pi_C(x)*f(x)`. For a transition observable, attach phase q
to the destination state. This proves phase-conditioned **time averages**, not
convergence of the instantaneous law along a phase subsequence.

### D. Continuing movement and contacts

The autonomous joint-position chain is irreducible on the finite product grid:
voters can follow any finite lattice path while others propose stay. Every state
also has a positive position self-loop. Thus every joint-position configuration
is revisited infinitely often almost surely. Agents keep moving; for every pair,
coincident and far-separated configurations recur, so their contact relation is
made/broken infinitely often at radius0.12. Ballot absorption, if it occurs, does
not imply stopped movement or a frozen network.

### Nonclaims and implementation boundary

- No ballot-absorption or Nash-equilibrium theorem; strict improvement concerns
  each voter's current **prediction**, not necessarily the actual election result.
- No per-round limiting law or useful finite mixing/settling bound. A deterministic
  two-cycle has stationary occupation1/2,1/2 but alternating instantaneous laws.
- Ideal independent draws are a theorem assumption. SHA-keyed seeded replay is
  not itself an infinite-i.i.d. process or a proof covering every seed. A future
  implementation must state the sampling abstraction and separately test replay.
- No theorem for current continuous motion, mixed policies or ongoing attacks.
  Finite-state availability alone does not prove a general-state Markov result.

## 4. Review and verification gates

**Independent analytic review passed; scoped engine correspondence tests passed.**
Exact tiny-model verification is now [implemented and recorded](../stochastic-stability-verification.md);
See [implementation plan](stochastic-stability-implementation.md) and
[verification/limitations](../stochastic-stability-verification.md).
Do not treat this document or a test pass as a stationary-distribution certificate.

Required review artifacts and acceptance:

1. Check A–D, finiteness bound, timestamp quotient and restrictions. Verify the
   initial-poll exception, inclusive contact formula and atomic simultaneous phase order.
2. Tiny formal fixtures only, explicitly `verification_scope`: enumerate declared
   N=2/3, two candidates,2×2 grid, K=1/2 and L=1/2 cases, with a2,000,000-state
   ceiling/case. Record skipped larger cases; no false exhaustive claim for K=L=10.
   Retain actual default-boundary symbolic/transition checks separately.
3. Independently derive the tiny rational kernel from enumerated proposal vectors;
   rows sum to1. Compute SCCs, closed classes and periods; solve stationary
   distributions exactly. Large-state ceiling is not a proof failure or success.
4. Challenge with two-cycles, multiple closed classes, directed-contact test
   extensions, isolation/re-entry, simultaneous swaps, K expiry and L poll reset.
   Directed variants test boundaries, not membership in the common-radius baseline.
5. Shift two valid histories by multiples of L beyond startup: require identical
   abstract successors/probabilities. Same ballots with different caches/phase
   must not be merged. Round0 versus positive round10 must remain distinct.
6. Future engine mapping: no non-improving action, hidden tally/ranking leakage,
   silent snapping or policy waits; CLI/browser/export/checkpoint/rewind agreement;
   unsupported proof-domain configurations rejected, legacy motion unchanged.

Worked algebraic fixtures, not simulation evidence:

- `P=[[0,1],[1,0]]`: one recurrent class, period2, pi=(1/2,1/2);
  occupation converges despite infinite flips. Per-round convergence claim fails.
- `P=[[1,0],[0,1]]`: two closed singleton classes; limit depends on start.
- `P=[[0,1/3,2/3],[0,1,0],[0,0,1]]`: transient0 enters either closed class;
  expected limiting occupation=(0,1/3,2/3), individual runs select one class.
- Deterministic10-phase cycle: uniform occupation over phases; phase-conditioned
  distribution can differ. A quiet window cannot establish entry into a class.

## 5. Evaluation specification; execution deferred

Use N=200, three candidates, K=L=10 and radius0.12 as the declared baseline.
Controls: sincere/grid; memory-pivotal/grid; memory-pivotal/continuous-normal.
Only the first two share exact motion streams. Across grid/continuous comparisons
match electorate, initial grid-aligned positions and initial poll, not trajectories.
Continuous results remain uncertified; no altered defaults in existing examples.

| Observable | Per-round definition | Aggregation |
| --- | --- | --- |
| Winner frequency(c) | 1[winner=c] | Mean; frequencies sum to1 |
| Candidate share(c) | submitted votes for c / N | Mean for each c |
| Ballot flip fraction | count changed submitted ballots / N | Transition mean; k=1 |
| Winner-change frequency | 1[winner_t != winner_previous] | Transition mean |
| Contact additions/removals | directed arcs in E_t\E_previous / E_previous\E_t | Separate event counts and normalized counts / N(N−1) |
| Poll-phase behavior | each above restricted to destination t mod10 | Separate phase means and cycle average |
| Initial-state dependence | same fixed model, separately declared initial state | Preserve per-state/per-run results; no forced shared limit |

Freeze later finite-horizon protocol before running: calibration seeds1000–1029;
held-out2000–2029; T=10,000 completed rounds/run, no early quiet-window stopping.
Store cumulative estimates from round1 and a fixed burn-prefix-excluded view
(discard first1,000; retain9,000). Burn-in is a sensitivity convention, not a
proved mixing time. Retain failures/cutoffs and source/configuration hashes.

For dependence diagnostics, split the retained view into90 nonoverlapping
100-round batches, aligned to10-round poll cycles; inspect batch means and
autocorrelation. Batch-based Monte Carlo error requires its own stationarity/CLT
conditions; without them label it descriptive. Across independent seeds report
run means, spread and initial-state sensitivity, not binomial errors treating
rounds as independent. Recurrent classes need not share an expectation.

Outcome studies require separate implementation approval and resource preflight.
Do not enumerate the N=200 full state space; stream observables and retain
reproducible checkpoints/raw summaries rather than every dense frame. Persistent
window drift/metastability remains a finite-horizon limitation, not grounds for
silently extending runs or declaring stationarity.
At N=200, recurrent-class IDs remain unknown without a valid certificate;
histogram clusters or matching winners are not recurrent-class identification.

## Progress

- 9 November2026: source passages audited; conditional finite-grid proof and
  state quotient written; startup flag added to prevent invalid clock removal.
- No grid code, new CLI option, runtime certificate or outcome experiment added.
- Follow-up gate: independent mathematical review, then a separate implementation
  plan covering existing engine/information/replay contracts. Two literature access
  blockers do not support, or invalidate, the accessible finite-chain foundation.
- Documentation checks:14 edited documents, balanced code fences and all local
  files/anchors valid;24 citation rows and24 model rows, exactly one of each/ID.
  Four worked stationary-measure identities and6,561 rational radius comparisons
  checked algebraically; no trajectories, grid enumeration or outcome studies run.
  Source/config/test/script aggregate hash unchanged:
  `4616c412f5983ef7c7115cfdad42250e5af4a07cb4342f0a475c374dd7784a1d`.
  `git diff --check` passed. Existing runtime test counts are historical evidence,
  not rerun by this documentation-only update.
- Later9 November: [formal checker](../../scripts/verify_stochastic_stability.py)
  and18 adversarial tests added. Eight declared two-candidate models fully
  explored:992 reachable states/23688 edges; exact stationary measures and
  phase mass1/L verified. Separate three-candidate simultaneous-change fixture.
  [Evidence/scope](../stochastic-stability-verification.md). Independent review
  remains pending; no production model/experiment/certificate or dependent
  implementation plan added. Earlier unchanged-source hash is historical only.
- Subsequent execution: independent review passed; user-approved grid runtime,
  guards, checkpoint24, browser/exports and streaming diagnostics implemented.
  Reviewer found override-detection/manual-queue gaps; fixed and re-reviewed.
  Scoped engine correspondence passes;414 full-suite tests,410 stdlib passes/4
  optional skips. [Evidence](../stochastic-stability-verification.md). Evaluation
  protocol remains frozen; no full research campaign or new convergence claim.
