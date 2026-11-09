"""Adversarial engine and independent-oracle checks for exploratory memory voting."""

import copy
from itertools import permutations
import json
import math
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.majority import MajorityConfig, MajorityState
from multi_agent_election.voting import configure_voting, memory_pivotal
from test_memory_voting_proof import fraction_oracle


def witness():
    return {"parties": ["A", "B", "C"], "k": 1, "rounds": 8, "seed": 101,
            "majority_estimation": {"poll_counts": [2, 1, 1], "memory_rounds": 10, "poll_weight": .5},
            "network": {"radius": math.sqrt(2)},
            "groups": {"people": {"voting": "memory_pivotal", "movement": "random_walk", "max_step": .025}},
            "people": [{"id": str(i), "group": "people", "preference": pref, "position": [.2*i, .5]}
                       for i, pref in enumerate((["A", "B", "C"], ["A", "B", "C"],
                                                  ["B", "C", "A"], ["C", "B", "A"]))]}


class MemoryPivotalTests(VerificationTestCase):
    def test_exhaustive_decisions_against_independent_fraction_oracle(self):
        parties = ("A", "B", "C")
        entries = (("v1", "A", 1, 0), ("v2", "A", 1, 0), ("v3", "C", 1, 0))
        for weight in (0, .25, .5, 1):
            for poll in ((2, 1, 1), (0, 0, 4), (1, 2, 1)):
                config = MajorityConfig(poll, 10, weight)
                for present in ((), entries):
                    state = MajorityState(1, present, (2, 0, 1) if present else (0, 0, 0))
                    for preference in permutations(parties):
                        for current in parties:
                            expected, baseline, predicted = fraction_oracle(parties, preference, current, 4, present, config)
                            choice, trace = memory_pivotal(parties, preference, current, 4, state, config)
                            self.assertEqual((choice, trace["baseline_winner"], tuple(trace["predicted_winners"].items())),
                                             (expected, baseline, predicted))
                            self.assertEqual(trace["strict_improvement"], choice != current)

    def test_real_engine_known_cycle_cache_timing_and_replay(self):
        sim = Simulation(make_scenario(witness()))
        self.assertEqual(tuple(b[0] for _, b in sim.current.ballots), ("A", "A", "B", "C"))
        for tick in range(1, 7):
            frame = sim.step()
            self.assertEqual(tuple(b[0] for _, b in frame.ballots),
                             ("A", "A", "C", "B") if tick % 2 else ("A", "A", "B", "C"))
            self.assertTrue(all(len(state.entries) == 3 and state.round == tick for _, state in frame.majority_states))
            trace = json.loads(dict(frame.policy_memory)["2"])
            self.assertEqual(trace["ballot_source_round"], tick - 1)
            self.assertTrue(trace["strict_improvement"])
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(restored.run(3), sim.run(3))

    def test_other_private_rankings_do_not_enter_decision(self):
        first = witness()
        second = copy.deepcopy(first)
        second["people"][0]["preference"] = ["A", "C", "B"]
        a, b = Simulation(make_scenario(first)).step(), Simulation(make_scenario(second)).step()
        self.assertEqual(dict(a.majority_states)["2"], dict(b.majority_states)["2"])
        self.assertEqual(dict(a.policy_memory)["2"], dict(b.policy_memory)["2"])
        self.assertEqual(dict(a.ballots)["2"], dict(b.ballots)["2"])

    def test_invalid_configuration_and_midrun_override_are_atomic(self):
        data = witness()
        for update in ({"k": 2}, {"majority_estimation": {"enabled": False}},
                       {"majority_estimation": {"poll_counts": [0, 0, 0]}}):
            changed = copy.deepcopy(data); changed.update(update)
            with self.assertRaises(ElectionError): make_scenario(changed)
        with self.assertRaises(ElectionError):
            configure_voting(make_scenario(data), "memory_pivotal", {"samples": 3})
        for invalid in ([], None, False, 0, {"samples": 3}):
            changed = copy.deepcopy(data)
            changed["groups"]["people"]["parameters"] = {"voting": invalid}
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError):
                make_scenario(changed)
        changed = copy.deepcopy(data); changed["groups"]["people"]["voting"] = "sincere"
        changed.pop("majority_estimation")
        sim = Simulation(make_scenario(changed))
        sim.edit_after(0, "0", overrides={"voting": "memory_pivotal"})
        before = sim.current
        with self.assertRaisesRegex(ElectionError, "majority_estimation"):
            sim.step()
        self.assertEqual(sim.current, before)

    def test_rewind_edit_preserves_previous_cache_and_invalidates_future(self):
        sim = Simulation(make_scenario(witness()))
        sim.run(3)
        prior = sim.frames[1]
        sim.edit_after(1, "0", position=[.9, .9])
        self.assertEqual(sim.current, prior)
        self.assertEqual(len(sim.frames), 2)
        changed = sim.step()
        self.assertEqual(dict(changed.positions)["0"] != dict(prior.positions)["0"], True)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, changed)


if __name__ == "__main__": unittest.main()
