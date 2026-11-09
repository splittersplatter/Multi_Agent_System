# MARL interface for learned movement

Added on branch `suchit-sims`, 9 November 2026. This is a deliberately small
change that lets an outside reinforcement-learning loop control how chosen
agents move. Everything else in the simulator is unchanged.

## What changed

| File | Change |
| --- | --- |
| `src/multi_agent_election/model.py` | New movement mode `movement = "external"` (alongside `stationary`, `random_walk`, `python:...`). |
| `src/multi_agent_election/engine.py` | `Simulation.step(external_moves=None)`. The old body moved unchanged to `_step()`. |
| `src/multi_agent_election/marl.py` | New `MovementEnv`: a PettingZoo-style parallel environment, standard library only. |
| `src/multi_agent_election/provenance.py` | `marl.py` added to the pipeline fingerprint. |
| `tests/test_marl.py` | 11 tests (below). |

`step()` with no argument behaves exactly as before; one test checks the frames are identical.

## How external moves work

`sim.step(external_moves={"spy01": (0.42, 0.61), ...})` gives new positions for
people whose movement is `"external"`. Anyone without a move stays where they are.

Each move is checked before anything changes:
- the person exists and their movement mode is `"external"` (after per-person overrides);
- they have the `move` capability;
- the position is two finite numbers in `[0, 1]`;
- the distance moved is at most their `max_step`;
- no other position edit is already queued for them at that boundary.

Valid moves are stored as position interventions for the next round. Checkpoints
therefore save them, and `Simulation.from_checkpoint` replays them exactly; a
tampered position is rejected. If anything fails, the step is rolled back, so the
history and the queued interventions stay as they were.

In saved frames these moves show up as `interactive` position interventions.
This is the label every replayed manual intervention gets, and it keeps live
and replayed frames identical without changing the checkpoint format.

## Environment API

```python
import tomllib
from pathlib import Path
from multi_agent_election.model import make_scenario
from multi_agent_election.marl import MovementEnv

scenario = make_scenario(tomllib.loads(Path("my_spies.toml").read_text()))   # spies use movement = "external"
env = MovementEnv(scenario, reward_party="B", max_rounds=50, max_neighbours=8)
observations, infos = env.reset(seed=3)
while env.agents:
    actions = {a: policy(env.observation_vector(a)) for a in env.agents}   # (dx, dy) per agent
    observations, rewards, terminations, truncations, infos = env.step(actions)
checkpoint = env.checkpoint()   # replayable like any other run
```

- **Agents:** everyone with `movement = "external"` (`env.possible_agents`).
- **Action:** a displacement `(dx, dy)`. If it is longer than the agent's `max_step` it is scaled down to `max_step`, and the result is clipped to the unit square. The engine then checks it again.
- **Observation:** `env.observe(agent)` returns an `AgentObservation` with:
  - the round, the agent's own position and own current ballot;
  - the public first-choice shares;
  - the `max_neighbours` nearest people within `observation_radius` (default: the agent's proximity radius), as relative offsets `(dx, dy)`, nearest first.

  Neighbours' last ballots are included only if the agent has `sense_public_ballots`; otherwise they show as `-1`. Private preferences, messages and hidden state are never exposed. `env.observation_vector(agent)` flattens this into a fixed-length float list for neural networks.
- **Reward:** the change in `reward_party`'s share each round, shared by all controlled agents (a team reward). Pass `reward_fn(previous_frame, frame, agent)` for anything else, such as win bonuses or per-agent shaping.
- **Episode end:** every agent is truncated at `max_rounds`; there is no early termination.
- **Seeding:** `reset(seed=s)` reruns the scenario with seed `s`. The same seed and the same actions give byte-identical frames (tested).

## Tests (`tests/test_marl.py`, 11, all passing)

- A valid move commits; agents without a move stay put; built-in random walkers still move.
- Passing no moves gives exactly the same result as a plain `step()`.
- Eight kinds of invalid move each fail with the state left unchanged: over `max_step`, mover not `external`, `move` capability denied, unknown person, NaN, outside the square, boolean coordinate, wrong length. The simulation can still step afterwards.
- A move conflicting with an already-queued position edit is rejected.
- Checkpoint replay matches exactly; a tampered position fails replay.
- Environment: API shapes and truncation, scaling and clipping, determinism under a fixed seed, the sensing-permission observation boundary (checked against a hand-computed nearest-neighbour list), the reward formula, and errors when no agent is external or the reward party is invalid.

## Population rule (after merging `main`)

`main` requires at least 100 people per simulation. `MovementEnv` creates a normal `Simulation`,
so training scenarios need 100 or more people (`marl_demo.py` uses 85 residents + 15 spies).
Small fixtures are allowed only inside the unit-test verification scope (`VerificationTestCase`),
which `tests/test_marl.py` uses.

## Limits

- Only **movement** is externally controlled. Voting, communication and graph actions still come from the scenario's own policies or plugins. They could be added the same way: validate, then record as an intervention.
- The browser UI and CLI have no way to supply external moves, so external movers stay put there.
- Each controlled agent adds one intervention per round to the history. A very long training episode with a saved checkpoint grows accordingly; training loops normally don't save checkpoints.
- Speed: a 75-agent round takes about 17 ms (measured), so expect roughly 60 rounds/s per core. Run environments in parallel processes for training.
