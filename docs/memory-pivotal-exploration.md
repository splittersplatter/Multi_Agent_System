# Memory-pivotal: exploratory implementation and pilot

Status: implemented, opt-in, **uncertified**. Normal simulations N>=100.
The example now publishes the completed tally every10 rounds and uses a linearly
decreasing poll weight; the five-seed results below are historical fixed-poll
results from the earlier source and are not results for the updated scenario.
The estimator is shared with the browser, CLI, replay and exports; its original
passive use and all default policies are unchanged.

## Run

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000 --voting memory_pivotal
PYTHONPATH=src python3 -m multi_agent_election.cli compare examples/recent-majority.toml --seeds 101 102 103 104 105 --rounds 100 --window 10 --policies sincere memory_pivotal --output outputs/memory-pivotal-new.json
```

Open `http://127.0.0.1:8000`. Output filename must be new. Inspector voting
memory shows predicted outcomes, baseline winner, estimated leaders, sample size,
observation timing and strict-improvement decision. `k=1` and an enabled explicit
`[majority_estimation]` poll are required; no extra voting parameters are accepted.

## Decision contract

At round r, after movement, incoming proximity neighbors reveal completed round
r−1 ballots. Update the existing unique-neighbor cache, expire entries outside
its rolling window, then calculate blended poll/cache shares p. The latest true
tally is published after every tenth completed round; its decision weight resets
to1 in the next round and decreases by0.1 each round until the next publication.
The initial poll is the configured sample, not the full electorate tally.
For each candidate
c, predict the plurality winner from `(N−1)p + e_c`, with fixed party-order ties.
Compare all hypothetical winners against keeping the existing vote under the
same estimate. Switch to the most-preferred achievable winner only if strictly
better; otherwise retain. Arithmetic uses exact integer ratios; all decisions use
the same completed ballots and commit simultaneously. Actual current counts,
other private rankings, messages and nonproximity edges do not enter the rule.

The poll is not a continuously truthful census; estimates are heuristic.
The rule tests predicted winners, not expected utility over uncertain elections.
Previous policy/cache separation, replay/rewind and mixed-group support remain.
[Derivation, original-domain counterexample and proof limits](memory-voting-convergence.md).

## Exploratory 200-voter run

Same electorate and initial poll in every run; seeds101–105 vary movement, paired
between sincere and memory-pivotal, 100 rounds, K10, poll weight .5. Five
independent motion seeds only; not held-out evaluation or evidence of superiority.
`outputs/memory-pivotal-current-source-2026-11-09.json` contains scenario,
metrics, final decision traces, source manifest and retained failure statuses.

| Seed | Memory-pivotal switches | Final A/B/C counts | Final 10 rounds no ballot changes? |
| --- | ---: | --- | --- |
| 101 | 19 | 95/70/35 | No |
| 102 | 18 | 98/69/33 | Yes |
| 103 | 18 | 98/69/33 | No |
| 104 | 11 | 91/70/39 | No |
| 105 | 16 | 92/69/39 | No |

Sincere control: no switches; final80/70/50 for each seed. Winner A in every
round of both arms;10 completed runs, zero failures. A quiet last-10 window is
an observation, not a convergence certificate. Winner stability does not imply
ballot stability. Repeated starts from a single electorate constrain interpretation.

## Verification and remaining work

- Independent rational-oracle decision tests include weight endpoints, empty and
  populated caches, exact ties, strict improvement and retained ballots.
- Real engine reproduces the existing four-voter two-cycle in explicit verification
  scope; source timing, current cache, replay, rewind/edit, invalid configurations,
  atomic rejection and hidden-ranking independence are checked.
- Real HTTP startup selection/steps, CLI frames, CSV and checkpoint replay are
  checked alongside all existing voting policies; separate production-scope
  200-person HTTP test verifies startup selection, decision trace and replay.
- Latest full suite373 pass; stdlib369 pass/4 optional-image skips. Logs:
  `outputs/periodic-poll-verified-tests.log`, `outputs/periodic-poll-verified-stdlib.log`.
  JS playback harness and 200-person periodic HTTP/replay checks pass.
- No theorem covers the full N>=100 moving composition. Convergence is optional
  for labelled exploratory finite-horizon studies and required for claims of
  certified convergence. Further comparisons need varied electorates, independent
  held-out seeds, matched information, failures/cutoffs and uncertainty.
