# Eclipse: multi-agent election research

One engine for CLI, browser, replay and seven election-influence mechanisms.
Research software—not a validated model of real elections.

## Run

Python >=3.11; core/browser need no external packages or API keys. From repository root:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000
```

Open [localhost:8000](http://127.0.0.1:8000). Ctrl-C stops; rerun to restart.
Demo: **200 distinct moving voters**, sincere ballots, passive recent-encounter
majority estimates. The estimator does not change votes. The initial public poll
is a sample; completed global tallies are published every10 rounds. Poll weight
decays from100% to10%, then resets on the next publication.
Demo motion: truncated-normal length, mean0.025/std0.00625, hard cap0.05;
uniform direction and reflective boundaries. Quiet ballots do not prove stability
under future contacts; [conditions and research](docs/dynamic-network-stability.md).

**Every normal simulation requires >=100 voters**, including API, CLI, browser,
pilots, benchmarks and checkpoint resume. Small examples are explicit verification
fixtures, not outcome workloads. Never silently pad or duplicate them.

```bash
mkdir -p outputs
# Efficient run; metrics only.
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/recent-majority.toml --summary
# Full checkpoint; choose new output names on subsequent runs.
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/recent-majority.toml --checkpoint outputs/demo.json
PYTHONPATH=src python3 -m multi_agent_election.cli resume outputs/demo.json --rounds 10 --output outputs/demo-resumed.json
PYTHONPATH=src python3 -m multi_agent_election.cli export outputs/demo.json --csv outputs/demo.csv --plot-svg outputs/demo.svg
```

Outputs are exclusive; parents must exist. PNG/GIF additionally require
`python3 -m pip install -r requirements-visualization.txt`. Plugins are trusted
local Python, **not sandboxed**. Replay checks source identity and recomputes history.

## Verify

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -S -m unittest discover -s tests -v
node tests/playback_harness.js
```

Latest recorded verification: **414 tests pass**; stdlib-only410 pass/4 optional
image skips. [Evidence and limits](docs/implementation-status-report.md#verification).

## Documentation

- [Current state and documentation index](docs/README.md)
- [Simulator/configuration reference](docs/simulator-guide.md)
- [Voting policies and source departures](docs/voting-heuristics.md)
- [Majority estimator](docs/recent-encounter-majority.md)
- [Roadmap](docs/project-roadmap.md) · [Stage plans](docs/plans/README.md)
- [Literature survey](docs/election-manipulation-literature-survey.md) · [Method audit](docs/literature-heuristics-and-metrics.md)

Run the exploratory memory-based voter with the200-person estimator scenario:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000 --voting memory_pivotal
```

`memory_pivotal` uses the moving recent-contact estimate; it is not convergence
certified. Convergence proofs remain required for certified claims, while labelled
finite-horizon exploratory studies may investigate nonconvergent dynamics.
The [finite-grid occupation model](docs/stochastic-stability-verification.md)
is opt-in; continuous defaults remain unchanged. Run its200-voter browser preset:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/stochastic-grid.toml --port 8000
```

For fixed-horizon frequency/phase summaries and streamed raw rows:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli frequencies examples/stochastic-grid.toml \
  --rounds 10000 --burn-in 1000 --batch-size 100 --seed 2000 \
  --rows outputs/grid-2000.csv --output outputs/grid-2000.json
```

Add `--control sincere-grid` or `--control continuous-normal` with different output
names. Only the grid arms share motion trajectories. The theorem assumes ideal IID
motion; seeded replay and finite plots do not prove stationarity, absorption or
a unique limit. Fixed-domain grid episodes disallow edits/policy changes; playback
and exports remain available. Full evaluation campaign has not been run.
