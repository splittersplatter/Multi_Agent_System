import json
import os
import subprocess
import sys
import unittest


class ExampleTests(unittest.TestCase):
    def test_campaign_layer_example_survives_then_is_removed(self):
        env = {**os.environ, "PYTHONPATH": "src"}
        result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "run", "examples/campaign-layer.toml"],
                                capture_output=True, text=True, env=env, check=True)
        data = json.loads(result.stdout)
        self.assertEqual([row["campaign_edge_count"] for row in data["metrics"]], [1, 1, 0, 0])
        self.assertEqual([frame["ballots"]["2"] for frame in data["frames"]],
                         [["B", "A"], ["A", "B"], ["B", "A"], ["B", "A"]])
        self.assertEqual(data["frames"][1]["proximity_edges"], [])

    def test_sensor_example_distinguishes_trusted_ballots_from_reports(self):
        env = {**os.environ, "PYTHONPATH": "src"}
        result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "run", "examples/sensors.toml"],
                                capture_output=True, text=True, env=env, check=True)
        data = json.loads(result.stdout)
        self.assertEqual([frame["ballots"]["2"] for frame in data["frames"]], [["B", "A"], ["A", "B"], ["C", "B"]])
        self.assertEqual([frame["ballots"]["3"] for frame in data["frames"]], [["B", "A"]] * 3)
        self.assertEqual([row["sensor_observation_count"] for row in data["metrics"]], [0, 1, 1])
        self.assertEqual(data["frames"][2]["ballot_sensors"], [["2", "1", "public", 1, ["C", "A"]]])

    def test_restricted_example_delivers_only_authorized_reports(self):
        env = {**os.environ, "PYTHONPATH": "src"}
        result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "run", "examples/restricted.toml"],
                                capture_output=True, text=True, env=env, check=True)
        data = json.loads(result.stdout)
        delivered = data["frames"][2]["delivered"]
        self.assertEqual([message[:3] for message in delivered], [["1", "2", "team"]])
        self.assertEqual(data["frames"][1]["ballots"]["2"], ["B", "A"])
        self.assertEqual(data["frames"][2]["ballots"]["2"], ["A", "B"])

    def test_custom_example_executes_all_four_policy_phases(self):
        env = {**os.environ, "PYTHONPATH": "src:examples"}
        result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "run", "examples/custom.toml"],
                                capture_output=True, text=True, env=env, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["frames"]), 4)
        first = data["frames"][1]
        self.assertAlmostEqual(first["positions"]["1"][0], 0.23)
        self.assertEqual(first["ballots"]["1"], ["C", "A"])
        self.assertIn(["1", "2"], first["persistent_edges"])
        self.assertTrue(any(message[0:3] == ["1", "2", "public"] for message in first["pending"]))
        self.assertEqual(len(data["policy_digests"]), 4)


if __name__ == "__main__": unittest.main()
