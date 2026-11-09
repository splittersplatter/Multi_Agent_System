import json
import math
import unittest

from verification_support import VerificationTestCase

from multi_agent_election.engine import Simulation
from multi_agent_election.marl import MovementEnv
from multi_agent_election.model import ElectionError, make_scenario


def scenario(**changes):
    raw = {
        "parties": ["A", "B"], "k": 1, "seed": 4, "rounds": 5,
        "groups": {
            "agents": {"voting": "sincere", "movement": "external", "max_step": 0.1, "proximity_radius": 0.3},
            "sensing": {"voting": "sincere", "movement": "external", "max_step": 0.1, "proximity_radius": 0.3,
                        "capabilities": {"sense_public_ballots": True}},
            "walkers": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.05,
                        "capabilities": {"sense_public_ballots": True}},
            "frozen": {"voting": "sincere", "movement": "external", "max_step": 0.1, "capabilities": {"move": False}},
        },
        "network": {"radius": 0.3},
        "people": [
            {"id": "a1", "group": "agents", "preference": ["B", "A"], "position": [0.5, 0.5]},
            {"id": "a2", "group": "sensing", "preference": ["B", "A"], "position": [0.9, 0.9]},
            {"id": "w1", "group": "walkers", "preference": ["A", "B"], "position": [0.55, 0.5]},
            {"id": "w2", "group": "walkers", "preference": ["A", "B"], "position": [0.1, 0.1]},
            {"id": "f1", "group": "frozen", "preference": ["A", "B"], "position": [0.2, 0.8]},
        ],
    }
    raw.update(changes)
    return make_scenario(raw)


class ExternalMovementTests(VerificationTestCase):
    def test_valid_move_commits_and_others_stay(self):
        sim = Simulation(scenario())
        frame = sim.step(external_moves={"a1": (0.58, 0.56)})
        positions = dict(frame.positions)
        self.assertEqual(positions["a1"], (0.58, 0.56))
        self.assertEqual(positions["a2"], (0.9, 0.9))  # no action: stays put
        self.assertEqual(positions["f1"], (0.2, 0.8))
        self.assertNotEqual(positions["w2"], (0.1, 0.1))  # built-in movers still move

    def test_no_moves_is_identical_to_plain_step(self):
        a, b = Simulation(scenario()), Simulation(scenario())
        self.assertEqual(a.step(), b.step(external_moves={}))

    def test_invalid_moves_fail_atomically(self):
        cases = [
            ({"a1": (0.7, 0.5)}, "max_step"),               # 0.2 > 0.1
            ({"w1": (0.55, 0.52)}, "external"),             # not an external mover
            ({"f1": (0.21, 0.8)}, "capability"),            # move permission denied
            ({"ghost": (0.5, 0.5)}, "unknown"),
            ({"a1": (0.5, float("nan"))}, "finite"),
            ({"a1": (0.5, 1.05)}, "finite"),
            ({"a1": (True, 0.5)}, "finite"),
            ({"a1": (0.5,)}, "finite"),
        ]
        for moves, message in cases:
            with self.subTest(moves=moves):
                sim = Simulation(scenario())
                sim.step(external_moves={"a1": (0.52, 0.5)})
                frames, queued = list(sim.frames), sim.manual_interventions
                with self.assertRaisesRegex(ElectionError, message):
                    sim.step(external_moves=moves)
                self.assertEqual(sim.frames, frames)
                self.assertEqual(sim.manual_interventions, queued)
                sim.step()  # still usable afterwards

    def test_conflicting_queued_position_edit_rejected(self):
        sim = Simulation(scenario())
        sim.edit_after(0, "a1", position=[0.45, 0.5])
        with self.assertRaisesRegex(ElectionError, "already queued"):
            sim.step(external_moves={"a1": (0.52, 0.5)})

    def test_checkpoint_replays_external_history(self):
        sim = Simulation(scenario())
        path = [(0.55, 0.5), (0.6, 0.55), (0.6, 0.55), (0.65, 0.6)]
        for target in path:
            sim.step(external_moves={"a1": target, "a2": (0.85, 0.85)})
        payload = json.loads(json.dumps(sim.checkpoint()))
        restored = Simulation.from_checkpoint(payload)
        self.assertEqual(restored.frames, sim.frames)
        self.assertEqual(dict(restored.current.positions)["a1"], (0.65, 0.6))
        tampered = json.loads(json.dumps(payload))
        tampered["manual_interventions"][0]["position"] = [0.54, 0.5]
        with self.assertRaises(ElectionError):
            Simulation.from_checkpoint(tampered)


class MovementEnvTests(VerificationTestCase):
    def test_api_shapes_and_truncation(self):
        env = MovementEnv(scenario(), reward_party="B", max_rounds=3)
        self.assertEqual(env.possible_agents, ["a1", "a2", "f1"])
        obs, infos = env.reset(seed=9)
        self.assertEqual(set(obs), {"a1", "a2", "f1"})
        steps = 0
        while env.agents:
            obs, rewards, terms, truncs, infos = env.step({"a1": (0.01, 0.0)})
            steps += 1
            self.assertEqual(set(rewards), {"a1", "a2", "f1"})
            self.assertEqual(set(terms), set(rewards))
            self.assertEqual(set(truncs), set(rewards))
        self.assertEqual(steps, 3)
        self.assertTrue(all(truncs.values()))
        with self.assertRaises(ElectionError):
            env.step({})

    def test_actions_are_scaled_and_clipped(self):
        env = MovementEnv(scenario(), reward_party="B")
        env.reset()
        env.step({"a1": (5.0, 0.0), "a2": (0.0, 1.0)})
        positions = dict(env.simulation.current.positions)
        self.assertAlmostEqual(positions["a1"][0], 0.6, places=6)       # scaled to max_step
        self.assertLessEqual(math.dist(positions["a2"], (0.9, 0.9)), 0.1)
        self.assertLessEqual(positions["a2"][1], 1.0)                     # clipped to the square

    def test_same_seed_same_actions_same_history(self):
        def play(seed):
            env = MovementEnv(scenario(), reward_party="A")
            env.reset(seed=seed)
            while env.agents:
                env.step({"a1": (0.03, -0.02), "a2": (-0.05, -0.05)})
            return env.simulation.frames
        self.assertEqual(play(7), play(7))
        self.assertNotEqual(play(7), play(8))  # random walkers depend on the seed

    def test_observation_boundary_respects_sensing_permission(self):
        env = MovementEnv(scenario(), reward_party="B", observation_radius=1.5, max_neighbours=4)
        env.reset()
        hidden, seen = env.observe("a1"), env.observe("a2")
        self.assertEqual(len(hidden.neighbours), 4)
        self.assertEqual(len(seen.neighbours), 4)
        self.assertTrue(all(party == -1 for *_, party in hidden.neighbours))   # a1 lacks ballot sensing
        ballots = dict(env.simulation.current.ballots)
        positions = dict(env.simulation.current.positions)
        nearest = sorted((math.dist(positions["a2"], positions[p]), p) for p in positions if p != "a2")[:4]
        expected = [env.parties.index(ballots[p][0]) for _, p in nearest]
        self.assertEqual([party for *_, party in seen.neighbours], expected)  # nearest first, true last ballots
        self.assertEqual(len(env.observation_vector("a1")), 2 + 2 + 2 + 4 * (3 + 2))

    def test_reward_is_change_in_party_share(self):
        env = MovementEnv(scenario(), reward_party="B")
        env.reset()
        before = dict(env.simulation.current.counts)
        _, rewards, *_ = env.step({})
        after = dict(env.simulation.current.counts)
        expected = after["B"] / sum(after.values()) - before["B"] / sum(before.values())
        self.assertTrue(all(abs(r - expected) < 1e-12 for r in rewards.values()))

    def test_requires_external_agents_and_valid_party(self):
        raw_without = scenario().as_dict()
        for g in raw_without["groups"].values():
            if g["movement"] == "external":
                g["movement"] = "stationary"
        with self.assertRaises(ElectionError):
            MovementEnv(make_scenario(raw_without), reward_party="A")
        with self.assertRaises(ElectionError):
            MovementEnv(scenario(), reward_party="Z")


if __name__ == "__main__":
    unittest.main()
