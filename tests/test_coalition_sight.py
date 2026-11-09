import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.metrics import series
from multi_agent_election.visual import Session


def example():
    with Path("examples/coalition-sight.toml").open("rb") as handle:
        return tomllib.load(handle)


class CoalitionSightTests(VerificationTestCase):
    def test_separate_budgets_replay_and_rewind(self):
        sim = Simulation(make_scenario(example())); sim.run()
        frames = [frame.as_dict() for frame in sim.frames]
        self.assertEqual([f["coalition_sight_spend"]["campaign"] for f in frames],[0,1,2,2,2])
        self.assertEqual([f["coalition_report_spend"]["campaign"] for f in frames],[0,1,1,1,1])
        self.assertEqual([f["ballots"]["1"] for f in frames],[["A"],["B"],["B"],["A"],["A"]])
        self.assertEqual(frames[1]["preference_sight"], [{"coalition":"campaign","observer":"1",
                         "target":"2","round":1,"preference":["B","C","A"]}])
        self.assertEqual([row["preference_sight_count"] for row in series(sim.scenario,sim.frames)],[0,1,1,0,0])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,sim.current)
        forged = sim.checkpoint(); forged["frames"][1]["preference_sight"][0]["preference"] = ["C","B","A"]
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(forged)
        forged = sim.checkpoint(); forged["frames"][1]["coalition_sight_spend"]["campaign"] = 0
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(forged)
        forged = sim.checkpoint(); forged["version"] = 12
        with self.assertRaisesRegex(ElectionError,"version 13"): Simulation.from_checkpoint(forged)
        sim.edit_after(1,"2",preference=["C","B","A"]); next_frame = sim.step().as_dict()
        self.assertEqual(next_frame["preference_sight"][0]["preference"],["C","B","A"])
        self.assertEqual(next_frame["ballots"]["1"],["C"])
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current.as_dict(),next_frame)

    def test_scoped_observations_and_no_cross_phase_leak(self):
        raw = example(); raw["groups"]["coalition"].update(voting="python:strategy_fixture:capture_sight",
                      movement="python:strategy_fixture:capture_sight_movement")
        raw["groups"]["residents"]["voting"] = "python:strategy_fixture:capture_sight"
        sim = Simulation(make_scenario(raw)); sim.step(); frame=sim.current.as_dict()
        self.assertEqual(frame["policy_memory"]["1"]["sighted"],[["2",1,["B","C","A"]]])
        self.assertEqual(frame["policy_memory"]["2"]["sighted"],[])
        self.assertEqual(frame["policy_memory"]["3"]["sighted"],[])
        self.assertEqual(frame["phase_memory"][0][2]["sighted"],[])
        changed = copy.deepcopy(raw); changed["people"][2]["preference"] = ["C","B","A"]
        other = Simulation(make_scenario(changed)); other.step()
        self.assertEqual(frame["policy_memory"]["1"],other.current.as_dict()["policy_memory"]["1"])

    def test_communication_plugin_sees_only_its_authorized_sight(self):
        raw = example(); raw["groups"]["coalition"]["communication"] = "python:strategy_fixture:capture_sight_communication"
        sim = Simulation(make_scenario(raw)); sim.step()
        memories = {(person,phase):memory for person,phase,memory in sim.current.as_dict()["phase_memory"]}
        self.assertEqual(memories[("1","communication")]["sighted"],[["2",1,["B","C","A"]]])
        self.assertEqual(sim.current.pending,())

    def test_zero_budget_and_revocation_do_not_create_readings(self):
        raw = example(); raw["coalitions"][0]["sight_budget_total"] = 0
        sim = Simulation(make_scenario(raw)); sim.run(2)
        self.assertTrue(all(not f.preference_sight for f in sim.frames))
        self.assertEqual(dict(sim.current.ballots)["1"],("A",))
        raw = example(); raw["groups"]["coalition"]["voting"] = "python:strategy_fixture:capture_sight"
        sim = Simulation(make_scenario(raw)); sim.step()
        sim.edit_after(1,"1",overrides={"capabilities":{"observe_target_preferences":False}})
        frame = sim.step().as_dict()
        self.assertEqual(frame["policy_memory"]["1"]["sighted"],[])
        self.assertEqual(frame["coalition_sight_spend"]["campaign"],1)
        self.assertEqual(frame["preference_sight"],[])

    def test_shared_sight_budget_uses_sorted_members_and_targets(self):
        data=example(); data["people"][2]["group"]="coalition"
        data["people"] = list(reversed(data["people"]))
        data["coalitions"][0]["members"] = ["3","1"]
        data["coalitions"][0]["sight_targets"] = ["3","2"]
        sim=Simulation(make_scenario(data)); sim.step()
        events=sim.current.as_dict()["preference_sight"]
        self.assertEqual([(event["observer"],event["target"]) for event in events],[("1","2")])
        self.assertEqual(dict(sim.current.coalition_sight_spend),{"campaign":1})

    def test_invalid_grants_configs_and_failure_are_atomic(self):
        changes = [lambda x:x["coalitions"][0].update(sight_targets=["unknown"]),
                   lambda x:x["coalitions"][0].update(sight_targets=["2","2"]),
                   lambda x:x["coalitions"][0].update(sight_targets=[]),
                   lambda x:x["coalitions"][0].update(sight_budget_total=-1),
                   lambda x:x["coalitions"][0].pop("sight_budget_per_round"),
                   lambda x:x["coalitions"][0].update(members=["2"]),
                   lambda x:x["groups"]["coalition"].update(capabilities={})]
        for change in changes:
            raw = example(); change(raw)
            with self.subTest(raw=raw), self.assertRaises(ElectionError): make_scenario(raw)
        raw = example(); raw["groups"]["coalition"].update(communication="python:strategy_fixture:proposed_reports",
              parameters={"reports":[{"recipient":"3","channel":"public","ballot":["B"]}]})
        sim = Simulation(make_scenario(raw)); before=sim.checkpoint()
        with self.assertRaises(ElectionError): sim.step()
        self.assertEqual(before,sim.checkpoint())
        raw = example(); sim = Simulation(make_scenario(raw)); sim.step()
        sim.edit_after(1,"2",overrides={"capabilities":{"observe_target_preferences":True}})
        before=sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"coalition membership"): sim.step()
        self.assertEqual(before,sim.checkpoint())

    def test_legacy_checkpoint_cli_session_and_csv(self):
        with Path("examples/coalition-report.toml").open("rb") as handle:
            legacy = Simulation(make_scenario(tomllib.load(handle)))
        legacy.run(2); checkpoint = legacy.checkpoint(); checkpoint["version"] = 12
        for group in checkpoint["scenario"]["groups"].values(): group["capabilities"].pop("observe_target_preferences")
        self.assertEqual(Simulation.from_checkpoint(checkpoint).current,legacy.current)
        sim = Simulation(make_scenario(example())); session = Session(sim)
        for revision in range(4): session.command({"action":"step","revision":revision})
        output=io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(main(["run","examples/coalition-sight.toml"]),0)
        self.assertEqual(session.snapshot()["frames"],json.loads(output.getvalue())["frames"])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path=root/"checkpoint.json"; path.write_text(json.dumps(sim.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(["export",str(path),"--csv",str(root/"metrics.csv")]),0)
            with (root/"metrics.csv").open(newline="") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual([row["preference_sight_count"] for row in rows],["0","1","1","0","0"])
            self.assertEqual([row["coalition_sight_spend:campaign"] for row in rows],["0","1","2","2","2"])

    def test_startup_selection_enforces_membership_and_permission(self):
        session=Session(Simulation(make_scenario(example())))
        self.assertIn("sight_plurality",session.snapshot()["voting_policies"])
        before=session.snapshot()
        with self.assertRaisesRegex(ElectionError,"preference sight requires"):
            session.command({"action":"configure_voting","revision":0,"policy":"sight_plurality","parameters":{}})
        self.assertEqual(session.snapshot(),before)
        raw=example(); raw["coalitions"][0]["members"]=["1","2","3"]
        raw["groups"]["residents"]["capabilities"]={"observe_target_preferences":True}
        session=Session(Simulation(make_scenario(raw)))
        state=session.command({"action":"configure_voting","revision":0,"policy":"sight_plurality","parameters":{}})
        self.assertEqual({group["policy"] for group in state["startup_voting"].values()},{"sight_plurality"})

    def test_http_sight_state_and_step(self):
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
        self.assertEqual(state["coalitions"][0]["sight_targets"],["2","3"])
        request=Request(base+"/command",headers=headers,data=json.dumps({"action":"step","revision":0}).encode(),method="POST")
        with urlopen(request) as response: reply=json.load(response)
        self.assertEqual(reply["frame"],direct.current.as_dict())
        self.assertEqual(reply["metric"]["preference_sight_count"],1)


if __name__ == "__main__": unittest.main()
