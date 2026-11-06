import copy
import math
import unittest

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.network import proximity_edges
from test_baseline import example


class NetworkTests(unittest.TestCase):
    def test_edges_against_independent_brute_force(self):
        positions = {"a": (0.0, 0.0), "b": (0.3, 0.4), "c": (0.3, 0.4), "d": (1.0, 1.0)}
        for radius in (0, 0.5, 1.0, math.sqrt(2)):
            expected = tuple(sorted((a, b) for a in positions for b in positions if a != b and math.dist(positions[a], positions[b]) <= radius))
            self.assertEqual(proximity_edges(positions, radius), expected)
        self.assertEqual(proximity_edges(positions, None), ())

    def test_moving_agents_replay_and_persistent_edges_survive(self):
        data = example()
        data["network"] = {"radius": 0.1, "persistent_edges": [["1", "2"]]}
        data["people"][0]["position"] = [0.0, 0.0]
        data["people"][1]["position"] = [1.0, 1.0]
        data["groups"]["residents"].update(movement="random_walk", max_step=0.5)
        scenario = make_scenario(data)
        a, b = Simulation(scenario).run(6), Simulation(scenario).run(6)
        self.assertEqual(a, b)
        self.assertNotEqual(a[0].positions, a[1].positions)
        for frame in a:
            self.assertEqual(frame.persistent_edges, (("1", "2"),))
            self.assertTrue(all(0 <= coord <= 1 for _, pos in frame.positions for coord in pos))

    def test_reject_invalid_network_and_coordinates(self):
        mutations = [lambda x: x.update(network={"radius": float("nan")}),
                     lambda x: x.update(network={"radius": -1}),
                     lambda x: x.update(network={"persistent_edges": [["1", "1"]]}),
                     lambda x: x.update(network={"persistent_edges": [["1", "no"]]}),
                     lambda x: x["people"][0].update(position=[1.1, 0]),
                     lambda x: x["groups"]["residents"].update(movement="fly")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(example()); mutation(data)
                with self.assertRaises(ElectionError): make_scenario(data)

    def test_random_walk_checkpoint_continuation(self):
        data = example()
        data["groups"]["residents"].update(movement="random_walk", max_step=0.4)
        data["network"] = {"radius": 0.2}
        original = Simulation(make_scenario(data))
        original.run(3)
        resumed = Simulation.from_checkpoint(original.checkpoint())
        self.assertEqual(original.run(4), resumed.run(4))


if __name__ == "__main__": unittest.main()
