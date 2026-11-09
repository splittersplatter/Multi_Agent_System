"""Recorded rounds must match the engine and remain inert during playback."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from verification_support import VerificationTestCase
from test_baseline import example
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election import cli
from multi_agent_election.metrics import series
from multi_agent_election.playback import load_recording, make_playback_server
from multi_agent_election.state_recording import RecordingGroup, active_recordings
from multi_agent_election.visual import Session

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def recordings(directory):
    group = RecordingGroup(Path(directory) / "rounds")
    token = active_recordings.set(group)
    try:
        yield group
    finally:
        active_recordings.reset(token)
        group.close()


class StateRecordingTests(VerificationTestCase):
    def test_all_rounds_ranked_ballots_dynamic_preferences_and_no_vote_effect(self):
        raw = example()
        raw["interventions"] = [{"round": 2, "person": "1", "preference": ["B", "C", "A"],
                                  "position": [.8, .2]}]
        scenario = make_scenario(raw)
        plain = Simulation(scenario); plain.run(4)
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                recorded = Simulation(scenario); recorded.run(4)
                # Initial and committed rounds are visible before the file closes.
                prefix = load_recording(group.recorders[0].path)
                self.assertFalse(prefix[-1])
                self.assertEqual(len(prefix[2]), 5)
            data = load_recording(group.recorders[0].path)
            self.assertTrue(data[-1])
            self.assertEqual(data[2], [f.as_dict() for f in plain.frames])
            self.assertEqual(data[3], series(scenario, plain.frames))
            self.assertEqual(recorded.frames, plain.frames)
            self.assertEqual(data[2][2]["preferences"]["1"], ["B", "C", "A"])
            self.assertEqual(data[2][2]["positions"]["1"], [.8, .2])
            self.assertEqual(len(data[2][2]["ballots"]["1"]), scenario.k)

    def test_rewind_replaces_future_without_inventing_old_rounds(self):
        scenario = make_scenario(example())
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                simulation = Simulation(scenario); simulation.run(4)
                simulation.edit_after(1, "1", position=[.9, .9])
                simulation.run(2)
            result = load_recording(group.recorders[0].path)
            self.assertEqual([f["round"] for f in result[2]], [0, 1, 2, 3])
            self.assertEqual(result[2], [f.as_dict() for f in simulation.frames])
            self.assertEqual(result[2][2]["positions"]["1"], [.9, .9])

    def test_failed_round_is_absent_and_existing_file_is_preserved(self):
        raw = example()
        raw["interventions"] = [{"round": 2, "person": "1", "remove_edges": ["2"]}]
        # Remove every edge so the requested deletion necessarily fails.
        raw["network"] = {}
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                simulation = Simulation(make_scenario(raw))
                simulation.step()
                with self.assertRaises(ElectionError):
                    simulation.step()
            path = group.recorders[0].path
            self.assertEqual([f["round"] for f in load_recording(path)[2]], [0, 1])
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                with recordings(directory):
                    Simulation(make_scenario(example()))
            self.assertEqual(path.read_bytes(), original)

    def test_separate_episodes_and_browser_policy_restart_have_separate_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                session = Session(Simulation(make_scenario(example())))
                session.command({"revision": 0, "action": "configure_voting", "policy": "local_plurality", "parameters": {}})
                session.command({"revision": 1, "action": "step"})
            self.assertEqual(len(group.recorders), 2)
            self.assertEqual(len(load_recording(group.recorders[0].path)[2]), 1)
            self.assertEqual(len(load_recording(group.recorders[1].path)[2]), 2)
            self.assertIsNone(active_recordings.get())

    def test_recording_io_failure_prevents_round_and_rewind_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                simulation = Simulation(make_scenario(example()))
                initial = simulation.current
                with patch.object(group.recorders[0], "_write", side_effect=OSError("disk full")):
                    with self.assertRaises(OSError):
                        simulation.step()
                self.assertEqual(simulation.current, initial)
                simulation.run(3)
                saved = simulation.checkpoint()
                with patch.object(group.recorders[0], "_write", side_effect=OSError("disk full")):
                    with self.assertRaises(OSError):
                        simulation.edit_after(1, "1", position=[.8, .8])
                self.assertEqual(simulation.checkpoint(), saved)
            self.assertEqual(len(load_recording(group.recorders[0].path)[2]), 4)

    def test_bad_schema_gaps_tallies_and_truncated_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            with recordings(directory) as group:
                simulation = Simulation(make_scenario(example())); simulation.run(2)
            path = group.recorders[0].path
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            for change in ("round", "node", "preference", "tally", "header", "end"):
                bad = copy.deepcopy(rows)
                if change == "round": bad[2]["data"]["round"] = 9
                elif change == "node": bad[2]["data"]["positions"].pop("1")
                elif change == "preference": bad[2]["data"]["preferences"]["1"] = ["A", "A", "A"]
                elif change == "tally": bad[2]["data"]["counts"]["A"] += 1
                elif change == "header": bad[0]["version"] = 900
                else: bad[-1]["last_round"] += 1
                target = Path(directory) / f"bad-{change}.jsonl"
                target.write_text("".join(json.dumps(row) + "\n" for row in bad))
                with self.subTest(change=change), self.assertRaises(ElectionError):
                    load_recording(target)
            target = Path(directory) / "interrupted.jsonl"
            target.write_text("".join(json.dumps(row) + "\n" for row in rows[:-1]) + '{"type":')
            result = load_recording(target)
            self.assertFalse(result[-1])
            self.assertEqual(len(result[2]), 3)

    def test_frequency_cli_streams_all_rounds_and_view_serves_same_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                out = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(out):
                    self.assertEqual(cli.main(["frequencies", str(ROOT / "examples/gaussian-memory.toml"), "--rounds", "12",
                                               "--burn-in", "0", "--batch-size", "10", "--save-states"]), 0)
                paths = list(Path("outputs").glob("*-states.jsonl"))
                self.assertEqual(len(paths), 1)
                self.assertIn(str(paths[0]), out.getvalue())
                scenario, _, frames, metrics, closed = load_recording(paths[0])
                self.assertEqual(len(frames), 13)
                self.assertEqual(len(frames[-1]["positions"]), 200)
                self.assertTrue(closed)
                with patch.object(Simulation, "__init__", side_effect=AssertionError("playback must not rerun simulation")):
                    server = make_playback_server(paths[0], 0)
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                try:
                    base = f"http://127.0.0.1:{server.server_port}"
                    with urlopen(base + "/") as response:
                        token = response.read().decode().split('name="session-token" content="')[1].split('"')[0]
                    with urlopen(Request(base + "/state", headers={"X-Session-Token": token})) as response:
                        state = json.load(response)
                    self.assertTrue(state["read_only"])
                    self.assertEqual(state["frames"], frames)
                    self.assertEqual(state["metrics"], metrics)
                    for action in ("step", "edit", "configure_voting"):
                        request = Request(base + "/command", data=json.dumps({"action": action}).encode(),
                                          headers={"X-Session-Token": token, "Content-Type": "application/json"})
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(request)
                        self.assertEqual(caught.exception.code, 405)
                        caught.exception.close()
                finally:
                    server.shutdown(); server.server_close(); thread.join(timeout=5)
            finally:
                os.chdir(previous)

    def test_latest_view_selects_saved_recording_without_running_simulation(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(["view", "--latest"]), 2)
                Path("outputs").mkdir()
                older = Path("outputs/run-old-states.jsonl")
                newer = Path("outputs/grid-new-states.jsonl")
                older.touch(); newer.touch()
                os.utime(older, ns=(100, 100)); os.utime(newer, ns=(200, 200))
                server = SimpleNamespace(server_port=8000, serve_forever=lambda: None, server_close=lambda: None)
                with patch("multi_agent_election.playback.make_playback_server", return_value=server) as factory:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main(["view", "--latest"]), 0)
                    factory.assert_called_once_with(newer, 8000)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(["view", str(older), "--latest"]), 2)
            finally:
                os.chdir(previous)
