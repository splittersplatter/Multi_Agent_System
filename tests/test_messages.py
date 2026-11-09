import copy
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class MessageTests(VerificationTestCase):
    def scenario(self):
        data = example()
        data["groups"]["residents"]["communication"] = "truthful"
        data["groups"]["strategic"] = {"voting": "local_plurality", "communication": "none"}
        data["people"][3]["group"] = "strategic"
        data["network"] = {"persistent_edges": [["1", "4"], ["2", "4"]],
                           "private_channels": {"private": ["2", "3"]}}
        return data

    def test_one_round_delay_scoped_delivery_and_checkpoint(self):
        sim = Simulation(make_scenario(self.scenario()))
        frame1 = sim.step()
        self.assertEqual(frame1.delivered, ())
        self.assertEqual(dict(frame1.ballots)["4"], ("B", "A"))
        frame2 = sim.step()
        self.assertEqual(dict(frame2.ballots)["4"], ("A", "B"))
        self.assertEqual({(a, b, c) for a, b, c, _ in frame2.delivered},
                         {("1", "4", "public"), ("2", "4", "public"),
                          ("2", "3", "private"), ("3", "2", "private")})
        self.assertTrue(all(not (channel == "private" and to == "4") for _, to, channel, _ in frame2.delivered))
        resumed = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.run(2), resumed.run(2))

    def test_reject_invalid_channel(self):
        for channels in ({"public": ["1"]}, {"x": ["1", "1"]}, {"x": ["unknown"]}):
            data = copy.deepcopy(self.scenario()); data["network"]["private_channels"] = channels
            with self.subTest(channels=channels), self.assertRaises(ElectionError):
                make_scenario(data)

    def test_phase_specific_provenance_tracks_generation_and_delivery(self):
        data = example()
        data["groups"]["residents"]["communication"] = "truthful"
        data["people"][1]["overrides"] = {"voting":"python:strategy_fixture:capture_report_provenance",
                                          "movement":"python:strategy_fixture:capture_movement_provenance"}
        data["network"] = {"persistent_edges":[["1","2"]]}
        # The report sent during round 1 contains sender 1's round-0 ballot,
        # even though a boundary intervention changes its round-1 ballot.
        data["interventions"] = [{"round":1,"person":"1","ballot":["B","A"]}]
        sim = Simulation(make_scenario(data)); sim.run(2)
        voting = sim.current.as_dict()["policy_memory"]["2"]
        self.assertEqual(voting["messages"], [["1","public",["A","B"]]])
        self.assertEqual(voting["provenance"], [["1","public",1,0,2,["A","B"]]])
        recorded = sim.current.as_dict()["report_provenance"]["delivered"]
        self.assertIn({"sender":"1", "recipient":"2", "channel":"public", "ballot":["A","B"],
                       "source_round":0, "generated_round":1, "delivered_round":2}, recorded)
        tampered = sim.checkpoint()
        tampered["frames"][2]["report_provenance"]["delivered"][0]["source_round"] = 1
        with self.assertRaisesRegex(ElectionError, "history does not match"):
            Simulation.from_checkpoint(tampered)
        self.assertEqual(dict(sim.current.ballots)["1"], ("A","B"))
        sim.step()
        movement = {(person, phase): memory for person, phase, memory in sim.current.as_dict()["phase_memory"]}
        self.assertEqual(movement[("2","movement")]["provenance"], [["1","public",1,0,2,["A","B"]]])
        voting = sim.current.as_dict()["policy_memory"]["2"]
        self.assertEqual(voting["provenance"], [["1","public",2,1,3,["B","A"]]])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_revocation_hides_report_and_its_provenance(self):
        data = example()
        data["groups"]["residents"]["communication"] = "truthful"
        data["network"] = {"persistent_edges":[["1","2"]]}
        data["people"][1]["overrides"] = {"voting":"python:strategy_fixture:capture_report_provenance"}
        sim = Simulation(make_scenario(data)); sim.step()
        sim.edit_after(1, "2", overrides={"voting":"python:strategy_fixture:capture_report_provenance",
                                          "capabilities":{"receive_public_reports":False}})
        frame = sim.step()
        self.assertEqual(frame.as_dict()["policy_memory"]["2"], {"messages":[],"provenance":[]})
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, frame)

    def test_legacy_migration_does_not_rewrite_unrelated_plugin_memory(self):
        data = example()
        data["people"][0]["overrides"] = {"voting":"python:strategy_fixture:unrelated_history"}
        sim = Simulation(make_scenario(data)); sim.step()
        old = sim.checkpoint(); old["version"] = 10
        for frame in old["frames"]: frame.pop("report_provenance")
        restored = Simulation.from_checkpoint(old)
        self.assertEqual(restored.current, sim.current)


if __name__ == "__main__": unittest.main()
