"""Deterministic coalition information acquisition with independent budgets."""

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AcquiredInformation:
    sighted: dict
    overheard: dict
    sight_spend: dict
    eavesdrop_spend: dict
    sight_events: tuple
    overheard_events: tuple


def acquire_information(coalitions, permissions, preferences, pending, round_number,
                        previous_sight_spend, previous_eavesdrop_spend):
    """Build proposed observations/ledgers; never mutate committed inputs."""
    sighted = defaultdict(list)
    overheard = defaultdict(list)
    sight_spend = dict(previous_sight_spend)
    eavesdrop_spend = dict(previous_eavesdrop_spend)
    sight_events = []
    overheard_events = []
    for coalition in coalitions:
        if not coalition.sight_targets:
            continue
        round_spend = 0
        for observer in coalition.members:
            if not permissions[observer].observe_target_preferences:
                continue
            for target in coalition.sight_targets:
                if target == observer:
                    continue
                if round_spend >= coalition.sight_budget_per_round or sight_spend[coalition.id] >= coalition.sight_budget_total:
                    break
                round_spend += 1
                sight_spend[coalition.id] += 1
                sighted[observer].append((target, round_number, preferences[target]))
                sight_events.append((coalition.id, observer, target, preferences[target]))
    for coalition in coalitions:
        if not coalition.eavesdrop_channels:
            continue
        round_spend = 0
        for observer in coalition.members:
            if not permissions[observer].intercept_private_reports:
                continue
            for sender, recipient, channel, payload in sorted(pending):
                if channel not in coalition.eavesdrop_channels or observer in (sender, recipient):
                    continue
                if round_spend >= coalition.eavesdrop_budget_per_round or eavesdrop_spend[coalition.id] >= coalition.eavesdrop_budget_total:
                    break
                round_spend += 1
                eavesdrop_spend[coalition.id] += 1
                overheard[observer].append((sender, recipient, channel, round_number - 1,
                                           round_number - 2, round_number, payload))
                overheard_events.append((coalition.id, observer, sender, recipient, channel, payload))
    return AcquiredInformation(sighted, overheard, sight_spend, eavesdrop_spend,
                               tuple(sight_events), tuple(overheard_events))
