import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.combined import MECHANISMS, combined_ablation
from multi_agent_election.metrics import series


def example():
    with Path("examples/all-enabled.toml").open("rb") as handle:
        return tomllib.load(handle)


class CombinedAblationTests(unittest.TestCase):
    def test_full_matrix_configuration_replay_and_pairing(self):
        scenario = make_scenario(example()); original = scenario.as_dict()
        result = combined_ablation(scenario, [11, 22], "alice")
        self.assertEqual(result["record_version"], 1)
        self.assertEqual(len(result["arms"]), 17)
        self.assertEqual(len({arm["id"] for arm in result["arms"]}), 17)
        specs = {arm["id"]: arm for arm in result["arms"]}
        self.assertEqual(specs["all_enabled"]["enabled"], list(MECHANISMS))
        self.assertEqual(specs["all_disabled"]["enabled"], [])
        for name in MECHANISMS:
            self.assertEqual(specs[f"isolated_{name}"]["enabled"], [name])
            self.assertEqual(set(specs[f"without_{name}"]["enabled"]), set(MECHANISMS) - {name})
        for row in result["rows"]:
            runs = row["runs"]
            for arm, run in runs.items():
                self.assertEqual(run["status"], "ok", (arm, run.get("error")))
                self.assertTrue(run["movement_matched"]); self.assertTrue(run["same_candidates"])
                encoded = json.dumps(run["scenario"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                self.assertEqual(run["scenario_sha256"], hashlib.sha256(encoded).hexdigest())
                enabled = set(specs[arm]["enabled"]); config = run["scenario"]
                self.assertEqual(config["network"].get("proximity_mode", "dynamic"), "dynamic" if "proximity" in enabled else "frozen")
                self.assertEqual(config["campaign_controller"]["policy"], "target_heuristic" if "campaign_edges" in enabled else "none")
                self.assertEqual(config["signal_controller"]["policy"], "target_biased" if "poll_distortion" in enabled else "truthful")
                self.assertEqual(config["nomination"]["mode"], "endogenous" if "nomination" in enabled else "fixed")
                self.assertEqual(config["alignment"]["attack"]["policy"], "toward_target" if "alignment_attack" in enabled else "none")
                self.assertEqual(config["leaders"]["policy"], "feedback" if "leader_adaptation" in enabled else "fixed")
                self.assertEqual(config["coalitions"][0]["report_budget_total"], 2 if "coalition" in enabled else 0)
                self.assertEqual("detector" not in config, arm == "detector_off")
                replay = Simulation(make_scenario(run["scenario"])); replay.run()
                self.assertEqual(run["frames"], [f.as_dict() for f in replay.frames])
                self.assertEqual(run["metrics"], series(replay.scenario, replay.frames))
                baseline = runs[run["baseline"]]
                for pair, control, treated in zip(run["paired"], baseline["metrics"], run["metrics"]):
                    self.assertEqual(pair["target_win_delta"], int(treated["winner"] == "alice") - int(control["winner"] == "alice"))
                    self.assertAlmostEqual(pair["target_share_delta"], treated["shares"]["alice"] - control["shares"]["alice"])
                expected = {p: 0 for p in ("alice", "bob", "cara", "dina")}
                for frame in run["frames"][1:]:
                    for _, receiver in frame["proximity_edges"]: expected[receiver] += 1
                for frame in baseline["frames"][1:]:
                    for _, receiver in frame["proximity_edges"]: expected[receiver] -= 1
                self.assertEqual(run["exposure"]["person_delta"], expected)
                self.assertEqual(run["exposure"]["absolute_delta_sum"], sum(abs(x) for x in expected.values()))
                turnover = sum(len(set(map(tuple, a["proximity_edges"])) ^ set(map(tuple, b["proximity_edges"])))
                               for a, b in zip(run["frames"][1:], baseline["frames"][1:]))
                self.assertEqual(run["exposure"]["edge_round_symmetric_difference"], turnover)
            self.assertTrue(runs["detector_off"]["detector_noninterference"])
            self.assertEqual(runs["without_nomination"]["nomination"]["nominees"], runs["all_enabled"]["nomination"]["nominees"])
            self.assertEqual(runs["without_nomination"]["frames"], runs["all_enabled"]["frames"])
        self.assertEqual(scenario.as_dict(), original)
        self.assertEqual(result, combined_ablation(scenario, [11, 22], "alice"))

    def test_disabled_contracts_preserve_drift_and_detector(self):
        runs = combined_ablation(make_scenario(example()), [2026], "alice")["rows"][0]["runs"]
        disabled = runs["all_disabled"]
        config = disabled["scenario"]
        self.assertEqual(config["network"]["proximity_mode"], "frozen")
        self.assertEqual(config["nomination"]["mode"], "fixed")
        self.assertEqual(config["campaign_controller"]["policy"], "none")
        self.assertEqual(config["signal_controller"]["policy"], "truthful")
        self.assertEqual(config["alignment"]["attack"]["policy"], "none")
        self.assertGreater(config["alignment"]["drift_max_step"], 0)
        self.assertEqual(config["leaders"]["policy"], "fixed")
        self.assertEqual(config["leaders"]["signal_mode"], "broadcast")
        self.assertIn("detector", config)
        capabilities = next(p["overrides"]["capabilities"] for p in config["people"] if p["id"] == "alice")
        self.assertFalse(capabilities["send_private_reports"]); self.assertFalse(capabilities["receive_private_reports"])
        for coalition in config["coalitions"]:
            for key in ("report_budget_per_round", "report_budget_total", "sight_budget_per_round", "sight_budget_total", "eavesdrop_budget_per_round", "eavesdrop_budget_total"):
                self.assertEqual(coalition[key], 0)
        for frame in disabled["frames"][1:]:
            self.assertEqual(frame["alignment"]["attack_spend"], 0)
            self.assertEqual(frame["public_signal"]["broadcast_cost"], 0)
            self.assertEqual(frame["campaign_controller"]["spent"], 0)
            self.assertEqual(frame["coalition_sight_spend"]["team"], 0)
        self.assertTrue(any(row["alignment_natural_distance"] > 0 for row in disabled["metrics"][1:]))
        self.assertEqual(runs["detector_off"]["scenario"].get("detector"), None)

    def test_failed_arm_and_failed_baseline_are_retained_unpaired(self):
        scenario = make_scenario(example()); real = Simulation.step
        def fail_selected(sim):
            if sim.scenario.campaign_controller.policy == "none" and sim.scenario.signal_controller.policy == "truthful":
                raise ElectionError("deliberate control failure")
            return real(sim)
        with patch.object(Simulation, "step", fail_selected): result = combined_ablation(scenario, [1], "alice")
        runs = result["rows"][0]["runs"]
        self.assertEqual(runs["all_disabled"]["status"], "failed")
        self.assertEqual(runs["all_disabled"]["completed_round"], 0)
        self.assertEqual(runs["all_enabled"]["status"], "ok")
        self.assertIsNone(runs["all_enabled"]["movement_matched"])
        self.assertNotIn("paired", runs["all_enabled"])
        self.assertTrue(runs["detector_off"]["detector_noninterference"])

    def test_invalid_matrix_contracts_and_exclusive_cli(self):
        scenario = make_scenario(example())
        for seeds in ([], [1, 1], [True], [-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): combined_ablation(scenario, seeds, "alice")
        with self.assertRaisesRegex(ElectionError, "target"): combined_ablation(scenario, [1], "unknown")
        mutations = [lambda x: x["network"].update(proximity_mode="frozen"),
                     lambda x: x["nomination"].update(mode="fixed", nominees=["alice", "cara"]),
                     lambda x: x["signal_controller"].update(policy="truthful"),
                     lambda x: x["campaign_controller"].update(lifetime_budget=0),
                     lambda x: x["alignment"]["attack"].update(total_budget=0),
                     lambda x: x["leaders"].update(policy="fixed"),
                     lambda x: x["coalitions"][0].update(sight_budget_total=0),
                     lambda x: x.pop("detector"),
                     lambda x: x.update(interventions=[{"round": 1, "person": "bob", "ballot": ["alice", "cara"]}])]
        for mutate in mutations:
            data = copy.deepcopy(example()); mutate(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): combined_ablation(make_scenario(data), [1], "alice")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "matrix.json"; stdout = io.StringIO()
            args = ["combined-ablation", "examples/all-enabled.toml", "--seeds", "1", "--target", "alice", "--output", str(output)]
            with contextlib.redirect_stdout(stdout): self.assertEqual(main(args), 0)
            summary = json.loads(stdout.getvalue())
            self.assertEqual((summary["arms_per_seed"], summary["failed"], summary["detector_invariant_failures"]), (17, 0, 0))
            saved = json.loads(output.read_text())
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)


if __name__ == "__main__": unittest.main()
