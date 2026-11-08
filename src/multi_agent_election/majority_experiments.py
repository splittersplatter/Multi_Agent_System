"""Matched, evaluator-only pilots for passive majority estimation."""

from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import random
import resource
import statistics
import sys
import time

from .engine import Simulation
from .majority import MajorityConfig, MajorityState, advance_population, estimate, leader_indices
from .model import ElectionError, make_scenario
from .provenance import manifest


def _rng(seed, name):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}\0majority-pilot\0{name}".encode()).digest(), "big"))


def pilot_scenario(seed, case, moving, rounds=100):
    """Separate initial-layout, ballot-shuffle and poll-sample randomness."""
    if case not in ("well_mixed", "clustered", "support_shift"):
        raise ElectionError("unknown majority pilot case")
    layout, shuffle = _rng(seed, "layout"), _rng(seed, "ballots")
    preferences = (["A"] * 70 + ["B"] * 20 + ["C"] * 10,
                   ["A"] * 10 + ["B"] * 50 + ["C"] * 40) if case == "clustered" else (["A"] * 80 + ["B"] * 70 + ["C"] * 50,)
    people = []
    for cluster, choices in enumerate(preferences):
        shuffle.shuffle(choices)
        for choice in choices:
            x = layout.uniform(0.1, 0.4) if cluster == 0 else layout.uniform(0.6, 0.9)
            if case != "clustered":
                x = layout.random()
            people.append({"id": f"p{len(people):03d}", "group": "people",
                           "preference": [choice] + [c for c in ("A", "B", "C") if c != choice],
                           "position": [x, layout.random()]})
    poll_ids = _rng(seed, "poll-sample").sample(range(200), 100)
    poll = Counter(people[i]["preference"][0] for i in poll_ids)
    raw = {"parties": ["A", "B", "C"], "k": 1, "seed": seed, "rounds": rounds,
           "groups": {"people": {"voting": "sincere", "movement": "random_walk" if moving else "stationary",
                                    "max_step": 0.025 if moving else 0, "communication": "none"}},
           "network": {"radius": 0.12}, "people": people,
           "majority_estimation": {"poll_counts": [poll[c] for c in ("A", "B", "C")]}}
    if case == "support_shift":
        changed = [p for p in people if p["preference"][0] == "A"][:20]
        raw["interventions"] = [{"round": 50, "person": p["id"], "preference": ["B", "A", "C"]} for p in changed]
    return make_scenario(raw), {"poll_sample_ids": [people[i]["id"] for i in poll_ids], "support_shift_source_round": 50 if case == "support_shift" else None}


def _arms(config, sensitivity):
    arms = {"poll_only": replace(config, poll_weight=1.0, memory_rounds=1),
            "current_contacts": replace(config, poll_weight=0.0, memory_rounds=1),
            "window_only": replace(config, poll_weight=0.0), "blended": config}
    if sensitivity:
        arms.update({f"window_{k}": replace(config, memory_rounds=k) for k in (5, 20)})
        arms.update({f"weight_{w}": replace(config, poll_weight=w) for w in (0.25, 0.75)})
    return arms


def _percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] if ordered else None


def _compressed(path):
    # Stable gzip timestamp; payload order does not depend on hash iteration.
    return io.TextIOWrapper(gzip.GzipFile(filename=str(path), mode="xb", mtime=0), encoding="utf-8")


def _write_line(handle, payload):
    handle.write(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n")


def _evaluate(scenario, directory, sensitivity, shift_round):
    simulation = Simulation(scenario)
    config = scenario.majority_estimation
    if config is None:
        raise ElectionError("estimate-majority requires majority_estimation with explicit poll_counts")
    arms = _arms(config, sensitivity)
    states = {name: tuple((p.id, MajorityState.initial(scenario.parties)) for p in scenario.people) for name in arms}
    totals = {name: Counter() for name in arms}
    timings = {name: [] for name in arms}
    recovered = {name: {} for name in arms}
    max_entries = {name: 0 for name in arms}
    people = [p.id for p in scenario.people]
    history_bytes = len(json.dumps(simulation.current.as_dict(), separators=(",", ":")).encode())
    engine_seconds = []
    trace_hash = hashlib.sha256()
    with _compressed(directory / "predictions.jsonl.gz") as predictions, _compressed(directory / "trace.jsonl.gz") as trace:
        _write_line(predictions, {"type": "header", "parties": scenario.parties, "people": people,
                                "arms": {name: c.as_dict() for name, c in arms.items()},
                                "empty_memory": "initial_poll", "time": "encounter r observes completed ballot r-1"})
        _write_line(trace, simulation.current.as_dict())
        for _ in range(scenario.rounds):
            previous = simulation.current
            started = time.perf_counter()
            current = simulation.step()
            engine_seconds.append(time.perf_counter() - started)
            truth_counts = dict(previous.counts)
            n = len(people)
            truth = tuple(truth_counts[c] / n for c in scenario.parties)
            highest = max(truth_counts.values())
            truth_leaders = tuple(i for i, c in enumerate(scenario.parties) if truth_counts[c] == highest)
            raw_trace = {"round": current.round, "positions": dict(current.positions),
                         "ballots": dict(current.ballots), "proximity_edges": current.proximity_edges}
            trace_data = json.dumps(raw_trace, separators=(",", ":"))
            trace_hash.update(trace_data.encode() + b"\n")
            _write_line(trace, raw_trace)
            history_bytes += len(json.dumps(current.as_dict(), separators=(",", ":")).encode())
            for name, arm in arms.items():
                started = time.perf_counter()
                states[name] = (tuple((p, replace(state, round=current.round)) for p, state in states[name])
                                if name == "poll_only" else advance_population(states[name], scenario.parties, arm, current.round,
                                                 current.proximity_edges, dict(previous.ballots)))
                timings[name].append(time.perf_counter() - started)
                if name == "blended" and states[name] != current.majority_states:
                    raise ElectionError("engine/evaluation cache disagreement")
                predictions_round, leaders_round, sizes, ages_round = [], [], [], []
                for person, state in states[name]:
                    shares = estimate(state, arm)
                    leaders = leader_indices(state, arm)
                    correct = leaders == truth_leaders
                    totals[name]["observations"] += 1
                    totals[name]["leader_matches"] += correct
                    totals[name]["ambiguous"] += len(leaders) > 1
                    totals[name]["share_error"] += sum(abs(a - b) for a, b in zip(shares, truth)) / 2
                    size = len(state.entries)
                    totals[name]["retained"] += size
                    ages = [current.round - seen for _, _, seen, _ in state.entries]
                    totals[name]["age_total"] += sum(ages)
                    if shift_round is not None and previous.round >= shift_round and correct:
                        recovered[name].setdefault(person, previous.round - shift_round)
                    predictions_round.append(shares); leaders_round.append(leaders); sizes.append(size)
                    ages_round.append(sum(ages) / size if size else None)
                max_entries[name] = max(max_entries[name], sum(sizes))
                _write_line(predictions, {"round": current.round, "source_round": previous.round, "arm": name,
                            "truth_counts": truth_counts, "truth_leaders": truth_leaders,
                            "shares": predictions_round, "leaders": leaders_round, "sample_sizes": sizes,
                            "mean_encounter_ages": ages_round})
            # Summary mode: retain only current frame; raw trace is streamed above.
            simulation.frames = [current]
    results = {}
    for name, values in totals.items():
        denominator = values["observations"]
        delays = list(recovered[name].values())
        evaluated_shift = shift_round is not None and scenario.rounds > shift_round
        results[name] = {"leader_set_accuracy": values["leader_matches"] / denominator if denominator else None,
                        "ambiguous_fraction": values["ambiguous"] / denominator if denominator else None,
                        "mean_total_variation_error": values["share_error"] / denominator if denominator else None,
                        "mean_retained_neighbors": values["retained"] / denominator if denominator else None,
                        "mean_coverage": values["retained"] / (denominator * (len(people) - 1)) if denominator and len(people) > 1 else None,
                        "mean_encounter_age": values["age_total"] / values["retained"] if values["retained"] else None,
                        "maximum_population_cache_entries": max_entries[name],
                        "population_update_median_seconds": statistics.median(timings[name]) if timings[name] else None,
                        "population_update_p95_seconds": _percentile(timings[name], 0.95),
                        "recovery_first_match_delays": recovered[name] if evaluated_shift else None,
                        "mean_recovery_delay_recovered_only": statistics.mean(delays) if delays else None,
                        "unrecovered_fraction": 1 - len(delays) / len(people) if evaluated_shift else None}
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"status": "ok", "arms": results, "rounds": scenario.rounds,
            "engine_round_median_seconds": statistics.median(engine_seconds) if engine_seconds else None,
            "engine_round_p95_seconds": _percentile(engine_seconds, 0.95),
            "serialized_frame_payload_bytes": history_bytes,
            "history_note": "sum of compact JSON frame bytes, including initial; excludes array/checkpoint envelope",
            "process_peak_rss_bytes": rss if sys.platform == "darwin" else rss * 1024,
            "memory_note": "process-lifetime high-water RSS includes evaluator; not isolated estimator allocation",
            "trajectory_sha256": trace_hash.hexdigest()}


def run_pilot(output_dir, *, seeds=(101, 102, 103, 104, 105), sensitivity=False, scenario=None):
    """Exclusive artifact directory; retain partial runs/failures, never overwrite."""
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink() or not output_dir.parent.is_dir():
        raise ElectionError("output directory must be new with an existing parent")
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ElectionError("seeds must be unique nonnegative integers")
    if scenario is not None and scenario.majority_estimation is None:
        raise ElectionError("scenario requires majority_estimation with explicit poll_counts")
    output_dir.mkdir()
    context = {"record_type": "eclipse.majority-estimation-pilot", "record_version": 1,
               "created_utc": datetime.now(timezone.utc).isoformat(), "manifest": manifest(),
               "command": sys.argv, "platform": platform.platform(), "seeds": list(seeds),
               "sensitivity": sensitivity, "rng_schema": "sha256-keyed majority-pilot layout/ballots/poll-sample; engine actor-round motion",
               "inference": "exploratory; no convergence, calibrated confidence or superiority claim"}
    with (output_dir / "context.json").open("x") as handle:
        json.dump(context, handle, indent=2)
    results = []
    cases = (("provided", None),) if scenario is not None else tuple((case, moving) for case in ("well_mixed", "clustered", "support_shift") for moving in (False, True))
    for case, moving in cases:
        for seed in seeds:
            motion = "configured" if moving is None else "moving" if moving else "stationary"
            name = f"{case}-{motion}-{seed}"
            directory = output_dir / name
            directory.mkdir()
            row = {"name": name, "seed": seed, "case": case, "moving": moving}
            try:
                if scenario is None:
                    configured, audit = pilot_scenario(seed, case, moving)
                else:
                    configured = make_scenario({**scenario.as_dict(), "seed": seed})
                    audit = {"support_shift_source_round": None}
                with (directory / "scenario.json").open("x") as handle:
                    json.dump(configured.as_dict(), handle, indent=2)
                with (directory / "sampling.json").open("x") as handle:
                    json.dump(audit, handle, indent=2)
                row.update(_evaluate(configured, directory, sensitivity, audit["support_shift_source_round"]))
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
    artifacts = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            artifacts[str(path.relative_to(output_dir))] = {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}
    result = {**context, "runs": results, "failed": sum(row["status"] != "ok" for row in results), "artifacts": artifacts}
    with (output_dir / "results.json").open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result
