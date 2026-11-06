import copy
import unittest
from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class InterventionTests(unittest.TestCase):
    def test_scheduled_edit_changes_only_target_round_and_replays(self):
        data = example()
        data["interventions"] = [{"round": 2, "person": "2", "preference": ["C", "A", "B"], "position": [0.1, 0.2]}]
        sim = Simulation(make_scenario(data))
        frame1 = sim.step(); frame2 = sim.step()
        self.assertEqual(frame1.winner, "A")
        self.assertEqual(frame2.winner, "B")
        self.assertEqual(dict(frame2.positions)["2"], (0.1, 0.2))
        self.assertEqual(len(frame2.interventions), 1)
        expected = sim.run(2)
        self.assertEqual(expected, tuple(Simulation.from_checkpoint(sim.checkpoint()).frames))

    def test_zero_change_matches_baseline_state(self):
        control = example(); treated = copy.deepcopy(control)
        treated["interventions"] = [{"round": 1, "person": "1", "preference": ["A", "B", "C"]}]
        a, b = Simulation(make_scenario(control)).step(), Simulation(make_scenario(treated)).step()
        self.assertEqual(a.ballots, b.ballots)
        self.assertEqual(a.counts, b.counts)
        self.assertEqual(a.winner, b.winner)
        self.assertEqual(a.positions, b.positions)

    def test_invalid_actions_rejected_before_execution(self):
        invalid = [[{"round": 0, "person": "1", "group": "residents"}],
                   [{"round": 1, "person": "absent", "group": "residents"}],
                   [{"round": 1, "person": "1", "preference": ["A", "A", "C"]}],
                   [{"round": 1, "person": "1", "group": "residents"}, {"round": 1, "person": "1", "position": [0, 0]}]]
        for actions in invalid:
            data = example(); data["interventions"] = actions
            with self.subTest(actions=actions), self.assertRaises(ElectionError): make_scenario(data)

    def test_ballot_override_is_one_round_and_preference_unchanged(self):
        sim = Simulation(make_scenario(example()))
        sim.edit_after(0, "2", ballot=["C", "A"])
        edited = sim.step()
        self.assertEqual(edited.winner, "B")
        self.assertEqual(dict(edited.preferences)["2"], ("A", "C", "B"))
        self.assertEqual(dict(edited.ballots)["2"], ("C", "A"))
        self.assertEqual(dict(sim.step().ballots)["2"], ("A", "C"))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_edit_edges_and_channels_is_atomic_and_replayable(self):
        data = example(); data["network"] = {"persistent_edges": [["1", "2"]], "private_channels": {"team": ["1"]}}
        sim = Simulation(make_scenario(data)); sim.run(2)
        before = sim.checkpoint()
        with self.assertRaises(ElectionError): sim.edit_after(0, "1", remove_edges=["3"])
        self.assertEqual(sim.checkpoint(), before)
        sim.edit_after(0, "1", remove_edges=["2"], add_edges=["3"], remove_channels=["team"])
        frame = sim.step()
        self.assertEqual(frame.persistent_edges, (("1", "3"),))
        self.assertEqual(dict(frame.private_channels)["team"], ())
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, frame)


if __name__ == "__main__": unittest.main()
