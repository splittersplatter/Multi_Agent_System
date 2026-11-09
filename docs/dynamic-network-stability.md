# Moving-network stability

9 November2026. Normal-step motion, rolling contacts, periodic polls,
simultaneous `memory_pivotal`. Research findings; no new runtime certificate.

Later9 November: selected target is now **almost-sure long-run occupation
frequencies**, not frozen ballots. An opt-in finite-grid model is specified in the
[contract/proof dossier](plans/stochastic-stability.md); opt-in grid runtime now implemented.
Tiny formal [verification tooling](stochastic-stability-verification.md) now
checks eight scoped models; independent analytic/runtime reviews passed. The
ideal-IID theorem is not an infinite seeded-replay certificate.
Keep immediate strict improvement and continuing motion; no voter inertia/noisy
worse choices. Existing normal-walk behavior and evidence below are preserved.

## Implemented motion

Demo:200 voters; uniform direction; keyed length draws from
`Normal(mean_step,std_step)` conditioned on `[0,max_step]`; reflective unit-square
boundaries. Effective group/person parameters:

```toml
movement = "random_walk"
max_step = 0.05
parameters = { movement = { distribution = "normal", mean_step = 0.025, std_step = 0.00625 } }
```

- Mean = configured step, not previous realised displacement. Default spread=mean/4.
- Hard cap preserved; inverse-CDF sampling avoids clipping probability onto endpoints.
  Truncation can shift realised mean; demo bounds are symmetric around0.025.
  Reflection can shorten actual displacement.
- Zero spread gives fixed path length; zero mean/default spread gives no motion.
  Mean within `[0,max_step]`, spread within `[0,1]`; invalid/unrepresentable inputs fail.
- Missing parameters preserve the old uniform-length walk exactly. No speed decay;
  later movement remains possible, not guaranteed ballot flips.
- Matched actor/round motion across policies; existing configuration/checkpoints
  retain parameters. Restart servers after source changes.

## Guarantee routes

| Route | Required argument | Current applicability |
| --- | --- | --- |
| Closed ballot-absorbing region | All allowed successors preserve ballots and region membership | Earlier absorption target; conditional case below |
| Finite-chain occupation theorem | Full finite homogeneous state, then ergodic theorem inside reached recurrent class | Selected statistical target; grid-only mathematical contract, not runtime certification |
| Common well-founded potential | Every ballot-changing transition decreases it; others never increase it | Open for memory/poll/simultaneous dynamics |
| Restricted exact best response | Sequential direct replies, unit weights, exact information, deterministic ties | Existing F1; not the memory voter |
| Finite Markov abstraction | Every reachable recurrent class preserves one ballot profile; faithful transition model | Possible almost-sure absorption, not automatically every-execution convergence |
| Switching-network consensus | Source averaging rule and joint-connectivity assumptions | Inspiration, not a strategic-ballot theorem |

Meir et al., *Convergence to Equilibria in Plurality Voting*, §3.1/Theorem3
(PDF pp.5–6), proves the sequential unit-weight deterministic-tie best-reply case.
Its direct-response assumptions exclude arbitrary simultaneous ballot swaps.
[Full text](https://comsoc-community.org/assets/proceedings/comsoc-2010/Meir.pdf).

Jadbabaie, Lin & Morse, IEEE TAC48(6),2003, Theorem2 (printed p.990), establishes
heading consensus for its averaging model under repeated joint connectivity.
It does not prove finite ballot absorption for memory-pivotal decisions.
[Full text](https://web.mit.edu/~jadbabai/www/papers/JadLiMorseTAC_June03.pdf).

Closed communicating classes cannot escape; absorbing states are closed singletons.
For ballots, a region can contain moving positions but retain one ballot profile.
[Lancaster notes, Definition4.2.5](https://lancaster.ac.uk/~prendivs/accessible/math332/lec332.tex/Ch4.S2.html).
Continuous positions, finite-precision implementation, unbounded round keys and RNG
semantics do not automatically define a finite homogeneous chain.

## Sufficient moving-contact invariant

Our deduction from the implemented rule; not a published general convergence theorem
or implemented auto-stop. Suppose at a completed round:

1. `N>=3`, fixed candidates/tie order, `k=1`, homogeneous `memory_pivotal`.
2. Every submitted ballot supports candidate `c`.
3. Published poll puts all support on `c`; every retained cache entry also supports `c`.
4. Future observations remain truthful completed ballots. No external ballot edits,
   policy changes, deceptive polls, candidate changes or other ballot-changing interventions.
   Motion/contact changes and normal cache expiry remain allowed.

Proof: new contacts report `c`; expiry leaves only `c` or an empty cache.
Every blend/fallback assigns probability1 to `c`. For any hypothetical own ballot,
estimated other-voter score for `c` is `N−1>=2`; any opponent receives at most1.
Every predicted winner is `c`; no strict improvement exists, so all retain their
ballots. Future truthful polls also concentrate on `c`. By induction these conditions
persist under every future proximity graph.

This proves **ballot absorption conditional on entry**, not guaranteed entry
from arbitrary initial states, preference consensus, or a runtime certificate.
Unanimous current ballots alone are insufficient: stale contrary caches/polls
violate the premise. Large current margins alone are insufficient: future cache
replacement can change them.

## Next proof work; no silent restrictions

1. Generalize to mixed-ballot absorbing regions: enclose every future reachable
   estimate, including expiry, contacts and poll phases.
2. Prove every agent retains its ballot throughout the enclosure; prove closure
   under simultaneous transitions and code/oracle agreement before certification.
3. For convergence from every initial state, additionally prove entry into a
   certified region. Reachability tests and quiet windows cannot establish this.
4. Only afterward implement guarded certificates. No freezing, vote locks,
   serialization or exact-information substitution without scope approval.

## Diagnostics, not proofs

`compare` retains legacy `observed_ballot_stability` as a finite-window observation.
Successful rows add `stability_assessment`: `certified=false`, recent proximity-arc
symmetric-difference counts, flip reactivations after quiet windows and
`future_contact_changes_checked=false`. Arc changes count events across rounds,
not distinct edges or normalized turnover. Quietness never triggers auto-stop.
Browser fallback warns that contacts and poll information can change.

Track flips, contact turnover, estimation error and post-quiet reactivation together.
Stable winners, quiet ballots, stable estimates and stationary outcome frequencies
are different properties; none alone proves no future ballot changes.

## Verification

`tests/test_normal_walk.py`: legacy draws; normal moments/median; invalid parameters;
reflection/bounds; degenerate cases; replay/edit/overrides; matched policy motion;
quiet-then-new-contact flips; quiet ballots with edge churn. Tiny cases are explicitly
scoped verification fixtures, not outcome simulations.
[Full-suite and200-person CLI evidence](implementation-status-report.md#verification).

Exploratory smoke command; output path must be new:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare examples/recent-majority.toml --seeds 101 --policies memory_pivotal sincere --rounds 100 --window 10 --output outputs/normal-walk-comparison-2026-11-09.json
```

Observed:2/2 successful runs,200 actual voters each,100 rounds. Memory voter:
22 ballot changes, final A90/B66/C44, one flip reactivation after a>=10-round quiet
window. Sincere control:0 changes, A80/B70/C50. Both:5494 proximity-arc change
events in final10 transitions; no convergence certificate. Single-seed smoke,
not a performance/quality comparison or general convergence result. Raw comparison
includes configuration, per-round metrics, source/environment hashes and final traces.

## 24-work evidence matrix

Audit date9 November2026. Focused theorem/model audit, not an exhaustive systematic
review or a novelty claim.24 distinct works:22 accessible full texts inspected
(21 text-extracted; Blume model pages visually checked),2 full-text blockers.
An accessible PDF does not mean every theorem was independently reproved.
No additional guarantee is selected from unreviewed or inaccessible passages.

`STxx` are this supplement's row IDs, not replacement corpus IDs. ST01–ST06 map
to existing S4/S6/S12/S3/S9/S10; retain those original IDs/versions. Proceedings,
journal references and their expanded preprints count once per work here.
The existing31-work/36-PDF corpus, collection script and manifest are unchanged;
this supplement is not a new complete collection in `References`.

Pages below are one-based PDF pages of the specified reviewed copy; printed
pages/sections/theorem labels disambiguate publisher versus expanded layouts.
Author preprints are labelled as reviewed versions, not newly verified journal
versions. Mathematical source claims are separate from our model application.

### Citation, version and evidence

| Row / existing ID | Work; publication/version; stable reviewed link | Full-text evidence / access |
| --- | --- | --- |
| ST01 / S4 | Meir, Polukarov, Rosenschein, Jennings, **Convergence to Equilibria in Plurality Voting**; AAAI2010; [expanded COMSOC2010 copy](https://comsoc-community.org/assets/proceedings/comsoc-2010/Meir.pdf) | PDF5–6, §3.1/Theorem3/footnote4; PDF5 Proposition2 simultaneous-cycle warning. Expanded copy, not six-page proceedings. |
| ST02 / S6 | Meir, Lev, Rosenschein, **A Local-Dominance Theory of Voting Equilibria**; EC2014; [extended author arXiv v2](https://arxiv.org/pdf/1404.4688v2) | 51-page copy; PDF10–14 definitions, PDF17/Theorem4; broader conditions PDF19–21. Internal manuscript date2018; do not infer version equality from year alone. |
| ST03 / S12 | Anaelle Wilczynski, **Poll-Confident Voters in Iterative Voting**; AAAI2019,2205–2212; [proceedings](https://ojs.aaai.org/index.php/AAAI/article/download/4055/3933) | PDF2–4, Definitions1–3, Proposition1, Corollary2, Theorem1; printed2206–2208. |
| ST04 / S3 | Endriss, Obraztsova, Polukarov, Rosenschein, **Strategic Voting with Incomplete Information**; IJCAI2016,236–241; [proceedings entry](https://ijcai.org/proceedings/2016/41) | Existing local S3 PDF5–6, §4/Theorems8–9; explicit stable-outcome versus stable-profile distinction. Local copy inspected despite web PDF-fetch errors. |
| ST05 / S9 | Tsang, Larson, **The Echo Chamber: Strategic Voting and Homophily in Social Networks**; AAMAS2016,368–375; [author copy](https://cs.uwaterloo.ca/~klarson/papers/TL.AAMAS2016.pdf) | PDF2–3, §§2.2–2.3; empirical setup/results PDF3–7. No general moving-memory convergence theorem identified. |
| ST06 / S10 | Tsang, Salehi-Abari, Larson, **Boundedly Rational Voters in Large(r) Networks**; AAMAS2018,301–308; [proceedings](https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p301.pdf) | PDF2–4 response models/heuristics; PDF4–7 experiments. Equilibrium is a modelling goal, not a theorem for our extension. |
| ST07 | Jadbabaie, Lin, Morse, **Coordination of Groups of Mobile Autonomous Agents Using Nearest Neighbor Rules**; IEEE TAC48(6),988–1001,2003; [author PDF](https://web.mit.edu/~jadbabai/www/papers/JadLiMorseTAC_June03.pdf) | PDF2–3, model/Theorem2, printed990; joint-connectivity condition. |
| ST08 | Luc Moreau, **Time-dependent unidirectional communication in multi-agent systems**; [author preprint math/0306426v1,2003](https://arxiv.org/pdf/math/0306426v1) | PDF6 Assumptions1–2; PDF12/Theorem3, proof PDF13 onward. Reviewed preprint; not a separately audited later journal layout. |
| ST09 | Hendrickx, Tsitsiklis, **Convergence of Type-Symmetric and Cut-Balanced Consensus Seeking Systems**; IEEE TAC58(1),214–218,2013; [extended author v2](https://web.mit.edu/jnt/www/Papers/J141-13-jh-cut-balanced-extended.pdf) | PDF3/Theorem1; PDF8–9/§VI, Theorem2 discrete-time version. Extended12-page copy, not five-page journal layout. |
| ST10 | Kashyap, Basar, Srikant, **Quantized consensus**; Automatica43(7),1192–1203,2007; [author PDF](https://tamerbasar.csl.illinois.edu/KashyapBasarSrikantAutoVol42Iss7_2007.pdf) | PDF2–4, Eq.(1), properties P1–P3, Theorems1–2, conditions G1–G2. |
| ST11 | Monderer, Shapley, **Potential Games**; Games and Economic Behavior14,124–143,1996; [paper PDF](https://people.csail.mit.edu/jrennie/trg/papers/monderer-potential-96.pdf) | PDF5–6, Lemmas2.3/2.5, printed128–129; unilateral improvement paths. |
| ST12 | Auletta, Ferraioli, Pasquale, Penna, Persiano, **Convergence to Equilibrium of Logit Dynamics for Strategic Games**; Algorithmica76,110–142,2016; [reviewed expanded preprint v2,2012](https://arxiv.org/pdf/1212.1884v2) | PDF4–5 Markov/logit definitions; PDF8/Theorem3.1; mixing bounds concern the specified noisy game dynamics. |
| ST13 | Same five authors, **Logit Dynamics with Concurrent Updates for Local Interaction Games**; [reviewed author preprint v4,2013](https://arxiv.org/pdf/1207.2908v4) | PDF5–6, Eq.(1)–(3), strictly positive transition argument; reversibility section follows. No journal-version identity assumed. |
| ST14 | Auletta, Ferraioli, Pasquale, Persiano, **Metastability of Logit Dynamics for Coordination Games**; SODA2012 preliminary; [expanded author preprint v4,2017](https://arxiv.org/pdf/1107.4537v4) | PDF7/Definition3.1; PDF11 examples distinguish metastability from full mixing. |
| ST15 | Shimizu, Shiraga, **Reversible Random Walks on Dynamic Graphs**; [author preprint v2,2022](https://arxiv.org/pdf/2102.08002v2) | PDF4–5, Proposition1.1/Theorem1.2; common invariant measure, reversibility/laziness assumptions. Reviewed preprint status. |
| ST16 | Cai, Sauerwald, Zanetti, **Random walks on randomly evolving graphs**; [author preprint v1,2020](https://arxiv.org/pdf/2006.10589v1) | PDF3–5 definitions/Theorems1.1–1.3; edge-Markovian density/speed regimes. Reviewed preprint status. |
| ST17 | Sauerwald, Zanetti, **Random Walks on Dynamic Graphs: Mixing Times, Hitting Times, and Return Probabilities**; ICALP2019,93:1–93:15; [proceedings](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2019.93) | PDF2/Main Result1, PDF9/Theorem3.3; full version linked by proceedings, not counted again. |
| ST18 | Poveda, Krstic, Basar, **Fixed-Time Nash Equilibrium Seeking in Time-Varying Networks**; IEEE TAC68(4),1954–1969,2023; [author PDF](https://flyingv.ucsd.edu/papers/PDF/408.pdf) | PDF3–5 cost assumptions; PDF10/Assumption5/Theorem2. Distinguish exact first-order from practical model-free bounds. |
| ST19 | Swenson, Kar, **On the Exponential Rate of Convergence of Fictitious Play in Potential Games**; [reviewed author preprint v1,2017](https://arxiv.org/pdf/1707.08055v1) | PDF2–3 definitions; PDF4/Theorem8. Regularity and almost-every-initial-condition qualifications retained. |
| ST20 | Engle, Morsky, **The dynamics of strategic voting: pathways to consensus and gridlock**; [reviewed author preprint v1,2024](https://arxiv.org/pdf/2410.20237v1) | PDF3–6 Methods/Table2/imitation dynamics; PDF14 discussion. Empirical mechanism study, not proof for our heuristic. |
| ST21 | Lawrence Blume, **The Statistical Mechanics of Strategic Interaction**; GEB5,387–424,1993; [scanned paper](https://www.stat.berkeley.edu/~aldous/206-RWG/RWGpapers/blume.pdf) | Automated extraction yielded no body text. Visually inspected PDF5–7, printed391–393, Eq.(2.1)–(2.3): Poisson revision clocks, best-response and noisy choice. No stationary-distribution theorem imported. |
| ST22 | H. Peyton Young, **The Evolution of Conventions**; Econometrica61(1),57–84,1993; [DOI](https://doi.org/10.2307/2951778) | **Full-text blocked.** Oxford repository web403; CiteSeer web403/local retrieval404; no verified full-text theorem/page. Metadata/abstract-only; request lawful copy if this route is reopened. |
| ST23 | Zhu, Zhang, Xia, Li, Chen, **Finite Strategy Switches of Coordinating and Anti-Coordinating Games on Weighted Networks**; IEEE TCyb56(1),446–459,2026; [DOI](https://doi.org/10.1109/TCYB.2025.3612486) | **Full-text blocked.** DOI retrieval returned HTML, not a PDF; publication metadata indexed under PMID41052190. Exact assumptions/theorem numbers unverified; request lawful copy before use. |
| ST24 | Levin, Peres, with Wilmer contributions, **Markov Chains and Mixing Times**, second edition, AMS2017; [author-hosted book](https://pages.uoregon.edu/dlevin/MARKOV/mcmt2e.pdf) | §1.7/classification, Proposition1.29; Theorem4.9 requires aperiodicity for instantaneous convergence; Appendix C/Theorem C.1 does not require it for occupation averages. Audited download: PDF406–407/printed390–391 for C.1. |

Book download SHA-256:
`9ef39f9467d9647ff3f5e8747b9ce24b7a90d13be2f8156fbd827b95b661a772`.
Web extraction/cache pagination can differ; theorem labels and the specified
download hash take precedence over an unverified page offset.

### Model, information boundary and applicability

All unspecified details below are **not used in a transferred theorem**.
No K-round unique-neighbor cache is implied by the word “memory” in another paper.
F=mathematical foundation; P=partial precedent; I=inspiration; X=excluded method;
B=blocked. None is an exact published implementation of our proposed grid model.

| Row | State / information | Update; topology; memory and randomness | Guarantee / missing assumptions / classification |
| --- | --- | --- | --- |
| ST01 | Submitted votes, fixed private rankings; current election feedback | Single direct best reply; no graph/cache; deterministic election ties in Theorem3 | Finite Nash convergence for unit weights; not simultaneous belief responses. P |
| ST02 | Votes and uncertain possible score worlds | Singleton dominance response; shared uncertainty type, truthful start; no rolling social cache; no random decision needed | Theorem4 bounds changes under source uncertainty semantics. Local contact estimates/expiry do not satisfy them automatically. P |
| ST03 | Votes, poll-adjusted integer beliefs, pivotal thresholds | One deviator; fixed directed observation graph; observed score deltas, not replacement cache; initial/repeated-poll variants | DAG local result; transitive results need stated thresholds/scheduler. General cycles possible; moving edges and fixed10-round broadcasts are not covered. P |
| ST04 | Ranked reports; winner/score/majority-graph disclosure | Unilateral safe manipulation; conservative dynamics for positional-rule result; no moving social cache | Some stable-outcome theorems allow continued ballot changes. Different information function and action semantics. P |
| ST05 | Neighbor ballots, inferred population support, cardinal utilities | Expected marginal utility; sequential/simultaneous variants; fixed random/homophilic graph; multinomial inference and source tie variants | Empirical strategization/welfare; no full-model absorption guarantee. Useful information-boundary precedent, not proof. P |
| ST06 | Local support estimates, utility rankings; bounded computations | One-by-one heuristic responses; fixed networks; smoothed local sample; random election ties in model | Empirical tractability/behavior; not a theorem for moving-window/poll compositions. P |
| ST07 | Continuous headings/positions; current neighbor headings | Discrete averaging with self; moving metric graph; no strategic ranking/cache | Consensus under source joint-connectivity assumptions. Headings are not discrete strategic ballots. I |
| ST08 | Real vector states; current received neighbor states | Nonlinear strict-convex-hull updates; directed switching graph, no K-cache; deterministic topology permitted | Source weak-connectivity-over-windows plus Assumptions1–2 yields attractivity. Use source connectivity definition, not ordinary undirected weak connectivity. I |
| ST09 | Continuous opinions; time-dependent influence coefficients | Continuous integration/cut-balance; discrete theorem adds positive diagonal and lower bounds; no strategic ballot payoff/cache | Value convergence under stated reciprocity conditions; not strict predicted-election response. I |
| ST10 | Integer values with conserved sum; endpoint values | Random pairwise quantized averaging on connected undirected graph; no ranking/poll memory; positive edge-selection probabilities | Convergence to quantized-consensus **set**, not necessarily frozen per-node values; conservation/pairwise rules differ. I |
| ST11 | Finite action profiles and fixed payoffs | Strict unilateral payoff improvement; graph only if encoded in one fixed potential; no independent memory/RNG premise | Finite improvement from a valid generalized ordinal potential. Rewiring can change payoffs/potential; one must prove a common full-state potential. F |
| ST12 | Finite game profiles, own counterfactual utilities | Random single reviser; finite-temperature logit; no moving environment/cache in the base chain | Stationary law/mixing analysis; potential-game structure needed for special formulas/bounds, not generic finite-logit irreducibility. Worse choices violate selected rule. X |
| ST13 | Finite profiles, local-interaction payoffs | Simultaneous logit; fixed game/network; positive probability for every ballot, no rolling cache | Positive transition matrix gives ergodicity; local-game conditions govern reversibility/formulas. Immediate strict response lacks positivity. X |
| ST14 | Finite profiles/distributions under logit | Random revision/noisy payoffs; coordination games on specified graphs; no K-cache | Near-stationary behavior may persist before later transitions. Diagnostic warning, not a certificate for observed quietness. I |
| ST15 | Walker location; sequence of transition matrices | Lazy reversible kernels; changing graph, shared stationary measure; current location sufficient | Mixing/hitting bounds depend on common invariant distribution and source assumptions; joint voting/cache process need not have them. I |
| ST16 | Walker and edge-Markovian graph | Edges independently added/deleted under source p,q model; random walk uses current graph | Positive/negative mixing regimes; proximity edges are not independent edge-Markov chains. I |
| ST17 | Walker location and specified graph sequence | Lazy walk; changing connected graphs sharing invariant measure; no ballot memory | Mixing/hitting bounds under shared-measure assumptions; no direct joint-voter conclusion. I |
| ST18 | Continuous actions plus estimates/auxiliary states; costs/gradients or measured costs | Continuous/hybrid equilibrium seeking; smooth potential/monotone games; source switching connectivity/balance/dwell assumptions | Exact/practical fixed-time results for different continuous controllers. Discrete plurality utilities and arbitrary disconnection do not fit. I |
| ST19 | Continuous empirical mixed-strategy beliefs; game payoffs | Continuous-time fictitious play in regular potential games; cumulative belief, not finite encounter cache | Almost-every-initial-condition exponential convergence; no unrestricted finite-window theorem or election-potential mapping. I |
| ST20 | Two-party affiliations, strategies, preference types and outcome beliefs | Strategic reconsideration/social imitation; ER/homophilic networks; strategy tables/past outcomes, stochastic imitation | Simulated consensus/gridlock patterns; changing preferences/imitation differ from fixed-ranking strict response. I |
| ST21 | Strategy configurations; current local payoff sums | Continuous-time Poisson opportunities; fixed lattice interactions; random best-response ties or fully mixed noisy choice; no K-cache | Audited model equations explain the distinction from our synchronous process. No theorem transferred; noisy branch excluded. I/X |
| ST22 | Model details unverified in full text | Metadata abstract concerns sampled past play and occasional mistakes; sampling/scheduling/topology parameters unverified | No theorem or bound selected from abstract. B |
| ST23 | Weighted coordination/anti-coordination named in title | Exact state, observations, scheduling qualifications, memory and stochasticity unverified | No transfer from metadata's finite-switch claim. B |
| ST24 | Complete finite homogeneous Markov state, not ballots alone | Arbitrary finite kernel; recurrent-class decomposition; periodic classes allowed for time averages | Selected foundation: class-conditioned ergodic averages. Our finite-state/domain mapping still needs review and future engine correspondence. F |

### Decision and remaining blockers

- Adopt only ST24's occupation-frequency route for the new mathematical contract.
  Strict voting preserves zero-probability actions, so logit irreducibility and
  Gibbs formulas are unavailable; no unique initial-state-independent law assumed.
- Preserve earlier absorbing-region analysis as a stronger, separate conditional
  property. A stationary occupation measure can coexist with infinite flips.
- Require complete state, startup exception and poll phase; neither a stationary
  spatial walk nor a quietly observed winner proves joint-process stationarity.
- ST22/ST23 need lawful full-text copies before theorem-level audit. ST21's
  scanned stationary-theorem sections remain unaudited; only the visually checked
  model equations support its entry. These are not prerequisites of ST24's proof.
- Next deliverable: independent review of the [finite-grid proof](plans/stochastic-stability.md),
  then a separate implementation plan. No source code, reference manifest or
  existing outcome evidence changed by this documentation audit.
