import contextlib
import copy
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import calibrate_and_evaluate_detector, compare_leaders
from multi_agent_election.leaders import advance_leaders
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.model import LeaderConfig
from multi_agent_election.policies import Observation, policy_rng
from multi_agent_election.visual import Session


def example():
    with Path("examples/leader-adaptation.toml").open("rb") as handle:
        return tomllib.load(handle)


class LeaderTests(VerificationTestCase):
    def test_feedback_uses_only_public_support_and_own_action(self):
        config = LeaderConfig("feedback", ("A",), 0.1, 1.0, "none", 0.0, 1.0)
        parties = ("A", "B"); true = {"A": (0.2, 0.5), "B": (0.9, 0.5)}
        perceived = dict(true); spend = {"A": 0.0, "B": 0.0}; memory = {"A": (None, None), "B": (None, None)}
        t1, p1, s1, m1, _ = advance_leaders(config, 1, 1, parties, {"A": 2, "B": 2}, true, perceived, spend, memory)
        self.assertAlmostEqual(t1["A"][0], 0.3); self.assertEqual(m1["A"], (0, 2))
        t2, p2, s2, m2, _ = advance_leaders(config, 1, 2, parties, {"A": 1, "B": 3}, t1, p1, s1, m1)
        self.assertAlmostEqual(t2["A"][0], 0.2); self.assertEqual(m2["A"], (1, 1))
        t3, _, _, m3, _ = advance_leaders(config, 1, 3, parties, {"A": 1, "B": 3}, t2, p2, s2, m2)
        self.assertAlmostEqual(t3["A"][1], 0.6); self.assertEqual(m3["A"], (2, 1))
        self.assertEqual(t3["B"], true["B"])

    def test_hidden_leader_cannot_leak_with_no_signal(self):
        data = example(); data["leaders"]["signal_mode"] = "none"
        fixed = copy.deepcopy(data); fixed["leaders"]["policy"] = "fixed"
        a, b = Simulation(make_scenario(data)), Simulation(make_scenario(fixed)); a.run(); b.run()
        self.assertNotEqual(a.current.leader_true, b.current.leader_true)
        self.assertEqual([f.leader_perceived for f in a.frames], [f.leader_perceived for f in b.frames])
        self.assertEqual([f.ballots for f in a.frames], [f.ballots for f in b.frames])
        self.assertEqual([f.preferences for f in a.frames], [f.preferences for f in b.frames])
        self.assertEqual([f.detector for f in a.frames], [f.detector for f in b.frames])
        self.assertTrue(all(f.leader_signals is None for f in a.frames))
        self.assertNotEqual(frame_metrics(a.scenario, a.current)["mean_winner_true_current_distance"],
                            frame_metrics(b.scenario, b.current)["mean_winner_true_current_distance"])

    def test_no_signal_with_voter_attacks_uses_previous_perception_not_hidden_truth(self):
        data = example(); data["leaders"]["signal_mode"] = "none"
        data["alignment"] = {"drift_max_step": 0.03,
                             "attack": {"target": "alice", "policy": "toward_target", "targets": ["bob"],
                                        "per_person_round": 0.1, "total_budget": 0.3, "observe_target_ideals": True}}
        fixed = copy.deepcopy(data); fixed["leaders"]["policy"] = "fixed"
        a, b = Simulation(make_scenario(data)), Simulation(make_scenario(fixed)); a.run(); b.run()
        self.assertNotEqual(a.current.leader_true, b.current.leader_true)
        self.assertEqual([f.alignment_changes for f in a.frames], [f.alignment_changes for f in b.frames])
        self.assertEqual([f.ballots for f in a.frames], [f.ballots for f in b.frames])
        self.assertEqual([f.detector for f in a.frames], [f.detector for f in b.frames])

    def test_budgets_noisy_signals_perception_and_reproducibility(self):
        scenario = make_scenario(example()); sim = Simulation(scenario); sim.run()
        self.assertEqual(sim.frames, list(Simulation(scenario).run()))
        for frame, previous in zip(sim.frames[1:], sim.frames):
            truth, signals, perceived = dict(frame.leader_true), dict(frame.leader_signals), dict(frame.leader_perceived)
            prior, old_truth = dict(previous.leader_perceived), dict(previous.leader_true)
            for party in scenario.parties:
                self.assertLessEqual(math.dist(truth[party], old_truth[party]), scenario.leaders.per_round_step)
                self.assertLessEqual(dict(frame.leader_spend)[party], scenario.leaders.lifetime_budget)
                rng = policy_rng(scenario.seed, party, frame.round, "leader-signal")
                expected = tuple(min(1, max(0, x + rng.uniform(-0.05, 0.05))) for x in truth[party])
                self.assertEqual(signals[party], expected)
                self.assertEqual(perceived[party], tuple(0.5 * x + 0.5 * y for x, y in zip(prior[party], expected)))
                self.assertTrue(all(0 <= x <= 1 for x in signals[party]))
        self.assertEqual(dict(sim.current.leader_spend)["cara"], 0)

    def test_fixed_and_zero_step_are_equivalent_with_same_signal(self):
        data = example(); data["leaders"]["per_round_step"] = 0
        fixed = copy.deepcopy(data); fixed["leaders"]["policy"] = "fixed"
        a, b = Simulation(make_scenario(data)), Simulation(make_scenario(fixed)); a.run(); b.run()
        self.assertEqual(a.frames, b.frames)

    def test_multiple_leaders_simultaneous_boundary_and_independent_budgets(self):
        data = example(); data["leaders"].update(adaptors=["cara", "alice"], signal_noise=0, perception_weight=1)
        sim = Simulation(make_scenario(data)); sim.step()
        truth, spent = dict(sim.current.leader_true), dict(sim.current.leader_spend)
        self.assertAlmostEqual(truth["alice"][0], 0.2)
        self.assertAlmostEqual(truth["cara"][0], 0.8)  # + axis is clipped, then - axis
        self.assertAlmostEqual(spent["alice"], 0.2); self.assertAlmostEqual(spent["cara"], 0.2)
        self.assertEqual(dict(sim.current.leader_perceived), truth)
        sim.run(4)
        self.assertTrue(all(value <= 0.5 for value in dict(sim.current.leader_spend).values()))

    def test_detector_calibration_keeps_honest_adaptation_in_baseline(self):
        data = example(); data["alignment"] = {"drift_max_step": 0.02,
                         "attack": {"target": "alice", "policy": "none", "targets": ["bob"],
                                    "per_person_round": 0.1, "total_budget": 0.2, "observe_target_ideals": True}}
        result = calibrate_and_evaluate_detector(make_scenario(data), [1, 2], [3], 0.1)
        self.assertEqual(result["status"], "ok")
        for record in result["calibration"]:
            self.assertEqual(record["scenario"]["leaders"]["policy"], "feedback")
            self.assertEqual(record["scenario"]["alignment"]["attack"]["policy"], "none")
        self.assertEqual(result["summary"]["drift_only"]["completed"], 1)

    def test_voter_observation_contains_only_own_ideal_and_perceived_leaders(self):
        data = example(); data["groups"]["residents"]["voting"] = "python:strategy_fixture:capture_leader_scope"
        sim = Simulation(make_scenario(data)); sim.step()
        traces = sim.current.as_dict()["policy_memory"]
        self.assertEqual(traces["bob"]["own_ideal"], [0.4, 0.5])
        self.assertFalse(traces["bob"]["exposes_true"])
        self.assertEqual(dict(traces["bob"]["perceived"]), {p: list(v) for p, v in sim.current.leader_perceived})
        self.assertNotIn("leader_true", Observation.__dataclass_fields__)
        self.assertNotIn("other_ideals", Observation.__dataclass_fields__)

    def test_hidden_voter_ideals_do_not_affect_identical_public_history(self):
        left = example(); right = copy.deepcopy(left); right["people"][1]["ideal"] = [0.2, 0.5]
        a, b = Simulation(make_scenario(left)), Simulation(make_scenario(right))
        self.assertEqual(a.current.counts, b.current.counts)
        a.step(); b.step()
        self.assertEqual(a.current.leader_true, b.current.leader_true)
        self.assertEqual(a.current.leader_signals, b.current.leader_signals)

    def test_comparison_controls_invariants_replay_and_unconfounded_alerts(self):
        scenario = make_scenario(example()); result = compare_leaders(scenario, [11, 22])
        self.assertEqual(result, compare_leaders(scenario, [11, 22]))
        self.assertTrue(result["honest_exogenous_configuration"])
        for row in result["rows"]:
            for arm, run in row["runs"].items():
                self.assertEqual(run["status"], "ok"); self.assertTrue(run["movement_matched"])
                replay = Simulation(make_scenario(run["scenario"])); replay.run()
                self.assertEqual(run["frames"], [frame.as_dict() for frame in replay.frames])
                self.assertIsInstance(run["honest_adaptation_alert"], bool)
            fixed, adaptive = row["runs"]["fixed_no_signal"], row["runs"]["adaptive_no_signal"]
            self.assertTrue(adaptive["nonsignal_invariant"])
            self.assertEqual([f["ballots"] for f in fixed["frames"]], [f["ballots"] for f in adaptive["frames"]])
            self.assertEqual(row["runs"]["adaptive_broadcast"]["baseline"], "fixed_broadcast")
        data = example(); data["signal_controller"] = {"target": "alice", "policy": "target_biased", "schedule": "repeated",
                                                        "per_broadcast_budget": 1, "lifetime_budget": 1}
        confounded = compare_leaders(make_scenario(data), [1])
        self.assertFalse(confounded["honest_exogenous_configuration"])
        self.assertTrue(all(run["honest_adaptation_alert"] is None for run in confounded["rows"][0]["runs"].values()))

    def test_comparison_failure_missing_controls_and_exclusive_cli(self):
        from unittest.mock import patch
        scenario = make_scenario(example()); real_step = Simulation.step
        def fail_control(sim):
            if sim.scenario.leaders.policy == "fixed" and sim.scenario.leaders.signal_mode == "none":
                raise ElectionError("deliberate baseline failure")
            return real_step(sim)
        with patch.object(Simulation, "step", fail_control):
            runs = compare_leaders(scenario, [1])["rows"][0]["runs"]
        self.assertEqual(runs["fixed_no_signal"]["status"], "failed")
        self.assertEqual(runs["adaptive_no_signal"]["status"], "ok")
        self.assertIsNone(runs["adaptive_no_signal"]["movement_matched"])
        self.assertNotIn("nonsignal_invariant", runs["adaptive_no_signal"])
        self.assertIn("paired", runs["adaptive_broadcast"])
        for seeds in ([], [1, 1], [True], [-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): compare_leaders(scenario, seeds)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "comparison.json"; stdout = io.StringIO()
            args = ["compare-leaders", "examples/leader-adaptation.toml", "--seeds", "1", "2", "--output", str(output)]
            with contextlib.redirect_stdout(stdout): self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(stdout.getvalue())["invariant_failures"], 0)
            saved = json.loads(output.read_text())
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)

    def test_validation_manual_edits_checkpoint_and_output(self):
        changes = [lambda x: x["leaders"].update(policy="invented"),
                   lambda x: x["leaders"].update(adaptors=["bob"]),
                   lambda x: x["leaders"].update(adaptors=["alice", "alice"]),
                   lambda x: x["leaders"].update(signal_mode="unknown"),
                   lambda x: x["leaders"].update(per_round_step=-1),
                   lambda x: x["leaders"].update(signal_noise=True),
                   lambda x: x["leaders"].update(perception_weight=1.1),
                   lambda x: x.update(interventions=[{"round": 1, "person": "bob", "preference": ["cara", "alice"]}]),
                   lambda x: x.update(convergence={"case": "direct_best_response"})]
        for change in changes:
            data = example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        sim = Simulation(make_scenario(example())); session = Session(sim); session.command({"revision": 0, "action": "step"})
        original = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "derive preferences"): sim.edit_after(1, "bob", preference=["cara", "alice"])
        self.assertEqual(sim.checkpoint(), original)
        self.assertEqual(Simulation.from_checkpoint(original).current, sim.current)
        old = copy.deepcopy(original); old["version"] = 20
        with self.assertRaisesRegex(ElectionError, "version 21"): Simulation.from_checkpoint(old)
        for field in ("true", "perceived", "spend", "memory", "signals"):
            changed = copy.deepcopy(original)
            if field in ("true", "perceived", "signals"): changed["frames"][1]["leaders"][field]["alice"][0] = 0.99
            elif field == "spend": changed["frames"][1]["leaders"][field]["alice"] = 0
            else: changed["frames"][1]["leaders"][field]["alice"]["last_direction"] = 99
            with self.subTest(field=field), self.assertRaisesRegex(ElectionError, "history"): Simulation.from_checkpoint(changed)
        sim.edit_after(0, "bob", ballot=["cara", "alice"]); sim.run(3)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"; output = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/leader-adaptation.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(output)]), 0)
            with output.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertAlmostEqual(float(rows[1]["leader_true:alice:1"]), 0.2)
            self.assertEqual(rows[0]["leader_signal:alice:1"], "")


if __name__ == "__main__": unittest.main()
