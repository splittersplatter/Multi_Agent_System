"""Versioned cumulative mechanism controls and independently replayable runs."""

import hashlib
import json

from .engine import Simulation
from .metrics import series
from .model import ElectionError, apply_overrides, make_scenario


MECHANISMS = ("proximity", "coalition", "campaign_edges", "poll_distortion",
              "nomination", "alignment_attack", "leader_adaptation")


def _validate_source(scenario, seeds, target):
    if not isinstance(seeds, list) or not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("combined seeds must be unique nonnegative integers")
    if not isinstance(target, str) or target not in scenario.parties:
        raise ElectionError("combined target must be a nominated party")
    if scenario.interventions:
        raise ElectionError("combined matrix excludes scheduled interventions")
    groups = {group.id: group for group in scenario.groups}
    effective = {p.id: apply_overrides(groups[p.group], p.overrides) for p in scenario.people}
    if any(g.movement not in ("stationary", "random_walk") or g.graph != "none"
           or any(getattr(g, field).startswith("python:") for field in ("voting", "movement", "communication", "graph"))
           for g in effective.values()):
        raise ElectionError("combined matrix requires built-in policies and no graph plugins")
    if (scenario.proximity_mode != "dynamic" or
            not any(g.movement == "random_walk" and g.max_step > 0 for g in effective.values()) or
            not any((g.proximity_radius if g.proximity_radius is not None else scenario.radius) is not None for g in effective.values())):
        raise ElectionError("combined source requires moving agents and dynamic proximity")
    if scenario.nomination is None or scenario.nomination.mode != "endogenous":
        raise ElectionError("combined source requires endogenous nomination")
    if scenario.detector is None:
        raise ElectionError("combined source requires a passive detector")
    campaign = scenario.campaign_controller
    if campaign is None or campaign.policy == "none" or not campaign.per_round_budget or not campaign.lifetime_budget:
        raise ElectionError("combined source requires a positive-budget campaign controller")
    signal = scenario.signal_controller
    if signal is None or signal.policy == "truthful" or not signal.per_broadcast_budget or not signal.lifetime_budget:
        raise ElectionError("combined source requires a positive-budget distorted signal")
    alignment = scenario.alignment
    if (alignment is None or alignment.attack.policy == "none" or not alignment.attack.targets
            or not alignment.attack.per_person_round or not alignment.attack.total_budget):
        raise ElectionError("combined source requires a positive-budget alignment attack")
    leaders = scenario.leaders
    if (leaders is None or leaders.policy != "feedback" or not leaders.adaptors or not leaders.per_round_step
            or not leaders.lifetime_budget or leaders.signal_mode != "broadcast" or not leaders.perception_weight):
        raise ElectionError("combined source requires adaptive leaders with broadcast perceptions")
    coalitions = scenario.coalitions
    members = {p for c in coalitions for p in c.members}
    deception = any(c.report_budget_per_round and c.report_budget_total and
                    any(effective[p].communication == "target_report" for p in c.members) for c in coalitions)
    sight = any(c.sight_targets and c.sight_budget_per_round and c.sight_budget_total and
                any(effective[p].capabilities.observe_target_preferences for p in c.members) for c in coalitions)
    interception = any(c.eavesdrop_channels and c.eavesdrop_budget_per_round and c.eavesdrop_budget_total and
                       any(effective[p].capabilities.intercept_private_reports for p in c.members) for c in coalitions)
    coordination = any(len(channel_members) > 1 and any(p in members and effective[p].capabilities.send_private_reports
                       and effective[p].capabilities.receive_private_reports for p in channel_members)
                       for _, channel_members in scenario.private_channels)
    if not (deception and sight and interception and coordination):
        raise ElectionError("combined source requires configured coalition deception, sight, interception and private coordination")


def _arm_specifications():
    all_set = set(MECHANISMS)
    arms = [("all_enabled", all_set, False), ("all_disabled", set(), False)]
    arms += [(f"isolated_{name}", {name}, False) for name in MECHANISMS]
    arms += [(f"without_{name}", all_set - {name}, False) for name in MECHANISMS]
    arms.append(("detector_off", all_set, True))
    return arms


def _configure(raw, enabled, nominees, detector_off):
    if "proximity" not in enabled:
        raw["network"]["proximity_mode"] = "frozen"
        raw["network"].pop("static_proximity_edges", None)
    if "coalition" not in enabled:
        members = set()
        for coalition in raw["coalitions"]:
            members.update(coalition["members"])
            for key in ("report_budget_per_round", "report_budget_total", "sight_budget_per_round", "sight_budget_total",
                        "eavesdrop_budget_per_round", "eavesdrop_budget_total"):
                if key in coalition:
                    coalition[key] = 0
        for person in raw["people"]:
            if person["id"] in members:
                capabilities = person["overrides"].setdefault("capabilities", {})
                capabilities.update(send_private_reports=False, receive_private_reports=False)
    if "campaign_edges" not in enabled:
        raw["campaign_controller"]["policy"] = "none"
    if "poll_distortion" not in enabled:
        raw["signal_controller"]["policy"] = "truthful"
    if "nomination" not in enabled:
        raw["nomination"]["mode"] = "fixed"
        raw["nomination"]["nominees"] = list(nominees)
    if "alignment_attack" not in enabled:
        raw["alignment"]["attack"]["policy"] = "none"
    if "leader_adaptation" not in enabled:
        raw["leaders"]["policy"] = "fixed"
    if detector_off:
        raw.pop("detector")
    return raw


def _exposure(frames, people):
    exposure = {p: 0 for p in people}
    for frame in frames[1:]:
        for _, receiver in frame["proximity_edges"]:
            exposure[receiver] += 1
    return exposure


def combined_ablation(scenario, seeds, target):
    """Produce fully specified 17-arm matched controls; no statistical inference."""
    _validate_source(scenario, seeds, target)
    specifications = _arm_specifications(); rows = []; run_manifest = None
    people = sorted(p.id for p in scenario.people)
    for seed in seeds:
        seed_raw = scenario.as_dict(); seed_raw["seed"] = seed
        # Nominees are resolved from the unmodified initial network for every arm.
        try:
            seed_scenario = make_scenario(seed_raw)
            nominees = seed_scenario.nomination.nominees
            nomination_error = None
        except ElectionError as exc:
            nominees = None; nomination_error = str(exc)
        runs = {}
        for arm, enabled, detector_off in specifications:
            raw = scenario.as_dict(); raw["seed"] = seed
            if nominees is None and "nomination" not in enabled:
                runs[arm] = {"status": "failed", "scenario": None,
                             "error": f"baseline nomination unavailable: {nomination_error}",
                             "completed_round": None, "frames": [], "metrics": [], "policy_digests": {}}
                continue
            raw = _configure(raw, enabled, nominees, detector_off)
            selected = None; sim = None; manifest_mismatch = False
            try:
                selected = make_scenario(raw); sim = Simulation(selected)
                if run_manifest is not None and sim.runtime_manifest != run_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between combined runs")
                run_manifest = sim.runtime_manifest; sim.run()
                config = selected.as_dict()
                digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
                run = {"status": "ok", "scenario": config, "scenario_sha256": digest,
                       "nomination": selected.nomination.as_dict(), "parties": list(selected.parties),
                       "frames": [f.as_dict() for f in sim.frames], "metrics": series(selected, sim.frames),
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()}}
            except ElectionError as exc:
                if manifest_mismatch:
                    raise
                run = {"status": "failed", "scenario": selected.as_dict() if selected else raw,
                       "error": str(exc), "completed_round": sim.current.round if sim else None,
                       "frames": [f.as_dict() for f in sim.frames] if sim else [],
                       "metrics": series(selected, sim.frames) if sim else [],
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()} if sim else {}}
            runs[arm] = run
        for arm, enabled, detector_off in specifications:
            run = runs[arm]
            if run["status"] != "ok":
                continue
            baseline_name = ("all_disabled" if arm == "all_disabled" or arm.startswith("isolated_") else
                             "all_disabled" if arm == "all_enabled" else "all_enabled")
            baseline = runs[baseline_name]; run["baseline"] = baseline_name
            run["movement_matched"] = (None if baseline["status"] != "ok" else
                len(run["frames"]) == len(baseline["frames"]) and
                all(a["positions"] == b["positions"] for a, b in zip(run["frames"], baseline["frames"])))
            run["same_candidates"] = None if baseline["status"] != "ok" else run["parties"] == baseline["parties"]
            if not run["movement_matched"] or not run["same_candidates"]:
                continue
            actual = _exposure(run["frames"], people); control = _exposure(baseline["frames"], people)
            delta = {p: actual[p] - control[p] for p in people}
            run["exposure"] = {"person_delta": delta, "absolute_delta_sum": sum(abs(v) for v in delta.values()),
                "edge_round_symmetric_difference": sum(len({tuple(e) for e in a["proximity_edges"]} ^
                                                             {tuple(e) for e in b["proximity_edges"]})
                                                       for a, b in zip(run["frames"][1:], baseline["frames"][1:]))}
            run["paired"] = [{"round": t["round"], "target_win_delta": int(t["winner"] == target) - int(c["winner"] == target),
                              "target_share_delta": t["shares"][target] - c["shares"][target],
                              "target_margin_delta": (t["counts"][target] - max((v for p, v in t["counts"].items() if p != target), default=0)) -
                                                     (c["counts"][target] - max((v for p, v in c["counts"].items() if p != target), default=0)),
                              "winner_same": t["winner"] == c["winner"]}
                             for c, t in zip(baseline["metrics"], run["metrics"])]
            if arm == "detector_off":
                run["detector_noninterference"] = all({k: v for k, v in a.items() if k != "detector"} ==
                                                      {k: v for k, v in b.items() if k != "detector"}
                                                      for a, b in zip(run["frames"], baseline["frames"]))
        rows.append({"seed": seed, "runs": runs})
    return {"record_type": "eclipse.combined-ablation", "record_version": 1,
            "scenario": scenario.as_dict(), "target": target, "seeds": seeds, "manifest": run_manifest,
            "arms": [{"id": arm, "enabled": [name for name in MECHANISMS if name in enabled], "detector_off": detector_off}
                     for arm, enabled, detector_off in specifications], "rows": rows,
            "notes": ["Enabled means configured, not necessarily a realized action; inspect budgets and traces.",
                      "Nomination-off fixes the same initial nominees; it measures process-only differences, not composition effects.",
                      "Proximity-off freezes initial contacts but retains physical movement; exposure residuals are reported.",
                      "Coalition-off zeros capability budgets and disables coalition private send/receive; membership remains fixed.",
                      "Poll-off is truthful, campaign-off adds no edges, alignment attack-off retains natural drift, leader-off retains coupled noisy broadcasts.",
                      "Detector is passive instrumentation in all seven-mechanism arms; a separate detector-off arm checks noninterference.",
                      "Realized signals and graph contacts can differ after interventions; matched seeds do not establish causal identification or convergence.",
                      "Failures, mismatched controls and full frames remain visible; outcomes are descriptive."]}
