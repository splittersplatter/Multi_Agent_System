# Research improvement: exploratory and certified studies

User decision: use `memory_pivotal` with moving proximity, expiring memory and
simultaneous decisions for exploratory simulations. Proof is mandatory for
certified convergence claims, optional for explicitly labelled exploratory runs.
Status: **contract implemented; original-size guarantee refuted; N>=100 uncertified**.

Latest9 November: Gaussian moving baseline adopted; grid runtime retired. The
[grid proof](stochastic-stability.md) is historical only. Strict response/memory/
polls retained; frequency diagnostics are exploratory. Gaussian mixing/occupation
guarantees and the stronger ballot-absorption question remain open.

Population follow-up: outcome runs N>=100; small cases remain formal verification.
The prior four-voter refutation covers the original size-unrestricted contract;
N>=100-only convergence is not established by excluding the earlier witness.
[Population contract](minimum-population.md).

## A. Mathematical contract

The contract below describes the original fixed-poll model and its counterexample.
The current demo additionally publishes a completed tally every ten rounds and
linearly decays its poll weight. That updated composition needs its own proof;
the old fixed-poll witness is not automatically a witness for the new schedule.

- Fixed candidates/tie order, strict fixed rankings, unit weights, k=1;
  homogeneous candidate rule. Public N, own ranking/current ballot, private cache,
  explicit immutable initial poll only; no evaluator truth/messages/other rankings.
- Existing cache: moved incoming proximity observes completed ballots r−1;
  unique latest first choices; retain encounters `[r−K+1,r]`; K=10, w=.5.
- Blend p_i as implemented. Counterfactual score for action c:
  `(N−1)p_i + e_c`; fixed election ties. Compare every action against retaining
  current ballot under that same estimate. Choose most-preferred reachable winner
  directly, only for strict predicted-winner improvement; otherwise retain.
- Rational/integer comparisons; no fabricated integer electorate or inherited
  complete-information theorem. Public N does not reveal identities.
- [Dossier](../memory-voting-convergence.md): source mapping, timing, full state,
  worked decisions, assumptions and proof/code obligations.

## B. Convergence gate

Universal property: every permitted initial state/execution eventually stops
changing submitted ballots. Distinguish this from winner stability, almost-sure
absorption, empirical quietness and belief stability.

- Seek potential/finite-improvement/absorbing-state argument; attack simultaneous
  updates, directed contacts, expiry, revisits, stale polls and heterogeneous inputs.
- Tiny verification: N2–5, m2/3, K1/2/10, w0/.5/1. Declare finite search family;
  do not claim enumeration of continuous positions or every possible cache/poll.
- Use implemented keyed motion; broader adversarial motion is a different domain.
- Ballot repetition alone is insufficient. Include normalized cache/time state,
  or prove an autonomous projection independent of unrecorded environment/RNG.
- Deliver theorem/domain mapping or verified counterexample/open-case dossier.
- Refutation/unsupported scope excludes certification, not exploratory runs.
  No automatic serialization, frozen contacts, altered memory or vote locks.

## C. Implementation and results

- Opt-in policy, explicit scenario population size, decision trace; shared
  engine/CLI/browser/export/checkpoint. Existing defaults unchanged; uncertified.
- Independent decision oracle, tiny-model agreement, privacy/atomicity/replay
  tests and full regression. Never expose an unavailable dummy selector.
- Freeze protocol; calibration1000–1029, evaluation2000–2029; matched exogenous
  streams, failures/cutoffs retained; independent run-level uncertainty.
- Separate absorption, dynamics, decision regret, welfare, estimation and cost.
  Exact-information policies are references, never substitutes for intended voters.
- Certified interventions need a composition proof, including post-event states.
  Exploratory interventions report finite horizon/cutoffs. Native-budget dose
  response; no cross-unit leaderboard.

## Gated backlog / critique decisions

| Suggestion | Decision/prerequisite |
| --- | --- |
| Counting rules | Defer; rule-aware ballots/responses/attacks/metrics/new proofs, not count-function swap |
| Common cost ranking | Reject equivalent units; report native realized costs + named denominators |
| Budget-to-flip bisection | Monotonicity required; otherwise smallest successful tested budget only |
| Interactions | One predeclared four-arm design; certify composition only for certified claims; 17 arms insufficient |
| Shapley | Define valid coalition interventions/value first; no novelty from integration alone |
| Adaptive attacker/CUSUM/defender | Observation/action authority, finite positive-cost events, composition proof, calibrated false alarms/delay |
| Trust/opinion dynamics/turnout | New state/action/proof contracts; defer |
| Demo tools | Reproduce validated results; provenance is not causal attribution without counterfactuals |

Method references: [factorial interactions](https://www.itl.nist.gov/div898/handbook/pri/section5/pri594.htm),
[CUSUM calibration](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm).

## Progress

9 November: contract/source mapping and independent rational oracle complete.
Original four-voter composition has an inductive moving-proximity cycle, not
merely a repeated finite trace. Evidence:
`outputs/memory-voting-convergence-2026-11-09-final.json`;
28,152 finite-family orbits/84,456 window cases and20,862 oracle decisions.
[Dossier](../memory-voting-convergence.md) preserves assumptions and limitations.

Later population floor does not establish N>=100 convergence. User authorized
exploratory implementation and finite-horizon outcomes. Preserve the counterexample
and proof obligations; no forced serialization or silent rule changes.
Current tests: [central evidence](../implementation-status-report.md#verification).
Five-seed implementation pilot and decision/replay checks:
[memory-pivotal report](../memory-pivotal-exploration.md).

Statistical follow-up:24-work evidence matrix and conditional finite-grid proof
draft completed as documentation. Startup/phase and relative ages are explicit;
independent review and future engine mapping remain open. No new experiments.
