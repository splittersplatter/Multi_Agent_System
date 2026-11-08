import contextlib
import csv
import io
import json
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.detector import update_detector
from multi_agent_election.experiments import compare_leaders
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.visual import Session


def example():
    with Path("examples/all-enabled.toml").open("rb") as handle:
        return tomllib.load(handle)


class AllEnabledTests(unittest.TestCase):
    def test_joint_budget_information_phase_and_replay_invariants(self):
        sim = Simulation(make_scenario(example())); sim.run()
        self.assertEqual(sim.scenario.parties, ("alice", "cara"))
        self.assertEqual(len(sim.current.ballots), 4)
        self.assertTrue(any(frame.positions != sim.frames[0].positions for frame in sim.frames[1:]))
        for previous, frame in zip(sim.frames, sim.frames[1:]):
            self.assertLessEqual(frame.alignment_spend, 0.3)
            self.assertLessEqual(dict(frame.leader_spend)["alice"], 0.3)
            self.assertLessEqual(frame.signal_spend, 2)
            self.assertLessEqual(len(frame.campaign_controller_purchased), 1)
            self.assertLessEqual(dict(frame.coalition_sight_spend)["team"], 2)
            self.assertEqual(frame.detector, update_detector(sim.scenario.detector, sim.scenario.parties,
                             dict(frame.counts), frame.round, previous.detector, dict(previous.counts)))
            self.assertEqual(frame.signal_latest[3], tuple(dict(previous.counts)[p] for p in sim.scenario.parties))
            event = next(c for c in frame.alignment_changes if c[0] == "bob")
            if event[4] > 1e-14:
                prior_perceived = dict(previous.leader_perceived)["alice"]
                drift, after = event[2], event[3]
                direction = tuple(t - x for t, x in zip(prior_perceived, drift))
                movement = tuple(y - x for x, y in zip(drift, after))
                self.assertAlmostEqual(direction[0]*movement[1] - direction[1]*movement[0], 0, places=12)
                self.assertGreaterEqual(sum(a*b for a, b in zip(direction, movement)), 0)
            for _, _, target, seen in frame.preference_sight:
                self.assertEqual(seen, dict(frame.preferences)[target])
            trace = json.loads(dict(frame.policy_memory)["bob"])
            self.assertNotIn("leader_true", trace); self.assertNotIn("source_truth", trace)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        sim.edit_after(2, "dina", ballot=["cara", "alice"]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        self.assertEqual(sim.frames[3].interventions[0].origin, "interactive")

    def test_cli_session_csv_and_nosignal_control_match(self):
        scenario = make_scenario(example()); sim = Simulation(scenario); session = Session(sim)
        for revision in range(scenario.rounds): session.command({"revision": revision, "action": "step"})
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(main(["run", "examples/all-enabled.toml"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["frames"], [frame.as_dict() for frame in sim.frames])
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"; csv_path = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/all-enabled.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(csv_path)]), 0)
            with csv_path.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertEqual(float(rows[1]["leader_spend:alice"]), 0.1)
            self.assertEqual(float(rows[1]["alignment_attack_spend"]), 0.15)
            self.assertEqual(rows[1]["signal_spend"], "1")
        comparison = compare_leaders(scenario, [2026])
        self.assertFalse(comparison["honest_exogenous_configuration"])
        self.assertTrue(comparison["rows"][0]["runs"]["adaptive_no_signal"]["nonsignal_invariant"])

    def test_http_step_matches_integrated_engine(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario = make_scenario(example()); direct = Simulation(scenario); direct.step()
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as response: html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        with urlopen(Request(base + "/state", headers=headers)) as response: snapshot = json.load(response)
        self.assertEqual(snapshot["leaders"]["policy"], "feedback")
        self.assertEqual(snapshot["detector"]["target"], "alice")
        request = Request(base + "/command", headers=headers, data=json.dumps({"action":"step", "revision":0}).encode(), method="POST")
        with urlopen(request) as response: result = json.load(response)
        self.assertEqual(result["frame"], direct.current.as_dict())
        self.assertEqual(result["metric"], frame_metrics(scenario, direct.current, direct.frames[0]))

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "optional Pillow not installed")
    def test_integrated_gif_export(self):
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "state.json"; gif = Path(folder) / "timeline.gif"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "examples/all-enabled.toml", "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--gif", str(gif)]), 0)
            from PIL import Image
            with Image.open(gif) as image:
                self.assertGreaterEqual(image.n_frames, 2)


if __name__ == "__main__": unittest.main()
