"""Directed proximity graphs and keyed bounded motion."""

import hashlib
import math
import random
from statistics import NormalDist
from collections import defaultdict
from typing import Mapping

from .model import ElectionError


def proximity_edges(positions: Mapping[str, tuple[float, float]], radius: float | None,
                    radii: Mapping[str, float | None] | None = None) -> tuple[tuple[str, str], ...]:
    """Arcs point sender -> receiver; each receiver's radius determines reach."""
    effective = {person: radii.get(person, radius) if radii is not None else radius for person in positions}
    active = [value for value in effective.values() if value is not None]
    if not active:
        return ()
    if max(active) == 0:
        # Zero reach observes only coincident senders. Partition by exact position
        # instead of comparing every pair in the unit square.
        coincident = defaultdict(list)
        for person in sorted(positions):
            coincident[positions[person]].append(person)
        return tuple(sorted((sender, receiver) for members in coincident.values()
                            for receiver in members if effective[receiver] is not None
                            for sender in members if sender != receiver))
    grid: dict[tuple[int, int], list[str]] = defaultdict(list)
    # radius zero still connects coincident points, with a fixed cell size.
    largest = max(active)
    # Tiny positive floats can overflow x/cell; a larger cell preserves correctness.
    cell = max(largest, 1e-9) if largest > 0 else 1.0
    edges = []
    for person in sorted(positions):
        x, y = positions[person]
        gx, gy = math.floor(x / cell), math.floor(y / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in grid[(gx + dx, gy + dy)]:
                    ox, oy = positions[other]
                    distance = math.hypot(x - ox, y - oy)
                    if effective[person] is not None and distance <= effective[person]:
                        edges.append((other, person))
                    if effective[other] is not None and distance <= effective[other]:
                        edges.append((person, other))
        grid[(gx, gy)].append(person)
    return tuple(sorted(edges))


def _reflect(value: float) -> float:
    value %= 2.0
    return value if value <= 1 else 2 - value


def validate_walk_parameters(parameters, max_step):
    if not isinstance(parameters, dict) or set(parameters) - {"distribution", "mean_step", "std_step"}:
        raise ElectionError("random-walk movement parameters require distribution, mean_step and std_step only")
    distribution = parameters.get("distribution", "uniform")
    if distribution not in ("uniform", "normal"):
        raise ElectionError("random-walk distribution must be uniform or normal")
    if distribution == "uniform":
        if set(parameters) - {"distribution"}:
            raise ElectionError("mean_step/std_step require normal movement")
        return distribution, 0.0, 0.0
    mean = parameters.get("mean_step", max_step)
    if type(mean) not in (int, float) or not math.isfinite(mean) or not 0 <= mean <= max_step:
        raise ElectionError("normal mean_step must be finite within [0,max_step]")
    spread = parameters.get("std_step", mean * .25)
    if type(spread) not in (int, float) or not math.isfinite(spread) or not 0 <= spread <= 1:
        raise ElectionError("normal std_step must be finite within [0,1]")
    if spread:
        normal = NormalDist(mean, spread)
        if normal.cdf(max_step) <= normal.cdf(0):
            raise ElectionError("normal movement has no representable probability inside [0,max_step]")
    return distribution, float(mean), float(spread)


def random_walk(position: tuple[float, float], max_step: float, seed: int, person: str, round_number: int,
                parameters=None) -> tuple[float, float]:
    """Keyed uniform direction; optional truncated-normal length and reflective bounds."""
    distribution, mean, spread = validate_walk_parameters({} if parameters is None else parameters, max_step)
    payload = f"{seed}\0movement\0{len(person)}:{person}\0{round_number}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))
    angle = rng.random() * 2 * math.pi
    if distribution == "uniform":
        length = rng.random() * max_step
    elif spread == 0:
        length = mean
    else:
        normal = NormalDist(mean, spread)
        lower, upper = normal.cdf(0), normal.cdf(max_step)
        probability = lower + (upper - lower) * rng.random()
        probability = min(math.nextafter(1.0, 0.0), max(math.nextafter(0.0, 1.0), probability))
        length = min(max_step, max(0.0, normal.inv_cdf(probability)))
    return (_reflect(position[0] + length * math.cos(angle)), _reflect(position[1] + length * math.sin(angle)))
