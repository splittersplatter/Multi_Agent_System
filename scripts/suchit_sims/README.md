# suchit-sims: scenario studies

Each script builds its scenarios as dictionaries and saves them as TOML under
`docs/suchit_sims/<study>/configs/`, so every showcase run can be replayed with
the normal CLI. The scripts then run the configs on the shared engine and write
figures, GIFs and a `summary.json`.

| Script | Study | Runs | Time (16-core Windows laptop) |
| --- | --- | --- | --- |
| `watchdog.py` | Aggregate-only watchdog against voter-alignment attacks; detector search; attacker best response | 420 | ~3.5 min |
| `foreign_intel.py` | Sleeper spy cells spreading targeted disinformation | 64 | ~1.5 min |
| `propaganda.py` | Long-term issue-position propaganda with natural drift | 25 | ~1 min |
| `echo_chambers.py` | Echo chambers and three strategic party campaigns (5×5×5 factorial) | 435 | ~8 min |
| `marl_demo.py` | Rolls out two simple policies through the new `MovementEnv` | 10 | ~20 s |

`common.py` holds the shared tools: a TOML writer, the runner, and drawing with
shape = agent profile and colour = current ballot, plus GIFs. `spatial.py` holds
the issue-space electorate used by the watchdog and propaganda studies.
`plugins/` holds the two policy plugins: `spy_comms.py` (communication phase) and
`echo_campaign.py` (movement and graph phases).

## Running

Run from this folder. Matplotlib and Pillow are only needed for the figures.

```bash
python -m venv ../../.venv && ../../.venv/Scripts/python -m pip install matplotlib pillow numpy
PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python watchdog.py
PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python foreign_intel.py
PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python propaganda.py
PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python echo_chambers.py
PYTHONIOENCODING=utf-8 ../../.venv/Scripts/python marl_demo.py
```

On Linux or macOS use `.venv/bin/python`. To replay a saved showcase config:

```bash
# Windows: separate PYTHONPATH entries with ';'   (Linux/macOS: ':')
PYTHONPATH="../../src;plugins" python -m multi_agent_election.cli run ../../docs/suchit_sims/foreign_intelligence/configs/F2_seed1.toml --summary
```

Verified: this reproduces F2 seed 1's final counts exactly (A 38, B 41, C 21).

The engine refuses to keep running if its own source changes during a run (a
provenance guard). Don't edit `src/` while a study is running.
