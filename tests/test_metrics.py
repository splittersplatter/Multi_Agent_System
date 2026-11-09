import copy
import contextlib
import io
import json
import tempfile
from pathlib import Path
import unittest
from verification_support import VerificationTestCase
from dataclasses import replace
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.experiments import batch
from multi_agent_election.metrics import series
from multi_agent_election.cli import main
from test_baseline import example


class MetricTests(VerificationTestCase):
    def test_hand_computed_counts_ranks_and_margin(self):
        scenario = make_scenario(example())
        sim = Simulation(scenario); sim.run()
        row = series(scenario, sim.frames)[0]
        self.assertEqual(row["counts"], {"A": 2, "B": 2, "C": 0})
        self.assertEqual(row["shares"], {"A": 0.5, "B": 0.5, "C": 0.0})
        self.assertEqual(row["rank_counts"]["A"], [2, 1])
        self.assertEqual(row["mean_winner_rank"], 0.75)
        self.assertEqual(row["winner_margin"], 0)

    def test_missing_initial_switches_empty_groups_and_rank_frequencies(self):
        data = example(); data["groups"]["empty"] = {"voting": "sincere"}
        data["interventions"] = [{"round": 1, "person": "2", "group": "empty", "ballot": ["C", "A"]}]
        scenario = make_scenario(data); sim = Simulation(scenario); sim.run(1)
        initial, changed = series(scenario, sim.frames)
        self.assertIsNone(initial["ballot_switch_count"])
        self.assertIsNone(initial["ballot_switch_rate"])
        self.assertEqual(initial["group_sizes"]["empty"], 0)
        self.assertEqual(initial["group_counts"]["empty"], {"A": 0, "B": 0, "C": 0})
        self.assertEqual(initial["group_shares"]["empty"], {"A": None, "B": None, "C": None})
        self.assertEqual(initial["rank_frequencies"]["A"], [0.5, 0.25])
        for rank in range(scenario.k):
            self.assertAlmostEqual(sum(initial["rank_frequencies"][party][rank] for party in scenario.parties), 1)
        self.assertEqual((changed["ballot_switch_count"], changed["ballot_switch_rate"]), (1, 0.25))
        self.assertEqual(changed["group_shares"]["empty"], {"A": 0, "B": 0, "C": 1})
        self.assertEqual(changed["intervention_origin_counts"], {"interactive": 0, "policy": 0, "scheduled": 1})

    def test_switching_unavailable_across_missing_rounds(self):
        scenario = make_scenario(example()); sim = Simulation(scenario); sim.run(4)
        sparse = series(scenario, [sim.frames[0], sim.frames[3], sim.frames[4]])
        self.assertEqual([row["ballot_switch_rate"] for row in sparse], [None, None, 0])

    def test_directed_turnover_deduplicates_layers_and_handles_missing_history(self):
        scenario = make_scenario(example()); original = Simulation(scenario).current
        before = replace(original, round=1, proximity_edges=(("1","2"),("2","1")),
                         persistent_edges=(("1","2"),("3","4")))
        after = replace(original, round=2, proximity_edges=(("2","1"),("2","3")),
                        persistent_edges=(("1","2"),("3","4")), campaign_edges=(("2","1"),))
        initial, current = series(scenario, [before, after])
        self.assertIsNone(initial["proximity_edge_turnover"])
        self.assertEqual((current["proximity_edge_additions"],current["proximity_edge_removals"]), (1,1))
        self.assertAlmostEqual(current["proximity_edge_turnover"], 2/3)
        self.assertEqual((current["public_edge_additions"],current["public_edge_removals"]), (1,0))
        self.assertAlmostEqual(current["public_edge_turnover"], 1/4)
        self.assertEqual(current["proximity_mean_in_degree"], 0.5)
        gap = series(scenario, [replace(before, round=0), after])[-1]
        self.assertIsNone(gap["proximity_edge_turnover"])
        empty = replace(original, proximity_edges=(), persistent_edges=(), campaign_edges=())
        same = replace(empty, round=1)
        row = series(scenario, [empty, same])[-1]
        self.assertEqual((row["proximity_edge_turnover"],row["public_edge_turnover"]), (0,0))

    def test_intervention_origins_replay_and_legacy_projection(self):
        data = example(); data["interventions"] = [{"round": 1, "person": "2", "ballot": ["C", "A"]}]
        data["people"][0]["overrides"] = {"graph": "python:strategy_fixture:graph", "parameters": {"target": "2"}}
        sim = Simulation(make_scenario(data)); sim.edit_after(0, "3", position=[0.2, 0.2]); frame = sim.step()
        origins = {event["person"]: event["origin"] for event in frame.as_dict()["interventions"]}
        self.assertEqual(origins, {"1": "policy", "2": "scheduled", "3": "interactive"})
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, frame)
        altered = sim.checkpoint(); altered["frames"][1]["interventions"][0]["origin"] = "policy"
        with self.assertRaisesRegex(ElectionError, "history does not match"):
            Simulation.from_checkpoint(altered)
        old = sim.checkpoint(); old["version"] = 9
        for saved in old["frames"]:
            saved.pop("report_provenance")
            for event in saved["interventions"]: event.pop("origin")
        self.assertEqual(Simulation.from_checkpoint(old).current, frame)

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
