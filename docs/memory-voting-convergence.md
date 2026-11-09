# Memory-based strategic voting: specification and convergence gate

9 November 2026. **Original-size universal claim refuted; N>=100 domain uncertified.**
`memory_pivotal` is now selectable for exploratory finite-horizon simulations;
it uses the existing estimator and does not inherit the F1–F5 certificates.
This dossier analyzes the original fixed-poll contract. The current demo uses
periodic tally publication and changing poll weights; the witness below does not
by itself prove a cycle for that revised composition.
[Maintained improvement plan](plans/research-improvement.md).

Later population contract: normal runs require N>=100. The four-voter witness
below remains a formal counterexample to the original unrestricted-size contract,
not an admissible production run or a proof about the N>=100-only domain.
That domain remains uncertified; the population floor establishes no convergence.

## 1. Frozen contract

Fixed N unit-weight voters, m candidates C, strict fixed private rankings,
fixed party-order election ties; plurality, k=1. Initially sincere ballots.
Homogeneous `memory_pivotal` response with each voter's own ranking/cache.
Public N is an explicit assumption; no electorate identity/hidden-ranking access.

At boundary r, full state includes `(b, M, x, E, poll, rankings, parameters, seed, r)`:
ballots, ordered caches and timestamps/counts, physical positions, graph, immutable
initial poll, own rankings, configuration and keyed-motion inputs. No independent
decision RNG. Private report/policy mixtures, changing preferences/candidates and
attacker/defender actions require separate contracts and composition proofs.

1. Move via existing actor/round-keyed bounded random walk; recompute incoming
   proximity from receiver radii, not outgoing arcs or remote graph layers.
2. Cache completed ballots b^(r−1): latest first choice per neighbor, source r−1,
   last-seen r; expire encounters outside `[r−K+1,r]` even without new contacts.
3. For cached n_i>0, `q_i(c)=cached_count_i(c)/n_i` and
   `p_i(c)=w*P(c)/sum(P)+(1−w)*q_i(c)`. Empty cache uses poll alone.
4. Treat p_i as other-voter propensity: `s_i(c)=(N−1)*p_i(c)`.
   It is NOT a factual count, nor a known electorate with rounded integers.
5. Define `F_i(a)=argmax_c(s_i(c)+1[c=a])`, using fixed party-order ties.
   Baseline `F_i(b_i)` and all alternative predictions use the same cache/poll.
6. Let c* be i's favorite member of `{F_i(a):a∈C}`. Submit c* only if
   `c* ≻_i F_i(b_i)`; otherwise retain b_i. Directly voting for c* elects c*
   in that estimated election: transferring the added vote to its predicted winner
   cannot worsen that winner's score relative to rivals.
7. Commit every voter's decision simultaneously from the common completed snapshot.

Round zero has empty caches/poll-only estimates, no strategic update. Defaults:
K=10, w=.5, explicit nonnegative integer poll with positive total. The proof target
retains movement, expiry and simultaneous voting; it does not silently restrict them.

Exact implementation contract: if p_i has integer numerators u and denominator D,
compare `(N−1)u_c + D*1[c=a]`. Public N and own vote are supplied once; do not
subtract the own vote from an already other-voter score. Poll contribution is a
propensity approximation; observing everyone does not automatically override w.

## 2. Source mapping — adaptation, not paper reproduction

| Source/evidence | Reused idea | Material differences / proof limits |
| --- | --- | --- |
| [S9](../References/S9-the-echo-chamber-strategic-voting-and-homophily-in-social-networks.pdf), PDFpp2–3 / printed369–370, §§2.2–2.3 | Infer population support from observed neighbor ballots; compare scheduling regimes | Paper uses Laplace-smoothed multinomial/pairwise expected utility, not our mean-score predicted winner; no rolling-cache/poll blend theorem |
| [S12](../References/S12-poll-confident-voters-in-iterative-voting.pdf), PDFpp2–3 / printed2206–2207, Definitions1–3 | Initial poll, belief-conditioned pivotal response, exclude own vote in counterfactual | Paper maintains score deltas, one deviator/step, graph-specific convergence; not memory-window re-estimation |
| [S13](../References/Manipulation%20of%20Opinion%20Polls%20to%20Influence%20Iterative%20Elections%20-%20p132.pdf), PDFpp2–3 / printed133–134, Definitions2.1–2.3 | Prefer a reachable predicted winner; fixed election ties | Unilateral poll-delta dynamics and plausible-report conditions; not simultaneous fractional propensity scores |

Source arcs observer→observed must be reversed when mapped to repository
sender→receiver arcs. Complete relevant model pages checked from local full text;
no new literature/novelty claim. Existing exact-information sequential theorems
cannot establish convergence of this candidate.

## 3. Inductive counterexample at defaults

Four voters; candidate/tie order A,B,C. Poll `(2,1,1)` is the **accurate initial
census** and remains numerically accurate in both recurring states; this does not
require poll deception or stale incorrect counts. Initial ballots are sincere:

| Voter | Fixed private ranking | Initial ballot |
| --- | --- | --- |
| v1 | A > B > C | A |
| v2 | A > B > C | A |
| v3 | B > C > A | B |
| v4 | C > B > A | C |

Let S0=`(A,A,B,C)` and S1=`(A,A,C,B)`.

Positions remain in `[0,1]^2`; every receiver radius is `sqrt(2)`; movement is
enabled with max_step=.025. The graph is dynamically recomputed, not frozen.
The unit square's diameter proves that every voter sees every other voter at
**every future round**, for every legal motion trajectory/seed. Thus all three
cache entries refresh each round, for any K≥1. Forgetting remains enabled but
no record becomes old enough to expire in this valid instance.

With w=.5 and N=4, complete observation gives
`s_i(c)=(3/2)*poll_share(c)+(1/2)*actual_other_count_i(c)`.

| Prior state / voter | Estimated other scores (A,B,C) | Current ballot → predicted winner | Direct switch → predicted winner |
| --- | --- | --- | --- |
| S0 / v3 | (7/4,3/8,7/8) | B → A | C → C |
| S0 / v4 | (7/4,7/8,3/8) | C → A | B → B |
| S1 / v3 | (7/4,7/8,3/8) | C → A | B → B |
| S1 / v4 | (7/4,3/8,7/8) | B → A | C → C |

Both switches in each phase strictly improve the voter's **predicted winner**.
v1/v2 already predict their favorite A and retain A. Therefore:

`S0 → S1 → S0 → S1 → …`

**Induction:** geometry guarantees complete sensing indefinitely; cache refresh
makes the next decision an autonomous function of the previous ballots and fixed
poll/rankings. The exact two transitions above therefore hold at every future
round. Two voters switch every round forever. No countdown, RNG event or finite
sampling premise is needed. Winner A nevertheless remains unchanged (2,1,1).

This is not a claimed repetition of the complete physical/RNG/absolute-clock state.
The projection consists of ballots plus cached IDs/first choices, encounter age0,
source age1 and counts. From round1 this projection has period2. Its independence
from the remaining state is proved by the complete-sensing invariant; projected
repetition alone, without that argument, would not suffice.

**Conclusion:** universal finite ballot absorption is false. For this instance the
ballot cycle holds for every motion path, so almost-sure ballot absorption is also
false under any motion distribution. A 40-round replay checks transcription and
helper alignment; the induction, not its finite duration, establishes the result.

## 4. Executable verification / limits

```bash
python3 scripts/verify_memory_voting.py --output outputs/memory-voting-convergence-new.json
python3 scripts/verify_memory_voting.py --witness-only
PYTHONPATH=src python3 -m unittest discover -s tests -p test_memory_voting_proof.py -v
```

Research checker only: real `majority.advance_population`, `network.random_walk`
and `network.proximity_edges`; exact observation-only decision kernel; independent
integer complete-observation reduction. No production-policy or engine change.

Finite family exhausts every strict preference profile for N2–5/m2–3, sincere
starts, truthful initial census and w0/.5/1: **28,152 directly enumerated orbits**.
The all-fresh invariant covers K1/2/10: **84,456 window-parameter cases**, not
independent experiments. This is not enumeration of all graphs, caches, initial
ballots, polls, continuous positions or RNG paths, and not a positive theorem.
Relative ages are normalized only in the justified autonomous projection.

Evidence file records full source/checker hashes, exact decisions, initial
conditions, actual keyed-motion sample, normalized cache recurrence and bounded
enumeration scope. Proof-only checking does not change runtime source identity.

Final evidence: [JSON proof audit](../outputs/memory-voting-convergence-2026-11-09-final.json).
N4/m3/w.5 complete-observation family: 1,296 preference profiles, 144 cyclic,
1,152 reaching fixed points. These are exhaustive finite-family counts, not a
population-level convergence probability. Some other cells have no found cycles;
that does not establish their unrestricted convergence.

Verification: **12 new tests pass**, including **20,862 independent exact-rational
decision comparisons** and shared-cache/reduced-model agreement across all N2/3
truthful strict profiles, weights0/.5/1 and windows1/2/10 for three updates.
Malformed, expired, duplicate-ID and histogram-inconsistent cache inputs fail.
Negative geometry test rejects the witness if a required contact is missing.

Historical proof-check logs: `outputs/memory-voting-tests-2026-11-09.log`,
`outputs/memory-voting-tests-stdlib-2026-11-09.log` and
`outputs/memory-voting-runtime-audit-2026-11-09.json`.
Current complete-suite evidence is centralized in [status](implementation-status-report.md#verification).

Checker SHA-256: `b6c3ff40d172eb517358a13534a2ceb7951b61324d25169a591beff73b15d49e`.
At that proof-audit snapshot, core/pipeline matched the prior estimator pilot;
subsequent population enforcement changed current runtime hashes. Historical
proof artifacts retain their own source/checker identity; no current-hash claim.

## 5. Gate and next decision

The original unrestricted-size claim is **refuted with a concrete counterexample**.
The N>=100-only domain remains uncertified. User authorized implementation and
exploratory studies without the convergence gate; proof remains necessary for any
convergence-certified claim. Preserve simultaneous updates and report cutoffs/cycles.

## Progress

Original contract/counterexample and final proof audit complete9 November.
Current population restriction is documented above; no N>=100 theorem claimed.
The implemented exploratory policy follows this contract. [Research plan](plans/research-improvement.md).
[Current engine verification](implementation-status-report.md#verification).
