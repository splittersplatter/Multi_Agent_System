"""Read-only browser timelines from streamed round-state recordings."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
import math
import secrets
from urllib.parse import urlsplit

from .model import ElectionError, make_scenario
from .population import require_simulation_population


def _reject_constant(value):
    raise ElectionError(f"non-finite JSON value in recording: {value}")


def load_recording(path):
    frames, metrics = [], []
    closed, truncated = False, False
    with path.open(encoding="utf-8") as handle:
        try:
            header = json.loads(next(handle), parse_constant=_reject_constant)
        except (StopIteration, json.JSONDecodeError) as exc:
            raise ElectionError("missing or invalid state-recording header") from exc
        if (not isinstance(header, dict) or header.get("type") != "header"
                or header.get("record_type") != "eclipse.round-states" or header.get("version") != 1):
            raise ElectionError("view requires a --save-states JSONL recording")
        scenario = make_scenario(header.get("scenario"))
        require_simulation_population(scenario)
        people = {p.id for p in scenario.people}
        parties = set(scenario.parties)
        groups = {g.id for g in scenario.groups}
        for line_number, line in enumerate(handle, 2):
            if closed:
                raise ElectionError("records after end marker")
            try:
                record = json.loads(line, parse_constant=_reject_constant)
            except json.JSONDecodeError as exc:
                if not line.endswith("\n"):
                    truncated = True
                    break
                raise ElectionError(f"invalid state record at line {line_number}") from exc
            if not isinstance(record, dict):
                raise ElectionError("state records must be JSON objects")
            if record.get("type") == "truncate":
                tick = record.get("after_round")
                if type(tick) is not int or not 0 <= tick < len(frames):
                    raise ElectionError("invalid recorded rewind boundary")
                frames, metrics = frames[:tick + 1], metrics[:tick + 1]
                continue
            if record.get("type") == "end":
                if not frames or record.get("last_round") != frames[-1]["round"]:
                    raise ElectionError("invalid recording end marker")
                closed = True
                continue
            frame, metric = record.get("data"), record.get("metric")
            if (record.get("type") != "frame" or not isinstance(frame, dict) or not isinstance(metric, dict)
                    or type(frame.get("round")) is not int or frame["round"] != len(frames)
                    or metric.get("round") != frame["round"]):
                raise ElectionError("recorded frames must start at zero and be consecutive")
            maps = ("positions", "preferences", "ballots", "groups", "overrides", "policy_memory")
            if any(not isinstance(frame.get(key), dict) or set(frame[key]) != people for key in maps):
                raise ElectionError("recorded frame has missing or unexpected nodes")
            if any(not isinstance(frame["groups"][p], str) or frame["groups"][p] not in groups
                   or not isinstance(frame["overrides"][p], dict) for p in people):
                raise ElectionError("invalid recorded group or overrides")
            for p in people:
                xy, pref, ballot = frame["positions"][p], frame["preferences"][p], frame["ballots"][p]
                if (not isinstance(xy, list) or len(xy) != 2
                        or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in xy)
                        or not isinstance(pref, list) or len(pref) != len(parties)
                        or any(not isinstance(c, str) for c in pref) or set(pref) != parties
                        or not isinstance(ballot, list) or len(ballot) != scenario.k
                        or any(not isinstance(c, str) or c not in parties for c in ballot)
                        or len(set(ballot)) != scenario.k):
                    raise ElectionError("invalid recorded node position, ranking or ballot")
            required_lists = ("persistent_edges", "proximity_edges", "campaign_edges", "delivered", "pending",
                              "phase_memory", "ballot_sensors", "interventions")
            if any(not isinstance(frame.get(key), list) for key in required_lists):
                raise ElectionError("incomplete browser frame")
            if not isinstance(frame.get("private_channels"), dict):
                raise ElectionError("incomplete recorded private-channel map")
            for key in ("persistent_edges", "proximity_edges", "campaign_edges"):
                if any(not isinstance(e, list) or len(e) != 2 or any(not isinstance(p, str) or p not in people for p in e)
                       for e in frame[key]):
                    raise ElectionError("recorded edge references an unknown node")
            counts = {c: sum(b[0] == c for b in frame["ballots"].values()) for c in scenario.parties}
            winner = max(scenario.parties, key=counts.get)
            if (frame.get("counts") != counts or frame.get("winner") != winner
                    or metric.get("counts") != counts or metric.get("winner") != winner
                    or metric.get("shares") != {c: counts[c] / len(people) for c in scenario.parties}):
                raise ElectionError("recorded tally/metrics disagree with submitted ballots")
            frames.append(frame)
            metrics.append(metric)
    if not frames:
        raise ElectionError("recording has no complete frames")
    return scenario, header, frames, metrics, closed and not truncated


def playback_snapshot(scenario, header, frames, metrics, closed):
    return {"revision": 0, "read_only": True, "recording_closed": closed,
            "parties": scenario.parties, "k": scenario.k, "frames": frames, "metrics": metrics,
            "group_names": [g.id for g in scenario.groups],
            "group_capabilities": {g.id: asdict(g.capabilities) for g in scenario.groups},
            "proximity_radius": scenario.radius, "proximity_mode": scenario.proximity_mode,
            "group_proximity_radii": {g.id: g.proximity_radius for g in scenario.groups},
            "coalitions": [asdict(c) for c in scenario.coalitions],
            "nomination": ({**scenario.nomination.as_dict(), "ideals": {p.id: p.ideal for p in scenario.people}}
                           if scenario.nomination else None),
            **{key: asdict(getattr(scenario, key)) if getattr(scenario, key) else None
               for key in ("campaign_controller", "signal_controller", "alignment", "detector", "leaders")},
            "convergence_case": None, "startup_voting_locked": True, "voting_policies": [],
            "startup_voting": {g.id: {"policy": g.voting, "parameters": json.loads(g.parameters).get("voting", {})}
                               for g in scenario.groups},
            "source_manifest": header.get("manifest"),
            **({"majority_estimation": scenario.majority_estimation.as_dict()} if scenario.majority_estimation else {})}


def make_playback_server(path, port=0):
    scenario, header, frames, metrics, closed = load_recording(path)
    snapshot = playback_snapshot(scenario, header, frames, metrics, closed)
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, payload, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            url = urlsplit(self.path)
            assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                      "/edit.js": ("edit.js", "text/javascript"), "/download.js": ("download.js", "text/javascript"),
                      "/inspector.js": ("inspector.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
            if url.path in assets and not url.query:
                name, content_type = assets[url.path]
                payload = resources.files("multi_agent_election").joinpath("web", name).read_bytes()
                if name == "index.html":
                    payload = payload.replace(b"__SESSION_TOKEN__", token.encode())
                self.send(200, payload, content_type + "; charset=utf-8")
            elif url.path == "/state" and not url.query:
                if self.headers.get("X-Session-Token") != token:
                    self.send(403, b'{"error":"invalid session token"}', "application/json")
                    return
                self.send(200, json.dumps(snapshot, allow_nan=False).encode(), "application/json; charset=utf-8")
            else:
                self.send(404, b'{"error":"recorded playback supports viewing only"}', "application/json")

        def do_POST(self):
            self.send(405, b'{"error":"recorded playback is read-only"}', "application/json")

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
