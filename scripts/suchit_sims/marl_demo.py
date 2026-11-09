"""MARL smoke demo: 75 agents, 11 spies (15%) with ``movement = "external"``.

Spies vote for B and are visible to nearby conformist residents. A learner
would replace ``policy``; here a random policy and a hand-written "go where
non-B voters are" policy are rolled out through ``MovementEnv`` to show the API,
the reward signal and throughput. No learning library is needed.
"""

from __future__ import annotations

import math
import random
import statistics as stats
import time
import tomllib

from common import to_toml
from multi_agent_election.marl import MovementEnv
from multi_agent_election.model import make_scenario


def scenario(seed: int = 3) -> dict:
    rng = random.Random(seed)
    people = []
    for i in range(64):
        first = rng.choices(["A", "B", "C"], weights=[0.42, 0.33, 0.25])[0]
        rest = [p for p in "ABC" if p != first]
        people.append({"id": f"r{i:02d}", "group": "residents", "preference": [first, *rest],
                       "position": [round(rng.random(), 4), round(rng.random(), 4)]})
    for i in range(11):
        people.append({"id": f"spy{i:02d}", "group": "spies", "preference": ["B", "A", "C"],
                       "position": [round(rng.random(), 4), round(rng.random(), 4)]})
    return {"parties": ["A", "B", "C"], "k": 1, "seed": seed, "rounds": 40,
            "groups": {"residents": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.01,
                                     "proximity_radius": 0.12, "capabilities": {"sense_public_ballots": True}},
                       "spies": {"voting": "sincere", "movement": "external", "max_step": 0.04, "proximity_radius": 0.25,
                                 "capabilities": {"sense_public_ballots": True}}},
            "network": {"radius": 0.12}, "people": people}


def random_policy(obs, rng):
    angle = rng.uniform(0, 2 * math.pi)
    return (math.cos(angle), math.sin(angle))


def seek_policy(obs, rng):
    """Move toward the centroid of visible non-B neighbours (B is index 1)."""
    targets = [(dx, dy) for dx, dy, party in obs.neighbours if party not in (1, -1)]
    if not targets:
        return random_policy(obs, rng)
    return (sum(t[0] for t in targets) / len(targets), sum(t[1] for t in targets) / len(targets))


def rollout(policy, seed):
    env = MovementEnv(make_scenario(tomllib.loads(to_toml(scenario()))), reward_party="B", max_rounds=40)
    env.reset(seed=seed)
    rng = random.Random(seed)
    total, start = 0.0, time.perf_counter()
    while env.agents:
        actions = {a: policy(env.observe(a), rng) for a in env.agents}
        _, rewards, _, _, _ = env.step(actions)
        total += rewards[env.possible_agents[0]]
    elapsed = time.perf_counter() - start
    frame = env.simulation.current
    return total, dict(frame.counts)["B"], elapsed / 40


def main():
    for name, policy in (("random", random_policy), ("seek non-B", seek_policy)):
        results = [rollout(policy, s) for s in range(1, 6)]
        print(f"{name:11s} episode return (change in B share) {stats.mean(r[0] for r in results):+.3f}  "
              f"final B votes {stats.mean(r[1] for r in results):.1f}  "
              f"{1000 * stats.mean(r[2] for r in results):.1f} ms/round")


if __name__ == "__main__":
    main()
