"""Matched interventions compared under keyed exogenous randomness."""

from dataclasses import replace
import itertools
import json
import math
import time
from .campaign import select_campaign_edges
from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario, apply_overrides, make_scenario
from .voting import STRATEGIC, configure_voting
from .epistemic import EPISTEMIC_POLICIES


def compare_leaders(scenario: Scenario, seeds: list[int]) -> dict:
    """Compare fixed/adaptive leaders with broadcast/frozen perceptions."""
    if scenario.leaders is None:
        raise ElectionError("leader comparison requires leader configuration")
    if not isinstance(seeds, list) or not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("leader comparison seeds must be unique nonnegative integers")
    groups = {g.id: g for g in scenario.groups}
    effective = [apply_overrides(groups[p.group], p.overrides) for p in scenario.people]
    if any(g.movement not in ("stationary", "random_walk") or g.graph != "none"
           or any(getattr(g, field).startswith("python:") for field in ("voting", "movement", "communication", "graph"))
           for g in effective):
        raise ElectionError("leader comparison requires built-in policies and no graph plugins")
    if any(a.group is not None or a.overrides is not None for a in scenario.interventions):
        raise ElectionError("leader comparison excludes scheduled group or policy-override changes")
    arms = {"fixed_no_signal": ("fixed", "none"), "adaptive_no_signal": ("feedback", "none"),
            "fixed_broadcast": ("fixed", "broadcast"), "adaptive_broadcast": ("feedback", "broadcast")}
    clean = ((scenario.alignment is None or scenario.alignment.attack.policy == "none" or
              scenario.alignment.attack.total_budget == 0 or scenario.alignment.attack.per_person_round == 0 or not scenario.alignment.attack.targets)
             and (scenario.signal_controller is None or scenario.signal_controller.policy == "truthful" or
                  scenario.signal_controller.lifetime_budget == 0 or scenario.signal_controller.per_broadcast_budget == 0)
             and (scenario.campaign_controller is None or scenario.campaign_controller.policy == "none" or
                  scenario.campaign_controller.lifetime_budget == 0 or scenario.campaign_controller.per_round_budget == 0)
             and not scenario.coalitions and not scenario.interventions)
    rows = []; run_manifest = None
    for seed in seeds:
        runs = {}
        for arm, (policy, signal_mode) in arms.items():
            raw = scenario.as_dict(); raw["seed"] = seed
            raw["leaders"]["policy"] = policy; raw["leaders"]["signal_mode"] = signal_mode
            selected = None; sim = None; manifest_mismatch = False
            try:
                selected = make_scenario(raw); sim = Simulation(selected)
                if run_manifest is not None and sim.runtime_manifest != run_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between leader runs")
                run_manifest = sim.runtime_manifest; sim.run()
                run = {"status": "ok", "scenario": selected.as_dict(), "nomination": selected.nomination.as_dict(),
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
        for arm, run in runs.items():
            if run["status"] != "ok":
                continue
            baseline_name = "fixed_broadcast" if arm == "adaptive_broadcast" else "fixed_no_signal"
            baseline = runs[baseline_name]; run["baseline"] = baseline_name
            run["movement_matched"] = (None if baseline["status"] != "ok" else
                len(run["frames"]) == len(baseline["frames"]) and
                all(a["positions"] == b["positions"] for a, b in zip(run["frames"], baseline["frames"])))
            run["honest_adaptation_alert"] = (None if not clean or scenario.detector is None else
                                               any(row["detector_alert"] for row in run["metrics"]))
            if not run["movement_matched"]:
                continue
            if arm == "adaptive_no_signal":
                run["nonsignal_invariant"] = all({k: v for k, v in a.items() if k != "leaders"} ==
                                                  {k: v for k, v in b.items() if k != "leaders"}
                                                  for a, b in zip(run["frames"], baseline["frames"]))
            run["paired"] = [{"round": t["round"], "winner_same": t["winner"] == c["winner"],
                              "winner_true_distance_delta": t["mean_winner_true_current_distance"] - c["mean_winner_true_current_distance"],
                              "winner_perceived_distance_delta": t["mean_winner_perceived_current_distance"] - c["mean_winner_perceived_current_distance"],
                              "perception_error_delta": t["mean_leader_perception_error"] - c["mean_leader_perception_error"],
                              "detector_alert": t.get("detector_alert")}
                             for c, t in zip(baseline["metrics"], run["metrics"])]
        rows.append({"seed": seed, "runs": runs})
    return {"record_type": "eclipse.leader-comparison", "record_version": 1, "scenario": scenario.as_dict(),
            "seeds": seeds, "arms": list(arms), "honest_exogenous_configuration": clean,
            "manifest": run_manifest, "rows": rows,
            "notes": ["Adaptive broadcast pairs with fixed broadcast; no-signal feedback pairs with fixed no-signal.",
                      "Broadcast noise streams are coupled by leader/round, but clipping and different hidden positions change realized signals.",
                      "No-signal invariance checks every non-leader frame field, including ballots, communications and detector output.",
                      "Detector false-alarm labeling is only provided when other configured attacks and interventions are absent.",
                      "Failures and unpaired runs remain visible; outcomes are descriptive and not convergence evidence."]}


def _validate_alignment_comparison(scenario):
    if scenario.alignment is None:
        raise ElectionError("alignment comparison requires an alignment scenario")
    if not scenario.alignment.attack.observe_target_ideals:
        raise ElectionError("alignment comparison requires observe_target_ideals permission for the directed arm")
    groups = {group.id: group for group in scenario.groups}
    effective = [apply_overrides(groups[p.group], p.overrides) for p in scenario.people]
    if any(group.movement not in ("stationary", "random_walk") or group.graph != "none"
           or any(getattr(group, field).startswith("python:") for field in ("voting", "movement", "communication", "graph"))
           for group in effective):
        raise ElectionError("alignment comparison requires built-in policies and no graph plugins")
    if any(a.group is not None or a.overrides is not None for a in scenario.interventions):
        raise ElectionError("alignment comparison excludes scheduled group or policy-override changes")


def _detector_episode(frames, attack_arm):
    """Evaluator-only labels; never passed to the aggregate detector."""
    alerts = [f["round"] for f in frames if f["detector"]["alert"]]
    t3 = frames[-1]["detector"]["first_triple_win_round"]
    if not attack_arm:
        return {"false_alarm": bool(alerts), "alert_rounds": alerts, "first_triple_win_round": t3}
    onset = next((f["round"] for f in frames if any(c["attack_cost"] > 0 for c in f["alignment"]["changes"])), None)
    if onset is None:
        return {"realized_attack": False, "onset": None, "alert_rounds": alerts, "first_triple_win_round": t3,
                "post_onset_alert": None, "detection_delay": None, "pre_t3_alert": None, "pre_t3_eligible": False}
    post = [t for t in alerts if t >= onset]
    eligible = t3 is not None and t3 > onset
    return {"realized_attack": True, "onset": onset, "alert_rounds": alerts,
            "pre_onset_alert": any(t < onset for t in alerts), "first_triple_win_round": t3,
            "post_onset_alert": bool(post), "detection_delay": post[0] - onset if post else None,
            "pre_t3_alert": (any(t < t3 for t in post) if eligible else None), "pre_t3_eligible": eligible}


def calibrate_and_evaluate_detector(scenario: Scenario, calibration_seeds: list[int],
                                    evaluation_seeds: list[int], false_alarm_rate: float) -> dict:
    """Freeze an empirical episode-level threshold before disjoint-seed evaluation."""
    if scenario.alignment is None or scenario.detector is None:
        raise ElectionError("detector calibration requires alignment and detector configurations")
    if scenario.detector.target != scenario.alignment.attack.target:
        raise ElectionError("detector evaluation requires the monitored and alignment attack targets to match")
    if scenario.rounds < 1:
        raise ElectionError("detector calibration requires at least one comparison round")
    if (not isinstance(calibration_seeds, list) or not isinstance(evaluation_seeds, list)
            or not calibration_seeds or not evaluation_seeds
            or any(type(s) is not int or s < 0 for s in calibration_seeds + evaluation_seeds)
            or len(set(calibration_seeds)) != len(calibration_seeds)
            or len(set(evaluation_seeds)) != len(evaluation_seeds)
            or set(calibration_seeds) & set(evaluation_seeds)):
        raise ElectionError("calibration and evaluation seeds must be nonempty, unique and disjoint")
    if (isinstance(false_alarm_rate, bool) or not isinstance(false_alarm_rate, (int, float))
            or not math.isfinite(false_alarm_rate) or not 0 <= false_alarm_rate < 1):
        raise ElectionError("false_alarm_rate must be finite in [0, 1)")
    _validate_alignment_comparison(scenario)
    records = []; maxima = []; run_manifest = None
    for seed in calibration_seeds:
        raw = scenario.as_dict(); raw["seed"] = seed
        raw["alignment"]["attack"]["policy"] = "none"
        raw["detector"]["threshold"] = 1.0
        selected = None; sim = None; manifest_mismatch = False
        try:
            selected = make_scenario(raw); sim = Simulation(selected)
            if run_manifest is not None and sim.runtime_manifest != run_manifest:
                manifest_mismatch = True
                raise ElectionError("runtime or core source changed during detector calibration")
            run_manifest = sim.runtime_manifest
            sim.run()
            metrics = series(selected, sim.frames)
            maximum = max(0.0, *(row["detector_share_change"] for row in metrics[1:]))
            maxima.append(maximum)
            records.append({"seed": seed, "status": "ok", "scenario": selected.as_dict(),
                            "max_share_increase": maximum, "frames": [f.as_dict() for f in sim.frames], "metrics": metrics,
                            "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()}})
        except ElectionError as exc:
            if manifest_mismatch:
                raise
            records.append({"seed": seed, "status": "failed", "scenario": selected.as_dict() if selected else raw,
                            "error": str(exc), "completed_round": sim.current.round if sim else None,
                            "frames": [f.as_dict() for f in sim.frames] if sim else [],
                            "metrics": series(selected, sim.frames) if sim else [],
                            "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()} if sim else {}})
    result = {"record_type": "eclipse.detector-evaluation", "record_version": 1, "scenario": scenario.as_dict(),
              "calibration_seeds": calibration_seeds, "evaluation_seeds": evaluation_seeds,
              "requested_false_alarm_rate": false_alarm_rate, "manifest": run_manifest,
              "calibration": records, "threshold": None, "evaluation": None,
              "notes": ["Calibration disables only alignment attacks; all other configured mechanisms remain active.",
                        "Threshold is an empirical order statistic of per-episode maximum positive share increase; alerts use strict >.",
                        "Threshold is frozen before disjoint evaluation. This is not a population false-alarm guarantee.",
                        "Attack labels/onsets are computed only by the evaluator from realized costs; the detector sees aggregates alone.",
                        "Overall recall includes all realized attacks, including failures and no-triple-win runs; pre-t3 recall is conditional on t3 > onset."]}
    if len(maxima) != len(calibration_seeds):
        result["status"] = "calibration_failed"
        return result
    ordered = sorted(maxima)
    index = max(0, min(len(ordered)-1, math.ceil((1 - false_alarm_rate) * len(ordered)) - 1))
    threshold = ordered[index]
    result["threshold"] = threshold
    result["calibration_empirical_false_alarm_rate"] = sum(value > threshold for value in maxima) / len(maxima)
    frozen_raw = scenario.as_dict(); frozen_raw["detector"]["threshold"] = threshold
    frozen = make_scenario(frozen_raw)
    evaluation = compare_alignment(frozen, evaluation_seeds)
    if run_manifest is not None and evaluation["manifest"] is not None and run_manifest != evaluation["manifest"]:
        raise ElectionError("runtime or core source changed between calibration and evaluation")
    totals = {}
    for arm in evaluation["arms"]:
        runs = [row["runs"][arm] for row in evaluation["rows"]]
        completed = []
        for run in runs:
            if run["status"] == "ok":
                episode = _detector_episode(run["frames"], arm in ("targeted_with_drift", "random_with_drift"))
                run["detector_evaluation"] = episode
                completed.append(episode)
        summary = {"requested": len(runs), "completed": len(completed), "failed": len(runs) - len(completed),
                   "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs)}
        if arm in ("no_drift_no_attack", "drift_only"):
            false_alarms = sum(e["false_alarm"] for e in completed)
            summary.update(false_alarm_episodes=false_alarms,
                           false_alarm_rate=false_alarms / len(completed) if completed else None)
        else:
            realized = [e for e in completed if e["realized_attack"]]
            detected = [e for e in realized if e["post_onset_alert"]]
            eligible = [e for e in realized if e["pre_t3_eligible"]]
            early = sum(e["pre_t3_alert"] for e in eligible)
            summary.update(realized_attack_episodes=len(realized), no_realized_attack_episodes=len(completed)-len(realized),
                           detected_episodes=len(detected), recall=len(detected)/len(realized) if realized else None,
                           pre_onset_alert_episodes=sum(e["pre_onset_alert"] for e in realized),
                           no_triple_win_censored=sum(e["first_triple_win_round"] is None for e in realized),
                           triple_at_or_before_onset=sum(e["first_triple_win_round"] is not None and not e["pre_t3_eligible"] for e in realized),
                           pre_t3_eligible_episodes=len(eligible), pre_t3_detected_episodes=early,
                           pre_t3_recall=early/len(eligible) if eligible else None,
                           detection_delays=[e["detection_delay"] for e in detected],
                           delay_censored=len(realized)-len(detected))
        totals[arm] = summary
    incomplete = any(summary["failed"] or summary["unpaired"] for summary in totals.values())
    result.update(status="evaluation_incomplete" if incomplete else "ok", evaluation=evaluation, summary=totals)
    return result


def compare_alignment(scenario: Scenario, seeds: list[int]) -> dict:
    """Paired no-drift, drift-only, directed and random influence controls."""
    _validate_alignment_comparison(scenario)
    if not isinstance(seeds, list) or not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("alignment comparison seeds must be unique nonnegative integers")
    arms = ("no_drift_no_attack", "drift_only", "targeted_with_drift", "random_with_drift")
    rows = []; run_manifest = None
    for seed in seeds:
        runs = {}
        for arm in arms:
            raw = scenario.as_dict(); raw["seed"] = seed
            raw["alignment"]["attack"]["policy"] = ("toward_target" if arm == "targeted_with_drift" else
                                                       "random" if arm == "random_with_drift" else "none")
            if arm == "no_drift_no_attack":
                raw["alignment"]["drift_max_step"] = 0
            selected = None; sim = None; manifest_mismatch = False
            try:
                selected = make_scenario(raw); sim = Simulation(selected)
                if run_manifest is not None and run_manifest != sim.runtime_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between alignment runs")
                run_manifest = sim.runtime_manifest
                sim.run()
                run = {"status": "ok", "scenario": selected.as_dict(),
                       "nomination": selected.nomination.as_dict(),
                       "frames": [f.as_dict() for f in sim.frames], "metrics": series(selected, sim.frames),
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()}}
            except ElectionError as exc:
                if manifest_mismatch:
                    raise
                run = {"status": "failed", "scenario": selected.as_dict() if selected is not None else raw,
                       "error": str(exc), "completed_round": sim.current.round if sim is not None else None,
                       "frames": [f.as_dict() for f in sim.frames] if sim is not None else [],
                       "metrics": series(selected, sim.frames) if sim is not None else [],
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()} if sim is not None else {}}
            runs[arm] = run
        for arm, run in runs.items():
            if run["status"] != "ok":
                continue
            baseline_name = "no_drift_no_attack" if arm == "drift_only" else "drift_only"
            baseline = runs[baseline_name]
            run["baseline"] = baseline_name
            run["movement_matched"] = (None if baseline["status"] != "ok" else
                len(run["frames"]) == len(baseline["frames"]) and
                all(a["positions"] == b["positions"] for a, b in zip(run["frames"], baseline["frames"])))
            if not run["movement_matched"]:
                continue
            target = scenario.alignment.attack.target
            def margin(row):
                return row["counts"][target] - max((v for p, v in row["counts"].items() if p != target), default=0)
            run["paired"] = [{"round": t["round"], "target_win_delta": int(t["winner"] == target) - int(c["winner"] == target),
                              "target_share_delta": t["shares"][target] - c["shares"][target],
                              "target_margin_delta": margin(t) - margin(c),
                              "current_winner_distance_delta": t["mean_winner_current_ideal_distance"] - c["mean_winner_current_ideal_distance"],
                              "initial_winner_distance_delta": t["mean_winner_ideal_distance"] - c["mean_winner_ideal_distance"],
                              "attack_spend": t["alignment_attack_spend"]}
                             for c, t in zip(baseline["metrics"], run["metrics"])]
        rows.append({"seed": seed, "runs": runs})
    return {"record_type": "eclipse.alignment-comparison", "record_version": 1, "scenario": scenario.as_dict(),
            "seeds": seeds, "arms": list(arms), "manifest": run_manifest, "rows": rows,
            "notes": ["No-drift/no-attack and drift-only are controls; attacks pair with drift-only under equal allowed budgets.",
                      "Drift and random attack use distinct person-round keyed streams; clipping and prior attacks can change realized drift paths.",
                      "Attack target scope and permissions are fixed. Realized spending can differ after clipping or target saturation.",
                      "Other enabled mechanisms may respond endogenously. Failures and unpaired runs remain visible; no convergence claim."]}


def compare_nominations(scenario: Scenario, seeds: list[int]) -> dict:
    """Compare endogenous, identical fixed and equal-size random nominee sets."""
    if scenario.nomination is None:
        raise ElectionError("nomination comparison requires a nomination scenario")
    if not isinstance(seeds, list) or not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("nomination comparison seeds must be unique nonnegative integers")
    groups = {group.id: group for group in scenario.groups}
    effective = [apply_overrides(groups[p.group], p.overrides) for p in scenario.people]
    if any(group.movement not in ("stationary", "random_walk") or group.graph != "none"
           or any(getattr(group, field).startswith("python:") for field in ("voting", "movement", "communication", "graph"))
           for group in effective):
        raise ElectionError("nomination comparison requires built-in movement, voting and communication, and no graph plugins")
    if any(action.group is not None or action.overrides is not None for action in scenario.interventions):
        raise ElectionError("nomination comparison excludes scheduled group or policy-override changes")
    rows = []; run_manifest = None
    for seed in seeds:
        runs = {}
        for mode in ("endogenous", "fixed", "random"):
            raw = scenario.as_dict(); raw["seed"] = seed
            raw["nomination"]["mode"] = mode
            raw["nomination"].pop("nominees", None)
            if mode == "fixed":
                base = runs["endogenous"].get("nomination")
                if base is None:
                    runs[mode] = {"status": "failed", "scenario": None, "error": "endogenous nominee selection unavailable",
                                  "completed_round": None, "frames": [], "metrics": [], "policy_digests": {}}
                    continue
                raw["nomination"]["nominees"] = list(base["nominees"])
            selected = None; sim = None; manifest_mismatch = False
            try:
                selected = make_scenario(raw)
                sim = Simulation(selected)
                if run_manifest is not None and run_manifest != sim.runtime_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between nomination runs")
                run_manifest = sim.runtime_manifest
                sim.run()
                run = {"status": "ok", "scenario": selected.as_dict(), "nomination": selected.nomination.as_dict(),
                       "frames": [f.as_dict() for f in sim.frames], "metrics": series(selected, sim.frames),
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()}}
            except ElectionError as exc:
                if manifest_mismatch:
                    raise
                run = {"status": "failed", "scenario": selected.as_dict() if selected is not None else raw,
                       "error": str(exc), "completed_round": sim.current.round if sim is not None else None,
                       "frames": [f.as_dict() for f in sim.frames] if sim is not None else [],
                       "metrics": series(selected, sim.frames) if sim is not None else [],
                       "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()} if sim is not None else {}}
                if selected is not None:
                    run["nomination"] = selected.nomination.as_dict()
            runs[mode] = run
        control = runs["endogenous"]
        for run in runs.values():
            if run["status"] != "ok":
                continue
            run["movement_matched"] = (None if control["status"] != "ok" else
                len(run["frames"]) == len(control["frames"]) and
                all(a["positions"] == b["positions"] for a, b in zip(run["frames"], control["frames"])))
            if not run["movement_matched"]:
                continue
            run["same_nominees"] = run["nomination"]["nominees"] == control["nomination"]["nominees"]
            run["same_frames"] = run["frames"] == control["frames"]
            run["paired"] = [{"round": t["round"], "winner_same": t["winner"] == c["winner"],
                              "winner_ideal_distance_delta": t["mean_winner_ideal_distance"] - c["mean_winner_ideal_distance"],
                              "nearest_nominee_distance_delta": t["mean_nearest_nominee_distance"] - c["mean_nearest_nominee_distance"]}
                             for c, t in zip(control["metrics"], run["metrics"])]
        rows.append({"seed": seed, "runs": runs})
    return {"record_type": "eclipse.nomination-comparison", "record_version": 1, "scenario": scenario.as_dict(),
            "seeds": seeds, "manifest": run_manifest, "rows": rows,
            "notes": ["Fixed control uses exactly the endogenous nominees and party-ID order; nomination records are not policy observations.",
                      "Random control selects the same number of eligible people with a separate seed-keyed stream.",
                      "The identity of a winner cannot be compared as a fixed target when candidate sets differ.",
                      "Configured target-specific mechanisms may fail when their target is not nominated; failures remain visible.",
                      "Distances use fixed initial voter ideals and fixed nominee positions; differences are descriptive, not convergence evidence."]}


def compare_signal_responses(scenario: Scenario, seeds: list[int], groups: list[str],
                             signal_distortion_bound: int, max_worlds: int = 10000) -> dict:
    """Pair truthful/random/targeted reports within each selected voter response."""
    controller = scenario.signal_controller
    if controller is None:
        raise ElectionError("signal comparison requires a signal_controller")
    if not isinstance(seeds, list) or not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("signal comparison seeds must be unique nonnegative integers")
    group_map = {group.id: group for group in scenario.groups}
    occupied = {person.group for person in scenario.people}
    if (not isinstance(groups, list) or not groups or any(not isinstance(g, str) for g in groups)
            or len(set(groups)) != len(groups) or not set(groups) <= occupied):
        raise ElectionError("signal comparison groups must be unique occupied group IDs")
    if type(signal_distortion_bound) is not int or not 0 <= signal_distortion_bound <= 1000000:
        raise ElectionError("signal_distortion_bound must be an integer in [0, 1000000]")
    required = 0 if len(scenario.parties) == 1 else min(controller.per_broadcast_budget, controller.lifetime_budget, len(scenario.people))
    if signal_distortion_bound < required:
        raise ElectionError(f"signal_distortion_bound must be at least the comparison controller bound {required}")
    if type(max_worlds) is not int or not 1 <= max_worlds <= 1000000:
        raise ElectionError("max_worlds must be an integer in [1, 1000000]")
    if any(action.group is not None or action.overrides is not None for action in scenario.interventions):
        raise ElectionError("signal comparison excludes scheduled group or policy-override changes")
    effective = [apply_overrides(group_map[person.group], person.overrides) for person in scenario.people]
    if any(group.movement not in ("stationary", "random_walk") or group.graph != "none"
           or any(getattr(group, field).startswith("python:") for field in ("voting", "movement", "communication", "graph"))
           for group in effective):
        raise ElectionError("signal comparison requires built-in movement, voting and communication, and no graph plugins")
    for person, group in zip(scenario.people, effective):
        if person.group not in groups:
            continue
        override = json.loads(person.overrides)
        if "voting" in override or "parameters" in override:
            raise ElectionError("signal comparison excludes selected-person voting or parameter overrides")
        if not group.capabilities.observe_public_signal or not group.capabilities.observe_electorate:
            raise ElectionError("selected voters require public-signal and electorate permissions for all arms")
    responses = ("sincere", "signal_confident", "epistemic_signal_dominant")
    policies = ("truthful", "bounded_random", "target_biased")
    rows = []
    run_manifest = None
    for seed in seeds:
        runs = {}
        for response in responses:
            runs[response] = {}
            for policy_name in policies:
                raw = scenario.as_dict()
                raw["seed"] = seed
                raw["signal_controller"]["policy"] = policy_name
                for group in groups:
                    raw["groups"][group]["voting"] = response
                    raw["groups"][group]["parameters"]["voting"] = (
                        {"signal_distortion_bound": signal_distortion_bound, "max_worlds": max_worlds}
                        if response == "epistemic_signal_dominant" else {})
                sim = None
                manifest_mismatch = False
                try:
                    selected = make_scenario(raw)
                    sim = Simulation(selected)
                    if run_manifest is not None and sim.runtime_manifest != run_manifest:
                        manifest_mismatch = True
                        raise ElectionError("runtime or core source changed between signal runs")
                    run_manifest = sim.runtime_manifest
                    sim.run()
                    run = {"status": "ok", "scenario": selected.as_dict(),
                           "frames": [frame.as_dict() for frame in sim.frames], "metrics": series(selected, sim.frames),
                           "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()}}
                except ElectionError as exc:
                    if manifest_mismatch:
                        raise
                    run = {"status": "failed", "scenario": raw, "error": str(exc),
                           "completed_round": sim.current.round if sim is not None else None,
                           "frames": [frame.as_dict() for frame in sim.frames] if sim is not None else [],
                           "metrics": series(sim.scenario, sim.frames) if sim is not None else [],
                           "policy_digests": {name: digest for name, (_, digest, _) in sim.plugins.items()} if sim is not None else {}}
                runs[response][policy_name] = run
            control = runs[response]["truthful"]
            for run in runs[response].values():
                if run["status"] != "ok":
                    continue
                run["movement_matched"] = (None if control["status"] != "ok" else
                    len(run["frames"]) == len(control["frames"]) and
                    all(a["positions"] == b["positions"] for a, b in zip(run["frames"], control["frames"])))
                if not run["movement_matched"]:
                    continue
                target = controller.target
                def margin(row):
                    return row["counts"][target] - max((value for candidate, value in row["counts"].items() if candidate != target), default=0)
                run["paired"] = [{"round": t["round"], "target_won": t["winner"] == target,
                                  "target_win_delta": int(t["winner"] == target) - int(c["winner"] == target),
                                  "target_share_delta": t["shares"][target] - c["shares"][target],
                                  "target_margin_delta": margin(t) - margin(c),
                                  "ballot_switch_delta": (None if t["ballot_switch_count"] is None else
                                                          t["ballot_switch_count"] - c["ballot_switch_count"]),
                                  "signal_broadcast_cost": t["signal_broadcast_cost"],
                                  "signal_spend": t["signal_spend"]}
                                 for c, t in zip(control["metrics"], run["metrics"])]
        for response in responses:
            for policy_name in policies:
                run = runs[response][policy_name]
                control = runs["sincere"][policy_name]
                if run["status"] != "ok":
                    continue
                run["response_movement_matched"] = (None if control["status"] != "ok" else
                    len(run["frames"]) == len(control["frames"]) and
                    all(a["positions"] == b["positions"] for a, b in zip(run["frames"], control["frames"])))
                if not run["response_movement_matched"]:
                    continue
                target = controller.target
                def margin(row):
                    return row["counts"][target] - max((value for candidate, value in row["counts"].items() if candidate != target), default=0)
                run["response_paired"] = [{"round": t["round"],
                                           "target_win_delta": int(t["winner"] == target) - int(c["winner"] == target),
                                           "target_share_delta": t["shares"][target] - c["shares"][target],
                                           "target_margin_delta": margin(t) - margin(c),
                                           "ballot_switch_delta": (None if t["ballot_switch_count"] is None else
                                                                   t["ballot_switch_count"] - c["ballot_switch_count"]),
                                           "signal_report_equal": (None if t["signal_report"] is None or c["signal_report"] is None
                                                                   else t["signal_report"] == c["signal_report"] and
                                                                   t["signal_source_round"] == c["signal_source_round"] and
                                                                   t["signal_broadcast_round"] == c["signal_broadcast_round"]),
                                           "signal_source_truth_equal": (None if t["signal_source_truth"] is None or c["signal_source_truth"] is None
                                                                         else t["signal_source_truth"] == c["signal_source_truth"])}
                                          for c, t in zip(control["metrics"], run["metrics"])]
        rows.append({"seed": seed, "runs": runs})
    return {"record_type": "eclipse.signal-comparison", "record_version": 1, "scenario": scenario.as_dict(),
            "groups": groups, "seeds": seeds, "target": controller.target, "responses": list(responses),
            "signal_policies": list(policies), "signal_distortion_bound": signal_distortion_bound,
            "max_worlds": max_worlds, "manifest": run_manifest, "rows": rows,
            "notes": ["Within each response, truthful report is the paired baseline; allowed budgets are equal.",
                      "Within each signal policy, the sincere response is the response_paired baseline; signal equality is checked per round.",
                      "Selected groups retain permissions, but sincere, trusting and epistemic policies use information differently.",
                      "Prior vote differences can change later reports, networks and other mechanisms; reports need not match across responses.",
                      "Movement is checked; failed and unpaired runs are retained. Outcomes are descriptive, not convergence evidence."]}


def exhaustive_one_round_campaign(scenario: Scenario, max_combinations: int = 10000) -> dict:
    """Exact evaluator-only upper bounds for one-round stationary edge selection."""
    controller = scenario.campaign_controller
    if controller is None:
        raise ElectionError("exhaustive campaign evaluation requires a campaign_controller")
    if scenario.rounds != 1 or len(scenario.people) > 8 or scenario.interventions:
        raise ElectionError("exhaustive campaign evaluation requires one round, at most 8 voters and no interventions")
    if type(max_combinations) is not int or not 1 <= max_combinations <= 100000:
        raise ElectionError("max_combinations must be an integer in [1, 100000]")
    groups = {group.id:group for group in scenario.groups}
    effective = [apply_overrides(groups[person.group],person.overrides) for person in scenario.people]
    if any(group.movement != "stationary" or group.graph != "none" or
           any(getattr(group,field).startswith("python:") for field in ("voting","movement","graph","communication"))
           for group in (*scenario.groups,*effective)):
        raise ElectionError("exhaustive campaign evaluation requires stationary movement, no graph actions and no plugins")
    baseline = Simulation(replace(scenario,campaign_controller=replace(controller,policy="none")))
    initial = baseline.current
    public_edges = set(initial.persistent_edges) | set(initial.proximity_edges) | set(initial.campaign_edges)
    budget = min(controller.lifetime_budget,controller.per_round_budget)
    if budget:
        probe = replace(controller,policy="target_heuristic")
        eligible, _ = select_campaign_edges(probe,{person:ballot[0] for person,ballot in initial.ballots},
                                             public_edges,set(),None)
        eligible_report = [list(edge) for edge in eligible]
    else:
        eligible = ()
        eligible_report = None
    budget = min(budget,len(eligible))
    count = sum(math.comb(len(eligible),size) for size in range(budget+1))
    if count > max_combinations:
        raise ElectionError("exhaustive campaign evaluation exceeds max_combinations")
    best_votes = -1; votes_witness = None; target_witness = None
    records = []
    for size in range(budget+1):
        for chosen in itertools.combinations(eligible,size):
            selected = replace(scenario, campaign_controller=replace(controller,policy="none"),
                               campaign_edges=tuple(sorted(set(scenario.campaign_edges) | set(chosen))))
            sim = Simulation(selected)
            if sim.runtime_manifest != baseline.runtime_manifest:
                raise ElectionError("runtime or core source changed between evaluator runs")
            sim.step()
            votes = dict(sim.current.counts)[controller.target]
            target_won = sim.current.winner == controller.target
            record = {"edges":[list(edge) for edge in chosen], "cost":len(chosen),
                      "target_votes":votes, "winner":sim.current.winner, "target_won":target_won}
            records.append(record)
            if votes > best_votes:
                best_votes = votes; votes_witness = record
            if target_won and target_witness is None:
                target_witness = record
    return {"record_type":"eclipse.campaign-one-round-exhaustive", "record_version":1,
            "scenario":scenario.as_dict(), "manifest":baseline.runtime_manifest, "target":controller.target,
            "eligible":eligible_report, "budget":budget, "combinations_checked":count,
            "max_target_votes":best_votes, "target_win_possible":target_witness is not None,
            "max_votes_witness":votes_witness, "target_win_witness":target_witness, "records":records,
            "notes":["Exact only for one-round stationary, intervention-free, no-plugin cases and the controller's eligible-edge rule.",
                     "Evaluator preinstalls each chosen set; with no prior graph-dependent phases this matches round-one action visibility.",
                     "Full-outcome search is evaluator-only and is not available to agents or the controller.",
                     "Not an upper bound for later adaptive additions, different eligible edges or other model domains."]}


def compare_campaign_policies(scenario: Scenario, seeds: list[int]) -> dict:
    """Matched no-addition, random and target-directed campaign controllers."""
    controller = scenario.campaign_controller
    if controller is None:
        raise ElectionError("campaign comparison requires a campaign_controller")
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("campaign comparison seeds must be unique nonnegative integers")
    if any(action.group is not None or action.overrides is not None for action in scenario.interventions):
        raise ElectionError("campaign comparison excludes scheduled group or policy-override changes")
    groups = {group.id:group for group in scenario.groups}
    effective = [apply_overrides(groups[person.group],person.overrides) for person in scenario.people]
    if any(group.movement not in ("stationary","random_walk") or group.graph != "none" for group in effective):
        raise ElectionError("campaign comparison requires built-in movement and no graph-policy plugins")
    policies = ("none", "random", "target_heuristic")
    rows = []; run_manifest = None
    for seed in seeds:
        runs = {}; simulations = {}
        for name in policies:
            selected = replace(scenario, seed=seed, campaign_controller=replace(controller,policy=name))
            sim = None; manifest_mismatch = False
            try:
                sim = Simulation(selected)
                if run_manifest is not None and sim.runtime_manifest != run_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between campaign runs")
                run_manifest = sim.runtime_manifest
                sim.run()
                runs[name] = {"status":"ok", "scenario":selected.as_dict(),
                              "frames":[frame.as_dict() for frame in sim.frames],
                              "metrics":series(selected,sim.frames),
                              "policy_digests":{key:digest for key,(_,digest,_) in sim.plugins.items()}}
                simulations[name] = sim
            except ElectionError as exc:
                if manifest_mismatch: raise
                runs[name] = {"status":"failed", "scenario":selected.as_dict(),"error":str(exc),
                              "completed_round":sim.current.round if sim is not None else None,
                              "frames":[frame.as_dict() for frame in sim.frames] if sim is not None else [],
                              "metrics":series(selected,sim.frames) if sim is not None else [],
                              "policy_digests":{key:digest for key,(_,digest,_) in sim.plugins.items()} if sim is not None else {}}
        baseline = simulations.get("none")
        for name, sim in simulations.items():
            runs[name]["movement_matched"] = (None if baseline is None else
                all(a.positions == b.positions for a,b in zip(sim.frames,baseline.frames)))
            if baseline is None or not runs[name]["movement_matched"]:
                continue
            paired = []
            for control, treated in zip(runs["none"]["metrics"],runs[name]["metrics"]):
                target = controller.target
                def margin(row):
                    return row["counts"][target] - max((row["counts"][party] for party in scenario.parties if party != target),default=0)
                paired.append({"round":treated["round"],
                               "target_won":treated["winner"] == target,
                               "target_win_delta":int(treated["winner"] == target)-int(control["winner"] == target),
                               "target_share_delta":treated["shares"][target]-control["shares"][target],
                               "target_margin_delta":margin(treated)-margin(control),
                               "controller_spend":treated["campaign_controller_spend"]})
            runs[name]["paired"] = paired
        rows.append({"seed":seed,"runs":runs})
    return {"record_type":"eclipse.campaign-comparison", "record_version":1,
            "scenario":scenario.as_dict(), "target":controller.target, "seeds":seeds,
            "policies":list(policies), "manifest":run_manifest, "rows":rows,
            "notes":["All policies have identical allowed budgets; realized spending can differ.",
                     "Random and target heuristic use the same eligible-edge rule but can face different future states.",
                     "Movement trajectories are checked against no-addition; failed runs are retained.",
                     "Per-round paired outcomes are descriptive, not a convergence or causal guarantee."]}


def coalition_ablations(scenario: Scenario, seeds: list[int]) -> dict:
    """Matched zero-capability, single-capability and combined coalition runs."""
    if not scenario.coalitions:
        raise ElectionError("coalition ablations require at least one coalition")
    if scenario.campaign_controller is not None:
        raise ElectionError("coalition ablations exclude campaign controllers")
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("ablation seeds must be unique nonnegative integers")
    if any(action.group is not None or action.overrides is not None for action in scenario.interventions):
        raise ElectionError("coalition ablations exclude scheduled group or policy-override changes")
    group_map = {group.id:group for group in scenario.groups}
    effective = [apply_overrides(group_map[person.group],person.overrides) for person in scenario.people]
    if any(group.movement not in ("stationary","random_walk") or group.graph != "none" for group in effective):
        raise ElectionError("coalition ablations require built-in movement and no graph-policy plugins")
    arms = {"none":(), "sight_only":("sight",), "deception_only":("deception",),
            "eavesdrop_only":("eavesdrop",), "coordination_only":("coordination",),
            "all":("sight","deception","eavesdrop","coordination")}
    members = {member for coalition in scenario.coalitions for member in coalition.members}
    raw_scenario = scenario.as_dict()
    def configured(enabled):
        import copy
        raw = copy.deepcopy(raw_scenario)
        for coalition in raw["coalitions"]:
            for feature, fields in (("deception",("report_budget_per_round","report_budget_total")),
                                    ("sight",("sight_budget_per_round","sight_budget_total")),
                                    ("eavesdrop",("eavesdrop_budget_per_round","eavesdrop_budget_total"))):
                if feature not in enabled:
                    for field in fields:
                        if field in coalition: coalition[field] = 0
        if "coordination" not in enabled:
            for person in raw["people"]:
                if person["id"] in members:
                    capabilities = person["overrides"].setdefault("capabilities", {})
                    capabilities.update(send_private_reports=False, receive_private_reports=False)
        return make_scenario(raw)
    configurations = {name:configured(enabled) for name,enabled in arms.items()}
    rows = []; run_manifest = None
    for seed in seeds:
        runs = {}; simulations = {}
        for arm, enabled in arms.items():
            selected = replace(configurations[arm], seed=seed)
            sim = None; manifest_mismatch = False
            try:
                sim = Simulation(selected)
                if run_manifest is not None and sim.runtime_manifest != run_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between ablation runs")
                run_manifest = sim.runtime_manifest
                sim.run()
                runs[arm] = {"status":"ok", "scenario":selected.as_dict(),
                             "metrics":series(selected,sim.frames),
                             "frames":[frame.as_dict() for frame in sim.frames],
                             "policy_digests":{name:digest for name,(_,digest,_) in sim.plugins.items()}}
                simulations[arm] = sim
            except ElectionError as exc:
                if manifest_mismatch: raise
                runs[arm] = {"status":"failed", "scenario":selected.as_dict(), "error":str(exc),
                             "completed_round":sim.current.round if sim is not None else None,
                             "metrics":series(selected,sim.frames) if sim is not None else [],
                             "frames":[frame.as_dict() for frame in sim.frames] if sim is not None else [],
                             "policy_digests":{name:digest for name,(_,digest,_) in sim.plugins.items()} if sim is not None else {}}
        baseline = simulations.get("none")
        for arm, sim in simulations.items():
            runs[arm]["movement_matched"] = (None if baseline is None else
                all(a.positions == b.positions for a,b in zip(sim.frames,baseline.frames)))
            if baseline is None or not runs[arm]["movement_matched"]:
                continue
            metrics, controls = runs[arm]["metrics"], runs["none"]["metrics"]
            target_results = {}
            for coalition in scenario.coalitions:
                target = coalition.target
                def margin(row):
                    return row["counts"][target] - max((row["counts"][party] for party in scenario.parties if party != target),default=0)
                target_results[coalition.id] = {"target":target,
                    "target_won":metrics[-1]["winner"] == target,
                    "paired_target_win_delta":int(metrics[-1]["winner"] == target) - int(controls[-1]["winner"] == target),
                    "paired_target_share_delta":metrics[-1]["shares"][target] - controls[-1]["shares"][target],
                    "paired_target_margin_delta":margin(metrics[-1]) - margin(controls[-1])}
            runs[arm]["paired_targets"] = target_results
        rows.append({"seed":seed, "runs":runs})
    return {"record_type":"eclipse.coalition-ablations", "record_version":1,
            "scenario":raw_scenario, "seeds":seeds, "arms":{name:list(enabled) for name,enabled in arms.items()},
            "manifest":run_manifest, "rows":rows,
            "notes":["Disabled deception, sight and interception use zero budgets; coordination disables coalition members' private report send/receive permissions.",
                     "Single-capability arms retain only the named configured capability; all retains the original configuration.",
                     "Coordination changes private reports only; channel membership and separately enabled sensing are unchanged.",
                     "Movement positions are checked against the no-capability arm. Failed runs are retained without imputation.",
                     "Metrics are descriptive at the configured horizon; a quiet period is not a convergence proof."]}


def _matched_static_edges(frames, people):
    """Minimize per-receiver cumulative exposure L1; ties favor smaller degree."""
    horizon = len(frames) - 1
    if horizon < 1:
        raise ElectionError("matched static control requires at least one simulated round")
    frequencies = {person.id:{} for person in people}
    for frame in frames[1:]:
        for sender, receiver in frame.proximity_edges:
            counts = frequencies[receiver]
            counts[sender] = counts.get(sender, 0) + 1
    edges = []
    for receiver in sorted(frequencies):
        counts = frequencies[receiver]
        lower, remainder = divmod(sum(counts.values()), horizon)
        degree = lower + int(2 * remainder > horizon)
        ranked = sorted(counts, key=lambda sender: (-counts[sender], sender))
        edges.extend((sender, receiver) for sender in ranked[:degree])
    return tuple(sorted(edges))


def compare_proximity(scenario: Scenario, seeds: list[int], calibration_seeds: list[int] | None = None) -> dict:
    """Paired dynamic/frozen and separately calibrated static contacts."""
    if scenario.campaign_controller is not None:
        raise ElectionError("network comparison excludes campaign controllers")
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("comparison seeds must be unique nonnegative integers")
    if calibration_seeds is not None and (len(calibration_seeds) != len(seeds)
            or any(type(seed) is not int or seed < 0 for seed in calibration_seeds)
            or len(set(calibration_seeds)) != len(calibration_seeds) or set(seeds) & set(calibration_seeds)):
        raise ElectionError("calibration seeds must be unique, disjoint from evaluation seeds and paired one-to-one")
    if calibration_seeds is not None and any(a.position is not None or a.group is not None or a.overrides is not None
                                              for a in scenario.interventions):
        raise ElectionError("static calibration excludes scheduled position, group or override changes")
    groups = {group.id: group for group in scenario.groups}
    settings = {person.id:(person.group, person.overrides) for person in scenario.people}
    candidates = [apply_overrides(groups[group], overrides) for group,overrides in settings.values()]
    for action in scenario.interventions:
        group, overrides = settings[action.person]
        group = action.group if action.group is not None else group
        overrides = action.overrides if action.overrides is not None else overrides
        settings[action.person] = group, overrides
        candidates.append(apply_overrides(groups[group], overrides))
    if any(group.movement not in ("stationary", "random_walk") or group.graph != "none" for group in candidates):
        raise ElectionError("network comparison requires built-in movement and no graph-policy plugins")
    rows = []; run_manifest = None
    for index, seed in enumerate(seeds):
        outcomes = {}; simulations = {}
        for mode in ("dynamic", "frozen"):
            selected = replace(scenario, seed=seed, proximity_mode=mode, static_proximity_edges=())
            sim = None; manifest_mismatch = False
            try:
                sim = Simulation(selected)
                if run_manifest is not None and sim.runtime_manifest != run_manifest:
                    manifest_mismatch = True
                    raise ElectionError("runtime or core source changed between comparison runs")
                run_manifest = sim.runtime_manifest
                sim.run()
                outcomes[mode] = {"status":"ok", "metrics":series(selected,sim.frames),
                                  "policy_digests":{name:digest for name,(_,digest,_) in sim.plugins.items()}}
                simulations[mode] = sim
            except ElectionError as exc:
                if manifest_mismatch:
                    raise
                outcomes[mode] = {"status":"failed", "error":str(exc),
                                  "completed_round":sim.current.round if sim is not None else None}
        row = {"seed":seed, "dynamic":outcomes["dynamic"], "frozen":outcomes["frozen"]}
        if len(simulations) == 2:
            dynamic, frozen = simulations["dynamic"], simulations["frozen"]
            same_positions = all(a.positions == b.positions for a,b in zip(dynamic.frames,frozen.frames))
            row["movement_matched"] = same_positions
            row["status"] = "ok" if same_positions else "movement_mismatch"
            counts = {}
            for mode, sim in simulations.items():
                exposure = {person.id:0 for person in scenario.people}
                for frame in sim.frames[1:]:
                    for _, receiver in frame.proximity_edges:
                        exposure[receiver] += 1
                counts[mode] = exposure
            delta = {person:counts["dynamic"][person]-counts["frozen"][person] for person in sorted(counts["dynamic"])}
            row.update(exposure_dynamic=counts["dynamic"], exposure_frozen=counts["frozen"],
                       exposure_delta=delta, exposure_l1=sum(abs(value) for value in delta.values()),
                       final_winner_changed=dynamic.current.winner != frozen.current.winner)
        else:
            row["status"] = "failed"
        if calibration_seeds is None:
            row["matched_static"] = {"status":"unavailable", "reason":"calibration seed not supplied"}
        elif "dynamic" not in simulations:
            row["matched_static"] = {"status":"unavailable", "reason":"dynamic run failed"}
        elif scenario.rounds == 0:
            row["matched_static"] = {"status":"unavailable", "reason":"zero-round horizon"}
        else:
            dynamic = simulations["dynamic"]
            calibration = None
            try:
                calibration_scenario = replace(scenario, seed=calibration_seeds[index], proximity_mode="dynamic", static_proximity_edges=())
                calibration = Simulation(calibration_scenario)
                if calibration.runtime_manifest != run_manifest:
                    raise ElectionError("runtime or core source changed between comparison runs")
                calibration.run()
            except ElectionError as exc:
                if calibration is not None and calibration.runtime_manifest != run_manifest:
                    raise
                row["matched_static"] = {"status":"failed", "phase":"calibration", "error":str(exc),
                                         "calibration_seed":calibration_seeds[index],
                                         "completed_round":calibration.current.round if calibration is not None else None}
                rows.append(row)
                continue
            static_edges = _matched_static_edges(calibration.frames, scenario.people)
            calibration_exposure = {person.id:0 for person in scenario.people}
            for frame in calibration.frames[1:]:
                for _,receiver in frame.proximity_edges: calibration_exposure[receiver] += 1
            static_degree = {person.id:0 for person in scenario.people}
            for _,receiver in static_edges: static_degree[receiver] += 1
            calibration_delta = {person:calibration_exposure[person] - scenario.rounds * static_degree[person]
                                 for person in sorted(calibration_exposure)}
            raw = scenario.as_dict()
            raw["seed"] = seed
            raw["network"]["proximity_mode"] = "static"
            raw["network"]["static_proximity_edges"] = [list(edge) for edge in static_edges]
            matched = None
            try:
                matched_scenario = make_scenario(raw)
                matched = Simulation(matched_scenario)
                if matched.runtime_manifest != run_manifest:
                    raise ElectionError("runtime or core source changed between comparison runs")
                matched.run()
                same_positions = all(a.positions == b.positions for a,b in zip(dynamic.frames,matched.frames))
                exposure_dynamic = {person.id:0 for person in scenario.people}
                exposure_static = {person.id:0 for person in scenario.people}
                symmetric_difference = union = 0
                static_set = set(static_edges)
                for frame in dynamic.frames[1:]:
                    dynamic_set = set(frame.proximity_edges)
                    symmetric_difference += len(dynamic_set ^ static_set)
                    union += len(dynamic_set | static_set)
                    for _,receiver in dynamic_set: exposure_dynamic[receiver] += 1
                    for _,receiver in static_set: exposure_static[receiver] += 1
                delta = {person:exposure_dynamic[person]-exposure_static[person] for person in sorted(exposure_dynamic)}
                row["matched_static"] = {"status":"ok" if same_positions else "movement_mismatch",
                    "movement_matched":same_positions, "scenario":matched_scenario.as_dict(),
                    "calibration_seed":calibration_seeds[index],
                    "calibration_exposure":calibration_exposure, "static_in_degree":static_degree,
                    "calibration_exposure_delta":calibration_delta,
                    "calibration_exposure_l1":sum(abs(value) for value in calibration_delta.values()),
                    "calibration_proximity_frames":[{"round":frame.round,"edges":[list(edge) for edge in frame.proximity_edges]}
                                                     for frame in calibration.frames],
                    "metrics":series(matched_scenario, matched.frames),
                    "policy_digests":{name:digest for name,(_,digest,_) in matched.plugins.items()},
                    "exposure_dynamic":exposure_dynamic, "exposure_static":exposure_static,
                    "exposure_delta":delta, "exposure_l1":sum(abs(value) for value in delta.values()),
                    "temporal_arc_symmetric_difference":symmetric_difference,
                    "temporal_arc_union":union, "temporal_arc_mismatch":symmetric_difference/union if union else 0.0,
                    "final_winner_changed":dynamic.current.winner != matched.current.winner}
            except ElectionError as exc:
                if matched is not None and matched.runtime_manifest != run_manifest:
                    raise
                row["matched_static"] = {"status":"failed", "error":str(exc),
                                         "phase":"evaluation", "calibration_seed":calibration_seeds[index],
                                         "completed_round":matched.current.round if matched is not None else None,
                                         "static_proximity_edges":[list(edge) for edge in static_edges]}
        rows.append(row)
    return {"record_type":"eclipse.proximity-comparison", "record_version":2,
            "scenario":scenario.as_dict(), "seeds":seeds, "calibration_seeds":calibration_seeds,
            "manifest":run_manifest, "rows":rows,
            "notes":["Frozen uses the initial directed proximity layer; all other layers are independent.",
                     "Exposure counts incoming proximity arcs across post-initial rounds; L1 is over voters.",
                     "Matched static is built from a disjoint calibration trajectory, not the evaluation trajectory; it minimizes calibration exposure L1 per voter and selects most frequent partners for the chosen degree.",
                     "Same exposure totals do not imply matched partners or timing; no pure-turnover causal claim.",
                     "Built-in movement draws are keyed by actor and round; equality is checked per pair."]}


def batch(scenario: Scenario, seeds: list[int], target: str) -> dict:
    if target not in scenario.parties:
        raise ElectionError("target must be a known party")
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("seeds must be non-empty, unique non-negative integers")
    rows = []
    run_manifest = None
    for seed in seeds:
        treated = replace(scenario, seed=seed)
        control = replace(treated, interventions=())
        a, b = Simulation(control), Simulation(treated)
        if run_manifest is None:
            run_manifest = a.runtime_manifest
        if a.runtime_manifest != run_manifest or b.runtime_manifest != run_manifest:
            raise ElectionError("runtime or core source changed between batch runs")
        a.run(); b.run()
        left, right = series(control, a.frames), series(treated, b.frames)
        def target_margin(row):
            counts = row["counts"]
            return counts[target] - max((counts[p] for p in scenario.parties if p != target), default=0)
        rows.append({"seed": seed, "control": left, "treated": right,
                     "winner_changed": left[-1]["winner"] != right[-1]["winner"],
                     "target_share_delta": right[-1]["shares"][target] - left[-1]["shares"][target],
                     "target_margin_delta": target_margin(right[-1]) - target_margin(left[-1])})
    return {"record_type": "eclipse.batch", "record_version": 2,
            "target": target, "runs": len(rows), "scenario": scenario.as_dict(), "manifest": run_manifest,
            "policy_digests": {name: digest for name, (_, digest, _) in b.plugins.items()},
            "control_target_win_rate": sum(row["control"][-1]["winner"] == target for row in rows) / len(rows),
            "treated_target_win_rate": sum(row["treated"][-1]["winner"] == target for row in rows) / len(rows),
            "winner_change_rate": sum(row["winner_changed"] for row in rows) / len(rows),
            "mean_target_share_delta": sum(row["target_share_delta"] for row in rows) / len(rows),
            "mean_target_margin_delta": sum(row["target_margin_delta"] for row in rows) / len(rows),
            "rows": rows}


def compare_heuristics(scenario, seeds, policies, parameters=None, rounds=None, window=10):
    """Matched electorate/movement; descriptive metrics, not a 'best' claim."""
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ElectionError("comparison seeds must be unique nonnegative integers")
    if not policies or len(set(policies)) != len(policies):
        raise ElectionError("comparison requires unique policies")
    if type(window) is not int or window < 1:
        raise ElectionError("stability window must be positive")
    horizon = scenario.rounds if rounds is None else rounds
    if type(horizon) is not int or horizon < 1:
        raise ElectionError("comparison rounds must be positive")
    rows=[]; manifest=None
    # Validate every configuration before any run; never silently drop failures.
    configured = {p: configure_voting(scenario,p,parameters if p in STRATEGIC + EPISTEMIC_POLICIES else {}) for p in policies}
    for seed in seeds:
        for policy in policies:
            selected=replace(configured[policy],seed=seed,rounds=horizon)
            sim=Simulation(selected)
            if manifest is not None and sim.runtime_manifest != manifest:
                raise ElectionError("runtime changed between heuristic comparison runs")
            manifest=sim.runtime_manifest
            started=time.perf_counter()
            try:
                sim.run(horizon)
            except ElectionError as exc:
                rows.append({"seed":seed,"policy":policy,"status":"failed","error":str(exc),
                             "completed_round":sim.current.round,"runtime_seconds":time.perf_counter()-started})
                continue
            elapsed=time.perf_counter()-started
            metrics=series(selected,sim.frames)
            switches=[sum(a != dict(right.ballots)[person] for person,a in left.ballots)
                      for left,right in zip(sim.frames,sim.frames[1:])]
            final=sim.current
            # Deliberately labelled ordinal-rank proxy; not interpersonal cardinal welfare.
            prefs=dict(final.preferences); m=len(selected.parties)
            welfare=sum((m-1-prefs[person.id].index(final.winner))/max(1,m-1) for person in selected.people)/len(selected.people)
            stable=len(switches)>=window and all(s==0 for s in switches[-window:])
            winners=[f.winner for f in sim.frames[-window-1:]]
            trace={p:json.loads(mem) for p,mem in final.policy_memory}
            rows.append({"seed":seed,"policy":policy,"status":"observed_ballot_stability" if stable else "horizon_reached",
                         "completed_round":final.round,"winner":final.winner,
                         "winner_stable_window":len(winners)==window+1 and len(set(winners))==1,
                         "ballot_stable_window":stable,"total_ballot_switches":sum(switches),
                         "final_switch_fraction":switches[-1]/len(selected.people),
                         "winner_mean_rank_utility":welfare,"runtime_seconds":elapsed,
                         "metrics":metrics,"final_decisions":trace,
                         "scenario":selected.as_dict(),
                         "policy_digests":{name:digest for name,(_,digest,_) in sim.plugins.items()}})
    return {"record_type":"eclipse.heuristic-comparison","record_version":1,
            "manifest":manifest,"scenario":scenario.as_dict(),"seeds":seeds,
            "parameters":parameters or {},"rounds":horizon,"stability_window":window,
            "notes":["Same electorate and actor-round movement streams across policies.",
                     "Simultaneous updates; stability window is not proof of convergence.",
                     "Native information: pivotal receives initial global poll, other new policies use local sensors. Set information_source=poll for matched strategic information.",
                     "Epistemic policies require electorate access and trusted sensors; they do not accept the poll-information parameter and are not information-matched with poll-based policies.",
                     "Winner rank utility is a researcher ordinal proxy, not validated welfare."],"rows":rows}
