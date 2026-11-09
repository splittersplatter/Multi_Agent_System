# Convergence dossier

7 November 2026. **Original size-unrestricted full-model guarantee: refuted.**
Analytical audit only; no new simulator experiments.
[Candidate plan](plans/heuristic-evaluation.md) · [Source audit](literature-heuristics-and-metrics.md).

**Subsequent decision, 7 November:** user requested confirmed-convergence cases
as the foundation. [Restricted cases and proof checks](convergence-foundations.md)
now define that scope. The tiny counterexample below remains a formal statement about that original
domain, not an admissible normal run after the N>=100 requirement. F1–F3 and scheduled F4/F5 are now
implemented under those guards; unrestricted simultaneous modes remain uncertified.

## Required property and observability

Let X_t contain ballots, preferences, positions, graph layers, policies, memory,
messages, budgets, RNG state and future schedules. B(X_t) is the submitted ballot
vector. Required: for every admissible initial X_0 and permitted execution,
there exists finite T such that B(X_t)=B(X_T) for every t>=T.

- Deterministic seeded replay is repeatability, not termination.
- Almost-sure absorption permits exceptional infinite paths; weaker than the
  requested every-execution guarantee. Expected stopping time is different again.
- A ballot-stable window or constant winner is not an absorbing-state certificate.
- Nash equilibrium additionally excludes profitable permitted unilateral actions
  under specified objectives/information; no-flips alone does not prove it.
- Ballot absorption may coexist with movement. A certificate must show every
  reachable future observation/action preserves ballots, not merely the next frame.
- Horizon, timestamp and RNG-dependent policies prevent assuming a finite
  time-homogeneous state graph. Any abstraction must preserve possible flips.

## Counterexample in original small-domain semantics

Permitted composition: two people, two parties, ballot length 1; private rankings
u: A>B and v: B>A; both use `sensed_plurality`; public-ballot sensing enabled;
persistent directed edges u->v and v->u; no movement, messages or interventions;
no proximity contacts required. Initial sincere ballots are (A,B).

| Time | u observes v | v observes u | Committed ballots (u,v) |
| --- | --- | --- | --- |
| 0 | — | — | (A,B) |
| 1 | B | A | (B,A) |
| 2 | A | B | (A,B) |

The voting rule copies the sole neighbour's previous first choice. Both updates
use previous ballots, hence `(a,b)->(b,a)` indefinitely. Induction establishes
two flips per step for every horizon; ties/ranking/RNG never enter the decision.
The election winner can remain A under the fixed election tie rule throughout.
Thus even a stable winner gives no evidence of ballot absorption.

Static code evidence: [sensor delivery](../src/multi_agent_election/engine.py),
`sensed()` uses `previous_ballots`; voting branch `sensed_plurality` picks the
most frequent observed first choice; all ballots commit after the voting loop.
This is a hand-derived transition proof, not a newly executed regression test.
Finite configured rounds merely truncate the cycle; extending the same rules
does not produce convergence. Fair simultaneous activation already holds.

This refutes a guarantee over the original size-unrestricted mixtures. It does **not**
prove each strategic candidate independently divergent, or exclude the possibility
of a different certified composition. Open-ended permitted ballot interventions
can additionally prevent absorption; finite budgets alone do not eliminate
endogenous cycles after those budgets are spent.

## Source theorem boundaries

| Evidence | Guaranteed/source result | Missing match in full simulator |
| --- | --- | --- |
| S4 PDF p.5, Proposition 2/Theorem 3; pp.6-7 proof | Simultaneous best replies can cycle; unweighted plurality/direct best replies with deterministic ties converge under unilateral updates | Simultaneous updates, incomplete/local information, heterogeneous rules and evolving observations |
| S6 PDF p.17, Theorem 4; pp.18-19 proof | Stated common-r strategic voters, truthful start, singleton scheduler: at most n(m-1) steps | Current fixed-total L1 variant must be checked against source uncertainty model; heterogeneity/mobility/attacks outside theorem |
| S9/S10 | Networked strategic simulation and approximation behaviour | Empirical outcomes are not full-model termination certificates |
| S14 | One-shot source response and manipulation bounds | No repeated strategic-response theorem |
| S16/S17/S19 | Source-specific influence/optimization guarantees | Finite cascade/search is not ballot absorption after strategic feedback |
| S18 | Source-specific optimization/game bounds | Mixed-strategy iteration/payoff bounds do not imply no future vote flips |
| S30 | Party-adaptation experiments/burn-in | No full mixed-agent absorption theorem |

Source evidence is indexed in the linked audit; PDFs are locally available.
No unrestricted mobile/mixed strategic composition has a full-model theorem;
F1–F5 have separate guarded mappings.
Unimplemented poll/network/campaign/defense methods lack a composed transition
system; certification remains unsupported, not assumed false from absence alone.

## Certification gate

For each proposed composition require: domain + initial-state assumptions;
policy/action/observation contracts; scheduler/fairness; future interventions;
then a well-founded potential/finite-improvement proof or sound closed absorbing
region proof covering every legal successor. For finite abstractions, absence of
reachable nonabsorbing recurrent behaviour needs rigorous abstraction justification;
enumerating a few traces is insufficient. Bound on T only if separately established.

Restricted confirmed cases have been adopted and implemented. Keep their proofs
separate from unrestricted modes. The memory-voter is available for exploratory
studies: its original four-voter witness does not decide the N>=100 domain, and no
positive theorem for that domain has been established. Do not infer convergence
from a population floor, quiet window or finite run.
