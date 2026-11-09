"""Spatial (issue-space) electorates shared by the watchdog and propaganda studies.

Voters hold a private 2-D issue ideal; three fixed nominees publish their own
ideals as platforms; every voter ranks nominees by issue distance (the engine's
spatial nomination model). Physical positions are separate and only drive the
proximity network that is drawn for context.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

CANDIDATES = {"ana": (0.25, 0.42), "ben": (0.74, 0.42), "cyd": (0.50, 0.84)}
# cluster centre, spread, size; nominees are added separately (3 people)
CLUSTERS = [((0.24, 0.40), 0.13, 39), ((0.74, 0.40), 0.13, 34), ((0.50, 0.80), 0.11, 24)]
TARGET = "cyd"


def _clip(v: float) -> float:
    return min(1.0, max(0.0, v))


def electorate(seed: int = 7, clusters=CLUSTERS) -> list[dict]:
    rng = random.Random(seed)
    people = [{"id": cid, "group": "candidates", "ideal": list(p), "position": [round(rng.random(), 4), round(rng.random(), 4)]}
              for cid, p in CANDIDATES.items()]
    n = 0
    for (cx, cy), sd, size in clusters:
        for _ in range(size):
            ideal = [round(_clip(rng.gauss(cx, sd)), 4), round(_clip(rng.gauss(cy, sd)), 4)]
            people.append({"id": f"v{n:02d}", "group": "voters", "ideal": ideal,
                           "position": [round(rng.random(), 4), round(rng.random(), 4)]})
            n += 1
    return people


def nearest(ideal: Sequence[float]) -> str:
    return min(sorted(CANDIDATES), key=lambda c: math.dist(ideal, CANDIDATES[c]))


def swing_order(people: list[dict], target: str = TARGET) -> list[str]:
    """Non-target voters ordered by how little the target trails their current favourite."""
    rows = []
    for p in people:
        if p["group"] != "voters":
            continue
        fav = nearest(p["ideal"])
        if fav == target:
            continue
        rows.append((math.dist(p["ideal"], CANDIDATES[target]) - math.dist(p["ideal"], CANDIDATES[fav]), p["id"]))
    return [pid for _, pid in sorted(rows)]


def core_order(people: list[dict], target: str = TARGET) -> list[str]:
    return list(reversed(swing_order(people, target)))


def base_config(people: list[dict], seed: int, rounds: int, drift: float, attack: dict, detector: float | None = None,
                radius: float = 0.11) -> dict:
    config = {
        "k": 1, "seed": seed, "rounds": rounds,
        "nomination": {"mode": "fixed", "m": 3, "eligible": sorted(CANDIDATES), "nominees": sorted(CANDIDATES)},
        "alignment": {"drift_max_step": drift, "attack": attack},
        "groups": {"candidates": {"voting": "sincere"}, "voters": {"voting": "sincere"}},
        "network": {"radius": radius},
        "people": people,
    }
    if detector is not None:
        config["detector"] = {"target": attack["target"], "threshold": detector}
    return config


def ideal_positions(frame) -> dict:
    return {p: tuple(v[:2]) for p, v in frame.alignment_ideals}
