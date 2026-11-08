"""Shared exclusive output writers for CLI and HTTP exports."""

import csv
import json
from pathlib import Path
from urllib.parse import quote

from .model import ElectionError


def write_jsonl(path: Path, data: dict) -> None:
    """Write a manifest followed by every metric and available recorded frame."""
    header = {key: data[key] for key in ("record_type", "record_version", "scenario", "manifest", "policy_digests", "recording")}
    if "nomination" in data:
        header["nomination"] = data["nomination"]
    if "stride" in data:
        header["stride"] = data["stride"]
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "manifest", **header}, allow_nan=False) + "\n")
        for row in data["metrics"]:
            handle.write(json.dumps({"type": "metrics", "data": row}, allow_nan=False) + "\n")
        for frame in data.get("frames", []):
            handle.write(json.dumps({"type": "frame", "data": frame}, allow_nan=False) + "\n")


def preflight_outputs(paths: list[Path | None]) -> None:
    """Reject conflicts before starting a run or creating any requested output."""
    outputs = [path for path in paths if path is not None]
    for path in outputs:
        if path.exists() or path.is_symlink():
            raise ElectionError(f"output already exists: {path}")
        if not path.parent.is_dir():
            raise ElectionError(f"output parent directory does not exist: {path.parent}")
    canonical = [path.resolve() for path in outputs]
    if len(set(canonical)) != len(outputs):
        raise ElectionError("output paths must be distinct, including aliases")


def write_metrics_csv(path: Path, scenario, rows: list[dict]) -> None:
    fixed = ("round", "winner", "winner_margin", "mean_winner_rank", "ballot_switch_count", "ballot_switch_rate",
             "public_edge_count", "persistent_edge_count", "proximity_edge_count", "campaign_edge_count",
             "private_channel_count", "private_membership_count", "mean_out_degree", "intervention_count",
             "sensor_observation_count", "proximity_edge_additions", "proximity_edge_removals",
             "proximity_edge_turnover", "public_edge_additions", "public_edge_removals", "public_edge_turnover",
             "proximity_mean_in_degree")
    names = list(fixed) + [f"count:{party}" for party in scenario.parties]
    majority_fields = ("majority_cached_neighbors", "majority_mean_sample_size", "majority_empty_fraction")
    if scenario.majority_estimation is not None:
        names += list(majority_fields)
    names += [f"share:{quote(party, safe='')}" for party in scenario.parties]
    names += [f"{kind}:{rank + 1}:{quote(party, safe='')}" for kind in ("rank_count", "rank_frequency")
              for rank in range(scenario.k) for party in scenario.parties]
    groups = sorted(group.id for group in scenario.groups)
    names += [f"group_size:{quote(group, safe='')}" for group in groups]
    names += [f"{kind}:{quote(group, safe='')}:{quote(party, safe='')}" for kind in ("group_count", "group_share")
              for group in groups for party in scenario.parties]
    origins = ("scheduled", "interactive", "policy", "unknown")
    names += [f"intervention_origin:{origin}" for origin in origins]
    if scenario.coalitions:
        names += ["deceptive_report_count"] + [f"coalition_report_spend:{quote(c.id, safe='')}" for c in scenario.coalitions]
    sight_coalitions = [c for c in scenario.coalitions if c.sight_targets]
    if sight_coalitions:
        names += ["preference_sight_count"] + [f"coalition_sight_spend:{quote(c.id, safe='')}" for c in sight_coalitions]
    eavesdrop_coalitions = [c for c in scenario.coalitions if c.eavesdrop_channels]
    if eavesdrop_coalitions:
        names += ["eavesdrop_count"] + [f"coalition_eavesdrop_spend:{quote(c.id, safe='')}" for c in eavesdrop_coalitions]
    if scenario.campaign_controller is not None:
        names += ["campaign_controller_spend", "campaign_controller_added_count", "campaign_controller_eligible_count"]
    if scenario.signal_controller is not None:
        names += ["signal_spend","signal_broadcast_cost","signal_source_round","signal_broadcast_round"]
        names += [f"signal_{kind}:{quote(party,safe='')}" for kind in ("report","truth") for party in scenario.parties]
    if scenario.nomination is not None:
        names += ["mean_winner_ideal_distance", "mean_nearest_nominee_distance"]
    if scenario.alignment is not None:
        names += ["mean_winner_current_ideal_distance", "mean_nearest_current_nominee_distance", "alignment_attack_spend",
                  "alignment_attack_cost", "alignment_targeted_count", "alignment_natural_distance"]
    if scenario.leaders is not None:
        names += ["leader_total_spend", "mean_leader_perception_error", "mean_winner_true_current_distance", "mean_winner_perceived_current_distance"]
        names += [f"leader_{kind}:{quote(party,safe='')}" for kind in ("spend", "perception_error") for party in scenario.parties]
        names += [f"leader_{kind}:{quote(party,safe='')}:{axis+1}" for kind in ("true", "perceived", "signal")
                  for party in scenario.parties for axis in range(len(scenario.people[0].ideal))]
    detector_fields = ("detector_share_change", "detector_alert", "detector_first_alert_round",
                       "detector_target_win_streak", "detector_first_triple_win_round")
    if scenario.detector is not None:
        names += list(detector_fields)
    convergence_fields = ("case", "scheduler", "next_actor", "improving_voters", "status", "reason", "next_intervention_round")
    if scenario.convergence_case:
        names += [f"convergence:{field}" for field in convergence_fields]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(names)
        for row in rows:
            values = [row[key] for key in fixed] + [row["counts"][party] for party in scenario.parties]
            if scenario.majority_estimation is not None:
                values += [row[name] for name in majority_fields]
            values += [row["shares"][party] for party in scenario.parties]
            values += [row["rank_counts" if kind == "rank_count" else "rank_frequencies"][party][rank]
                       for kind in ("rank_count", "rank_frequency") for rank in range(scenario.k) for party in scenario.parties]
            values += [row["group_sizes"][group] for group in groups]
            values += [row["group_counts" if kind == "group_count" else "group_shares"][group][party]
                       for kind in ("group_count", "group_share") for group in groups for party in scenario.parties]
            values += [row["intervention_origin_counts"].get(origin, 0) for origin in origins]
            if scenario.coalitions:
                values += [row["deceptive_report_count"]] + [row["coalition_report_spend"][c.id] for c in scenario.coalitions]
            if sight_coalitions:
                values += [row["preference_sight_count"]] + [row["coalition_sight_spend"][c.id] for c in sight_coalitions]
            if eavesdrop_coalitions:
                values += [row["eavesdrop_count"]] + [row["coalition_eavesdrop_spend"][c.id] for c in eavesdrop_coalitions]
            if scenario.campaign_controller is not None:
                values += [row["campaign_controller_spend"],row["campaign_controller_added_count"],row["campaign_controller_eligible_count"]]
            if scenario.signal_controller is not None:
                values += [row["signal_spend"],row["signal_broadcast_cost"],row["signal_source_round"],row["signal_broadcast_round"]]
                values += [(row["signal_report" if kind == "report" else "signal_source_truth"] or {}).get(party)
                           for kind in ("report","truth") for party in scenario.parties]
            if scenario.nomination is not None:
                values += [row["mean_winner_ideal_distance"], row["mean_nearest_nominee_distance"]]
            if scenario.alignment is not None:
                values += [row[name] for name in ("mean_winner_current_ideal_distance", "mean_nearest_current_nominee_distance",
                           "alignment_attack_spend", "alignment_attack_cost", "alignment_targeted_count", "alignment_natural_distance")]
            if scenario.leaders is not None:
                values += [row[name] for name in ("leader_total_spend", "mean_leader_perception_error", "mean_winner_true_current_distance", "mean_winner_perceived_current_distance")]
                values += [row[f"leader_{kind}"][party] for kind in ("spend", "perception_error") for party in scenario.parties]
                values += [(row["leader_signals"] or {}).get(party, [None] * len(scenario.people[0].ideal))[axis] if kind == "signal"
                           else row[f"leader_{kind}"][party][axis] for kind in ("true", "perceived", "signal")
                           for party in scenario.parties for axis in range(len(scenario.people[0].ideal))]
            if scenario.detector is not None:
                values += [row[name] for name in detector_fields]
            if scenario.convergence_case:
                values += [row["convergence"].get(field) for field in convergence_fields]
            writer.writerow(values)

