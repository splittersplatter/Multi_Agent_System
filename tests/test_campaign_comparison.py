import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import compare_campaign_policies
from multi_agent_election.metrics import series


def example():
    with Path("examples/campaign-controller.toml").open("rb") as handle:
        return tomllib.load(handle)


class CampaignComparisonTests(unittest.TestCase):
    def test_matched_policies_have_same_budget_and_replayable_data(self):
        for stationary in (False,True):
            data=example()
            if stationary: data["groups"]["supporters"]["movement"]="stationary"
            scenario=make_scenario(data); result=compare_campaign_policies(scenario,[1,2])
            self.assertEqual(result["policies"],["none","random","target_heuristic"])
            for row in result["rows"]:
                runs=row["runs"]; control=runs["none"]
                for name,run in runs.items():
                    self.assertEqual(run["status"],"ok"); self.assertTrue(run["movement_matched"])
                    self.assertEqual([f["positions"] for f in run["frames"]],[f["positions"] for f in control["frames"]])
                    config=run["scenario"]["campaign_controller"]
                    self.assertEqual((config["policy"],config["target"],config["lifetime_budget"],config["per_round_budget"]),(name,"B",2,1))
                    sim=Simulation(make_scenario(run["scenario"])); sim.run()
                    self.assertEqual(run["frames"],[frame.as_dict() for frame in sim.frames])
                    self.assertEqual(run["metrics"],series(sim.scenario,sim.frames))
                    for paired,baseline,treated in zip(run["paired"],control["metrics"],run["metrics"]):
                        self.assertEqual(paired["target_win_delta"],int(treated["winner"]=="B")-int(baseline["winner"]=="B"))
                        self.assertAlmostEqual(paired["target_share_delta"],treated["shares"]["B"]-baseline["shares"]["B"])
                        self.assertEqual(paired["controller_spend"],treated["campaign_controller_spend"])
                self.assertEqual(control["paired"][-1]["target_win_delta"],0)
                self.assertEqual(runs["target_heuristic"]["paired"][-1]["target_win_delta"],1)
                self.assertEqual(runs["target_heuristic"]["paired"][-1]["target_margin_delta"],4)
            self.assertEqual(compare_campaign_policies(scenario,[1,2]),result)

    def test_zero_budget_control_and_candidate_limit_failures(self):
        data=example(); data["campaign_controller"]["lifetime_budget"]=0
        runs=compare_campaign_policies(make_scenario(data),[1])["rows"][0]["runs"]
        for run in runs.values():
            self.assertEqual([f["ballots"] for f in run["frames"]],[f["ballots"] for f in runs["none"]["frames"]])
            self.assertEqual(run["paired"][-1]["controller_spend"],0)
            self.assertEqual(run["paired"][-1]["target_win_delta"],0)
        data=example(); data["campaign_controller"]["max_candidates"]=1
        runs=compare_campaign_policies(make_scenario(data),[1])["rows"][0]["runs"]
        self.assertEqual(runs["none"]["status"],"ok")
        for policy in ("random","target_heuristic"):
            self.assertEqual((runs[policy]["status"],runs[policy]["completed_round"]),("failed",0))
            self.assertEqual(len(runs[policy]["frames"]),1)
            self.assertNotIn("paired",runs[policy])
            self.assertIn("max_candidates",runs[policy]["error"])

    def test_baseline_failure_keeps_successful_unpaired_runs(self):
        scenario=make_scenario(example()); real_step=Simulation.step
        def fail_baseline(sim):
            if sim.scenario.campaign_controller.policy == "none" and sim.current.round == 1:
                raise ElectionError("deliberate test failure")
            return real_step(sim)
        with patch.object(Simulation,"step",fail_baseline): result=compare_campaign_policies(scenario,[1])
        runs=result["rows"][0]["runs"]
        self.assertEqual((runs["none"]["status"],runs["none"]["completed_round"]),("failed",1))
        self.assertEqual(len(runs["none"]["frames"]),2)
        self.assertEqual(runs["random"]["status"],"ok")
        self.assertIsNone(runs["random"]["movement_matched"])
        self.assertNotIn("paired",runs["random"])

    def test_validation_and_cli_exclusive_output(self):
        data=example(); scenario=make_scenario(data)
        for seeds in ([],[1,1],[-1],[True]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): compare_campaign_policies(scenario,seeds)
        data=example(); data.pop("campaign_controller")
        with self.assertRaisesRegex(ElectionError,"requires a campaign_controller"): compare_campaign_policies(make_scenario(data),[1])
        data=example(); data["interventions"]=[{"round":1,"person":"1","overrides":{}}]
        with self.assertRaisesRegex(ElectionError,"excludes scheduled"): compare_campaign_policies(make_scenario(data),[1])
        data=example(); data["groups"]["supporters"]["movement"]="python:strategy_fixture:capture_sight_movement"
        with self.assertRaisesRegex(ElectionError,"built-in movement"): compare_campaign_policies(make_scenario(data),[1])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"comparison.json"; out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["compare-campaign","examples/campaign-controller.toml","--seeds","1","--output",str(path)]),0)
            self.assertEqual((json.loads(out.getvalue())["failed"],json.loads(out.getvalue())["unpaired"]),(0,0))
            saved=json.loads(path.read_text()); self.assertEqual(len(saved["rows"][0]["runs"]),3)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["compare-campaign","examples/campaign-controller.toml","--seeds","1","--output",str(path)]),2)
            self.assertEqual(json.loads(path.read_text()),saved)


if __name__ == "__main__": unittest.main()
