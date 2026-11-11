"""The spoiler town used by every experiment in the talk.

Two separate spaces:

* opinion space [0, 1]^2: each voter has a fixed point and ranks the three
  candidates by distance to their platforms (opinions never change);
* the map, the engine's 1x1 square: each voter has a position, walks a small
  random step every round, and sees last round's votes of everyone within
  its hearing radius.

The town is built so the usual answers to "who should win?" disagree:
Left has the most first choices (about 118 of 300), Right is preferred to
Left by a majority, and Centre beats both head to head.

``build_town`` returns a raw scenario dictionary for the team's engine
(``multi_agent_election.model.make_scenario``); the engine itself is unchanged.
For a given seed, opinions, map positions, voter types and the tie order come
from named random streams that do not depend on the setting being tested, so
every experiment compares the same 30 towns.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

FULL = 1.4142                      # radius that covers the whole map: full information
PLATFORMS = {"Left": (0.25, 0.45), "Right": (0.72, 0.40), "Centre": (0.55, 0.62)}
LEFT_CAMP, RIGHT_CAMP, CAMP_SD, LEFT_SHARE = (0.25, 0.45), (0.64, 0.50), 0.10, 0.40

# name in the talk -> (engine voting policy, voting parameters, senses ballots)
TYPES = {
    "sincere": ("sincere", None, False),
    "frontrunner": ("top_k", {"top_k": 2}, True),
    "copycat": ("sensed_plurality", None, True),
    "pivot": ("pivotal", None, True),
}
DEFAULT_MIX = {"sincere": 0.4, "frontrunner": 0.3, "copycat": 0.2, "pivot": 0.1}


@dataclass(frozen=True)
class Town:
    voters: int = 300
    mix: tuple = tuple(DEFAULT_MIX.items())   # ((type, share), ...)
    radius: float = FULL                       # hearing radius for everyone
    walking: bool = True                       # random walk (step <= max_step) or standing still
    max_step: float = 0.03
    rounds: int = 40
    # Experiment 4: an organised minority that always votes `minority_party`;
    # each member gets `followers` random listeners anywhere in town (propaganda reach).
    minority: int = 0
    minority_party: str | None = None
    followers: int = 0
    # Multi-agent pilots (presentation/mas_pilots); the defaults reproduce the talk's towns exactly.
    homophily: float = 0.0       # 0: map spot unrelated to opinion; 1: map spot = opinion point (echo chambers)
    follower_pool: str = "all"   # who may be a follower: all, copycat, frontrunner, frontrunner_right,
                                 # frontrunner_left, sincere, pivot


def _clip(v: float) -> float:
    return min(1.0, max(0.0, v))


def ranking(point: tuple[float, float]) -> list[str]:
    return sorted(PLATFORMS, key=lambda p: (math.dist(point, PLATFORMS[p]), p))


def opinions(town: Town, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(f"opinions-{town.voters}-{seed}")
    n_left = round(LEFT_SHARE * town.voters)
    pts = []
    for i in range(town.voters):
        cx, cy = LEFT_CAMP if i < n_left else RIGHT_CAMP
        pts.append((_clip(rng.gauss(cx, CAMP_SD)), _clip(rng.gauss(cy, CAMP_SD))))
    return pts


def preferences(town: Town, seed: int) -> list[list[str]]:
    return [ranking(p) for p in opinions(town, seed)]


def positions(town: Town, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(f"map-{town.voters}-{seed}")
    spots = [(rng.random(), rng.random()) for _ in range(town.voters)]
    if town.homophily:   # pull each map spot towards the voter's opinion point
        h = town.homophily
        spots = [(h * o[0] + (1 - h) * s[0], h * o[1] + (1 - h) * s[1]) for o, s in zip(opinions(town, seed), spots)]
    return spots


def tie_order(seed: int) -> list[str]:
    order = sorted(PLATFORMS)
    random.Random(f"tie-order-{seed}").shuffle(order)   # the engine breaks count ties by this order
    return order


def minority_members(town: Town, seed: int) -> list[int]:
    """`town.minority` voters chosen at random among those whose favourite is the minority's party."""
    if not town.minority:
        return []
    prefs = preferences(town, seed)
    fans = [i for i, p in enumerate(prefs) if p[0] == town.minority_party]
    if len(fans) < town.minority:
        raise ValueError("not enough supporters to form the minority")
    return sorted(random.Random(f"minority-{town.minority_party}-{seed}").sample(fans, town.minority))


def types(town: Town, seed: int) -> list[str]:
    """Exact shares, randomly assigned; minority members are overridden later."""
    counts, assigned = [], 0
    for i, (_, share) in enumerate(town.mix):
        n = town.voters - assigned if i == len(town.mix) - 1 else round(share * town.voters)
        counts.append(n); assigned += n
    labels = [t for (t, _), n in zip(town.mix, counts) for _ in range(n)]
    random.Random(f"types-{town.voters}-{seed}").shuffle(labels)
    return labels


def followers(town: Town, seed: int, members: list[int]) -> list[tuple[str, str]]:
    """Directed persistent links member -> listener: the listener sees the member's vote every round."""
    if not members or not town.followers:
        return []
    rng = random.Random(f"followers-{seed}")
    others = [i for i in range(town.voters) if i not in set(members)]
    if town.follower_pool != "all":   # targeted propaganda: followers drawn from one kind of voter only
        kinds, favourite = types(town, seed), [p[0] for p in preferences(town, seed)]
        wanted = {"copycat": lambda i: kinds[i] == "copycat",
                  "frontrunner": lambda i: kinds[i] == "frontrunner",
                  "frontrunner_right": lambda i: kinds[i] == "frontrunner" and favourite[i] == "Right",
                  "frontrunner_left": lambda i: kinds[i] == "frontrunner" and favourite[i] == "Left",
                  "sincere": lambda i: kinds[i] == "sincere",
                  "pivot": lambda i: kinds[i] == "pivot"}[town.follower_pool]
        others = [i for i in others if wanted(i)]
    edges = []
    for m in members:
        for listener in rng.sample(others, town.followers):
            edges.append((f"{m:04d}", f"{listener:04d}"))
    return edges


def build_town(town: Town, seed: int) -> dict:
    prefs = preferences(town, seed)
    pos = positions(town, seed)
    labels = types(town, seed)
    members = minority_members(town, seed)
    for m in members:
        labels[m] = "minority"
    groups = {}
    for name in sorted(set(labels)):
        policy, params, senses = TYPES["sincere"] if name == "minority" else TYPES[name]
        group = {"voting": policy, "movement": "random_walk" if town.walking else "stationary",
                 "capabilities": {"sense_public_ballots": senses}}
        if town.walking:
            group["max_step"] = town.max_step
        if params:
            group["parameters"] = {"voting": dict(params)}
        groups[name] = group
    people = [{"id": f"{i:04d}", "group": labels[i], "preference": prefs[i], "position": list(pos[i])}
              for i in range(town.voters)]
    network = {"radius": town.radius}
    edges = followers(town, seed, members)
    if edges:
        network["persistent_edges"] = [list(e) for e in edges]
    return {"parties": tie_order(seed), "k": 1, "seed": seed, "rounds": town.rounds,
            "groups": groups, "network": network, "people": people}


def all_mixes(step: float = 0.1, minimum: float = 0.1):
    """Every mix of the four types in `step` increments with each type at least `minimum`."""
    units, low = round(1 / step), round(minimum / step)
    out = []
    for s in range(low, units + 1):
        for f in range(low, units + 1 - s):
            for c in range(low, units + 1 - s - f):
                p = units - s - f - c
                if p >= low:
                    out.append((("sincere", s / units), ("frontrunner", f / units),
                                ("copycat", c / units), ("pivot", p / units)))
    return out
