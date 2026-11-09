"""Shared-engine/grid proof correspondence, guarded by explicit fixture scope."""

import contextlib
import copy
from dataclasses import replace
from fractions import Fraction
from itertools import product
import io
import json
from pathlib import Path
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from verification_support import VerificationTestCase
from scripts import verify_stochastic_stability as proof
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election import cli, grid
from multi_agent_election.model import Intervention
from multi_agent_election.exports import write_metrics_csv
from multi_agent_election.metrics import frame_metrics, series
from multi_agent_election.occupation import Means, configure_control, observables, run_frequencies
from multi_agent_election.visual import Session, make_server

ROOT = Path(__file__).resolve().parents[1]


def fixture(n=3):
    return {"parties": ["A", "B", "C"], "k": 1, "seed": 101, "rounds": 21,
            "stochastic_stability": {"case": grid.CASE},
            "majority_estimation": {"poll_counts": [2, 1, 1], "memory_rounds": 10,
                                    "poll_weight": .5, "poll_refresh_rounds": 10},
            "network": {"radius": .12},
            "groups": {"people": {"voting": "memory_pivotal", "movement": "grid_walk", "max_step": .025}},
            "people": [{"id": f"p{i}", "group": "people", "preference": pref,
                        "grid_position": [20 + i * 3, 20]}
                       for i, pref in enumerate((["A", "B", "C"], ["B", "C", "A"], ["C", "B", "A"])[:n])]}


def normalize(frame):
    states = dict(frame.majority_states)
    people = tuple(p for p, _ in frame.ballots)
    poll = next(iter(states.values())).published_poll or (2, 1, 1)
    return proof.State(tuple(grid.integer_position(pos) for _, pos in frame.positions),
                       tuple(("A", "B", "C").index(b[0]) for _, b in frame.ballots),
                       tuple(tuple((people.index(p), ("A", "B", "C").index(c), frame.round - seen)
                                   for p, c, seen, _ in states[i].entries) for i in people),
                       poll, frame.round % 10, frame.round == 0)


class GridEngineTests(VerificationTestCase):
    def test_every_initial_proposal_vector_matches_formal_successor(self):
        raw = fixture()
        model = proof.Model(((0, 1, 2), (1, 2, 0), (2, 1, 0)), (2, 1, 1))
        for proposals in product(range(5), repeat=3):
            simulation = Simulation(make_scenario(raw))
            expected = proof.transition(model, normalize(simulation.current), proposals)
            with patch.object(grid, "proposal", side_effect=proposals):
                actual = simulation.step()
            self.assertEqual(normalize(actual), expected)

    def test_25_round_cache_phase_publication_correspondence_with_actual_seeded_draws(self):
        simulation = Simulation(make_scenario(fixture()))
        model = proof.Model(((0, 1, 2), (1, 2, 0), (2, 1, 0)), (2, 1, 1))
        expected = normalize(simulation.current)
        for tick in range(1, 26):
            proposals = tuple(grid.proposal(101, f"p{i}", tick) for i in range(3))
            expected = proof.transition(model, expected, proposals)
            self.assertEqual(normalize(simulation.step()), expected)

    def test_integer_bucket_proximity_matches_all_pairs_fraction_oracle(self):
        positions = {str(i): grid.physical((i % 41, i // 41)) for i in range(1681)}
        # Full lattice tests adjacent-cell boundaries, coincident exclusion and all offsets.
        actual = set(grid.proximity(positions))
        expected = set()
        for i in range(1681):
            x, y = i % 41, i // 41
            for dx, dy in product(range(-5, 6), repeat=2):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx <= 40 and 0 <= ny <= 40 and 25*(dx*dx + dy*dy) <= 576:
                    expected.add((str(i), str(ny*41 + nx)))
        self.assertEqual(actual, expected)

    def test_boundary_stay_and_off_grid_rejection(self):
        for proposal in (0, 2, 4):
            with patch.object(grid, "proposal", return_value=proposal):
                self.assertEqual(grid.walk((0, 0), 101, "p", 1), (0, 0))
        for point in ((.10000000001, .5), (.001, .5), (True, .5)):
            with self.assertRaises(ElectionError):
                grid.integer_position(point)
        for coords in ((True, 0), (41, 0), (1.0, 1), (-1, 1)):
            with self.assertRaises(ElectionError):
                grid.physical(coords)

    def test_guard_rejects_domain_expansions_and_ambiguous_initial_coordinates(self):
        base = fixture()
        variants = []
        for key, value in (("k", 2), ("interventions", [{"round": 1, "person": "p0", "ballot": ["B"]}])):
            raw = copy.deepcopy(base); raw[key] = value; variants.append(raw)
        for key, value in (("movement", "random_walk"), ("voting", "sincere"), ("communication", "truthful"),
                           ("capabilities", {"sense_public_ballots": True}), ("parameters", {"unused": True}),
                           ("max_step", .05), ("proximity_radius", .1)):
            raw = copy.deepcopy(base); raw["groups"]["people"][key] = value; variants.append(raw)
        for key, value in (("memory_rounds", 9), ("poll_refresh_rounds", 9), ("poll_weight", .25)):
            raw = copy.deepcopy(base); raw["majority_estimation"][key] = value; variants.append(raw)
        for key, value in (("radius", .1), ("proximity_mode", "frozen"), ("persistent_edges", [["p0", "p1"]])):
            raw = copy.deepcopy(base); raw["network"][key] = value; variants.append(raw)
        raw = copy.deepcopy(base); raw["people"][0]["position"] = [.5, .5]; variants.append(raw)
        raw = copy.deepcopy(base); raw["people"][0].pop("grid_position"); variants.append(raw)
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ElectionError):
                make_scenario(raw)
        scenario = make_scenario(base)
        with self.assertRaises(ElectionError):
            Simulation(replace(scenario, radius=.13))

    def test_checkpoint24_replay_tamper_and_domain_edit_atomicity(self):
        simulation = Simulation(make_scenario(fixture()))
        simulation.run(12)
        saved = simulation.checkpoint()
        self.assertEqual(saved["version"], 24)
        self.assertEqual(Simulation.from_checkpoint(saved).step(), simulation.step())
        frozen = simulation.checkpoint()
        with self.assertRaises(ElectionError):
            simulation.edit_after(2, "p0", ballot=["B"])
        self.assertEqual(simulation.checkpoint(), frozen)
        for kind in ("version", "coordinate", "cache", "manual"):
            invalid = copy.deepcopy(saved)
            if kind == "version": invalid["version"] = 23
            elif kind == "coordinate": invalid["frames"][1]["positions"]["p0"][0] += .001
            elif kind == "cache": invalid["frames"][1]["majority_estimation"]["p0"]["sample_size"] += 1
            else: invalid["manual_interventions"] = [{"round": 1, "person": "p0", "ballot": ["B"]}]
            with self.subTest(kind=kind), self.assertRaises(ElectionError):
                Simulation.from_checkpoint(invalid)

    def test_direct_manual_queue_assignment_cannot_bypass_stochastic_guard(self):
        simulation = Simulation(make_scenario(fixture()))
        saved = simulation.current
        simulation.manual_interventions = (Intervention(1, "p0", preference=("C", "B", "A")),)
        with self.assertRaisesRegex(ElectionError, "excludes interactive interventions"):
            simulation.step()
        self.assertEqual(simulation.current, saved)

    def test_effective_grid_overrides_get_exact_contacts_guard_and_checkpoint24(self):
        raw = fixture()
        raw.pop("stochastic_stability")
        raw["groups"]["people"].update(movement="stationary", max_step=0)
        for person in raw["people"]:
            person["overrides"] = {"movement": "grid_walk", "max_step": .025}
        simulation = Simulation(make_scenario(raw))
        self.assertTrue(grid.enabled(simulation.scenario))
        self.assertEqual(simulation.checkpoint()["version"], 24)
        self.assertEqual(simulation.current.proximity_edges, grid.proximity(dict(simulation.current.positions)))
        raw["network"]["radius"] = .5
        with self.assertRaises(ElectionError):
            make_scenario(raw)
        raw["network"]["radius"] = .12
        raw["interventions"] = [{"round": 1, "person": "p0", "overrides": {"movement": "stationary"}}]
        with self.assertRaises(ElectionError):
            make_scenario(raw)

    def test_browser_session_equivalence_locked_edits_and_csv_metadata(self):
        simulation = Simulation(make_scenario(fixture()))
        session = Session(Simulation(simulation.scenario))
        self.assertTrue(session.snapshot()["startup_voting_locked"])
        self.assertEqual(session.snapshot()["stochastic_stability"]["status"], "conditional_occupation_theorem")
        for tick in range(3):
            result = session.command({"action": "step", "revision": tick})
            expected = simulation.step()
            self.assertEqual(result["frame"], expected.as_dict())
            self.assertEqual(result["metric"], frame_metrics(simulation.scenario, expected, simulation.frames[-2]))
        with self.assertRaises(ElectionError):
            session.command({"action": "edit", "revision": 3, "round": 1, "person": "p0", "changes": {"ballot": ["B"]}})
        self.assertEqual(session.revision, 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.csv"
            write_metrics_csv(path, simulation.scenario, series(simulation.scenario, simulation.frames))
            self.assertIn("occupation_theorem_status", path.read_text())

    def test_200_person_http_steps_and_population_floor(self):
        with (ROOT / "examples/stochastic-grid.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        scenario = make_scenario(raw)
        self.assertEqual(len(scenario.people), 200)
        self.assertEqual(len({p.grid_position for p in scenario.people}), 200)
        simulation = Simulation(scenario)
        server = make_server(Simulation(scenario), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            with urlopen(url + "/") as response:
                self.assertEqual(response.status, 200)
                html = response.read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            with urlopen(Request(url + "/state", headers={"X-Session-Token": token})) as response:
                state = json.load(response)
            self.assertIn("stochastic_stability", state)
            request = Request(url + "/command", data=json.dumps({"action": "step", "revision": 0}).encode(),
                              headers={"Content-Type": "application/json", "X-Session-Token": token})
            with urlopen(request) as response: actual = json.load(response)
            expected = json.loads(json.dumps(simulation.step().as_dict()))
            self.assertEqual(actual["frame"], expected)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)


class GridPopulationTests(unittest.TestCase):
    def test_production_floor_cannot_be_bypassed_by_stability_declaration(self):
        with (ROOT / "examples/stochastic-grid.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        for n in (99, 100, 101):
            case = copy.deepcopy(raw)
            case["people"] = case["people"][:n]
            if n == 99:
                with self.assertRaisesRegex(ElectionError, "at least 100"):
                    Simulation(make_scenario(case))
            else:
                self.assertEqual(len(Simulation(make_scenario(case)).current.ballots), n)


class OccupationDiagnosticsTests(VerificationTestCase):
    def test_streamed_views_match_independent_full_history_aggregation(self):
        scenario = make_scenario(fixture())
        simulation = Simulation(scenario); simulation.run(21)
        expected = [observables(scenario, b, a) for a, b in zip(simulation.frames, simulation.frames[1:])]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"
            result = run_frequencies(scenario, rounds=21, burn_in=10, batch_size=10, rows_path=path)
            self.assertEqual(len(path.read_text().splitlines()), 22)
        self.assertEqual(result["status"], "complete")
        for key in expected[0]:
            self.assertAlmostEqual(result["all_rounds"]["means"][key], sum(r[key] for r in expected) / 21)
            self.assertAlmostEqual(result["retained"]["means"][key], sum(r[key] for r in expected[10:]) / 11)
        self.assertEqual([b["complete"] for b in result["batches"]], [True, False])
        self.assertEqual(sum(p["rounds"] for p in result["retained"]["phase_conditioned"]), 11)
        for phase in result["retained"]["phase_conditioned"]:
            subset = [v for tick, v in enumerate(expected, 1) if tick > 10 and tick % 10 == phase["phase"]]
            self.assertEqual(phase["rounds"], len(subset))

    def test_descriptive_lag1_correlation_no_fake_error_bars(self):
        accumulator = Means(2)
        for t in range(1, 11): accumulator.add(t, {"cycle": t % 2, "constant": 1})
        self.assertAlmostEqual(accumulator.summary()["lag1_correlation_descriptive"]["cycle"], -1)
        self.assertIsNone(accumulator.summary()["lag1_correlation_descriptive"]["constant"])

    def test_failure_retains_prefix_and_invalid_protocol_does_not_create_files(self):
        scenario = make_scenario(fixture())
        actual = Simulation.step
        def fail_after_two(sim):
            if sim.current.round == 2: raise ElectionError("injected resource failure")
            return actual(sim)
        with patch.object(Simulation, "step", fail_after_two):
            result = run_frequencies(scenario, rounds=20, burn_in=0, batch_size=10)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["completed_rounds"], 2)
        self.assertIn("injected", result["error"])
        with patch.object(Simulation, "step", side_effect=MemoryError("resource ceiling")):
            failed = run_frequencies(scenario, rounds=20, burn_in=0, batch_size=10)
        self.assertEqual(failed["completed_rounds"], 0)
        self.assertEqual(failed["status"], "failed")
        self.assertIn("MemoryError", failed["error"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"
            for args in ({"rounds": 10, "burn_in": 10}, {"rounds": 20, "burn_in": 1}, {"rounds": 20, "batch_size": 9}):
                with self.assertRaises(ElectionError):
                    run_frequencies(scenario, rows_path=path, **args)
            self.assertFalse(path.exists())

    def test_controls_match_grid_motion_but_do_not_claim_continuous_certification(self):
        scenario = make_scenario(fixture())
        sincere = configure_control(scenario, "sincere-grid")
        normal = configure_control(scenario, "continuous-normal")
        base, ref = Simulation(scenario), Simulation(sincere)
        for _ in range(12):
            self.assertEqual(base.step().positions, ref.step().positions)
        self.assertEqual([p.position for p in normal.people], [p.position for p in scenario.people])
        self.assertIsNone(normal.stochastic_case)
        self.assertEqual(grid.assessment(normal)["status"], "uncertified_comparison")

    def test_cli_controls_rows_and_summary_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output, rows = Path(directory) / "summary.json", Path(directory) / "rows.csv"
            args = ["frequencies", str(ROOT / "examples/stochastic-grid.toml"), "--rounds", "11", "--burn-in", "0",
                    "--batch-size", "10", "--control", "sincere-grid", "--seed", "2000", "--rows", str(rows), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(cli.main(args), 0)
            record = json.loads(output.read_text())
            self.assertEqual(record["completed_rounds"], 11)
            self.assertEqual(record["seed"], 2000)
            self.assertEqual(record["control"], "sincere-grid")
            saved = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(cli.main(args), 2)
            self.assertEqual(output.read_bytes(), saved)
