"""Streaming finite-horizon occupation diagnostics; never a stationarity test."""

from contextlib import ExitStack
import csv
import hashlib
import json
import math

from .engine import Simulation
from .exports import preflight_outputs
from .grid import assessment, CASE
from .model import ElectionError, make_scenario


def configure_control(scenario, control):
    if control not in ("baseline", "sincere-grid", "continuous-normal"):
        raise ElectionError("unknown occupation control")
    if control == "baseline":
        return scenario
    if scenario.stochastic_case != CASE:
        raise ElectionError("occupation controls require the declared finite-grid baseline")
    raw = scenario.as_dict()
    raw.pop("stochastic_stability")
    for group in raw["groups"].values():
        if control == "sincere-grid":
            group["voting"] = "sincere"
        else:
            group.update(movement="random_walk", max_step=.05,
                         parameters={"movement": {"distribution": "normal", "mean_step": .025, "std_step": .00625}})
    if control == "continuous-normal":
        positions = {p.id: p.position for p in scenario.people}
        for person in raw["people"]:
            person.pop("grid_position")
            person["position"] = list(positions[person["id"]])
    return make_scenario(raw)


class Means:
    def __init__(self, interval):
        self.interval = interval
        self.count = 0
        self.sums = {}
        self.phases = [dict(count=0, sums={}) for _ in range(interval)]
        self.previous = None
        self.lags = {}

    def add(self, tick, values):
        self.count += 1
        phase = self.phases[tick % self.interval]
        phase["count"] += 1
        for key, value in values.items():
            self.sums[key] = self.sums.get(key, 0.0) + value
            phase["sums"][key] = phase["sums"].get(key, 0.0) + value
            if self.previous is not None:
                x, y = self.previous[key], value
                row = self.lags.setdefault(key, [0, 0.0, 0.0, 0.0, 0.0, 0.0])
                for i, v in enumerate((1, x, y, x*x, y*y, x*y)):
                    row[i] += v
        self.previous = dict(values)

    def summary(self):
        correlations = {}
        for key, (n, sx, sy, sxx, syy, sxy) in self.lags.items():
            denominator = math.sqrt(max(0.0, n*sxx - sx*sx) * max(0.0, n*syy - sy*sy))
            correlations[key] = max(-1.0, min(1.0, (n*sxy - sx*sy) / denominator)) if denominator else None
        return {"rounds": self.count, "means": {k: v / self.count for k, v in self.sums.items()} if self.count else {},
                "phase_conditioned": [{"phase": q, "rounds": p["count"],
                                       "means": {k: v / p["count"] for k, v in p["sums"].items()} if p["count"] else {}}
                                      for q, p in enumerate(self.phases)],
                "lag1_correlation_descriptive": correlations}


def observables(scenario, current, previous):
    n = len(scenario.people)
    counts = dict(current.counts)
    before = dict(previous.ballots)
    old, new = set(previous.proximity_edges), set(current.proximity_edges)
    additions, removals = len(new - old), len(old - new)
    return {**{f"winner:{c}": int(current.winner == c) for c in scenario.parties},
            **{f"share:{c}": counts[c] / n for c in scenario.parties},
            "ballot_flip_fraction": sum(b != before[p] for p, b in current.ballots) / n,
            "winner_change": int(current.winner != previous.winner),
            "contact_additions": additions, "contact_removals": removals,
            "contact_additions_normalized": additions / (n * (n - 1)),
            "contact_removals_normalized": removals / (n * (n - 1))}


def run_frequencies(scenario, *, rounds, burn_in=1000, batch_size=100, rows_path=None):
    """One seed, fixed horizon. Retain one frame plus small phase/batch statistics."""
    config = scenario.majority_estimation
    if scenario.k != 1 or config is None or config.poll_refresh_rounds is None:
        raise ElectionError("frequencies requires k1 and periodic majority polls")
    interval = config.poll_refresh_rounds
    if (type(rounds) is not int or rounds < 1 or type(burn_in) is not int or not 0 <= burn_in < rounds
            or type(batch_size) is not int or batch_size < 1 or burn_in % interval or batch_size % interval):
        raise ElectionError("require rounds>burn-in>=0; burn-in and positive batch-size must align to poll interval")
    preflight_outputs([rows_path])
    simulation = Simulation(scenario)
    all_rounds, retained, batch = Means(interval), Means(interval), Means(interval)
    batches = []
    status, error = "complete", None
    with ExitStack() as stack:
        writer = None
        if rows_path is not None:
            writer = csv.writer(stack.enter_context(rows_path.open("x", encoding="utf-8", newline="")))
        keys = None
        for _ in range(rounds):
            previous = simulation.current
            try:
                current = simulation.step()
                values = observables(scenario, current, previous)
            except (ElectionError, MemoryError, RuntimeError) as exc:
                status, error = "failed", f"{type(exc).__name__}: {exc}"
                break
            if keys is None:
                keys = tuple(values)
                if writer:
                    writer.writerow(("round", "poll_phase", *keys))
            if writer:
                writer.writerow((current.round, current.round % interval, *(values[k] for k in keys)))
            all_rounds.add(current.round, values)
            if current.round > burn_in:
                retained.add(current.round, values)
                batch.add(current.round, values)
                if batch.count == batch_size:
                    batches.append({"start_round": current.round - batch_size + 1,
                                    "end_round": current.round, "complete": True, **batch.summary()})
                    batch = Means(interval)
            simulation.frames = [current]
    if batch.count:
        batches.append({"start_round": all_rounds.count - batch.count + 1,
                        "end_round": all_rounds.count, "complete": False, **batch.summary()})
    raw_scenario = scenario.as_dict()
    return {"record_type": "eclipse.occupation-diagnostics", "version": 1,
            "status": status, "error": error, "requested_rounds": rounds, "completed_rounds": all_rounds.count,
            "seed": scenario.seed, "scenario": raw_scenario, "manifest": simulation.runtime_manifest,
            "scenario_sha256": hashlib.sha256(json.dumps(raw_scenario, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "stochastic_stability": assessment(scenario), "burn_prefix": burn_in, "batch_size": batch_size,
            "all_rounds": all_rounds.summary(), "retained": retained.summary(), "batches": batches,
            "raw_rows": str(rows_path) if rows_path else None,
            "limits": ["fixed finite horizon, not stationarity or recurrent-class identification",
                       "burn-prefix exclusion is not a validated mixing time",
                       "phase/batch means and lag1 correlations are descriptive; rounds are dependent",
                       "single run; no independent-round error bars or cross-seed superiority claim",
                       "failure records retain completed prefix; no quiet-window stopping"]}
