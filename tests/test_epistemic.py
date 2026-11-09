import contextlib
import copy
import io
import itertools
import json
import tomllib
import unittest
from verification_support import VerificationTestCase
from pathlib import Path
from dataclasses import replace

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.epistemic import KnowledgeModel, response_from_observation
from multi_agent_election.policies import Observation
from multi_agent_election.visual import Session


def example():
    return json.loads(Path("examples/knowledge-profile.json").read_text())


class KnowledgeModelTests(VerificationTestCase):
    def test_de_dicto_de_re_dominance_and_pessimism(self):
        model = KnowledgeModel.from_dict(example())
        result = model.analyze("1")
        self.assertEqual(result["baseline_winners"], ["B", "C"])
        self.assertEqual(result["action_winners"]["A"], ["A", "C"])
        self.assertEqual(result["action_winners"]["B"], ["B", "B"])
        self.assertTrue(result["de_dicto"])
        self.assertEqual(result["de_re"], [])
        self.assertEqual(result["dominant"], ["A", "B"])
        self.assertEqual(result["pessimistic"], ["B"])

    def test_factive_knowledge_nested_relations_and_truthful_announcements(self):
        model = KnowledgeModel.from_dict(example())
        is_left = lambda world: world.id == "left"
        self.assertFalse(model.knows("1", is_left))
        self.assertTrue(model.possible("1", is_left))
        self.assertTrue(model.knows("2", is_left))
        self.assertFalse(model.knows("1", lambda world: model.knows("2", is_left, world.id)))
        with self.assertRaisesRegex(ElectionError, "false at the actual"):
            model.announce(lambda world: world.id == "right")
        updated = model.announce(is_left)
        self.assertEqual([w.id for w in updated.worlds], ["left"])
        self.assertEqual(updated.actual, "left")
        self.assertTrue(updated.knows("1", is_left))
        self.assertEqual(updated.analyze("1")["de_re"], ["A"])
        self.assertEqual(len(model.worlds), 2)  # update is immutable

    def test_conditional_profile_checks_every_information_set(self):
        raw = {"parties":["A","B"],"k":1,"agents":["1"],"actual":"left",
               "worlds":[{"id":side,"preferences":{"1":["A","B"]},"ballots":{"1":["A"]},
                          "observations":{"1":side}} for side in ("left","right")]}
        model = KnowledgeModel.from_dict(raw)
        profile = {"1":{"left":"A", "right":"B"}}
        result = model.conditional_equilibrium(profile)
        self.assertFalse(result["equilibrium"])
        cells = {row["observation"]: row for row in result["information_sets"]}
        self.assertEqual(cells["left"]["pessimistic_deviations"], [])
        self.assertEqual(cells["right"]["pessimistic_deviations"], ["A"])
        # Conditional actions are not overwritten by each world's recorded ballot.
        self.assertEqual(cells["right"]["baseline_worst"], "B")
        updated, restricted = model.announce_with_profile(lambda w: w.id == "left", profile)
        self.assertEqual(restricted, {"1":{"left":"A"}})
        self.assertTrue(updated.conditional_equilibrium(restricted)["equilibrium"])
        with self.assertRaisesRegex(ElectionError, "false at the actual"):
            model.announce_with_profile(lambda w: w.id == "right", profile)

    def test_conditional_solver_matches_independent_nash_enumeration(self):
        data = json.loads(Path("examples/knowledge-two-voters.json").read_text())
        model = KnowledgeModel.from_dict(data)
        result = model.solve_conditional_equilibria()
        actual = {(p["1"]["only"], p["2"]["only"]) for p in result["equilibria"]}
        preferences = (("A","B","C"), ("C","B","A"))
        parties = tuple(data["parties"])
        def winner(votes):
            return min(parties, key=lambda c: (-votes.count(c), parties.index(c)))
        expected = set()
        for actions in itertools.product(parties, repeat=2):
            if all(not any(preferences[i].index(winner(actions[:i]+(choice,)+actions[i+1:]))
                               < preferences[i].index(winner(actions)) for choice in parties)
                   for i in range(2)):
                expected.add(actions)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, {("A","B"), ("B","B")})
        self.assertEqual(result["profiles_checked"], 9)

    def test_conditional_solver_matches_independent_multiworld_oracle(self):
        raw = {"parties":["A","B"],"k":1,"agents":["1","2"],"actual":"left",
               "worlds":[
                   {"id":"left","preferences":{"1":["A","B"],"2":["B","A"]},
                    "ballots":{"1":["A"],"2":["B"]},"observations":{"1":"shared","2":"left"}},
                   {"id":"right","preferences":{"1":["A","B"],"2":["A","B"]},
                    "ballots":{"1":["A"],"2":["A"]},"observations":{"1":"shared","2":"right"}}]}
        model = KnowledgeModel.from_dict(raw)
        def is_equilibrium(profile):
            for actor in raw["agents"]:
                for label in {w["observations"][actor] for w in raw["worlds"]}:
                    worlds = [w for w in raw["worlds"] if w["observations"][actor] == label]
                    preference = worlds[0]["preferences"][actor]
                    def worst(replacement=None):
                        outcomes = []
                        for world in worlds:
                            choices = [replacement if other == actor and replacement is not None else
                                       profile[other][world["observations"][other]] for other in raw["agents"]]
                            winner = min(raw["parties"], key=lambda p: (-choices.count(p), raw["parties"].index(p)))
                            outcomes.append(preference.index(winner))
                        return max(outcomes)
                    if any(worst(choice) < worst() for choice in raw["parties"]):
                        return False
            return True
        expected = set()
        for one, left, right in itertools.product(raw["parties"], repeat=3):
            profile = {"1":{"shared":one}, "2":{"left":left,"right":right}}
            oracle = is_equilibrium(profile)
            self.assertEqual(model.conditional_equilibrium(profile)["equilibrium"], oracle)
            if oracle:
                expected.add((one,left,right))
        result = model.solve_conditional_equilibria()
        actual = {(p["1"]["shared"],p["2"]["left"],p["2"]["right"]) for p in result["equilibria"]}
        self.assertEqual(actual, expected)
        self.assertEqual(result["profiles_checked"], 8)

    def test_conditional_profile_matches_submitted_world_ballots(self):
        model = KnowledgeModel.from_dict(example())
        profile = json.loads(Path("examples/conditional-profile.json").read_text())
        result = model.conditional_equilibrium(profile)
        row = next(r for r in result["information_sets"] if r["agent"] == "1")
        self.assertEqual(row["pessimistic_deviations"], model.analyze("1")["pessimistic"])
        self.assertEqual(row["baseline_winners"], ["B", "C"])
        self.assertFalse(result["equilibrium"])
        for invalid in ({}, {**profile, "1":{}}, {**profile,"1":{"unknown":"Z"}},
                        {**profile,"extra":{}}):
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError):
                model.conditional_equilibrium(invalid)
        with self.assertRaisesRegex(ElectionError, "max_evaluations"):
            model.conditional_equilibrium(profile, max_evaluations=1)
        with self.assertRaisesRegex(ElectionError, "max_profiles"):
            model.solve_conditional_equilibria(max_profiles=1)
        with self.assertRaisesRegex(ElectionError, "max_evaluations"):
            model.solve_conditional_equilibria(max_evaluations=32)

    def test_conditional_cli_check_and_solve(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["knowledge", "examples/knowledge-profile.json", "--conditional",
                                   "examples/conditional-profile.json"]), 0)
        self.assertFalse(json.loads(output.getvalue())["analysis"]["equilibrium"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["knowledge", "examples/knowledge-two-voters.json", "--solve-conditional"]), 0)
        self.assertEqual(len(json.loads(output.getvalue())["analysis"]["equilibria"]), 2)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["knowledge", "examples/knowledge-two-voters.json", "--solve-conditional", "--agent", "1"]), 2)
            self.assertEqual(main(["knowledge", "examples/knowledge-two-voters.json"]), 2)

    def test_worlds_are_separate_even_with_identical_profiles(self):
        data = example()
        data["worlds"][1]["preferences"] = copy.deepcopy(data["worlds"][0]["preferences"])
        data["worlds"][1]["ballots"] = copy.deepcopy(data["worlds"][0]["ballots"])
        model = KnowledgeModel.from_dict(data)
        self.assertEqual(len(model.information_set("1")), 2)
        self.assertFalse(model.knows("1", lambda w: w.id == "left"))
        self.assertTrue(model.knows("2", lambda w: w.id == "left"))

    def test_partition_cannot_hide_own_preference_ballot_or_public_info(self):
        for mutation in (lambda x: x["worlds"][1]["preferences"].update({"1":["B","A","C"]}),
                         lambda x: x["worlds"][1]["ballots"].update({"1":["A"]}),
                         lambda x: x["worlds"][1].update(public_signal={"A":2}),
                         lambda x: x["worlds"][1].update(public_history=[{"round":1}])):
            data = example(); mutation(data)
            with self.subTest(data=data), self.assertRaisesRegex(ElectionError, "known own/public"):
                KnowledgeModel.from_dict(data)

    def test_validation_fails_closed_and_defensively_copies(self):
        for mutation in (lambda x: x.update(actual="missing"),
                         lambda x: x.update(k=True),
                         lambda x: x["worlds"][0]["ballots"].update({"1":["Z"]}),
                         lambda x: x["worlds"][0]["preferences"].update({"1":["A","A","C"]}),
                         lambda x: x["worlds"][1].update(id="left"),
                         lambda x: x["worlds"][0]["observations"].pop("1"),
                         lambda x: x["worlds"][0].update(public_signal=float("nan"))):
            data = example(); mutation(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): KnowledgeModel.from_dict(data)
        with self.assertRaisesRegex(ElectionError, "max_worlds"):
            KnowledgeModel.from_dict(example(), max_worlds=1)
        data = example(); model = KnowledgeModel.from_dict(data)
        data["worlds"][0]["preferences"]["1"][0] = "C"
        self.assertEqual(dict(model.world().preferences)["1"], ("A","B","C"))
        self.assertEqual(KnowledgeModel.from_dict(model.as_dict()), model)

    def test_cli_emits_exact_analysis_and_limits(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["knowledge", "examples/knowledge-profile.json", "--agent", "1"]), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["analysis"]["dominant"], ["A", "B"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["knowledge", "examples/knowledge-profile.json", "--agent", "1", "--max-worlds", "1"]), 2)
            self.assertEqual(main(["knowledge", "examples/knowledge-profile.json", "--agent", "unknown"]), 2)

    def test_agent_information_projection_counts_complete_logical_worlds(self):
        obs = Observation("1", 1, ("A","B","C"), 2, ("A","B","C"), (0.5,0.5), (),
                          ("C","A"), (), (), (), ("1","2","3"))
        for policy in ("epistemic_dere", "epistemic_dominant", "epistemic_pessimistic"):
            ballot, trace = response_from_observation(policy, obs, {"max_worlds":1296})
            self.assertEqual(trace["world_count"], 6**2 * 6**2)
            self.assertEqual(trace["projected_ballot_profiles"], 3**2)
            self.assertEqual(len(ballot), 2)
            self.assertEqual(set(trace["unobserved_preferences"]), {"2", "3"})
            with self.assertRaisesRegex(ElectionError, "max_worlds"):
                response_from_observation(policy, obs, {"max_worlds":1295})
        sensed = replace(obs, sensed_ballots=(("2","public",0,("B","C")),))
        _, trace = response_from_observation("epistemic_dere", sensed, {})
        self.assertEqual(trace["world_count"], 6**2 * 6)
        self.assertEqual(trace["projected_ballot_profiles"], 3)
        self.assertEqual(trace["observed_ballots"], {"2":["B","C"]})
        self.assertNotIn("C", trace["de_re"])  # keeping the current choice never strictly improves

    def test_factored_agent_decisions_match_explicit_preference_and_ballot_worlds(self):
        parties = ("A", "B", "C")
        orders = tuple(itertools.permutations(parties))
        for k in (1, 2):
            for sensed in (False, True):
                sensor = (("2","public",0,tuple(parties[:k])),) if sensed else ()
                obs = Observation("1", 1, parties, k, ("A","B","C"), (0.5,0.5), (),
                                  tuple(reversed(parties))[:k], (), (), sensor, ("1","2","3"))
                ballots = tuple(itertools.permutations(parties, k))
                voters2 = (tuple(parties[:k]),) if sensed else ballots
                worlds = []
                for p2, p3, b2, b3 in itertools.product(orders, orders, voters2, ballots):
                    wid = str(len(worlds))
                    worlds.append({"id":wid, "preferences":{"1":list(obs.own_preference),"2":list(p2),"3":list(p3)},
                                   "ballots":{"1":list(obs.own_previous_ballot),"2":list(b2),"3":list(b3)},
                                   "observations":{"1":"same","2":"2-"+wid,"3":"3-"+wid}})
                model = KnowledgeModel.from_dict({"parties":list(parties),"agents":["1","2","3"],"k":k,
                                                  "worlds":worlds,"actual":"0"})
                exact = model.analyze("1")
                for policy in ("epistemic_dere", "epistemic_dominant", "epistemic_pessimistic"):
                    _, trace = response_from_observation(policy, obs, {})
                    self.assertEqual(trace["world_count"], len(worlds))
                    for field in ("de_dicto", "de_re", "dominant", "pessimistic"):
                        self.assertEqual(trace[field], exact[field], (k,sensed,policy,field))

    def test_agent_rejects_forged_or_stale_observations(self):
        obs = Observation("1", 1, ("A","B"), 1, ("A","B"), (0.5,0.5), (),
                          ("B",), (), (), (), ("1","2"))
        cases = [replace(obs, electorate=()),
                 replace(obs, own_previous_ballot=()),
                 replace(obs, own_preference=("A","A")),
                 replace(obs, sensed_ballots=(("2","public",1,("A",)),)),
                 replace(obs, sensed_ballots=(("3","public",0,("A",)),)),
                 replace(obs, sensed_ballots=(("2","public",0,("A",)),("2","team",0,("B",))))]
        for invalid in cases:
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError):
                response_from_observation("epistemic_dere", invalid, {})

    def test_no_justified_move_retains_entire_submitted_ballot(self):
        obs = Observation("1", 1, ("A","B","C"), 3, ("A","B","C"), (0.5,0.5), (),
                          ("C","B","A"), (), (), (), ("1","2"))
        ballot, trace = response_from_observation("epistemic_dere", obs, {})
        self.assertEqual(trace["de_re"], [])
        self.assertEqual(ballot, ("C","B","A"))

    def test_integrated_epistemic_trace_hidden_isolation_and_replay(self):
        with Path("examples/epistemic.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        sim = Simulation(make_scenario(raw)); first = sim.step()
        self.assertEqual(dict(first.ballots)["1"], ("C",))
        second = sim.step(); trace = second.as_dict()["policy_memory"]["1"]
        self.assertEqual(dict(second.ballots)["1"], ("A",))
        self.assertEqual(trace["de_re"], ["A"])
        self.assertEqual(trace["world_count"], 216)
        self.assertEqual(trace["projected_ballot_profiles"], 1)
        alternate = copy.deepcopy(raw)
        alternate["people"][1]["preference"] = ["A","C","B"]
        alternate["people"][2]["preference"] = ["B","C","A"]
        other = Simulation(make_scenario(alternate)); other.run(2)
        self.assertEqual(second.as_dict()["policy_memory"]["1"], other.current.as_dict()["policy_memory"]["1"])
        self.assertEqual(dict(second.ballots)["1"], dict(other.current.ballots)["1"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        sim.edit_after(1, "1", ballot=["C"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_cumulative_mixed_information_cli_session_and_rewind(self):
        path = "examples/epistemic-integrated.toml"
        with Path(path).open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["run", path]), 0)
        cli = json.loads(output.getvalue())
        session = Session(Simulation(scenario))
        frames, metrics = session.snapshot()["frames"], session.snapshot()["metrics"]
        for revision in range(4):
            reply = session.command({"action":"step", "revision":revision})
            frames.append(reply["frame"]); metrics.append(reply["metric"])
        self.assertEqual(frames, cli["frames"])
        self.assertEqual(metrics, cli["metrics"])
        self.assertEqual([frame["winner"] for frame in frames], ["A", "B", "A", "A", "A"])
        self.assertNotEqual(frames[0]["positions"]["1"], frames[1]["positions"]["1"])
        reasoner, poll = frames[2]["policy_memory"]["1"], frames[2]["policy_memory"]["2"]
        self.assertEqual((reasoner["previous"],reasoner["choice"],reasoner["de_re"]), ("C","A",["A"]))
        self.assertEqual(reasoner["world_count"], 216)
        self.assertEqual((poll["policy"],poll["scores"],poll["choice"]), ("pivotal",[1,2,1],"A"))
        self.assertEqual(frames[2]["ballots"]["3"], ["B"])
        history = reasoner["observation_history"][-1]
        self.assertEqual({r["channel"] for r in history["received_reports"]}, {"public","team"})
        self.assertTrue(all(r["source_round"] == 0 and r["delivered_round"] == 2 for r in history["received_reports"]))
        self.assertTrue(all(r["completed_round"] == 1 for r in history["trusted_ballots"]))
        self.assertNotIn("convergence", metrics[-1])
        restored = Simulation.from_checkpoint(session.simulation.checkpoint())
        self.assertEqual(restored.current, session.simulation.current)
        edited = session.command({"action":"edit", "revision":4, "round":1, "person":"1",
                                  "changes":{"overrides":{"capabilities":{"sense_public_ballots":False}}}})
        self.assertEqual(len(edited["frames"]), 2)
        updated = session.command({"action":"step", "revision":5})["frame"]
        self.assertEqual(updated["policy_memory"]["1"]["world_count"], 5832)
        observations = updated["policy_memory"]["1"]["observation_history"]
        self.assertTrue(observations[0]["trusted_ballots"])
        self.assertFalse(observations[1]["trusted_ballots"])
        self.assertEqual(Simulation.from_checkpoint(session.simulation.checkpoint()).current.as_dict(), updated)

    def test_cumulative_hidden_preferences_future_and_private_report_isolation(self):
        with Path("examples/epistemic-integrated.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        alternate = copy.deepcopy(raw)
        alternate["people"][2]["preference"] = ["B","C","A"]
        alternate["people"][3]["preference"] = ["B","A","C"]
        alternate["interventions"].append({"round":4,"person":"4","preference":["C","B","A"]})
        left, right = Simulation(make_scenario(raw)), Simulation(make_scenario(alternate))
        left.run(2); right.run(2)
        self.assertEqual(left.current.as_dict()["policy_memory"]["1"], right.current.as_dict()["policy_memory"]["1"])
        self.assertEqual(dict(left.current.ballots)["1"], dict(right.current.ballots)["1"])
        revoked = copy.deepcopy(raw)
        revoked["groups"]["reasoner"]["capabilities"]["receive_private_reports"] = False
        denied = Simulation(make_scenario(revoked)); denied.run(2)
        memory = denied.current.as_dict()["policy_memory"]["1"]
        self.assertTrue(memory["observation_history"][-1]["received_reports"])
        self.assertTrue(all(r["channel"] == "public" for r in memory["observation_history"][-1]["received_reports"]))
        self.assertEqual(memory["de_re"], left.current.as_dict()["policy_memory"]["1"]["de_re"])

    def test_integrated_permission_limit_and_ui_atomicity(self):
        with Path("examples/epistemic.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        data = copy.deepcopy(raw); data["groups"]["reasoner"]["capabilities"]["observe_electorate"] = False
        with self.assertRaisesRegex(ElectionError, "observe_electorate"):
            Simulation(make_scenario(data))
        data = copy.deepcopy(raw); data["groups"]["reasoner"]["parameters"] = {"voting":{"max_worlds":215}}
        limited = Simulation(make_scenario(data)); before = limited.checkpoint()
        with self.assertRaisesRegex(ElectionError, "max_worlds"): limited.step()
        self.assertEqual(before, limited.checkpoint())
        session = Session(Simulation(make_scenario(raw)))
        self.assertIn("epistemic_dere", session.snapshot()["voting_policies"])
        for revision in range(2):
            frame = session.command({"revision":revision,"action":"step"})["frame"]
        self.assertEqual(frame["policy_memory"]["1"]["de_re"], ["A"])
        raw["groups"]["residents"]["capabilities"]["observe_electorate"] = False
        session = Session(Simulation(make_scenario(raw)))
        before = session.snapshot()
        with self.assertRaisesRegex(ElectionError, "observe_electorate"):
            session.command({"revision":0,"action":"configure_voting","policy":"epistemic_dere","parameters":{}})
        self.assertEqual(session.snapshot(), before)

    def test_observation_history_replays_rewinds_and_preserves_revoked_readings(self):
        with Path("examples/epistemic.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        raw["groups"]["reasoner"]["parameters"] = {"voting":{"remember_observations":True,"max_history":3}}
        sim = Simulation(make_scenario(raw)); sim.run(2)
        trace = sim.current.as_dict()["policy_memory"]["1"]
        history = trace["observation_history"]
        self.assertEqual([row["round"] for row in history], [1,2])
        self.assertEqual(history[0]["own_previous_ballot"], ["A"])
        self.assertEqual(history[1]["own_previous_ballot"], ["C"])
        self.assertEqual({row["completed_round"] for row in history[1]["trusted_ballots"]}, {1})
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), restored.step())
        before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "max_history"): sim.step()
        self.assertEqual(before, sim.checkpoint())
        # Rewinding restores the valid history prefix; revoked sensing does not erase memory.
        sim.edit_after(1, "1", overrides={"capabilities":{"sense_public_ballots":False}})
        next_frame = sim.step()
        history = next_frame.as_dict()["policy_memory"]["1"]["observation_history"]
        self.assertEqual([row["round"] for row in history], [1,2])
        self.assertTrue(history[0]["trusted_ballots"])
        self.assertFalse(history[1]["trusted_ballots"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_history_parameters_and_corruption_are_rejected(self):
        obs = Observation("1", 1, ("A","B"), 1, ("A","B"), (0.5,0.5), (),
                          ("B",), (), (), (), ("1","2"))
        for params in ({"remember_observations":"yes"}, {"max_history":2},
                       {"remember_observations":True,"max_history":0}):
            with self.subTest(params=params), self.assertRaises(ElectionError):
                response_from_observation("epistemic_dere", obs, params)
        with self.assertRaisesRegex(ElectionError, "history"):
            response_from_observation("epistemic_dere", obs, {"remember_observations":True},
                                      {"policy":"epistemic_dere","observation_history":[{"round":3}]})

    def test_report_provenance_and_version_ten_history_migration(self):
        with Path("examples/epistemic.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        raw["groups"]["residents"]["communication"] = "truthful"
        raw["interventions"].append({"round":1,"person":"2","ballot":["B"]})
        sim = Simulation(make_scenario(raw)); sim.run(2)
        event = sim.current.as_dict()["policy_memory"]["1"]["observation_history"][1]
        report = next(r for r in event["received_reports"] if r["sender"] == "2")
        sensor = next(r for r in event["trusted_ballots"] if r["sender"] == "2")
        self.assertEqual((report["ballot"], report["source_round"], report["generated_round"], report["delivered_round"]),
                         (["A"], 0, 1, 2))
        self.assertEqual((sensor["ballot"], sensor["completed_round"]), (["B"], 1))
        old = sim.checkpoint(); old["version"] = 10
        for frame in old["frames"]:
            frame.pop("report_provenance")
            for memory in frame["policy_memory"].values():
                if isinstance(memory, dict):
                    for item in memory.get("observation_history", []):
                        for entry in item["received_reports"]:
                            entry.pop("generated_round"); entry.pop("delivered_round"); entry["source_round"] = None
        restored = Simulation.from_checkpoint(old)
        self.assertEqual(restored.current, sim.current)
        self.assertEqual(restored.checkpoint()["version"], 21)
        old["frames"][2]["policy_memory"]["1"]["observation_history"][1]["received_reports"][0]["ballot"] = ["C"]
        with self.assertRaisesRegex(ElectionError, "history does not match"):
            Simulation.from_checkpoint(old)


if __name__ == "__main__":
    unittest.main()
