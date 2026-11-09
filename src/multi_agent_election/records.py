"""Checkpoint field serialization and explicit legacy frame projections."""

import copy
import json
from typing import Any

from .model import ElectionError, Intervention, apply_overrides
from .policies import canonical_json
from .epistemic import EPISTEMIC_POLICIES


def checkpoint_scenario(raw, manual_actions=()):
    """Pin historical group motion defaults; never replay implicit overrides differently."""
    if not isinstance(raw, dict) or not isinstance(raw.get("groups"), dict):
        return raw
    raw = copy.deepcopy(raw)
    groups = raw["groups"]
    for group in groups.values():
        if not isinstance(group, dict) or group.get("movement") != "random_walk":
            continue
        params = group.get("parameters", {})
        motion = params.get("movement", {}) if isinstance(params, dict) else None
        if not isinstance(motion, dict):
            continue  # Normal scenario validation reports malformed data.
        distribution = motion.get("distribution", "uniform")
        if distribution == "normal":
            mean = motion.get("mean_step", group.get("max_step", 0))
            motion = {**motion, "distribution": distribution, "mean_step": mean,
                      "std_step": motion.get("std_step", mean / 4 if type(mean) in (int, float) else mean)}
        else:
            motion = {**motion, "distribution": distribution}
        group["parameters"] = {**params, "movement": motion}
    # Override dictionaries are serialized in each frame. Rewriting them would
    # falsify recorded history; require the archived runtime for ambiguous cases.
    people = raw.get("people", [])
    if not isinstance(people, list):
        return raw
    overrides = [p.get("overrides", {}) for p in people if isinstance(p, dict)]
    actions = raw.get("interventions", [])
    if isinstance(actions, list) and isinstance(manual_actions, (list, tuple)):
        overrides += [a.get("overrides", {}) for a in (*actions, *manual_actions) if isinstance(a, dict)]
    for override in overrides:
        if not isinstance(override, dict):
            continue
        if override.get("movement") == "random_walk" and "parameters" not in override:
            if any(isinstance(g, dict) and g.get("movement", "stationary") != "random_walk"
                   for g in groups.values()):
                raise ElectionError("legacy checkpoint has implicit movement parameters in an override; "
                                    "resume with the archived runtime, not changed Gaussian defaults")
        if not isinstance(override.get("parameters"), dict) or override.get("movement") == "stationary":
            continue
        motion = override["parameters"].get("movement", {})
        if not isinstance(motion, dict):
            continue
        # Conservative for mixed groups: absent override motion could have been
        # used after a scheduled group switch. Never guess its historical kernel.
        if (any(isinstance(g, dict) and g.get("movement") == "random_walk" for g in groups.values())
                or override.get("movement") == "random_walk"):
            if "distribution" not in motion or (motion["distribution"] == "normal"
                    and not {"mean_step", "std_step"} <= set(motion)):
                raise ElectionError("legacy checkpoint has implicit movement parameters in an override; "
                                    "resume with the archived runtime, not changed Gaussian defaults")
    return raw


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
