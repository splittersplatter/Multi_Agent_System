import copy
import io
import contextlib
import tomllib
import unittest
from verification_support import VerificationTestCase
from pathlib import Path

from multi_agent_election import ElectionError, Simulation, count_plurality, make_scenario
from multi_agent_election.cli import main


def example():
    with Path("examples/baseline.toml").open("rb") as handle:
        return tomllib.load(handle)


class BaselineTests(VerificationTestCase):
    def test_hand_worked_case_and_repeat(self):
        simulation = Simulation(make_scenario(example()))
        frames = simulation.run()
        self.assertEqual(len(frames), 3)
        self.assertEqual([f.round for f in frames], [0, 1, 2])
        for frame in frames:
            self.assertEqual(dict(frame.counts), {"A": 2, "B": 2, "C": 0})
            self.assertEqual(frame.winner, "A")
            self.assertEqual(dict(frame.ballots)["2"], ("A", "C"))

    def test_counterexample_manipulated_ballot(self):
        counts, winner = count_plurality(("A", "B", "C"), 2, {"1": ("A", "B"), "2": ("C", "A"), "3": ("B", "C"), "4": ("B", "A")})
        self.assertEqual(dict(counts), {"A": 1, "B": 2, "C": 1})
        self.assertEqual(winner, "B")

    def test_tie_order_and_k_boundaries(self):
        for k in (1, 2, 3):
            scenario = example(); scenario["k"] = k
            frame = Simulation(make_scenario(scenario)).current
            self.assertTrue(all(len(b) == k for _, b in frame.ballots))
        _, winner = count_plurality(("B", "A"), 1, {"1": ("A",), "2": ("B",)})
        self.assertEqual(winner, "B")

    def test_invalid_scenario_does_not_get_normalized_away(self):
        changes = [lambda x: x.update(k=0), lambda x: x.update(k=4), lambda x: x.update(k=True),
                   lambda x: x.update(rounds=-1), lambda x: x.update(seed=-1),
                   lambda x: x["parties"].append("A"), lambda x: x["people"][0].update(group="missing"),
                   lambda x: x["people"][0].update(preference=["A", "A", "C"]),
                   lambda x: x["people"][0].update(id="2"),
                   lambda x: x["groups"]["residents"].update(voting="nonexistent"),
                   lambda x: x.update(unrecognized=True)]
        for change in changes:
            with self.subTest(change=change):
                data = copy.deepcopy(example()); change(data)
                with self.assertRaises(ElectionError): make_scenario(data)

    def test_invalid_ballots_fail_explicitly(self):
        for ballot in [("A", "A"), ("A", "Z"), ("A",), "AB", ("A", ["B"])]:
            with self.subTest(ballot=ballot), self.assertRaises(ElectionError):
                count_plurality(("A", "B", "C"), 2, {"v": ballot})
        with self.assertRaises(ElectionError): count_plurality(("A",), 1, {})
        for invalid in ("ABC", ("A", []), ("",), None):
            with self.subTest(parties=invalid), self.assertRaises(ElectionError):
                count_plurality(invalid, 1, {"v": ("A",)})

    def test_replay_and_invalid_step_are_safe(self):
        scenario = make_scenario(example())
        a, b = Simulation(scenario), Simulation(scenario)
        self.assertEqual(a.run(), b.run())
        old = tuple(a.frames)
        with self.assertRaises(ElectionError): a.run(-1)
        self.assertEqual(tuple(a.frames), old)

    def test_cli_exit_on_failure_and_valid_json(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["run", "missing-scenario.toml"]), 2)
            self.assertEqual(main(["run", "examples/baseline.toml"]), 0)
        self.assertIn("error:", err.getvalue())
        import json
        self.assertEqual(json.loads(out.getvalue())["frames"][0]["winner"], "A")

    def test_checkpoint_roundtrip_rejects_tampering(self):
        simulation = Simulation(make_scenario(example()))
        simulation.run(2)
        restored = Simulation.from_checkpoint(simulation.checkpoint())
        self.assertEqual(restored.run(3), simulation.run(3))
        bad = copy.deepcopy(restored.checkpoint())
        bad["frames"][1]["winner"] = "C"
        with self.assertRaises(ElectionError): Simulation.from_checkpoint(bad)
        bad = copy.deepcopy(restored.checkpoint()); bad["version"] = True
        with self.assertRaises(ElectionError): Simulation.from_checkpoint(bad)
        old_runtime = copy.deepcopy(restored.checkpoint()); old_runtime["manifest"]["python"] = "different"
        with self.assertRaisesRegex(ElectionError, "runtime or core source changed"):
            Simulation.from_checkpoint(old_runtime)
        self.assertEqual(Simulation.from_checkpoint(old_runtime, allow_environment_change=True).current, restored.current)

    def test_runtime_change_stops_mutations_and_preserves_history_identity(self):
        from unittest.mock import patch
        sim = Simulation(make_scenario(example()))
        sim.step()
        before = sim.checkpoint()
        changed = dict(before["manifest"], core_sha256="changed")
        with patch("multi_agent_election.engine.manifest", return_value=changed):
            with self.assertRaisesRegex(ElectionError, "source changed during run"):
                sim.step()
            with self.assertRaisesRegex(ElectionError, "source changed during run"):
                sim.edit_after(0, "1", position=[0.2, 0.3])
            self.assertEqual(sim.checkpoint(), before)

    def test_known_version_one_layout_migrates_by_replay(self):
        simulation = Simulation(make_scenario(example())); simulation.run(2)
        payload = simulation.checkpoint()
        payload["version"] = 1
        del payload["manifest"], payload["manual_interventions"], payload["policy_digests"]
        keep = {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges"}
        payload["frames"] = [{key: frame[key] for key in keep} for frame in payload["frames"]]
        self.assertEqual(Simulation.from_checkpoint(payload).current, simulation.current)

    def test_rewind_edit_invalidates_future_and_replays(self):
        sim = Simulation(make_scenario(example())); original = sim.run(4)
        sim.edit_after(1, "2", preference=["C", "A", "B"])
        self.assertEqual(tuple(sim.frames), original[:2])
        sim.edit_after(1, "1", position=[0.2, 0.2])
        resumed = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), resumed.step())
        self.assertEqual(sim.current.winner, "B")
        self.assertEqual(dict(sim.current.positions)["1"], (0.2, 0.2))
        saved = sim.checkpoint()
        with self.assertRaises(ElectionError): sim.edit_after(99, "1", position=[0, 0])
        with self.assertRaises(ElectionError): sim.edit_after(1, "1", **{"round": 99, "position": [0, 0]})
        with self.assertRaises(ElectionError): sim.edit_after(1, "1", position=None)
        self.assertEqual(sim.checkpoint(), saved)
        sim.edit_after(0, "1", group="residents")
        self.assertEqual(len(sim.frames), 1)
        self.assertEqual(len(sim.manual_interventions), 1)


if __name__ == "__main__":
    unittest.main()
