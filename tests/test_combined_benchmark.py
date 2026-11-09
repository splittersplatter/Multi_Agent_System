import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.metrics import series
from scripts.benchmark_combined import activity, scenario_text


SCRIPT = "scripts/benchmark_combined.py"


class CombinedBenchmarkTests(VerificationTestCase):
    def test_generator_is_reproducible_valid_and_exercises_full_stack(self):
        for agents in (4, 8, 24):
            text = scenario_text(agents, 3, 42)
            self.assertEqual(text, scenario_text(agents, 3, 42))
            scenario = make_scenario(tomllib.loads(text))
            self.assertEqual(len(scenario.people), agents)
            self.assertEqual(scenario.parties, ("alice", "cara"))
            self.assertEqual(scenario.nomination.mode, "endogenous")
            self.assertEqual(scenario.alignment.attack.policy, "toward_target")
            self.assertEqual(scenario.leaders.policy, "feedback")
            self.assertEqual(scenario.signal_controller.policy, "target_biased")
            self.assertEqual(scenario.campaign_controller.policy, "target_heuristic")
            self.assertIsNotNone(scenario.detector)
            sim = Simulation(scenario); sim.run()
            observed = activity(series(scenario, sim.frames))
            self.assertGreater(observed["coalition_sight_events"], 0)
            self.assertGreater(observed["deceptive_reports"], 0)
            self.assertGreater(observed["ideal_attack_spend"], 0)
            self.assertGreater(observed["leader_move_spend"], 0)
            self.assertGreater(observed["signal_spend"], 0)
            self.assertGreater(observed["campaign_edges_purchased"], 0)
            if agents > 4: self.assertGreater(observed["trusted_sensor_observations"], 0)

    def test_cli_http_metrics_match_direct_engine_and_isolated_repeats(self):
        results = {}
        for mode in ("cli", "http"):
            cmd = [sys.executable, SCRIPT, mode, "--agents", "100", "--rounds", "2", "--seed", "42", "--repetitions", "2"]
            result = json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout)
            self.assertEqual(result["sensor_enabled_people"], 10)
            self.assertEqual(len(result["runs"]), 2)
            self.assertTrue(all(run["status"] == "ok" for run in result["runs"]))
            self.assertEqual(result["runs"][0]["metrics"], result["runs"][1]["metrics"])
            self.assertTrue(result["runs"][0]["manifest"]["core_sha256"])
            self.assertIn("excludes browser", result["runs"][0]["includes"])
            self.assertEqual(result["scenario_sha256"], hashlib.sha256(scenario_text(100, 2, 42).encode()).hexdigest())
            results[mode] = result
        scenario = make_scenario(tomllib.loads(scenario_text(100, 2, 42)))
        sim = Simulation(scenario); sim.run()
        expected = series(scenario, sim.frames)
        self.assertEqual(results["cli"]["runs"][0]["metrics"], expected)
        self.assertEqual(results["http"]["runs"][0]["metrics"], expected)
        self.assertEqual(results["cli"]["runs"][0]["activity"], results["http"]["runs"][0]["activity"])
        self.assertGreater(results["http"]["runs"][0]["p95_ms"], 0)
        self.assertGreater(results["cli"]["runs"][0]["agent_rounds_per_second"], 0)

    def test_paths_validation_timeouts_and_nonoverwrite(self):
        invalid = [sys.executable, SCRIPT, "cli", "--agents", "3", "--rounds", "1"]
        self.assertNotEqual(subprocess.run(invalid, capture_output=True).returncode, 0)
        invalid = [sys.executable, SCRIPT, "http", "--agents", "100", "--rounds", "0"]
        self.assertNotEqual(subprocess.run(invalid, capture_output=True).returncode, 0)
        timeout = [sys.executable, SCRIPT, "cli", "--agents", "100", "--rounds", "2", "--timeout-seconds", "0.001"]
        record = json.loads(subprocess.run(timeout, check=True, capture_output=True, text=True).stdout)
        self.assertEqual(record["runs"][0]["status"], "timed_out")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = root / "scenario.toml"; report = root / "report.json"
            generate = [sys.executable, SCRIPT, "generate", "--agents", "100", "--rounds", "2", "--output", str(config)]
            subprocess.run(generate, check=True, capture_output=True, text=True)
            original = config.read_bytes()
            self.assertNotEqual(subprocess.run(generate, capture_output=True).returncode, 0)
            self.assertEqual(config.read_bytes(), original)
            command = [sys.executable, SCRIPT, "cli", "--agents", "100", "--rounds", "2", "--output", str(report)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            saved = report.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(report.read_bytes(), saved)
            missing = command[:-1] + [str(root / "missing" / "out.json")]
            self.assertNotEqual(subprocess.run(missing, capture_output=True).returncode, 0)


if __name__ == "__main__": unittest.main()
