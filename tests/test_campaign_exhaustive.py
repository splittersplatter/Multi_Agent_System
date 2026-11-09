import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import exhaustive_one_round_campaign, compare_campaign_policies


def example():
    with Path("examples/campaign-controller.toml").open("rb") as handle: data=tomllib.load(handle)
    data["rounds"]=1; data["groups"]["supporters"]["movement"]="stationary"
    data["campaign_controller"]["per_round_budget"]=2
    return data


class ExhaustiveCampaignTests(VerificationTestCase):
    def test_every_subset_matches_independently_scheduled_round_one_actions(self):
        data=example(); scenario=make_scenario(data); result=exhaustive_one_round_campaign(scenario)
        self.assertEqual(result["combinations_checked"],11)
        self.assertEqual(result["budget"],2)
        target_votes=[]; target_wins=[]
        for record in result["records"]:
            raw=copy.deepcopy(data); raw["campaign_controller"]["policy"]="none"
            by_sender={}
            for sender,recipient in record["edges"]: by_sender.setdefault(sender,[]).append(recipient)
            raw["interventions"]=[{"round":1,"person":sender,"add_campaign_edges":recipients}
                                  for sender,recipients in sorted(by_sender.items())]
            sim=Simulation(make_scenario(raw)); sim.step()
            self.assertEqual(record["target_votes"],dict(sim.current.counts)["B"])
            self.assertEqual(record["winner"],sim.current.winner)
            self.assertEqual(record["target_won"],sim.current.winner=="B")
            target_votes.append(dict(sim.current.counts)["B"]); target_wins.append(sim.current.winner=="B")
        self.assertEqual(result["max_target_votes"],max(target_votes))
        self.assertEqual(result["target_win_possible"],any(target_wins))
        self.assertEqual(result["max_target_votes"],3)
        self.assertTrue(result["target_win_possible"])
        matched=compare_campaign_policies(scenario,[scenario.seed])["rows"][0]["runs"]
        for run in matched.values():
            self.assertLessEqual(run["metrics"][-1]["counts"]["B"],result["max_target_votes"])
            self.assertLessEqual(int(run["metrics"][-1]["winner"]=="B"),int(result["target_win_possible"]))

    def test_zero_budget_limits_and_domain_guards(self):
        data=example(); data["campaign_controller"]["lifetime_budget"]=0
        result=exhaustive_one_round_campaign(make_scenario(data))
        self.assertEqual((result["combinations_checked"],result["budget"]),(1,0))
        self.assertEqual(result["records"][0]["edges"],[])
        self.assertIsNone(result["eligible"])
        limited=example(); limited["campaign_controller"]["per_round_budget"]=1
        self.assertEqual(exhaustive_one_round_campaign(make_scenario(limited))["combinations_checked"],5)
        impossible=example()
        for person in impossible["people"]: person["preference"]=["A","B"]
        no_win=exhaustive_one_round_campaign(make_scenario(impossible))
        self.assertFalse(no_win["target_win_possible"]); self.assertIsNone(no_win["target_win_witness"])
        self.assertEqual(no_win["eligible"],[])
        capped=example(); capped["campaign_controller"]["max_candidates"]=1
        with self.assertRaisesRegex(ElectionError,"max_candidates"): exhaustive_one_round_campaign(make_scenario(capped))
        with self.assertRaisesRegex(ElectionError,"max_combinations"):
            exhaustive_one_round_campaign(make_scenario(example()),10)
        for invalid in (0,True,100001):
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError): exhaustive_one_round_campaign(make_scenario(example()),invalid)
        changes=[lambda x:x.update(rounds=2),
                 lambda x:x["groups"]["supporters"].update(movement="random_walk"),
                 lambda x:x.update(interventions=[{"round":1,"person":"1","ballot":["A"]}]),
                 lambda x:x["groups"]["supporters"].update(voting="python:strategy_fixture:vote"),
                 lambda x:x.pop("campaign_controller")]
        for change in changes:
            data=example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): exhaustive_one_round_campaign(make_scenario(data))

    def test_cli_output_is_replayable_and_non_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); scenario=Path("examples/campaign-exhaustive.toml"); output=root/"out.json"
            out=io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(main(["campaign-exhaustive",str(scenario),"--output",str(output)]),0)
            self.assertEqual(json.loads(out.getvalue())["combinations_checked"],11)
            saved=json.loads(output.read_text()); self.assertEqual(len(saved["records"]),11)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["campaign-exhaustive",str(scenario),"--output",str(output)]),2)
            self.assertEqual(json.loads(output.read_text()),saved)


if __name__ == "__main__": unittest.main()
