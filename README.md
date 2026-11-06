# Eclipse: multi-agent election research

[Roadmap](docs/project-roadmap.md) · [Stage plans](docs/plans/README.md) ·
[Current state](docs/README.md#current-state)

Goal: one political simulator, seven mechanism studies, combined experiments,
reproducible report. Stage 00 is verified; Stage 01 is in progress. The current
engine supports sincere/local-plurality voters, ranked ballots, movement,
persistent/proximity graphs, delayed reports, scheduled edits and replay.
It is research software, not a validated election model.

Run from the project root with Python 3.11+:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/baseline.toml
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/network.toml --checkpoint /tmp/eclipse-checkpoint.json
PYTHONPATH=src python3 -m multi_agent_election.cli resume /tmp/eclipse-checkpoint.json --rounds 2
PYTHONPATH=src python3 -m multi_agent_election.cli batch examples/network.toml --seeds 1 2 3 --target A --plot-svg /tmp/eclipse-paired.svg
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/network.toml
PYTHONPATH=src python3 -m multi_agent_election.cli export /tmp/eclipse-checkpoint.json --csv /tmp/eclipse-metrics.csv --plot-svg /tmp/eclipse-plot.svg --gif /tmp/eclipse.gif
```

Checkpoint output must not already exist. Inputs are TOML; `k` is global and
each ballot has exactly `k` distinct parties. First-choice plurality is the
current count; private rankings remain separate. `local_plurality` selects the
most-reported first choice, breaking report ties by the voter's preference;
no messages means sincere voting. Truthful messages arrive one round later.
Groups choose voting, movement, `max_step`, and communication policies. Network
layers, private channels, positions and scheduled interventions are illustrated
in [network.toml](examples/network.toml). Replay checks checkpoint history by
recomputing it. Export uses recorded frames; PNG/GIF require `python3 -m pip install -r requirements-visualization.txt`.
The browser serves on localhost, default port 8000; stop with Ctrl-C. It supports
playback, inspection and past-frame edits; a ballot override lasts one round.

Trusted local plugins for voting, movement, graph and communication use
`python:module:function`; [simulator guide](docs/simulator-guide.md) gives their
contracts. Source hashes are checked for replay. Python plugins are **not sandboxed**.

Stage 01 verification is ongoing; epistemic integration and seven mechanisms
remain pending. Current progress: [Stage 01](docs/plans/stage-01-political-simulator.md#progress).
