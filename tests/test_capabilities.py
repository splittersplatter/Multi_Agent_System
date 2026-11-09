import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class CapabilityTests(VerificationTestCase):
    def test_legacy_scenarios_and_checkpoints_keep_original_permissions(self):
        scenario = make_scenario(example())
        implicit = Simulation(scenario)
        normalized = scenario.as_dict()
        explicit = Simulation(make_scenario(normalized))
        self.assertEqual(implicit.run(2), explicit.run(2))
        legacy = implicit.checkpoint()
        for group in legacy["scenario"]["groups"].values():
            del group["capabilities"]
        self.assertEqual(Simulation.from_checkpoint(legacy).current, implicit.current)

    def test_capability_values_are_strict_and_unknown_names_fail(self):
        for capability in ({"move": 0}, {"move": "false"}, {"bogus": True}, [], None):
            data = example()
            data["groups"]["residents"]["capabilities"] = capability
            with self.subTest(capability=capability), self.assertRaisesRegex(ElectionError, "capabilities"):
                make_scenario(data)

    def test_scoped_observation_and_receive_permissions_do_not_leak(self):
        data = example()
        data["groups"]["residents"].update(communication="truthful", capabilities={"receive_private_reports": False})
        data["network"] = {"persistent_edges": [["1", "2"], ["2", "1"]],
                           "private_channels": {"team": ["1", "2"]}}
        data["people"][0]["overrides"] = {
            "voting": "python:strategy_fixture:capture_scope", "communication": "none",
            "capabilities": {"observe_public_neighbors": False, "observe_private_channels": False}}
        sim = Simulation(make_scenario(data))
        sim.run(2)
        memory = sim.current.as_dict()["policy_memory"]["1"]
        self.assertEqual(memory["neighbors"], [])
        self.assertEqual(memory["channels"], [])
        self.assertEqual([message[:2] for message in memory["messages"]], [["2", "public"]])
        self.assertFalse(any(channel == "team" for _, recipient, channel, _ in sim.current.delivered if recipient == "1"))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_send_permissions_and_partial_agent_overrides_inherit_group_restrictions(self):
        data = example()
        data["groups"]["residents"].update(communication="truthful", capabilities={"send_private_reports": False})
        data["network"] = {"persistent_edges": [["1", "2"], ["2", "1"]],
                           "private_channels": {"team": ["1", "2"]}}
        data["people"][0]["overrides"] = {"capabilities": {"send_public_reports": False}}
        first = Simulation(make_scenario(data)).step()
        self.assertFalse(any(sender == "1" for sender, _, _, _ in first.pending))
        self.assertFalse(any(channel == "team" for _, _, channel, _ in first.pending))
        self.assertIn(("2", "1", "public", ("A", "C")), first.pending)

    def test_denied_policy_actions_abort_without_committing(self):
        cases = (
            ({"movement": "python:strategy_fixture:move", "max_step": 0.1,
              "capabilities": {"move": False}}, {}, "movement"),
            ({"movement": "random_walk", "max_step": 0.1, "capabilities": {"move": False}}, {}, "movement"),
            ({"graph": "python:strategy_fixture:graph", "parameters": {"target": "2"},
              "capabilities": {"modify_persistent_edges": False}}, {}, "graph"),
            ({"graph": "python:strategy_fixture:join_channel", "parameters": {"channel": "team"},
              "capabilities": {"modify_private_channels": False}}, {"private_channels": {"team": ["2"]}}, "graph"),
            ({"communication": "python:strategy_fixture:communicate", "capabilities": {"send_public_reports": False}},
             {"persistent_edges": [["1", "2"]]}, "communication"),
        )
        for overrides, network, phase in cases:
            data = example()
            data["people"][0]["overrides"] = overrides
            data["network"] = network
            sim = Simulation(make_scenario(data))
            before = sim.checkpoint()
            with self.subTest(phase=phase, overrides=overrides), self.assertRaisesRegex(ElectionError, phase):
                sim.step()
            self.assertEqual(sim.checkpoint(), before)

    def test_researcher_edit_can_grant_one_permission_without_clearing_other_restrictions(self):
        data = example()
        data["groups"]["residents"]["capabilities"] = {"modify_persistent_edges": False, "receive_private_reports": False}
        data["people"][0]["overrides"] = {"graph": "python:strategy_fixture:graph", "parameters": {"target": "2"}}
        sim = Simulation(make_scenario(data))
        with self.assertRaisesRegex(ElectionError, "capability denied"):
            sim.step()
        sim.edit_after(0, "1", overrides={"graph": "python:strategy_fixture:graph", "parameters": {"target": "2"},
                                           "capabilities": {"modify_persistent_edges": True}})
        self.assertIn(("1", "2"), sim.step().persistent_edges)
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), restored.step())
        self.assertFalse(sim.scenario.groups[0].capabilities.receive_private_reports)

    def test_revocation_filters_queued_reports_before_delivery(self):
        data = example()
        data["groups"]["residents"]["communication"] = "truthful"
        data["network"] = {"persistent_edges": [["1", "2"]]}
        sim = Simulation(make_scenario(data))
        first = sim.step()
        self.assertTrue(first.pending)
        sim.edit_after(1, "2", overrides={"capabilities": {"receive_public_reports": False}})
        second = sim.step()
        self.assertFalse(any(recipient == "2" for _, recipient, _, _ in second.delivered))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, second)

    def test_revocation_also_filters_previous_inbox_from_movement_observations(self):
        data = example()
        data["groups"]["residents"]["communication"] = "truthful"
        data["network"] = {"persistent_edges": [["2", "1"]]}
        data["people"][0]["overrides"] = {"movement": "python:strategy_fixture:capture_movement"}
        sim = Simulation(make_scenario(data))
        sim.run(2)
        self.assertTrue(any(recipient == "1" for _, recipient, _, _ in sim.current.delivered))
        sim.edit_after(2, "1", overrides={"movement": "python:strategy_fixture:capture_movement",
                                          "capabilities": {"receive_public_reports": False}})
        third = sim.step()
        phase = {(person, name): value for person, name, value in third.as_dict()["phase_memory"]}
        self.assertEqual(phase[("1", "movement")]["messages"], [])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, third)


if __name__ == "__main__":
    unittest.main()
