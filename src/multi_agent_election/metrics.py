"""Measurements computed solely from committed simulation frames."""

from collections import Counter, defaultdict
from .model import ElectionError, Frame, Scenario, apply_overrides
from .voting import direct_best_response, source_local_dominance, certified_conformity
import json
import math


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
    proximity = set(frame.proximity_edges)
    previous_proximity = set(previous.proximity_edges) if prev is not None else None
    previous_public = (set(previous.persistent_edges) | set(previous.proximity_edges) | set(previous.campaign_edges)
                       if prev is not None else None)

    def changes(current, prior):
        if prior is None:
            return None, None, None
        union = current | prior
        return len(current - prior), len(prior - current), len(current ^ prior) / len(union) if union else 0.0

    proximity_added, proximity_removed, proximity_turnover = changes(proximity, previous_proximity)
    public_added, public_removed, public_turnover = changes(edges, previous_public)
    ordered_counts = sorted(counts.values(), reverse=True)
    group_sizes = Counter(groups.values())
    group_ids = sorted(group.id for group in scenario.groups)
    group_counts = {group: {party: group_counts[group][party] for party in scenario.parties} for group in group_ids}
    origin_counts = Counter(action.origin or "unknown" for action in frame.interventions)
    origin_counts = {origin: origin_counts[origin] for origin in sorted(set(origin_counts) | {"scheduled", "interactive", "policy"})}
    result = {
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
        "proximity_edge_additions": proximity_added,
        "proximity_edge_removals": proximity_removed,
        "proximity_edge_turnover": proximity_turnover,
        "public_edge_additions": public_added,
        "public_edge_removals": public_removed,
        "public_edge_turnover": public_turnover,
        "proximity_mean_in_degree": len(proximity) / n,
        "campaign_edge_count": len(frame.campaign_edges),
        "private_channel_count": len(frame.private_channels),
        "private_membership_count": sum(len(members) for _, members in frame.private_channels),
        "mean_out_degree": len(edges) / n,
        "intervention_count": len(frame.interventions),
        "intervention_origin_counts": origin_counts,
        "sensor_observation_count": len(frame.ballot_sensors),
    }
    if scenario.nomination is not None:
        ideals = {person.id: person.ideal for person in scenario.people}
        result["mean_winner_ideal_distance"] = sum(math.dist(ideals[p], ideals[frame.winner]) for p in ballots) / n
        result["mean_nearest_nominee_distance"] = sum(min(math.dist(ideals[p], ideals[c]) for c in scenario.parties)
                                                       for p in ballots) / n
        if frame.alignment_ideals is not None:
            current = dict(frame.alignment_ideals)
            result["mean_winner_current_ideal_distance"] = sum(math.dist(current[p], ideals[frame.winner]) for p in ballots) / n
            result["mean_nearest_current_nominee_distance"] = sum(min(math.dist(current[p], ideals[c]) for c in scenario.parties)
                                                                   for p in ballots) / n
            result["alignment_attack_spend"] = frame.alignment_spend
            result["alignment_attack_cost"] = sum(event[4] for event in frame.alignment_changes)
            result["alignment_targeted_count"] = sum(event[4] > 0 for event in frame.alignment_changes)
            result["alignment_natural_distance"] = sum(math.dist(event[1], event[2]) for event in frame.alignment_changes)
        if frame.leader_true is not None:
            true = dict(frame.leader_true); perceived = dict(frame.leader_perceived)
            current = dict(frame.alignment_ideals) if frame.alignment_ideals is not None else ideals
            errors = {p: math.dist(true[p], perceived[p]) for p in scenario.parties}
            result["leader_true"] = {p: list(true[p]) for p in scenario.parties}
            result["leader_perceived"] = {p: list(perceived[p]) for p in scenario.parties}
            result["leader_signals"] = None if frame.leader_signals is None else {p: list(v) for p, v in frame.leader_signals}
            result["leader_spend"] = dict(frame.leader_spend)
            result["leader_total_spend"] = sum(result["leader_spend"].values())
            result["leader_perception_error"] = errors
            result["mean_leader_perception_error"] = sum(errors.values()) / len(errors)
            result["mean_winner_true_current_distance"] = sum(math.dist(current[p], true[frame.winner]) for p in ballots) / n
            result["mean_winner_perceived_current_distance"] = sum(math.dist(current[p], perceived[frame.winner]) for p in ballots) / n
    if scenario.majority_estimation is not None:
        sizes = [len(state.entries) for _, state in frame.majority_states]
        result["majority_cached_neighbors"] = sum(sizes)
        result["majority_mean_sample_size"] = sum(sizes) / n
        result["majority_empty_fraction"] = sum(size == 0 for size in sizes) / n
    if scenario.coalitions:
        result["deceptive_report_count"] = len(frame.deceptive_reports)
        result["coalition_report_spend"] = dict(frame.coalition_report_spend)
    if frame.coalition_sight_spend:
        result["preference_sight_count"] = len(frame.preference_sight)
        result["coalition_sight_spend"] = dict(frame.coalition_sight_spend)
    if frame.coalition_eavesdrop_spend:
        result["eavesdrop_count"] = len(frame.overheard_reports)
        result["coalition_eavesdrop_spend"] = dict(frame.coalition_eavesdrop_spend)
    if frame.campaign_controller_purchased is not None:
        result["campaign_controller_spend"] = len(frame.campaign_controller_purchased)
        result["campaign_controller_added_count"] = len(frame.campaign_controller_added)
        result["campaign_controller_eligible_count"] = (None if frame.campaign_controller_eligible is None
                                                        else len(frame.campaign_controller_eligible))
    if frame.signal_spend is not None:
        latest = frame.signal_latest
        target_index = scenario.parties.index(scenario.signal_controller.target)
        result.update(signal_spend=frame.signal_spend, signal_broadcast_cost=frame.signal_broadcast_cost,
                      signal_source_round=None if latest is None else latest[0],
                      signal_broadcast_round=None if latest is None else latest[1],
                      signal_report=None if latest is None else dict(zip(scenario.parties,latest[2])),
                      signal_source_truth=None if latest is None else dict(zip(scenario.parties,latest[3])),
                      signal_target_report=None if latest is None else latest[2][target_index],
                      signal_target_truth=None if latest is None else latest[3][target_index])
    if frame.detector is not None:
        result.update(detector_share_change=frame.detector.share_change, detector_alert=frame.detector.alert,
                      detector_first_alert_round=frame.detector.first_alert_round,
                      detector_target_win_streak=frame.detector.target_win_streak,
                      detector_first_triple_win_round=frame.detector.first_triple_win_round)
    if scenario.convergence_case:
        group_map = {g.id: g for g in scenario.groups}
        overrides = dict(frame.overrides)
        incoming = defaultdict(list)
        if scenario.convergence_case == "certified_conformity":
            for sender, receiver in edges:
                incoming[receiver].append(ballots[sender])
        movers = []
        reason = None
        try:
            for person in sorted(ballots):
                if scenario.convergence_case == "direct_best_response":
                    choice = direct_best_response(scenario.parties, counts, ballots[person][0], preferences[person])
                elif scenario.convergence_case == "source_local_dominance":
                    group = apply_overrides(group_map[groups[person]], overrides[person])
                    params = json.loads(group.parameters).get("voting", {})
                    choice = source_local_dominance(scenario.parties, counts, ballots[person][0], preferences[person],
                                                    params.get("radius", 0), params.get("max_states", 200000))
                else:
                    choice = certified_conformity(preferences[person], incoming[person])
                if choice != ballots[person][0]:
                    movers.append(person)
        except ElectionError as exc:
            reason = str(exc)
        result["convergence"] = {"case": scenario.convergence_case,
                                 "scheduler": "cyclic_person_id",
                                 "next_actor": sorted(ballots)[frame.round % n],
                                 "improving_voters": None if reason else len(movers),
                                 "status": ("unavailable" if reason else
                                            ("certified_equilibrium" if scenario.convergence_case == "direct_best_response" else "certified_policy_equilibrium") if not movers else "not_equilibrium"),
                                 **({"reason": reason} if reason else {})}
        future = [a.round for a in scenario.interventions if a.round > frame.round]
        if future:
            result["convergence"]["status"] = "pending_intervention"
            result["convergence"]["next_intervention_round"] = min(future)
    return result


def series(scenario: Scenario, frames: list[Frame] | tuple[Frame, ...]) -> list[dict]:
    return [frame_metrics(scenario, frame, frames[i - 1] if i else None) for i, frame in enumerate(frames)]
