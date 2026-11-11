import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.campaign import select_campaign_edges
from multi_agent_election.cli import main
from multi_agent_election.experiments import coalition_ablations, compare_proximity
from multi_agent_election.metrics import series
from multi_agent_election.visual import Session


def example():
    with Path("examples/campaign-controller.toml").open("rb") as handle:
        return tomllib.load(handle)


class CampaignControllerTests(unittest.TestCase):
    def test_hand_worked_controller_and_sensor_effect(self):
        sim=Simulation(make_scenario(example())); sim.run()
        frames=[f.as_dict() for f in sim.frames]
        self.assertEqual(frames[1]["campaign_controller"]["eligible"],[["1","2"],["1","3"],["4","2"],["4","3"]])
        self.assertEqual(frames[1]["campaign_controller"]["accepted"],[["1","2"]])
        self.assertEqual(frames[2]["campaign_controller"]["accepted"],[["1","3"]])
        self.assertEqual([f["campaign_controller"]["spent"] for f in frames],[0,1,2,2,2])
        self.assertEqual(frames[1]["ballots"]["2"],["B"])
        self.assertIn(["2","1","public",0,["B"]],frames[1]["ballot_sensors"])
        self.assertEqual(frames[4]["campaign_edges"],[["1","2"],["1","3"]])
        self.assertEqual([m["campaign_controller_added_count"] for m in series(sim.scenario,sim.frames)],[0,1,1,0,0])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)
        tampered=sim.checkpoint(); tampered["frames"][1]["campaign_controller"]["spent"]=0
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(tampered)
        tampered=sim.checkpoint(); tampered["version"]=14
        with self.assertRaisesRegex(ElectionError,"version 15"): Simulation.from_checkpoint(tampered)

    def test_zero_budget_none_and_candidate_cap_are_safe(self):
        raw=example(); raw["campaign_controller"]["lifetime_budget"]=0
        control=copy.deepcopy(raw); control.pop("campaign_controller")
        left,right=Simulation(make_scenario(raw)),Simulation(make_scenario(control)); left.run(); right.run()
        for a,b in zip(left.frames,right.frames):
            self.assertEqual((a.ballots,a.positions,a.campaign_edges,a.ballot_sensors),
                             (b.ballots,b.positions,b.campaign_edges,b.ballot_sensors))
        limited=example(); limited["campaign_controller"]["max_candidates"]=1
        sim=Simulation(make_scenario(limited)); before=sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"max_candidates"): sim.step()
        self.assertEqual(sim.checkpoint(),before)
        limited["campaign_controller"]["policy"]="none"
        sim=Simulation(make_scenario(limited)); sim.step()
        self.assertIsNone(sim.current.campaign_controller_eligible)
        self.assertEqual(sim.current.campaign_controller_added,())

    def test_existing_edges_are_ineligible_and_purchases_are_never_reused(self):
        raw=example(); raw["network"]["persistent_edges"]=[["1","2"],["1","3"],["2","3"]]
        raw["network"]["campaign_edges"]=[["4","2"]]
        sim=Simulation(make_scenario(raw)); first=sim.step()
        self.assertEqual(first.campaign_controller_eligible,(("4","3"),))
        self.assertEqual(first.campaign_controller_added,(("4","3"),))
        raw=example(); raw["campaign_controller"]["lifetime_budget"]=3
        raw["interventions"]=[{"round":2,"person":"1","remove_campaign_edges":["2"]},
                              {"round":2,"person":"2","ballot":["A"]}]
        sim=Simulation(make_scenario(raw)); sim.run(3)
        self.assertNotIn(("1","2"),sim.frames[3].campaign_edges)
        self.assertNotIn(("1","2"),sim.frames[3].campaign_controller_eligible)
        self.assertIn(("1","2"),sim.frames[3].campaign_controller_purchased)
        self.assertEqual(len(sim.frames[3].campaign_controller_purchased),3)
        sim.edit_after(1,"4",position=[0.95,0.95]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)

    def test_random_is_reproducible_and_selection_uses_only_public_inputs(self):
        raw=example(); raw["campaign_controller"]["policy"]="random"
        edges=[]
        for seed in range(12):
            data=copy.deepcopy(raw); data["seed"]=seed
            sim=Simulation(make_scenario(data)); first=sim.step()
            self.assertIn(first.campaign_controller_added[0],first.campaign_controller_eligible)
            self.assertEqual(first,Simulation(make_scenario(data)).step())
            edges.append(first.campaign_controller_added)
        self.assertGreater(len(set(edges)),1)
        controller=make_scenario(example()).campaign_controller
        public={"1":"B","2":"A","3":"A","4":"B"}
        eligible,chosen=select_campaign_edges(controller,public,{("2","3")},set(),None)
        self.assertEqual(chosen,(("1","2"),))
        self.assertTrue(all(public[a]=="B" and public[b]!="B" and a!=b for a,b in eligible))

    def test_validation_migration_and_experiment_guards(self):
        for change in (lambda x:x["campaign_controller"].update(policy="invented"),
                       lambda x:x["campaign_controller"].update(target="unknown"),
                       lambda x:x["campaign_controller"].update(lifetime_budget=-1),
                       lambda x:x["campaign_controller"].update(per_round_budget=True),
                       lambda x:x["campaign_controller"].update(max_candidates=1000001),
                       lambda x:x["campaign_controller"].pop("target")):
            raw=example(); change(raw)
            with self.subTest(raw=raw), self.assertRaises(ElectionError): make_scenario(raw)
        with Path("examples/certified-direct.toml").open("rb") as handle: certified=tomllib.load(handle)
        certified["campaign_controller"]=copy.deepcopy(example()["campaign_controller"])
        with self.assertRaisesRegex(ElectionError,"excludes campaign"): make_scenario(certified)
        raw=example(); scenario=make_scenario(raw)
        with self.assertRaisesRegex(ElectionError,"exclude campaign"): coalition_ablations(scenario,[1])
        with self.assertRaisesRegex(ElectionError,"excludes campaign"): compare_proximity(scenario,[1])
        raw.pop("campaign_controller"); sim=Simulation(make_scenario(raw)); sim.run(2)
        old=sim.checkpoint(); old["version"]=14
        self.assertEqual(Simulation.from_checkpoint(old).current,sim.current)

    def test_cli_session_summary_and_csv(self):
        path="examples/campaign-controller.toml"
        with Path(path).open("rb") as handle: scenario=make_scenario(tomllib.load(handle))
        sim=Simulation(scenario); session=Session(sim)
        self.assertEqual(session.snapshot()["campaign_controller"]["lifetime_budget"],2)
        for revision in range(4): session.command({"action":"step","revision":revision})
        full,summary=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(full): self.assertEqual(main(["run",path]),0)
        with contextlib.redirect_stdout(summary): self.assertEqual(main(["run",path,"--summary"]),0)
        a,b=json.loads(full.getvalue()),json.loads(summary.getvalue())
        self.assertEqual(a["metrics"],b["metrics"])
        self.assertEqual(a["frames"],session.snapshot()["frames"])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); checkpoint=root/"checkpoint.json"; checkpoint.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(["export",str(checkpoint),"--csv",str(root/"metrics.csv")]),0)
            with (root/"metrics.csv").open(newline="") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual([r["campaign_controller_spend"] for r in rows],["0","1","2","2","2"])
            self.assertEqual([r["campaign_controller_eligible_count"] for r in rows],["","4","2","",""])

    def test_http_controller_state_and_edge_trace(self):
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
        self.assertEqual(state["campaign_controller"]["policy"],"target_heuristic")
        request=Request(base+"/command",headers=headers,data=json.dumps({"action":"step","revision":0}).encode(),method="POST")
        with urlopen(request) as response: reply=json.load(response)
        self.assertEqual(reply["frame"],direct.current.as_dict())
        self.assertEqual(reply["metric"]["campaign_controller_spend"],1)


if __name__ == "__main__": unittest.main()
