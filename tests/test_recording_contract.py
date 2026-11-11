import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.provenance import manifest
from test_baseline import example


class RecordingContractTests(unittest.TestCase):
    def test_run_preflights_aliased_outputs_before_constructing_simulation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "sub").mkdir()
            target, alias = root / "run.json", root / "sub" / ".." / "run.json"
            with patch("multi_agent_election.cli.Simulation") as constructor, contextlib.redirect_stderr(io.StringIO()):
                status = main(["run", "examples/baseline.toml", "--checkpoint", str(target), "--jsonl", str(alias)])
            self.assertEqual(status, 2)
            constructor.assert_not_called()
            self.assertFalse(target.exists())

    def test_batch_and_export_preflight_all_outputs_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            simulation = Simulation(make_scenario(example())); simulation.run()
            checkpoint = root / "input.json"; checkpoint.write_text(json.dumps(simulation.checkpoint()))
            for command in ("batch", "export"):
                csv_file = root / (command + ".csv")
                args = (["batch", "examples/network.toml", "--seeds", "1", "--target", "A"]
                        if command == "batch" else ["export", str(checkpoint)])
                args += ["--csv", str(csv_file), "--plot-svg", str(root / "missing" / "plot.svg")]
                with self.subTest(command=command), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(args), 2)
                self.assertFalse(csv_file.exists())

    def test_existing_and_dangling_symlinks_never_get_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); original = root / "original"; original.write_text("keep")
            existing, dangling = root / "link", root / "dangling"
            try:
                existing.symlink_to(original); dangling.symlink_to(root / "missing")
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            for path in (existing, dangling):
                with self.subTest(path=path), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["run", "examples/baseline.toml", "--checkpoint", str(path)]), 2)
            self.assertEqual(original.read_text(), "keep")
            self.assertTrue(dangling.is_symlink())
            self.assertFalse((root / "missing").exists())

    def test_distinct_spellings_through_symlinked_parent_cannot_share_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); alias = root / "alias"
            try:
                alias.symlink_to(root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            output = root / "same"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["batch", "examples/network.toml", "--seeds", "1", "--target", "A",
                                       "--csv", str(output), "--plot-svg", str(alias / "same")]), 2)
            self.assertFalse(output.exists())

    def test_resume_cannot_overwrite_its_input_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "checkpoint.json"
            sim = Simulation(make_scenario(example())); sim.run(1)
            checkpoint.write_text(json.dumps(sim.checkpoint()))
            original = checkpoint.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["resume", str(checkpoint), "--rounds", "1", "--output", str(checkpoint)]), 2)
            self.assertEqual(checkpoint.read_bytes(), original)

    def test_record_modes_and_resume_preserve_integrated_history(self):
        env = {**os.environ, "PYTHONPATH": "src:examples", "PYTHONDONTWRITEBYTECODE": "1"}
        def cli(*args):
            result = subprocess.run([sys.executable, "-m", "multi_agent_election.cli", *args],
                                    env=env, check=True, capture_output=True, text=True)
            return json.loads(result.stdout)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint, jsonl = root / "run.json", root / "run.jsonl"
            full = cli("run", "examples/integrated.toml")
            summary = cli("run", "examples/integrated.toml", "--summary")
            sampled = cli("run", "examples/integrated.toml", "--sample", "2",
                          "--checkpoint", str(checkpoint), "--jsonl", str(jsonl))
            for output in (full, summary, sampled):
                self.assertEqual((output["record_type"], output["record_version"]), ("eclipse.run", 2))
                self.assertEqual(output["manifest"]["manifest_version"], 1)
                self.assertTrue(output["manifest"]["pipeline_sha256"])
                self.assertEqual(output["metrics"], full["metrics"])
            self.assertNotIn("frames", summary)
            self.assertEqual([frame["round"] for frame in sampled["frames"]], [0, 2, 3])
            self.assertEqual(sampled["frames"], [full["frames"][i] for i in (0, 2, 3)])
            self.assertEqual(json.loads(checkpoint.read_text())["frames"], full["frames"])
            records = [json.loads(line) for line in jsonl.read_text().splitlines()]
            self.assertEqual((records[0]["record_type"], records[0]["record_version"]), ("eclipse.run", 2))
            self.assertEqual([record["data"] for record in records if record["type"] == "metrics"], full["metrics"])
            self.assertEqual([record["data"] for record in records if record["type"] == "frame"], sampled["frames"])
            resumed = cli("resume", str(checkpoint), "--rounds", "2", "--output", str(root / "resumed.json"))
            with Path("examples/integrated.toml").open("rb") as handle:
                scenario = make_scenario(tomllib.load(handle))
            examples_path = str(Path("examples").resolve()); sys.path.insert(0, examples_path)
            self.addCleanup(lambda: sys.path.remove(examples_path))
            direct = Simulation(scenario); direct.run(5)
            self.assertEqual(resumed["frames"], [frame.as_dict() for frame in direct.frames])
            self.assertEqual(resumed["frames"], json.loads((root / "resumed.json").read_text())["frames"])

    def test_pipeline_fingerprint_and_migration_are_explicit(self):
        from pathlib import Path as ConcretePath
        original_read = ConcretePath.read_bytes
        baseline = manifest()
        def changed(path):
            data = original_read(path)
            return data + b"\n# changed" if path.name == "experiments.py" else data
        with patch.object(ConcretePath, "read_bytes", changed):
            altered = manifest()
        self.assertEqual(baseline["core_sha256"], altered["core_sha256"])
        self.assertNotEqual(baseline["pipeline_sha256"], altered["pipeline_sha256"])
        sim = Simulation(make_scenario(example())); sim.run(2); checkpoint = sim.checkpoint()
        with patch("multi_agent_election.engine.manifest", return_value=altered):
            with self.assertRaisesRegex(ElectionError, "runtime or core source changed"):
                Simulation.from_checkpoint(checkpoint)
            restored = Simulation.from_checkpoint(checkpoint, allow_environment_change=True)
            self.assertEqual(restored.current, sim.current)
            self.assertEqual(restored.checkpoint()["manifest"], altered)

    def test_batch_has_versioned_record_and_seeded_rows(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["batch", "examples/network.toml", "--seeds", "3", "7", "--target", "A"]), 0)
        result = json.loads(out.getvalue())
        self.assertEqual((result["record_type"], result["record_version"]), ("eclipse.batch", 2))
        self.assertEqual(result["manifest"]["manifest_version"], 1)
        self.assertEqual(result["manifest"]["rng_schema"], "actor-round-phase-v1")
        self.assertEqual([row["seed"] for row in result["rows"]], [3, 7])

    def test_voting_rng_draws_do_not_change_movement_stream(self):
        data = example()
        data["groups"]["residents"].update(movement="random_walk", max_step=0.2)
        original = Simulation(make_scenario(data)); original.run(4)
        data["groups"]["residents"]["voting"] = "python:strategy_fixture:rng_burn"
        changed = Simulation(make_scenario(data)); changed.run(4)
        self.assertEqual([frame.positions for frame in original.frames], [frame.positions for frame in changed.frames])
        self.assertEqual([frame.ballots for frame in original.frames], [frame.ballots for frame in changed.frames])

    def test_one_agents_draws_and_input_order_do_not_change_other_agents_streams(self):
        data = example()
        data["groups"]["residents"]["voting"] = "python:strategy_fixture:rng_echo"
        first = Simulation(make_scenario(data)); first.run(3)
        data["people"][0]["overrides"] = {"voting": "python:strategy_fixture:rng_burn"}
        data["people"].reverse()
        second = Simulation(make_scenario(data)); second.run(3)
        for a, b in zip(first.frames, second.frames):
            am, bm = a.as_dict()["policy_memory"], b.as_dict()["policy_memory"]
            for person in ("2", "3", "4"):
                self.assertEqual(am[person], bm[person])
            self.assertEqual(dict(a.ballots), dict(b.ballots))


if __name__ == "__main__":
    unittest.main()
