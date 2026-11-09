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
# Full checkpoint; explicit paths are optional.
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

Current verification and historical checks:
[evidence and limits](docs/implementation-status-report.md#verification).

## Documentation

- [Current state and documentation index](docs/README.md)
- [Simulator/configuration reference](docs/simulator-guide.md)
- [Voting policies and source departures](docs/voting-heuristics.md)
- [Majority estimator](docs/recent-encounter-majority.md)
- [Roadmap](docs/project-roadmap.md) · [Stage plans](docs/plans/README.md)
- [Literature survey](docs/election-manipulation-literature-survey.md) · [Method audit](docs/literature-heuristics-and-metrics.md)

CLI simulations automatically save timestamped artifacts in `outputs/`: full
runs/resumes save checkpoints, summary/sample runs save JSONL, comparisons save
JSON, and estimator pilots save a directory. Browser sessions save a checkpoint
when stopped with Ctrl+C. Explicit output paths remain supported; existing files
are never overwritten. `--save-plots` also saves SVG vote-share plots (batch:
paired target-share change; comparisons: one SVG per available trajectory).
Add `--save-states` to stream every completed round (including round zero) to a
timestamped `*-states.jsonl` file. It records nodes, positions, true rankings,
submitted ballots, edges and inspector data. Each episode/control has its own
file. Open the newest recording with:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli view --latest --port 8000
```

The browser supports play/pause, timeline scrubbing and agent inspection. Saved
playback is read-only; use checkpoints for verified resume. Recording streams to
disk; playback currently loads the saved timeline into memory.

Run the exploratory memory-based voter with the200-person estimator scenario:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000 --voting memory_pivotal
```

`memory_pivotal` uses the moving recent-contact estimate; it is not convergence
certified. Convergence proofs remain required for certified claims, while labelled
finite-horizon exploratory studies may investigate nonconvergent dynamics.
Grid movement is retired. Gaussian random walk is the default moving kernel;
explicit stationary policies remain stationary. Run the200-voter strategic preset:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/gaussian-memory.toml --port 8000 --save-plots --save-states
```

For fixed-horizon frequency/phase summaries and streamed raw rows:

```bash
PYTHONPATH=src python3 -m multi_agent_election.cli frequencies examples/gaussian-memory.toml \
  --rounds 10000 --burn-in 1000 --batch-size 100 --seed 2000 --save-plots --save-states
```

The command creates `outputs/` if needed and prints the generated CSV and JSON
paths, named with the UTC start time. Pass `--rows` and `--output` for custom paths;
existing files are never overwritten. Add `--control sincere` for a sincere-voter
control with identical Gaussian motion. View recorded rounds with `view --latest`.
Frequency summaries are exploratory: no occupation-frequency, absorption or
mixing-time guarantee. Gaussian steps do not establish faster mixing. The retired
[grid proof/checker](docs/stochastic-stability-verification.md) remains historical
evidence only; grid scenarios/checkpoints fail explicitly rather than being
silently converted. Full evaluation campaign has not been run.
