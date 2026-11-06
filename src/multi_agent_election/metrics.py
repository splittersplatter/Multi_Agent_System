"""Measurements computed solely from committed simulation frames."""

from collections import Counter, defaultdict
from .model import Frame, Scenario


def frame_metrics(scenario: Scenario, frame: Frame, previous: Frame | None = None) -> dict:
    ballots, preferences, groups = dict(frame.ballots), dict(frame.preferences), dict(frame.groups)
    counts = dict(frame.counts)
    n = len(ballots)
    group_counts = defaultdict(Counter)
    ranks = {party: [0] * scenario.k for party in scenario.parties}
    for person, ballot in ballots.items():
        group_counts[groups[person]][ballot[0]] += 1
        for rank, party in enumerate(ballot):
            ranks[party][rank] += 1
    # A gap in recorded history cannot establish one-round switching.
    prev = dict(previous.ballots) if previous is not None and previous.round == frame.round - 1 else None
    switches = sum(ballots[p] != prev[p] for p in ballots) if prev is not None else None
    edges = set(frame.persistent_edges) | set(frame.proximity_edges) | set(frame.campaign_edges)
    ordered_counts = sorted(counts.values(), reverse=True)
    group_sizes = Counter(groups.values())
    group_ids = sorted(group.id for group in scenario.groups)
    group_counts = {group: {party: group_counts[group][party] for party in scenario.parties} for group in group_ids}
    origin_counts = Counter(action.origin or "unknown" for action in frame.interventions)
    origin_counts = {origin: origin_counts[origin] for origin in sorted(set(origin_counts) | {"scheduled", "interactive", "policy"})}
    return {
        "round": frame.round,
        "winner": frame.winner,
        "counts": counts,
        "shares": {party: counts[party] / n for party in scenario.parties},
        "rank_counts": ranks,
        "rank_frequencies": {party: [count / n for count in values] for party, values in ranks.items()},
        "winner_margin": ordered_counts[0] - (ordered_counts[1] if len(ordered_counts) > 1 else 0),
        "mean_winner_rank": sum(pref.index(frame.winner) for pref in preferences.values()) / n,
        "ballot_switch_count": switches,
        "ballot_switch_rate": switches / n if switches is not None else None,
        "group_sizes": {group: group_sizes[group] for group in group_ids},
        "group_counts": group_counts,
        "group_shares": {group: {party: group_counts[group][party] / group_sizes[group] if group_sizes[group] else None
                                  for party in scenario.parties} for group in group_ids},
        "public_edge_count": len(edges),
        "persistent_edge_count": len(frame.persistent_edges),
        "proximity_edge_count": len(frame.proximity_edges),
        "campaign_edge_count": len(frame.campaign_edges),
        "private_channel_count": len(frame.private_channels),
        "private_membership_count": sum(len(members) for _, members in frame.private_channels),
        "mean_out_degree": len(edges) / n,
        "intervention_count": len(frame.interventions),
        "intervention_origin_counts": origin_counts,
        "sensor_observation_count": len(frame.ballot_sensors),
    }


def series(scenario: Scenario, frames: list[Frame] | tuple[Frame, ...]) -> list[dict]:
    return [frame_metrics(scenario, frame, frames[i - 1] if i else None) for i, frame in enumerate(frames)]
