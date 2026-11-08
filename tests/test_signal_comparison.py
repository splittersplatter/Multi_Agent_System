import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import compare_signal_responses
from multi_agent_election.metrics import series


def example():
    with Path("examples/epistemic-public-signal.toml").open("rb") as handle:
        return tomllib.load(handle)


class SignalComparisonTests(unittest.TestCase):
    def test_factorial_runs_replay_pairing_and_hand_worked_first_round(self):
        data = example()
        data["groups"]["residents"].update(movement="random_walk", max_step=0.02)
        scenario = make_scenario(data)
        result = compare_signal_responses(scenario, [11, 22], ["signal_voter"], 1)
        self.assertEqual(result["responses"], ["sincere", "signal_confident", "epistemic_signal_dominant"])
        self.assertEqual(result["signal_policies"], ["truthful", "bounded_random", "target_biased"])
        for row in result["rows"]:
            for response, arms in row["runs"].items():
                baseline = arms["truthful"]
                for policy, run in arms.items():
                    self.assertEqual(run["status"], "ok")
                    self.assertTrue(run["movement_matched"])
                    self.assertEqual([f["positions"] for f in run["frames"]], [f["positions"] for f in baseline["frames"]])
                    self.assertEqual(run["scenario"]["groups"]["signal_voter"]["voting"], response)
                    self.assertEqual(run["scenario"]["groups"]["residents"]["voting"], "sincere")
                    self.assertEqual(run["scenario"]["signal_controller"]["policy"], policy)
                    sim = Simulation(make_scenario(run["scenario"])); sim.run()
                    self.assertEqual(run["frames"], [frame.as_dict() for frame in sim.frames])
                    self.assertEqual(run["metrics"], series(sim.scenario, sim.frames))
                    for paired, control, treated in zip(run["paired"], baseline["metrics"], run["metrics"]):
                        self.assertEqual(paired["target_win_delta"], int(treated["winner"] == "B") - int(control["winner"] == "B"))
                        self.assertAlmostEqual(paired["target_share_delta"], treated["shares"]["B"] - control["shares"]["B"])
                        self.assertEqual(paired["signal_spend"], treated["signal_spend"])
                        if treated["round"]:
                            self.assertEqual(paired["ballot_switch_delta"], treated["ballot_switch_count"] - control["ballot_switch_count"])
                        else:
                            self.assertIsNone(paired["ballot_switch_delta"])
                    self.assertTrue(run["response_movement_matched"])
                    sincere = row["runs"]["sincere"][policy]
                    for paired, control, treated in zip(run["response_paired"], sincere["metrics"], run["metrics"]):
                        self.assertEqual(paired["target_win_delta"], int(treated["winner"] == "B") - int(control["winner"] == "B"))
                        self.assertAlmostEqual(paired["target_share_delta"], treated["shares"]["B"] - control["shares"]["B"])
                        if treated["signal_report"] is not None:
                            self.assertEqual(paired["signal_report_equal"], treated["signal_report"] == control["signal_report"])
            trusting = row["runs"]["signal_confident"]
            self.assertEqual(trusting["truthful"]["frames"][1]["ballots"]["4"], ["C"])
            self.assertEqual(trusting["target_biased"]["frames"][1]["ballots"]["4"], ["A"])
            self.assertEqual(trusting["target_biased"]["paired"][1]["target_margin_delta"], -1)
            self.assertTrue(trusting["target_biased"]["response_paired"][1]["signal_report_equal"])
            self.assertFalse(trusting["target_biased"]["response_paired"][2]["signal_report_equal"])
        self.assertEqual(result, compare_signal_responses(scenario, [11, 22], ["signal_voter"], 1))

    def test_zero_budget_is_equivalent_within_each_response(self):
        data = example(); data["signal_controller"]["lifetime_budget"] = 0
        runs = compare_signal_responses(make_scenario(data), [5], ["signal_voter"], 0)["rows"][0]["runs"]
        for arms in runs.values():
            expected = arms["truthful"]["frames"]
            for arm in arms.values():
                self.assertEqual(arm["frames"], expected)
                self.assertTrue(all(row["target_win_delta"] == row["target_margin_delta"] == 0 for row in arm["paired"]))

    def test_failures_and_missing_baselines_are_not_discarded_or_paired(self):
        scenario = make_scenario(example())
        result = compare_signal_responses(scenario, [1], ["signal_voter"], 1, max_worlds=1)
        runs = result["rows"][0]["runs"]
        for run in runs["epistemic_signal_dominant"].values():
            self.assertEqual((run["status"], run["completed_round"]), ("failed", 0))
            self.assertEqual(len(run["frames"]), 1)
            self.assertNotIn("paired", run)
        self.assertTrue(all(run["status"] == "ok" for run in runs["signal_confident"].values()))
        real_step = Simulation.step
        def fail_control(sim):
            if (sim.scenario.signal_controller.policy == "truthful" and
                    next(g for g in sim.scenario.groups if g.id == "signal_voter").voting == "signal_confident"):
                raise ElectionError("deliberate control failure")
            return real_step(sim)
        with patch.object(Simulation, "step", fail_control):
            runs = compare_signal_responses(scenario, [1], ["signal_voter"], 1)["rows"][0]["runs"]
        self.assertEqual(runs["signal_confident"]["truthful"]["status"], "failed")
        for name in ("bounded_random", "target_biased"):
            self.assertEqual(runs["signal_confident"][name]["status"], "ok")
            self.assertIsNone(runs["signal_confident"][name]["movement_matched"])
            self.assertNotIn("paired", runs["signal_confident"][name])
        self.assertIn("paired", runs["sincere"]["target_biased"])
        self.assertIsNone(runs["signal_confident"]["truthful"].get("response_paired"))
        def fail_sincere_random(sim):
            if (sim.scenario.signal_controller.policy == "bounded_random" and
                    next(g for g in sim.scenario.groups if g.id == "signal_voter").voting == "sincere"):
                raise ElectionError("deliberate response baseline failure")
            return real_step(sim)
        with patch.object(Simulation, "step", fail_sincere_random):
            runs = compare_signal_responses(scenario, [1], ["signal_voter"], 1)["rows"][0]["runs"]
        for response in ("signal_confident", "epistemic_signal_dominant"):
            arm = runs[response]["bounded_random"]
            self.assertEqual(arm["status"], "ok")
            self.assertIsNone(arm["response_movement_matched"])
            self.assertNotIn("response_paired", arm)
            self.assertIn("paired", arm)

    def test_cumulative_coalition_campaign_movement_and_signal(self):
        with Path("examples/coalition-combined.toml").open("rb") as handle: data = tomllib.load(handle)
        data["rounds"] = 3
        data["groups"]["listener"]["capabilities"] = {"observe_public_signal": True, "observe_electorate": True}
        data["signal_controller"] = copy.deepcopy(example()["signal_controller"])
        data["campaign_controller"] = {"target": "B", "policy": "target_heuristic", "lifetime_budget": 1, "per_round_budget": 1}
        scenario = make_scenario(data)
        runs = compare_signal_responses(scenario, [9], ["listener"], 1)["rows"][0]["runs"]
        for arms in runs.values():
            for run in arms.values():
                self.assertEqual(run["status"], "ok")
                self.assertTrue(run["movement_matched"])
                self.assertTrue(run["response_movement_matched"])
                self.assertIn("coalition_sight_spend", run["frames"][1])
                self.assertIn("campaign_controller", run["frames"][1])
                self.assertIn("public_signal", run["frames"][1])
                self.assertEqual(run["frames"][1]["campaign_controller"]["spent"], 1)

    def test_invalid_contracts_rejected_and_inputs_unchanged(self):
        data = example(); scenario = make_scenario(data); original = scenario.as_dict()
        for seeds in ([], [1, 1], [True], [-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): compare_signal_responses(scenario, seeds, ["signal_voter"], 1)
        for groups in ([], ["unknown"], ["signal_voter", "signal_voter"], [False]):
            with self.subTest(groups=groups), self.assertRaises(ElectionError): compare_signal_responses(scenario, [1], groups, 1)
        for bound in (0, -1, True, 1.5):
            with self.subTest(bound=bound), self.assertRaises(ElectionError): compare_signal_responses(scenario, [1], ["signal_voter"], bound)
        for limit in (0, True, 1000001):
            with self.subTest(limit=limit), self.assertRaises(ElectionError): compare_signal_responses(scenario, [1], ["signal_voter"], 1, limit)
        altered = copy.deepcopy(data); altered["groups"]["signal_voter"]["capabilities"]["observe_electorate"] = False
        with self.assertRaisesRegex(ElectionError, "permissions"): compare_signal_responses(make_scenario({**altered, "groups": {**altered["groups"], "signal_voter": {"voting": "sincere"}}}), [1], ["signal_voter"], 1)
        altered = copy.deepcopy(data); altered["people"][3]["overrides"] = {"voting": "sincere"}
        with self.assertRaisesRegex(ElectionError, "overrides"): compare_signal_responses(make_scenario(altered), [1], ["signal_voter"], 1)
        altered = copy.deepcopy(data); altered["interventions"] = [{"round": 1, "person": "1", "overrides": {}}]
        with self.assertRaisesRegex(ElectionError, "scheduled"): compare_signal_responses(make_scenario(altered), [1], ["signal_voter"], 1)
        self.assertEqual(scenario.as_dict(), original)

    def test_cli_exclusive_output_and_no_silent_partial_success(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "comparison.json"; stdout = io.StringIO()
            args = ["compare-signals", "examples/epistemic-public-signal.toml", "--seeds", "1", "--groups", "signal_voter",
                    "--signal-distortion-bound", "1", "--max-worlds", "1", "--output", str(output)]
            with contextlib.redirect_stdout(stdout): self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(stdout.getvalue())["failed"], 3)
            saved = json.loads(output.read_text())
            self.assertEqual(len(saved["rows"][0]["runs"]), 3)
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)


if __name__ == "__main__":
    unittest.main()
