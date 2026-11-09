# Heuristic metric contract

Maintained metric specification; existing runtime metrics implement only a subset.
This dictionary is not a coverage claim or experimentally validated ranking.
Selected statistical follow-up: [occupation-frequency specification](plans/stochastic-stability.md#5-evaluation-specification-execution-deferred).
It permits continuing flips and class-dependent limits; it is not an absorption
metric, a per-round-law certificate or implemented stationarity detection.
Outcome simulations N>=100; tiny oracle cases are verification-only.
[Plan](plans/heuristic-evaluation.md) · [Convergence gate](heuristic-convergence.md) · [Published methods](literature-heuristics-and-metrics.md).

## Notation and measurement boundary

N fixed voters, C candidates, m=|C|, B_i(t) full submitted ballot, b_i(t) its first
choice, s_c(t) first-choice count, w(t) deterministic plurality winner. Preferences
and utilities are distinct from ballots. Evaluator may access truth; never feed
evaluator-only values into policy observations. Record group membership at t.
Use frozen pre-intervention preferences/utilities for attack welfare comparisons;
changed-preference welfare is a separately labelled outcome.

All election metrics per committed frame; primary outcome is certified terminal
state when available. Cutoff outcome labelled horizon-specific, never equilibrium.
Comparisons pair the same electorate/exogenous draws. Seeds/runs—not voters or
time steps—are independent replication units. No cross-role aggregate score.

## Formula dictionary

| Metric | Definition | Eligibility / undefined cases |
| --- | --- | --- |
| Invalid-action/ballot violations | Count invalid accepted actions/ballots; count rejected invalid proposals separately | Accepted count must be zero; expected negative-test rejections are not failures |
| Information leakage | Paired decision differences after hidden-state changes preserving allowed input, memory and RNG | Must be zero; use identical complete authorized inputs |
| Budget violation | max(0, realized cost - allowed budget), plus illegal unit/action counts | Must be zero; no pooling different budget units |
| Exact-oracle error | Decisions violating independently calculated policy optimum / queries | Must be zero for exact methods, allowing explicitly defined co-optimal ties; approximation error reported separately |
| Replay mismatch | Divergent deterministic model-state hashes/decisions / compared checkpoints | Must be zero within recorded software/environment; exclude wall time/render metadata |
| Proof status | certified / refuted / unsupported; theorem/domain/certificate reference | Per composition, not inferred from outcomes |
| Certified absorption T | Earliest t for which all permitted reachable future ballots equal B(t) | Null without certificate; quiet window gives only observed stability |
| Pre-absorption flips | sum over t=1..T and i of 1[B_i(t)!=B_i(t-1)] | Requires certified T; also report first-choice counterpart |
| Cycle occurrence | Certified reachable recurring transition cycle with nonconstant ballots | Repeated ballots alone insufficient; distinguish existential counterexample from observed path |
| Run statuses | Counts and fractions certified-absorbed / observed-cycle / cutoff / failed | Denominator all attempted runs; categories exclusive; quiet windows auxiliary only |
| First-choice switching | sum_i 1[b_i(t)!=b_i(t-1)] / N | t>=1; first frame null |
| Full-ballot switching | sum_i 1[B_i(t)!=B_i(t-1)] / N | t>=1; suffix changes counted even under plurality |
| Winner changes | sum_t 1[w(t)!=w(t-1)] | Fixed declared horizon or certified T, labelled |
| Nontruthful share | sum_i 1[b_i(t)!=private_favourite_i] / N | Separate full-ballot prefix disagreement; not evidence of harmful behaviour |
| Decision regret | max_a Q_i(a|O_i)-Q_i(chosen|O_i) | Same observation/utility/model oracle; exact EU, maximin and dominance objectives not interchangeable |
| Approximation disagreement | Non-co-optimal approximation decisions / matched oracle queries | Report exact-EU and paper-Full references separately; null if oracle exceeds budget |
| Winner utility | U(w)=sum_i u_i(w)/N | Normalized rank utility u_i(c)=1-rank0_i(c)/(m-1), m>1; m=1 null for rank metric; synthetic interpersonal proxy |
| Welfare gap | max_c U(c)-U(w) | Same frozen utility basis; nonnegative except numeric tolerance |
| Sincere-relative welfare | U(w_policy)-U(w_sincere) | Paired runs, same electorate/preferences; report group means separately |
| Condorcet efficiency | Runs electing strict Condorcet winner / runs containing one | Strict pairwise majority against every alternative using full private rankings; no CW -> excluded with eligibility count; zero eligible -> null |
| Target victory probability | sum_r 1[w_r=target] / R | Fixed target rule chosen before treatment; valid completed results only with coverage/failure bounds below |
| Added attack success | mean_r(1[w_attack,r=target]-1[w_control,r=target]) | Complete matched pairs; may be negative; report constructive/destructive separately |
| Conditional attack success | Target victories under attack among pairs where control target loses / control-loss pairs | Zero baseline losses -> null; not same as added success |
| Target margin | M=s_target-max_{c!=target}s_c | m>=2; may be negative; tie victory follows fixed tie rule |
| Margin improvement | M_attack-M_control | Paired outcomes; distinguish within-run final-initial change |
| Realized cost | Sum accepted charged actions in declared units | Also attempts/rejections and budget utilization; zero allowed budget -> utilization null |
| Success-budget curve | Target victory/added success against realized and allowed cost | Equal model/knowledge/horizon; minimum found cost not proven optimum |
| Defense benefit | Attack objective_undefended - attack objective_defended | Paired attack/controller assumptions; fixed attack and adaptive best-response tracks separate |
| Defender cost | Accepted defense spending and utilization | Separate attacker units; no anomaly-detection metrics unless detector/labels exist |
| Runtime | Median/p95 decision and round elapsed seconds | Monotonic clock; exclude setup/serialization/rendering; cold/warm separately; record hardware |
| Peak memory | Maximum process resident bytes during run | Fresh process and sampling method/interval recorded; report measurement limits |
| Failure rate | Failed attempts / all attempts | Resource-limit, invalid-state and environment failures separated; never impute success |
| Sensitivity | Within-case paired changes and cross-seed distributions of above metrics | Tie order, source, graph, mobility, mixture, utility and size/parity explicitly labelled |

Dominance regret is not a scalar utility difference: record whether the selected
action violates the declared dominance/undominated-choice contract; additionally
report observed utility consequences. Monte Carlo methods may disagree with exact
oracles; report sampling uncertainty rather than calling every disagreement a bug.

## Aggregation, censoring and controls

- Every result includes numerator, denominator, scenario, policy version, horizon,
  information boundary, tie/schedule rules and proof domain. Null != zero.
- Report run-level mean/median/distribution and 95% uncertainty per cell;
  paired differences use paired run bootstrap. Proportions use Wilson intervals.
- Failed runs remain in all-attempt summaries. Outcome means use available results
  with explicit coverage; no silent complete-case policy ranking. Binary outcomes
  also report all-attempt worst/best bounds: observed successes/R through
  (successes+unresolved)/R. Paired added-success bounds assign unresolved pair
  differences -1/+1. Cutoffs unresolved for terminal outcomes, valid only for
  explicitly horizon-specific metrics.
- Absorption statistics: certified T distribution plus cutoff/failure counts;
  no invented terminal time. If later using survival estimates, justify censoring
  assumptions separately; resource failures are not automatically noninformative.
- Sensitivity is not convergence proof. Report flip reactivation after quiet
  windows and after allowed perturbations as counterexample diagnostics.
- Clean controls: sincere, sensed conformity, source-matched oracle where feasible.
  Attack controls: no intervention and equal-budget random legal intervention.
  Defense controls: undefended counterpart, same observation/action constraints.
- Logs include exact utility definitions, targets, intervention budgets and
  source-method deviations. Do not import an undefined source normalization
  (notably S23) or ambiguous confusion-matrix orientation (S7).

## Acceptance

- Hand calculations for switches, negative target margins, margin deltas, utility,
  CW eligibility and paired success; tie winners resolved by configured order.
- Challenge zero eligible CW, one candidate, first frame, empty group, unavailable
  oracle, budget zero, unresolved pairs and truncated history; nulls explicit.
- Challenge repeated ballot windows with later flips, constant-winner cycles,
  hidden-state changes, mixed policies and RNG replay. Never certify by timeout.
- Certified claims follow [confirmed foundation cases](convergence-foundations.md).
  Exploratory finite-horizon experiments can use uncertified policies when labelled;
  report run horizon, failures, observed switches and possible cycles.
