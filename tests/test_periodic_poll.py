"""Periodic completed-tally publication and exact linear weighting."""

from dataclasses import replace
import gzip
import json
import tempfile
from pathlib import Path
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.majority import MajorityConfig, MajorityState, advance, estimate, parse_config
from multi_agent_election.majority_experiments import run_pilot
from test_memory_pivotal import witness


class PeriodicPollTests(VerificationTestCase):
    def test_exact_schedule_and_missing_contacts(self):
        parties = ("A", "B", "C")
        config = MajorityConfig((2, 1, 1), poll_refresh_rounds=10)
        state = MajorityState.initial(parties)
        for tick in range(1, 22):
            tally = (1, 3, 0) if tick in (11, 21) else None
            state = advance(state, observer="v0", parties=parties, config=config,
                            round_number=tick, encounters=[("v1", "C", tick - 1)], published_counts=tally)
            record = state.as_dict(parties, config)
            self.assertEqual(record["poll_weight"], (10 - (tick - 1) % 10) / 10)
            self.assertEqual(record["poll_round"], ((tick - 1) // 10) * 10)
            self.assertEqual(record["poll_counts"], [2, 1, 1] if tick <= 10 else [1, 3, 0])
            if tick == 1:
                self.assertEqual(estimate(state, config), (.5, .25, .25))
            if tick == 11:
                self.assertEqual(estimate(state, config), (.25, .75, 0))
        isolated = MajorityState(2, (), (0, 0, 0))
        self.assertEqual(estimate(isolated, config), (.5, .25, .25))
        self.assertEqual(isolated.as_dict(parties, config)["poll_weight"], .9)
        self.assertEqual(isolated.as_dict(parties, config)["effective_poll_weight"], 1.0)

    def test_publication_uses_completed_tally_replay_and_rewind(self):
        raw = witness()
        raw["majority_estimation"]["poll_refresh_rounds"] = 10
        raw["interventions"] = [{"round": 10, "person": "0", "ballot": ["C"]}]
        sim = Simulation(make_scenario(raw))
        sim.run(12)
        self.assertEqual(sim.checkpoint()["version"], 25)
        for tick in (1, 2, 10, 11, 12):
            record = sim.frames[tick].as_dict()["majority_estimation"]["2"]
            trace = json.loads(dict(sim.frames[tick].policy_memory)["2"])
            self.assertEqual(trace["poll_weight"], record["poll_weight"])
            self.assertEqual(trace["effective_poll_weight"], record["effective_poll_weight"])
            self.assertEqual(trace["poll_counts"], record["poll_counts"])
            self.assertEqual(trace["poll_source_round"], record["poll_round"])
            self.assertEqual(record["poll_round"], 0 if tick <= 10 else 10)
        expected = [dict(sim.frames[10].counts)[c] for c in raw["parties"]]
        self.assertEqual(sim.frames[11].as_dict()["majority_estimation"]["2"]["poll_counts"], expected)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).frames, sim.frames)
        tampered = sim.checkpoint()
        tampered["frames"][11]["majority_estimation"]["2"]["poll_counts"][0] += 1
        with self.assertRaises(ElectionError): Simulation.from_checkpoint(tampered)
        legacy = sim.checkpoint(); legacy["version"] = 22
        with self.assertRaisesRegex(ElectionError, "version 23"): Simulation.from_checkpoint(legacy)
        old = sim.frames[9]
        sim.edit_after(9, "1", ballot=["C"])
        self.assertEqual(sim.current, old)
        tenth = sim.step(); eleventh = sim.step()
        self.assertEqual(eleventh.as_dict()["majority_estimation"]["2"]["poll_counts"],
                         [dict(tenth.counts)[c] for c in raw["parties"]])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, eleventh)

    def test_validation_and_no_silent_invented_tally(self):
        parties = ("A", "B", "C")
        for value in (0, -1, True, 1.5, "10"):
            with self.assertRaises(ElectionError):
                parse_config({"poll_counts": [2, 1, 1], "poll_refresh_rounds": value}, parties)
        config = MajorityConfig((2, 1, 1), poll_refresh_rounds=10)
        state = MajorityState(10, (), (0, 0, 0))
        with self.assertRaisesRegex(ElectionError, "completed tally"):
            advance(state, observer="0", parties=parties, config=config, round_number=11, encounters=[])
        with self.assertRaisesRegex(ElectionError, "outside"):
            advance(MajorityState.initial(parties), observer="0", parties=parties, config=config,
                    round_number=1, encounters=[], published_counts=(2, 1, 1))

    def test_periodic_estimator_pilot_preserves_control_meanings(self):
        raw = witness()
        raw["rounds"] = 11
        raw["groups"]["people"]["voting"] = "sincere"
        raw["majority_estimation"]["poll_refresh_rounds"] = 10
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "pilot"
            result = run_pilot(out, seeds=[101], sensitivity=True, scenario=make_scenario(raw))
            self.assertEqual(result["failed"], 0, result["runs"])
            with gzip.open(out / "provided-configured-101" / "predictions.jsonl.gz", "rt") as handle:
                rows = [json.loads(line) for line in handle]
            self.assertIn("weight_semantics", rows[0])
            poll = next(row for row in rows[1:] if row["arm"] == "poll_only" and row["round"] == 11)
            self.assertEqual(poll["shares"][0], [n / 4 for n in (2, 1, 1)])
            self.assertEqual(poll["sample_sizes"], [0, 0, 0, 0])
            contact = next(row for row in rows[1:] if row["arm"] == "window_only" and row["round"] == 1)
            self.assertEqual(contact["shares"][0], [1/3, 1/3, 1/3])


if __name__ == "__main__": unittest.main()
