"""Gaussian runtime, retired-grid rejection and retained streaming/CLI contracts."""

import contextlib
import copy
import io
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from verification_support import VerificationTestCase
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election import cli
from multi_agent_election.network import random_walk, proximity_edges
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.occupation import Means, assessment, configure_control, observables, run_frequencies
from multi_agent_election.visual import Session, make_server

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return {"parties": ["A", "B", "C"], "k": 1, "seed": 101, "rounds": 21,
            "majority_estimation": {"poll_counts": [2, 1, 1], "memory_rounds": 10,
                                    "poll_weight": .5, "poll_refresh_rounds": 10},
            "network": {"radius": .12},
            "groups": {"people": {"voting": "memory_pivotal", "movement": "random_walk", "max_step": .05}},
            "people": [{"id": f"p{i}", "group": "people", "preference": pref,
                        "position": [.5 + i * .075, .5]}
                       for i, pref in enumerate((["A", "B", "C"], ["B", "C", "A"], ["C", "B", "A"]))]}


class GaussianEngineTests(VerificationTestCase):
    def test_default_kernel_positions_contacts_and_bounds(self):
        sim = Simulation(make_scenario(fixture()))
        params = json.loads(sim.scenario.groups[0].parameters)["movement"]
        self.assertEqual(params, {"distribution": "normal", "mean_step": .025, "std_step": .00625})
        for tick in range(1, 26):
            previous = dict(sim.current.positions)
            frame = sim.step()
            for person, xy in frame.positions:
                self.assertEqual(xy, random_walk(previous[person], .05, 101, person, tick, params))
                self.assertLessEqual(math.dist(xy, previous[person]), .05 + 1e-15)
                self.assertTrue(all(0 <= v <= 1 for v in xy))
            self.assertEqual(frame.proximity_edges, proximity_edges(dict(frame.positions), .12))
            state = dict(frame.majority_states)["p0"]
            self.assertEqual(state.published_round, ((tick - 1) // 10) * 10)

    def test_retired_grid_rejected_in_groups_overrides_and_declarations(self):
        for mutation in (lambda raw: raw["groups"]["people"].update(movement="grid_walk"),
                         lambda raw: raw["people"][0].update(overrides={"movement": "grid_walk"}),
                         lambda raw: raw.update(interventions=[{"round": 1, "person": "p0", "overrides": {"movement": "grid_walk"}}]),
                         lambda raw: raw.update(stochastic_stability={"case": "finite_grid_occupation_v1"}),
                         lambda raw: raw["people"][0].update(grid_position=[0, 0])):
            raw = fixture(); mutation(raw)
            with self.assertRaisesRegex(ElectionError, "retired"):
                make_scenario(raw)
        sim = Simulation(make_scenario(fixture())); before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "retired"):
            sim.edit_after(0, "p0", overrides={"movement": "grid_walk"})
        self.assertEqual(sim.checkpoint(), before)

    def test_checkpoint25_replay_rewind_and_tamper(self):
        sim = Simulation(make_scenario(fixture())); sim.run(12)
        saved = sim.checkpoint()
        self.assertEqual(saved["version"], 25)
        self.assertEqual(Simulation.from_checkpoint(saved).step(), sim.step())
        invalid = copy.deepcopy(saved); invalid["frames"][1]["positions"]["p0"][0] += .001
        with self.assertRaises(ElectionError): Simulation.from_checkpoint(invalid)
        sim.edit_after(2, "p0", ballot=["B"])
        self.assertEqual(sim.current.round, 2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).step(), sim.step())

    def test_legacy_implicit_uniform_is_preserved_not_silently_replaced(self):
        raw = fixture(); raw["groups"]["people"]["parameters"] = {"movement": {"distribution": "uniform"}}
        sim = Simulation(make_scenario(raw)); sim.run(12)
        legacy = sim.checkpoint(); legacy["version"] = 23
        legacy["scenario"]["groups"]["people"]["parameters"] = {}
        restored = Simulation.from_checkpoint(legacy)
        self.assertEqual(restored.frames, sim.frames)
        self.assertEqual(restored.step(), sim.step())
        # Grid checkpoints are never silently migrated to a different motion model.
        legacy["scenario"]["stochastic_stability"] = {"case": "finite_grid_occupation_v1"}
        with self.assertRaisesRegex(ElectionError, "retired"): Simulation.from_checkpoint(legacy)

    def test_legacy_implicit_normal_parameters_and_ambiguous_overrides(self):
        raw = fixture()
        raw["groups"]["people"]["parameters"] = {"movement": {"distribution": "normal", "mean_step": .05, "std_step": .0125}}
        sim = Simulation(make_scenario(raw)); sim.run(3)
        legacy = sim.checkpoint(); legacy["version"] = 23
        legacy["scenario"]["groups"]["people"]["parameters"]["movement"] = {"distribution": "normal"}
        self.assertEqual(Simulation.from_checkpoint(legacy).frames, sim.frames)
        legacy["scenario"]["people"][0]["overrides"] = {"parameters": {}}
        with self.assertRaisesRegex(ElectionError, "archived runtime"): Simulation.from_checkpoint(legacy)
        raw = fixture(); raw["groups"]["people"]["movement"] = "stationary"
        raw["people"][0]["overrides"] = {"movement": "random_walk"}
        legacy = Simulation(make_scenario(raw)).checkpoint(); legacy["version"] = 23
        with self.assertRaisesRegex(ElectionError, "archived runtime"): Simulation.from_checkpoint(legacy)

    def test_new_checkpoint_resolves_overrides_and_rejects_source_changes(self):
        raw = fixture(); raw["people"][0]["overrides"] = {"parameters": {"voting": {}}}
        raw["interventions"] = [{"round": 2, "person": "p1", "overrides": {"parameters": {}}}]
        sim = Simulation(make_scenario(raw)); sim.run(3)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).step(), sim.step())
        changed = sim.checkpoint(); changed["manifest"]["core_sha256"] = "changed"
        with self.assertRaisesRegex(ElectionError, "core source changed"): Simulation.from_checkpoint(changed)

    def test_browser_shared_engine_no_grid_certificate_or_edit_lock(self):
        sim = Simulation(make_scenario(fixture()))
        session = Session(Simulation(sim.scenario))
        self.assertFalse(session.snapshot()["startup_voting_locked"])
        self.assertNotIn("stochastic_stability", session.snapshot())
        for tick in range(3):
            result = session.command({"action": "step", "revision": tick})
            expected = sim.step()
            self.assertEqual(result["frame"], expected.as_dict())
            self.assertEqual(result["metric"], frame_metrics(sim.scenario, expected, sim.frames[-2]))
        session.command({"action": "edit", "revision": 3, "round": 1, "person": "p0", "changes": {"ballot": ["B"]}})
        self.assertEqual(session.simulation.current.round, 1)

    def test_200_person_http_agrees_with_cli_engine(self):
        with (ROOT / "examples/gaussian-memory.toml").open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        self.assertEqual(len(scenario.people), 200)
        self.assertEqual(len({p.position for p in scenario.people}), 200)
        sim = Simulation(scenario)
        server = make_server(Simulation(scenario), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/") as response:
                token = response.read().decode().split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            with urlopen(Request(base + "/state", headers=headers)) as response:
                self.assertNotIn("stochastic_stability", json.load(response))
            request = Request(base + "/command", data=json.dumps({"action": "step", "revision": 0}).encode(), headers=headers)
            with urlopen(request) as response:
                actual = json.load(response)
            self.assertEqual(actual["frame"], json.loads(json.dumps(sim.step().as_dict())))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)


class GaussianPopulationTests(unittest.TestCase):
    def test_production_floor_99_100_101(self):
        with (ROOT / "examples/gaussian-memory.toml").open("rb") as handle:
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
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["stochastic_stability"]["status"], "uncertified_exploration")
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

    def test_controls_match_gaussian_motion_without_certification(self):
        scenario = make_scenario(fixture())
        sincere = configure_control(scenario, "sincere")
        base, ref = Simulation(scenario), Simulation(sincere)
        for _ in range(12):
            self.assertEqual(base.step().positions, ref.step().positions)
        self.assertEqual(assessment(scenario)["status"], "uncertified_exploration")
        self.assertFalse(assessment(scenario)["occupation_frequency_guarantee"])
        for old_control in ("continuous-normal", "sincere-grid"):
            with self.assertRaises(ElectionError): configure_control(scenario, old_control)

    def test_sincere_control_removes_policy_overrides_but_preserves_motion(self):
        raw = fixture()
        raw["people"][0]["overrides"] = {"voting": "memory_pivotal", "parameters": {"movement": {"std_step": .003}}}
        raw["interventions"] = [{"round": 2, "person": "p1", "overrides": {"voting": "memory_pivotal"}}]
        base = Simulation(make_scenario(raw))
        sincere = Simulation(configure_control(base.scenario, "sincere"))
        for _ in range(12):
            a, b = base.step(), sincere.step()
            self.assertEqual(a.positions, b.positions)
            self.assertEqual(a.proximity_edges, b.proximity_edges)
            self.assertEqual(dict(b.ballots), {p.id: p.preference[:1] for p in sincere.scenario.people})

    def test_cli_controls_rows_and_summary_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output, rows = Path(directory) / "summary.json", Path(directory) / "rows.csv"
            args = ["frequencies", str(ROOT / "examples/gaussian-memory.toml"), "--rounds", "11", "--burn-in", "0",
                    "--batch-size", "10", "--control", "sincere", "--seed", "2000", "--rows", str(rows), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(cli.main(args), 0)
            record = json.loads(output.read_text())
            self.assertEqual(record["completed_rounds"], 11)
            self.assertEqual(record["seed"], 2000)
            self.assertEqual(record["control"], "sincere")
            saved = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(cli.main(args), 2)
            self.assertEqual(output.read_bytes(), saved)

    def test_cli_automatically_names_paired_outputs_and_never_overwrites(self):
        from datetime import datetime, timezone
        started = datetime(2026, 11, 9, 12, 34, 56, 123456, tzinfo=timezone.utc)
        args = ["frequencies", str(ROOT / "examples/gaussian-memory.toml"), "--rounds", "1",
                "--burn-in", "0", "--batch-size", "10"]
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(cli, "datetime") as clock:
                    clock.now.return_value = started
                    capture = io.StringIO()
                    with contextlib.redirect_stdout(capture):
                        self.assertEqual(cli.main(args), 0)
                    result = json.loads(capture.getvalue())
                    output, rows = Path(result["output"]), Path(result["rows"])
                    self.assertEqual(output.name, "frequencies-20261109T123456-123456Z.json")
                    self.assertEqual(rows.name, "frequencies-20261109T123456-123456Z.csv")
                    self.assertEqual(json.loads(output.read_text())["raw_rows"], str(rows))
                    self.assertEqual(len(rows.read_text().splitlines()), 2)
                    before = output.read_bytes(), rows.read_bytes()
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(cli.main(args), 2)
                    self.assertEqual((output.read_bytes(), rows.read_bytes()), before)
            finally:
                os.chdir(previous)

    def test_run_summary_and_frequencies_save_real_plots_without_file_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                scenario = Path(directory) / "scenario.toml"
                # Use the real 200-person preset, but reduce the configured run horizon.
                source = (ROOT / "examples/gaussian-memory.toml").read_text()
                scenario.write_text(source.replace("rounds = 10000", "rounds = 2", 1))
                for args in (["run", str(scenario), "--summary", "--save-plots"],
                             ["frequencies", str(scenario), "--rounds", "2", "--burn-in", "0",
                              "--batch-size", "10", "--save-plots"]):
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(cli.main(args), 0)
                outputs = list(Path("outputs").iterdir())
                self.assertEqual(len(list(Path("outputs").glob("*.svg"))), 2)
                self.assertEqual(len(list(Path("outputs").glob("*.jsonl"))), 1)
                self.assertEqual(len(list(Path("outputs").glob("*.csv"))), 1)
                for path in (p for p in outputs if p.suffix == ".svg"):
                    self.assertIn("<polyline", path.read_text())
            finally:
                os.chdir(previous)

    def test_comparison_saves_result_and_plots_preserving_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                source = (ROOT / "examples/recent-majority.toml").read_text().replace("rounds = 100", "rounds = 1", 1)
                scenario = Path(directory) / "scenario.toml"
                scenario.write_text(source)
                capture = io.StringIO()
                with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(["compare", str(scenario), "--seeds", "1", "--policies", "sincere", "--save-plots"]), 0)
                result = json.loads(capture.getvalue())
                saved = list(Path("outputs").glob("*.json"))
                self.assertEqual(len(saved), 1)
                self.assertEqual(json.loads(saved[0].read_text()), result)
                plots = list(Path("outputs").glob("*-plots/*.svg"))
                self.assertEqual(len(plots), 1)
                self.assertIn("<polyline", plots[0].read_text())
                self.assertTrue(list(Path("outputs").glob("*-plots/index.json")))
            finally:
                os.chdir(previous)

    def test_majority_pilot_auto_directory_and_actual_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                scenario = Path(directory) / "scenario.toml"
                scenario.write_text((ROOT / "examples/recent-majority.toml").read_text().replace("rounds = 100", "rounds = 1", 1))
                with contextlib.redirect_stdout(io.StringIO()) as capture:
                    self.assertEqual(cli.main(["estimate-majority", str(scenario), "--seeds", "101", "--save-plots"]), 0)
                output = Path(json.loads(capture.getvalue())["output_dir"])
                self.assertTrue((output / "results.json").exists())
                plots = list(output.glob("*/vote-shares.svg"))
                self.assertEqual(len(plots), 1)
                self.assertIn("<svg", plots[0].read_text())
            finally:
                os.chdir(previous)

    def test_visual_shutdown_saves_current_session_checkpoint_and_plot(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                scenario = Path(directory) / "scenario.toml"
                scenario.write_text((ROOT / "examples/gaussian-memory.toml").read_text())
                def make_server(simulation, port):
                    session = Session(simulation)
                    def serve():
                        session.command({"action": "step", "revision": 0})
                        raise KeyboardInterrupt
                    return SimpleNamespace(server_port=port, session=session, serve_forever=serve, server_close=lambda: None)
                with patch("multi_agent_election.visual.make_server", side_effect=make_server), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main(["visual", str(scenario), "--port", "8001", "--save-plots"]), 0)
                saved = list(Path("outputs").glob("visual-*.json"))
                self.assertEqual(len(saved), 1)
                self.assertEqual(json.loads(saved[0].read_text())["frames"][-1]["round"], 1)
                self.assertEqual(len(list(Path("outputs").glob("visual-*.svg"))), 1)
            finally:
                os.chdir(previous)
