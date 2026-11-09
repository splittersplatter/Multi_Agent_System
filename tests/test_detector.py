import contextlib
import copy
import csv
from dataclasses import replace
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
from multi_agent_election.detector import update_detector
from multi_agent_election.experiments import _detector_episode, calibrate_and_evaluate_detector
from multi_agent_election.model import DetectorConfig
from multi_agent_election.policies import Observation
from multi_agent_election.visual import Session


def example():
    with Path("examples/detector.toml").open("rb") as handle:
        return tomllib.load(handle)


class DetectorTests(VerificationTestCase):
    def test_hand_worked_change_strict_threshold_and_interrupted_streaks(self):
        config = DetectorConfig("B", 0.25); parties = ("A", "B")
        values = [{"A": 2, "B": 2}, {"A": 1, "B": 3}, {"A": 1, "B": 3},
                  {"A": 3, "B": 1}, {"A": 1, "B": 3}, {"A": 1, "B": 3}, {"A": 1, "B": 3}]
        states = [update_detector(config, parties, values[0], 0)]
        for i in range(1, len(values)):
            states.append(update_detector(config, parties, values[i], i, states[-1], values[i-1]))
        self.assertEqual(states[0].target_win_streak, 0)  # party order breaks A/B tie
        self.assertFalse(states[1].alert)  # 0.25 equals threshold, not above
        self.assertTrue(states[4].alert)
        self.assertEqual(states[4].first_alert_round, 4)
        self.assertEqual([s.target_win_streak for s in states], [0, 1, 2, 0, 1, 2, 3])
        self.assertEqual(states[-1].first_triple_win_round, 6)
        self.assertTrue(all(s.first_triple_win_round is None for s in states[:-1]))
        first = update_detector(config, parties, {"A": 1, "B": 3}, 0)
        second = update_detector(config, parties, {"A": 1, "B": 3}, 1, first, {"A": 1, "B": 3})
        third = update_detector(config, parties, {"A": 1, "B": 3}, 2, second, {"A": 1, "B": 3})
        self.assertEqual(third.first_triple_win_round, 2)  # round zero is an election

    def test_detector_only_uses_aggregates_and_is_passive(self):
        data = example(); scenario = make_scenario(data)
        detected = Simulation(scenario); detected.run()
        raw = copy.deepcopy(data); raw.pop("detector")
        control = Simulation(make_scenario(raw)); control.run()
        self.assertEqual([replace(f, detector=None) for f in detected.frames], control.frames)
        self.assertNotIn("detector", Observation.__dataclass_fields__)
        state = detected.frames[1].detector
        self.assertTrue(state.alert); self.assertEqual(state.first_alert_round, 1)
        self.assertEqual(detected.frames[3].detector.first_triple_win_round, 3)
        self.assertEqual(state, update_detector(scenario.detector, scenario.parties,
                         dict(detected.frames[1].counts), 1, detected.frames[0].detector, dict(detected.frames[0].counts)))
        left = example(); left["alignment"]["attack"]["total_budget"] = 0
        right = copy.deepcopy(left); right["people"][1]["ideal"] = [0.2, 0.5]
        a, b = Simulation(make_scenario(left)), Simulation(make_scenario(right)); a.run(); b.run()
        self.assertNotEqual(a.current.alignment_ideals, b.current.alignment_ideals)
        self.assertEqual([f.counts for f in a.frames], [f.counts for f in b.frames])
        self.assertEqual([f.detector for f in a.frames], [f.detector for f in b.frames])

    def test_rewind_resume_tamper_and_summary_match(self):
        sim = Simulation(make_scenario(example())); sim.run(4)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        broken = sim.checkpoint(); broken["frames"][1]["detector"]["alert"] = False
        with self.assertRaisesRegex(ElectionError, "history"): Simulation.from_checkpoint(broken)
        old = sim.checkpoint(); old["version"] = 19
        with self.assertRaisesRegex(ElectionError, "version 20"): Simulation.from_checkpoint(old)
        sim.edit_after(0, "bob", ballot=["alice", "cara"]); sim.run(3)
        self.assertIsNone(sim.frames[1].detector.first_alert_round)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        full, summary = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(full): self.assertEqual(main(["run", "examples/detector.toml"]), 0)
        with contextlib.redirect_stdout(summary): self.assertEqual(main(["run", "examples/detector.toml", "--summary"]), 0)
        self.assertEqual(json.loads(full.getvalue())["metrics"], json.loads(summary.getvalue())["metrics"])
        session = Session(Simulation(make_scenario(example())))
        self.assertEqual(session.snapshot()["detector"], {"target": "cara", "threshold": 0.1})
        self.assertTrue(session.command({"revision": 0, "action": "step"})["metric"]["detector_alert"])

    def test_cumulative_detector_with_coalition_campaign_and_signal(self):
        data = example()
        data["groups"]["observer"] = {"voting": "sight_plurality", "capabilities": {"observe_target_preferences": True}}
        data["people"][0]["group"] = "observer"
        data["coalitions"] = [{"id": "team", "members": ["alice"], "target": "cara", "report_budget_per_round": 0,
                               "report_budget_total": 0, "sight_targets": ["bob"], "sight_budget_per_round": 1, "sight_budget_total": 2}]
        data["signal_controller"] = {"target": "cara", "policy": "target_biased", "schedule": "repeated",
                                     "per_broadcast_budget": 1, "lifetime_budget": 2}
        data["campaign_controller"] = {"target": "cara", "policy": "target_heuristic", "per_round_budget": 1, "lifetime_budget": 1}
        sim = Simulation(make_scenario(data)); sim.run(2)
        first = sim.frames[1].as_dict()
        self.assertEqual(first["alignment"]["attack_spend"], 0.25)
        self.assertEqual(first["public_signal"]["spend"], 1)
        self.assertEqual(first["campaign_controller"]["spent"], 1)
        self.assertEqual(first["coalition_sight_spend"]["team"], 1)
        self.assertEqual(sim.frames[1].detector, update_detector(sim.scenario.detector, sim.scenario.parties,
                         dict(sim.frames[1].counts), 1, sim.frames[0].detector, dict(sim.frames[0].counts)))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_detector_http_status_matches_direct_engine(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario = make_scenario(example()); direct = Simulation(scenario); direct.step()
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as reply: html = reply.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        with urlopen(Request(base + "/state", headers=headers)) as reply: snapshot = json.load(reply)
        self.assertEqual(snapshot["detector"]["target"], "cara")
        request = Request(base + "/command", headers=headers, data=json.dumps({"action": "step", "revision": 0}).encode(), method="POST")
        with urlopen(request) as reply: actual = json.load(reply)
        self.assertEqual(actual["frame"], direct.current.as_dict())
        self.assertTrue(actual["metric"]["detector_alert"])

    def test_invalid_detector_configuration_and_aggregate_inputs(self):
        for value in (-1, 1.1, True, float("nan")):
            data = example(); data["detector"]["threshold"] = value
            with self.subTest(value=value), self.assertRaises(ElectionError): make_scenario(data)
        for data in ({"target":"missing", "threshold":0.1}, {"target":"cara"}, None):
            raw = example(); raw["detector"] = data
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(raw)
        config = DetectorConfig("A", 0.1)
        for counts in ({"A": 0, "B": 0}, {"A": True, "B": 1}, {"A": -1, "B": 2}, {"A": 1}):
            with self.subTest(counts=counts), self.assertRaises(ElectionError): update_detector(config, ("A", "B"), counts, 0)

    def test_episode_timing_strictly_before_endpoint_and_censoring(self):
        def frame(t, *, alert=False, cost=0, t3=None):
            return {"round": t, "detector": {"alert": alert, "first_triple_win_round": t3},
                    "alignment": {"changes": [{"attack_cost": cost}]}}
        records = [frame(0), frame(1, alert=True), frame(2, cost=0.1), frame(3, alert=True, t3=3)]
        result = _detector_episode(records, True)
        self.assertTrue(result["pre_onset_alert"])
        self.assertTrue(result["post_onset_alert"])
        self.assertEqual(result["detection_delay"], 1)
        self.assertTrue(result["pre_t3_eligible"])
        self.assertFalse(result["pre_t3_alert"])  # alert at t3 is not early
        missing = _detector_episode([frame(0), frame(1, cost=0.1), frame(2)], True)
        self.assertIsNone(missing["first_triple_win_round"])
        self.assertIsNone(missing["pre_t3_alert"])
        self.assertFalse(missing["post_onset_alert"])
        no_attack = _detector_episode([frame(0), frame(1, alert=True)], True)
        self.assertFalse(no_attack["realized_attack"])
        self.assertIsNone(no_attack["post_onset_alert"])

    def test_frozen_calibration_and_held_out_aggregate_evaluation(self):
        scenario = make_scenario(example())
        result = calibrate_and_evaluate_detector(scenario, [100, 101, 102], [200, 201], 0.05)
        self.assertEqual(result, calibrate_and_evaluate_detector(scenario, [100, 101, 102], [200, 201], 0.05))
        self.assertEqual(result["threshold"], calibrate_and_evaluate_detector(scenario, [100, 101, 102], [300], 0.05)["threshold"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["threshold"], 0)
        self.assertEqual(result["calibration_empirical_false_alarm_rate"], 0)
        for record in result["calibration"]:
            self.assertEqual(record["scenario"]["alignment"]["attack"]["policy"], "none")
            self.assertEqual(record["scenario"]["detector"]["threshold"], 1)
        self.assertEqual(result["summary"]["drift_only"]["false_alarm_rate"], 0)
        target = result["summary"]["targeted_with_drift"]
        self.assertEqual((target["realized_attack_episodes"], target["detected_episodes"], target["recall"]), (2, 2, 1))
        self.assertEqual((target["pre_t3_eligible_episodes"], target["pre_t3_detected_episodes"], target["pre_t3_recall"]), (2, 2, 1))
        for row in result["evaluation"]["rows"]:
            for run in row["runs"].values():
                self.assertEqual(run["scenario"]["detector"]["threshold"], result["threshold"])
        data = example(); data["alignment"]["attack"]["total_budget"] = 0
        empty = calibrate_and_evaluate_detector(make_scenario(data), [1], [2], 0)
        for arm in ("targeted_with_drift", "random_with_drift"):
            self.assertEqual(empty["summary"][arm]["no_realized_attack_episodes"], 1)
            self.assertIsNone(empty["summary"][arm]["recall"])

    def test_calibration_order_statistic_matches_independent_counts(self):
        data = example(); data["alignment"]["drift_max_step"] = 0.2
        alpha = 0.4
        result = calibrate_and_evaluate_detector(make_scenario(data), [10, 11, 12, 13, 14], [30], alpha)
        maxima = []
        for record in result["calibration"]:
            frames = record["frames"]
            increases = [(b["counts"]["cara"] - a["counts"]["cara"]) / len(a["ballots"])
                         for a, b in zip(frames, frames[1:])]
            maxima.append(max(0.0, *increases))
        expected = sorted(maxima)[math.ceil((1-alpha) * len(maxima)) - 1]
        self.assertEqual(result["threshold"], expected)
        self.assertAlmostEqual(result["calibration_empirical_false_alarm_rate"], sum(x > expected for x in maxima) / len(maxima))
        self.assertLessEqual(result["calibration_empirical_false_alarm_rate"], alpha)

    def test_calibration_failure_never_uses_surviving_subset(self):
        from unittest.mock import patch
        scenario = make_scenario(example()); real = Simulation.step
        def fail_seed(sim):
            if sim.scenario.seed == 101 and sim.scenario.alignment.attack.policy == "none":
                raise ElectionError("deliberate calibration failure")
            return real(sim)
        with patch.object(Simulation, "step", fail_seed):
            result = calibrate_and_evaluate_detector(scenario, [100, 101], [200], 0.1)
        self.assertEqual(result["status"], "calibration_failed")
        self.assertIsNone(result["threshold"]); self.assertIsNone(result["evaluation"])
        self.assertEqual([r["status"] for r in result["calibration"]], ["ok", "failed"])
        self.assertEqual(result["calibration"][1]["completed_round"], 0)
        def fail_evaluation_control(sim):
            if sim.scenario.seed == 200 and sim.scenario.alignment.attack.policy == "none":
                raise ElectionError("deliberate evaluation control failure")
            return real(sim)
        with patch.object(Simulation, "step", fail_evaluation_control):
            partial = calibrate_and_evaluate_detector(scenario, [100, 101], [200], 0.1)
        self.assertEqual(partial["status"], "evaluation_incomplete")
        self.assertEqual(partial["summary"]["drift_only"]["failed"], 1)
        self.assertEqual(partial["summary"]["targeted_with_drift"]["unpaired"], 1)
        self.assertEqual(partial["summary"]["targeted_with_drift"]["completed"], 1)

    def test_invalid_splits_cli_exclusive_output_and_csv(self):
        scenario = make_scenario(example())
        for calibration, evaluation in (([], [1]), ([1], []), ([1], [1]), ([1, 1], [2]), ([True], [2])):
            with self.subTest(calibration=calibration, evaluation=evaluation), self.assertRaises(ElectionError):
                calibrate_and_evaluate_detector(scenario, calibration, evaluation, 0.1)
        for value in (-0.1, 1, True, float("nan")):
            with self.subTest(value=value), self.assertRaises(ElectionError):
                calibrate_and_evaluate_detector(scenario, [1], [2], value)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); output = root / "evaluation.json"; checkpoint = root / "state.json"; csv_path = root / "metrics.csv"
            args = ["evaluate-detector", "examples/detector.toml", "--calibration-seeds", "11", "12", "--evaluation-seeds", "21",
                    "--false-alarm-rate", "0.1", "--output", str(output)]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout): self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "ok")
            saved = json.loads(output.read_text())
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/detector.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(csv_path)]), 0)
            with csv_path.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertEqual(rows[1]["detector_alert"], "True")
            self.assertEqual(rows[3]["detector_first_triple_win_round"], "3")


if __name__ == "__main__":
    unittest.main()
