import contextlib
import copy
import csv
import io
import json
import math
from pathlib import Path
import random
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.alignment import _bounded_move
from multi_agent_election.cli import main
from multi_agent_election.experiments import compare_alignment
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.visual import Session


def example():
    with Path("examples/alignment-attack.toml").open("rb") as handle:
        return tomllib.load(handle)


class AlignmentTests(VerificationTestCase):
    def test_hand_worked_attack_ranking_cost_and_fixed_platform(self):
        sim = Simulation(make_scenario(example())); sim.run()
        frames = [f.as_dict() for f in sim.frames]
        self.assertEqual(frames[0]["ballots"]["bob"], ["alice", "cara"])
        self.assertEqual(frames[1]["ballots"]["bob"], ["cara", "alice"])
        self.assertEqual(frames[1]["counts"], {"alice": 1, "cara": 3})
        self.assertEqual(frames[1]["alignment"]["ideals"]["bob"], [0.65, 0.5])
        self.assertAlmostEqual(frames[2]["alignment"]["ideals"]["bob"][0], 0.75)
        self.assertEqual(frames[2]["alignment"]["attack_spend"], 0.35)
        self.assertTrue(all(f["alignment"]["attack_spend"] == 0.35 for f in frames[2:]))
        self.assertEqual(sim.scenario.people[2].ideal, (1.0, 0.5))
        for frame in frames:
            self.assertEqual(frame["alignment"]["ideals"]["cara"], [1.0, 0.5])
            self.assertLessEqual(frame["alignment"]["attack_spend"], 0.35)

    def test_clipped_motion_cost_and_strict_limits(self):
        rng = random.Random(71)
        for dimensions in (1, 2, 5):
            for _ in range(300):
                origin = tuple(rng.choice((0.0, 1.0, rng.random())) for _ in range(dimensions))
                vector = [rng.uniform(-1, 1) for _ in range(dimensions)]
                norm = math.hypot(*vector)
                direction = tuple(x / norm for x in vector)
                limit = rng.random() * 0.9
                after, realized = _bounded_move(origin, direction, limit)
                self.assertEqual(realized, math.dist(origin, after))
                self.assertLessEqual(realized, limit)
                self.assertTrue(all(0 <= x <= 1 for x in after))
        after, realized = _bounded_move((1.0, 0.0), (math.sqrt(0.5), -math.sqrt(0.5)), 0.5)
        self.assertEqual(after, (1.0, 0.0)); self.assertEqual(realized, 0)

    def test_global_budget_scope_and_deterministic_allocation(self):
        data = example(); data["alignment"]["attack"].update(targets=["dina", "bob"], total_budget=0.1)
        sim = Simulation(make_scenario(data)); sim.step(); trace = sim.current.as_dict()["alignment"]
        changes = {change["person"]: change for change in trace["changes"]}
        self.assertAlmostEqual(changes["bob"]["attack_cost"], 0.1)
        self.assertEqual(changes["dina"]["attack_cost"], 0)
        self.assertEqual(changes["alice"]["before"], changes["alice"]["after_attack"])
        self.assertLessEqual(trace["attack_spend"], 0.1)
        data["alignment"]["attack"]["targets"].reverse()
        self.assertEqual(Simulation(make_scenario(data)).run(1), tuple(sim.frames))

    def test_zero_controls_drift_keying_and_replay(self):
        data = example(); data["alignment"]["attack"]["total_budget"] = 0
        attacked = Simulation(make_scenario(data)); attacked.run()
        plain = copy.deepcopy(data); plain.pop("alignment")
        control = Simulation(make_scenario(plain)); control.run()
        self.assertEqual([f.ballots for f in attacked.frames], [f.ballots for f in control.frames])
        self.assertEqual([f.preferences for f in attacked.frames], [f.preferences for f in control.frames])
        data["alignment"]["drift_max_step"] = 0.12
        drift = Simulation(make_scenario(data)); drift.run(3)
        again = Simulation(make_scenario(data)); again.run(3)
        self.assertEqual(drift.frames, again.frames)
        targeted = copy.deepcopy(data); targeted["alignment"]["attack"]["total_budget"] = 0.35
        treated = Simulation(make_scenario(targeted)); treated.step()
        first_a = {x["person"]: x["after_drift"] for x in drift.frames[1].as_dict()["alignment"]["changes"]}
        first_b = {x["person"]: x["after_drift"] for x in treated.frames[1].as_dict()["alignment"]["changes"]}
        self.assertEqual(first_a, first_b)
        self.assertEqual(Simulation.from_checkpoint(drift.checkpoint()).current, drift.current)
        drift.edit_after(1, "bob", ballot=["alice", "cara"]); drift.run(2)
        self.assertEqual(Simulation.from_checkpoint(drift.checkpoint()).current, drift.current)

    def test_cumulative_nomination_coalition_campaign_and_signal(self):
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
        self.assertEqual(first["preference_sight"][0]["preference"], ["cara", "alice"])
        self.assertNotIn("ideal", first["preference_sight"][0])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_permissions_invalid_configs_and_ordinal_edits_fail_closed(self):
        changes = [lambda x: x["alignment"]["attack"].update(observe_target_ideals=False),
                   lambda x: x["alignment"]["attack"].update(observe_target_ideals=1),
                   lambda x: x["alignment"]["attack"].update(target="bob"),
                   lambda x: x["alignment"]["attack"].update(targets=["nobody"]),
                   lambda x: x["alignment"]["attack"].update(targets=["bob", "bob"]),
                   lambda x: x["alignment"]["attack"].update(per_person_round=-1),
                   lambda x: x["alignment"]["attack"].update(total_budget=True),
                   lambda x: x["alignment"].update(drift_max_step=float("nan")),
                   lambda x: x["alignment"]["attack"].update(policy="unknown"),
                   lambda x: x.update(interventions=[{"round": 1, "person": "bob", "preference": ["cara", "alice"]}]),
                   lambda x: x.update(convergence={"case": "direct_best_response"})]
        for change in changes:
            data = example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        sim = Simulation(make_scenario(example())); checkpoint = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "derive preferences"):
            sim.edit_after(0, "bob", preference=["cara", "alice"])
        self.assertEqual(sim.checkpoint(), checkpoint)
        random_data = example(); random_data["alignment"]["attack"].update(policy="random", observe_target_ideals=False)
        Simulation(make_scenario(random_data)).step()

    def test_control_comparison_pairing_seed_replay_and_zero_budget(self):
        data = example(); data["alignment"]["drift_max_step"] = 0.05
        scenario = make_scenario(data)
        comparison = compare_alignment(scenario, [11, 22])
        self.assertEqual(comparison, compare_alignment(scenario, [11, 22]))
        self.assertEqual(comparison["arms"], ["no_drift_no_attack", "drift_only", "targeted_with_drift", "random_with_drift"])
        for row in comparison["rows"]:
            runs = row["runs"]
            for arm, run in runs.items():
                self.assertEqual(run["status"], "ok"); self.assertTrue(run["movement_matched"])
                self.assertEqual(run["scenario"]["alignment"]["attack"]["total_budget"], 0.35)
                replay = Simulation(make_scenario(run["scenario"])); replay.run()
                self.assertEqual(run["frames"], [frame.as_dict() for frame in replay.frames])
                control = runs[run["baseline"]]
                for paired, baseline, treated in zip(run["paired"], control["metrics"], run["metrics"]):
                    self.assertEqual(paired["target_win_delta"], int(treated["winner"] == "cara") - int(baseline["winner"] == "cara"))
                    self.assertAlmostEqual(paired["target_share_delta"], treated["shares"]["cara"] - baseline["shares"]["cara"])
                    self.assertAlmostEqual(paired["current_winner_distance_delta"], treated["mean_winner_current_ideal_distance"] - baseline["mean_winner_current_ideal_distance"])
            self.assertEqual(runs["targeted_with_drift"]["baseline"], "drift_only")
        data["alignment"]["attack"]["total_budget"] = 0
        arms = compare_alignment(make_scenario(data), [7])["rows"][0]["runs"]
        for name in ("targeted_with_drift", "random_with_drift"):
            self.assertEqual(arms[name]["frames"], arms["drift_only"]["frames"])
            self.assertTrue(all(row["target_win_delta"] == row["attack_spend"] == 0 for row in arms[name]["paired"]))

    def test_comparison_failure_missing_baseline_validation_and_cli(self):
        from unittest.mock import patch
        scenario = make_scenario(example()); real = Simulation.step
        def fail_drift(sim):
            if sim.scenario.alignment.attack.policy == "none" and sim.scenario.alignment.drift_max_step > 0:
                raise ElectionError("deliberate drift-control failure")
            return real(sim)
        data = example(); data["alignment"]["drift_max_step"] = 0.1
        with patch.object(Simulation, "step", fail_drift):
            runs = compare_alignment(make_scenario(data), [1])["rows"][0]["runs"]
        self.assertEqual(runs["drift_only"]["status"], "failed")
        for name in ("targeted_with_drift", "random_with_drift"):
            self.assertEqual(runs[name]["status"], "ok")
            self.assertIsNone(runs[name]["movement_matched"])
            self.assertNotIn("paired", runs[name])
        for seeds in ([], [1, 1], [True], [-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): compare_alignment(scenario, seeds)
        unsafe = example(); unsafe["alignment"]["attack"].update(policy="random", observe_target_ideals=False)
        with self.assertRaisesRegex(ElectionError, "permission"):
            compare_alignment(make_scenario(unsafe), [1])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "comparison.json"; stream = io.StringIO()
            args = ["compare-alignment", "examples/alignment-attack.toml", "--seeds", "11", "22", "--output", str(output)]
            with contextlib.redirect_stdout(stream): self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(stream.getvalue())["failed"], 0)
            saved = json.loads(output.read_text())
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)

    def test_csv_session_http_and_checkpoint_tamper(self):
        scenario = make_scenario(example()); sim = Simulation(scenario); session = Session(sim)
        self.assertEqual(session.snapshot()["alignment"]["attack"]["target"], "cara")
        response = session.command({"revision": 0, "action": "step"})
        self.assertEqual(response["metric"]["alignment_attack_spend"], 0.25)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        for field in ("attack_spend", "ideals", "changes"):
            changed = sim.checkpoint()
            if field == "attack_spend": changed["frames"][1]["alignment"][field] = 0
            elif field == "ideals": changed["frames"][1]["alignment"][field]["bob"][0] = 0
            else: changed["frames"][1]["alignment"][field][0]["attack_cost"] = 0.1
            with self.subTest(field=field), self.assertRaisesRegex(ElectionError, "history"):
                Simulation.from_checkpoint(changed)
        old = sim.checkpoint(); old["version"] = 18
        with self.assertRaisesRegex(ElectionError, "version 19"): Simulation.from_checkpoint(old)
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"; csv_path = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/alignment-attack.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(csv_path)]), 0)
            with csv_path.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertEqual(float(rows[1]["alignment_attack_spend"]), 0.25)
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as reply: html = reply.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        request = Request(base + "/command", headers=headers, data=json.dumps({"action": "step", "revision": 0}).encode(), method="POST")
        with urlopen(request) as reply: actual = json.load(reply)
        self.assertEqual(actual["frame"], sim.current.as_dict())
        self.assertEqual(actual["metric"], frame_metrics(scenario, sim.current, sim.frames[0]))


if __name__ == "__main__":
    unittest.main()
