import contextlib
import copy
import csv
import io
import itertools
import json
import tomllib
import tempfile
import unittest
from verification_support import VerificationTestCase
from dataclasses import replace
from pathlib import Path

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.visual import Session
from multi_agent_election.voting import direct_best_response, source_local_dominance
from scripts.verify_convergence_foundations import dominance_moves, direct_moves, conformity_choice, potential


def example():
    with Path("examples/certified-direct.toml").open("rb") as handle:
        return tomllib.load(handle)


class CertifiedDirectTests(VerificationTestCase):
    def test_tiny_profiles_against_independent_winner_oracle(self):
        parties = ("A", "B", "C")
        for ballots in itertools.product(parties, repeat=4):
            counts = {p: ballots.count(p) for p in parties}
            for person in range(4):
                for pref in itertools.permutations(parties):
                    outcomes = {}
                    for choice in parties:
                        modified = list(ballots); modified[person] = choice
                        outcomes[choice] = min(parties, key=lambda p: (-modified.count(p), parties.index(p)))
                    before = outcomes[ballots[person]]
                    best = min(outcomes.values(), key=pref.index)
                    expected = best if pref.index(best) < pref.index(before) else ballots[person]
                    self.assertEqual(direct_best_response(parties, counts, ballots[person], pref), expected)

    def test_first_move_certification_and_replay(self):
        scenario = make_scenario(example()); sim = Simulation(scenario)
        self.assertEqual(dict(sim.current.counts), {"A": 2, "B": 2, "C": 1})
        first = sim.step()
        self.assertEqual(dict(first.ballots)["1"], ("B",))
        self.assertEqual(first.winner, "B")
        self.assertEqual(frame_metrics(scenario, first)["convergence"]["status"], "certified_equilibrium")
        checkpoint = sim.checkpoint()
        restored = Simulation.from_checkpoint(checkpoint)
        self.assertEqual(restored.run(8), sim.run(8))
        self.assertTrue(all(frame.ballots == first.ballots for frame in sim.frames[1:]))
        checkpoint["frames"][1]["ballots"]["1"] = ["A"]
        with self.assertRaisesRegex(ElectionError, "history"):
            Simulation.from_checkpoint(checkpoint)

    def test_certification_rejects_unsupported_scenarios_and_edits_atomically(self):
        mutations = [lambda x: x.update(k=2),
                     lambda x: x.pop("convergence"),
                     lambda x: x["groups"]["residents"].update(voting="sincere"),
                     lambda x: x["groups"]["residents"].update(movement="random_walk"),
                     lambda x: x["groups"]["residents"].update(communication="truthful"),
                     lambda x: x["groups"]["residents"].update(graph="python:strategy_fixture:graph"),
                     lambda x: x["people"][0].update(overrides={"voting":"sincere"}),
                     lambda x: x["groups"]["residents"].update(parameters={"voting":{"radius":2}}),
                     lambda x: x.update(convergence=None),
                     lambda x: x.update(interventions=[{"round":1,"person":"1","group":"residents"}]),
                     lambda x: x.update(convergence={"case":"direct_best_response", "extra":True})]
        for mutate in mutations:
            data = copy.deepcopy(example()); mutate(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        sim = Simulation(make_scenario(example())); original = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "exclude interactive"):
            sim.edit_after(0, "1", ballot=["A"])
        self.assertEqual(original, sim.checkpoint())
        forged = sim.checkpoint()
        forged["manual_interventions"] = [{"round":1,"person":"1","ballot":["A"]}]
        with self.assertRaisesRegex(ElectionError, "cannot contain interactive"):
            Simulation.from_checkpoint(forged)
        with self.assertRaises(ElectionError):
            Simulation(replace(sim.scenario, k=2))

    def test_cli_summary_browser_and_full_run_match(self):
        data = example(); data["rounds"] = 4
        sim = Simulation(make_scenario(data)); session = Session(sim)
        self.assertTrue(session.snapshot()["startup_voting_locked"])
        for revision in range(4):
            result = session.command({"revision":revision,"action":"step"})
            self.assertEqual(result["metric"]["convergence"], frame_metrics(sim.scenario, sim.current)["convergence"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["run", "examples/certified-direct.toml", "--summary"]), 0)
        rows = json.loads(output.getvalue())["metrics"]
        self.assertEqual([row["convergence"] for row in rows[:5]],
                         [frame_metrics(sim.scenario, frame)["convergence"] for frame in sim.frames])

    def test_single_candidate_certifies_immediately(self):
        data = {"parties":["A"],"k":1,"groups":{"x":{"voting":"direct_best_response"}},
                "people":[{"id":"x","group":"x","preference":["A"]}],
                "convergence":{"case":"direct_best_response"}}
        sim = Simulation(make_scenario(data))
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "certified_equilibrium")
        self.assertEqual(sim.step().winner, "A")

    def test_source_dominance_matches_independent_all_world_oracle(self):
        parties = ("A", "B", "C")
        for votes in itertools.product(range(3), repeat=3):
            counts = {party: votes.count(i) for i, party in enumerate(parties)}
            for pref in itertools.permutations(range(3)):
                profiles = (pref, (0, 1, 2), (0, 1, 2))
                for radius in (0, 1, 2):
                    possible = list(dominance_moves(votes, profiles, radius))
                    expected = possible[0][0] if possible and possible[0][1:] == votes[1:] else votes[0]
                    actual = source_local_dominance(parties, counts, parties[votes[0]],
                                                    tuple(parties[i] for i in pref), radius, 10000)
                    self.assertEqual(actual, parties[expected])

    def test_source_dominance_certificate_resume_and_limits(self):
        with Path("examples/certified-local-dominance.toml").open("rb") as handle:
            data = tomllib.load(handle)
        sim = Simulation(make_scenario(data)); sim.run(15)
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "certified_policy_equilibrium")
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        data["groups"]["residents"]["parameters"]["voting"]["max_states"] = 1
        limited = Simulation(make_scenario(data)); before = limited.checkpoint()
        row = frame_metrics(limited.scenario, limited.current)["convergence"]
        self.assertEqual(row["status"], "unavailable")
        self.assertIsNone(row["improving_voters"])
        with self.assertRaisesRegex(ElectionError, "max_states"): limited.step()
        self.assertEqual(limited.checkpoint(), before)
        data["people"][0]["overrides"] = {"parameters":{"voting":{"radius":2}}}
        with self.assertRaisesRegex(ElectionError, "common radius"): make_scenario(data)

    def test_sequential_conformity_breaks_simultaneous_copying_cycle(self):
        with Path("examples/certified-conformity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        scenario = make_scenario(data); sim = Simulation(scenario)
        self.assertEqual(frame_metrics(scenario, sim.current)["convergence"]["improving_voters"], 2)
        first = sim.step()
        self.assertEqual(dict(first.ballots), {"1":("B",), "2":("B",)})
        self.assertEqual(frame_metrics(scenario, first)["convergence"]["status"], "certified_policy_equilibrium")
        sim.run(5)
        self.assertTrue(all(frame.ballots == first.ballots for frame in sim.frames[1:]))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        data["network"]["persistent_edges"] = [["1", "2"]]
        with self.assertRaisesRegex(ElectionError, "undirected"): make_scenario(data)
        data["network"]["persistent_edges"] = []
        data["groups"]["residents"]["capabilities"]["sense_public_ballots"] = False
        with self.assertRaisesRegex(ElectionError, "sensing"): make_scenario(data)

    def test_conformity_finite_interventions_exhaustive_post_event_states(self):
        # Enumerate every 3-voter, 2-candidate ranking, ballot and undirected graph.
        # Intervention ballots are committed after round 1; never reset to sincere.
        parties = ("A", "B")
        possible_edges = ((0, 1), (0, 2), (1, 2))
        checked = 0
        for edge_mask in range(8):
            edges = tuple(edge for index, edge in enumerate(possible_edges) if edge_mask & (1 << index))
            neighbors = tuple(tuple(j for j in range(3) if (min(i, j), max(i, j)) in edges)
                              for i in range(3))
            for preferences in itertools.product(((0, 1), (1, 0)), repeat=3):
                for ballots in itertools.product(range(2), repeat=3):
                    raw = {"parties": list(parties), "k": 1,
                           "convergence": {"case": "certified_conformity"},
                           "groups": {"x": {"voting": "certified_conformity",
                                            "capabilities": {"sense_public_ballots": True}}},
                           "network": {"persistent_edges": [[str(a), str(b)] for a, b in edges
                                                              for a, b in ((a, b), (b, a))]},
                           "people": [{"id": str(i), "group": "x",
                                       "preference": [parties[c] for c in preferences[i]]}
                                      for i in range(3)],
                           "interventions": [{"round": 1, "person": str(i), "ballot": [parties[ballots[i]]]}
                                             for i in range(3)]}
                    sim = Simulation(make_scenario(raw))
                    self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"],
                                     "pending_intervention")
                    sim.step()
                    actual = tuple(parties.index(dict(sim.current.ballots)[str(i)][0]) for i in range(3))
                    self.assertEqual(actual, ballots)
                    changes = 0
                    bound = 2 * len(edges) + 3
                    for _ in range(3 * (bound + 1)):
                        choices = tuple(conformity_choice(actual, preferences[i], neighbors[i]) for i in range(3))
                        status = frame_metrics(sim.scenario, sim.current)["convergence"]
                        self.assertEqual(status["improving_voters"], sum(c != b for c, b in zip(choices, actual)))
                        if choices == actual:
                            self.assertEqual(status["status"], "certified_policy_equilibrium")
                            break
                        self.assertEqual(status["status"], "not_equilibrium")
                        active = sim.current.round % 3
                        expected = actual[:active] + (choices[active],) + actual[active + 1:]
                        sim.step()
                        new = tuple(parties.index(dict(sim.current.ballots)[str(i)][0]) for i in range(3))
                        self.assertEqual(new, expected)
                        if new != actual:
                            self.assertGreater(potential(new, preferences, edges), potential(actual, preferences, edges))
                            changes += 1
                        actual = new
                    else:
                        self.fail((edges, preferences, ballots, "failed to reach certified fixed point"))
                    self.assertLessEqual(changes, bound)
                    checked += 1
        self.assertEqual(checked, 512)

    def test_conformity_preference_and_ballot_interventions_preserve_certification_contract(self):
        with Path("examples/certified-conformity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        data["interventions"] = [{"round": 3, "person": "1", "preference": ["B", "A"], "ballot": ["A"]}]
        sim = Simulation(make_scenario(data))
        sim.run(2)
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "pending_intervention")
        sim.step()
        self.assertEqual(dict(sim.current.preferences)["1"], ("B", "A"))
        self.assertEqual(dict(sim.current.ballots)["1"], ("A",))
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "not_equilibrium")
        sim.run(3)
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "certified_policy_equilibrium")
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        for change in ({"position": [0, 0]}, {"add_edges": ["2"]}, {"group": "residents"},
                       {"overrides": {"voting": "sincere"}}):
            invalid = copy.deepcopy(data)
            invalid["interventions"] = [{"round": 3, "person": "1", **change}]
            with self.subTest(change=change), self.assertRaises(ElectionError):
                make_scenario(invalid)
        invalid = copy.deepcopy(data)
        invalid["groups"]["residents"]["voting"] = "source_local_dominance"
        invalid["convergence"]["case"] = "source_local_dominance"
        with self.assertRaisesRegex(ElectionError, "excludes scheduled interventions"):
            make_scenario(invalid)

    def test_conformity_intervention_cli_session_export_and_future_cutoff(self):
        path = "examples/certified-conformity-intervention.toml"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["run", path, "--until-equilibrium"]), 0)
        result = json.loads(output.getvalue())
        rows = result["metrics"]
        self.assertEqual([row["convergence"]["status"] for row in rows[:3]], ["pending_intervention"] * 3)
        self.assertEqual(rows[3]["convergence"]["status"], "not_equilibrium")
        self.assertEqual(rows[-1]["convergence"]["status"], "certified_policy_equilibrium")
        self.assertGreater(rows[-1]["round"], 3)
        with Path(path).open("rb") as handle:
            data = tomllib.load(handle)
        sim = Simulation(make_scenario(data)); session = Session(sim)
        for revision in range(rows[-1]["round"]):
            session.command({"revision": revision, "action": "step"})
            self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"],
                             rows[revision + 1]["convergence"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"; output_path = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", path, "--until-equilibrium", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(output_path)]), 0)
            with output_path.open(newline="") as handle:
                exported = list(csv.DictReader(handle))
            self.assertEqual(exported[0]["convergence:status"], "pending_intervention")
            self.assertEqual(exported[-1]["convergence:status"], "certified_policy_equilibrium")
        data["interventions"][0]["round"] = data["rounds"] + 10
        truncated = Simulation(make_scenario(data)); truncated.run(data["rounds"])
        self.assertEqual(frame_metrics(truncated.scenario, truncated.current)["convergence"]["status"],
                         "pending_intervention")

    def test_conformity_isolates_choose_favourite_and_ties_use_private_ranking(self):
        from multi_agent_election.voting import certified_conformity
        self.assertEqual(certified_conformity(("B", "A"), []), "B")
        self.assertEqual(certified_conformity(("B", "A"), [("A",), ("B",)]), "B")
        self.assertEqual(certified_conformity(("B", "A"), [("A",), ("A",), ("B",)]), "A")

    def test_pending_intervention_invalidates_early_certificate_and_preserves_actual_ballot(self):
        data = example()
        data["interventions"] = [{"round": 3, "person": "1", "ballot": ["C"]}]
        sim = Simulation(make_scenario(data)); sim.run(1)
        status = frame_metrics(sim.scenario, sim.current)["convergence"]
        self.assertEqual(status["status"], "pending_intervention")
        self.assertEqual(status["next_intervention_round"], 3)
        sim.run(2)
        self.assertEqual(dict(sim.current.ballots)["1"], ("C",))
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "not_equilibrium")
        sim.run(5)
        self.assertEqual(frame_metrics(sim.scenario, sim.current)["convergence"]["status"], "certified_equilibrium")
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_checkpoint_export_includes_certificate_history(self):
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"
            output = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/certified-intervention.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(output)]), 0)
            with output.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["convergence:status"], "pending_intervention")
            self.assertEqual(rows[0]["convergence:next_intervention_round"], "3")
            self.assertEqual(rows[-1]["convergence:status"], "certified_equilibrium")

    def test_stop_at_certificate_respects_pending_events_and_sampled_final_frame(self):
        for recording in ([], ["--summary"], ["--sample", "4"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["run", "examples/certified-intervention.toml", "--until-equilibrium", *recording]), 0)
            result = json.loads(output.getvalue())
            self.assertGreaterEqual(result["metrics"][-1]["round"], 3)
            self.assertEqual(result["metrics"][-1]["convergence"]["status"], "certified_equilibrium")
            if "frames" in result:
                self.assertEqual(result["frames"][-1]["round"], result["metrics"][-1]["round"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["run", "examples/baseline.toml", "--until-equilibrium"]), 2)

    def test_engine_transitions_against_independent_models_for_all_two_voter_profiles(self):
        parties = ("A", "B", "C")
        for case in ("direct_best_response", "source_local_dominance", "certified_conformity"):
            for prefs in itertools.product(tuple(itertools.permutations(range(3))), repeat=2):
                group = {"voting":case}
                if case == "source_local_dominance":
                    group["parameters"] = {"voting":{"radius":1}}
                if case == "certified_conformity":
                    group["capabilities"] = {"sense_public_ballots":True}
                raw = {"parties":list(parties), "k":1, "convergence":{"case":case},
                       "groups":{"x":group}, "network":{"persistent_edges":[["0","1"],["1","0"]]},
                       "people":[{"id":str(i),"group":"x","preference":[parties[p] for p in prefs[i]]}
                                 for i in range(2)]}
                sim = Simulation(make_scenario(raw))
                for step in range(6):
                    before = tuple(parties.index(dict(sim.current.ballots)[str(i)][0]) for i in range(2))
                    active = step % 2
                    if case == "certified_conformity":
                        choice = conformity_choice(before, prefs[active], (1-active,))
                        expected = before[:active] + (choice,) + before[active+1:]
                    else:
                        moves = direct_moves(before, prefs) if case == "direct_best_response" else dominance_moves(before, prefs, 1)
                        expected = next((after for after in moves if after[active] != before[active]), before)
                    sim.step()
                    actual = tuple(parties.index(dict(sim.current.ballots)[str(i)][0]) for i in range(2))
                    self.assertEqual(actual, expected, (case, prefs, before, active))


if __name__ == "__main__":
    unittest.main()
