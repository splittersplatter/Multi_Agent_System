import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import coalition_ablations
from multi_agent_election.metrics import series


def example():
    with Path("examples/coalition-combined.toml").open("rb") as handle:
        return tomllib.load(handle)


class CoalitionAblationTests(VerificationTestCase):
    def test_each_arm_is_paired_and_preserves_raw_evidence(self):
        scenario=make_scenario(example()); result=coalition_ablations(scenario,[1,2])
        self.assertEqual(result["record_type"],"eclipse.coalition-ablations")
        self.assertEqual(set(result["arms"]),{"none","sight_only","deception_only","eavesdrop_only","coordination_only","all"})
        for row in result["rows"]:
            baseline=row["runs"]["none"]
            for arm,run in row["runs"].items():
                self.assertEqual(run["status"],"ok"); self.assertTrue(run["movement_matched"])
                self.assertEqual([f["positions"] for f in run["frames"]],[f["positions"] for f in baseline["frames"]])
                self.assertEqual(run["scenario"]["seed"],row["seed"])
                configured=run["scenario"]["coalitions"][0]
                self.assertEqual((configured["members"],configured["target"]),(["1"],"B"))
                for feature,field in (("sight","sight_budget_total"),("deception","report_budget_total"),("eavesdrop","eavesdrop_budget_total")):
                    self.assertEqual(configured[field] > 0,feature in result["arms"][arm])
                override=run["scenario"]["people"][0]["overrides"].get("capabilities",{})
                self.assertEqual(override.get("send_private_reports",True),"coordination" in result["arms"][arm])
                self.assertEqual(override.get("receive_private_reports",True),"coordination" in result["arms"][arm])
                sim=Simulation(make_scenario(run["scenario"])); sim.run()
                self.assertEqual(run["frames"],[f.as_dict() for f in sim.frames])
                self.assertEqual(run["metrics"],series(sim.scenario,sim.frames))
                paired=run["paired_targets"]["campaign"]; last=run["metrics"][-1]; control=baseline["metrics"][-1]
                self.assertEqual(paired["paired_target_win_delta"],int(last["winner"]=="B")-int(control["winner"]=="B"))
                self.assertAlmostEqual(paired["paired_target_share_delta"],last["shares"]["B"]-control["shares"]["B"])
            for frame in baseline["frames"]:
                self.assertFalse(frame["preference_sight"]); self.assertFalse(frame["deceptive_reports"]); self.assertFalse(frame["overheard_reports"])
                self.assertFalse(any(channel != "public" and "1" in (sender,recipient) for sender,recipient,channel,_ in frame["delivered"]))
        self.assertEqual(result["rows"][0]["runs"]["sight_only"]["paired_targets"]["campaign"]["paired_target_win_delta"],1)
        self.assertEqual(result["rows"][0]["runs"]["eavesdrop_only"]["paired_targets"]["campaign"]["paired_target_win_delta"],1)
        self.assertEqual(coalition_ablations(scenario,[1,2]),result)

    def test_fusion_deduplicates_sources_and_prefers_sighted_preference(self):
        raw=example()
        raw["people"][2]["overrides"]={"communication":"target_report"}
        raw["coalitions"].append({"id":"other","members":["3"],"target":"C",
                                  "report_budget_per_round":2,"report_budget_total":2})
        sim=Simulation(make_scenario(raw)); sim.run(2); frame=sim.current.as_dict()
        self.assertEqual(frame["overheard_reports"][0]["ballot"],["C"])
        self.assertEqual(frame["preference_sight"][0]["preference"][0],"B")
        trace=frame["policy_memory"]["1"]
        self.assertEqual(trace["sighted_first_choices"],{"3":"B"})
        self.assertNotIn("3",trace["overheard_first_choices"])
        self.assertEqual(trace["choice"],"B")

    def test_failures_are_retained_and_do_not_fabricate_paired_results(self):
        scenario=make_scenario(example()); real_step=Simulation.step
        def fail_zero(sim):
            if sim.scenario.coalitions[0].report_budget_total == 0 and sim.current.round == 1:
                raise ElectionError("deliberate test failure")
            return real_step(sim)
        with patch.object(Simulation,"step",fail_zero): result=coalition_ablations(scenario,[1])
        runs=result["rows"][0]["runs"]
        self.assertEqual((runs["none"]["status"],runs["none"]["completed_round"]),("failed",1))
        self.assertEqual(len(runs["none"]["frames"]),2)
        self.assertEqual(runs["all"]["status"],"ok")
        self.assertIsNone(runs["all"]["movement_matched"])
        self.assertNotIn("paired_targets",runs["all"])

    def test_validation_and_cli_exclusive_output(self):
        raw=example(); scenario=make_scenario(raw)
        for seeds in ([],[1,1],[-1],[True]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): coalition_ablations(scenario,seeds)
        raw=example(); raw["interventions"]=[{"round":1,"person":"1","overrides":{}}]
        with self.assertRaisesRegex(ElectionError,"exclude scheduled"): coalition_ablations(make_scenario(raw),[1])
        raw=example(); raw["groups"]["coalition"]["movement"]="python:strategy_fixture:capture_sight_movement"
        with self.assertRaisesRegex(ElectionError,"built-in movement"): coalition_ablations(make_scenario(raw),[1])
        raw=example(); raw.pop("coalitions"); raw["groups"]["coalition"].update(voting="sincere",capabilities={})
        with self.assertRaisesRegex(ElectionError,"at least one coalition"): coalition_ablations(make_scenario(raw),[1])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"ablation.json"; out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["coalition-ablations","examples/coalition-combined.toml","--seeds","1","--output",str(path)]),0)
            self.assertEqual(json.loads(out.getvalue())["failed"],0)
            saved=json.loads(path.read_text()); self.assertEqual(len(saved["rows"][0]["runs"]),6)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["coalition-ablations","examples/coalition-combined.toml","--seeds","1","--output",str(path)]),2)
            self.assertEqual(json.loads(path.read_text()),saved)


if __name__ == "__main__": unittest.main()
