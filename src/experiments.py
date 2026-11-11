"""Stable experiment API; mechanism studies live in focused modules."""

from dataclasses import replace
import json
import time

from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario
from .voting import STRATEGIC, configure_voting
from .epistemic import EPISTEMIC_POLICIES
from .spatial_experiments import (compare_leaders, _validate_alignment_comparison, _detector_episode,
                                  calibrate_and_evaluate_detector, compare_alignment, compare_nominations)
from .signal_experiments import compare_signal_responses
from .network_experiments import (exhaustive_one_round_campaign, compare_campaign_policies,
                                  coalition_ablations, _matched_static_edges, compare_proximity)


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
            switches = []
            for left, right in zip(sim.frames, sim.frames[1:]):
                next_ballots = dict(right.ballots)
                switches.append(sum(ballot != next_ballots[person] for person, ballot in left.ballots))
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
