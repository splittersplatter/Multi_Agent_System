"""Local interactive view over the same simulation used by the CLI."""

import json
import secrets
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any

from .engine import Simulation
from .metrics import frame_metrics, series
from .model import ElectionError


class Session:
    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.revision = 0
        self.token = secrets.token_urlsafe(24)
        self.lock = threading.RLock()

    def snapshot(self) -> dict[str, Any]:
        return {"revision": self.revision, "parties": self.simulation.scenario.parties,
                "k": self.simulation.scenario.k,
                "group_names": [g.id for g in self.simulation.scenario.groups],
                "group_capabilities": {g.id: asdict(g.capabilities) for g in self.simulation.scenario.groups},
                "voting_policies": sorted({g.voting for g in self.simulation.scenario.groups} | {"sincere", "local_plurality", "sensed_plurality"}),
                "frames": [frame.as_dict() for frame in self.simulation.frames],
                "metrics": series(self.simulation.scenario, self.simulation.frames)}

    def command(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or type(value.get("revision")) is not int:
            raise ElectionError("command requires a revision")
        if value["revision"] != self.revision:
            raise ElectionError("stale revision; reload current state")
        if value.get("action") == "step" and set(value) == {"revision", "action"}:
            previous = self.simulation.current
            self.simulation.step()
        elif value.get("action") == "edit" and set(value) == {"revision", "action", "round", "person", "changes"}:
            if not isinstance(value["changes"], dict):
                raise ElectionError("changes must be an object")
            self.simulation.edit_after(value["round"], value["person"], **value["changes"])
        else:
            raise ElectionError("unsupported command")
        self.revision += 1
        if value["action"] == "step":
            return {"revision": self.revision, "frame": self.simulation.current.as_dict(),
                    "metric": frame_metrics(self.simulation.scenario, self.simulation.current, previous)}
        return self.snapshot()


def make_server(simulation: Simulation, port: int = 0) -> ThreadingHTTPServer:
    session = Session(simulation)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, data: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status: int, value: Any) -> None:
            self._send(status, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            if self.path in ("/", "/app.js", "/edit.js", "/style.css"):
                name = {"/": "index.html", "/app.js": "app.js", "/edit.js": "edit.js", "/style.css": "style.css"}[self.path]
                payload = resources.files("multi_agent_election").joinpath("web", name).read_bytes()
                if name == "index.html":
                    payload = payload.replace(b"__SESSION_TOKEN__", session.token.encode())
                kind = {"index.html": "text/html", "app.js": "text/javascript", "edit.js": "text/javascript", "style.css": "text/css"}[name]
                self._send(200, payload, kind + "; charset=utf-8")
            elif self.path in ("/state", "/checkpoint"):
                if self.headers.get("X-Session-Token") != session.token:
                    self._json(403, {"error": "invalid session token"}); return
                with session.lock:
                    self._json(200, session.snapshot() if self.path == "/state" else session.simulation.checkpoint())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/command":
                self._json(404, {"error": "not found"}); return
            if self.headers.get("X-Session-Token") != session.token:
                self._json(403, {"error": "invalid session token"}); return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"error": "application/json required"}); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise ElectionError("invalid command size")
                data = json.loads(self.rfile.read(size))
                with session.lock:
                    response = session.command(data)
                self._json(200, response)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
