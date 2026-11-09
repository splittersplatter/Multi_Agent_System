import contextlib
import copy
import csv
from dataclasses import replace
import gzip
import io
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import threading
import unittest
from verification_support import VerificationTestCase
from unittest.mock import patch
from urllib.request import Request, urlopen

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.exports import write_metrics_csv
from multi_agent_election.majority import MajorityConfig, MajorityState, advance, advance_population, estimate, leader_indices
from multi_agent_election.majority_experiments import pilot_scenario, run_pilot
from multi_agent_election.metrics import series
from multi_agent_election.visual import Session, make_server
from test_baseline import example


PARTIES = ("A", "B", "C")


def configured(**options):
    data = example()
    data["majority_estimation"] = {"poll_counts": [4, 3, 3], **options}
    return data


class MajorityCacheTests(VerificationTestCase):
    def update(self, state, tick, records=(), window=3, weight=0.5):
        return advance(state, observer="self", parties=PARTIES,
                       config=MajorityConfig((4, 3, 3), window, weight), round_number=tick, encounters=records)

    def test_hand_calculated_blend_and_unique_people(self):
        initial = MajorityState.initial(PARTIES)
        state = self.update(initial, 1, [("x", "A", 0), ("x", "A", 0), ("y", "B", 0)])
        self.assertEqual(state.counts, (1, 1, 0))
        self.assertEqual(len(state.entries), 2)
        self.assertEqual(estimate(state, MajorityConfig((4, 3, 3))), (0.45, 0.4, 0.15))
        self.assertEqual(initial.entries, ())

    def test_expiration_uses_encounter_not_ballot_source_round(self):
        state = self.update(MajorityState.initial(PARTIES), 1, [("x", "A", 0)])
        self.assertEqual(len(self.update(state, 3).entries), 1)
        self.assertEqual(self.update(state, 4).entries, ())

    def test_refresh_survives_old_expiry_and_changes_counts(self):
        state = self.update(MajorityState.initial(PARTIES), 1, [("x", "A", 0), ("y", "C", 0)])
        state = self.update(state, 3, [("x", "B", 2)])
        state = self.update(state, 4)
        self.assertEqual(state.entries, (("x", "B", 3, 2),))
        self.assertEqual(state.counts, (0, 1, 0))
        state = self.update(state, 5, [("x", "B", 4)])
        self.assertEqual(self.update(state, 7).counts, (0, 1, 0))
        self.assertEqual(self.update(state, 8).counts, (0, 0, 0))

    def test_window_one_and_return_after_forgetting(self):
        state = self.update(MajorityState.initial(PARTIES), 1, [("x", "A", 0)], window=1)
        state = self.update(state, 2, window=1)
        self.assertEqual(state.entries, ())
        state = self.update(state, 3, [("x", "C", 2)], window=1)
        self.assertEqual(state.entries, (("x", "C", 3, 2),))

    def test_reads_do_not_refresh_and_stale_records_do_not_revive(self):
        state = self.update(MajorityState.initial(PARTIES), 1, [("x", "A", 0)])
        original = state
        for _ in range(4):
            estimate(state, MajorityConfig((4, 3, 3)))
            state.as_dict(PARTIES, MajorityConfig((4, 3, 3)))
        self.assertEqual(state, original)
        self.assertEqual(self.update(state, 4, [("x", "A", 0)]).entries, ())

    def test_conflicting_duplicates_fail_without_mutation(self):
        state = self.update(MajorityState.initial(PARTIES), 1, [("x", "A", 0)])
        for records in ([("x", "A", 1), ("x", "B", 1)], [("x", "B", 0)]):
            with self.assertRaisesRegex(ElectionError, "conflicting"):
                self.update(state, 2, records)
        self.assertEqual(state.counts, (1, 0, 0))

    def test_source_validation_self_exclusion_and_monotonic_rounds(self):
        state = MajorityState.initial(PARTIES)
        self.assertEqual(self.update(state, 1, [("self", "C", 0)]).entries, ())
        for records in ([("x", "Z", 0)], [("x", "A", -1)], [("x", "A", 1)], [("x", "A", True)],
                        [("x", ["A"], 0)], [("x", "A")], [None], [(" ", "A", 0)]):
            with self.assertRaises(ElectionError):
                self.update(state, 1, records)
        with self.assertRaises(ElectionError):
            self.update(state, 0)

    def test_population_reads_only_observed_senders(self):
        class ScopedBallots(dict):
            def __getitem__(self, person):
                if person != "seen":
                    raise AssertionError("unobserved ballot accessed")
                return ("C",)
        previous = (("self", MajorityState.initial(PARTIES)),)
        states = advance_population(previous, PARTIES, MajorityConfig((4, 3, 3)), 1,
                                    (("seen", "self"),), ScopedBallots())
        self.assertEqual(states[0][1].entries, (("seen", "C", 1, 0),))

    def test_empty_fallback_endpoints_and_exact_ties(self):
        empty = MajorityState.initial(PARTIES)
        state = self.update(empty, 1, [("x", "B", 0)])
        self.assertEqual(estimate(empty, MajorityConfig((1, 1, 0), poll_weight=0)), (0.5, 0.5, 0))
        self.assertEqual(leader_indices(empty, MajorityConfig((1, 1, 0))), (0, 1))
        self.assertEqual(estimate(state, MajorityConfig((4, 3, 3), poll_weight=0)), (0, 1, 0))
        self.assertEqual(estimate(state, MajorityConfig((4, 3, 3), poll_weight=1)), (0.4, 0.3, 0.3))
        self.assertEqual(leader_indices(state, MajorityConfig((1, 0, 0), poll_weight=0.5)), (0, 1))

    def test_randomized_trace_against_independent_reconstruction(self):
        rng = random.Random(137)
        for window in (1, 2, 10, 10000):
            state = MajorityState.initial(PARTIES)
            oracle = {}
            for tick in range(1, 101):
                observations = [(str(p), rng.choice(PARTIES), tick - 1) for p in rng.sample(range(15), rng.randrange(16))]
                shuffled = observations[:]; rng.shuffle(shuffled)
                first = self.update(state, tick, observations, window=window)
                self.assertEqual(first, self.update(state, tick, shuffled, window=window))
                oracle = {p: record for p, record in oracle.items() if record[1] >= tick - window + 1}
                for p, c, source in observations:
                    oracle[p] = (c, tick, source)
                expected = tuple((p, *record) for p, record in sorted(oracle.items(), key=lambda row: (row[1][1], row[0])))
                self.assertEqual(first.entries, expected)
                self.assertEqual(first.counts, tuple(sum(record[0] == c for record in oracle.values()) for c in PARTIES))
                self.assertAlmostEqual(sum(estimate(first, MajorityConfig((4, 3, 3)))), 1)
                state = first


class MajorityIntegrationTests(VerificationTestCase):
    def test_mid_estimator_failure_is_atomic(self):
        simulation = Simulation(make_scenario(configured()))
        original = simulation.checkpoint()
        calls = 0
        def broken(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ElectionError("injected second-agent failure")
            return advance(*args, **kwargs)
        with patch("multi_agent_election.majority.advance", side_effect=broken):
            with self.assertRaisesRegex(ElectionError, "second-agent"):
                simulation.step()
        self.assertEqual(simulation.checkpoint(), original)
        self.assertEqual(simulation.step().round, 1)

    def test_real_http_state_step_checkpoint_and_csv_match_engine(self):
        simulation = Simulation(make_scenario(configured()))
        expected = Simulation(simulation.scenario)
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/") as response:
                token = response.read().decode().split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            for tick in range(2):
                payload = json.dumps({"action": "step", "revision": tick}).encode()
                with urlopen(Request(base + "/command", data=payload, headers=headers)) as response:
                    self.assertEqual(json.load(response)["frame"], expected.step().as_dict())
            with urlopen(Request(base + "/checkpoint?revision=2", headers=headers)) as response:
                self.assertEqual(Simulation.from_checkpoint(json.load(response)).frames, expected.frames)
            with urlopen(Request(base + "/export?format=csv&revision=2", headers=headers)) as response:
                rows = list(csv.DictReader(io.StringIO(response.read().decode())))
                self.assertIn("majority_mean_sample_size", rows[-1])
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_configuration_fail_closed(self):
        for changes in ({"memory_rounds": 0}, {"memory_rounds": True}, {"memory_rounds": 1.5},
                        {"poll_weight": float("nan")}, {"poll_weight": float("inf")}, {"poll_weight": True},
                        {"poll_weight": -0.1}, {"poll_weight": 1.1}, {"poll_weight": 10**500}, {"poll_counts": [0, 0, 0]},
                        {"poll_counts": [1, -1, 3]}, {"poll_counts": [1, 2]}, {"poll_counts": [True, 1, 2]},
                        {"poll_counts": [1.0, 2, 3]}, {"poll_round": 1}, {"poll_round": False}, {"enabled": 1}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(ElectionError):
                make_scenario(configured(**changes))
        data = example(); data["majority_estimation"] = {}
        with self.assertRaisesRegex(ElectionError, "explicit"):
            make_scenario(data)
        data["majority_estimation"] = {"enabled": False}
        self.assertIsNone(make_scenario(data).majority_estimation)

    def test_dataclass_bypass_rejected(self):
        scenario = make_scenario(configured())
        with self.assertRaises(ElectionError):
            Simulation(replace(scenario, majority_estimation=replace(scenario.majority_estimation, memory_rounds=0)))

    def test_poll_only_initial_state_and_disabled_equivalence(self):
        baseline = Simulation(make_scenario(example()))
        enabled = Simulation(make_scenario(configured()))
        self.assertEqual(enabled.current.as_dict()["majority_estimation"]["1"]["sample_size"], 0)
        baseline.run(4); enabled.run(4)
        for first, second in zip(baseline.frames, enabled.frames):
            saved = second.as_dict(); saved.pop("majority_estimation")
            self.assertEqual(saved, first.as_dict())

    def test_incoming_asymmetric_proximity_and_no_remote_channels(self):
        data = configured()
        data["network"] = {"radius": 0, "persistent_edges": [["2", "4"]],
                           "campaign_edges": [["3", "4"]], "private_channels": {"team": ["2", "4"]}}
        for p, position in zip(data["people"], ([0, 0], [0.8, 0.8], [1, 1], [0.1, 0])):
            p["position"] = position
        data["people"][3]["overrides"] = {"proximity_radius": 0.2}
        frame = Simulation(make_scenario(data)).step()
        states = dict(frame.majority_states)
        self.assertEqual(states["4"].entries, (("1", "A", 1, 0),))
        self.assertEqual(states["1"].entries, ())
        self.assertEqual(frame.ballot_sensors, ())  # No global permission override.

    def test_coincident_nodes_and_no_self(self):
        data = configured(); data["network"] = {"radius": 0}
        for person in data["people"]:
            person["position"] = [0.5, 0.5]
        for person, state in Simulation(make_scenario(data)).step().majority_states:
            self.assertEqual(len(state.entries), 3)
            self.assertNotIn(person, [p for p, *_ in state.entries])

    def test_completed_ballots_not_preferences_or_future_edits(self):
        data = configured(); data["network"] = {"radius": 1.4}
        data["interventions"] = [{"round": 1, "person": "1", "ballot": ["C", "A"]}]
        simulation = Simulation(make_scenario(data))
        first, second = simulation.step(), simulation.step()
        def vote(frame): return next(c for p, c, _, _ in dict(frame.majority_states)["4"].entries if p == "1")
        self.assertEqual(vote(first), "A")
        self.assertEqual(vote(second), "C")
        self.assertEqual(dict(second.preferences)["1"][0], "A")

    def test_policy_switch_does_not_erase_memory(self):
        data = configured(); data["network"] = {"radius": 1.4}
        for person, position in zip(data["people"], ([0, 0], [0.4, 0.4], [1, 1], [0.2, 0.2])):
            person["position"] = position
        sim = Simulation(make_scenario(data)); sim.step()
        self.assertGreater(len(dict(sim.current.majority_states)["4"].entries), 0)
        sim.edit_after(1, "4", overrides={"voting": "local_plurality", "proximity_radius": 0})
        frame = sim.step()
        self.assertEqual(dict(frame.majority_states)["4"].entries, dict(sim.frames[1].majority_states)["4"].entries)

    def test_replay_rewind_immutable_frames_and_tampering(self):
        data = configured(); data["network"] = {"radius": 0.5}
        sim = Simulation(make_scenario(data)); sim.run(3)
        original = copy.deepcopy(sim.frames[1].as_dict())
        self.assertEqual(sim.checkpoint()["version"], 22)
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(restored.step(), sim.step())
        sim.edit_after(1, "1", position=[0, 0])
        sim.run(2)
        self.assertEqual(sim.frames[1].as_dict(), original)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        changed = copy.deepcopy(sim.checkpoint())
        changed["frames"][1]["majority_estimation"]["1"]["sample_size"] += 1
        with self.assertRaisesRegex(ElectionError, "history"):
            Simulation.from_checkpoint(changed)
        old = sim.checkpoint(); old["version"] = 21
        with self.assertRaisesRegex(ElectionError, "version 22"):
            Simulation.from_checkpoint(old)
        disabled = Simulation(make_scenario(example())); disabled.run(2)
        self.assertEqual(disabled.checkpoint()["version"], 21)
        self.assertEqual(Simulation.from_checkpoint(disabled.checkpoint()).current, disabled.current)

    def test_session_cli_json_csv_and_inspector(self):
        sim = Simulation(make_scenario(configured())); session = Session(sim)
        response = session.command({"action": "step", "revision": 0})
        self.assertEqual(response["frame"], sim.current.as_dict())
        self.assertIn("majority_estimation", session.snapshot())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "metrics.csv"
            write_metrics_csv(output, sim.scenario, series(sim.scenario, sim.frames))
            with output.open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(float(rows[-1]["majority_mean_sample_size"]), response["metric"]["majority_mean_sample_size"])
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["run", "examples/recent-majority.toml", "--sample", "100"]), 0)
            self.assertIn("majority_estimation", json.loads(stdout.getvalue())["frames"][-1])
        if shutil.which("node"):
            result = subprocess.run(["node", "-e", "const {inspectAgent}=require('./src/multi_agent_election/web/inspector.js');let d='';process.stdin.on('data',x=>d+=x);process.stdin.on('end',()=>console.log(JSON.stringify(inspectAgent(JSON.parse(d),'1').majority_estimation)));"],
                                    input=json.dumps(sim.current.as_dict()), text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), sim.current.as_dict()["majority_estimation"]["1"])


class MajorityPilotTests(VerificationTestCase):
    def test_generator_counts_poll_pairing_and_shift(self):
        for case in ("well_mixed", "clustered", "support_shift"):
            first, audit = pilot_scenario(101, case, False)
            second, other = pilot_scenario(101, case, True)
            self.assertEqual(first.people, second.people)
            self.assertEqual(audit, other)
            self.assertEqual(sum(first.majority_estimation.poll_counts), 100)
            self.assertEqual([sum(p.preference[0] == c for p in first.people) for c in PARTIES], [80, 70, 50])
            if case == "support_shift":
                self.assertEqual(len(first.interventions), 20)

    def test_small_pilot_raw_predictions_and_exclusive_outputs(self):
        scenario = replace(make_scenario(configured()), rounds=3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot"
            result = run_pilot(path, seeds=[11], sensitivity=True, scenario=scenario)
            self.assertEqual(result["failed"], 0, result["runs"])
            self.assertEqual(len(result["runs"][0]["arms"]), 8)
            with gzip.open(path / "provided-configured-11" / "predictions.jsonl.gz", "rt") as handle:
                rows = [json.loads(line) for line in handle]
            self.assertEqual(len(rows), 1 + 3 * 8)
            self.assertEqual(rows[1]["source_round"], 0)
            self.assertEqual(result["runs"][0]["arms"]["poll_only"]["mean_retained_neighbors"], 0)
            repeated = Path(directory) / "repeated"
            again = run_pilot(repeated, seeds=[11], sensitivity=True, scenario=scenario)
            self.assertEqual(again["failed"], 0)
            for name in ("trace.jsonl.gz", "predictions.jsonl.gz"):
                relative = "provided-configured-11/" + name
                self.assertEqual(result["artifacts"][relative]["sha256"], again["artifacts"][relative]["sha256"])
            self.assertEqual(result["runs"][0]["arms"]["blended"]["leader_set_accuracy"],
                             again["runs"][0]["arms"]["blended"]["leader_set_accuracy"])
            with self.assertRaises(ElectionError):
                run_pilot(path, seeds=[11], scenario=scenario)

    def test_cli_pilot_errors_do_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["estimate-majority", "--output-dir", str(path)]), 2)
                self.assertEqual(main(["estimate-majority", "examples/baseline.toml", "--output-dir", str(path)]), 2)
            self.assertFalse(path.exists())
