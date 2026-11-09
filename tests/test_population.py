"""Production minimum tests deliberately do NOT enable tiny verification scope."""

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiment_support import ExperimentRunner
from multi_agent_election.majority_experiments import run_pilot
from multi_agent_election.population import require_population, verification_scope
from multi_agent_election.visual import Session, make_server
from scripts.benchmark_simulator import scenario_text


def scenario(people):
    return make_scenario({"parties": ["A", "B", "C"], "k": 1, "rounds": 1,
                          "groups": {"people": {"voting": "sincere"}},
                          "people": [{"id": f"v{i}", "group": "people", "preference": ["A", "B", "C"],
                                      "position": [i / max(people, 1), 0.5]} for i in range(people)]})


class MinimumPopulationTests(unittest.TestCase):
    def test_normal_engine_rejects_99_and_accepts_100_and_101(self):
        with self.assertRaisesRegex(ElectionError, "at least 100.*99"):
            Simulation(scenario(99))
        for population in (100, 101):
            simulation = Simulation(scenario(population))
            self.assertEqual(sum(dict(simulation.step().counts).values()), population)
            self.assertIsNone(simulation.verification_reason)

    def test_scope_is_explicit_nested_and_restored_after_error(self):
        with self.assertRaises(ElectionError):
            require_population(99)
        with verification_scope("formal tiny case"):
            simulation = Simulation(scenario(4))
            self.assertEqual(simulation.verification_reason, "formal tiny case")
            with self.assertRaises(RuntimeError):
                with verification_scope("nested fixture"):
                    require_population(4)
                    raise RuntimeError("exit nested")
            self.assertEqual(Simulation(scenario(4)).verification_reason, "formal tiny case")
        with self.assertRaises(ElectionError):
            Simulation(scenario(99))
        for reason in ("", " ", None, False):
            with self.assertRaises(ElectionError), verification_scope(reason):
                pass
        for population in (0, -1, True, 100.0, "100"):
            with self.assertRaises(ElectionError):
                require_population(population)

    def test_environment_does_not_enable_exception(self):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "fixture", "ECLIPSE_VERIFICATION": "1"}):
            with self.assertRaises(ElectionError):
                Simulation(scenario(99))

    def test_small_checkpoint_cannot_resume_as_normal_simulation(self):
        with verification_scope("legacy replay fixture"):
            simulation = Simulation(scenario(4)); simulation.step()
            payload = simulation.checkpoint()
        with self.assertRaisesRegex(ElectionError, "at least 100"):
            Simulation.from_checkpoint(payload)
        with verification_scope("legacy replay fixture"):
            self.assertEqual(Simulation.from_checkpoint(payload).current, simulation.current)

    def test_cli_run_visual_and_comparison_reject_small_before_outputs(self):
        for command in (["run", "examples/baseline.toml"],
                        ["visual", "examples/baseline.toml"],
                        ["compare", "examples/baseline.toml", "--seeds", "1"],
                        ["batch", "examples/baseline.toml", "--seeds", "1", "--target", "A"]):
            error = io.StringIO()
            with contextlib.redirect_stderr(error), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(command), 2)
            self.assertIn("at least 100", error.getvalue())

    def test_experiment_and_custom_pilot_do_not_start_small_runs(self):
        small = scenario(99)
        record, simulation = ExperimentRunner("minimum-check").execute(small)
        self.assertEqual(record["status"], "failed")
        self.assertIsNone(simulation)
        self.assertEqual(record["frames"], [])
        raw = small.as_dict(); raw["majority_estimation"] = {"poll_counts": [50, 30, 20]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot"
            with self.assertRaisesRegex(ElectionError, "at least 100"):
                run_pilot(output, seeds=[101], scenario=make_scenario(raw))
            self.assertFalse(output.exists())

    def test_benchmark_generator_obeys_minimum(self):
        with self.assertRaisesRegex(ElectionError, "at least 100"):
            scenario_text(99, 1, 101)
        self.assertEqual(len(tomllib.loads(scenario_text(100, 1, 101))["people"]), 100)

    def test_demo_has_200_distinct_moving_voters_and_memory_estimates(self):
        with Path("examples/recent-majority.toml").open("rb") as handle:
            configured = make_scenario(tomllib.load(handle))
        self.assertEqual(len(configured.people), 200)
        self.assertEqual(len({p.id for p in configured.people}), 200)
        self.assertTrue(all(g.movement == "random_walk" and g.max_step > 0 for g in configured.groups))
        simulation = Simulation(configured)
        frame = simulation.step()
        self.assertEqual(len(frame.ballots), 200)
        self.assertEqual(len(frame.majority_states), 200)
        self.assertGreater(sum(len(state.entries) for _, state in frame.majority_states), 0)
        snapshot = Session(simulation).snapshot()
        self.assertNotIn("verification_only", snapshot)

    def test_production_http_200_startup_step_and_checkpoint(self):
        with Path("examples/recent-majority.toml").open("rb") as handle:
            simulation = Simulation(make_scenario(tomllib.load(handle)))
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/") as response:
                html = response.read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}

            def fetch(path, value=None):
                data = None if value is None else json.dumps(value).encode()
                with urlopen(Request(base + path, data=data, headers=headers)) as response:
                    return json.loads(response.read())

            initial = fetch("/state")
            self.assertNotIn("verification_only", initial)
            self.assertEqual(len(initial["frames"][0]["ballots"]), 200)
            configured = fetch("/command", {"action": "configure_voting", "revision": 0,
                                            "policy": "memory_pivotal", "parameters": {}})
            self.assertNotIn("verification_only", configured)
            self.assertEqual(len(configured["frames"][0]["ballots"]), 200)
            tally_after_ten = None
            for revision in range(1, 12):
                result = fetch("/command", {"action": "step", "revision": revision})
                self.assertEqual(result["frame"]["round"], revision)
                self.assertEqual(sum(result["metric"]["counts"].values()), 200)
                self.assertEqual(len(result["frame"]["majority_estimation"]), 200)
                self.assertEqual(result["frame"]["policy_memory"]["p000"]["policy"], "memory_pivotal")
                self.assertEqual(result["frame"]["policy_memory"]["p000"]["convergence"], "uncertified")
                if revision == 10:
                    tally_after_ten = result["metric"]["counts"]
                if revision == 11:
                    belief = result["frame"]["majority_estimation"]["p000"]
                    self.assertEqual(belief["poll_round"], 10)
                    self.assertEqual(belief["poll_weight"], 1)
                    self.assertEqual(belief["poll_counts"], [tally_after_ten[c] for c in ("A", "B", "C")])
            replay = Simulation.from_checkpoint(fetch("/checkpoint"))
            self.assertEqual(replay.current.as_dict(), result["frame"])
            self.assertIsNone(replay.verification_reason)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
