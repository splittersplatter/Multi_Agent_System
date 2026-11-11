"""Budgeted directed campaign links from explicitly public inputs only."""

from collections import Counter
from .model import ElectionError


def select_campaign_edges(controller, public_first_choices, public_edges, purchased, rng):
    """Return exact eligible set and selected additions; no private data is accepted."""
    remaining = controller.lifetime_budget - len(purchased)
    count = min(remaining, controller.per_round_budget)
    if controller.policy == "none" or count <= 0:
        return None, ()
    supporters = sorted(person for person,choice in public_first_choices.items() if choice == controller.target)
    others = sorted(person for person,choice in public_first_choices.items() if choice != controller.target)
    eligible = []
    for sender in supporters:
        for recipient in others:
            edge = (sender,recipient)
            if edge not in public_edges and edge not in purchased:
                eligible.append(edge)
                if len(eligible) > controller.max_candidates:
                    raise ElectionError("campaign eligible edge set exceeds max_candidates")
    if controller.policy == "random":
        choices = list(eligible); rng.shuffle(choices)
    else:
        outdegree = Counter(sender for sender,_ in public_edges)
        choices = sorted(eligible, key=lambda edge:(-outdegree[edge[1]],edge[1],edge[0]))
    return tuple(eligible), tuple(choices[:count])
