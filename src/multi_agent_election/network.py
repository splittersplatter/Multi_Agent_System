"""Directed proximity graphs and keyed bounded motion."""

import hashlib
import math
import random
from collections import defaultdict
from typing import Mapping


def proximity_edges(positions: Mapping[str, tuple[float, float]], radius: float | None) -> tuple[tuple[str, str], ...]:
    if radius is None:
        return ()
    grid: dict[tuple[int, int], list[str]] = defaultdict(list)
    # radius zero still connects coincident points, with a fixed cell size.
    cell = radius if radius > 0 else 1.0
    edges = []
    for person in sorted(positions):
        x, y = positions[person]
        gx, gy = math.floor(x / cell), math.floor(y / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in grid[(gx + dx, gy + dy)]:
                    ox, oy = positions[other]
                    if math.hypot(x - ox, y - oy) <= radius:
                        edges.extend(((person, other), (other, person)))
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
