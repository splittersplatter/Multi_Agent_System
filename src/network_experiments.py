"""Proximity, coalition and campaign studies; exact one-round campaign oracle."""

from dataclasses import replace
import itertools
import math
from .campaign import select_campaign_edges
from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario, apply_overrides, make_scenario
from .experiment_support import ExperimentRunner


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
    rows = []; runner = ExperimentRunner("campaign")
    for seed in seeds:
        runs = {}; simulations = {}
        for name in policies:
            selected = replace(scenario, seed=seed, campaign_controller=replace(controller,policy=name))
            run, sim = runner.execute(selected)
            runs[name] = run
            if run["status"] == "ok":
                simulations[name] = sim
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
            "policies":list(policies), "manifest":runner.manifest, "rows":rows,
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
    rows = []; runner = ExperimentRunner("ablation")
    for seed in seeds:
        runs = {}; simulations = {}
        for arm, enabled in arms.items():
            selected = replace(configurations[arm], seed=seed)
            run, sim = runner.execute(selected)
            runs[arm] = run
            if run["status"] == "ok":
                simulations[arm] = sim
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
            "manifest":runner.manifest, "rows":rows,
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
