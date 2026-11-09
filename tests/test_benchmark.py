import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase
from pathlib import Path

from multi_agent_election import Simulation, make_scenario


class BenchmarkTests(VerificationTestCase):
    def test_generated_scenario_is_deterministic_and_cannot_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.toml"
            cmd = [sys.executable, "scripts/benchmark_simulator.py", "generate", "--agents", "100",
                   "--rounds", "2", "--seed", "42", "--output", str(path)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            original = path.read_bytes()
            scenario = make_scenario(tomllib.loads(original.decode()))
            self.assertEqual((len(scenario.people), scenario.k, scenario.rounds), (100, 3, 2))
            self.assertEqual(len(Simulation(scenario).run()), 3)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(path.read_bytes(), original)
            another = Path(directory) / "again.toml"
            subprocess.run(cmd[:-1] + [str(another)], check=True, capture_output=True, text=True)
            self.assertEqual(another.read_bytes(), original)

    def test_cli_benchmark_runs_real_summary_and_rejects_invalid_size(self):
        cmd = [sys.executable, "scripts/benchmark_simulator.py", "cli", "--agents", "100", "--rounds", "2"]
        output = subprocess.run(cmd, check=True, capture_output=True, text=True)
        report = json.loads(output.stdout)
        self.assertEqual((report["mode"], report["agents"], report["rounds"]), ("cli-summary", 100, 2))
        self.assertGreater(report["agent_rounds_per_second"], 0)
        self.assertTrue(report["manifest"]["core_sha256"])
        self.assertNotEqual(subprocess.run(cmd[:3] + ["--agents", "1", "--rounds", "2"], capture_output=True).returncode, 0)

    def test_http_benchmark_checks_committed_rounds_and_reports_rss(self):
        cmd = [sys.executable, "scripts/benchmark_simulator.py", "http", "--agents", "100", "--rounds", "2"]
        output = subprocess.run(cmd, check=True, capture_output=True, text=True)
        report = json.loads(output.stdout)
        self.assertEqual((report["mode"], report["agents"], report["rounds"]), ("http-steps", 100, 2))
        self.assertGreater(report["mean_ms"], 0)
        self.assertGreater(report["mean_response_bytes"], 0)
        self.assertIn("excludes browser", report["includes"])

    def test_sensor_benchmark_exercises_real_sensor_observations(self):
        cmd = [sys.executable, "scripts/benchmark_simulator.py", "http", "--agents", "100", "--rounds", "2", "--sensors"]
        output = subprocess.run(cmd, check=True, capture_output=True, text=True)
        report = json.loads(output.stdout)
        self.assertTrue(report["sensors_enabled"])
        self.assertGreater(report["sensor_observations_final"], 0)


if __name__ == "__main__":
    unittest.main()
