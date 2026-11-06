import copy
import contextlib
import io
import json
import tempfile
from pathlib import Path
import unittest
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.experiments import batch
from multi_agent_election.metrics import series
from multi_agent_election.cli import main
from test_baseline import example


class MetricTests(unittest.TestCase):
    def test_hand_computed_counts_ranks_and_margin(self):
        scenario = make_scenario(example())
        sim = Simulation(scenario); sim.run()
        row = series(scenario, sim.frames)[0]
        self.assertEqual(row["counts"], {"A": 2, "B": 2, "C": 0})
        self.assertEqual(row["shares"], {"A": 0.5, "B": 0.5, "C": 0.0})
        self.assertEqual(row["rank_counts"]["A"], [2, 1])
        self.assertEqual(row["mean_winner_rank"], 0.75)
        self.assertEqual(row["winner_margin"], 0)

    def test_matched_zero_and_effect(self):
        data = example()
        no_attack = batch(make_scenario(data), [1, 2], "B")
        self.assertEqual(no_attack["winner_change_rate"], 0)
        self.assertEqual(no_attack["mean_target_share_delta"], 0)
        data["interventions"] = [{"round": 1, "person": "2", "preference": ["C", "A", "B"]}]
        changed = batch(make_scenario(data), [1, 2], "B")
        self.assertEqual(changed["winner_change_rate"], 1)
        self.assertEqual(changed["mean_target_share_delta"], 0)
        self.assertEqual(changed["control_target_win_rate"], 0)
        self.assertEqual(changed["treated_target_win_rate"], 1)
        self.assertEqual(changed["mean_target_margin_delta"], 1)
        self.assertEqual(changed["rows"][0]["treated"][1]["ballot_switch_rate"], 0.25)
        for seeds in ([], [1, 1], [-1], [True]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError):
                batch(make_scenario(data), seeds, "A")
        with self.assertRaises(ElectionError): batch(make_scenario(data), [1], "unknown")

    def test_summary_stream_matches_full_metrics(self):
        full, summary = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(full): self.assertEqual(main(["run", "examples/network.toml"]), 0)
        with contextlib.redirect_stdout(summary): self.assertEqual(main(["run", "examples/network.toml", "--summary"]), 0)
        self.assertEqual(json.loads(full.getvalue())["metrics"], json.loads(summary.getvalue())["metrics"])
        self.assertNotIn("frames", json.loads(summary.getvalue()))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["run", "examples/network.toml", "--summary", "--checkpoint", "/tmp/unused-checkpoint.json"]), 2)

    def test_sampled_recording_retains_end_and_full_metrics(self):
        full, sampled = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(full): main(["run", "examples/network.toml"])
        with contextlib.redirect_stdout(sampled): main(["run", "examples/network.toml", "--sample", "3"])
        a, b = json.loads(full.getvalue()), json.loads(sampled.getvalue())
        self.assertEqual([f["round"] for f in b["frames"]], [0, 3, 4])
        self.assertEqual(b["frames"], [a["frames"][i] for i in (0, 3, 4)])
        self.assertEqual(a["metrics"], b["metrics"])
        self.assertEqual(b["recording"], "sampled")

    def test_jsonl_summary_and_sampled_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            for option, expected_frames in (("--summary", 0), ("--sample", 3)):
                output = Path(folder) / option[2:]
                args = ["run", "examples/network.toml", option]
                if option == "--sample": args.append("3")
                args += ["--jsonl", str(output)]
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(args), 0)
                records = [json.loads(line) for line in output.read_text().splitlines()]
                self.assertEqual(records[0]["type"], "manifest")
                self.assertEqual(sum(r["type"] == "metrics" for r in records), 5)
                self.assertEqual(sum(r["type"] == "frame" for r in records), expected_frames)


if __name__ == "__main__": unittest.main()
