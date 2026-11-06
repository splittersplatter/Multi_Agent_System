import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import contextlib
import io
import shutil
import subprocess

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.visual import make_server
from multi_agent_election.cli import main
from test_baseline import example


class VisualTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js required for browser edit planner regression")
    def test_browser_edit_planner_omits_unchanged_fields_and_checks_lists(self):
        script = r"""
const assert = require('node:assert/strict');
const {planAgentEdit} = require('./src/multi_agent_election/web/edit.js');
const frame = {preferences:{p:['A','B']}, groups:{p:'g'}, positions:{p:[0.2,0.4]},
  overrides:{p:{parameters:{a:1,b:2}}}, persistent_edges:[['p','q']], campaign_edges:[],
  private_channels:{c:['p','q'], other:['q']}};
const values = {preference:['B','A'],group:'g',position:[0.2,0.4],
  overrides:{parameters:{b:2,a:1}},neighbors:['q'],campaignNeighbors:[],channels:['c']};
assert.deepEqual(planAgentEdit(frame,'p',values), {preference:['B','A']});
assert.deepEqual(planAgentEdit(frame,'p',{...values,preference:['A','B']}), {});
assert.deepEqual(planAgentEdit(frame,'p',{...values,neighbors:['r'],channels:['other'],ballot:['A']}),
  {preference:['B','A'],add_edges:['r'],remove_edges:['q'],add_channels:['other'],remove_channels:['c'],ballot:['A']});
assert.deepEqual(planAgentEdit(frame,'p',{...values,campaignNeighbors:['r']}),
  {preference:['B','A'],add_campaign_edges:['r']});
assert.throws(() => planAgentEdit(frame,'p',{...values,neighbors:['q','q']}), /distinct/);
assert.throws(() => planAgentEdit(frame,'p',{...values,channels:[3]}), /distinct/);
"""
        subprocess.run([shutil.which("node"), "-e", script], check=True, capture_output=True, text=True)

    def test_local_commands_revision_edit_and_checkpoint(self):
        server = make_server(Simulation(make_scenario(example())))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            self.assertIn('/edit.js', html)
            self.assertIn('planAgentEdit', urlopen(base + '/edit.js').read().decode())
            self.assertIn('Vote shares over time', html)
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            def command(data):
                req = Request(base + "/command", data=json.dumps(data).encode(), headers=headers, method="POST")
                return json.load(urlopen(req))
            state = command({"action": "step", "revision": 0})
            self.assertEqual(state["frame"]["round"], 1)
            with self.assertRaises(HTTPError) as stale:
                command({"action": "step", "revision": 0})
            self.assertEqual(stale.exception.code, 400)
            stale.exception.close()
            state = command({"action": "edit", "revision": 1, "round": 0, "person": "2", "changes": {"preference": ["C", "A", "B"]}})
            self.assertEqual(len(state["frames"]), 1)
            state = command({"action": "step", "revision": 2})
            self.assertEqual(state["frame"]["winner"], "B")
            self.assertEqual(state["metric"]["winner"], "B")
            checkpoint = json.load(urlopen(Request(base + "/checkpoint", headers={"X-Session-Token": token})))
            self.assertEqual(Simulation.from_checkpoint(checkpoint).current.winner, "B")
            with self.assertRaises(HTTPError) as unauthorized: urlopen(base + "/state")
            self.assertEqual(unauthorized.exception.code, 403)
            unauthorized.exception.close()
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_cli_and_browser_commit_identical_frames_and_metrics(self):
        import tomllib
        from pathlib import Path
        with Path("examples/network.toml").open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        expected_output = io.StringIO()
        with contextlib.redirect_stdout(expected_output): self.assertEqual(main(["run", "examples/network.toml"]), 0)
        expected = json.loads(expected_output.getvalue())
        server = make_server(Simulation(scenario))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            state = json.load(urlopen(Request(base + "/state", headers=headers)))
            self.assertTrue(state["group_capabilities"]["neighbors"]["move"])
            observed_frames, observed_metrics = state["frames"], state["metrics"]
            for revision in range(scenario.rounds):
                payload=json.dumps({"action":"step", "revision":revision}).encode()
                result=json.load(urlopen(Request(base + "/command", data=payload, headers=headers, method="POST")))
                observed_frames.append(result["frame"]); observed_metrics.append(result["metric"])
            self.assertEqual(observed_frames, expected["frames"])
            self.assertEqual(observed_metrics, expected["metrics"])
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_sensor_trace_matches_cli_over_browser_commands(self):
        import tomllib
        from pathlib import Path
        with Path("examples/sensors.toml").open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(["run", "examples/sensors.toml"]), 0)
        expected = json.loads(stream.getvalue())
        server = make_server(Simulation(scenario))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            for revision in range(scenario.rounds):
                request = Request(base + "/command", data=json.dumps({"action": "step", "revision": revision}).encode(),
                                  headers=headers, method="POST")
                reply = json.load(urlopen(request))
                self.assertEqual(reply["frame"], expected["frames"][revision + 1])
                self.assertEqual(reply["metric"], expected["metrics"][revision + 1])
            self.assertEqual(reply["frame"]["ballot_sensors"], [["2", "1", "public", 1, ["C", "A"]]])
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_campaign_interactive_edits_match_headless_replay(self):
        import tomllib
        from pathlib import Path
        with Path("examples/campaign-layer.toml").open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        expected = Simulation(scenario); expected.step()
        expected.edit_after(1, "2", add_campaign_edges=["1"]); expected.step()
        server = make_server(Simulation(scenario))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            self.assertIn('id="show-campaign"', html)
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            def command(data):
                request = Request(base + "/command", data=json.dumps(data).encode(), headers=headers, method="POST")
                return json.load(urlopen(request))
            command({"action": "step", "revision": 0})
            command({"action": "edit", "revision": 1, "round": 1, "person": "2", "changes": {"add_campaign_edges": ["1"]}})
            result = command({"action": "step", "revision": 2})
            self.assertEqual(result["frame"], expected.current.as_dict())
            self.assertEqual(result["frame"]["campaign_edges"], [["2", "1"]])
            self.assertEqual(result["metric"]["campaign_edge_count"], 1)
            checkpoint = json.load(urlopen(Request(base + "/checkpoint", headers=headers)))
            self.assertEqual(Simulation.from_checkpoint(checkpoint).current, expected.current)
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)


if __name__ == "__main__": unittest.main()
