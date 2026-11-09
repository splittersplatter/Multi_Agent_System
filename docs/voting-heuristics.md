# Voting policies

Updated 9 November 2026. One engine: CLI/browser/replay/exports. Plurality;
ranked ballots retain global `k`; party order breaks election ties. These are
explicit source-informed variants, not claims of exact paper reproduction.
New permission-scoped epistemic policies and their distinct world-count limit:
[epistemic guide](epistemic-voting.md), including bounded-signal variants.
Certified sequential cases:
[convergence foundation](convergence-foundations.md).
Comparison `stability_assessment` explicitly remains uncertified; it records recent
contact-arc changes and flips after quiet windows. No quiet-window auto-stop.
[Future-contact proof routes](dynamic-network-stability.md).

Population contract: normal runs N>=100. `population-scenario.toml` remains a
large sensor-enabled workload; undersized legacy `heuristics.toml` is verification
only. Startup policy selection does not grant sensing or prove convergence.

## Start

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/population-scenario.toml --port 8008
```

Before Play/Next/edit: select **Startup voting heuristic**, inspect JSON defaults,
click **Apply voting choice**. Applies to all groups; replaces voting-specific
individual/scheduled overrides; preserves other policies, parameters and abilities.
Restart server for a fresh episode. Rewind is not restart. Existing server must
restart after source changes. Use submitted-vote colors to observe switching.

CLI preselection:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/population-scenario.toml --port 8008 --voting top_k --voting-parameters '{"top_k":2}'
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/population-scenario.toml --voting local_dominance --voting-parameters '{"uncertainty_radius":2}' --checkpoint outputs/eclipse-heuristic-checkpoint.json
```

Checkpoint output must not already exist. Inspector **Agent reports and memory**
shows policy, observed count, utilities, response scores/world count, previous vote,
selected vote and switching; poll modes additionally retain believed scores and
last observed choices. Traces are researcher-visible, not shared between voters.

## Rules and source mapping

| ID | Implemented ballot response | Source / departure |
| --- | --- | --- |
| `sincere` | Private ranking prefix | Existing control |
| `local_plurality` | Most frequent first choice in delivered reports; ranking breaks ties; no reports -> sincere | Existing report-based conformity control |
| `sensed_plurality` | Same, using deduplicated trusted neighbor ballots | Existing sensor-based conformity control |
| `pivotal` | Maintain poll belief; remove own vote; evaluate every replacement; switch only if best achievable winner is strictly preferable | [Baumeister et al. 2020, §2.2](https://ifaamas.org/Proceedings/aamas2020/pdfs/p132.pdf). Plurality best response; simultaneous, mobile-network extension here; veto not implemented |
| `memory_pivotal` | Estimate support from explicit initial poll and recent unique incoming proximity contacts; switch only if it strictly improves the predicted winner | S9/S12/S13-inspired adaptation; simultaneous, moving, uncertified; requires `k=1` and enabled `majority_estimation` |
| `expected_utility` | Enumerate multinomial scores of other voters; maximize expected winner utility | [Tsang & Larson 2016, §2.2](https://www.ifaamas.org/Proceedings/aamas2016/pdfs/p368.pdf). Here exact multiway ties included, deterministic tie order; not their pairwise-only approximation |
| `top_k` | Retain locally most-supported K candidates; renormalize support; maximize summed pairwise pivotal utility gains | [Tsang et al. 2018, §2.3](https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p301.pdf). K is consideration-set size, independent of ballot `k` |
| `max_m` | Maximize largest pairwise pivotal utility gain, rather than sum | Same source, Max-M |
| `tie_u` | Uniformly sample enumerated two-way winning-tie score states; estimate pair probabilities | Same source, TieU family; use population/sample correction for an unbiased sum estimate; full enumeration still required |
| `tie_h` | Sample tied leaders' count, then feasible bounded allocations to randomly ordered other candidates; sum likelihoods | Same source, TieH family; nonuniform heuristic, not unbiased uniform-state sampling |
| `tie_r` | Draw multinomial elections; use frequency of each exact two-way winning tie | Same source, TieR; finite samples can observe no ties |
| `poisson` | Independent Poisson score model; sum two-way winning-tie probabilities using Poisson PMF and other-candidate CDFs | Same source, Poisson family; numerical PMF/CDF variant, NOT paper's asymptotic Skellam approximation; cutoff `max(mean)+12*sqrt(max(mean)+1)+50` |
| `local_dominance` | Switch only to a ballot weakly improving every possible state's winner and strictly improving at least one; prefer undominated dominators in ranking order | [Meir et al. 2014, §4](https://arxiv.org/html/1404.4688v2). Fixed-population L1 set here; original allows other metrics/variable totals |
| `maximin` | Maximize worst winner utility across possible score states | [Bakhtiari et al., §5.1](https://arxiv.org/abs/1809.10489). Exact score-world decision criterion; NOT full DEL, higher-order knowledge or conditional-equilibrium solver |

The original ten strategic modes use own ranking, previous ballot, authorized trusted ballot
sensors, public population/candidate counts, parameters and actor-round RNG.
Reports are not silently treated as trusted ballots. No sensor permission => empty
local sample (uniform smoothed prior), not access to hidden votes. Choosing a policy
does not grant sensing. Own vote excluded from sampled neighbors. Duplicate channels
to one sender count once. Policy choice leaves movement RNG unchanged.

All rounds remain simultaneous; every voter sees completed previous ballots through
post-movement/post-graph channels. No paper convergence theorem is asserted.
Utility-maximizing modes retain current vote on objective ties (`1e-12` tolerance),
then private ranking breaks remaining ties. Top-K may eliminate the current choice.
Pivotal and dominance require strict improvement; ballot suffix follows private ranking.

## Parameters

TOML: `[groups.residents.parameters.voting]`. Per-person overrides use
`parameters.voting`. CLI/UI parameters are that nested object's contents.

| Field | Default / contract |
| --- | --- |
| `utility_mode` | `"rank"`: normalized descending rank utilities, synthetic assumption; `"explicit"` requires `utilities` |
| `utilities` | Party->finite utility, absolute value <=1e6, weakly consistent with own ranking; configure per person when rankings differ |
| `top_k` | 2; positive integer <=100; effective min(K, party count) |
| `samples` | 200; 1..100000; TieU/H/R |
| `uncertainty_radius` | 2; integer 0..20; fixed-total L1 ball, excluding own ballot; radius 1 admits no vote transfers |
| `possible_scores` | Optional nonempty list of nonnegative integer vectors, party order, each sums to N-1; replaces generated world set for dominance/maximin |
| `information_source` | `"native"`: local sample except pivotal uses poll; `"poll"`: all strategic modes use maintained poll belief |
| `poll` | `"initial_truthful"`; or `"explicit"` with `initial_poll` vector of nonnegative integers summing to N |
| `max_states` | 200000; 1..1000000; hard enumeration/summation budget; sampled workloads also guarded |

Local sample probabilities: `(observed_count[c]+1)/(observed_neighbors+parties)`.
Local uncertainty center: largest-remainder rounding of `(N-1)*probabilities`.
Poll-based probabilities: `(believed_other_scores[c]+1)/(N-1+parties)`; uncertainty
center is the believed other-score vector. Poll belief starts from the configured
public initial poll, then applies own changes and changes between successive known
ballots of the same observed sender. Newly encountered senders establish a baseline;
their unobserved earlier changes are unknown. Negative/inconsistent poll beliefs fail.
Poll-based modes cannot be introduced/reset mid-episode; restart instead.

At most 32 parties for strategic policies. Exact EU space:
`choose(N+M-2,M-1)`; exact Top-K/Max-M and TieU enumeration can also be expensive.
Exact EU evaluates only pivotal profiles, including multiway/near ties, and
subtracts the action-independent abstention outcome; exhaustive small-state tests
verify identical utility differences. TieR uses exact conditional-binomial
factorization of the multinomial distribution, with inverse-CDF sampling.
500-agent browser responsiveness is NOT verified for these policies. Start with
the nine-person `examples/population-scenario.toml`. No resource-limit fallback to another rule.
Poisson truncation and Monte Carlo error are approximation limits, not exact guarantees.

## Matched experiments

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli compare examples/population-scenario.toml --seeds 11 22 33 --rounds 30 --window 10 --output outputs/eclipse-heuristics.json
```

Default: sincere + sensed-plurality + all ten strategic policies. Optional
`--policies pivotal expected_utility top_k max_m tie_u tie_h tie_r poisson local_dominance maximin`.
Use `--parameters '{"information_source":"poll"}'` to match strategic information;
native-policy comparisons otherwise conflate response rule with information source.
Conformity controls remain local by definition. Utilities and uncertainty assumptions
must be varied separately before substantive conclusions.

JSON retains full scenario per completed run, seeds, parameters, manifest/plugin
hashes, metric time series, final decisions, runtime, total switching, final switch
fraction, winner stability window and mean winner normalized-rank utility proxy.
Failures retained with reason/completed round; never drop or rank them as successes.
States labelled `observed_ballot_stability`, `horizon_reached`, or `failed`; an unchanged
window is not convergence, equilibrium, consensus, or proof of no future switching.
Repeated ballots on a moving graph are not a proof of a full-state cycle.

No universal “best”: choose primary objective before experiments; compare paired
seed differences, uncertainty, runtime and sensitivity. Current rank-utility proxy
is not validated interpersonal welfare. Fixed electorate + paired movement seeds
do not establish human realism. No substantive experiments validated yet.

## Verification record

Current suite/evidence: [status](implementation-status-report.md#verification).
Independent `test_voting_verification.py` checks exact-EU, pivotal, dominance and
maximin oracles; all13 baseline/strategic policies use actual verification HTTP
startup, CLI-equivalent frames, CSV and checkpoint replay.

Important retained limits: Top-2 exact-tie parity (test499/500/501), different
native information across policies, inactive report-only controls without messages,
finite-sample/truncation error, numerical objective ties. Match observations and
utility before attributing outcome differences to a response rule.

[Historical verification/results](history/heuristic-verification.md) retain the
original source-stamped findings. No best heuristic or general convergence follows
from those runs. `memory_pivotal` is exploratory and distinct from `pivotal`.

## Memory-pivotal

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000 --voting memory_pivotal
```

Requires explicit `[majority_estimation]` and k=1. After movement, each person
caches previous-round first choices from incoming proximity neighbors. It blends
its unique recent contacts with the latest poll, interprets shares as expected
other-voter support `(N-1)p`, and predicts winners after each possible vote.
Election ties use party order. It switches to its favorite achievable winner
only for a strict improvement over retaining its vote; all voters act simultaneously.
Exact integer comparisons avoid rounding fabricated electorates. No hidden current
counts/preferences, reports or persistent/campaign edges enter this decision.
Inspector voting memory exposes predictions, chosen ballot, leader set, sample size
and timestamps. Poll/count estimates are beliefs, not factual census values.

For mixed-policy comparisons: `compare ... --policies sincere memory_pivotal`.
The memory policy takes no voting-specific parameters: set memory length and poll
weight in `[majority_estimation]`. In the example, `poll_refresh_rounds=10`
publishes true completed tallies every ten rounds and linearly reduces poll
weight from 1.0 to 0.1 between publications. It is uncertified; a quiet window is not proof.
