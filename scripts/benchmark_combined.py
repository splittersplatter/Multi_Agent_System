#!/usr/bin/env python3
"""Benchmark reproducible all-mechanism workloads using isolated worker processes."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from multi_agent_election.population import require_population
TEMPLATE = ROOT / "examples" / "all-enabled.toml"


def _line_replace(lines, old, new):
    if lines.count(old) != 1:
        raise ValueError(f"workload template changed; expected exactly one {old!r} line")
    lines[lines.index(old)] = new


def scenario_text(agents, rounds, seed):
    require_population(agents)
    if type(agents) is not int or agents < 4 or type(rounds) is not int or rounds < 1 or type(seed) is not int or seed < 0:
        raise ValueError("agents >= 4, rounds >= 1 and seed >= 0 required")
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    radius = min(math.sqrt(12 / (math.pi * agents)), math.sqrt(2))
    replacements = {"seed = 2026": f"seed = {seed}", "rounds = 5": f"rounds = {rounds}",
                    "radius = 0.25": f"radius = {radius:.17g}",
                    "report_budget_total = 2": f"report_budget_total = {max(2, rounds)}",
                    "sight_budget_total = 2": f"sight_budget_total = {max(2, rounds)}",
                    "eavesdrop_budget_total = 2": f"eavesdrop_budget_total = {max(2, rounds)}",
                    "per_round_step = 0.1": "per_round_step = 0.001",
                    "lifetime_budget = 0.3": f"lifetime_budget = {max(0.001, rounds * 0.001):.17g}",
                    "per_person_round = 0.15": "per_person_round = 0.005",
                    "total_budget = 0.3": f"total_budget = {max(0.005, rounds * 0.005):.17g}",
                    "lifetime_budget = 1": f"lifetime_budget = {max(1, rounds)}",
                    "lifetime_budget = 2": f"lifetime_budget = {max(2, rounds)}"}
    for old in replacements:
        if lines.count(old) != 1:
            raise ValueError(f"workload template changed; expected exactly one {old!r} line")
    lines = [replacements.get(line, line) for line in lines]
    coalition_start = lines.index("[[coalitions]]")
    coalition_target = coalition_start + 3
    if lines[coalition_target] != 'target = "alice"':
        raise ValueError("workload template coalition target changed")
    lines[coalition_target] = 'target = "cara"'
    edges = [["alice", "bob"], ["bob", "dina"], ["cara", "dina"]]
    edges.extend(["alice", f"scale-{index:06d}"] for index in range(agents - 4))
    _line_replace(lines, 'persistent_edges = [["alice", "bob"], ["bob", "dina"], ["cara", "dina"]]',
                  "persistent_edges = " + json.dumps(edges, separators=(",", ":")))
    rng = random.Random(seed)
    for index in range(agents - 4):
        ideal = [rng.uniform(0, 0.04), rng.uniform(0.46, 0.54)]
        position = [rng.random(), rng.random()]
        lines.extend(("[[people]]", f'id = "scale-{index:06d}"', 'group = "residents"',
                      f"ideal = [{ideal[0]:.17g}, {ideal[1]:.17g}]",
                      f"position = [{position[0]:.17g}, {position[1]:.17g}]"))
        if index % 10 == 0:
            lines.append('overrides = { voting = "sensed_plurality", capabilities = { sense_public_ballots = true } }')
    return "\n".join(lines) + "\n"


def activity(metrics):
    last = metrics[-1]
    return {"final_counts": last["counts"], "final_winner": last["winner"],
            "proximity_edge_changes": sum((row["proximity_edge_additions"] or 0) + (row["proximity_edge_removals"] or 0) for row in metrics),
            "trusted_sensor_observations": sum(row["sensor_observation_count"] for row in metrics),
            "coalition_sight_events": sum(row.get("preference_sight_count", 0) for row in metrics),
            "coalition_interceptions": sum(row.get("eavesdrop_count", 0) for row in metrics),
            "deceptive_reports": sum(row.get("deceptive_report_count", 0) for row in metrics),
            "campaign_edges_purchased": last["campaign_controller_spend"], "signal_spend": last["signal_spend"],
            "ideal_attack_spend": last["alignment_attack_spend"], "leader_move_spend": last["leader_total_spend"],
            "detector_alerts": sum(row["detector_alert"] for row in metrics),
            "ballot_switches": sum(row["ballot_switch_count"] or 0 for row in metrics)}


def _check_metrics(metrics, agents, rounds):
    if len(metrics) != rounds + 1 or [row["round"] for row in metrics] != list(range(rounds + 1)):
        raise RuntimeError("workload returned incomplete or out-of-order rounds")
    if any(sum(row["counts"].values()) != agents for row in metrics):
        raise RuntimeError("workload changed the number of ballots")
    required = {"alignment_attack_spend", "leader_total_spend", "campaign_controller_spend", "signal_spend", "detector_alert"}
    if any(not required <= set(row) for row in metrics):
        raise RuntimeError("workload omitted an enabled mechanism")


def _cli(data, agents, rounds):
    with tempfile.TemporaryDirectory(prefix="eclipse-combined-benchmark-") as directory:
        path = Path(directory) / "scenario.toml"
        path.write_text(data, encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
        started = time.perf_counter()
        result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "run", str(path), "--summary"],
                                env=env, capture_output=True, text=True)
        elapsed = time.perf_counter() - started
        if result.returncode:
            raise RuntimeError(f"CLI exit {result.returncode}: {result.stderr.strip()}")
        output = json.loads(result.stdout)
    metrics = output["metrics"]; _check_metrics(metrics, agents, rounds)
    return {"mode": "cli-summary", "wall_seconds": elapsed, "agent_rounds_per_second": agents * rounds / elapsed,
            "peak_child_rss_kib_linux": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if sys.platform.startswith("linux") else None,
            "initial_public_mean_out_degree": metrics[0]["mean_out_degree"], "nomination": output["nomination"],
            "activity": activity(metrics), "manifest": output["manifest"], "metrics": metrics,
            "includes": "cold child process, TOML load, initialization, summary simulation and JSON output; excludes browser"}


def _http(data, agents, rounds):
    sys.path.insert(0, str(ROOT / "src"))
    from multi_agent_election import Simulation, make_scenario
    from multi_agent_election.metrics import frame_metrics
    from multi_agent_election.visual import make_server
    started = time.perf_counter()
    simulation = Simulation(make_scenario(tomllib.loads(data)))
    initialization = time.perf_counter() - started
    initial = frame_metrics(simulation.scenario, simulation.current)
    metrics = [initial]; times = []; sizes = []
    server = make_server(simulation)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/") as response: html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        for revision in range(rounds):
            body = json.dumps({"action": "step", "revision": revision}).encode()
            request = Request(base + "/command", data=body, headers=headers, method="POST")
            start = time.perf_counter()
            with urlopen(request) as response: raw = response.read()
            reply = json.loads(raw)
            times.append((time.perf_counter() - start) * 1000); sizes.append(len(raw))
            if reply["revision"] != revision + 1 or reply["frame"]["round"] != revision + 1:
                raise RuntimeError("HTTP response has incorrect revision or round")
            metrics.append(reply["metric"])
        _check_metrics(metrics, agents, rounds)
        ordered = sorted(times)
        return {"mode": "http-steps", "initialization_seconds": initialization, "mean_ms": sum(times) / len(times),
                "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1], "max_ms": max(times),
                "mean_response_bytes": sum(sizes) / len(sizes),
                "peak_process_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if sys.platform.startswith("linux") else None,
                "initial_public_mean_out_degree": initial["mean_out_degree"], "nomination": simulation.scenario.nomination.as_dict(),
                "activity": activity(metrics), "manifest": simulation.runtime_manifest, "metrics": metrics,
                "includes": "loopback client/server, JSON, engine, metrics and retained full history; excludes browser"}
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "cli", "http"))
    parser.add_argument("--agents", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--output", type=Path, help="new TOML (generate) or JSON (benchmark) path")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if not 1 <= args.repetitions <= 20 or not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
            raise ValueError("repetitions must be 1..20 and timeout must be positive and finite")
        data = scenario_text(args.agents, args.rounds, args.seed)
        digest = hashlib.sha256(data.encode()).hexdigest()
        if args.mode == "generate":
            if args.output is None or args.worker:
                raise ValueError("generate requires --output and cannot be a worker")
            with args.output.open("x", encoding="utf-8") as handle: handle.write(data)
            print(json.dumps({"scenario": str(args.output), "scenario_sha256": digest, "agents": args.agents}))
            return 0
        if args.worker:
            result = _cli(data, args.agents, args.rounds) if args.mode == "cli" else _http(data, args.agents, args.rounds)
            print(json.dumps({"status": "ok", **result}, allow_nan=False))
            return 0
        if args.output is not None and (args.output.exists() or args.output.is_symlink()):
            raise ValueError(f"output already exists: {args.output}")
        if args.output is not None and not args.output.parent.is_dir():
            raise ValueError(f"output parent directory does not exist: {args.output.parent}")
        records = []
        for repetition in range(args.repetitions):
            command = [sys.executable, str(Path(__file__).resolve()), args.mode, "--agents", str(args.agents),
                       "--rounds", str(args.rounds), "--seed", str(args.seed), "--worker"]
            start = time.perf_counter()
            try:
                worker = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                          start_new_session=(os.name == "posix"))
                try:
                    stdout, stderr = worker.communicate(timeout=args.timeout_seconds)
                except subprocess.TimeoutExpired:
                    if os.name == "posix":
                        try: os.killpg(worker.pid, signal.SIGTERM)
                        except ProcessLookupError: pass
                    else:
                        worker.kill()
                    try:
                        worker.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        if os.name == "posix":
                            try: os.killpg(worker.pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                        else:
                            worker.kill()
                        worker.communicate()
                    raise
                if worker.returncode:
                    record = {"status": "failed", "exit_code": worker.returncode, "error": stderr.strip()}
                else:
                    record = json.loads(stdout)
            except subprocess.TimeoutExpired:
                record = {"status": "timed_out", "timeout_seconds": args.timeout_seconds}
            except json.JSONDecodeError as exc:
                record = {"status": "failed", "error": f"invalid worker output: {exc}"}
            record.update(repetition=repetition, worker_wall_seconds=time.perf_counter() - start)
            records.append(record)
        cpu = None
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip(); break
        except OSError:
            pass
        report = {"record_type": "eclipse.combined-benchmark", "record_version": 1, "mode": args.mode,
                  "agents": args.agents, "rounds": args.rounds, "seed": args.seed, "repetitions": args.repetitions,
                  "timeout_seconds": args.timeout_seconds, "scenario_sha256": digest,
                  "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "template_sha256": hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
                  "python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
                  "cpu_model": cpu, "logical_cpus": os.cpu_count(),
                  "sensor_enabled_people": (args.agents - 4 + 9) // 10,
                  "workload": "all-enabled base; seeded added near-alice ideals, star links, sparse proximity, 10% added voters sense public ballots",
                  "runs": records}
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, allow_nan=False); handle.write("\n")
            print(json.dumps({"output": str(args.output), "runs": len(records),
                              "failed": sum(record["status"] != "ok" for record in records)}))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"benchmark error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
