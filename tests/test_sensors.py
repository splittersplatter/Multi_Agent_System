import copy
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class TrustedBallotSensorTests(VerificationTestCase):
    def test_sensor_is_opt_in_and_never_falls_back_to_reports(self):
        data = example()
        data["network"] = {"persistent_edges": [["1", "4"]]}
        data["people"][3]["overrides"] = {"voting": "sensed_plurality"}
        disabled = Simulation(make_scenario(data)).step()
        self.assertEqual(dict(disabled.ballots)["4"], ("B", "A"))
        self.assertEqual(disabled.ballot_sensors, ())
        data["people"][3]["overrides"]["capabilities"] = {"sense_public_ballots": True}
        sensed = Simulation(make_scenario(data)).step()
        self.assertEqual(dict(sensed.ballots)["4"], ("A", "B"))
        self.assertEqual(sensed.delivered, ())
        self.assertEqual(sensed.ballot_sensors, (("4", "1", "public", 0, ("A", "B")),))
        data["people"][3]["overrides"]["voting"] = "local_plurality"
        report_only = Simulation(make_scenario(data)).step()
        self.assertEqual(dict(report_only.ballots)["4"], ("B", "A"))
        self.assertEqual(report_only.delivered, ())

    def test_multiple_channels_do_not_count_one_sender_twice(self):
        data = example()
        data["network"] = {"persistent_edges": [["1", "4"], ["3", "4"]],
                           "private_channels": {"team": ["1", "4"]}}
        data["people"][3]["overrides"] = {"voting": "sensed_plurality", "capabilities":
            {"sense_public_ballots": True, "sense_private_ballots": True}}
        first = Simulation(make_scenario(data)).step()
        self.assertEqual(len(first.ballot_sensors), 3)
        # One A and one B sender: 4's own preference breaks the tie for B.
        self.assertEqual(dict(first.ballots)["4"], ("B", "A"))

    def test_sensors_observe_completed_ballots_not_private_ranking_or_future(self):
        data = example()
        data["network"] = {"persistent_edges": [["1", "4"]]}
        data["people"][3]["overrides"] = {"voting": "python:strategy_fixture:capture_sensors",
                                          "capabilities": {"sense_public_ballots": True}}
        data["interventions"] = [{"round": 1, "person": "1", "ballot": ["C", "A"]}]
        sim = Simulation(make_scenario(data))
        first, second = sim.step(), sim.step()
        self.assertEqual(first.as_dict()["policy_memory"]["4"]["reports"], [])
        self.assertEqual(first.as_dict()["policy_memory"]["4"]["sensed"], [["1", "public", 0, ["A", "B"]]])
        self.assertEqual(second.as_dict()["policy_memory"]["4"]["sensed"], [["1", "public", 1, ["C", "A"]]])
        self.assertEqual(dict(second.preferences)["1"], ("A", "B", "C"))

    def test_private_membership_and_public_direction_bound_sensor_access(self):
        data = example()
        data["network"] = {"persistent_edges": [["4", "1"]],
                           "private_channels": {"team": ["1", "4"], "other": ["2", "3"]}}
        data["people"][3]["overrides"] = {"capabilities": {"sense_public_ballots": True, "sense_private_ballots": True}}
        first = Simulation(make_scenario(data)).step()
        self.assertEqual(first.ballot_sensors, (("4", "1", "team", 0, ("A", "B")),))
        invalid = copy.deepcopy(data)
        invalid["people"][3]["overrides"]["capabilities"]["observe_private_channels"] = False
        with self.assertRaisesRegex(ElectionError, "requires private channel observation"):
            make_scenario(invalid)

    def test_phase_order_uses_old_graph_for_movement_and_new_graph_for_vote(self):
        data = example()
        data["people"][0]["overrides"] = {"graph": "python:strategy_fixture:graph", "parameters": {"target": "4"}}
        data["people"][3]["overrides"] = {"voting": "sensed_plurality", "movement": "python:strategy_fixture:capture_sensor_movement",
                                          "capabilities": {"sense_public_ballots": True}}
        first = Simulation(make_scenario(data)).step()
        phase = {(person, name): value for person, name, value in first.as_dict()["phase_memory"]}
        self.assertEqual(phase[("4", "movement")]["sensed"], [])
        self.assertEqual(first.ballot_sensors, (("4", "1", "public", 0, ("A", "B")),))
        self.assertEqual(dict(first.ballots)["4"], ("A", "B"))

    def test_movement_uses_prior_recorded_observation_not_retroactive_grant(self):
        data = example()
        data["network"] = {"persistent_edges": [["1", "4"]]}
        data["people"][3]["overrides"] = {"movement": "python:strategy_fixture:capture_sensor_movement"}
        data["interventions"] = [{"round": 1, "person": "1", "ballot": ["C", "A"]}]
        sim = Simulation(make_scenario(data))
        first = sim.step()
        self.assertEqual(first.ballot_sensors, ())
        sim.edit_after(1, "4", overrides={"movement": "python:strategy_fixture:capture_sensor_movement",
                                          "capabilities": {"sense_public_ballots": True}})
        second = sim.step()
        phase = {(person, name): value for person, name, value in second.as_dict()["phase_memory"]}
        self.assertEqual(phase[("4", "movement")]["sensed"], [])
        self.assertEqual(second.ballot_sensors, (("4", "1", "public", 1, ("C", "A")),))
        third = sim.step()
        phase = {(person, name): value for person, name, value in third.as_dict()["phase_memory"]}
        self.assertEqual(phase[("4", "movement")]["sensed"], [["1", "public", 1, ["C", "A"]]])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, third)

    def test_rewind_revocation_replay_and_tamper_detection(self):
        data = example()
        data["network"] = {"persistent_edges": [["1", "4"]]}
        data["people"][3]["overrides"] = {"voting": "sensed_plurality", "capabilities": {"sense_public_ballots": True}}
        sim = Simulation(make_scenario(data))
        sim.run(3)
        self.assertEqual(sim.checkpoint()["version"], 21)
        sim.edit_after(1, "4", overrides={"voting": "sensed_plurality", "capabilities": {"sense_public_ballots": False}})
        frame = sim.step()
        self.assertEqual(frame.ballot_sensors, ())
        self.assertEqual(dict(frame.ballots)["4"], ("B", "A"))
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(restored.step(), sim.step())
        tampered = sim.checkpoint()
        tampered["frames"][1]["ballot_sensors"][0][4][0] = "C"
        with self.assertRaisesRegex(ElectionError, "history does not match"):
            Simulation.from_checkpoint(tampered)

    def test_previous_version_checkpoint_replays_without_sensor_fields(self):
        sim = Simulation(make_scenario(example()))
        sim.run(2)
        old = sim.checkpoint()
        old["version"] = 7
        for group in old["scenario"]["groups"].values():
            group["capabilities"].pop("sense_public_ballots")
            group["capabilities"].pop("sense_private_ballots")
        for frame in old["frames"]:
            frame.pop("ballot_sensors")
            frame.pop("campaign_edges")
            frame.pop("report_provenance")
        restored = Simulation.from_checkpoint(old)
        self.assertEqual(restored.current, sim.current)
        self.assertEqual(restored.checkpoint()["version"], 21)


if __name__ == "__main__":
    unittest.main()
