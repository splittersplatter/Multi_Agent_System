# Project report and presentation

| File | Contents |
| --- | --- |
| [Eclipse_Project_Report.pdf](Eclipse_Project_Report.pdf) | 6-page report: goals, architecture, configuration definitions, studies A–J, convergence and optimal solutions, engineering quality, limitations |
| [Eclipse_Project_Presentation.pptx](Eclipse_Project_Presentation.pptx) | 24-slide editable deck. Most charts are native PowerPoint charts. |
| [Eclipse_Project_Presentation.pdf](Eclipse_Project_Presentation.pdf) | PDF rendering of the deck |
| [figures/](figures/) | Every plot and screenshot used in the report and deck |

## Provenance

All numbers were re-generated on 9 November 2026 from commit `86de48b`, with
Python 3.13 on a 4-core Linux container. Nothing was copied from earlier
`outputs/` artifacts, which are git-ignored and were not present.

- Full test suite: 343 tests, all passing.
- Every study run completed with zero failures and zero unpaired runs.
- The majority-estimation pilot reproduces the numbers in
  [majority-estimation-report.md](../majority-estimation-report.md) exactly.
- The 500-voter heuristic switch counts match
  [heuristic-verification-report.md](../heuristic-verification-report.md).

Performance figures (10k-voter CLI, HTTP p95 latency) are quoted from the
recorded single-run benchmarks in [stage-01-benchmarks.md](../stage-01-benchmarks.md)
and [code-audit-and-refinement-report.md](../code-audit-and-refinement-report.md).
They were not re-measured on this machine.

The mechanism studies (B–H) use the repository's example scenarios, which have
3–4 voters. They show that each control and accounting path behaves as designed.
They are not population-level effect estimates.

## Reproduce the data

Run from the repository root. Each output path must not already exist.

```bash
export PYTHONPATH=src:examples
C="python3 -m multi_agent_election.cli"
S="11 22 33 44 55"
python3 -m unittest discover -s tests
python3 scripts/verify_convergence_foundations.py
$C compare examples/heuristics.toml --seeds 101 202 303 --rounds 100 --window 20 --policies sincere local_plurality sensed_plurality pivotal expected_utility top_k max_m tie_u tie_h tie_r poisson local_dominance maximin --output heur-small.json
$C compare examples/heuristics.toml --seeds 101 202 303 --rounds 100 --window 20 --parameters '{"information_source":"poll"}' --policies pivotal expected_utility top_k max_m tie_u tie_h tie_r poisson local_dominance maximin --output heur-poll.json
$C compare examples/population-scenario.toml --seeds 101 202 303 --rounds 20 --window 10 --policies sincere local_plurality sensed_plurality pivotal expected_utility top_k max_m tie_u tie_h tie_r poisson local_dominance maximin --output heur-500.json
$C compare-networks examples/group-radius.toml --seeds $S --output networks.json
$C coalition-ablations examples/coalition-combined.toml --seeds $S --output coalition.json
$C compare-campaign examples/campaign-controller.toml --seeds $S --output campaign.json
$C campaign-exhaustive examples/campaign-exhaustive.toml --max-combinations 10000 --output exhaustive.json
$C compare-signals examples/epistemic-public-signal.toml --seeds $S --groups signal_voter --signal-distortion-bound 1 --output signals.json
$C compare-nominations examples/nomination.toml --seeds $S --output nominations.json
$C compare-alignment examples/alignment-attack.toml --seeds $S --output alignment.json
$C evaluate-detector examples/detector.toml --calibration-seeds 100 101 102 103 104 --evaluation-seeds 200 201 202 203 204 --false-alarm-rate 0.1 --output detector.json
$C compare-leaders examples/leader-adaptation.toml --seeds $S --output leaders.json
$C combined-ablation examples/all-enabled.toml --seeds $S --target alice --output combined.json
python3 scripts/benchmark_combined.py generate --agents 200 --rounds 20 --seed 2026 --output combined200.toml
$C combined-ablation combined200.toml --seeds 11 22 33 --target alice --output combined200.json
$C estimate-majority --pilot --sensitivity --output-dir majority-pilot
$C knowledge examples/knowledge-two-voters.json --solve-conditional
for e in certified-direct certified-local-dominance certified-conformity certified-intervention; do
  $C run examples/$e.toml --until-equilibrium --checkpoint $e.json
done
```

The figures were drawn with matplotlib from these JSON outputs. Browser
screenshots come from `cli visual` on `all-enabled.toml`, `integrated.toml` and
`heuristics.toml`, captured with Playwright after stepping a few rounds.
