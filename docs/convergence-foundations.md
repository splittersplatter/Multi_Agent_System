# Confirmed-convergence research foundation

[Moving-network analysis](dynamic-network-stability.md): quiet ballots are not a
certificate; existing guarded cases below remain unchanged.
The [retired grid occupation-frequency contract](plans/stochastic-stability.md) is
historical evidence, not a current runtime model. Its time-average result does not
establish ballot absorption, F1–F5 membership or convergence of the current normal walk.

Adopted scope: **restricted, explicitly certified cases**, requested 7 November
2026. The unrestricted simulator remains available and non-guaranteed. F1–F3
and finite scheduled F1/F3 interventions now use the shared engine.
[Dossier](heuristic-convergence.md) · [Evaluation plan](plans/heuristic-evaluation.md) · [Metrics](heuristic-evaluation-metrics.md).

9 November: [memory-based voter analysis](memory-voting-convergence.md) refutes
the original size-unrestricted `memory_pivotal` proposal under simultaneous updates, fresh complete
proximity and an accurate poll. No contradiction with the different F1–F5 guarded
policies below. N>=100-only memory-voter convergence remains uncertified; its
implementation is available for exploratory runs. Foundation runs also require N>=100.

## 1. Foundation cases

N unit-weight voters, m fixed candidates, strict fixed private rankings, fixed
deterministic election tie order. One voter updates at a time; others keep their
ballots. Latest committed observations are delivered before that update.
No intervention, candidate/preference change or observation-changing movement
during a certified relaxation episode. No vote locks or artificial quiet-window stop.
Response rules are pure functions of the declared current observations/ranking
and fixed parameters; no independent round-dependent action, plugin memory drift
or fresh decision sampling is permitted in these proof domains.

| ID / priority | Behaviour and information | Confirmed result | Bound: successful ballot changes | Engine status |
| --- | --- | --- | --- | --- |
| F1 / first | Direct best-response plurality; current truthful aggregate scores and own preference; any initial ballots | Pure Nash equilibrium; S4 Theorem 3 | <= m²N²; truthful start <= mN, source proof p.6 | Implemented: `direct_best_response`; initial ballots sincere, arbitrary ballots via scheduled interventions |
| F2 / second | Homogeneous source local dominance; truthful start, shared integer radius r, variable-total L1 worlds centred on actual other-voter counts | Source voting equilibrium; S6 Theorem 4 | <= N(m-1) | Implemented: `source_local_dominance`; distinct from prior fixed-total `local_dominance` |
| F3 / network control | Local plurality/conformity on a fixed simple undirected unweighted graph; own ranking breaks local support ties; current neighbour ballots | Fixed point of local response; bounded integer potential proof below | <= m|E| + N(m-1) | Implemented: `certified_conformity`; explicit public ballot sensing required |
| F4 / future attack studies | Finite genuine interventions, followed by F1 relaxation after the final event; preserve attacked ballots, no sincere reset | Eventual F1 Nash equilibrium of final fixed election | <= m²N² changes after final event | Scheduled ballot/preference changes implemented; budgeted controller algorithms pending |
| F5 / network recovery | Finite scheduled ballot/preference changes, then F3 on the unchanged undirected graph | Local-response fixed point | <= m|E| + N(m-1) changes after final event | Implemented; graph interventions and budgeted attackers excluded |
| F0 / sanity control | Fixed sincere voters with fixed rankings | Ballots constant after initialization; not a strategic equilibrium claim | 0 from sincere initialization | Existing control; exclude from competitive strategic shortlist |

F1-F3 are **different cases**, not a proof for mixing their voter policies. They
support different research behaviours; no balancing into one score or forced five.
F4/F5 are composition protocols, not additional ballot heuristics. Convergence need not
produce consensus, the same winner across schedules, or a welfare-optimal winner.

### F1: exact response and source assumptions

Let s_-i exclude voter i. Compute each achievable outcome w(s_-i+e_c), select
the most-preferred achievable winner c*. Move **only** if c* is strictly preferred
to the current winner, and vote for c* itself. This is a direct best reply, not
an arbitrary ballot producing the same winning outcome. Retain ballot otherwise.

The source proves finite improvement from every initial ballot state for unit
weights, fixed deterministic election ties and singleton updates. Do not extend
it to weighted voters, simultaneous updates, approximate polls, alternative best
reply tie choices or arbitrary better replies. Current `pivotal` belief updates
and action selection require a line-by-line mapping; policy name alone is insufficient.

Source: [S4 expanded proceedings](https://comsoc-community.org/assets/proceedings/comsoc-2010/Meir.pdf),
PDF p.5 Theorem 3/footnote 4; p.6 proof and bounds. [Full-text audit](literature-heuristics-and-metrics.md#s4--convergence-to-equilibria-in-plurality-voting).

### F2: exact uncertainty and response

S_i(a,r) = {z in nonnegative integer m-vectors: ||z-s_-i(a)||_1 <= r}.
**Do not impose sum(z)=N-1.** Actual electorate remains fixed; hypothetical worlds
may have different totals. This is the paper's epistemic uncertainty, not real
voter creation/removal. Every voter uses the same r and a truthful initial ballot.

d dominates current choice c iff d's winner is weakly preferred in every z and
strictly preferred in at least one z. Choose the most-preferred dominating
candidate; retain c if none. Equilibrium means no such dominance move exists,
not absence of all actual-state profitable deviations when r>0.

Proof skeleton: on source-reachable truthful-start paths, moves are compromises;
abandoned candidates cease to be possible winners; the possible-winner set only
shrinks. Each voter makes at most m-1 changes. Current fixed-total L1 score worlds
are a different uncertainty set: reducing radius or changing scheduler alone does
not reproduce this theorem. No mixed radii, stale local estimates or arbitrary starts.

Source: [S6](https://arxiv.org/abs/1404.4688v2), collected PDF pp.11-13 Definitions
1-4 and variable totals; p.17 Theorem 4, pp.17-19 proof. Appendix p.33 Theorem 10
requires Lemmas 2/3: not permission to transfer guarantees to any metric.

### F3: graph-based convergence proof

E contains each undirected edge once. Define q_i(c)=m-1-rank0_i(c),
A(b)=number of agreeing edges, and Phi(b)=m*A(b)+sum_i q_i(b_i).
Local response selects maximum neighbour-support count, then own preferred tied
candidate; isolated voters select their private favourite.

For a singleton change c->d, let Delta h be the change in neighbours supporting
the voter's choice. Only incident edges change, so Delta A=Delta h.

- If Delta h>=1, Delta Phi >= m-(m-1)=1.
- If Delta h=0, d wins the fixed private-ranking tie over c, hence Delta q_i>=1.
- Choosing a maximum-supported candidate cannot give Delta h<0.

Therefore every first-choice change strictly increases integer Phi, with
0<=Phi<=m|E|+N(m-1). Every changing path terminates within that bound. Fair
activation and a full unchanged sweep establish that every voter is at a fixed
point. Consensus is not required. This is an elementary local-coordination
argument, **not a novelty claim or a strategic election-utility theorem**.

Domain exclusions: directed/asymmetric observations, changing graph, stale reports,
simultaneous updates, changing rankings and extra independent tie RNG. The
verification helper includes a fair directed singleton six-cycle and the previous
synchronous two-cycle, demonstrating why those exclusions matter.
Per-group or per-person receiver radii can create directed proximity arcs; the
F3 scenario validator checks symmetry of the complete initial public graph before
certification. Stationary/unchanging-graph restrictions still apply.

### Scheduler, ballot and stopping contract

- Implemented reproducible scheduler: deterministic cyclic voter-ID order; one
  activation/commit per microstep. A sweep contains N activations. Alternative
  fair singleton schedules need separately logged order; outcome uniqueness not assumed.
- Bounds above count **changes**, not idle activations, browser frames or sweeps.
  Cyclic scheduling reaches a confirming unchanged sweep after at most
  N*(B+1) activations for a change bound B. No idle actor may starve others.
- Start certification with ballot length k=1. A later ranked-ballot extension must
  use a fixed private-ranking suffix and canonical initialization, proving full-ballot
  absorption separately; first-choice proofs alone do not cover arbitrary suffix plugins.
- Fresh no-change responses for every voter in one uninterrupted unchanged sweep,
  with fixed exogenous state, certify a policy fixed point. F1 additionally checks
  every unilateral ballot for no strictly better winner. F2/F3 use their own objectives.
- Store case ID, assumptions, scheduler index, source rule, observation version,
  accepted transitions, initial state and terminal response audit. Unsupported
  configurations fail certification explicitly; never silently coerce settings.

### F4: attack, then relaxation

Allow a finite number of legal, recorded intervention events, with the final one
at finite time L. After L, fix preferences/candidates/ties/observations and apply
F1 from the actual resulting ballot vector. Its any-start theorem guarantees
finite post-intervention relaxation; neither truth resets nor forced ballot locks
are required. Different finite stages may each reach different equilibria.

This does not prove convergence of an endlessly adapting attacker-defender game.
Finite spending only ensures finitely many attacks when every event consumes a
strictly positive nonrenewable unit and no zero-cost/replenished interventions are
allowed; stopping events do not stop endogenous cycles under uncertified voters.
Arbitrary false signals after L also violate the fresh truthful-information contract.
Graph-only attacks cannot affect F1 when voters depend solely on exact global
counts: this is a null-effect control, not a useful edge-attack experiment.

### F5: finite interventions, then network recovery

After the final scheduled ballot/preference event at finite round L, take the
actual resulting ballots and final fixed rankings. For unchanged undirected E,
the F3 potential is a bounded integer and strictly increases at every subsequent
changing singleton response, regardless of the ballot vector at L. At most
`m|E| + N(m-1)` changes follow; cyclic activation reaches a full-response fixed
point within `N*(m|E| + N(m-1) + 1)` further activations. The bound excludes
changes at or before L. No statement about earlier monotonicity is needed: a
preference intervention can change the potential itself. A fixed point is local
conformity, not necessarily Nash equilibrium or consensus.

This is a composition of the F3 proof, not a distinct literature theorem.
Implemented events are only scheduled ballot/preference changes, on the original
fixed graph. Status stays `pending_intervention` until the final event has
committed; a horizon before that event is a cutoff, never a certificate. The
same argument would permit a finite graph-change prefix **if** its eventual graph
were fixed and undirected and fresh sensor conditions held, but graph edits are
not implemented in this certified case. F2 cannot inherit this result: its
source theorem assumes truthful initialization, not arbitrary post-event ballots.

## 2. Deferred source-supported extensions

| Extension | Source condition | Why not foundation v1 |
| --- | --- | --- |
| Opportunity-priority LD from arbitrary starts | S6 Proposition 6, pp.20/36-37: shared r, opportunity moves first, eventual singleton selection | Choose deterministic singleton opportunity-priority scheduling to avoid confusing chance with every-path guarantee; implement/source-map separately |
| Truth-biased LD | S6 Definition 5/Proposition 7, pp.20-21/37-40: truthful start, common r, k_i>r; source iterative scheduling; <=3Nm moves | New bias-response rules, separate proof mapping; differing bias thresholds do not justify heterogeneous r |
| Lazy-biased LD | Same source; abstention action and stated conditions | Current ballot invariant forbids abstention; no silent ballot-API change |
| Frozen nonstrategic supporters + F1 | Restrict full direct-response transition graph; termination preserved | Endpoint is equilibrium only relative to active strategic agents; frozen actors not certified Nash players |
| Decoupled movement | Ballot transition independent of positions/graph for every legal movement | Requires noninterference proof; movement is not automatically safe just because one trajectory stayed stable |

EU/Top-K/Max-M/TieU/H/R/Poisson/maximin/AU/pragmatist and unrestricted policy
mixtures remain **uncertified**, not automatically disproved individually. They
may be studied later outside the certified track or after a separate theorem.

## 3. Run and inspect

Small linked TOMLs are explicit regression fixtures, not production scenarios.
Use the verification helper for exact checks; it cannot serve a browser:

```bash
PYTHONPATH=src python3 scripts/verify_fixture.py run examples/certified-direct.toml --until-equilibrium --summary
PYTHONPATH=src python3 scripts/verify_fixture.py run examples/certified-local-dominance.toml --summary
PYTHONPATH=src python3 scripts/verify_fixture.py run examples/certified-conformity-intervention.toml --until-equilibrium --summary
```

A normal outcome/browser run needs a deliberately configured N>=100 scenario
satisfying the same certificate guards. No large certified preset is asserted here.

Each step activates one voter in sorted-ID cyclic order; `round` counts activations.
Verification, 8 November 2026: `--summary --until-equilibrium` reached F1 Nash,
F2 policy and F3 policy fixed points at activation 1 in the supplied examples;
F4 reached Nash at activation 6 after its scheduled interventions. These are
smoke checks, not proofs or comparative experiments. The independent exhaustive
oracle checked 111,490 F1 states, 4,704 F2 profile/radius cases, and 127,758 F3
changing transitions; its finite checks supplement, not replace, the proofs above.
Scenario `[convergence]` chooses a case; all effective voter policies must match it.
Direct/LD cases explicitly grant the exact current aggregate to voters; conformity
requires public ballot sensing and a symmetric union of public graph layers. All
cases require k=1, stationary voters, no graph policy or message sending. F2 has
common `radius` (0..20) and `max_states` (1..1000000); variable-total worlds,
maximum 32 parties. Limits fail explicitly, not via approximate fallback.

Browser and JSON/JSONL/CSV metrics report case, scheduler, next actor, number of
voters with an available move and status. `certified_equilibrium` is F1's Nash
condition; `certified_policy_equilibrium` is F2/F3's response fixed point.
`not_equilibrium` means a move exists; `unavailable` records an enumeration
limit; `pending_intervention` prohibits certification until all scheduled events
have occurred. Browser updates automatically. Full equilibrium checks evaluate
all voters, not just the next actor. Interactive changes/policy switching are
rejected during certified episodes; use an unrestricted scenario for editing.

F1 and F3 permit finite scheduled ballot/preference changes. Preference edits apply at
the boundary; a ballot override applies after that round's voter action. The
following steps relax from that actual resulting state. Status remains pending
while any event is scheduled, including events beyond the configured run horizon.
F2 rejects interventions; F3 rejects graph and other interventions. There are no
certified attacker budgets/controllers.
`--until-equilibrium` is supported by `run` and `resume`; configured `rounds` or
`--rounds` remains a hard maximum. A cutoff with `not_equilibrium`, `unavailable`
or `pending_intervention` is not convergence. Browser playback pauses on a
certificate; manual steps remain available.
Checkpoints preserve scenario, scheduler position (committed round), and trace;
resume verifies all frames by replay. Existing simultaneous scenarios are unchanged.

## 4. Verification and remaining implementation

Independent deterministic verifier: [script](../scripts/verify_convergence_foundations.py).
It enumerates mathematical transition systems, not simulator executions. It checks
all enabled singleton transitions/paths in its declared tiny domains; universal
guarantees come from the proofs, never extrapolation from these finite checks.

```bash
python3 scripts/verify_convergence_foundations.py
```

- F1: every ranking profile/start, N=1..4 and m=2,3; acyclicity and source bounds.
- F2: every ranking profile, N=1..3/m=2 and N=1..4/m=3; r=0,1,2; truthful-reachable
  state DAG and N(m-1) change bound; source variable-total worlds retained.
- F3: every simple undirected graph, ranking profile/start, N=1..4/m=2 and
  N=1..3/m=3; strictly increasing potential on every changing singleton transition.
- Negative controls: synchronous copying cycle, directed sequential copying cycle,
  nondirect better-reply cycle, and source-world vector excluded by a fixed-total
  implementation. The DAG checker must explicitly reject the known directed cycle.

Integration and remaining implementation order:

1. **Implemented:** singleton scheduler, current score/sensor observations,
   checkpoint/replay, certificate validation and F1/F2/F3 rules. Independent
   transition oracle tests cover all two-voter, three-candidate preference profiles.
2. **Partial:** F4/F5 scheduled ballot/preference interventions and matched `batch`
   controls. Real attacker strategies, resource budgets and related metrics pending.
3. **Pending:** efficient bounded-world search at scale; broader state-space
   testing; additional certified source variants, cumulative attack mechanisms,
   multi-seed election-quality/cost evaluation and final selection.

Acceptance includes fresh versus stale observations, fixed deterministic ties,
N=1/m=1 boundaries, malformed/unsupported contracts, queued messages, rewind edits,
pending future events, differing radii, asymmetric graphs and source-to-engine
oracle disagreement. Guard checks must never silently certify unsupported modes.

## Verification evidence

[Independent checker](../scripts/verify_convergence_foundations.py):
F1 1,584 preference profiles/111,490 states; F2 4,704 profile/radius cases;
F3 2,904 graph/preference cases/127,758 changing transitions. F5 independent
post-event oracle checks512 configurations (`test_certified_direct.py`).
These are tiny mathematical checks, not outcome workloads or universal empirical bounds.

Engine tests cover scheduler/current observations, source-rule oracles, pending
events/cutoffs, unsupported mixtures, forged checkpoints, replay and exports.
[Current suite evidence](implementation-status-report.md#verification).
Budgeted controllers, broader certified variants and comparative studies remain
pending **inside these certified domains**; uncertified controller features elsewhere
do not inherit the guarantees.
