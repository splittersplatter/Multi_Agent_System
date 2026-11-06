# Election manipulation: literature survey and gap analysis

**Working research record — 2 November 2026.** Scope: the seven mechanisms in
the final [Eclipse-MAS proposal](</home/dhruv/Downloads/Eclipse-MAS-Proposal.pdf>).
Project scope/order is now fixed in the [roadmap](project-roadmap.md) and
[stage plans](plans/README.md); this survey supplies research evidence, not a
competing roadmap. It maps published models, not verified open-source implementations.
“Implemented” below means the paper specifies or simulates a mechanism; public
code availability is not assumed.

**Full-text collection/method audit — 7 November 2026:**
[paper-by-paper heuristics and metrics](literature-heuristics-and-metrics.md),
[local PDFs and access status](../References/README.md). 31/32 works available;
S24 still blocked. The 36 PDFs include five retained versions/prints, not 36
independent papers. Original files and historical survey scope retained. This
audit adds method/metric evidence and bibliographic corrections; it is not a
fresh systematic search or a simulator replication. In particular, k-pragmatist
and Top-K EU differ; S14 evaluates analytical success probabilities; final
margin, margin change and victory probability must not be pooled. S7's
confusion-axis inconsistency and S23's unclear normalized-gain denominator are
flagged rather than silently resolved. No novelty or stage-completion claim added.

## Main findings

1. **Poll manipulation is a close precedent, including repeated polls.**
   [Wilczynski 2019](https://ojs.aaai.org/index.php/AAAI/article/download/4055/3933)
   studies a strategic polling agency, local social observations, iterative
   plurality voting, and both one-poll and repeated-poll dynamics. The
   [2020 extension](https://ifaamas.org/Proceedings/aamas2020/pdfs/p132.pdf)
   adds constructive/destructive goals and distance-restricted poll changes;
   [Mousseau et al. 2024](https://doi.org/10.3233/FAIA240908) study restricted
   distortion and average-case conditions without a social network. Thus,
   repeated polls, bounded distortion, strategic voters, and local information
   are **not individually new**.
2. **Edge control is established.** [Sina et al. 2015](https://aamas.csc.liv.ac.uk/Proceedings/aamas2015/aamas/p705.pdf)
   combine network edge addition, polls and iterative strategic voting;
   [Castiglioni et al. 2020](https://doi.org/10.1609/aaai.v34i02.5556) and
   [2021](https://arxiv.org/abs/1911.06198) study edge changes with an influence
   diffusion model. Their different response assumptions matter when comparing
   tractability: neither model's conclusions automatically transfer to the other.
3. **Epistemic voting and networked simulations have strong separate
   foundations.** [van Ditmarsch et al.](https://arxiv.org/abs/1310.6436) and
   [Bakhtiari et al.](https://arxiv.org/abs/1809.10489) formalize knowledge and
   strategic voting. [Tsang and Larson](https://www.ifaamas.org/Proceedings/aamas2016/pdfs/p368.pdf)
   model network observations and expected-utility voting. A worthwhile next
   question is whether a *specific* false-signal information model changes
   strategic decisions compared with the poll-confident model—not whether
   combining logic and voting is novel by itself.
4. **Candidate alignment and adversarial preference influence are established.**
   [Lehrer and Schumacher 2018](https://doi.org/10.1371/journal.pone.0191649)
   model moving party positions; [Wu et al. 2022](https://doi.org/10.24963/ijcai.2022/79)
   manipulate voter perceptions in a spatial model; and
   [Givi et al. 2024](https://doi.org/10.1038/s41598-023-50648-6) model
   vector-valued opinions and external shifts. A detective observing only
   aggregate ballots remains a narrower, candidate intersection to investigate.
5. **Guarantees require precise semantics.** A false reported poll is an
   observation, not automatically a truthful public announcement. Knowledge
   must remain factive, whereas a voter can hold a false belief. A voter knowing
   that *some* manipulation exists is different from knowing *one particular*
   manipulation works in every possible world. The final proposal's examples
   are hypotheses or design choices, not established necessities: in particular,
   coalition coordination need not require common knowledge, and anomaly
   detection alone need not establish knowledge of an attack.

## Method and limits

This is a **targeted, citation-chained survey, not a systematic review**. The
search was run on 2 November 2026 using the final proposal, its two cited papers,
the repository's poll-manipulation paper, conference/publisher full texts and
academic indexes. Searches included combinations of *epistemic logic*,
*strategic/iterative voting*, *poll manipulation*, *social network*, *edge
addition*, *election influence*, *agent-based*, *spatial voting*, *detection*,
and *adversarial game*. References in the 2019 and 2020 poll papers were traced
backward; later work was sought through title/keyword searches and academic
index matches for 2020–2026. For example, S13 cites S12, S11, S17 and S18;
the later S14 explicitly positions itself against S12 and S13, while S25 cites
network-control work. These trails supplemented the independent date sweep.
This is search-based forward chasing, not a complete citation-index census.

The 32 records below are deduplicated by work. Peer-reviewed proceedings and
journals are preferred; preprints are explicitly labelled. Core comparisons
were checked against the accessible paper's model and results sections,
including [S9–S17, S19–S23, S27–S30]. S24 is based on its institutional
abstract: its full text was not accessible in this pass. Other concise entries
use the linked text or abstract as indicated and do not imply a complete
reproduction. A scholarly metadata service matched 24 of 25 checked
identifier/title pairs; its identifier resolution for S13 was ambiguous, so
the linked AAMAS proceedings and supplied paper are the authority for that
record. This is a metadata check, not an independent validation of findings.
Search access and terminology limit coverage, so
“not found” means *not found under this protocol*, not proof of absence.

**Evidence categories:** D = direct precedent for at least one Eclipse
mechanism; P = partial precedent; I = adjacent inspiration. Logic/theory
papers can be important without having a simulation. In source entries, an
unreported variable is marked **not established here** instead of being inferred.

## Coverage of the seven proposal mechanisms

| Eclipse option | Mechanisms already studied | Representative sources | Remaining specific question |
| --- | --- | --- | --- |
| 1. Proximity-defined dynamic edges | Recurrent physical mobility with election-like vote-share patterns; dynamic contacts and spatial opinion influence. | S28, S29; networked strategic voting S9–S10 | Does physical proximity-driven edge turnover alter **strategic, epistemic** voter outcomes? An exact combination was not found under this protocol. Opinion-distance neighborhoods are not the same as physical distance. |
| 2. Strong adversarial minority: sight, coordination, deception, eavesdropping | Strategic coalitions, network-positioned bots, differing player information, adversarial messages and competition. | S8, S16–S18, S21, S27 | Isolate each capability at a fixed coalition size, with explicit observations and decision rules. A four-capability comparison with formal voter knowledge was not found. |
| 3. Strategic edge addition | Edge additions change strategic-voting information and, separately, diffusion paths; removal and different budgets are also studied. | S11, S15–S16 | Compare *equal-budget* edges under limited attacker knowledge and evolving voter information; no claim that any such comparison is absent across all literature. |
| 4. Global-information manipulation | Manipulated one-off and repeated polls, plausibility and distance constraints, strategic updating, and complexity/experiments. | S12–S14 | Study a specified false-observation epistemic semantics and matched response rules against S12/S13. A formal knowledge/belief implementation with this exact combination was not found. |
| 5. In-network leader selection and alignment vectors | Spatial voter/candidate vectors, adaptive parties, and manipulated candidate perceptions. | S22, S23, S29–S30 | Electing leaders *from the network in a first stage* and voting for them in a second, under strategic knowledge restrictions: exact mechanism not found in this targeted search. |
| 6. Alignment alteration and detective | Alignment/opinion shifts and election robustness; attacker–defender games and misinformation detection interventions. | S18, S22–S24, S29 | Distinguish detectable anomalies from proof of manipulation; evaluate observability, false positives, and early warning before three consecutive wins in the same model. Exact full combination not found. |
| 7. Public-favoring leaders | Parties change public positions in response to election results, while party ideals may stay fixed. | S30; also S22 | Model hidden true leader shifts separately from perceived positions; compare indirect public behavior signals with a no-signal control. Public-position adaptation in prior work is adjacent, not the same hidden-state mechanism. |

The “not found” entries are search results, not novelty certifications. In
particular, S12 already models manipulative repeated polls; S11 already combines
edge addition with an adversarial poll; and S18 already incorporates differing
attacker/defender information.

The following cross-map identifies papers that cover each *component* of an
option. A row does not imply that all components appear together in one paper.
An em dash means no source in this corpus was mapped to that component for the
row, not that no such work exists anywhere.

| Eclipse option | Strategic decisions / knowledge | Polls / deception | Network or mobility | Coalitions / defense | Spatial / leader alignment |
| --- | --- | --- | --- | --- | --- |
| 1. Dynamic edges | S9–S10 | — | S28–S29 | — | S28–S29 |
| 2. Adversarial minorities | S8, S18 | S12, S27 | S11, S16, S27 | S8, S18, S21 | S23, S29 |
| 3. Edge addition | S11 | S11 | S11, S15–S16 | S16 | — |
| 4. Global information | S1–S3, S6 | S12–S14, S25 | S11–S13 | S18 | — |
| 5. Network leader selection | S30 | — | S9–S10 | — | S22–S23, S30 |
| 6. Altering alignments and detective | S18 | S18, S22 | S23–S24, S29 | S18 | S22–S23, S29 |
| 7. Public-favoring leaders | S30 | S22 | — | — | S22, S30 |

## Source notes

Notation: **A/I** = actors/actions and their information; **D/R** = dynamics,
network, rule and strategic criterion; **Result/limit** = contribution and the
boundary relevant here. “No network” describes the paper's model, not reality.

### Knowledge, information and strategic voting

**S1.** van Ditmarsch, Lang & Saffidine, [Strategic Voting and the Logic of Knowledge](https://arxiv.org/abs/1310.6436), TARK 2013; linked author preprint. **P**, epistemic voting. A/I: voters choose reported preferences under uncertainty about others and higher-order knowledge. D/R: finite knowledge profiles and information updates; several voting examples, no social graph required; strategic manipulation/equilibrium definitions. Result/limit: public polls and preference revelation change knowledge; foundational formal models rather than a validated population simulation.

**S2.** Bakhtiari, van Ditmarsch & Saffidine, [How does uncertainty about other voters determine a strategic vote?](https://arxiv.org/abs/1809.10489), *Studies in Logic* 12(3):32-56, 2019; linked arXiv v2. **P**, epistemic voting. A/I: agents know their own preferences but may be uncertain about others and their knowledge. D/R: finite possible worlds, preference profiles, knowledge, public announcements and strategic concepts; no physical interaction graph required. Result/limit: de dicto/de re manipulation, dominance and conditional equilibrium are already formalized; no probabilistic or arbitrary deceptive-message semantics follows automatically. Semantic reference for the planned model; former implementation removed.

**S3.** Endriss, Obraztsova, Polukarov & Rosenschein, [Strategic Voting with Incomplete Information](https://ijcai.org/proceedings/2016/41), IJCAI 2016. **P**, strategic/iterative game theory. A/I: voters choose ballots using an information set defined by a published winner, score vector or majority graph. D/R: repeated unilateral deviations; plurality, veto, k-approval, Borda, Copeland and Maximin; no social graph. Result/limit: manipulations and convergence depend on rule and disclosure; a stable *winner* is not necessarily a stable ballot profile.

**S4.** Meir, Polukarov, Rosenschein & Jennings, [Convergence to Equilibria in Plurality Voting](https://doi.org/10.1609/aaai.v24i1.7624), AAAI 2010. **P**, iterative voting game. A/I: uncoordinated voters alter individual ballots based on available outcome information. D/R: plurality, repeated unilateral responses, specified tie-breaking; no social graph. Result/limit: Nash convergence depends on strategy and game assumptions, so finite-horizon simulations must not assume convergence unconditionally.

**S5.** Reijngoud & Endriss, [Voter Response to Iterated Poll Information](https://ifaamas.org/Proceedings/aamas2012/papers/2D_5.pdf), AAMAS 2012. **P**, poll-informed strategic voting. A/I: voters observe one poll or a sequence of aggregate disclosures, then select votes according to response rules. D/R: single and repeated polls, several voting rules; no local network. Result/limit: theoretical and experimental comparisons show disclosure can help or hurt outcome quality; it does not itself model a malicious pollster.

**S6.** Meir, Lev & Rosenschein, [A Local-Dominance Theory of Voting Equilibria](https://arxiv.org/abs/1404.4688), EC 2014; linked extended preprint. **P**, bounded-rational game and simulation. A/I: voters consider possible scores near a poll without assigning probabilities and select locally dominating ballots. D/R: repeated plurality updates and a local-dominance equilibrium; no explicit social graph. Result/limit: convergence results have specified assumptions and simulations use synthetic and preference data; uncertainty sets are not higher-order epistemic models.

**S7.** Fairstein, Lauz, Gal & Meir, [Predicting Strategic Voting Behavior with Poll Information](https://arxiv.org/abs/1805.07606), 2018 preprint. **P**, behavioral comparison. A/I: voters combine poll scores and candidate utility; alternatives include expected-utility and heuristic rules. D/R: fit/compare predicted choices against controlled human voting data; no social network is central. Result/limit: the proposed heuristic performs well on the studied data, a useful response-rule baseline but not proof of real election prediction.

**S8.** Gourvès, Lesca & Wilczynski, [Strategic Voting in a Social Context: Considerate Equilibria](https://doi.org/10.3233/978-1-61499-672-9-1423), ECAI 2016. **P**, coalitional voting game. A/I: voters have preferences and consider the welfare of socially related agents; feasible coalitions follow network cliques. D/R: graph-restricted coalitional deviations and considerate equilibria; voting-rule cases are paper-specific. Result/limit: coalitions on graphs are already a formal topic; this is not a deception or observation-advantage simulation.

### Networked voters and public signals

**S9.** Tsang & Larson, [The Echo Chamber: Strategic Voting and Homophily in Social Networks](https://www.ifaamas.org/Proceedings/aamas2016/pdfs/p368.pdf), AAMAS 2016. **D**, networked strategic-voting simulation. A/I: voters see neighbors' ballots and infer likely outcomes; private preferences enter expected utility. D/R: iterative plurality with network homophily and strategic ballot revision. Result/limit: network structure affects strategic voting and modelled welfare; no explicit epistemic logic or attacker is required.

**S10.** Tsang, Salehi-Abari & Larson, [Boundedly Rational Voters in Large(r) Networks](https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p301.pdf), AAMAS 2018. **D**, scalable strategic-voter simulation. A/I: local neighbor ballots inform each voter's expected gains; heuristic voters approximate a fuller calculation. D/R: iterative networked plurality with top-k and other heuristics; analysis considers district size. Result/limit: heuristics can reproduce qualitative behavior with less computation; they remain specific behavioural assumptions.

**S11.** Sina, Hazon, Hassidim & Kraus, [Adapting the Social Network to Affect Elections](https://aamas.csc.liv.ac.uk/Proceedings/aamas2015/aamas/p705.pdf), AAMAS 2015. **D**, network control and game simulation. A/I: voters see neighbor ballots and a public poll; an organizer adds edges to favor a target. D/R: iterative strategic plurality and constrained information; theory plus simulations. Result/limit: the paper gives edge-addition guarantees under explicit preference/support assumptions and also considers an adversarial poll; do not transfer its guarantees to other voter-update rules.

**S12.** Wilczynski, [Poll-Confident Voters in Iterative Voting](https://ojs.aaai.org/index.php/AAAI/article/download/4055/3933), AAAI 2019. **D**, poll manipulation and iterative game/simulation. A/I: a polling institute announces scores; voters trust them and observe local ballot deviations, with pivotal thresholds. D/R: plurality on directed networks, one initial or repeated polls, local and global dynamics; pollster action subject to a likelihood condition. Result/limit: convergence is conditional and global dynamics may cycle; the paper studies manipulative repeated global polls too. Score beliefs are not a full DEL model.

**S13.** Baumeister, Selker & Wilczynski, [Manipulation of Opinion Polls to Influence Iterative Elections](https://ifaamas.org/Proceedings/aamas2020/pdfs/p132.pdf), AAMAS 2020; also supplied locally. **D**, poll-control game, complexity and experiments. A/I: an informed pollster sends plausible initial scores; each voter sees neighboring ballots. D/R: iterative plurality or veto, directed network, deterministic tie order, voter deviations and bounded poll-distance variants. Result/limit: constructive and destructive manipulation are analyzed, with heuristics and no-manipulation/exact comparisons; its principal simulated distortion is the initial poll.

**S14.** Mousseau, Surugue & Wilczynski, [Do We Care About Poll Manipulation in Political Elections?](https://doi.org/10.3233/FAIA240908), ECAI 2024. **D**, strategic poll manipulation. A/I: a pollster broadcasts candidate scores; voters trust the score and each can respond once without seeing others' deviations. D/R: plurality and truthful starting ballots, no network, bounded and unbounded poll changes. Result/limit: complexity and asymptotic probability depend on deviation bounds and preference cultures; it does not analyze network-local information.

### Influence, games and electoral control

**S15.** Castiglioni, Ferraioli & Gatti, [Election Control in Social Networks via Edge Addition or Removal](https://doi.org/10.1609/aaai.v34i02.5556), AAAI 2020. **D**, network-control complexity. A/I: an external controller alters edges while influencers and their candidate messages are fixed. D/R: network diffusion and election control for different candidate/message cases. Result/limit: hardness and reoptimization results hold under the stated diffusion and objective assumptions; not a model of strategic epistemic voters.

**S16.** Castiglioni, Ferraioli, Gatti & Landriani, [Election Manipulation on Social Networks: Seeding, Edge Removal, Edge Addition](https://doi.org/10.1613/jair.1.12826), *Journal of Artificial Intelligence Research* 2021; publisher full text collected; earlier arXiv v2 retained. **D**, network-diffusion election control. A/I: an outside agent selects seeds or changes edges; messages concern one or more candidates. D/R: independent-cascade influence over a graph and winner/margin objectives. Result/limit: broad worst-case and approximation hardness results; worst-case hardness does not imply all practical instances are hard.

**S17.** Wilder & Vorobeychik, [Controlling Elections through Social Influence](https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p265.pdf), AAMAS 2018. **D**, election-control optimization and simulation. A/I: budgeted outside actor selects information sources; affected nodes transmit stochastically and may change preferences. D/R: network diffusion followed by plurality; target-win probability and margin objectives. Result/limit: approximation/hardness analysis and experiments; voters do not use the strategic-poll reasoning of S12.

**S18.** Wilder & Vorobeychik, [Defending Elections Against Malicious Spread of Misinformation](https://bryanwilder.github.io/files/aaai_election_defense.pdf), AAAI 2019. **D**, attacker–defender game. A/I: attacker and defender choose budgeted channels; paper compares fully known, stochastic, asymmetric and adversarial uncertainty. D/R: zero-sum influence game with propagation probabilities and a defender mixed strategy. Result/limit: approximation algorithms and experiments use advertising-channel data; the payoff is expected voter switching, not proof that an anomaly detector knows an election was manipulated.

**S19.** Corò, Cruciani, D'Angelo & Ponziani, [Exploiting Social Influence to Control Elections Based on Scoring Rules](https://doi.org/10.24963/ijcai.2019/29), IJCAI 2019. **D**, rank diffusion and electoral control. A/I: a controller initiates network influence to affect a target candidate's ranking. D/R: linear-threshold ranking model and positional scoring rules. Result/limit: theoretical approximation depends on rule and diffusion; the voter response is influence-based rather than a strategic epistemic best response.

**S20.** Faliszewski, Gonen, Koutecký & Talmon, [Opinion Diffusion and Campaigning on Society Graphs](https://doi.org/10.24963/ijcai.2018/30), IJCAI 2018. **D**, clustered campaigning/diffusion. A/I: campaigner changes preferences of clusters under a budget; opinions propagate between clusters. D/R: society graph, specified diffusion and election rule, with cheapest-campaign analysis. Result/limit: tractability in relevant bounded-cluster settings depends on the model; it does not establish individual-level strategic voter behavior.

**S21.** Koutecký & Talmon, [Multi-Party Campaigning](https://doi.org/10.1609/aaai.v35i6.16693), AAAI 2021. **D**, sequential multi-agent campaigning game. A/I: several competing campaigners choose actions in alternating rounds under budget and action constraints. D/R: general election outcomes and possible network diffusion, solved via bounded-parameter logical formulations. Result/limit: competing adaptive campaigns are already formalized; use as a strategic-game comparison, not evidence of an implemented DEL simulation.

**S22.** Wu, Estornell, Kong & Vorobeychik, [Manipulating Elections by Changing Voter Perceptions](https://doi.org/10.24963/ijcai.2022/79), IJCAI 2022. **D**, spatial election control. A/I: controller changes perceived candidate positions within a norm budget; voter preferences derive from distances in issue space. D/R: binary or real-valued issue positions, plurality and other scoring-rule cases; no dynamic interpersonal network in the core model. Result/limit: complexity varies with candidate/issue/voter structure; perceptions must be distinguished from changing true voter ideals.

**S23.** Auletta, Carbone & Ferraioli, [Election Manipulation in Social Networks with Single-Peaked Agents](https://doi.org/10.1007/978-3-031-47546-7_32), 2023 proceedings; [full preprint](https://arxiv.org/abs/2308.10845). **D**, structured-preference network control. A/I: a controller influences voters whose rankings follow an ideological ordering. D/R: information diffusion on graphs and election objectives; algorithmic complexity plus heuristics. Result/limit: preference restrictions do not remove all hardness; the model does not provide a detective with knowledge of hidden interventions.

**S24.** Liu, Kato, Gu, Ren, Su & Zhang, [Diffusion of Ordinal Opinions in Social Networks: An Agent-Based Model and Heuristics for Campaigning](https://doi.org/10.1109/TCSS.2024.3458950), *IEEE Transactions on Computational Social Systems* 12(1), 2025. **D**, ordinal opinion-diffusion simulation. A/I: voter agents carry rankings and external campaigning changes some nodes' opinions. D/R: non-progressive, multi-opinion network diffusion with personalized features; the abstract does not establish a voting rule or epistemic game. Result/limit: a heuristic is compared to greedy for margin/runtime. **Abstract/metadata only:** full text was unavailable, so update after reading it.

**S25.** De, Dey & Sanyal, [Voter Participation Control in Online Polls](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2484.pdf), AAMAS 2025 extended abstract. **P**, network poll control. A/I: a poll spreads from an initiator through participants; a budgeted controller induces selected non-participation. D/R: a graph and plurality poll outcome, with complexity analysis. Result/limit: information exposure and participation jointly bias the poll; it is not identical to a pollster falsifying reported counts or to a subsequent election.

**S26.** Hota, Bandopadhyay & Dey, [Shift Bribery over Social Networks](https://arxiv.org/abs/2510.21200), arXiv preprint, 2025, version 3 June 2026. **P**, preference control and complexity. A/I: a budgeted agent pays for preference shifts, which propagate over a directed weighted network. D/R: ranking shifts with plurality/majority special cases and graph-parameter algorithms. Result/limit: theoretical complexity and restricted-case algorithms; publication status beyond the preprint is not established here and voter decisions are not DEL-based.

### Adjacent simulations and empirical inspiration

**S27.** Stewart et al., [Information gerrymandering and undemocratic decisions](https://doi.org/10.1038/s41586-019-1507-6), *Nature* 2019; [full text](https://ide.mit.edu/sites/default/files/publications/2019%20Stewart%20et%20al%20-%20Nature.pdf). **D**, networked voting game/experiment. A/I: two teams observe local aggregates and choose votes with incentives; some experiments include fixed-behavior bots. D/R: controlled influence networks and repeated collective decisions, mathematical analysis plus human experiments. Result/limit: information exposure can bias group decisions in the studied game; it is not evidence that its mechanism alone changed a national election.

**S28.** Fernández-Gracia, Suchecki, Ramasco, San Miguel & Eguíluz, [Is the Voter Model a Model for Voters?](https://doi.org/10.1103/PhysRevLett.112.158701), *Physical Review Letters* 2014. **P**, mobility and opinion simulation. A/I: agents move recurrently and copy or change opinions under social influence/noise. D/R: spatial population/mobility inputs, noisy voter dynamics, comparison to election vote-share correlations. Result/limit: a mobility reference for option 1; agents are not strategic epistemic plurality voters.

**S29.** Givi, Delabays, Jacquemet & Jacquod, [On the robustness of democratic electoral processes to computational propaganda](https://doi.org/10.1038/s41598-023-50648-6), *Scientific Reports* 2024. **D**, vector opinion dynamics and election robustness. A/I: voter vectors evolve from natural opinions and social interactions; external influence shifts some natural opinions. D/R: opinion-distance interaction and alternative electoral systems; simulation and qualitative comparison to election volatility. Result/limit: robustness patterns are conditional on the model and should not be treated as general causal evidence; no detective in the core model.

**S30.** Lehrer & Schumacher, [Governator vs. Hunter and Aggregator: A simulation of party competition with vote-seeking and office-seeking rules](https://doi.org/10.1371/journal.pone.0191649), *PLOS ONE* 2018. **D**, party competition simulation. A/I: parties do not know the consequences of position shifts and choose heuristics balancing policy/office goals; voters select the closest party. D/R: repeated elections, two-dimensional positions, proportional representation and government formation; party ideal points stay fixed. Result/limit: adaptive expressed positions and competing motivations already exist; no epistemic network or adversarial detector.

**S31.** Madsen & Pilditch, [A method for evaluating cognitively informed micro-targeted campaign strategies: An agent-based model proof of principle](https://doi.org/10.1371/journal.pone.0193909), *PLOS ONE* 2018. **I**, belief and campaign simulation. A/I: campaign agents communicate with cognitively heterogeneous voter agents; voter response depends on credibility. D/R: simulated campaigning and belief updates; exact voting-rule/network details are not established in this review. Result/limit: illustrates sensitivity to the persuasion model; evidence is proof-of-principle simulation, not a validated operational model.

**S32.** Zhou, Xu, Wang & Wang, [FlockVote: LLM-Empowered Agent-Based Modeling for Simulating U.S. Presidential Elections](https://arxiv.org/abs/2512.05982), 2025 arXiv v1; authors report ICAIS 2025 publication, not independently verified here. **I**, recent generative-agent election simulation. A/I: profile-conditioned language-model agents receive stated candidate information and output vote probabilities. D/R: state-level aggregation in an ex-post 2024 election case; the paper's setup does not establish strategic network equilibrium. Result/limit: useful as a contrasting experimental design, but retrospective agreement and generated rationales do not independently validate individual behavior or eliminate training-data leakage; no LLM is required for this project.

## Candidate gaps to investigate

Scores are historical **feasibility / distinctness**, 1–5, where 5 meant easier
for the former baseline / more potentially distinct. Reassess feasibility against
the current Stage 01 implementation. Distinctness is a provisional
assessment of the exact intersection against the sources above, not a novelty
guarantee. This historical ranking concerns research interest, not implementation
order or a semester deadline; the milestone roadmap includes all seven mechanisms.

| Rank and candidate | Falsifiable research question | Closest precedent and extension to demonstrate | Score |
| --- | --- | --- | --- |
| 1. False signals and epistemic voter response | With matched electorates, network, and poll perturbations, do explicit possible-world decision rules change target-win frequency or winner-change rate compared with poll-confident and local-dominance voters? | S12–S14 already cover local, repeated and bounded poll manipulation; S1–S3 and S6 cover uncertainty/knowledge. Demonstrate a precisely specified false-observation model and an effect beyond their response baselines, not merely “poll manipulation with DEL.” | 4 / 4 |
| 2. Capability ablation for adversarial minorities | At fixed coalition size and communication budget, how do sight, coordination, deceptive reports and expanded observation individually change simulated outcome impact? | S8, S11, S16–S18, S21 and S27 already study coalitions, networks, information asymmetry or bots. Demonstrate fair, one-capability-at-a-time comparisons under the same voter and budget model; test interaction only after individual effects. | 3 / 3 |
| 3. Physical contact turnover under the same information budget | Does proximity-based edge turnover change intervention impact relative to a static graph with matched average degree and contact exposure? | S9–S12 and S28–S29 already cover networked strategic voting or mobility/opinion proximity. Show that any difference remains after controlling for degree, exposure and initial preferences; do not equate physical and ideological distance. | 3 / 3 |
| 4. Early detection with limited observations | Can a detector using only allowed ballot aggregates reliably identify a bounded alignment shift before the target achieves three consecutive wins, relative to normal preference drift? | S18, S22–S24 and S29 cover defense, spatial manipulation or evolving opinions. Measure false-positive rate, recall and detection delay against no-attack drift and observation-matched controls. Treat a statistical alert as belief/evidence, not knowledge. | 2 / 4 |
| 5. In-network nomination with candidate adaptation | How do endogenous nominee composition and signal-mediated hidden leader adaptation separately change outcomes compared with exogenous nomination and fixed leaders? | S22, S29–S30 cover spatial preferences or party adaptation. An identical-nominee/no-information-effect control should be equivalent; use different nominee sets to study composition effects. Separate true alignment, public signals and perceived position. | 2 / 3 |

## Research protocol for roadmap experiments

1. **Replicate a baseline:** reproduce a hand-worked S12/S13 style case with
   truthful poll and no intervention; compare against a bounded intervention.
   The former source/tests were deleted; a new Stage 01 baseline exists, but
   this poll-specific replication remains unverified. Repeated-poll simulation,
   private/false-announcement semantics and empirical validation remain pending.
2. **Declare information:** record for each actor the exact public and private
   observations; prevent strategies from accessing simulator truth. Specify
   whether reports are truthful observations, possibly false claims, or noisy
   samples, and how each type changes possible worlds or beliefs.
3. **Use matched controls:** pair the same electorate, graph, target, update
   schedule and random draws when comparing interventions. Include no attack,
   random/baseline intervention with equal budget, and the closest published
   response rule. Common seeds alone do not ensure matched randomness after
   branches diverge; assign streams or replay exogenous draws explicitly.
4. **Measure and report:** predefine target-win and winner-change rates,
   target vote-share/margin changes, and preference-rank costs; report seed-level
   outcomes and uncertainty/variation, not only the favorable runs. Record
   cycles and finite-horizon cutoffs rather than assuming convergence.
5. **Validate in layers:** check election and information updates by hand on
   tiny models; compare finite possible-world calculations with enumeration;
   evaluate any approximate large-population beliefs against the small exact
   model. Knowledge claims require factivity and complete information sets;
   sampling alone cannot prove knowledge. Reassess source coverage and the
   gap matrix before committing to a novelty claim.

Candidate gaps remain hypotheses, not findings. The roadmap now requires all
seven individual studies plus integration. Use each stage's defined observations,
controls and acceptance gates; refine the closest comparison before its experiments.
This update aligns scope on 3 November 2026; it does not refresh the literature search.
