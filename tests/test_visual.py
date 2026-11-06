import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import contextlib
import io
import shutil
import subprocess
import csv
import importlib.util
from unittest.mock import patch

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.visual import make_server
from multi_agent_election.cli import main
from test_baseline import example


class VisualTests(unittest.TestCase):
    def test_checkpoint_revision_guard_rejects_stale_and_malformed_requests(self):
        simulation = Simulation(make_scenario(example()))
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token}
            with urlopen(Request(base + "/checkpoint?revision=0", headers=headers)) as response:
                self.assertEqual(json.load(response), simulation.checkpoint())
            request = Request(base + "/command", data=json.dumps({"action": "step", "revision": 0}).encode(),
                              headers={**headers, "Content-Type": "application/json"}, method="POST")
            with urlopen(request) as response:
                self.assertEqual(json.load(response)["revision"], 1)
            for query in ("revision=0", "revision=", "revision=1&revision=1", "revision=1&extra=x", "revision=oops"):
                with self.subTest(query=query), self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + "/checkpoint?" + query, headers=headers))
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
            with self.assertRaises(HTTPError) as unauthorized:
                urlopen(base + "/checkpoint?revision=1")
            self.assertEqual(unauthorized.exception.code, 403); unauthorized.exception.close()
            # Historical unversioned clients still request the current checkpoint.
            with urlopen(Request(base + "/checkpoint", headers=headers)) as response:
                self.assertEqual(json.load(response), simulation.checkpoint())
            with urlopen(Request(base + "/checkpoint?revision=1", headers=headers)) as response:
                self.assertEqual(json.load(response), simulation.checkpoint())
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_checkpoint_revision_check_and_snapshot_are_atomic_against_step(self):
        simulation = Simulation(make_scenario(example()))
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        entered, release, step_started = threading.Event(), threading.Event(), threading.Event()
        results = {}; real_checkpoint, real_step = simulation.checkpoint, simulation.step
        try:
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            def delayed_checkpoint():
                entered.set()
                if not release.wait(3): raise RuntimeError("checkpoint test did not release")
                return real_checkpoint()
            def checked_step():
                step_started.set()
                return real_step()
            def get_checkpoint():
                try:
                    with urlopen(Request(base + "/checkpoint?revision=0", headers=headers)) as response:
                        results["checkpoint"] = json.load(response)
                except Exception as exc: results["checkpoint_error"] = exc
            def step():
                try:
                    payload = json.dumps({"action": "step", "revision": 0}).encode()
                    with urlopen(Request(base + "/command", data=payload, headers=headers, method="POST")) as response:
                        results["step"] = json.load(response)
                except Exception as exc: results["step_error"] = exc
            with patch.object(simulation, "checkpoint", side_effect=delayed_checkpoint), \
                 patch.object(simulation, "step", side_effect=checked_step):
                downloader = threading.Thread(target=get_checkpoint, daemon=True); downloader.start()
                self.assertTrue(entered.wait(3))
                stepper = threading.Thread(target=step, daemon=True); stepper.start()
                self.assertFalse(step_started.wait(0.1))
                release.set(); downloader.join(timeout=3); stepper.join(timeout=3)
                self.assertFalse(downloader.is_alive()); self.assertFalse(stepper.is_alive())
            self.assertNotIn("checkpoint_error", results); self.assertNotIn("step_error", results)
            self.assertEqual(len(results["checkpoint"]["frames"]), 1)
            self.assertEqual(results["checkpoint"]["frames"][0]["round"], 0)
            self.assertEqual(results["step"]["revision"], 1)
        finally:
            release.set(); server.shutdown(); server.server_close(); worker.join(timeout=2)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for preference-proxy regression")
    def test_preference_proxy_uses_only_selected_observers_recorded_evidence(self):
        script = r"""
const assert = require('node:assert/strict');
const {estimatedPreferences} = require('./src/multi_agent_election/web/inspector.js');
const frame = {
  preferences:{o:['A'], a:['C'], b:['B'], c:['C'], d:['A'], e:['B']},
  ballots:{a:['C'], b:['B'], c:['C'], d:['A'], e:['B']},
  delivered:[['a','o','public',['B']], ['b','o','public',['A']],
             ['c','other','public',['C']], ['a','o','private',['B']]],
  ballot_sensors:[['o','b','public',1,['C']], ['o','d','private',1,['A']],
                  ['other','e','public',1,['B']]],
  pending:[['e','o','public',['B']]]
};
const original=JSON.stringify(frame);
const result=Object.fromEntries(estimatedPreferences(frame,'o'));
assert.deepEqual(result,{o:'A',a:'B',d:'A'}); // b conflicts; c/e not observed
assert.equal(JSON.stringify(frame),original); // read-only visualization
frame.preferences.a=['A']; frame.ballots.a=['A']; frame.pending.push(['c','o','public',['A']]);
assert.deepEqual(Object.fromEntries(estimatedPreferences(frame,'o')),result); // no hidden/future leak
assert.deepEqual(Object.fromEntries(estimatedPreferences({...frame,delivered:[],ballot_sensors:[]},'o')),{o:'A'});
"""
        subprocess.run([shutil.which("node"), "-e", script], check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for preference-proxy regression")
    def test_preference_proxy_tracks_recorded_sensor_time_and_observer(self):
        import tomllib
        from pathlib import Path
        with Path("examples/sensors.toml").open("rb") as handle:
            simulation = Simulation(make_scenario(tomllib.load(handle)))
        simulation.run(2)
        frames = [frame.as_dict() for frame in simulation.frames]
        script = r"""
const fs=require('node:fs');
const {estimatedPreferences}=require('./src/multi_agent_election/web/inspector.js');
const frames=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(frames.map(frame=>['2','3'].map(id=>Object.fromEntries(estimatedPreferences(frame,id))))));
"""
        result = subprocess.run([shutil.which("node"), "-e", script], input=json.dumps(frames),
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), [
            [{"2": "B"}, {"3": "B"}],
            [{"2": "B", "1": "A"}, {"3": "B"}],
            [{"2": "B", "1": "C"}, {"3": "B"}],
        ])
        # At round 1 the observed completed ballot A differs from current ballot C.
        self.assertEqual(frames[1]["ballots"]["1"][0], "C")

    @unittest.skipUnless(shutil.which("node"), "Node.js required for inspector regression")
    def test_agent_inspector_matches_recorded_frames_and_filters_other_agents(self):
        import sys
        import tomllib
        from pathlib import Path
        directory = str(Path("examples").resolve()); sys.path.insert(0, directory)
        self.addCleanup(lambda: sys.path.remove(directory))
        with Path("examples/integrated.toml").open("rb") as handle:
            simulation = Simulation(make_scenario(tomllib.load(handle)))
        simulation.run(2)
        frame = simulation.current.as_dict()
        script = r"""
const fs=require('node:fs');
const {inspectAgent}=require('./src/multi_agent_election/web/inspector.js');
const frame=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(['1','2','3'].map(id=>inspectAgent(frame,id))));
"""
        result = subprocess.run([shutil.which("node"), "-e", script], input=json.dumps(frame),
                                check=True, capture_output=True, text=True)
        inspectors = json.loads(result.stdout)
        for person, actual in zip(("1", "2", "3"), inspectors):
            expected_received = [{"sender": a, "recipient": b, "channel": c, "ballot": ballot}
                                 for a, b, c, ballot in frame["delivered"] if b == person]
            expected_pending = [{"sender": a, "recipient": b, "channel": c, "ballot": ballot}
                                for a, b, c, ballot in frame["pending"] if a == person]
            self.assertEqual(actual["round"], 2)
            self.assertEqual(actual["received_reports"], expected_received)
            self.assertEqual(actual["pending_outgoing_reports"], expected_pending)
            self.assertEqual(actual["voting_memory"], frame["policy_memory"][person])
            self.assertEqual(actual["interventions"], [event for event in frame["interventions"] if event["person"] == person])
            self.assertEqual(actual["phase_memory"], [{"phase": phase, "memory": memory}
                             for identifier, phase, memory in frame["phase_memory"] if identifier == person])
        self.assertEqual(inspectors[0]["voting_memory"], {"calls": 2})
        self.assertTrue(any(event.get("origin") == "scheduled" for event in inspectors[2]["interventions"]))

    @unittest.skipUnless(shutil.which("node"), "Node.js required for playback race regression")
    def test_pause_waits_for_inflight_step_and_disconnect_stops_playback(self):
        subprocess.run([shutil.which("node"), "tests/playback_harness.js"],
                       check=True, capture_output=True, text=True, timeout=10)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for browser download regression")
    def test_download_helper_keeps_retry_link_and_retires_old_url_safely(self):
        script = r"""
const assert = require('node:assert/strict');
const {createDownloadManager} = require('./src/multi_agent_election/web/download.js');
const events=[]; let revoke, index=0;
const container={children:[],replaceChildren(link){this.children=[link];events.push(['show',link.textContent]);}};
const env={URL:{createObjectURL(blob){events.push(['create',blob]);return `blob:${++index}`;},
                revokeObjectURL(url){events.push(['revoke',url]);}},
           document:{createElement(tag){assert.equal(tag,'a');return {click(){events.push(['click',this.href,this.download]);}};}},
           setTimeout(callback,delay){assert.equal(delay,60000);revoke=callback;events.push(['schedule']);}};
const manager=createDownloadManager(container,env);
manager.download('payload','result.csv','revision 4');
assert.deepEqual(events,[['create','payload'],['show','Save result.csv (revision 4)'],['click','blob:1','result.csv']]);
assert.equal(container.children[0].href,'blob:1');
manager.download('next','run.json','revision 5');
assert.equal(container.children[0].href,'blob:2');
assert.equal(container.children[0].download,'run.json');
assert.equal(container.children[0].textContent,'Save run.json (revision 5)');
assert.equal(events.some(item=>item[0]==='revoke'),false);
revoke();assert.deepEqual(events.at(-1),['revoke','blob:1']);
assert.equal(events.some(item=>item[0]==='revoke' && item[1]==='blob:2'),false);
"""
        subprocess.run([shutil.which("node"), "-e", script], check=True, capture_output=True, text=True)

    def test_export_snapshot_stays_consistent_during_concurrent_step(self):
        from multi_agent_election import render
        simulation = Simulation(make_scenario(example()))
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        entered, release = threading.Event(), threading.Event()
        results = {}
        try:
            html = urlopen(base + "/").read().decode()
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token, "Content-Type": "application/json"}
            real_plot = render.export_plot
            def delayed_plot(*args):
                entered.set()
                if not release.wait(3): raise RuntimeError("test did not release export")
                return real_plot(*args)
            def export():
                try:
                    request = Request(base + "/export?format=plot-svg&revision=0&frame=0", headers=headers)
                    with urlopen(request) as response: results["svg"] = response.read().decode()
                except Exception as exc:
                    results["error"] = exc
            with patch.object(render, "export_plot", side_effect=delayed_plot):
                downloader = threading.Thread(target=export, daemon=True); downloader.start()
                self.assertTrue(entered.wait(3))
                body = json.dumps({"action": "step", "revision": 0}).encode()
                with urlopen(Request(base + "/command", data=body, headers=headers, method="POST")) as response:
                    self.assertEqual(json.load(response)["frame"]["round"], 1)
                release.set(); downloader.join(timeout=3)
                self.assertFalse(downloader.is_alive())
            self.assertNotIn("error", results)
            self.assertIn("Round 0", results["svg"])
            self.assertNotIn("Round 1", results["svg"])
        finally:
            release.set(); server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_browser_export_uses_snapshot_without_stepping_and_validates_requests(self):
        data = example()
        data["interventions"] = [{"round": 1, "person": "2", "position": [0.1, 0.2], "ballot": ["C", "A"]}]
        simulation = Simulation(make_scenario(data)); simulation.run(2)
        before = simulation.checkpoint()
        server = make_server(simulation)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            html = urlopen(base + "/").read().decode()
            self.assertIn('id="export-format"', html)
            token = html.split('name="session-token" content="')[1].split('"')[0]
            headers = {"X-Session-Token": token}
            def fetch(query):
                return urlopen(Request(base + "/export?" + query, headers=headers))
            with patch.object(simulation, "step", side_effect=AssertionError("export must not simulate")):
                with fetch("format=csv&revision=0&frame=0") as response:
                    self.assertEqual(response.headers.get_content_type(), "text/csv")
                    rows = list(csv.DictReader(io.StringIO(response.read().decode())))
                self.assertEqual([row["winner"] for row in rows], ["A", "B", "A"])
                with fetch("format=plot-svg&revision=0&frame=1") as response:
                    self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
                    self.assertIn("Intervention round 1", response.read().decode())
                if importlib.util.find_spec("PIL"):
                    from PIL import Image
                    with fetch("format=network-png&revision=0&frame=0") as response:
                        first = response.read()
                    with fetch("format=network-png&revision=0&frame=1") as response:
                        second = response.read()
                    self.assertNotEqual(first, second)
                    with Image.open(io.BytesIO(second)) as image: image.verify()
                    with fetch("format=gif&revision=0&frame=1") as response:
                        self.assertEqual(response.headers.get_content_type(), "image/gif")
                        payload = response.read()
                    with Image.open(io.BytesIO(payload)) as image:
                        self.assertEqual(image.n_frames, 3)
                else:
                    with self.assertRaises(HTTPError) as missing:
                        fetch("format=gif&revision=0&frame=1")
                    self.assertIn("requires Pillow", missing.exception.read().decode())
                    missing.exception.close()
            for query in ("format=csv&revision=1", "format=csv&revision=0&frame=99",
                          "format=gif&revision=0&fps=0", "format=csv&revision=0&revision=0",
                          "format=bad&revision=0", "format=csv&revision=0&extra=x"):
                with self.subTest(query=query), self.assertRaises(HTTPError) as invalid:
                    fetch(query)
                self.assertEqual(invalid.exception.code, 400)
                invalid.exception.close()
            with self.assertRaises(HTTPError) as unauthorized:
                urlopen(base + "/export?format=csv&revision=0")
            self.assertEqual(unauthorized.exception.code, 403)
            unauthorized.exception.close()
            self.assertEqual(simulation.checkpoint(), before)
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

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
