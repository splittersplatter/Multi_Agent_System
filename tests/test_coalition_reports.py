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
    with Path("examples/coalition-report.toml").open("rb") as handle:
        return tomllib.load(handle)


class CoalitionReportTests(VerificationTestCase):
    def test_budgeted_deception_delay_sensor_separation_and_replay(self):
        sim = Simulation(make_scenario(example())); sim.run()
        frames = [frame.as_dict() for frame in sim.frames]
        self.assertEqual([frame["coalition_report_spend"]["campaign"] for frame in frames], [0,1,2,2,2])
        self.assertEqual([len(frame["deceptive_reports"]) for frame in frames], [0,1,1,0,0])
        self.assertEqual(frames[1]["pending"][0], ["1","2","public",["B"]])
        self.assertEqual(frames[2]["delivered"][0], ["1","2","public",["B"]])
        self.assertEqual(frames[2]["ballot_sensors"], [["2","1","public",1,["A"]]])
        self.assertEqual([frame["ballots"]["2"] for frame in frames], [["A"],["A"],["B"],["B"],["A"]])
        self.assertTrue(all(frame["ballots"]["1"] == ["A"] for frame in frames))
        self.assertEqual([r["deceptive_report_count"] for r in series(sim.scenario,sim.frames)], [0,1,1,0,0])
        restored = Simulation.from_checkpoint(sim.checkpoint()); self.assertEqual(restored.current, sim.current)
        self.assertEqual(restored.step(), sim.step())
        forged = sim.checkpoint(); forged["frames"][1]["coalition_report_spend"]["campaign"] = 0
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(forged)
        forged = sim.checkpoint(); forged["frames"][1]["deceptive_reports"][0]["ballot"] = ["A"]
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(forged)
        old = sim.checkpoint(); old["version"] = 11
        with self.assertRaisesRegex(ElectionError,"version 12"): Simulation.from_checkpoint(old)
        sim.edit_after(1,"2",preference=["B","A"])
        self.assertEqual(dict(sim.current.coalition_report_spend), {"campaign":1})
        sim.step(); self.assertEqual(dict(sim.current.coalition_report_spend), {"campaign":2})
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_zero_budget_is_truthful_and_receiver_never_gets_coalition_budget(self):
        raw = example(); raw["coalitions"][0]["report_budget_total"] = 0
        control = copy.deepcopy(raw); control.pop("coalitions"); control["groups"]["sender"]["communication"] = "truthful"
        left, right = Simulation(make_scenario(raw)),Simulation(make_scenario(control)); left.run(); right.run()
        for a,b in zip(left.frames,right.frames):
            self.assertEqual((a.positions,a.ballots,a.pending,a.delivered,a.ballot_sensors),
                             (b.positions,b.ballots,b.pending,b.delivered,b.ballot_sensors))
        legacy = right.checkpoint(); legacy["version"] = 11
        self.assertEqual(Simulation.from_checkpoint(legacy).current,right.current)
        raw = example(); raw["groups"]["listener"]["voting"] = "python:strategy_fixture:capture_coalition_budget"
        sim = Simulation(make_scenario(raw)); sim.run(2)
        memory = sim.current.as_dict()["policy_memory"]["2"]
        self.assertIsNone(memory["coalition_budget"])
        self.assertEqual(memory["messages"], [["1","public",["B"]]])
        self.assertEqual(memory["sensed"], [["1","public",1,["A"]]])

    def test_epistemic_and_trusted_sensor_responses_do_not_treat_reports_as_truth(self):
        data = example(); data["groups"]["listener"]["voting"] = "sensed_plurality"
        sensed = Simulation(make_scenario(data)); sensed.run(2)
        self.assertEqual(dict(sensed.current.ballots)["2"], ("A",))
        data["groups"]["listener"].update(voting="epistemic_dere",
                                          capabilities={"sense_public_ballots":True,"observe_electorate":True})
        truthful = copy.deepcopy(data); truthful["groups"]["sender"]["communication"] = "truthful"
        deceived, honest = Simulation(make_scenario(data)), Simulation(make_scenario(truthful))
        deceived.run(2); honest.run(2)
        self.assertNotEqual(deceived.current.delivered, honest.current.delivered)
        self.assertEqual(deceived.current.as_dict()["policy_memory"]["2"],honest.current.as_dict()["policy_memory"]["2"])
        self.assertEqual(dict(deceived.current.ballots)["2"],dict(honest.current.ballots)["2"])

    def test_plugin_cannot_exceed_budget_or_send_unauthorized_reports(self):
        raw = example(); raw["groups"]["sender"]["communication"] = "python:strategy_fixture:proposed_reports"
        reports = [{"recipient":"2","channel":"public","ballot":["B"]},
                   {"recipient":"3","channel":"public","ballot":["B"]}]
        raw["groups"]["sender"]["parameters"] = {"reports":reports}
        sim = Simulation(make_scenario(raw)); before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"budget exceeded"): sim.step()
        self.assertEqual(sim.checkpoint(),before)
        for invalid in ([{"recipient":"2","channel":"team","ballot":["B"]}],
                        [{"recipient":"2","channel":"public","ballot":["Z"]}],
                        [reports[0],reports[0]]):
            altered = copy.deepcopy(raw); altered["groups"]["sender"]["parameters"]["reports"] = invalid
            sim = Simulation(make_scenario(altered)); before = sim.checkpoint()
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError): sim.step()
            self.assertEqual(sim.checkpoint(),before)
        nonmember = copy.deepcopy(raw); nonmember.pop("coalitions")
        nonmember["groups"]["sender"]["parameters"]["reports"] = reports[:1]
        with self.assertRaisesRegex(ElectionError,"untruthful"): Simulation(make_scenario(nonmember)).step()
        raw["groups"]["sender"]["parameters"]["reports"] = reports[:1]
        first = Simulation(make_scenario(raw)).step().as_dict()
        self.assertEqual(first["phase_memory"][0][2]["coalition_budget"], ["campaign","B",1,2])

    def test_shared_coalition_budget_is_allocated_in_sorted_sender_order(self):
        raw = example(); raw["people"][2]["group"] = "sender"; raw["people"][2]["preference"] = ["A","B"]
        raw["people"] = list(reversed(raw["people"]))
        raw["coalitions"][0]["members"] = ["3","1"]
        raw["network"] = {"persistent_edges":[["1","2"],["3","2"]]}
        sim = Simulation(make_scenario(raw)); sim.run(2)
        for frame in sim.frames[1:]:
            self.assertEqual([(x[1],x[2]) for x in frame.deceptive_reports],[("1","2")])
        self.assertEqual(dict(sim.current.coalition_report_spend),{"campaign":2})

    def test_validation_session_and_csv(self):
        for change in (lambda x:x["coalitions"][0].update(report_budget_total=-1),
                       lambda x:x["coalitions"][0].update(report_budget_per_round=True),
                       lambda x:x["coalitions"][0].update(members=["unknown"]),
                       lambda x:x["coalitions"][0].update(target="unknown"),
                       lambda x:x["coalitions"].append(copy.deepcopy(x["coalitions"][0]))):
            data = example(); change(data)
            with self.subTest(data=data), self.assertRaises(ElectionError): make_scenario(data)
        raw = example(); raw.pop("coalitions")
        with self.assertRaisesRegex(ElectionError,"requires coalition"): Simulation(make_scenario(raw)).step()
        with Path("examples/certified-direct.toml").open("rb") as handle: certified = tomllib.load(handle)
        certified["coalitions"] = copy.deepcopy(example()["coalitions"])
        with self.assertRaisesRegex(ElectionError,"excludes coalition"): make_scenario(certified)
        scenario = make_scenario(example()); session = Session(Simulation(scenario))
        for revision in range(4): session.command({"action":"step","revision":revision})
        cli = io.StringIO()
        with contextlib.redirect_stdout(cli): self.assertEqual(main(["run","examples/coalition-report.toml"]),0)
        self.assertEqual(session.snapshot()["frames"],json.loads(cli.getvalue())["frames"])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); checkpoint=root/"checkpoint.json"
            checkpoint.write_text(json.dumps(session.simulation.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export",str(checkpoint),"--csv",str(root/"out.csv")]),0)
            with (root/"out.csv").open(newline="") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual([row["coalition_report_spend:campaign"] for row in rows],["0","1","2","2","2"])
            self.assertEqual([row["deceptive_report_count"] for row in rows],["0","1","1","0","0"])

    def test_http_state_and_report_budget_match_engine(self):
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        scenario = make_scenario(example()); direct = Simulation(scenario); direct.run(2)
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever,daemon=True); worker.start()
        self.addCleanup(worker.join,2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as response: html=response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers={"X-Session-Token":token,"Content-Type":"application/json"}
        with urlopen(Request(base+"/state",headers=headers)) as response: state=json.load(response)
        self.assertEqual(state["coalitions"][0]["report_budget_total"],2)
        for revision in range(2):
            payload=json.dumps({"action":"step","revision":revision}).encode()
            with urlopen(Request(base+"/command",headers=headers,data=payload,method="POST")) as response:
                reply=json.load(response)
            self.assertEqual(reply["frame"],direct.frames[revision+1].as_dict())
        with urlopen(Request(base+"/checkpoint?revision=2",headers=headers)) as response:
            self.assertEqual(Simulation.from_checkpoint(json.load(response)).current,direct.current)


if __name__ == "__main__": unittest.main()
