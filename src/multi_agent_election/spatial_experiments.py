"""Nomination, alignment, detector and leader studies with paired controls."""

import math
from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario, apply_overrides, make_scenario
from .experiment_support import ExperimentRunner, movement_matched


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
    rows = []; runner = ExperimentRunner("leader")
    for seed in seeds:
        runs = {}
        for arm, (policy, signal_mode) in arms.items():
            raw = scenario.as_dict(); raw["seed"] = seed
            raw["leaders"]["policy"] = policy; raw["leaders"]["signal_mode"] = signal_mode
            run, sim = runner.execute(raw)
            if sim is not None and (run["status"] == "ok"):
                run["nomination"] = sim.scenario.nomination.as_dict()
            runs[arm] = run
        for arm, run in runs.items():
            if run["status"] != "ok":
                continue
            baseline_name = "fixed_broadcast" if arm == "adaptive_broadcast" else "fixed_no_signal"
            baseline = runs[baseline_name]; run["baseline"] = baseline_name
            run["movement_matched"] = movement_matched(run, baseline)
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
            "manifest": runner.manifest, "rows": rows,
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
    rows = []; runner = ExperimentRunner("alignment")
    for seed in seeds:
        runs = {}
        for arm in arms:
            raw = scenario.as_dict(); raw["seed"] = seed
            raw["alignment"]["attack"]["policy"] = ("toward_target" if arm == "targeted_with_drift" else
                                                       "random" if arm == "random_with_drift" else "none")
            if arm == "no_drift_no_attack":
                raw["alignment"]["drift_max_step"] = 0
            run, sim = runner.execute(raw)
            if sim is not None and (run["status"] == "ok"):
                run["nomination"] = sim.scenario.nomination.as_dict()
            runs[arm] = run
        for arm, run in runs.items():
            if run["status"] != "ok":
                continue
            baseline_name = "no_drift_no_attack" if arm == "drift_only" else "drift_only"
            baseline = runs[baseline_name]
            run["baseline"] = baseline_name
            run["movement_matched"] = movement_matched(run, baseline)
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
            "seeds": seeds, "arms": list(arms), "manifest": runner.manifest, "rows": rows,
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
    rows = []; runner = ExperimentRunner("nomination")
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
            run, sim = runner.execute(raw)
            if sim is not None:
                run["nomination"] = sim.scenario.nomination.as_dict()
            runs[mode] = run
        control = runs["endogenous"]
        for run in runs.values():
            if run["status"] != "ok":
                continue
            run["movement_matched"] = movement_matched(run, control)
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
            "seeds": seeds, "manifest": runner.manifest, "rows": rows,
            "notes": ["Fixed control uses exactly the endogenous nominees and party-ID order; nomination records are not policy observations.",
                      "Random control selects the same number of eligible people with a separate seed-keyed stream.",
                      "The identity of a winner cannot be compared as a fixed target when candidate sets differ.",
                      "Configured target-specific mechanisms may fail when their target is not nominated; failures remain visible.",
                      "Distances use fixed initial voter ideals and fixed nominee positions; differences are descriptive, not convergence evidence."]}
