import csv
import io
import contextlib
import json
import tempfile
import unittest
from pathlib import Path
import importlib.util
import subprocess
import sys
import os

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.cli import main
from test_baseline import example


class ExportTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("PIL"), "install requirements-visualization.txt for PNG/GIF checks")
    def test_network_and_gif_keep_overlapping_layers_and_reciprocal_edges(self):
        from PIL import Image
        from multi_agent_election.render import network_image, export_gif
        data = example(); data["people"] = data["people"][:2]
        data["people"][0]["position"] = [0.1, 0.5]
        data["people"][1]["position"] = [0.9, 0.5]
        data["network"] = {"radius": 0.81, "persistent_edges": [["1", "2"]],
                           "campaign_edges": [["1", "2"]]}
        scenario = make_scenario(data); simulation = Simulation(scenario)
        image = network_image(scenario, simulation.current)
        expected = {281: (162, 170, 166), 287: (162, 170, 166),
                    293: (82, 111, 145), 299: (191, 102, 54)}
        for y, color in expected.items():
            self.assertEqual(image.getpixel((200, y)), color)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "overlap.gif"
            export_gif(scenario, simulation.frames, path, 1, 5)
            with Image.open(path) as gif:
                rgb = gif.convert("RGB")
                for y, color in expected.items():
                    self.assertEqual(rgb.getpixel((200, y)), color)

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "install requirements-visualization.txt for PNG/GIF checks")
    def test_network_export_arrow_points_from_sender_to_recipient(self):
        from multi_agent_election.render import network_image
        data = example()
        data["people"][0]["position"] = [0.1, 0.5]
        data["people"][1]["position"] = [0.9, 0.5]
        data["network"] = {"persistent_edges": [["1", "2"]]}
        scenario = make_scenario(data)
        image = network_image(scenario, Simulation(scenario).current)
        # The arrowhead widens near recipient 2; no reverse arrow exists near 1.
        self.assertEqual(image.getpixel((662, 288)), (82, 111, 145))
        self.assertEqual(image.getpixel((138, 288)), (255, 255, 255))
        data["network"]["campaign_edges"] = [["1", "2"]]
        scenario = make_scenario(data)
        image = network_image(scenario, Simulation(scenario).current)
        # Overlapping layers remain separate; both arrowheads point to 2.
        self.assertEqual(image.getpixel((662, 288)), (82, 111, 145))
        self.assertEqual(image.getpixel((662, 292)), (191, 102, 54))
        self.assertEqual(image.getpixel((138, 285)), (255, 255, 255))
        data["network"]["campaign_edges"] = [["2", "1"]]
        scenario = make_scenario(data)
        image = network_image(scenario, Simulation(scenario).current)
        # Reverse-direction campaign arrow widens at 1, not 2.
        self.assertEqual(image.getpixel((138, 292)), (191, 102, 54))
        self.assertEqual(image.getpixel((662, 292)), (255, 255, 255))
        self.assertEqual(image.getpixel((662, 288)), (82, 111, 145))

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "install requirements-visualization.txt for PNG/GIF checks")
    def test_metrics_and_rendered_frames(self):
        from PIL import Image
        data = example()
        data["interventions"] = [{"round": 1, "person": "2", "ballot": ["C", "A"]}]
        sim = Simulation(make_scenario(data)); sim.run(2)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"
            checkpoint.write_text(json.dumps(sim.checkpoint()))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(root/"metrics.csv"),
                                       "--plot-svg", str(root/"plot.svg"), "--plot-png", str(root/"plot.png"),
                                       "--network-png", str(root/"network.png"), "--gif", str(root/"run.gif")]), 0)
            with (root/"metrics.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([r["winner"] for r in rows], ["A", "B", "A"])
            self.assertEqual([r["count:C"] for r in rows], ["0", "1", "0"])
            self.assertIn("Intervention round 1", (root/"plot.svg").read_text())
            for name in ("plot.png", "network.png", "run.gif"):
                with Image.open(root/name) as image:
                    image.verify()
            with Image.open(root/"run.gif") as gif:
                self.assertEqual(gif.n_frames, 3)
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(root/"metrics.csv")]), 2)

    def test_svg_and_csv_require_only_standard_library(self):
        sim = Simulation(make_scenario(example())); sim.run(1)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"
            checkpoint.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(root/"out.csv"), "--plot-svg", str(root/"out.svg")]), 0)
            self.assertIn("Round 1", (root/"out.svg").read_text())

    def test_sensor_counts_export_from_recorded_history(self):
        import tomllib
        with Path("examples/sensors.toml").open("rb") as handle:
            simulation = Simulation(make_scenario(tomllib.load(handle)))
        simulation.run()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"
            checkpoint.write_text(json.dumps(simulation.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(root / "metrics.csv")]), 0)
            with (root / "metrics.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["sensor_observation_count"] for row in rows], ["0", "1", "1"])

    def test_csv_includes_rank_group_and_unavailable_values(self):
        data = example(); data["groups"]["empty:group"] = {"voting": "sincere"}
        sim = Simulation(make_scenario(data)); sim.run(1)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"; checkpoint.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(root / "metrics.csv")]), 0)
            with (root / "metrics.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["ballot_switch_rate"], "")
            self.assertEqual(rows[0]["group_size:empty%3Agroup"], "0")
            self.assertEqual(rows[0]["group_share:empty%3Agroup:A"], "")
            self.assertEqual(float(rows[0]["rank_frequency:1:A"]), 0.5)
            self.assertEqual(rows[0]["rank_count:2:A"], "1")

    def test_paired_annotations_only_mark_scheduled_treatment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); env = {**os.environ, "PYTHONPATH": "src:examples"}
            for scenario, expected in (("examples/custom.toml", False), ("examples/integrated.toml", True)):
                target = root / (Path(scenario).stem + ".svg")
                subprocess.run([sys.executable, "-m", "multi_agent_election.cli", "batch", scenario,
                                "--seeds", "1", "--target", "A", "--plot-svg", str(target)],
                               env=env, capture_output=True, text=True, check=True)
                svg = target.read_text()
                self.assertEqual("Intervention round 2" in svg, expected)
                self.assertNotIn("Intervention round 1", svg)

    def test_sampled_plot_uses_actual_round_spacing(self):
        from multi_agent_election.render import export_plot
        scenario = make_scenario(example()); sim = Simulation(scenario); sim.run(4)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plot.svg"
            export_plot(scenario, [sim.frames[i] for i in (0, 3, 4)], path, "svg")
            self.assertIn("55.00,275.00 580.00,275.00 755.00,275.00", path.read_text())

    def test_batch_comparison_csv_and_plot_match_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main(["batch", "examples/network.toml", "--seeds", "1", "2", "--target", "A", "--csv", str(root/"batch.csv"), "--plot-svg", str(root/"batch.svg")]), 0)
            result = json.loads(stream.getvalue())
            with (root/"batch.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 10)
            self.assertAlmostEqual(float(rows[-1]["target_share_delta"]), result["rows"][-1]["target_share_delta"])
            self.assertIn("Intervention round 3", (root/"batch.svg").read_text())


if __name__ == "__main__": unittest.main()
