#!/usr/bin/env python3
"""Generate repeatable scale workloads and time the real CLI summary path."""

import argparse
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from multi_agent_election.population import require_population


def scenario_text(agents: int, rounds: int, seed: int, sensors: bool = False) -> str:
    require_population(agents)
    if agents < 2 or rounds < 1 or seed < 0:
        raise ValueError("agents >= 2, rounds >= 1 and seed >= 0 required")
    # Expected mean degree is approximately 12 before boundary effects.
    radius = min(math.sqrt(12 / (math.pi * agents)), math.sqrt(2))
    rng = random.Random(seed)
    rankings = (("A", "B", "C"), ("B", "C", "A"), ("C", "A", "B"))
    lines = ['parties = ["A", "B", "C"]', 'k = 3', f'seed = {seed}', f'rounds = {rounds}',
             '[groups.residents]', f'voting = "{"sensed_plurality" if sensors else "sincere"}"',
             'movement = "stationary"', 'communication = "none"']
    if sensors:
        lines.append('capabilities = {sense_public_ballots = true}')
    lines.extend(('[network]', f'radius = {radius:.17g}'))
    for index in range(agents):
        preference = ", ".join(f'"{party}"' for party in rankings[index % len(rankings)])
        x, y = rng.random(), rng.random()
        lines.extend(('[[people]]', f'id = "{index:06d}"', 'group = "residents"',
                      f'preference = [{preference}]', f'position = [{x:.17g}, {y:.17g}]'))
    return "\n".join(lines) + "\n"


def http_benchmark(data: str, args: argparse.Namespace) -> dict:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from multi_agent_election import Simulation, make_scenario
    from multi_agent_election.metrics import frame_metrics
    from multi_agent_election.visual import make_server

    simulation = Simulation(make_scenario(tomllib.loads(data)))
    degree = frame_metrics(simulation.scenario, simulation.current)["mean_out_degree"]
    server = make_server(simulation)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/") as response:
            html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        times, sizes = [], []
        for revision in range(args.rounds):
            body = json.dumps({"action": "step", "revision": revision}).encode()
            request = Request(base + "/command", data=body, headers=headers, method="POST")
            started = time.perf_counter()
            with urlopen(request) as response:
                raw = response.read()
            reply = json.loads(raw)
            times.append((time.perf_counter() - started) * 1000)
            sizes.append(len(raw))
            if reply["frame"]["round"] != revision + 1 or reply["revision"] != revision + 1:
                raise RuntimeError("HTTP response has incorrect round or revision")
        ordered = sorted(times)
        return {"mode": "http-steps", "agents": args.agents, "rounds": args.rounds, "seed": args.seed,
                "sensors_enabled": args.sensors, "sensor_observations_final": reply["metric"]["sensor_observation_count"],
                "mean_out_degree_initial": degree, "mean_ms": sum(times) / len(times),
                "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1], "max_ms": max(times),
                "mean_response_bytes": sum(sizes) / len(sizes),
                "peak_process_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if sys.platform.startswith("linux") else None,
                "python": platform.python_version(), "platform": platform.platform(),
                "manifest": simulation.runtime_manifest,
                "includes": "local HTTP client, server, JSON encode/decode, engine, metrics and retained full history; excludes browser"}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "cli", "http"))
    parser.add_argument("--agents", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--sensors", action="store_true", help="enable public trusted sensing and sensed-plurality voting")
    parser.add_argument("--output", type=Path, help="new TOML path for generate mode")
    args = parser.parse_args()
    try:
        data = scenario_text(args.agents, args.rounds, args.seed, args.sensors)
        if args.mode == "generate":
            if args.output is None:
                parser.error("generate requires --output")
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(data)
            print(json.dumps({"scenario": str(args.output), "agents": args.agents, "rounds": args.rounds, "seed": args.seed}))
            return 0
        if args.output is not None:
            parser.error("--output is only valid with generate")
        if args.mode == "http":
            print(json.dumps(http_benchmark(data, args), indent=2, allow_nan=False))
            return 0
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="eclipse-benchmark-") as directory:
            scenario = Path(directory) / "scenario.toml"
            scenario.write_text(data, encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1")
            command = [sys.executable, "-m", "multi_agent_election.cli", "run", str(scenario), "--summary"]
            started = time.perf_counter()
            result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
            elapsed = time.perf_counter() - started
            output = json.loads(result.stdout)
        metrics = output["metrics"]
        if len(metrics) != args.rounds + 1 or metrics[-1]["round"] != args.rounds:
            raise RuntimeError("CLI returned an incomplete metrics history")
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        report = {"mode": "cli-summary", "agents": args.agents, "rounds": args.rounds, "seed": args.seed,
                  "sensors_enabled": args.sensors, "sensor_observations_final": metrics[-1]["sensor_observation_count"],
                  "mean_out_degree_initial": metrics[0]["mean_out_degree"], "wall_seconds": elapsed,
                  "agent_rounds_per_second": args.agents * args.rounds / elapsed,
                  "peak_child_rss_kib_linux": usage.ru_maxrss if sys.platform.startswith("linux") else None,
                  "python": platform.python_version(), "platform": platform.platform(),
                  "machine": platform.machine(), "manifest": output["manifest"],
                  "includes": "scenario load, initialization, simulation and JSON output"}
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"benchmark error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
