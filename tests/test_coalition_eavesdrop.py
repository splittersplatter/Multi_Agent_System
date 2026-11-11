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
from multi_agent_election.cli import main
from multi_agent_election.metrics import series
from multi_agent_election.visual import Session


def example():
    with Path("examples/coalition-eavesdrop.toml").open("rb") as handle:
        return tomllib.load(handle)


class EavesdropTests(unittest.TestCase):
    def test_private_packet_delay_budget_and_replay(self):
        sim=Simulation(make_scenario(example())); sim.run()
        frames=[f.as_dict() for f in sim.frames]
        self.assertEqual([f["coalition_eavesdrop_spend"]["campaign"] for f in frames],[0,0,1,2,2])
        self.assertEqual([f["ballots"]["1"] for f in frames],[["A"],["A"],["B"],["B"],["A"]])
        self.assertEqual(frames[2]["overheard_reports"],[{"coalition":"campaign","observer":"1","sender":"2",
                         "recipient":"3","channel":"team","ballot":["B"],"reference_round":0,
                         "generated_round":1,"intercepted_round":2}])
        self.assertEqual([row["eavesdrop_count"] for row in series(sim.scenario,sim.frames)],[0,0,1,1,0])
        self.assertTrue(all(not f.persistent_edges and not f.proximity_edges and not f.campaign_edges for f in sim.frames))
        self.assertTrue(all(not f.ballot_sensors for f in sim.frames))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)
        tampered=sim.checkpoint(); tampered["frames"][2]["overheard_reports"][0]["ballot"]=["A"]
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(tampered)
        tampered=sim.checkpoint(); tampered["frames"][2]["coalition_eavesdrop_spend"]["campaign"]=0
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(tampered)
        tampered=sim.checkpoint(); tampered["version"]=13
        with self.assertRaisesRegex(ElectionError,"version 14"): Simulation.from_checkpoint(tampered)
        sim.edit_after(1,"2",preference=["A","B"]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)

    def test_observations_are_scoped_untrusted_and_never_membership(self):
        raw=example(); raw["groups"]["observer"].update(voting="python:strategy_fixture:capture_overheard",
                                      movement="python:strategy_fixture:capture_overheard_movement")
        raw["groups"]["residents"]["voting"]="python:strategy_fixture:capture_overheard"
        sim=Simulation(make_scenario(raw)); sim.run(2); frame=sim.current.as_dict()
        memory=frame["policy_memory"]["1"]
        self.assertEqual(memory["overheard"],[["2","3","team",1,0,2,["B"]]])
        self.assertEqual((memory["messages"],memory["sensed"],memory["channels"]),([],[],[]))
        self.assertEqual(frame["policy_memory"]["2"]["overheard"],[])
        self.assertEqual(frame["policy_memory"]["3"]["overheard"],[])
        phase={(p,k):v for p,k,v in frame["phase_memory"]}
        self.assertEqual(phase[("1","movement")]["overheard"],[])
        self.assertNotIn("1",frame["private_channels"]["team"])

    def test_communication_receives_interception_and_later_failure_rolls_back_spend(self):
        raw=example(); raw["groups"]["observer"]["communication"]="python:strategy_fixture:capture_overheard_communication"
        sim=Simulation(make_scenario(raw)); sim.run(2)
        memories={(p,phase):value for p,phase,value in sim.current.as_dict()["phase_memory"]}
        self.assertEqual(memories[("1","communication")]["overheard"],[["2","3","team",1,0,2,["B"]]])
        raw["groups"]["observer"]["communication"]="python:strategy_fixture:invalid_second_communication"
        sim=Simulation(make_scenario(raw)); sim.step(); before=sim.checkpoint()
        with self.assertRaises(ElectionError): sim.step()
        self.assertEqual(sim.checkpoint(),before)

    def test_false_reports_remain_untrusted_and_delivery_denial_is_independent(self):
        raw=example(); raw["groups"]["observer"]["voting"]="python:strategy_fixture:capture_overheard"
        raw["people"][1]["overrides"]={"communication":"target_report"}
        raw["people"][2]["overrides"]={"capabilities":{"receive_private_reports":False}}
        raw["coalitions"].append({"id":"other","members":["2"],"target":"A",
                                  "report_budget_per_round":1,"report_budget_total":1})
        sim=Simulation(make_scenario(raw)); sim.run(2); frame=sim.current.as_dict()
        self.assertEqual(frame["policy_memory"]["1"]["overheard"],[["2","3","team",1,0,2,["A"]]])
        self.assertNotIn(["2","3","team",["A"]],frame["delivered"])
        self.assertEqual(frame["ballots"]["2"],["B"])
        self.assertEqual(frame["ballot_sensors"],[])
        self.assertNotIn("truth",str(frame["policy_memory"]["1"]))

    def test_zero_budget_revocation_and_no_self_intercept(self):
        raw=example(); raw["coalitions"][0]["eavesdrop_budget_total"]=0
        sim=Simulation(make_scenario(raw)); sim.run(4)
        self.assertTrue(all(not f.overheard_reports for f in sim.frames))
        self.assertTrue(all(dict(f.ballots)["1"] == ("A",) for f in sim.frames))
        raw=example(); raw["groups"]["observer"]["voting"]="python:strategy_fixture:capture_overheard"
        sim=Simulation(make_scenario(raw)); sim.run(2)
        sim.edit_after(2,"1",overrides={"capabilities":{"intercept_private_reports":False}})
        frame=sim.step().as_dict()
        self.assertEqual(frame["policy_memory"]["1"]["overheard"],[])
        self.assertEqual(frame["coalition_eavesdrop_spend"]["campaign"],1)
        raw=example(); raw["people"][0]["group"]="residents"; raw["people"][1]["group"]="observer"
        raw["coalitions"][0]["members"]=["2"]
        sim=Simulation(make_scenario(raw)); sim.run(2)
        self.assertFalse(sim.current.overheard_reports)

    def test_budget_allocation_and_repeated_sender_deduplication(self):
        raw=example(); raw["people"].append({"id":"4","group":"observer","preference":["A","B"]})
        raw["coalitions"][0]["members"]=["4","1"]
        sim=Simulation(make_scenario(raw)); sim.run(2)
        self.assertEqual([(event[1],event[2],event[3]) for event in sim.current.overheard_reports],[("1","2","3")])
        raw=example(); raw["people"].append({"id":"4","group":"residents","preference":["A","B"],
                                             "overrides":{"communication":"none"}})
        raw["network"]["private_channels"]["team"]=["2","3","4"]
        raw["coalitions"][0].update(eavesdrop_budget_per_round=3,eavesdrop_budget_total=3)
        sim=Simulation(make_scenario(raw)); sim.run(2)
        self.assertEqual([(event[2],event[3],event[5]) for event in sim.current.overheard_reports],
                         [("2","3",("B",)),("2","4",("B",)),("3","2",("A",))])
        self.assertEqual(dict(sim.current.ballots)["1"],("A",))  # one vote per sender, tie -> own preference

    def test_validation_and_atomic_unauthorized_grant(self):
        changes=[lambda x:x["coalitions"][0].update(eavesdrop_channels=["public"]),
                 lambda x:x["coalitions"][0].update(eavesdrop_channels=["missing"]),
                 lambda x:x["coalitions"][0].update(eavesdrop_channels=["team","team"]),
                 lambda x:x["coalitions"][0].update(eavesdrop_channels=[]),
                 lambda x:x["coalitions"][0].update(eavesdrop_budget_total=-1),
                 lambda x:x["coalitions"][0].pop("eavesdrop_budget_per_round"),
                 lambda x:x["groups"]["observer"].update(capabilities={}),
                 lambda x:x["coalitions"][0].update(members=["2"])]
        for change in changes:
            data=example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        raw=example(); sim=Simulation(make_scenario(raw)); sim.step()
        sim.edit_after(1,"2",overrides={"capabilities":{"intercept_private_reports":True}})
        before=sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"coalition membership"): sim.step()
        self.assertEqual(before,sim.checkpoint())

    def test_startup_policy_selection_checks_authority(self):
        session=Session(Simulation(make_scenario(example())))
        self.assertIn("overheard_plurality",session.snapshot()["voting_policies"])
        before=session.snapshot()
        with self.assertRaisesRegex(ElectionError,"eavesdropping requires"):
            session.command({"action":"configure_voting","revision":0,"policy":"overheard_plurality","parameters":{}})
        self.assertEqual(session.snapshot(),before)
        raw=example(); raw["coalitions"][0]["members"]=["1","2","3"]
        raw["groups"]["residents"]["capabilities"]={"intercept_private_reports":True}
        session=Session(Simulation(make_scenario(raw)))
        state=session.command({"action":"configure_voting","revision":0,"policy":"overheard_plurality","parameters":{}})
        self.assertEqual({group["policy"] for group in state["startup_voting"].values()},{"overheard_plurality"})

    def test_cli_session_checkpoint_migration_and_csv(self):
        with Path("examples/coalition-sight.toml").open("rb") as handle: legacy=Simulation(make_scenario(tomllib.load(handle)))
        legacy.run(2); old=legacy.checkpoint(); old["version"]=13
        for group in old["scenario"]["groups"].values(): group["capabilities"].pop("intercept_private_reports")
        self.assertEqual(Simulation.from_checkpoint(old).current,legacy.current)
        sim=Simulation(make_scenario(example())); session=Session(sim)
        for revision in range(4): session.command({"action":"step","revision":revision})
        output=io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(main(["run","examples/coalition-eavesdrop.toml"]),0)
        self.assertEqual(session.snapshot()["frames"],json.loads(output.getvalue())["frames"])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path=root/"checkpoint.json"; path.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(["export",str(path),"--csv",str(root/"metrics.csv")]),0)
            with (root/"metrics.csv").open(newline="") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual([r["eavesdrop_count"] for r in rows],["0","0","1","1","0"])
            self.assertEqual([r["coalition_eavesdrop_spend:campaign"] for r in rows],["0","0","1","2","2"])

    def test_http_eavesdrop_state_and_step(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario=make_scenario(example()); direct=Simulation(scenario); direct.run(2)
        server=make_server(Simulation(scenario)); worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
        self.addCleanup(worker.join,2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base=f"http://127.0.0.1:{server.server_port}"
        with urlopen(base+"/") as response: html=response.read().decode()
        token=html.split('name="session-token" content="')[1].split('"')[0]
        headers={"X-Session-Token":token,"Content-Type":"application/json"}
        with urlopen(Request(base+"/state",headers=headers)) as response: state=json.load(response)
        self.assertEqual(state["coalitions"][0]["eavesdrop_channels"],["team"])
        for revision in range(2):
            request=Request(base+"/command",headers=headers,data=json.dumps({"action":"step","revision":revision}).encode(),method="POST")
            with urlopen(request) as response: reply=json.load(response)
        self.assertEqual(reply["frame"],direct.current.as_dict())
        self.assertEqual(reply["metric"]["eavesdrop_count"],1)


if __name__ == "__main__": unittest.main()
