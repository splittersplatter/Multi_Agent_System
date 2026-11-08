"""Bounded issue-ideal drift and scoped, explicitly authorized influence."""

import math

from .model import Alignment, AlignmentAttack, ElectionError, _number
from .policies import policy_rng


def parse_alignment(raw, scenario):
    if not isinstance(raw, dict) or set(raw) != {"drift_max_step", "attack"}:
        raise ElectionError("alignment requires drift_max_step and attack")
    if scenario.nomination is not None or not scenario.people or scenario.people[0].ideal is None:
        raise ElectionError("alignment requires a spatial nomination scenario")
    if scenario.convergence_case is not None:
        raise ElectionError("certified convergence excludes changing issue ideals")
    if any(event.preference is not None for event in scenario.interventions):
        raise ElectionError("alignment scenarios derive preferences; ordinal preference interventions are unsupported")
    dimension = len(scenario.people[0].ideal)
    maximum = math.sqrt(dimension)
    drift = _number(raw["drift_max_step"], "drift_max_step", 0, maximum)
    attack = raw["attack"]
    required = {"target", "policy", "targets", "per_person_round", "total_budget", "observe_target_ideals"}
    if not isinstance(attack, dict) or set(attack) != required:
        raise ElectionError("alignment attack requires target, policy, targets, per_person_round, total_budget and observe_target_ideals")
    target = attack["target"]
    if not isinstance(target, str) or target not in scenario.parties:
        raise ElectionError("alignment attack target must be a nominated party")
    policy = attack["policy"]
    if policy not in ("none", "toward_target", "random"):
        raise ElectionError("alignment attack policy must be none, toward_target or random")
    people = {person.id for person in scenario.people}
    targets = attack["targets"]
    if (not isinstance(targets, list) or any(not isinstance(p, str) or p not in people for p in targets)
            or len(set(targets)) != len(targets)):
        raise ElectionError("alignment attack targets must be unique known people")
    if type(attack["observe_target_ideals"]) is not bool:
        raise ElectionError("observe_target_ideals must be boolean")
    if policy == "toward_target" and not attack["observe_target_ideals"]:
        raise ElectionError("toward_target requires explicit observe_target_ideals permission")
    per_person = _number(attack["per_person_round"], "alignment per_person_round", 0, maximum)
    total = _number(attack["total_budget"], "alignment total_budget", 0, 1e12)
    return Alignment(drift, AlignmentAttack(target, policy, tuple(sorted(targets)), per_person, total,
                                             attack["observe_target_ideals"]))


def _random_direction(rng, dimensions):
    values = tuple(rng.uniform(-1, 1) for _ in range(dimensions))
    length = math.hypot(*values)
    return tuple(v / length for v in values) if length else (0.0,) * dimensions


def _bounded_move(origin, direction, limit):
    if limit <= 0:
        return origin, 0.0
    scale = limit
    for _ in range(12):
        result = tuple(min(1.0, max(0.0, x + scale * d)) for x, d in zip(origin, direction))
        distance = math.dist(origin, result)
        if distance <= limit:
            return result, distance
        scale *= (limit / distance) * (1 - 1e-12)
    raise ElectionError("cannot realize bounded alignment movement within floating-point precision")


def advance_alignment(scenario, previous, previous_spend, round_number, target_platform=None):
    """Drift first, then deterministic-ID budget allocation; return committed candidates."""
    config = scenario.alignment
    attack = config.attack
    initial = {p.id: p.ideal for p in scenario.people}
    target_platform = initial[attack.target] if target_platform is None else target_platform
    targets = set(attack.targets)
    current = {}; changes = []; spend = previous_spend
    for person in sorted(previous):
        before = previous[person]
        drift_rng = policy_rng(scenario.seed, person, round_number, "ideal-drift")
        direction = _random_direction(drift_rng, len(before))
        drift, _ = _bounded_move(before, direction, config.drift_max_step * drift_rng.random())
        after, cost = drift, 0.0
        remaining = max(0.0, attack.total_budget - spend)
        limit = min(attack.per_person_round, remaining)
        if person in targets and attack.policy != "none" and limit > 0:
            if attack.policy == "toward_target":
                vector = tuple(t - x for t, x in zip(target_platform, drift))
                distance = math.hypot(*vector)
                direction = tuple(v / distance for v in vector) if distance else (0.0,) * len(drift)
                limit = min(limit, distance)
            else:
                rng = policy_rng(scenario.seed, person, round_number, "ideal-attack")
                direction = _random_direction(rng, len(drift))
            after, cost = _bounded_move(drift, direction, limit)
            if attack.policy == "toward_target":
                after = tuple(min(max(value, min(start, target)), max(start, target))
                              for value, start, target in zip(after, drift, target_platform))
                cost = math.dist(drift, after)
            if spend + cost > attack.total_budget:
                after, cost = _bounded_move(drift, direction, math.nextafter(limit, 0.0))
                if attack.policy == "toward_target":
                    after = tuple(min(max(value, min(start, target)), max(start, target))
                                  for value, start, target in zip(after, drift, target_platform))
                    cost = math.dist(drift, after)
            if spend + cost > attack.total_budget:
                raise ElectionError("alignment attack exceeds total budget")
            spend += cost
        current[person] = after
        changes.append((person, before, drift, after, cost))
    platforms = {party: initial[party] for party in scenario.parties}
    preferences = {person: tuple(sorted(scenario.parties,
                     key=lambda party: (math.dist(ideal, platforms[party]), scenario.parties.index(party))))
                   for person, ideal in current.items()}
    return current, spend, tuple(changes), preferences
