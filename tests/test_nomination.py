import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import compare_nominations
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.visual import Session


def example():
    with Path("examples/nomination.toml").open("rb") as handle:
        return tomllib.load(handle)


class NominationTests(unittest.TestCase):
    def test_hand_worked_nomination_preferences_and_representation(self):
        scenario = make_scenario(example())
        self.assertEqual(scenario.parties, ("alice", "cara"))
        self.assertEqual(dict(scenario.nomination.votes), {"alice": "alice", "bob": "bob", "cara": "cara", "dina": "cara"})
        self.assertEqual(dict(scenario.nomination.counts), {"alice": 1, "bob": 1, "cara": 2})
        self.assertEqual({p.id: p.preference for p in scenario.people},
                         {"alice": ("alice", "cara"), "bob": ("alice", "cara"),
                          "cara": ("cara", "alice"), "dina": ("cara", "alice")})
        sim = Simulation(scenario)
        self.assertEqual(len(sim.current.ballots), 4)  # leaders are not extra voters
        self.assertEqual(sim.current.winner, "alice")
        metrics = frame_metrics(scenario, sim.current)
        self.assertAlmostEqual(metrics["mean_winner_ideal_distance"], 0.575)
        self.assertAlmostEqual(metrics["mean_nearest_nominee_distance"], 0.125)
        self.assertEqual(make_scenario(scenario.as_dict()), scenario)

    def test_directed_observations_isolates_and_tie_breaking(self):
        data = example(); data["network"]["persistent_edges"] = [["dina", "cara"], ["bob", "dina"], ["cara", "dina"]]
        data["people"][3]["ideal"] = [0.7, 0.5]  # equidistant from bob/cara; ID breaks tie
        scenario = make_scenario(data)
        self.assertEqual(dict(scenario.nomination.votes)["dina"], "bob")
        data["network"]["persistent_edges"] = [["dina", "cara"]]
        scenario = make_scenario(data)
        self.assertIsNone(dict(scenario.nomination.votes)["dina"])
        self.assertEqual(scenario.parties, ("alice", "bob"))  # all tied one-vote nominees
        data["nomination"]["eligible"] = ["alice", "bob"]
        data["network"]["persistent_edges"] = []
        self.assertIsNone(dict(make_scenario(data).nomination.votes)["cara"])

    def test_exact_ties_zero_count_fill_and_order_independence(self):
        data = example()
        for person in data["people"]: person["ideal"] = [0.5, 0.5]
        data["network"]["persistent_edges"] = [["alice", "bob"], ["alice", "cara"], ["alice", "dina"]]
        scenario = make_scenario(data)
        self.assertEqual(dict(scenario.nomination.counts), {"alice": 4, "bob": 0, "cara": 0})
        self.assertEqual(scenario.parties, ("alice", "bob"))
        self.assertTrue(all(person.preference == ("alice", "bob") for person in scenario.people))
        reversed_data = copy.deepcopy(data); reversed_data["people"].reverse(); reversed_data["nomination"]["eligible"].reverse()
        other = make_scenario(reversed_data)
        self.assertEqual(other.nomination, scenario.nomination)
        self.assertEqual(other.parties, scenario.parties)

    def test_observation_does_not_expose_ideals_or_nomination_record(self):
        from multi_agent_election.policies import Observation
        self.assertNotIn("ideal", Observation.__dataclass_fields__)
        self.assertNotIn("nomination", Observation.__dataclass_fields__)

    def test_proximity_and_layer_union_are_initial_and_directional(self):
        data = example(); data["network"] = {"proximity_mode": "static", "static_proximity_edges": [["cara", "dina"]]}
        self.assertEqual(dict(make_scenario(data).nomination.votes)["dina"], "cara")
        data["network"] = {"radius": 0.3, "campaign_edges": [["cara", "dina"]]}
        scenario = make_scenario(data)
        self.assertEqual(dict(scenario.nomination.votes)["dina"], "cara")
        sim = Simulation(scenario); before = sim.scenario.nomination
        sim.edit_after(0, "dina", position=[0.9, 0.9]); sim.step()
        self.assertEqual(sim.scenario.nomination, before)

    def test_fixed_identical_nominees_and_seeded_random_controls(self):
        data = example(); endogenous = make_scenario(data)
        fixed = copy.deepcopy(data); fixed["nomination"].update(mode="fixed", nominees=list(endogenous.parties))
        control = make_scenario(fixed)
        self.assertEqual(control.parties, endogenous.parties)
        a, b = Simulation(endogenous), Simulation(control); a.run(); b.run()
        self.assertEqual(a.frames, b.frames)
        data["nomination"]["mode"] = "random"
        first = make_scenario(data)
        self.assertEqual(first, make_scenario(data))
        self.assertEqual(first, make_scenario(first.as_dict()))
        selected = {make_scenario({**data, "seed": seed}).parties for seed in range(20)}
        self.assertGreater(len(selected), 1)
        self.assertTrue(all(len(value) == 2 and set(value) <= {"alice", "bob", "cara"} for value in selected))

    def test_nomination_comparison_control_replay_and_failure_retention(self):
        from dataclasses import replace
        scenario = make_scenario(example())
        result = compare_nominations(scenario, [1, 2, 3, 4])
        self.assertEqual(result, compare_nominations(scenario, [1, 2, 3, 4]))
        for row in result["rows"]:
            base = row["runs"]["endogenous"]
            fixed = row["runs"]["fixed"]
            self.assertTrue(fixed["same_nominees"] and fixed["same_frames"] and fixed["movement_matched"])
            self.assertEqual(fixed["frames"], base["frames"])
            self.assertTrue(all(p["winner_ideal_distance_delta"] == p["nearest_nominee_distance_delta"] == 0 for p in fixed["paired"]))
            for run in row["runs"].values():
                replay = Simulation(make_scenario(run["scenario"])); replay.run()
                self.assertEqual(run["frames"], [frame.as_dict() for frame in replay.frames])
        random_data = example(); random_data["nomination"]["mode"] = "random"
        initial = make_scenario(random_data)
        different = next(seed for seed in range(100) if make_scenario({**random_data, "seed": seed}).parties != initial.parties)
        with self.assertRaisesRegex(ElectionError, "canonically validated"):
            Simulation(replace(initial, seed=different))
        targeted = example()
        targeted["signal_controller"] = {"target": "cara", "policy": "truthful", "schedule": "initial",
                                         "per_broadcast_budget": 1, "lifetime_budget": 1}
        result = compare_nominations(make_scenario(targeted), list(range(20)))
        self.assertTrue(any(row["runs"]["random"]["status"] == "failed" for row in result["rows"]))
        for row in result["rows"]:
            self.assertEqual(row["runs"]["fixed"]["status"], "ok")
            if row["runs"]["random"]["status"] == "failed":
                self.assertIn("target", row["runs"]["random"]["error"])
                self.assertNotIn("paired", row["runs"]["random"])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "nominations.json"; stdout = io.StringIO()
            args = ["compare-nominations", "examples/nomination.toml", "--seeds", "1", "2", "--output", str(output)]
            with contextlib.redirect_stdout(stdout): self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(stdout.getvalue())["failed"], 0)
            saved = json.loads(output.read_text())
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(output.read_text()), saved)

    def test_invalid_nomination_inputs_are_rejected(self):
        changes = [lambda x: x.update(parties=["A", "B"]),
                   lambda x: x["people"][0].update(preference=["alice", "cara"]),
                   lambda x: x["people"][0].update(ideal=[]),
                   lambda x: x["people"][0].update(ideal=[0.1]),
                   lambda x: x["people"][0].update(ideal=[float("nan"), 0]),
                   lambda x: x["people"][0].update(ideal=[True, 0]),
                   lambda x: x["nomination"].update(m=1),
                   lambda x: x["nomination"].update(m=4),
                   lambda x: x["nomination"].update(eligible=["alice", "alice"]),
                   lambda x: x["nomination"].update(eligible=["missing"]),
                   lambda x: x["nomination"].update(mode="fixed", nominees=["alice", "alice"]),
                   lambda x: x["nomination"].update(mode="bad"),
                   lambda x: x["nomination"].update(nominees=["alice", "cara"]),
                   lambda x: x["network"].update(persistent_edges=[["alice", "missing"]])]
        for change in changes:
            data = example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)

    def test_checkpoint_cli_csv_and_session_replay(self):
        data = example(); sim = Simulation(make_scenario(data)); session = Session(sim)
        view = session.snapshot()["nomination"]
        self.assertEqual(view["nominees"], ["alice", "cara"])
        self.assertEqual(view["ideals"]["dina"], (0.9, 0.5))
        session.command({"revision": 0, "action": "step"})
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        changed = sim.checkpoint(); changed["nomination"]["counts"]["cara"] += 1
        with self.assertRaisesRegex(ElectionError, "nomination record"): Simulation.from_checkpoint(changed)
        changed = sim.checkpoint(); changed.pop("nomination")
        with self.assertRaisesRegex(ElectionError, "checkpoint fields"): Simulation.from_checkpoint(changed)
        old = sim.checkpoint(); old["version"] = 17
        with self.assertRaisesRegex(ElectionError, "version 18"): Simulation.from_checkpoint(old)
        sim.edit_after(0, "dina", preference=["alice", "cara"]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        self.assertEqual(sim.scenario.nomination.nominees, ("alice", "cara"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"; output = root / "metrics.csv"; jsonl = root / "run.jsonl"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/nomination.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(output)]), 0)
                self.assertEqual(main(["run", "examples/nomination.toml", "--summary", "--jsonl", str(jsonl)]), 0)
            with output.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertAlmostEqual(float(rows[0]["mean_winner_ideal_distance"]), 0.575)
            self.assertAlmostEqual(float(rows[0]["mean_nearest_nominee_distance"]), 0.125)
            self.assertEqual(json.loads(jsonl.read_text().splitlines()[0])["nomination"]["votes"]["dina"], "cara")

    def test_http_snapshot_and_step_match_direct_simulation(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario = make_scenario(example()); direct = Simulation(scenario); direct.step()
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as response: html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        with urlopen(Request(base + "/state", headers=headers)) as response: state = json.load(response)
        self.assertEqual(state["nomination"]["nominees"], ["alice", "cara"])
        request = Request(base + "/command", headers=headers,
                          data=json.dumps({"action": "step", "revision": 0}).encode(), method="POST")
        with urlopen(request) as response: reply = json.load(response)
        self.assertEqual(reply["frame"], direct.current.as_dict())
        self.assertEqual(reply["metric"], frame_metrics(scenario, direct.current, direct.frames[0]))

    def test_signal_campaign_and_convergence_integrate_with_nominees(self):
        data = example()
        data["groups"]["attacker"] = {"voting": "sincere", "capabilities": {"observe_target_preferences": True}}
        data["people"][0]["group"] = "attacker"
        data["coalitions"] = [{"id": "team", "members": ["alice"], "target": "cara",
                               "report_budget_per_round": 0, "report_budget_total": 0,
                               "sight_targets": ["bob"], "sight_budget_per_round": 1, "sight_budget_total": 1}]
        data["signal_controller"] = {"target": "cara", "policy": "target_biased", "schedule": "repeated",
                                     "per_broadcast_budget": 1, "lifetime_budget": 2}
        data["campaign_controller"] = {"target": "cara", "policy": "target_heuristic", "per_round_budget": 1, "lifetime_budget": 1}
        sim = Simulation(make_scenario(data)); sim.run(2)
        self.assertEqual(sim.current.signal_spend, 2)
        self.assertIsNotNone(sim.current.campaign_controller_purchased)
        self.assertEqual(dict(sim.current.coalition_sight_spend)["team"], 1)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        data.pop("signal_controller"); data.pop("campaign_controller"); data.pop("coalitions"); data["k"] = 1
        data["groups"]["attacker"] = {"voting": "direct_best_response"}
        data["groups"]["residents"]["voting"] = "direct_best_response"
        data["convergence"] = {"case": "direct_best_response"}
        certified = Simulation(make_scenario(data)); certified.run(4)
        self.assertIn(frame_metrics(certified.scenario, certified.current)["convergence"]["status"], ("certified_equilibrium", "not_equilibrium"))


if __name__ == "__main__":
    unittest.main()
