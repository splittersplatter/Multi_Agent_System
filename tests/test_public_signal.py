import contextlib
import copy
import csv
import io
import itertools
import json
from pathlib import Path
import random
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.metrics import series
from multi_agent_election.model import SignalController
from multi_agent_election.signals import generate_signal, trusting_response
from multi_agent_election.visual import Session


def example():
    with Path("examples/public-signal.toml").open("rb") as handle:
        return tomllib.load(handle)


class PublicSignalTests(VerificationTestCase):
    def test_report_cost_integrality_and_budget_invariants(self):
        parties=("A","B","C")
        for policy in ("truthful","target_biased","bounded_random"):
            for truth in ((0,0,0),(2,1,1),(0,4,0),(1,0,5)):
                for cap in range(5):
                    controller=SignalController("B",policy,"repeated",cap,7)
                    for remaining in range(5):
                        report,cost=generate_signal(controller,parties,truth,remaining,random.Random(812))
                        self.assertTrue(all(type(n) is int and n>=0 for n in report))
                        self.assertEqual(sum(report),sum(truth))
                        self.assertEqual(cost,sum(abs(a-b) for a,b in zip(truth,report))//2)
                        self.assertLessEqual(cost,min(cap,remaining))
                        if policy == "truthful": self.assertEqual(report,truth)
                        if policy == "target_biased": self.assertGreaterEqual(report[1],truth[1])
        ctrl=SignalController("B","target_biased","repeated",1,2)
        self.assertEqual(generate_signal(ctrl,parties,(2,1,1),2,random.Random(1)),((1,2,1),1))
        self.assertEqual(generate_signal(ctrl,("A",),(4,),2,random.Random(1)),((4,),0))

    def test_trusting_response_matches_independent_ballot_oracle(self):
        parties=("A","B","C")
        for reported in itertools.product(range(4),repeat=3):
            if not 1 <= sum(reported) <= 5: continue
            for pref in itertools.permutations(parties):
                for current in parties:
                    actual,trace=trusting_response(parties,pref,(current,),(0,1,reported))
                    if reported[parties.index(current)]==0:
                        self.assertEqual((actual,trace["status"]),((current,),"inconsistent_own_ballot")); continue
                    others=list(reported); others[parties.index(current)]-=1
                    def winner(choice):
                        scores=[n+int(p==choice) for p,n in zip(parties,others)]
                        return parties[scores.index(max(scores))]
                    before=winner(current); outcomes={winner(choice) for choice in parties}
                    best=min(outcomes,key=pref.index)
                    expected=best if pref.index(best)<pref.index(before) else current
                    self.assertEqual(actual,(expected,))

    def test_repeated_signal_timing_cost_and_replay(self):
        sim=Simulation(make_scenario(example())); sim.run(); frames=[f.as_dict() for f in sim.frames]
        self.assertEqual([f["public_signal"]["spend"] for f in frames],[0,1,2,2,2])
        self.assertEqual([f["public_signal"]["broadcast_cost"] for f in frames],[None,1,1,0,0])
        self.assertEqual(frames[1]["public_signal"]["latest"],{"source_round":0,"broadcast_round":1,
                          "report":[1,2,1],"source_truth":[2,1,1]})
        self.assertEqual(frames[1]["ballots"]["4"],["A"])
        self.assertEqual(frames[1]["policy_memory"]["4"]["status"],"trusting_report")
        for n in range(1,len(frames)):
            self.assertEqual(frames[n]["public_signal"]["latest"]["source_truth"],
                             [frames[n-1]["counts"][p] for p in ("A","B","C")])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)
        altered=sim.checkpoint(); altered["frames"][1]["public_signal"]["latest"]["report"][0]=2
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(altered)
        altered=sim.checkpoint(); altered["version"]=15
        with self.assertRaisesRegex(ElectionError,"version 16"): Simulation.from_checkpoint(altered)
        sim.edit_after(1,"3",ballot=["C"]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)

    def test_initial_schedule_staleness_and_boundary_timing(self):
        data=example(); data["signal_controller"]["schedule"]="initial"
        data["interventions"]=[{"round":1,"person":"3","ballot":["C"]}]
        sim=Simulation(make_scenario(data)); sim.run(3); frames=[f.as_dict() for f in sim.frames]
        self.assertEqual([f["public_signal"]["broadcast_cost"] for f in frames],[None,1,None,None])
        self.assertEqual(frames[1]["public_signal"]["latest"]["source_truth"],[2,1,1])
        self.assertEqual(frames[1]["ballots"]["3"],["C"])
        self.assertEqual(frames[3]["public_signal"]["latest"],frames[1]["public_signal"]["latest"])
        self.assertTrue(frames[2]["policy_memory"]["4"]["stale"])
        data["signal_controller"]["schedule"]="repeated"
        sim=Simulation(make_scenario(data)); sim.run(2)
        self.assertEqual(sim.current.signal_latest[3],tuple(dict(sim.frames[1].counts)[p] for p in sim.scenario.parties))

    def test_zero_distortion_and_random_reproducibility(self):
        data=example(); data["signal_controller"]["lifetime_budget"]=0
        truthful=copy.deepcopy(data); truthful["signal_controller"]["policy"]="truthful"
        left,right=Simulation(make_scenario(data)),Simulation(make_scenario(truthful)); left.run(); right.run()
        self.assertEqual(left.frames,right.frames)
        data=example(); data["signal_controller"]["policy"]="bounded_random"
        self.assertEqual(Simulation(make_scenario(data)).run(),Simulation(make_scenario(data)).run())

    def test_signal_scope_excludes_truth_and_earlier_phases(self):
        data=example(); data["groups"]["signal_voter"].update(voting="python:strategy_fixture:capture_public_signal",
                        movement="python:strategy_fixture:capture_signal_movement")
        data["groups"]["residents"]["voting"]="python:strategy_fixture:capture_public_signal"
        sim=Simulation(make_scenario(data)); sim.step(); frame=sim.current.as_dict()
        self.assertEqual(frame["policy_memory"]["4"]["signal"],[0,1,[1,2,1]])
        self.assertIsNone(frame["policy_memory"]["1"]["signal"])
        self.assertIsNone(frame["phase_memory"][0][2]["signal"])
        self.assertNotIn("source_truth",frame["policy_memory"]["4"])

    def test_validation_and_revocation_are_atomic(self):
        changes=[lambda x:x["signal_controller"].update(target="missing"),
                 lambda x:x["signal_controller"].update(policy="unsupported"),
                 lambda x:x["signal_controller"].update(schedule="later"),
                 lambda x:x["signal_controller"].update(per_broadcast_budget=-1),
                 lambda x:x["signal_controller"].update(lifetime_budget=True),
                 lambda x:x["groups"]["signal_voter"].update(capabilities={}),
                 lambda x:x.pop("signal_controller")]
        for change in changes:
            data=example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        sim=Simulation(make_scenario(example())); sim.step()
        sim.edit_after(1,"4",overrides={"capabilities":{"observe_public_signal":False}}); before=sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"public-signal permission"): sim.step()
        self.assertEqual(before,sim.checkpoint())
        with Path("examples/certified-direct.toml").open("rb") as handle: certified=tomllib.load(handle)
        certified["signal_controller"]=copy.deepcopy(example()["signal_controller"])
        with self.assertRaisesRegex(ElectionError,"excludes public-signal"): make_scenario(certified)

    def test_cli_summary_session_csv_and_legacy(self):
        data=example(); sim=Simulation(make_scenario(data)); session=Session(sim)
        self.assertEqual(session.snapshot()["signal_controller"]["schedule"],"repeated")
        for revision in range(4): session.command({"action":"step","revision":revision})
        full,summary=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(full): self.assertEqual(main(["run","examples/public-signal.toml"]),0)
        with contextlib.redirect_stdout(summary): self.assertEqual(main(["run","examples/public-signal.toml","--summary"]),0)
        a,b=json.loads(full.getvalue()),json.loads(summary.getvalue())
        self.assertEqual(a["frames"],session.snapshot()["frames"]); self.assertEqual(a["metrics"],b["metrics"])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path=root/"checkpoint.json"; path.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(["export",str(path),"--csv",str(root/"out.csv")]),0)
            with (root/"out.csv").open(newline="") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual([r["signal_spend"] for r in rows],["0","1","2","2","2"])
            self.assertEqual([r["signal_report:B"] for r in rows],["","2","2","1","1"])
            self.assertEqual([r["signal_truth:B"] for r in rows],["","1","1","1","1"])
        with Path("examples/campaign-controller.toml").open("rb") as handle: legacy=Simulation(make_scenario(tomllib.load(handle)))
        legacy.run(2); old=legacy.checkpoint(); old["version"]=15
        for group in old["scenario"]["groups"].values(): group["capabilities"].pop("observe_public_signal")
        self.assertEqual(Simulation.from_checkpoint(old).current,legacy.current)

    def test_cumulative_coalition_campaign_and_signal_remain_separate(self):
        with Path("examples/coalition-combined.toml").open("rb") as handle: data=tomllib.load(handle)
        data["campaign_controller"]={"target":"B","policy":"target_heuristic","lifetime_budget":1,"per_round_budget":1}
        data["signal_controller"]=copy.deepcopy(example()["signal_controller"])
        data["groups"]["listener"].update(voting="signal_confident",capabilities={"observe_public_signal":True})
        sim=Simulation(make_scenario(data)); sim.run(3); first=sim.frames[1].as_dict()
        self.assertEqual(first["campaign_controller"]["spent"],1)
        self.assertEqual(first["coalition_sight_spend"]["campaign"],1)
        self.assertEqual(first["public_signal"]["spend"],1)
        self.assertNotIn("source_truth",first["policy_memory"]["2"])
        self.assertEqual(first["policy_memory"]["2"]["report"],first["public_signal"]["latest"]["report"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)
        self.assertNotIn("convergence",series(sim.scenario,sim.frames)[-1])

    def test_http_signal_status_and_step(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario=make_scenario(example()); direct=Simulation(scenario); direct.step()
        server=make_server(Simulation(scenario)); worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
        self.addCleanup(worker.join,2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base=f"http://127.0.0.1:{server.server_port}"
        with urlopen(base+"/") as response: html=response.read().decode()
        token=html.split('name="session-token" content="')[1].split('"')[0]
        headers={"X-Session-Token":token,"Content-Type":"application/json"}
        with urlopen(Request(base+"/state",headers=headers)) as response: state=json.load(response)
        self.assertEqual(state["signal_controller"]["policy"],"target_biased")
        request=Request(base+"/command",headers=headers,data=json.dumps({"action":"step","revision":0}).encode(),method="POST")
        with urlopen(request) as response: reply=json.load(response)
        self.assertEqual(reply["frame"],direct.current.as_dict())
        self.assertEqual(reply["metric"]["signal_report"],{"A":1,"B":2,"C":1})


if __name__ == "__main__": unittest.main()
