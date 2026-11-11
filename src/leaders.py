"""Leader feedback based only on public scores and the leader's own state."""

import math

from .alignment import _bounded_move
from .model import ElectionError, LeaderConfig, _number
from .policies import policy_rng


def parse_leaders(raw, scenario):
    fields = {"policy", "adaptors", "per_round_step", "lifetime_budget", "signal_mode", "signal_noise", "perception_weight"}
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ElectionError("leaders requires policy, adaptors, budgets and signal/perception settings")
    if not scenario.people or scenario.people[0].ideal is None:
        raise ElectionError("leaders require a spatial nomination scenario")
    if scenario.convergence_case is not None:
        raise ElectionError("certified convergence excludes leader adaptation and signals")
    if any(event.preference is not None for event in scenario.interventions):
        raise ElectionError("leader scenarios derive preferences; ordinal preference interventions are unsupported")
    if raw["policy"] not in ("fixed", "feedback"):
        raise ElectionError("leader policy must be fixed or feedback")
    adaptors = raw["adaptors"]
    if (not isinstance(adaptors, list) or any(not isinstance(p, str) or p not in scenario.parties for p in adaptors)
            or len(set(adaptors)) != len(adaptors)):
        raise ElectionError("leader adaptors must be unique nominated parties")
    if raw["signal_mode"] not in ("broadcast", "none"):
        raise ElectionError("leader signal_mode must be broadcast or none")
    diagonal = math.sqrt(len(scenario.people[0].ideal))
    return LeaderConfig(raw["policy"], tuple(sorted(adaptors)),
                        _number(raw["per_round_step"], "leader per_round_step", 0, diagonal),
                        _number(raw["lifetime_budget"], "leader lifetime_budget", 0, 1e12),
                        raw["signal_mode"], _number(raw["signal_noise"], "leader signal_noise", 0, 1),
                        _number(raw["perception_weight"], "leader perception_weight", 0, 1))


def advance_leaders(config, seed, round_number, parties, public_counts, prior_true, prior_perceived, prior_spend, prior_memory):
    """All leaders act simultaneously from previous public counts and own state."""
    true = {}; perceived = {}; spend = {}; memory = {}; signals = {}
    adaptors = set(config.adaptors)
    for party in parties:
        position = prior_true[party]
        old_action, old_support = prior_memory[party]
        support = public_counts[party]
        result = position; cost = 0.0; action = None
        remaining = max(0.0, config.lifetime_budget - prior_spend[party])
        limit = min(config.per_round_step, remaining)
        if config.policy == "feedback" and party in adaptors and limit > 0:
            directions = 2 * len(position)
            if old_action is None or old_support is None:
                start = 0
            elif support > old_support:
                start = old_action
            elif support < old_support:
                start = old_action ^ 1
            else:
                start = (old_action + 1) % directions
            for offset in range(directions):
                candidate = (start + offset) % directions
                vector = [0.0] * len(position)
                vector[candidate // 2] = 1.0 if candidate % 2 == 0 else -1.0
                proposed, distance = _bounded_move(position, vector, limit)
                if prior_spend[party] + distance > config.lifetime_budget:
                    proposed, distance = _bounded_move(position, vector, math.nextafter(limit, 0.0))
                if prior_spend[party] + distance > config.lifetime_budget:
                    raise ElectionError("leader movement exceeds lifetime budget")
                if distance > 0:
                    result, cost, action = proposed, distance, candidate
                    break
        true[party] = result
        spend[party] = prior_spend[party] + cost
        memory[party] = (action, support)
        if config.signal_mode == "broadcast":
            rng = policy_rng(seed, party, round_number, "leader-signal")
            signal = tuple(min(1.0, max(0.0, x + rng.uniform(-config.signal_noise, config.signal_noise))) for x in result)
            signals[party] = signal
            perceived[party] = tuple(min(1.0, max(0.0, (1 - config.perception_weight) * p + config.perception_weight * s))
                                     for p, s in zip(prior_perceived[party], signal))
        else:
            perceived[party] = prior_perceived[party]
    return true, perceived, spend, memory, (signals if config.signal_mode == "broadcast" else None)


def perceived_preferences(parties, ideals, perceived):
    return {person: tuple(sorted(parties, key=lambda p: (math.dist(ideal, perceived[p]), parties.index(p))))
            for person, ideal in ideals.items()}
