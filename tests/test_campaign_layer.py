import copy
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.metrics import series
from test_baseline import example


class CampaignLayerTests(VerificationTestCase):
    def test_layer_overlap_is_deduplicated_for_reports_and_sensors(self):
        data = example()
        for person, position in zip(data["people"], ([0.1, 0.1], [0.95, 0.9], [0.1, 0.9], [0.15, 0.1])):
            person["position"] = position
        data["network"] = {"radius": 0.1, "persistent_edges": [["1", "4"]], "campaign_edges": [["1", "4"]]}
        data["groups"]["residents"]["communication"] = "truthful"
        data["people"][3]["overrides"] = {"capabilities": {"sense_public_ballots": True}}
        sim = Simulation(make_scenario(data)); first = sim.step()
        self.assertIn(("1", "4"), first.proximity_edges)
        self.assertEqual(first.campaign_edges, (("1", "4"),))
        self.assertEqual(sum(a == "1" and b == "4" for a, b, _, _ in first.pending), 1)
        self.assertEqual(first.ballot_sensors, (("4", "1", "public", 0, ("A", "B")),))
        metrics = series(sim.scenario, sim.frames)[1]
        self.assertEqual(metrics["public_edge_count"], 2)
        self.assertEqual(metrics["campaign_edge_count"], 1)

    def test_campaign_survives_proximity_loss_and_carries_sensors(self):
        data = example()
        data["people"][0]["position"] = [0.1, 0.1]
        data["people"][3]["position"] = [0.15, 0.1]
        data["network"] = {"radius": 0.1, "campaign_edges": [["1", "4"]]}
        data["people"][3]["overrides"] = {"voting": "sensed_plurality", "capabilities": {"sense_public_ballots": True}}
        data["interventions"] = [{"round": 1, "person": "4", "position": [0.9, 0.9]}]
        sim = Simulation(make_scenario(data)); first = sim.step()
        self.assertNotIn(("1", "4"), first.proximity_edges)
        self.assertIn(("1", "4"), first.campaign_edges)
        self.assertEqual(dict(first.ballots)["4"], ("A", "B"))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).step(), sim.step())

    def test_scheduled_edits_rewind_conflicts_and_checkpoint_integrity(self):
        data = example()
        data["interventions"] = [{"round": 1, "person": "1", "add_campaign_edges": ["4"]},
                                 {"round": 2, "person": "1", "remove_campaign_edges": ["4"]}]
        sim = Simulation(make_scenario(data)); frames = sim.run(2)
        self.assertEqual(frames[0].campaign_edges, ())
        self.assertEqual(frames[1].campaign_edges, (("1", "4"),))
        self.assertEqual(frames[2].campaign_edges, ())
        before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "existing campaign"):
            sim.edit_after(0, "1", add_campaign_edges=["4"])
        self.assertEqual(sim.checkpoint(), before)
        sim.edit_after(0, "1", add_campaign_edges=["3"])
        first = sim.step()
        self.assertEqual(first.campaign_edges, (("1", "3"), ("1", "4")))
        checkpoint = sim.checkpoint()
        self.assertEqual(Simulation.from_checkpoint(checkpoint).step(), sim.step())
        checkpoint["frames"][1]["campaign_edges"] = []
        with self.assertRaisesRegex(ElectionError, "history does not match"):
            Simulation.from_checkpoint(checkpoint)

    def test_invalid_layers_and_actions_fail_without_mutation(self):
        for edges in ([["1", "1"]], [["1", "unknown"]], [["1", "2"], ["1", "2"]], "not-a-list"):
            data = example(); data["network"] = {"campaign_edges": edges}
            with self.subTest(edges=edges), self.assertRaises(ElectionError):
                make_scenario(data)
        sim = Simulation(make_scenario(example())); before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "absent campaign"):
            sim.edit_after(0, "1", remove_campaign_edges=["2"])
        with self.assertRaises(ElectionError):
            sim.edit_after(0, "1", add_campaign_edges=["2"], remove_campaign_edges=["2"])
        self.assertEqual(sim.checkpoint(), before)
        data = example()
        data["people"][0]["overrides"] = {"graph": "python:strategy_fixture:forbidden_campaign", "parameters": {"target": "2"}}
        sim = Simulation(make_scenario(data)); before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "unsupported action"):
            sim.step()
        self.assertEqual(sim.checkpoint(), before)

    def test_empty_layer_equivalence_and_version_eight_replay(self):
        base = example(); explicit = copy.deepcopy(base)
        explicit["network"] = {"campaign_edges": []}
        first = Simulation(make_scenario(base)); second = Simulation(make_scenario(explicit))
        self.assertEqual(first.run(2), second.run(2))
        old = first.checkpoint(); old["version"] = 8
        old["scenario"]["network"].pop("campaign_edges")
        for frame in old["frames"]:
            frame.pop("campaign_edges")
            frame.pop("report_provenance")
        self.assertEqual(Simulation.from_checkpoint(old).current, first.current)


if __name__ == "__main__":
    unittest.main()
