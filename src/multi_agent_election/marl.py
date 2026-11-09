"""Multi-agent RL interface for learned movement (standard library only).

``MovementEnv`` follows the PettingZoo *parallel* API shape without depending
on PettingZoo:

    env = MovementEnv(scenario, reward_party="B")
    observations, infos = env.reset(seed=3)
    while env.agents:
        actions = {agent: (dx, dy) for agent in env.agents}   # from your policy
        observations, rewards, terminations, truncations, infos = env.step(actions)

Controlled agents are the people whose group uses ``movement = "external"``;
everyone else runs the scenario's own policies. An action is a displacement
``(dx, dy)``: it is scaled down to the agent's ``max_step`` if longer and
clipped to the unit square, then committed through ``Simulation.step``, which
re-validates it. Histories therefore checkpoint and replay like any other run.

Observation boundary (explicit design choice): an agent sees its own position
and current ballot, the public round result (first-choice shares), and the
``max_neighbours`` nearest people within ``observation_radius`` (default: its
own proximity radius) as relative offsets. Their last ballots are included
only if the agent may ``sense_public_ballots``; otherwise they are hidden (-1).
No private preferences, messages or hidden state are exposed.

Default reward: change in ``reward_party``'s first-choice share this round,
shared by all controlled agents (a team reward). Pass ``reward_fn(previous,
current, agent) -> float`` for anything else.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .engine import Simulation
from .model import ElectionError, Frame, Scenario, apply_overrides, make_scenario


@dataclass(frozen=True, slots=True)
class AgentObservation:
    round: int
    own_position: tuple[float, float]
    own_ballot: str
    shares: tuple[float, ...]                      # public first-choice shares, scenario party order
    neighbours: tuple[tuple[float, float, int], ...]  # (dx, dy, party index or -1 if hidden), nearest first


class MovementEnv:
    metadata = {"name": "eclipse_movement_v0"}

    def __init__(self, scenario: Scenario, reward_party: str | None = None, max_rounds: int | None = None,
                 observation_radius: float | None = None, max_neighbours: int = 8,
                 reward_fn: Callable[[Frame, Frame, str], float] | None = None):
        if not isinstance(scenario, Scenario):
            raise ElectionError("MovementEnv requires a validated Scenario")
        if reward_fn is None and reward_party not in scenario.parties:
            raise ElectionError("reward_party must name a scenario party (or pass reward_fn)")
        if not isinstance(max_neighbours, int) or isinstance(max_neighbours, bool) or max_neighbours < 0:
            raise ElectionError("max_neighbours must be a non-negative integer")
        self._scenario = scenario
        self.reward_party = reward_party
        self.reward_fn = reward_fn
        self.max_rounds = scenario.rounds if max_rounds is None else max_rounds
        self.observation_radius = observation_radius
        self.max_neighbours = max_neighbours
        groups = {g.id: g for g in scenario.groups}
        self._policy = {p.id: apply_overrides(groups[p.group], p.overrides) for p in scenario.people}
        self.possible_agents = [p.id for p in scenario.people if self._policy[p.id].movement == "external"]
        if not self.possible_agents:
            raise ElectionError('no person uses movement = "external"')
        self.parties = scenario.parties
        self.agents: list[str] = []
        self.simulation: Simulation | None = None

    # ------------------------------------------------------------------ API
    def reset(self, seed: int | None = None, options: Mapping[str, Any] | None = None):
        scenario = self._scenario
        if seed is not None:
            raw = scenario.as_dict()
            raw["seed"] = seed
            scenario = make_scenario(raw)
        self.simulation = Simulation(scenario)
        self.agents = list(self.possible_agents)
        frame = self.simulation.current
        return {a: self.observe(a) for a in self.agents}, {a: {"round": frame.round} for a in self.agents}

    def step(self, actions: Mapping[str, Sequence[float]]):
        if self.simulation is None or not self.agents:
            raise ElectionError("call reset() before step()")
        unknown = set(actions) - set(self.agents)
        if unknown:
            raise ElectionError(f"actions for unknown or finished agents: {sorted(unknown)}")
        before = self.simulation.current
        moves = {agent: self._target(agent, action) for agent, action in actions.items()}
        frame = self.simulation.step(external_moves=moves)
        rewards = {a: self._reward(before, frame, a) for a in self.agents}
        truncated = frame.round >= self.max_rounds
        observations = {a: self.observe(a) for a in self.agents}
        terminations = {a: False for a in self.agents}
        truncations = {a: truncated for a in self.agents}
        infos = {a: {"round": frame.round, "winner": frame.winner} for a in self.agents}
        if truncated:
            self.agents = []
        return observations, rewards, terminations, truncations, infos

    def observe(self, agent: str) -> AgentObservation:
        frame = self.simulation.current
        positions = dict(frame.positions)
        ballots = dict(frame.ballots)
        policy = self._policy[agent]
        radius = self.observation_radius
        if radius is None:
            radius = policy.proximity_radius if policy.proximity_radius is not None else (self._scenario.radius or 0.0)
        x, y = positions[agent]
        near = sorted((math.dist((x, y), pos), other) for other, pos in positions.items()
                      if other != agent and math.dist((x, y), pos) <= radius)
        index = {p: i for i, p in enumerate(self.parties)}
        neighbours = tuple((positions[o][0] - x, positions[o][1] - y,
                            index[ballots[o][0]] if policy.capabilities.sense_public_ballots else -1)
                           for _, o in near[: self.max_neighbours])
        counts = dict(frame.counts)
        total = sum(counts.values())
        return AgentObservation(frame.round, (x, y), ballots[agent][0],
                                tuple(counts[p] / total for p in self.parties), neighbours)

    def observation_vector(self, agent: str) -> list[float]:
        obs = self.observe(agent)
        index = self.parties.index(obs.own_ballot)
        vector = [obs.own_position[0], obs.own_position[1], *obs.shares, *[1.0 if i == index else 0.0 for i in range(len(self.parties))]]
        for i in range(self.max_neighbours):
            if i < len(obs.neighbours):
                dx, dy, party = obs.neighbours[i]
                vector += [1.0, dx, dy, *[1.0 if party == j else 0.0 for j in range(len(self.parties))]]
            else:
                vector += [0.0] * (3 + len(self.parties))
        return vector

    def checkpoint(self) -> dict:
        return self.simulation.checkpoint()

    # ------------------------------------------------------------------ helpers
    def _target(self, agent: str, action: Sequence[float]) -> tuple[float, float]:
        if (not isinstance(action, (list, tuple)) or len(action) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in action)):
            raise ElectionError(f"agent {agent!r}: action must be a finite (dx, dy) pair")
        dx, dy = float(action[0]), float(action[1])
        limit = self._policy[agent].max_step * (1 - 1e-9)
        length = math.hypot(dx, dy)
        if length > limit:
            dx, dy = (dx / length * limit, dy / length * limit) if length > 0 else (0.0, 0.0)
        x, y = dict(self.simulation.current.positions)[agent]
        return (min(1.0, max(0.0, x + dx)), min(1.0, max(0.0, y + dy)))

    def _reward(self, before: Frame, after: Frame, agent: str) -> float:
        if self.reward_fn is not None:
            return float(self.reward_fn(before, after, agent))
        b, a = dict(before.counts), dict(after.counts)
        return a[self.reward_party] / sum(a.values()) - b[self.reward_party] / sum(b.values())
