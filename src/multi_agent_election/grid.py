"""Opt-in exact 41x41 grid. Ideal IID theorem and seeded replay are distinct."""

from collections import defaultdict
import hashlib
import json
import random

from .model import Capabilities, ElectionError, apply_overrides

CASE = "finite_grid_occupation_v1"
MOVES = ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0))


def physical(coordinates):
    if (not isinstance(coordinates, (tuple, list)) or len(coordinates) != 2
            or any(type(x) is not int or not 0 <= x <= 40 for x in coordinates)):
        raise ElectionError("grid_position requires two integers in [0,40]")
    return tuple(x / 40 for x in coordinates)


def integer_position(position):
    if (not isinstance(position, (tuple, list)) or len(position) != 2
            or any(type(x) not in (int, float) or not 0 <= x <= 1 for x in position)):
        raise ElectionError("invalid grid position")
    coordinates = tuple(round(x * 40) for x in position)
    if physical(coordinates) != tuple(position):
        raise ElectionError("grid position is off lattice; snapping is forbidden")
    return coordinates


def proposal(seed, person, round_number):
    payload = f"{seed}\0grid-motion-v1\0{len(person)}:{person}\0{round_number}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))
    return rng.randrange(5)


def walk(position, seed, person, round_number):
    x, y = integer_position(position)
    dx, dy = MOVES[proposal(seed, person, round_number)]
    target = (x + dx, y + dy)
    return physical(target if all(0 <= a <= 40 for a in target) else (x, y))


def proximity(positions):
    """Inclusive radius .12: 25*d²<=576. Integer cells of width5 suffice."""
    cells = defaultdict(list)
    edges = []
    for person in sorted(positions):
        x, y = integer_position(positions[person])
        gx, gy = x // 5, y // 5
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other, ox, oy in cells[gx + dx, gy + dy]:
                    if 25 * ((x - ox)**2 + (y - oy)**2) <= 576:
                        edges.extend(((other, person), (person, other)))
        cells[gx, gy].append((person, x, y))
    return tuple(sorted(edges))


def enabled(scenario):
    groups = {g.id: g for g in scenario.groups}
    return (any(g.movement == "grid_walk" for g in scenario.groups)
            or any(apply_overrides(groups[p.group], p.overrides).movement == "grid_walk" for p in scenario.people)
            or any(a.overrides is not None and json.loads(a.overrides).get("movement") == "grid_walk"
                   for a in scenario.interventions))


def validate_domain(scenario):
    """Strict declaration guard, also called after dataclass revalidation."""
    if scenario.stochastic_case is not None and scenario.stochastic_case != CASE:
        raise ElectionError("unsupported stochastic stability case")
    if not enabled(scenario):
        if scenario.stochastic_case is not None:
            raise ElectionError("finite-grid occupation requires grid_walk")
        return
    groups = {g.id: g for g in scenario.groups}
    effective = [apply_overrides(groups[p.group], p.overrides) for p in scenario.people]
    if (scenario.radius != .12 or scenario.proximity_mode != "dynamic"
            or any(g.movement != "grid_walk" or g.proximity_radius not in (None, .12) for g in effective)):
        raise ElectionError("grid_walk requires homogeneous grid movement, dynamic proximity and common radius .12")
    for p in scenario.people:
        if p.grid_position is None or physical(p.grid_position) != p.position:
            raise ElectionError("grid_walk requires explicit integer grid_position for every voter")
    # Even undeclared grid controls cannot queue an off-lattice intervention.
    for action in scenario.interventions:
        if action.position is not None:
            integer_position(action.position)
        if action.group is not None or (action.overrides is not None and any(
                key in json.loads(action.overrides) for key in ("movement", "max_step", "proximity_radius", "parameters"))):
            raise ElectionError("grid episodes exclude movement/radius/group reconfiguration; start a new episode")
    if scenario.stochastic_case is None:
        return
    majority = scenario.majority_estimation
    if (scenario.k != 1 or len(scenario.parties) < 2 or majority is None
            or majority.memory_rounds != 10 or majority.poll_refresh_rounds != 10
            or majority.poll_weight != .5 or scenario.convergence_case is not None
            or any(g.voting != "memory_pivotal" or g.graph != "none" or g.communication != "none"
                   or json.loads(g.parameters) or g.capabilities != Capabilities() for g in effective)
            or scenario.interventions or scenario.persistent_edges or scenario.campaign_edges or scenario.private_channels
            or scenario.coalitions or any(x is not None for x in (scenario.campaign_controller,
               scenario.signal_controller, scenario.nomination, scenario.alignment, scenario.detector, scenario.leaders))):
        raise ElectionError("finite-grid occupation domain requires k1, homogeneous memory_pivotal, K10/L10, "
                            "default capabilities, no parameters, layers, messages, interventions or controllers")
    if any(any(getattr(g, phase).startswith("python:") for phase in ("voting", "movement", "communication", "graph"))
           for g in scenario.groups):
        raise ElectionError("finite-grid occupation excludes plugins, including unused groups")


def assessment(scenario):
    """Never report a finite seeded path as a certified stationary distribution."""
    return {"case": scenario.stochastic_case,
            "status": "conditional_occupation_theorem" if scenario.stochastic_case else "uncertified_comparison",
            "target": "class_dependent_long_run_occupation_frequencies",
            "assumption": "ideal independent categorical proposals across agents and rounds",
            "sampler": "sha256-keyed seeded categorical replay; not an infinite-IID proof",
            "ballot_absorption": False, "distributional_convergence": False,
            "mixing_time_bound": None, "recurrent_class_identified": False}
