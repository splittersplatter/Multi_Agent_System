"""Adversarial boundaries introduced or exposed by the structural audit."""

import copy
import math
import random
from dataclasses import replace
from pathlib import Path
import unittest
from verification_support import VerificationTestCase
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.alignment import _bounded_move
from multi_agent_election.experiment_support import ExperimentRunner, RuntimeMismatch, movement_matched
from multi_agent_election.network import proximity_edges
from multi_agent_election.provenance import manifest
from scripts.audit_implementation import compare
from test_baseline import example


class RefinementTests(VerificationTestCase):
    def test_representable_residual_moves_respect_hard_path_budget(self):
        origin = (0.0568202538227679, 0.24859391180086332)
        direction = (-0.15690670490956715, -0.987613429411742)
        limit = 1.017237313865996e-14
        result, cost = _bounded_move(origin, direction, limit)
        self.assertGreater(cost, 0)
        self.assertLessEqual(cost, limit)
        self.assertEqual(cost, math.dist(origin, result))
        rng = random.Random(9701)
        for _ in range(1000):
            origin = (rng.random(), rng.random())
            angle = rng.random() * math.tau
            direction = (math.cos(angle), math.sin(angle))
            limit = 10 ** rng.uniform(-18, -12)
            result, cost = _bounded_move(origin, direction, limit)
            self.assertLessEqual(cost, limit)
            self.assertEqual(cost, math.dist(origin, result))
            self.assertTrue(all(0 <= x <= 1 for x in result))
            self.assertTrue(all((after - before) * d >= 0 for before, after, d in zip(origin, result, direction)))

    def test_dataclass_replacement_cannot_bypass_scenario_validation(self):
        scenario = make_scenario(example())
        invalid = [replace(scenario, seed=-1), replace(scenario, rounds=-1),
                   replace(scenario, people=(scenario.people[0], scenario.people[0])),
                   replace(scenario, people=(replace(scenario.people[0], group="absent"),)),
                   replace(scenario, groups=(replace(scenario.groups[0], voting="absent"),))]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ElectionError):
                Simulation(value)

    def test_zero_radius_does_not_compare_unrelated_pairs(self):
        positions = {str(i): (i / 10000, i / 10000) for i in range(10000)}
        with patch("multi_agent_election.network.math.hypot", side_effect=AssertionError("unnecessary distance")):
            self.assertEqual(proximity_edges(positions, 0), ())
            self.assertEqual(proximity_edges({"a": (0, 0), "b": (0, 0), "c": (0, 0), "d": (1, 1)},
                                             None, {"a": 0, "b": None, "c": 0}),
                             (("a", "c"), ("b", "a"), ("b", "c"), ("c", "a")))

    def test_experiment_failure_retains_prefix_and_does_not_mutate_configuration(self):
        data = example()
        data["interventions"] = [{"round": 2, "person": "1", "remove_edges": ["2"]}]
        original = copy.deepcopy(data)
        runner = ExperimentRunner("audit")
        run, sim = runner.execute(data)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["completed_round"], 1)
        self.assertEqual([frame["round"] for frame in run["frames"]], [0, 1])
        self.assertEqual([row["round"] for row in run["metrics"]], [0, 1])
        self.assertEqual(data, original)
        self.assertEqual(sim.current.round, 1)

    def test_manifest_change_during_last_arm_is_terminal(self):
        runner = ExperimentRunner("audit")
        current = manifest()
        altered = {**current, "core_sha256": "different"}
        with patch("multi_agent_election.experiment_support.manifest", side_effect=[current, altered]):
            with self.assertRaises(RuntimeMismatch):
                runner.execute(example())
        # A later arm must not replace the accepted implementation identity.
        runner = ExperimentRunner("audit")
        runner.execute(example())
        with patch("multi_agent_election.experiment_support.manifest", return_value=altered):
            with self.assertRaises(RuntimeMismatch):
                runner.execute(example())

    def test_web_and_extracted_sources_are_fingerprinted(self):
        current = manifest()
        original = Path.read_bytes
        for name, key in (("exports.py", "pipeline_sha256"), ("records.py", "core_sha256"),
                          ("coalitions.py", "core_sha256"), ("observations.py", "core_sha256"),
                          ("experiment_support.py", "pipeline_sha256"), ("app.js", "pipeline_sha256"),
                          ("spatial_experiments.py", "pipeline_sha256"), ("signal_experiments.py", "pipeline_sha256"),
                          ("network_experiments.py", "pipeline_sha256")):
            def changed(path, selected=name):
                return original(path) + (b"\n# probe" if path.name == selected else b"")
            with self.subTest(name=name), patch.object(Path, "read_bytes", changed):
                self.assertNotEqual(manifest()[key], current[key])

    def test_pairing_requires_same_horizon_and_timestamps(self):
        one = {"round": 0, "positions": {"a": [0, 0]}}
        two = {"round": 1, "positions": {"a": [0, 0]}}
        control = {"status": "ok", "frames": [one, two]}
        self.assertFalse(movement_matched({"status": "ok", "frames": [one]}, control))
        self.assertFalse(movement_matched({"status": "ok", "frames": [one, one]}, control))
        self.assertIsNone(movement_matched(control, {"status": "failed"}))

    def test_audit_comparison_rejects_missing_or_changed_examples(self):
        record = {"record_type": "eclipse.implementation-audit", "record_version": 1, "max_rounds": 6,
                  "rows": [{"path": "a", "status": "ok", "frames_sha256": "abc"}]}
        changed = copy.deepcopy(record)
        changed["rows"][0]["frames_sha256"] = "bad"
        self.assertEqual(compare(record, changed), ["a"])
        changed["rows"] = []
        self.assertEqual(compare(record, changed), ["a"])
        changed["max_rounds"] = 5
        with self.assertRaisesRegex(ValueError, "horizons"):
            compare(record, changed)


if __name__ == "__main__":
    unittest.main()
