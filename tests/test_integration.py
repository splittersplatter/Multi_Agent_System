"""Cumulative CLI/browser/replay/export contract on a hand-worked scenario."""

import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from urllib.request import Request, urlopen

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.visual import make_server


class IntegratedScenarioTests(unittest.TestCase):
    def test_cli_browser_rewind_replay_and_exports_share_one_history(self):
        scenario_path = Path("examples/integrated.toml")
        with scenario_path.open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        examples = str(Path("examples").resolve())
        sys.path.insert(0, examples)
        self.addCleanup(lambda: sys.path.remove(examples))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint_file = root / "cli.json"
            env = {**os.environ, "PYTHONPATH": os.pathsep.join(("src", examples))}
            result = subprocess.run(
                [sys.executable, "-m", "multi_agent_election.cli", "run", str(scenario_path),
                 "--checkpoint", str(checkpoint_file)], env=env, text=True,
                capture_output=True, check=True)
            cli = json.loads(result.stdout)
            self.assertEqual([f["winner"] for f in cli["frames"]], ["A", "C", "A", "C"])
            self.assertEqual(cli["frames"][2]["ballots"]["3"], ["A", "B"])
            self.assertEqual(cli["frames"][3]["ballots"]["3"], ["C", "A"])
            self.assertIn(["1", "2"], cli["frames"][1]["persistent_edges"])
            self.assertIn(["1", "3"], cli["frames"][1]["proximity_edges"])
            self.assertIn(["3", "1"], cli["frames"][1]["persistent_edges"])
            self.assertEqual(cli["frames"][1]["campaign_edges"], [["2", "3"]])
            self.assertEqual(cli["frames"][2]["campaign_edges"], [["2", "3"], ["3", "1"]])
            self.assertEqual(cli["frames"][2]["ballot_sensors"], [["2", "1", "public", 1, ["C", "A"]]])
            self.assertTrue(any(m[:3] == ["3", "2", "team"] for m in cli["frames"][2]["delivered"]))

            server = make_server(Simulation(scenario))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            self.addCleanup(worker.join, 2)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            base = f"http://127.0.0.1:{server.server_port}"
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            def command(value):
                req = Request(base + "/command", data=json.dumps(value).encode(), headers=headers, method="POST")
                return json.load(urlopen(req))
            state = json.load(urlopen(Request(base + "/state", headers=headers)))
            frames, metrics = state["frames"], state["metrics"]
            for revision in range(3):
                reply = command({"action": "step", "revision": revision})
                frames.append(reply["frame"])
                metrics.append(reply["metric"])
            self.assertEqual(frames, cli["frames"])
            self.assertEqual(metrics, cli["metrics"])

            state = command({"action": "edit", "revision": 3, "round": 1, "person": "3",
                             "changes": {"preference": ["B", "C", "A"]}})
            self.assertEqual(state["frames"], cli["frames"][:2])
            round2 = command({"action": "step", "revision": 4})
            self.assertEqual(round2["frame"]["ballots"]["3"], ["A", "B"])
            self.assertEqual(round2["frame"]["positions"]["3"], [0.65, 0.2])
            self.assertEqual(round2["frame"]["campaign_edges"], [["2", "3"], ["3", "1"]])
            self.assertEqual(round2["frame"]["delivered"], cli["frames"][2]["delivered"])
            round3 = command({"action": "step", "revision": 5})
            self.assertEqual(round3["frame"]["ballots"]["3"], ["B", "C"])
            checkpoint = json.load(urlopen(Request(base + "/checkpoint", headers=headers)))
            self.assertEqual(Simulation.from_checkpoint(checkpoint).current.as_dict(), round3["frame"])
            direct = Simulation.from_checkpoint(json.loads(checkpoint_file.read_text()))
            direct.edit_after(1, "3", preference=["B", "C", "A"])
            direct.run(2)
            self.assertEqual(direct.checkpoint(), checkpoint)

            edited = root / "edited.json"
            edited.write_text(json.dumps(checkpoint))
            args = ["export", str(edited), "--csv", str(root / "metrics.csv"),
                    "--plot-svg", str(root / "plot.svg")]
            if importlib.util.find_spec("PIL"):
                args += ["--network-png", str(root / "network.png"), "--gif", str(root / "history.gif")]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            with (root / "metrics.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["winner"] for row in rows], ["A", "C", "A", "C"])
            self.assertIn("Intervention round 2", (root / "plot.svg").read_text())
            if importlib.util.find_spec("PIL"):
                from PIL import Image
                from multi_agent_election.render import _palette
                with Image.open(root / "history.gif") as gif:
                    self.assertEqual(gif.n_frames, 4)
                    gif.seek(0)
                    self.assertEqual(gif.convert("RGB").getpixel((158, 470)), _palette(2))
                    gif.seek(gif.n_frames - 1)
                    self.assertEqual(gif.size, (800, 600))
                    self.assertEqual(gif.convert("RGB").getpixel((503, 425)), _palette(1))
                with Image.open(root / "network.png") as image:
                    image.verify()


if __name__ == "__main__":
    unittest.main()
