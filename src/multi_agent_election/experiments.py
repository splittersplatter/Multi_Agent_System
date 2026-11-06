"""Matched interventions compared under keyed exogenous randomness."""

from dataclasses import replace
from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario


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
    return {"record_type": "eclipse.batch", "record_version": 1,
            "target": target, "runs": len(rows), "scenario": scenario.as_dict(), "manifest": run_manifest,
            "policy_digests": {name: digest for name, (_, digest, _) in b.plugins.items()},
            "control_target_win_rate": sum(row["control"][-1]["winner"] == target for row in rows) / len(rows),
            "treated_target_win_rate": sum(row["treated"][-1]["winner"] == target for row in rows) / len(rows),
            "winner_change_rate": sum(row["winner_changed"] for row in rows) / len(rows),
            "mean_target_share_delta": sum(row["target_share_delta"] for row in rows) / len(rows),
            "mean_target_margin_delta": sum(row["target_margin_delta"] for row in rows) / len(rows),
            "rows": rows}
