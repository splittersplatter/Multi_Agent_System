"""Public-signal distortion and response factorial with information boundaries."""

import json
from .model import ElectionError, Scenario, apply_overrides
from .experiment_support import ExperimentRunner, movement_matched


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
    runner = ExperimentRunner("signal")
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
                run, sim = runner.execute(raw)
                if run["status"] == "failed":
                    run["scenario"] = raw
                runs[response][policy_name] = run
            control = runs[response]["truthful"]
            for run in runs[response].values():
                if run["status"] != "ok":
                    continue
                run["movement_matched"] = movement_matched(run, control)
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
                run["response_movement_matched"] = movement_matched(run, control)
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
            "max_worlds": max_worlds, "manifest": runner.manifest, "rows": rows,
            "notes": ["Within each response, truthful report is the paired baseline; allowed budgets are equal.",
                      "Within each signal policy, the sincere response is the response_paired baseline; signal equality is checked per round.",
                      "Selected groups retain permissions, but sincere, trusting and epistemic policies use information differently.",
                      "Prior vote differences can change later reports, networks and other mechanisms; reports need not match across responses.",
                      "Movement is checked; failed and unpaired runs are retained. Outcomes are descriptive, not convergence evidence."]}
