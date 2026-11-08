"""Checkpoint field serialization and explicit legacy frame projections."""

import json
from typing import Any

from .model import ElectionError, Intervention, apply_overrides
from .policies import canonical_json
from .epistemic import EPISTEMIC_POLICIES


def action_dict(action: Intervention) -> dict[str, Any]:
    return {"round": action.round, "person": action.person,
            **({"group": action.group} if action.group is not None else {}),
            **({"preference": list(action.preference)} if action.preference is not None else {}),
            **({"position": list(action.position)} if action.position is not None else {}),
            **({"ballot": list(action.ballot)} if action.ballot is not None else {}),
            **({"overrides": json.loads(action.overrides)} if action.overrides is not None else {}),
            **({"add_edges": list(action.add_edges)} if action.add_edges else {}),
            **({"remove_edges": list(action.remove_edges)} if action.remove_edges else {}),
            **({"add_channels": list(action.add_channels)} if action.add_channels else {}),
            **({"remove_channels": list(action.remove_channels)} if action.remove_channels else {}),
            **({"add_campaign_edges": list(action.add_campaign_edges)} if action.add_campaign_edges else {}),
            **({"remove_campaign_edges": list(action.remove_campaign_edges)} if action.remove_campaign_edges else {})}


def legacy_frames(expected_frames, frames, version, scenario):
    """Project freshly serialized frames to a supported historical schema."""
    if version < 11:
        groups = {group.id: group for group in scenario.groups}
        for frame in expected_frames:
            for actor, memory in frame["policy_memory"].items():
                effective = apply_overrides(groups[frame["groups"][actor]], canonical_json(frame["overrides"][actor], "overrides"))
                if effective.voting in EPISTEMIC_POLICIES and isinstance(memory, dict):
                    for event in memory.get("observation_history", []):
                        for report in event.get("received_reports", []):
                            report.pop("generated_round", None)
                            report.pop("delivered_round", None)
                            report["source_round"] = None
            frame.pop("report_provenance")
    if version < 3:
        for frame in expected_frames:
            frame.pop("policy_memory")
    if version < 4:
        for frame in expected_frames:
            frame.pop("overrides")
    if version < 5:
        for frame in expected_frames:
            frame.pop("private_channels")
    if version < 7:
        for frame in expected_frames:
            frame.pop("phase_memory")
    if version < 8:
        for frame in expected_frames:
            frame.pop("ballot_sensors")
    if version < 9:
        for frame in expected_frames:
            frame.pop("campaign_edges")
    if version < 10:
        for frame in expected_frames:
            for event in frame["interventions"]:
                event.pop("origin", None)
    if version == 1 and frames:
        layouts = [
            {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges"},
            {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges", "delivered", "pending"},
            {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges", "delivered", "pending", "preferences", "groups", "interventions"},
        ]
        if not isinstance(frames[0], dict) or set(frames[0]) not in layouts or any(not isinstance(f, dict) or set(f) != set(frames[0]) for f in frames):
            raise ElectionError("unknown version 1 frame layout")
        expected_frames = [{key: frame[key] for key in frames[0]} for frame in expected_frames]
    return expected_frames
