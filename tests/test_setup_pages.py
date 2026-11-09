"""Setup (/setup) and watch (/sim) pages: scenario import/export, validation, launch and bulk edits."""

import json
import threading
import tomllib
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from verification_support import VerificationTestCase
from multi_agent_election import Simulation, make_scenario
from multi_agent_election.model import ElectionError
from multi_agent_election.scenario_io import parse_scenario_text, to_toml
from multi_agent_election.visual import make_server
from test_baseline import example


class ScenarioTextTests(VerificationTestCase):
    def test_toml_round_trips_canonical_scenarios(self):
        config = make_scenario(example()).as_dict()
        config["groups"]["residents"]["parameters"] = {"voting": {"top_k": 2}, "note": 'quote " and \\ slash'}
        config["people"][0]["overrides"] = {"proximity_radius": 0.25}
        self.assertEqual(tomllib.loads(to_toml(config)), config)
        self.assertEqual(parse_scenario_text(to_toml(config)), config)
        self.assertEqual(parse_scenario_text(json.dumps(config)), config)

    def test_parse_reports_errors_plainly(self):
        for text, fragment in (("", "paste"), ("parties = [oops", "TOML error"), ('{"parties": [', "JSON error"), ("[1, 2]", "TOML error")):
            with self.subTest(text=text), self.assertRaisesRegex(ElectionError, fragment):
                parse_scenario_text(text)
        with self.assertRaisesRegex(ElectionError, "finite"):
            to_toml({"x": float("nan")})


class SetupServerTests(VerificationTestCase):
    def setUp(self):
        self.server = make_server(Simulation(make_scenario(example())))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True); self.worker.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        html = urlopen(self.base + "/setup").read().decode()
        self.token = html.split('name="session-token" content="')[1].split('"')[0]

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.worker.join(timeout=2)

    def get(self, path):
        with urlopen(Request(self.base + path, headers={"X-Session-Token": self.token})) as response:
            return json.load(response)

    def post(self, path, body, status=200):
        request = Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                          headers={"X-Session-Token": self.token, "Content-Type": "application/json"})
        try:
            with urlopen(request) as response:
                self.assertEqual(status, 200); return json.load(response)
        except HTTPError as error:
            with error:
                self.assertEqual(error.code, status, error.read()); return None

    def test_pages_and_assets_are_served_with_the_session_token(self):
        for path in ("/", "/classic", "/setup", "/sim"):
            with self.subTest(path=path), urlopen(self.base + path) as response:
                page = response.read().decode()
                self.assertIn(self.token, page); self.assertNotIn("__SESSION_TOKEN__", page)
        for path, kind in (("/eclipse.css", "text/css"), ("/shared.js", "text/javascript"), ("/setup.js", "text/javascript"), ("/sim.js", "text/javascript")):
            with self.subTest(path=path), urlopen(self.base + path) as response:
                self.assertTrue(response.headers["Content-Type"].startswith(kind))

    def test_scenario_export_convert_and_validate(self):
        exported = self.get("/scenario")
        self.assertEqual(exported["config"], self.server.session.simulation.scenario.as_dict())
        self.assertEqual(tomllib.loads(exported["toml"]), exported["config"])
        converted = self.post("/scenario/convert", {"text": exported["toml"]})
        self.assertEqual(converted["config"], exported["config"])
        self.assertEqual(json.loads(converted["json"]), exported["config"])
        summary = self.post("/scenario/validate", {"config": exported["config"]})
        self.assertEqual((summary["people"], summary["groups"]), (4, {"residents": 4}))
        self.post("/scenario/validate", {"config": {**exported["config"], "bogus": 1}}, status=400)
        self.post("/scenario/convert", {"text": "parties = ["}, status=400)
        with self.assertRaises(HTTPError) as denied:
            urlopen(Request(self.base + "/scenario"))
        self.assertEqual(denied.exception.code, 403); denied.exception.close()

    def test_launch_replaces_the_simulation_with_exact_people_and_seed(self):
        config = self.get("/scenario")["config"]
        config["seed"] = 4242
        config["people"][0]["position"] = [0.125, 0.875]
        config["people"][0]["preference"] = ["C", "B", "A"]
        result = self.post("/scenario/launch", {"config": config})
        self.assertEqual(result["revision"], 1)
        state = self.get("/state")
        self.assertEqual(len(state["frames"]), 1)
        self.assertEqual(state["frames"][0]["positions"]["1"], [0.125, 0.875])
        self.assertEqual(state["frames"][0]["preferences"]["1"], ["C", "B", "A"])
        self.assertEqual(self.get("/scenario")["config"]["seed"], 4242)
        self.post("/scenario/launch", {"config": {**config, "people": []}}, status=400)
        self.assertEqual(self.get("/state")["revision"], 1)

    def test_bulk_edit_applies_per_person_changes_together(self):
        revision = 0
        for _ in range(3):
            revision = self.post("/command", {"action": "step", "revision": revision})["revision"]
        snapshot = self.post("/command", {"action": "bulk_edit", "revision": revision, "round": 1, "edits": [
            {"person": "1", "changes": {"preference": ["C", "A", "B"], "position": [0.9, 0.9]}},
            {"person": "2", "changes": {"preference": ["C", "A", "B"], "position": [0.8, 0.8]}}]})
        self.assertEqual(len(snapshot["frames"]), 2)
        frame = self.post("/command", {"action": "step", "revision": snapshot["revision"]})["frame"]
        self.assertEqual(frame["positions"]["1"], [0.9, 0.9]); self.assertEqual(frame["positions"]["2"], [0.8, 0.8])
        self.assertEqual(frame["preferences"]["2"], ["C", "A", "B"])

    def test_failed_bulk_edit_leaves_history_untouched(self):
        revision = 0
        for _ in range(3):
            revision = self.post("/command", {"action": "step", "revision": revision})["revision"]
        before = self.server.session.simulation.checkpoint()
        self.post("/command", {"action": "bulk_edit", "revision": revision, "round": 1, "edits": [
            {"person": "1", "changes": {"position": [0.5, 0.5]}},
            {"person": "nobody", "changes": {"position": [0.5, 0.5]}}]}, status=400)
        for edits in ([], [{"person": "1", "changes": {"add_edges": ["2"]}}],
                      [{"person": "1", "changes": {"position": [0.1, 0.1]}}, {"person": "1", "changes": {"position": [0.2, 0.2]}}]):
            with self.subTest(edits=edits):
                self.post("/command", {"action": "bulk_edit", "revision": revision, "round": 1, "edits": edits}, status=400)
        self.assertEqual(self.server.session.simulation.checkpoint(), before)
        self.assertEqual(self.get("/state")["revision"], revision)
