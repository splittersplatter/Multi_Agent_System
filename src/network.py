"""Directed proximity graphs and keyed bounded motion."""

import hashlib
import math
import random
from collections import defaultdict
from typing import Mapping


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


def random_walk(position: tuple[float, float], max_step: float, seed: int, person: str, round_number: int) -> tuple[float, float]:
    payload = f"{seed}\0movement\0{len(person)}:{person}\0{round_number}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))
    angle = rng.random() * 2 * math.pi
    length = rng.random() * max_step
    return (_reflect(position[0] + length * math.cos(angle)), _reflect(position[1] + length * math.sin(angle)))
