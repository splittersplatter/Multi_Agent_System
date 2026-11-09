import unittest
from verification_support import VerificationTestCase
import importlib
import os
import py_compile
import sys
import tempfile
from pathlib import Path
from uuid import uuid4
from multi_agent_election import ElectionError, Simulation, make_scenario
from test_baseline import example


class PluginTests(VerificationTestCase):
    def test_policy_initialization_failure_is_actionable_and_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            module = "policy_" + uuid4().hex
            path = Path(directory) / (module + ".py")
            path.write_text("raise RuntimeError('missing policy resource')\n")
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            self.addCleanup(lambda: sys.modules.pop(module, None))
            importlib.invalidate_caches()
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{module}:vote"
            with self.assertRaisesRegex(ElectionError, "missing policy resource"):
                Simulation(make_scenario(data))
            self.assertNotIn(module, sys.modules)
            path.write_text("def vote(obs, params, memory, rng):\n    return {'ballot': list(obs.own_preference[:obs.k]), 'memory': None}\n")
            self.assertEqual(dict(Simulation(make_scenario(data)).step().ballots)["1"], ("A", "B"))

    def test_module_initialization_can_import_on_another_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            module, dependency = ("policy_" + uuid4().hex for _ in range(2))
            (Path(directory) / (dependency + ".py")).write_text("VALUE = 1\n")
            (Path(directory) / (module + ".py")).write_text(
                "import importlib, threading\n"
                f"worker = threading.Thread(target=lambda: importlib.import_module('{dependency}'))\n"
                "worker.start()\nworker.join(2)\n"
                "if worker.is_alive(): raise RuntimeError('import blocked')\n"
                "def vote(obs, params, memory, rng):\n"
                "    return {'ballot': list(obs.own_preference[:obs.k]), 'memory': None}\n")
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            for name in (module, dependency):
                self.addCleanup(lambda n=name: sys.modules.pop(n, None))
            importlib.invalidate_caches()
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{module}:vote"
            self.assertEqual(dict(Simulation(make_scenario(data)).step().ballots)["1"], ("A", "B"))

    def test_source_policy_supports_package_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            package = "policy_" + uuid4().hex
            path = Path(directory) / package
            path.mkdir()
            (path / "__init__.py").write_text("")
            (path / "helper.py").write_text("CHOICE = 'C'\n")
            (path / "voter.py").write_text(
                "from .helper import CHOICE\n"
                "def vote(obs, params, memory, rng):\n"
                "    return {'ballot': [CHOICE, 'A'], 'memory': None}\n")
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            for name in (package, package + ".voter", package + ".helper"):
                self.addCleanup(lambda n=name: sys.modules.pop(n, None))
            importlib.invalidate_caches()
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{package}.voter:vote"
            self.assertEqual(dict(Simulation(make_scenario(data)).step().ballots)["1"], ("C", "A"))

    def test_policy_import_compiles_source_not_stale_timestamp_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            module = "policy_" + uuid4().hex
            path = Path(directory) / (module + ".py")
            template = "def vote(obs, params, memory, rng):\n    return {{'ballot': ['{}', 'A'], 'memory': None}}\n"
            path.write_text(template.format("B"))
            original_stat = path.stat()
            py_compile.compile(str(path), doraise=True)
            path.write_text(template.format("C"))
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            self.addCleanup(lambda: sys.modules.pop(module, None))
            importlib.invalidate_caches()
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{module}:vote"
            self.assertEqual(dict(Simulation(make_scenario(data)).step().ballots)["1"], ("C", "A"))

    def test_changed_cached_source_cannot_be_misidentified_as_new_code(self):
        with tempfile.TemporaryDirectory() as directory:
            module = "policy_" + uuid4().hex
            path = Path(directory) / (module + ".py")
            source = "def vote(obs, params, memory, rng):\n    return {'ballot': list(obs.own_preference[:obs.k]), 'memory': None}\n"
            path.write_text(source)
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            self.addCleanup(lambda: sys.modules.pop(module, None))
            importlib.invalidate_caches()
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{module}:vote"
            first = Simulation(make_scenario(data))
            first.step()
            path.write_text(source + "\n# changed while module remains cached\n")
            before = first.current
            with self.assertRaisesRegex(ElectionError, "policy source changed"):
                first.step()
            self.assertEqual(first.current, before)
            with self.assertRaisesRegex(ElectionError, "cached policy source changed"):
                Simulation(make_scenario(data))
            path.write_text(source)
            self.assertEqual(Simulation(make_scenario(data)).step(), before)

    def test_preimported_policy_module_cannot_claim_verified_source(self):
        with tempfile.TemporaryDirectory() as directory:
            module = "policy_" + uuid4().hex
            (Path(directory) / (module + ".py")).write_text("def vote(*args): return {}\n")
            sys.path.insert(0, directory)
            self.addCleanup(lambda: sys.path.remove(directory))
            self.addCleanup(lambda: sys.modules.pop(module, None))
            importlib.invalidate_caches()
            importlib.import_module(module)
            data = example()
            data["groups"]["residents"]["voting"] = f"python:{module}:vote"
            with self.assertRaisesRegex(ElectionError, "imported outside the policy loader"):
                Simulation(make_scenario(data))

    def test_scoped_observations_separate_memory_and_checkpoint(self):
        data = example()
        data["groups"]["residents"].update(voting="python:strategy_fixture:vote", parameters={"choice": "C"})
        sim = Simulation(make_scenario(data)); first = sim.step()
        self.assertTrue(all(ballot[0] == "C" for _, ballot in first.ballots))
        self.assertEqual(first.as_dict()["policy_memory"]["1"], {"calls": 1})
        self.assertEqual(first.as_dict()["policy_memory"]["2"], {"calls": 1})
        resumed = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), resumed.step())
        self.assertEqual(sim.current.as_dict()["policy_memory"]["1"], {"calls": 2})
        tampered = sim.checkpoint(); tampered["policy_digests"]["python:strategy_fixture:vote"] = "0" * 64
        with self.assertRaises(ElectionError): Simulation.from_checkpoint(tampered)

    def test_invalid_policy_output_fails_without_committing(self):
        for function in ("invalid", "invalid_ballot", "illegal_mutation"):
            data = example(); data["groups"]["residents"]["voting"] = f"python:strategy_fixture:{function}"
            sim = Simulation(make_scenario(data)); before = sim.checkpoint()
            with self.subTest(function=function), self.assertRaisesRegex(ElectionError, "person.*round 1.*voting"):
                sim.step()
            self.assertEqual(sim.checkpoint(), before)

    def test_unknown_or_malformed_policy_fails(self):
        data = example(); data["groups"]["residents"]["voting"] = "python:absent_module:vote"
        with self.assertRaises(ElectionError): Simulation(make_scenario(data))

    def test_agent_overrides_can_change_policy_and_be_cleared(self):
        data = example()
        data["people"][0]["overrides"] = {"voting": "python:strategy_fixture:vote", "parameters": {"choice": "C"}}
        sim = Simulation(make_scenario(data)); first = sim.step()
        self.assertEqual(dict(first.ballots)["1"], ("C", "A"))
        self.assertEqual(dict(first.ballots)["2"], ("A", "C"))
        sim.edit_after(1, "1", overrides={})
        self.assertEqual(dict(sim.step().ballots)["1"], ("A", "B"))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_manual_plugin_override_loads_and_restores(self):
        sim = Simulation(make_scenario(example()))
        sim.edit_after(0, "1", overrides={"voting": "python:strategy_fixture:vote", "parameters": {"choice": "C"}})
        restored = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), restored.step())
        self.assertEqual(dict(sim.current.ballots)["1"], ("C", "A"))

    def test_unobserved_ranking_change_does_not_leak(self):
        first, second = example(), example()
        first["k"] = second["k"] = 1
        for data in (first, second):
            data["people"][0]["overrides"] = {"voting": "python:strategy_fixture:observe"}
            data["groups"]["residents"]["communication"] = "truthful"
            data["network"] = {"persistent_edges": [["2", "1"]]}
        second["people"][1]["preference"] = ["A", "B", "C"]
        a, b = Simulation(make_scenario(first)), Simulation(make_scenario(second))
        a.run(2); b.run(2)
        self.assertEqual(dict(a.current.ballots)["1"], dict(b.current.ballots)["1"])
        self.assertEqual(a.current.as_dict()["policy_memory"]["1"], b.current.as_dict()["policy_memory"]["1"])

    def test_movement_graph_and_communication_plugins_are_replayable(self):
        data = example()
        data["people"][0]["overrides"] = {
            "movement": "python:strategy_fixture:move", "max_step": 0.1,
            "graph": "python:strategy_fixture:graph", "communication": "python:strategy_fixture:communicate",
            "parameters": {"target": "2"},
        }
        sim = Simulation(make_scenario(data)); frame = sim.step()
        self.assertAlmostEqual(dict(frame.positions)["1"][0], 0.55)
        self.assertIn(("1", "2"), frame.persistent_edges)
        self.assertIn(("1", "2", "public", ("A", "B")), frame.pending)
        self.assertEqual({(person, phase) for person, phase, _ in frame.phase_memory},
                         {("1", "movement"), ("1", "graph"), ("1", "communication")})
        resumed = Simulation.from_checkpoint(sim.checkpoint())
        self.assertEqual(sim.step(), resumed.step())
        self.assertIn(("1", "2", "public", ("A", "B")), sim.current.delivered)

    def test_invalid_phase_plugins_leave_state_uncommitted(self):
        for phase, reference in (("movement", "teleport"), ("graph", "bad_graph"), ("communication", "bad_communication")):
            data = example(); data["people"][0]["overrides"] = {phase: f"python:strategy_fixture:{reference}", "max_step": 0.1}
            sim = Simulation(make_scenario(data)); before = sim.checkpoint()
            with self.subTest(phase=phase), self.assertRaisesRegex(ElectionError, phase): sim.step()
            self.assertEqual(sim.checkpoint(), before)


if __name__ == "__main__": unittest.main()
