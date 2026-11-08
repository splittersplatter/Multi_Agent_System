# Literature: heuristics and evaluation metrics

Audit: **7 November 2026**. Corpus: **31 retained works; stable source IDs**, not a new
systematic search. **31 reviewed works; 36 PDFs = 31 selected
copies + five retained versions/prints.** Three original PDFs preserved.
[Collection/versions](../References/README.md) · [Manifest](../References/manifest.json)
· [Earlier survey](election-manipulation-literature-survey.md).

Evidence: PDF-page numbers below are **1-based file pages**, including covers;
printed pages/sections are supplied where useful. Records audit model/algorithm,
evaluation and relevant appendices; they are not replications. **Theory** means
formal results, not measured benchmark performance. **NR** means not reported in
the cited evaluation, not permission to invent a default. Public access does not imply unrestricted redistribution.

## Main corrections and additions

- **k-pragmatist != Top-K EU:** choose favourite among poll leaders versus
  recompute probabilistic strategic utility on a consideration set (S5/S7 vs S10).
- Additional voter baselines: **Attainability-Utility, leader-biased dominance,
  voter-type rules, truth/lazy bias**. Mentioned alternatives such as minimax
  regret are not automatically implemented/tested policies (S1/S2/S6/S7).
- Attacker heuristics: **specter/two-potential-winner polls, greedy edge control,
  weighted influence seeding, political-distance/PageRank selection**. These are
  not ballot-selection rules (S11-S14/S17/S19/S23).
- **Final margin, margin improvement, probability of victory and conditional
  attack success are different estimands.** Existing winner margin is not a
  signed target margin (S17/S19/S23; simulator mapping below).
- S14 supplies **probabilistic bounds**, not a Monte Carlo benchmark. Its small
  distortion theorem uses `k = o(sqrt(n))`, not simply `k = o(n)`.
- Metadata: S1 is TARK 2013; S2 has a *Studies in Logic* 2019 journal reference.
  S32's PDF/arXiv claims ICAIS 2025; independent proceedings verification remains
  unavailable. S26 remains a preprint; its conference-template text is malformed.

## Per-paper evidence

### S1 — Strategic Voting and the Logic of Knowledge

van Ditmarsch, Lang, Saffidine; TARK 2013; [author preprint][S1].

- **Model:** voters report rankings; finite preference-profile worlds and
  indistinguishability relations; own/higher-order knowledge; voting examples
  with explicit tie orders. No physical network, intervention budget or round scheduler.
- **Decision:** manipulation knowledge de re/de dicto; conditional strategies
  per information class; **Wald/maximin** worst-outcome comparison. Laplace and
  maximum-regret criteria discussed, not experimentally compared. Truthful
  preference revelation restricts worlds; it is not deceptive reporting.
- **Evaluation:** theory/examples: definability, conditional equilibria,
  preservation under information updates; no empirical metrics, datasets,
  repetitions or runtime benchmark.
- **Evidence:** PDF pp.2-6, §§2-5; pp.7-9, §§6-9. Use for semantics/oracles,
  not a ready-made population policy or convergence result.

### S2 — How does uncertainty about other voters determine a strategic vote?

Bakhtiari, van Ditmarsch, Saffidine; *Studies in Logic* 12(3), 2019;
[existing arXiv 1809.10489v2][S2].

- **Model:** voters, ranking reports, finite epistemic profile models; own
  preference known for conditional-equilibrium analysis; no social graph/budget.
- **Decision:** dominant and pessimistic manipulation; conditional equilibrium
  excludes a profitable worst-outcome deviation in **every information class**.
  Maximin adopted; Laplace/minimax regret only discussed. Public truthful
  announcements change information, not preferences. No iterative scheduler.
- **Evaluation:** formal examples and preservation/counterexample results;
  no empirical performance metrics, fitted parameters, trials or benchmark.
- **Evidence:** PDF pp.3-10, Definitions 5-13/§5.1; pp.13-16, §6; pp.20-22,
  §§7-8. Score-world maximin in our engine is narrower than this model.

### S3 — Strategic Voting with Incomplete Information

Endriss, Obraztsova, Polukarov, Rosenschein; IJCAI 2016; [proceedings][S3].

- **Model:** ranking reports; winner, score or majority-graph disclosure defines
  possible profiles; lexicographic election ties; no social network or attacker.
  Plurality, veto, k-approval, Borda, Copeland and Maximin voting rules.
- **Decision:** safe `pi`-manipulation under disclosure; unilateral myopic moves;
  conservative dynamics select a safe move with the best actual resulting winner.
  Truthful starts in the stated convergence analysis.
- **Evaluation:** manipulation susceptibility/immunity, function monotonicity,
  convergence/cycle constructions. **Stable outcome need not mean stable ballots.**
  No simulation dataset or empirical success/runtime table.
- **Evidence:** PDF p.2/printed 237, §§2-3; pp.5-6/240-241, §4/Theorems 8-9.

### S4 — Convergence to Equilibria in Plurality Voting

Meir, Polukarov, Rosenschein, Jennings; AAAI 2010;
[expanded COMSOC 2010 copy][S4], not the six-page proceedings layout.

- **Model:** plurality voters; weights/tie regimes varied; current outcome/score
  feedback; no social graph, movement or attack budget.
- **Decision:** unilateral better replies versus **direct best replies** that
  elect the chosen candidate; truthful versus arbitrary starts; deterministic
  priority and randomized tie cases analyzed separately. Simultaneous moves
  included as counterexamples, not the default convergent process.
- **Evaluation:** existence/nonexistence, finite improvement, counterexamples,
  move bounds under specified assumptions; no empirical metric suite/trials.
- **Evidence:** PDF pp.3-5, §2/Proposition 2; pp.6-9, §3/Theorems 3/8;
  pp.10-11, discussion. Do not transfer proofs to our moving simultaneous engine.

### S5 — Voter Response to Iterated Poll Information

Reijngoud, Endriss; AAMAS 2012; [proceedings][S5].

- **Model/decision:** **truth-teller**, **strategist** (undominated response over
  poll-consistent profiles), **k-pragmatist** (favourite among k leaders).
  Ranking ballots, several counting/disclosure rules, lexicographic ties;
  no social graph. One voter updates at a time; simulation uses cyclic index order.
- **Metrics:** **Condorcet efficiency**, denominator restricted to profiles with
  a Condorcet winner; termination/cutoff. Paired McNemar tests of poll effects.
- **Protocol:** IC; 10,000 qualifying profiles/configuration; `n=10..100` by 5
  with `m=5`, or `m=3..15` with `n=50`; no-poll control; 2-/3-pragmatists and
  rank-/score-informed strategists. Rank-information runs capped at 10,000 poll rounds.
- **Evidence:** PDF pp.4-5, §4.1; pp.7-8, §4.4/Figs.1-2. No pollster attack.

### S6 — A Local-Dominance Theory of Voting Equilibria

Meir, Lev, Rosenschein; EC 2014; [extended arXiv v2][S6], 51-page layout.

- **Decision:** move to an undominated action dominating current ballot across
  nearby possible score states; no probabilities. Additive/multiplicative
  uncertainty, truth-biased and lazy variants; individual/group schedulers;
  no social graph. Guarantees depend on start, metric and voter assumptions.
- **Metrics:** convergence steps; Borda/Copeland/Maximin winner agreement;
  **conditional Condorcet efficiency**; Borda-utility welfare; ground-truth rank
  for Plackett-Luce; two-candidate vote concentration; winner consistency across starts.
- **Protocol:** 108 synthetic distributions, 200 profiles each, 100 paths/profile;
  IC, single-peaked, urn, riffle, Plackett-Luce; three German poll profiles and
  225 PrefLib profiles. Uncertainty `r=0..15`; truthful/random starts and heterogeneous radii.
- **Evidence:** PDF pp.10-14, §4; p.17, Theorem 4; pp.22-28, §6; pp.38-46, Appendix B.

### S7 — Predicting Strategic Voting Behavior with Poll Information

Fairstein, Lauz, Gal, Meir; 2018 [arXiv preprint v1][S7].

- **Model:** one voter sees poll scores/cardinal utilities; plurality;
  utility of tied winners averaged. No interaction network or dynamic equilibrium.
- **Methods:** **Attainability-Utility (AU)**; k-pragmatist; calculus-of-voting
  `CV_eta`; local dominance and **LD+leader bias**; **TRT/CMP/LB** voter-type
  baselines; neural classifier. AU maximizes
  `(epsilon+u(c))^alpha * (epsilon+a_beta(c,s))^(2-alpha)`, with
  `a_beta=sigmoid(beta*(s(c)/n-1/m))`; parameters fitted per voter.
- **Metrics/protocol:** confusion matrices; per-class precision/recall/F1 and
  weighted F1; leave-one-round-out within voter. 595 people, up to 20 rounds,
  three candidates; utility/reward ordering 10/5/0 cents; six poll-order scenarios.
- **Evidence:** PDF pp.3-8, §§2-4, especially §4.2. **Orientation warning:**
  prose definition of `A(x,y)` conflicts with its example/formulas; visually checked
  p.8. Define our own explicit actual/predicted axes before reproducing these metrics.

### S8 — Strategic Voting in a Social Context: Considerate Equilibria

Gourvès, Lesca, Wilczynski; ECAI 2016; [HAL proceedings copy][S8].

- **Model:** voters form graph-clique coalitions; graph encodes permissible
  cooperation/consideration, **not local observation**. Ranked/subset ballots
  depend on rule; fixed priority tie-breaking; weak/strict preferences considered.
- **Decision:** improving, weak-improving, **considerate improving** moves;
  considerate move benefits a coalition member without harming coalition or its
  neighbors. Better/best replies and unanimous deviations analyzed. One coalition
  moves per step, until no allowed move; cycles may prevent termination.
- **Evaluation:** equilibrium existence and convergence counterexamples across
  plurality, veto, k-approval, Borda, runoff, STV, Maximin, Copeland. No measured
  welfare, runtime, success frequency, dataset or Monte Carlo protocol.
- **Evidence:** PDF pp.3-4/printed 1424-1425, §2/Definitions 1-3;
  pp.5-9, §§3-6. Do not equate considerate coalitions with deceptive attackers.

### S9 — The Echo Chamber: Strategic Voting and Homophily in Social Networks

Tsang, Larson; AAMAS 2016; [proceedings][S9].

- **Decision:** infer multinomial population support from neighbor ballots with
  Laplace smoothing; maximize pairwise pivotal utility, including exact/near
  ties and neglecting multiway ties. Isolated voters retain ballots. Quadratic
  spatial utility `-|ideal-position|^2`; plurality; sequential/simultaneous and
  lexicographic/probabilistic election-tie regimes compared.
- **Metrics:** `PoH=SW_truthful/SW_strategic`, `PoS=SW_strategic/SW_optimal`;
  utilities negative, so ratio direction matters. Nontruthful final ballots,
  updates to stability, **SF ratio = third/second candidate support**.
- **Protocol:** 169 voters; ER/BA and homophilic variants; three/four candidates;
  first/second experiment sets average 400/800 replications; density varied;
  25-round limit; Mann-Whitney tests. Simulation stability is supplemented by a cycle counterexample.
- **Evidence:** PDF pp.2-4, §§2-4/Table 1; p.5, §5. Ratios are not directly
  comparable with our nonnegative ordinal-utility proxy.

### S10 — Boundedly Rational Voters in Large(r) Networks

Tsang, Salehi-Abari, Larson; AAMAS 2018; [proceedings][S10].

- **Methods:** **Full, Top-K, Max-M, TieU, TieH, TieR, Poisson**.
  Neighbor-smoothed support, quadratic spatial utility, sequential plurality,
  random election ties; truthful start; stop after an unchanged round.
  Top-K restricts candidates; Max-M uses largest pair gain; TieU samples enumerated
  pivots, TieH nonuniform tie states, TieR multinomial elections. Poisson uses
  asymptotic pivotal/Skellam approximations. Heuristics simplify to exact two-way
  winning ties; Full also considers near pivots (multiway ignored).
- **Metrics:** response seconds and **disagreement with Full** on identical inputs;
  decision-region plots; desiderata; SF ratio in district-size study.
- **Protocol:** response benchmarks: 25 neighbors, spatial draws in `[0,100]`,
  1,000 trials. District study: `n=200/400/600/800`, five candidates, degree ≈30,
  directed/undirected ER/BA, TieH `L=2000` versus Poisson, 200 replications/cell.
- **Evidence:** PDF pp.2-4, §§2-3; pp.5-7, §§4-5/Figs.4-10.

### S11 — Adapting the Social Network to Affect Elections

Sina, Hazon, Hassidim, Kraus; AAMAS 2015; [proceedings][S11].

- **Actors:** strategic voters plus edge-adding organizer. Voter score estimate
  is **poll score + current neighbor counts**, not S12's poll-delta memory.
  Plurality, fixed preference/tie orders; added edges precede sincere round one.
- **Organizer heuristic:** initial stabilization; rank candidate voter bags;
  attach supporters to induce target-favoring pivots; stabilize affected neighbors.
  Known/unknown-poll constructive algorithms also analyzed. Practical heuristic
  checks ten initial rounds; this is not a general convergence proof.
- **Metrics/protocol:** added edges, fraction/network overhead, affected-voter
  types, target's initial rank. Facebook MHRW BFS samples `n=25k..100k`,
  `m=3..10`, degree threshold 10, poll sample 500; 10 roots × 100 repetitions;
  synthetic cultures and PrefLib sushi preferences. No optimal-minimum-edge certificate.
- **Evidence:** PDF p.3/707, model; pp.6-8/710-712, §6/Figs.2-3.

### S12 — Poll-Confident Voters in Iterative Voting

Wilczynski; AAAI 2019; [proceedings][S12].

- **Voters:** maintain poll-based scores using observed neighbor deviations;
  own vote excluded for pivotal test; threshold `p_i` defines potential winners;
  choose favourite improving challenger. Directed graph; one deviator/step;
  fixed election ties; local initial poll versus repeated global polls after local stability.
- **Pollster:** **margin rebalance on two candidates**, **election-enforcing
  specter heuristic**, restricted best poll move using empty/DAG/transitive
  spanning subgraphs (Algorithms 1-3). Likelihood condition restricts reports.
- **Metrics:** convergence frequency, conditional Condorcet efficiency **within
  equilibria**, target-election frequency, mean final-winner rank in pollster's
  preferences **on converged runs**; lower rank better. Preserve censoring denominators.
- **Protocol:** 10,000 instances, 100 voters/10 candidates, IC, ER density sweep;
  homogeneous thresholds 1/5/10 or heterogeneous `[1,5]`/`[1,10]`;
  truthful-poll controls; equilibrium/cycle stopping.
- **Evidence:** PDF pp.2-3, model; pp.5-7, Figs.2-4/Algorithms 1-3.

### S13 — Manipulation of Opinion Polls to Influence Iterative Elections

Baumeister, Selker, Wilczynski; AAMAS 2020; [existing PDF][S13].

- **Voters:** poll-confident pivotal plurality/veto best response; directed local
  observations, fixed election ties, unilateral iterative deviations. Pollster
  knows preferences/network and announces plausible initial scores.
- **Pollster heuristics:** ordered **announced-winner/challenger pairs**, separately
  for constructive/destructive plurality/veto; rank pairs by candidate gain,
  transferable votes or removed/added vetoes. Complexity work also studies
  bounded report distance and voter restrictions; not every variant is benchmarked.
- **Metrics/protocol:** target elected (constructive) or not elected (destructive)
  as final iterative winner; **raw frequency**, not paired added success. No
  manipulation versus heuristic versus exhaustive feasible reports; 1,000 IC
  instances, 50 voters/five candidates, acyclic graphs. Targets: truthful,
  Borda or Condorcet losers/winners; Condorcet-domain restriction explicit.
  Further exact-search sweep `n=10..50`.
- **Evidence:** PDF pp.2-3, §2; pp.7-8/138-139, §5/Figs.1-2.

### S14 — Do We Care About Poll Manipulation in Political Elections?

Mousseau, Surugue, Wilczynski; ECAI 2024;
[full HAL proceedings][S14]; earlier two-page ROADEF abstract retained separately.

- **Model:** plurality, lexicographic ties, sincere start; no social graph.
  Each voter best-responds **once** to the same report without observing others'
  moves; order irrelevant. Pollster seeks a target victory; report budget
  `d(s,s_truth)=0.5*sum_c |s_c-s_truth,c| <= k`.
- **Methods:** **2PW-H(target,specter)**, Global Heuristic over specters,
  **Restricted 2PW-H**; arrange a threatening announced winner and target as the
  two potential winners. Generalized pivotal thresholds also analyzed.
- **Evaluation:** **theory**, success-event probabilities/bounds as functions of
  culture, `n,m,k,p`; strategic-voter proportion; balanced cultures. Small-budget
  result `k=o(sqrt(n))`; large-budget results require their stated culture/scaling
  conditions. No empirical trial/runtime comparison in this paper.
- **Evidence:** PDF p.3/3542, §2; pp.5-8/3544-3547, §§4-6/Theorems 5/7/11/14.

### S15 — Election Control in Social Networks via Edge Addition or Removal

Castiglioni, Ferraioli, Gatti; AAAI 2020; [proceedings][S15].

- **Model:** controller adds/removes edges; seeds/messages fixed. Directed
  weighted graph, generalized independent-cascade positive/negative messages;
  messages change candidate evaluation scores; myopic voters choose highest
  evaluation under plurality. Not strategic ballot optimization or epistemic updating.
- **Objective:** expected target **margin improvement**; auxiliary influence
  maximization/minimization. Finite/unlimited edge budgets; one/multiple
  candidate/message cases and reoptimization analyzed separately.
- **Evaluation:** hardness/inapproximability, reductions and trivial tractable
  cases; no proposed empirical heuristic league table, measured runtime or dataset.
  Do not treat a worst-case hardness result as an observed attack failure rate.
- **Evidence:** PDF pp.2-3/1879-1880, Model; pp.4-7, results/tables.

### S16 — Election Manipulation on Social Networks: Seeding, Edge Removal, Edge Addition

Castiglioni, Ferraioli, Gatti, Landriani; JAIR 71, 2021;
[publisher full text][S16]; earlier arXiv v2 retained.

- **Model:** budgeted seeding/messages or edge changes, multi-issue independent
  cascade, score/ranking changes followed by myopic plurality.
- **Methods:** greedy influence-based approximation in restricted susceptibility
  regimes; counterexamples for direct margin-greedy and network-only centralities,
  including degree/PageRank/VoteRank. Not evidence that all these were empirically
  benchmarked; they are analyzed as algorithm classes.
- **Evaluation:** formal expected margin improvement, approximation bounds,
  complexity and reoptimization resilience. Constructed networks demonstrate
  failure even on elementary graphs. No empirical dataset/repetition/runtime suite.
- **Evidence:** PDF pp.11-12, §§2.3-2.4/Definitions 1-5; pp.13-15, §3.1;
  pp.19-24, §3.2.1; p.39, discussion. Strong source for adversarial test cases,
  not a universal claim that practical graph heuristics cannot work.

### S17 — Controlling Elections through Social Influence

Wilder, Vorobeychik; AAMAS 2018; [proceedings][S17].

- **Model/methods:** budgeted influence seeds; independent cascade; influenced
  voters shift target up/down ranking; plurality. **MOVConstructive/Destructive**
  greedy surrogates; **POVConstructive/Destructive** threshold-truncated surrogates;
  sample-average **MILP** comparator. Non-strategic influenced voters.
- **Metrics:** expected **margin change (MOV)**; target win/loss probability
  **POV**; percentage of MILP objective; instance dispersion. MOV quality does
  not certify POV quality. MILP comparator conditional on sampled scenarios/solution status.
- **Protocol:** netscience 1461, facebook 2888, polblogs 1224, irvine 1889 nodes
  as reported here; 30 random preference instances/network; propagation `.1`;
  seed budgets 25/50/100; 2/5/10 candidates. POV uses budget 50, five candidates,
  150 random threshold values rather than exhaustive thresholds.
- **Evidence:** PDF pp.2-3, model/objectives; pp.7-8/271-272, §§6-7/Table 1/Fig.1.

### S18 — Defending Elections Against Malicious Spread of Misinformation

Wilder, Vorobeychik; AAAI 2019; [author full text][S18].

- **Model:** attacker/defender choose budgeted advertising channels; probabilistic
  exposure and voter preferences; zero-sum payoff **expected voters switched**.
  Disjoint/nondisjoint channels; known, stochastic, asymmetric, adversarial uncertainty.
- **Methods:** follow-the-perturbed-leader for linear disjoint setting; online
  projected/exponentiated-gradient attacker plus greedy defender responses for
  nondisjoint setting; mixed strategy from iterates; MIP best responses for evaluation.
- **Metrics/protocol:** attacker payoff and bound on relative optimality gap
  `(b_upper-b_lower)/b_lower`; Yahoo Webscope-derived 100 channels/500 voters,
  probabilities uniform `[0,.2]`, 30 instances; `T=50`, learning rate `.05`;
  budgets and uncertainty size swept; standard deviations reported.
- **Evidence:** PDF pp.2-5, model/Algorithms 1-4; p.7, Experiments/Table 1/Fig.1.
  Defense allocation, not an anomaly detector; gap undefined if lower bound is zero.

### S19 — Exploiting Social Influence to Control Elections Based on Scoring Rules

Corò, Cruciani, D'Angelo, Ponziani; IJCAI 2019;
[extended arXiv v2][S19]; proceedings copy retained (experiments omitted there).

- **Model/method:** budgeted seeds; linear-threshold ranking diffusion;
  constructive/destructive weighted influence-surrogate greedy approximation;
  plurality or positional scoring/Borda. Rank displacement controlled by `alpha`;
  voter response is diffusion, not strategic best reply.
- **Metrics:** **PoV = target wins/20 diffusion trials** per configuration;
  mean **final target score minus strongest opponent score**, possibly negative.
  The empirical MoV deliberately **does not subtract initial margin** (p.23 footnote 6).
- **Protocol:** facebook/irvine/netscience/polblogs; random edge weights;
  2/5/10 candidates; ten preference assignments; budgets 5/10/15;
  `alpha=.1/.5/1`; 20 diffusion trials; 43,200 runs, distribution plots.
  Runtime averaged ≈15 minutes/run on reported hardware; not our latency estimate.
- **Evidence:** PDF pp.4-7, model; pp.22-27, §8/Fig.1/Tables 1-3.

### S20 — Opinion Diffusion and Campaigning on Society Graphs

Faliszewski, Gonen, Koutecký, Talmon; IJCAI 2018; [proceedings][S20].

- **Model:** weighted **voter-type** graph, initially adjacent-ranking-swap
  edges; entire type assimilates into a strictly majority-weight neighboring
  type. Synchronous/asynchronous updates until no assimilation. Graph nodes are
  not individual people; type-edge distance is not physical proximity.
- **Controller:** budgeted unit-cost shifts before diffusion; exact
  **ILP/parameterized algorithms**; optimistic/pessimistic choices over asynchronous
  schedules. Generalized type, action and rule encodings also discussed.
- **Evaluation:** formal feasibility, hardness, FPT and convergence bounds in
  number of types; no measured campaigning heuristic benchmark or dataset.
  Candidate co-winner semantics differs from our single deterministic winner.
- **Evidence:** PDF pp.2-3/220-221, §2/Proposition 1; pp.5-6, §§3-4.

### S21 — Multi-Party Campaigning

Koutecký, Talmon; AAAI 2021; [proceedings][S21].

- **Actors:** competing budgeted campaigners alter voter types via paid moves;
  sequential multi-round play with responses and generalized diffusion/budgets.
  Campaigners strategize; voters are not necessarily strategic reasoners.
- **Method:** exact **Presburger-arithmetic winning-strategy formulation**,
  quantifier elimination and convex optimization under bounded parameters;
  rule/type/move extensions. Not a sampled-agent heuristic or learned campaign policy.
- **Evaluation:** fixed-parameter tractability and winning-strategy existence/
  optimization, parameter dependence; no empirical election dataset, runtime
  comparison or repeated-simulation success metric. Horizon/budget/rule are model
  inputs, not universally fixed defaults.
- **Evidence:** PDF pp.2-4, technical framework/basic model; pp.5-7, extensions.
  Relevant to later competing-campaign stages, not evidence those stages exist here.

### S22 — Manipulating Elections by Changing Voter Perceptions

Wu, Estornell, Kong, Vorobeychik; IJCAI 2022; [proceedings][S22].

- **Model:** attacker shifts **perceived target-candidate position** under an
  `l_p` budget; binary/real issue space; distance-generated rankings and scoring
  rules/plurality cases. Identical perception change across voters; no interpersonal
  diffusion, repeated ballot-response process or detector in core model.
- **Methods:** exact restricted-case algorithms: representative points,
  ball-intersection feasibility, linear programming; complexity varies with issue
  dimension, distinct voter types, candidate count and norm.
- **Evaluation:** constructive/destructive control feasibility, hardness and
  tractable parameter regimes; no measured heuristic/runtime/data benchmark.
  True voter ideals, candidate position and perceived candidate position must stay distinct.
- **Evidence:** PDF pp.1-2, §§1-3; pp.4-6/560-562, §4/Theorems 6-12.

### S23 — Election Manipulation in Social Networks with Single-Peaked Agents

Auletta, Carbone, Ferraioli; 2023 proceedings;
[extended arXiv v1][S23].

- **Model:** seed-budgeted influence shifts positions on ideological axis;
  cascade probabilities, plurality, single-/nearly-single-peaked rankings;
  repeated campaigns; no epistemic voter best response.
- **Methods:** greedy weighted-influence approximation; **SPoutdeg / _rev /
  _merge0.5**, **SPneig2 / _rev / _merge0.5**; weighted PageRank variants
  **SPpagerank1.0_pos, 0.5_pos, 1.0_hop2_pos, 1.0_manip_eq1,
  1.0_manip*_pos**. Rank by political closeness/manipulability plus network reach.
- **Metrics/protocol:** expected margin improvement, normalized margin improvement,
  runtime/scalability, noise sensitivity. Five candidates; 20/50/100 voters;
  budgets 5/10/15%; influence `.1..4`, up to ten campaigns; 800 synthetic
  scenarios/cell (approximation subset 775); Facebook 4039-node case;
  Monte Carlo error bounds; SD tables; scalability up to 20k nodes.
- **Evidence:** PDF pp.3-5, model; pp.9-13, §4; pp.14-23, §5,
  especially Eq.(9)/Corollary 1 and Tables 2-4. Tables report normalized gain;
  its denominator is not explicitly specified in the audited passages. Eq.(9)
  defines raw gain and Corollary 1 its range; do not infer a normalization silently.

### S25 — Voter Participation Control in Online Polls

De, Dey, Sanyal; AAMAS 2025 extended abstract;
[full arXiv 2410.12256v2][S25]; proceedings abstract retained.

- **Model:** controller pays voters not to participate; only nodes reachable
  from poll initiator after deletion count. Undirected graph, fixed candidate
  choices, plurality, **unique-winner** control; no strategic ballot switching.
- **Methods/objective:** budget-feasible vertex removal for constructive or
  destructive success; exact graph/parameterized algorithms, including treewidth
  dynamic programming; budgetless variants considered. Reachability, not repeated
  opinion diffusion, determines participation.
- **Evaluation:** complexity, tractability and parameter dependence; no empirical
  heuristic comparison, trial count, runtime measurements or detection metric.
- **Evidence:** full PDF pp.3-5, §3/problem definitions/results; subsequent
  proof/algorithm sections. Short proceedings PDF pp.1-2 independently matches model.

### S26 — Shift Bribery over Social Networks

Hota, Bandopadhyay, Dey; [arXiv 2510.21200v3, June 2026][S26]; preprint.

- **Model:** informed briber purchases upward ranking shifts; initial shifts
  transmit through directed weighted incoming edges. Effective shift is own
  shift plus floored weighted neighbor shifts, capped by available rank positions.
  This is a specified **one-hop transformation**, not arbitrary iterated cascading.
  Lexicographic election ties; plurality/majority special cases.
- **Methods:** exact special-graph algorithms, tree-decomposition/dynamic
  programming and parameterized reductions; costs/budget, degree, treewidth,
  cluster-deletion and supporter deficit distinguish cases.
- **Evaluation:** hardness, running-time bounds and parameterized complexity
  tables; no empirical policy benchmark, seeds or measured accuracy/runtime.
- **Evidence:** PDF pp.2-3, contributions/Definition 2.1/Tables 1-2;
  pp.4-9, algorithmic results. Do not cite malformed template venue/date as publication proof.

### S27 — Information gerrymandering and undemocratic decisions

Stewart et al.; *Nature* 573, 2019; [full text + supplement][S27].

- **Model:** two teams; local intention polls on directed influence network;
  six conditional voting probabilities (three projected outcomes × early/late
  phase); fixed-party zealots/bots. Payoffs reward team victory but may prefer
  opponent consensus to deadlock. Not ordinary multi-candidate plurality utility.
- **Metrics:** final share, consensus-win/deadlock frequencies, payoff;
  influence assortment/gap; model-versus-human outcome distributions. Parameters
  fitted by maximum likelihood on baseline, tested on network treatments.
- **Protocol:** 2,520 unique human subjects, 120 sessions; 24-player groups,
  12/team, 240 seconds, 60% threshold, payoffs 2/.5 in main conditions;
  baseline balanced exposure, gerrymandering and bot placements; logistic,
  binomial, signed-rank and chi-squared tests described in supplement.
- **Evidence:** PDF pp.1-4, Figs.1-4/Eqs.(1)-(2); pp.12-17,
  supplement §§1-2. Human data does not validate our current conformity rules.

### S28 — Is the Voter Model a Model for Voters?

Fernández-Gracia, Suchecki, Ramasco, San Miguel, Eguíluz;
PRL 112:158701, 2014; [arXiv v2 + supplement][S28].

- **Method:** **SIRM** noisy voter copying with recurrent home/work contacts,
  population and commuting fluxes; binary opinions. Random cell-update order,
  binomial transitions/Monte Carlo steps; no strategic utility or attacker budget.
- **Metrics:** centered county vote-share distribution and SD; spatial
  correlation `C(r)` (distance-binned normalized covariance); temporal vote-share
  dispersion; model/data share ratios with 80% intervals; coarse-graining consistency.
- **Protocol:** US presidential elections 1980-2012; 2001 census commuting/
  populations; year-2000 initialization; noise/mobility calibration; 100-realization
  means/SD in Fig.3; compare counties, districts, states. Not target-win optimization
  or a ballot-stability benchmark.
- **Evidence:** PDF pp.1-4, Eqs.(1)-(3)/Figs.1-3; supplementary methods thereafter.
  Physical commuting structure differs from ideology-distance networks.

### S29 — On the robustness of democratic electoral processes to computational propaganda

Givi, Delabays, Jacquemet, Jacquod; *Scientific Reports* 14:193, 2024;
[publisher PDF][S29].

- **Model:** anchored linear opinion consensus on multi-party simplex;
  ideology-distance graph from natural opinions; final opinions taken at equilibrium;
  several seat-allocation systems. Largest opinion component determines party.
- **Attack heuristic:** favour first runner-up; target agents near its boundary
  and electoral units with smallest majorities; increment natural-opinion shifts
  until outcome flips. Described efficient strategy, not proven globally minimal attack.
- **Metric:** effort `xi_u=K_u/n_u`; national effort
  `xi_total=sum_u (n_u/N)*xi_u`, where `K_u` counts influence increments.
  Compare robustness distributions/rank frequencies across electoral systems,
  polarization/connectivity; qualitative US House volatility comparison.
- **Evidence:** PDF pp.2-7, results/Figs.1-5; pp.8-10, Methods/Eqs.(1)-(10).
  Linear-system convergence does not apply to our strategic voting dynamics;
  effort is model-specific, not monetary cost or necessarily distinct people.

### S30 — Governator vs. Hunter and Aggregator

Lehrer, Schumacher; *PLOS ONE* 13(2), 2018;
[readable publisher PDF][S30]; original garbled-text print retained.

- **Party rules:** **Aggregator** moves toward supporters' mean; **Hunter**
  keeps direction after gains, reverses/randomizes after losses; **Sticker** stays;
  **Governator** approaches government position; **Satisficing Governator** stays
  when in government. Government-formation satisficing uses caretaker utility
  as aspiration; evolutionary experiment lets unsuccessful parties change rules.
- **Model:** fixed voter ideals, nearest-party voting, two-dimensional platforms,
  proportional seats/government formation; party ideal and expressed position
  distinct; maximum move `.12`. Not strategic voter ballot heuristics.
- **Metrics/protocol:** mean party eccentricity, mean squared nearest-party
  distance (**system misery**), normalized government misery; rule survival/utility
  in evolutionary study. 500 burnt-in chains/input; surrogate regressions and
  standard errors; one-rule versus mixed-rule populations.
- **Evidence:** PDF pp.3-9, model/rules/measurement; pp.13-18, evolutionary study.

### S31 — A method for evaluating cognitively informed micro-targeted campaign strategies

Madsen, Pilditch; *PLOS ONE* 13(4), 2018; [publisher PDF][S31].

- **Agents:** Bayesian source-credibility voters; targeted versus stochastic
  campaigners. Expertise/trust beliefs affect posterior support after messages;
  turnout probability separate. Targeted campaign filters persuadable, sufficiently
  credible, likely-turnout voters, then samples contacts; stochastic baseline
  contacts without those filters. Repeated contacts allowed across days.
- **Protocol:** 10,000 voters, two candidates, 50 ticks; campaign reach and
  credibility means `.4/.5/.6` varied; 100 repetitions × 9 credibility pairs ×
  10 reach settings = 9,000 runs; NetLogo. Votes cast after campaign, not every tick.
- **Metrics:** mean final vote share and reach needed to break even against
  opponent; compare targeted/stochastic strategies. No calibrated national-election
  accuracy, strategic regret or network-equilibrium metric.
- **Evidence:** PDF pp.5-8, cognitive/update model and ABM; pp.9-10, Fig.3/results.
  Proof-of-principle persuasion assumptions, not established human causal effects.

### S32 — FlockVote

Zhou, Xu, Wang, Wang; [arXiv 2512.05982v1][S32], 2025;
ICAIS 2025 stated by authors, independently unconfirmed here.

- **Method:** profile/context-conditioned LLM returns candidate/other probabilities;
  aggregate agent probabilities. Demographic sampling, candidate context and
  prompts are experimental factors. **No interacting social network** in core
  experiment; no strategic ballot-response/equilibrium heuristic.
- **Metrics:** aggregate support percentages and winner agreement against actual/
  polling outcomes; mean/SD across population-size trials; demographic ablations;
  variation across models, context wording and candidate-key order. Do not invent
  MAE/RMSE/calibration scores where not reported.
- **Protocol:** seven 2024 US swing states; ACS/religion profiles; primary
  Qwen model plus other LLMs; temperature zero except main result `.7`;
  10-2,000 agents in size study,
  ten trials/size; 300/state selected subsequently. No-context/context comparisons.
- **Evidence:** PDF pp.3-10, §§3-4/Figs.2-7/Tables 1-3. Retrospective agreement,
  rationale plausibility and prompt sensitivity are separate validity questions.

## Heuristic comparison matrix

Names denote **paper methods**, not implemented simulator features.

| Family / sources | Actor; required information | Decision/objective | Eclipse status / main incompatibility |
| --- | --- | --- | --- |
| Truthful, k-pragmatist — S5/S7 | Voter; ranking + poll leaders | Favourite overall / favourite among k leaders | Sincere implemented; pragmatist **absent**; not `top_k` |
| AU, CV_eta, LD+LB, TRT/CMP/LB — S7 | Voter; utilities/poll, fitted parameters | Attainability-utility / subjective pivotality / leader bias / type rules | **Absent** as named paper variants; fitting requires human data |
| Pivotal/direct response — S4/S11-S14 | Voter; current or believed score, tie rule | Preferred attainable winning outcome | `pivotal` variant; fixed threshold 1; simultaneous/moving departures |
| Full/pivotal EU — S9/S10 | Voter; local ballots, cardinal utilities | Expected winner utility | Exact `expected_utility` includes multiway/near outcomes; not paper Full oracle |
| Top-K/Max-M/TieU/H/R/Poisson — S10 | Voter; local support, utility, population/sample size | Simplified pivotal gains | Names implemented; inertia/ties/scheduling/utilities/Poisson differ |
| Local dominance, truth/lazy bias — S6 | Voter; plausible scores, current action | Robust improvement; bias variants | Fixed-total L1 dominance only; truth/lazy variants absent |
| Maximin conditional choice — S1/S2 | Voter; epistemic profile information classes | Best worst outcome; conditional equilibrium | Score-world `maximin` only; no higher-order/conditional-equilibrium solver |
| Considerate improving moves — S8 | Coalition; graph cliques, member/neighbor welfare | Joint gain without harming relatives | Absent; not an attacker coalition by default |
| Greedy supporter-edge construction — S11 | Organizer; network/preferences/poll | Force and stabilize target victory with fewer edges | Strategic edge policy absent; campaign layer alone insufficient |
| Specter/pair/2PW-H reports — S12-S14 | Pollster; electorate, feasible reports, target | Constructive/destructive victory | Attack optimizers absent; initial poll input is not optimizer |
| MOV/POV influence surrogates — S17/S19 | Controller; diffusion/utility/ranking model | Margin or win-probability effect under seed budget | Absent; requires explicit diffusion and evaluation oracle |
| Political-distance/PageRank — S23 | Controller; topology, ideology, probabilities | Rank seed usefulness over campaigns | Absent; centrality guarantees do not transfer (S16) |
| FTPL/online gradient + greedy defense — S18 | Attacker/defender; channel/payoff beliefs | Approximate minimax expected switched voters | Absent; distinct from detection |
| ILP/PA/DP control — S20-S22/S25-S26 | Campaigner; types, costs, graph/issue space | Exact feasible winning strategy in bounded cases | Absent; **algorithms**, not generic voter heuristics |
| SIRM / anchored opinion dynamics — S28/S29 | Voter; contact/commuting or opinion graph | Copying/noisy influence / anchored consensus | Absent; `random_walk` and conformity are not these models |
| Party adaptation — S30 | Party; support/history/government | Platform/office-oriented rules | Absent; nearest-party voter not strategic EU voter |
| Credibility targeting — S31 | Campaigner/voter; source beliefs, turnout | Bayesian persuasion and filtered contact | Absent; requires distinct belief/turnout state |
| Six-probability voting game / zealots — S27 | Voter; local poll, time/payoff regime | Conditional stochastic support, avoid deadlock | Absent; different election/payoff semantics |
| Profile-conditioned LLM — S32 | Generative agent; demographic/context prompt | Output support probabilities | Absent; not required for Eclipse |

## Metric comparison matrix

`R` = independent experiment instances; `H` = declared horizon; `s_p` = target
score; `SW` = source-specific social welfare. Undefined ratios stay undefined.

| Published measure | Definition / denominator / direction | Sources; eligibility and caveat |
| --- | --- | --- |
| Decision disagreement | Different heuristic/Full choices ÷ identical-observation queries; lower | S10 §3; same utilities, observations and election semantics required |
| Decision runtime | Seconds per response, averaged over benchmark trials; lower | S10; candidate/population/sample scaling; hardware-dependent |
| Condorcet efficiency | CW elected ÷ tested profiles **having a CW**; higher | S5 §4.4, S6 §6; S12 additionally conditions on converged equilibria |
| Winner agreement / consistency | Match other rule or ground truth; modal winner frequency across repeated starts | S6; comparator and random-start/scheduler denominator must be named |
| Borda welfare | Aggregate Borda-derived winner utility; change vs sincere | S6; ordinal welfare proxy, not measured human satisfaction |
| Price of Honesty / Stability | `SW_truth/SW_strategic`; `SW_strategic/SW_optimal` | S9 §4; **negative quadratic utilities**; do not reuse sign interpretation blindly |
| Strategic-ballot fraction | Final nontruthful ballots ÷ voters | S9; deviation from sincerity is not necessarily successful manipulation |
| Stabilization/convergence | Updates/steps, convergence frequency; cycle/equilibrium stopping | S6/S9/S12; scheduler-specific; winner, ballot and full-state stability differ |
| SF ratio | Third-place support / second-place support; lower = greater two-party concentration | S9/S10; not an intrinsic welfare objective; undefined if denominator zero |
| Target election/non-election frequency | Qualifying target victories/failures ÷ test instances | S12/S13; raw success includes targets already winning/losing |
| Pollster winner rank | Mean final winner rank in pollster preference; lower | S12 Fig.4; converged cases only; also report exclusions |
| Margin improvement | `E[(s_p-max_other s)_after-(s_p-max_other s)_before]` | S15-S17/S23; baseline/opponent can change; units votes unless normalized |
| Final target margin | `E[s_p-max_other s]` after campaign, possibly negative | S19 §8 footnote 6; **not** its theoretical improvement objective |
| Probability of victory | Target victories ÷ independent diffusion realizations | S17/S19; declare tie/success semantics; S19 uses 20/configuration |
| Approximation/comparator quality | Heuristic objective / solver comparator objective | S17; comparator optimality/sample error must be established; zero denominator invalid |
| Normalized margin gain | Reported normalized gain; denominator not explicit in audited passages | S23 Tables 2-6; Eq.(9)/Corollary 1 define raw gain/range, not an unambiguous normalization |
| Added edges / affected voters | Counts/overhead needed by found construction | S11 §6; “found cost” does not establish global minimum |
| Defense payoff / optimality bound | Expected switched voters; `(b_u-b_l)/b_l` | S18; not detection precision/recall; lower-bound zero needs separate handling |
| Manipulability probability / PSV | Analytical probability over culture; expected fraction strategic | S14; theoretical bounds, not empirical confidence intervals |
| Human-choice prediction | Per-class precision/recall/F1; weighted F1 on held-out rounds | S7 §4.2; actual/predicted-axis inconsistency flagged; needs real labels |
| Influence gap / consensus | Network influence-assortment difference; win/deadlock rates | S27; two-team supermajority game, not ordinary plurality |
| Spatial/temporal fit | Share distribution/SD, `C(r)`, temporal dispersion, prediction/data ratios | S28; spatial election-data validation, not voter-strategy optimality |
| Influence effort | `xi_u=K_u/n_u`; `xi_total=sum_u n_u*xi_u/N` | S29 Eqs.(8)-(9); increments to flip result, not certified least possible intervention |
| Representation | Mean eccentricity; `mean_v d(ideal_v,nearest_party)^2`; government misery `1-sum d(ideal,median)^2/sum d(ideal,government)^2` | S30 p.8; lower misery better; platform/government models required |
| Campaign efficiency | Final share and reach required for break-even against stochastic campaign | S31 Fig.3; model-specific credibility/turnout assumptions |
| Generative-model robustness | Aggregate shares/winner agreement; trial SD; prompt/model/key-order sensitivity | S32; no automatic human validity or calibration claim |
| Formal guarantees | Existence, convergence assumptions, complexity, approximation/parameter bounds | S1-S4/S8/S15-S16/S20-S22/S25-S26; not empirical scores |

## Current simulator mapping

Read-only source check: `voting.py`, `metrics.py`, `experiments.py`;
[implemented-policy reference](voting-heuristics.md) and
[verification caveats](heuristic-verification-report.md). No code or experiments changed.

| Capability | Present | Missing / comparison requirement |
| --- | --- | --- |
| Decision tracing | Scoped observations, score/world traces, deterministic replay | Held-out identical-observation decision benchmark; paper Full reference distinct from exact EU |
| Voting rules | Plurality winner over global ranked ballot length | Other counting rules, paper random election ties, sequential scheduling |
| Policy assumptions | Rank-derived utility default; optional explicit utility; startup selector | Spatial quadratic utility/preference generation matching S9/S10; calibrated human parameters |
| Empty observations | Smoothed uniform prior when strategic local sensors see nobody | S9 freezes isolated voters; uniform-prior decisions are a different assumption |
| EU approximations | Named S10-inspired policies | Poisson numerical sums != paper asymptotic Skellam; TieU correction differs; inertia differs; document Top-2 parity before rankings |
| Uncertainty | Fixed-total L1 worlds, dominance/maximin | Full epistemic profile worlds, higher-order knowledge, conditional equilibrium; source-matched radii/biases |
| Existing output | Counts/shares/groups, winner margin, winner rank, switching; comparison rank-utility/runtime/stable-window flags | Nontruthful fraction, CW eligibility/efficiency, SF ratio, decision regret, latency distributions/peak memory |
| Paired interventions | Researcher-scheduled edits and paired target-share/margin summaries | Actual poll/edge/campaign adversaries, budgets and equal-budget attack controls; no robustness claim yet |
| Dynamics | Full-horizon runs; winner/ballot stable windows; failures retained | Reactivation/censor-aware timing; full-state cycles only under appropriate state assumptions |
| External validity | Synthetic simulations | Human-choice data for S7-style prediction; election/commuting data for S28; do not infer realism from synthetic agreement |

## Recommended evaluation contract — proposed, not published results

Operational follow-up: [candidate plan](plans/heuristic-evaluation.md) and
[metric dictionary](heuristic-evaluation-metrics.md). The stricter requested
full-model convergence gate currently fails; recommendations below are research
context, not authorization to run experiments or certify convergence.

1. **Correctness gates:** independent tiny-state oracle; permitted-information
   invariance; valid ballots; tie/scheduler semantics; replay; explicit workload
   failures. Reproduce known cycles and S16-style graph counterexamples where applicable.
2. **Decision benchmark:** same observation/current ballot/utility snapshots;
   disagreement and exact-EU regret for EU approximations. Dominance/maximin get
   their own objective checks. Compare against both paper-style Full and exact EU
   only when labelled separately; vary sample/time budgets.
3. **Clean outcomes:** rank-utility welfare gap vs best available winner and
   matched sincere control; conditional CW efficiency; group utility; nontruthful
   fraction/SF ratio as diagnostics. No single weighted “best heuristic” score.
4. **Attacks, once implemented:** paired added target-win probability;
   conditional success among baseline losses; final target margin **and** margin
   change; welfare loss; realized budget-effect curves; equal-budget random/
   published attackers. Never call smallest found cost an optimum without proof.
5. **Dynamics/cost:** first-choice and full-ballot switches separately; switch
   opportunities, winner vs ballot stability,
   reactivation, cycle/cutoff/failure rates; censor-aware timing; median/p95
   decision/round time, peak memory; browser render latency separately.
6. **Design:** varied electorates/candidate counts, 499/500/501 parity controls,
   graph/exposure/mobility, utility gaps, update schedules, tie orders and information.
   Pair electorate/exogenous streams; replication uncertainty over independent
   runs, not over correlated voters. Calibration/evaluation separated; retain all failures.
7. **Conditional modules only:** human prediction F1 needs labels; defense game
   gap needs best-response bounds; detector precision/recall/delay needs attack
   labels and no-attack drift controls; representation/commuting fit needs those
   specific model states/data. These are not universal metrics for every heuristic.

## Verification / remaining work

- Original PDFs unchanged; all selected files opened with `pdfinfo`/`pdftotext`;
  title/author identity checked, including arXiv/HAL covers; SHA-256 manifest.
- Equations visually checked: S7 confusion/F1 p.8; S14 two-potential-winner
  construction p.5; S29 effort p.9; S30 representation p.8. S23 methods/normalization
  checked against pp.15-17 and tables. Parser repair/font warnings are recorded
  as extraction limits, not missing research results.
- New downloads may be different versions of the same work; manifest explicitly
  distinguishes five retained alternatives. No identical-hash duplicate selected works.
- Research audit does not complete Stage 01/02 or validate new simulator behavior.

[S1]: <../References/S1-strategic-voting-and-the-logic-of-knowledge.pdf>
[S2]: <../References/How%20does%20uncertainty%20about%20other%20voters%20determine%20a%0Astrategic%20vote%3F.pdf>
[S3]: <../References/S3-strategic-voting-with-incomplete-information.pdf>
[S4]: <../References/S4-convergence-to-equilibria-in-plurality-voting.pdf>
[S5]: <../References/S5-voter-response-to-iterated-poll-information.pdf>
[S6]: <../References/S6-a-local-dominance-theory-of-voting-equilibria.pdf>
[S7]: <../References/S7-predicting-strategic-voting-behavior-with-poll-information.pdf>
[S8]: <../References/S8-strategic-voting-in-a-social-context-considerate-equilibria.pdf>
[S9]: <../References/S9-the-echo-chamber-strategic-voting-and-homophily-in-social-networks.pdf>
[S10]: <../References/S10-boundedly-rational-voters-in-large-r-networks.pdf>
[S11]: <../References/S11-adapting-the-social-network-to-affect-elections.pdf>
[S12]: <../References/S12-poll-confident-voters-in-iterative-voting.pdf>
[S13]: <../References/Manipulation%20of%20Opinion%20Polls%20to%20Influence%20Iterative%20Elections%20-%20p132.pdf>
[S14]: <../References/S14-do-we-care-about-poll-manipulation-in-political-elections-fulltext.pdf>
[S15]: <../References/S15-election-control-in-social-networks-via-edge-addition-or-removal.pdf>
[S16]: <../References/S16-election-manipulation-on-social-networks-seeding-edge-removal-edge-addition-fulltext.pdf>
[S17]: <../References/S17-controlling-elections-through-social-influence.pdf>
[S18]: <../References/S18-defending-elections-against-malicious-spread-of-misinformation.pdf>
[S19]: <../References/S19-exploiting-social-influence-to-control-elections-based-on-scoring-rules-fulltext.pdf>
[S20]: <../References/S20-opinion-diffusion-and-campaigning-on-society-graphs.pdf>
[S21]: <../References/S21-multi-party-campaigning.pdf>
[S22]: <../References/S22-manipulating-elections-by-changing-voter-perceptions.pdf>
[S23]: <../References/S23-election-manipulation-in-social-networks-with-single-peaked-agents.pdf>
[S25]: <../References/S25-voter-participation-control-in-online-polls-fulltext.pdf>
[S26]: <../References/S26-shift-bribery-over-social-networks.pdf>
[S27]: <../References/S27-information-gerrymandering-and-undemocratic-decisions.pdf>
[S28]: <../References/S28-is-the-voter-model-a-model-for-voters.pdf>
[S29]: <../References/S29-on-the-robustness-of-democratic-electoral-processes-to-computational-propaganda.pdf>
[S30]: <../References/S30-governator-vs-hunter-and-aggregator-a-simulation-of-party-competition-with-vote-seeking-and-off-fulltext.pdf>
[S31]: <../References/S31-a-method-for-evaluating-cognitively-informed-micro-targeted-campaign-strategies-an-agent-based-.pdf>
[S32]: <../References/S32-flockvote-llm-empowered-agent-based-modeling-for-simulating-u-s-presidential-elections.pdf>
