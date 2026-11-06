import copy
import unittest

from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class MessageTests(unittest.TestCase):
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


if __name__ == "__main__": unittest.main()
