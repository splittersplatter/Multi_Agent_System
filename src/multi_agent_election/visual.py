"""Local interactive view over the same simulation used by the CLI."""

import json
import secrets
import tempfile
import threading
from contextlib import nullcontext
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .engine import Simulation
from .exports import write_metrics_csv
from .metrics import frame_metrics, series
from .model import ElectionError
from .population import verification_scope
from .state_recording import active_recordings
from .voting import VOTING_POLICIES, COALITION_POLICIES, SIGNAL_POLICIES, configure_voting
from .epistemic import EPISTEMIC_POLICIES


class Session:
    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.revision = 0
        self.token = secrets.token_urlsafe(24)
        self.lock = threading.RLock()

    def snapshot(self) -> dict[str, Any]:
        return {"revision": self.revision, "parties": self.simulation.scenario.parties,
                **({"verification_only": True, "verification_reason": self.simulation.verification_reason}
                   if self.simulation.verification_reason is not None else {}),
                "k": self.simulation.scenario.k,
                "group_names": [g.id for g in self.simulation.scenario.groups],
                "group_capabilities": {g.id: asdict(g.capabilities) for g in self.simulation.scenario.groups},
                "proximity_radius": self.simulation.scenario.radius,
                "proximity_mode": self.simulation.scenario.proximity_mode,
                "group_proximity_radii": {g.id: g.proximity_radius for g in self.simulation.scenario.groups},
                "campaign_controller": asdict(self.simulation.scenario.campaign_controller) if self.simulation.scenario.campaign_controller else None,
                "signal_controller": asdict(self.simulation.scenario.signal_controller) if self.simulation.scenario.signal_controller else None,
                "nomination": ({**self.simulation.scenario.nomination.as_dict(),
                                "ideals": {p.id: p.ideal for p in self.simulation.scenario.people}}
                               if self.simulation.scenario.nomination is not None else None),
                "alignment": asdict(self.simulation.scenario.alignment) if self.simulation.scenario.alignment else None,
                "detector": asdict(self.simulation.scenario.detector) if self.simulation.scenario.detector else None,
                "leaders": asdict(self.simulation.scenario.leaders) if self.simulation.scenario.leaders else None,
                "coalitions": [{"id":c.id,"members":list(c.members),"target":c.target,
                                 "report_budget_per_round":c.report_budget_per_round,
                                 "report_budget_total":c.report_budget_total,
                                 **({"sight_targets":list(c.sight_targets),"sight_budget_per_round":c.sight_budget_per_round,
                                     "sight_budget_total":c.sight_budget_total} if c.sight_targets else {}),
                                 **({"eavesdrop_channels":list(c.eavesdrop_channels),"eavesdrop_budget_per_round":c.eavesdrop_budget_per_round,
                                     "eavesdrop_budget_total":c.eavesdrop_budget_total} if c.eavesdrop_channels else {})} for c in self.simulation.scenario.coalitions],
                "convergence_case": self.simulation.scenario.convergence_case,
                "voting_policies": ([self.simulation.scenario.convergence_case] if self.simulation.scenario.convergence_case else
                                    sorted(({g.voting for g in self.simulation.scenario.groups} | set(VOTING_POLICIES) | set(COALITION_POLICIES) | set(SIGNAL_POLICIES) | set(EPISTEMIC_POLICIES)) - {"direct_best_response"})),
                "startup_voting": {g.id: {"policy": g.voting, "parameters": json.loads(g.parameters).get("voting", {})}
                                   for g in self.simulation.scenario.groups},
                "startup_voting_locked": bool(self.simulation.scenario.convergence_case) or self.simulation.current.round != 0 or bool(self.simulation.manual_interventions),
                "frames": [frame.as_dict() for frame in self.simulation.frames],
                **({"majority_estimation": self.simulation.scenario.majority_estimation.as_dict()}
                   if self.simulation.scenario.majority_estimation is not None else {}),
                "metrics": series(self.simulation.scenario, self.simulation.frames)}

    def command(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or type(value.get("revision")) is not int:
            raise ElectionError("command requires a revision")
        if value["revision"] != self.revision:
            raise ElectionError("stale revision; reload current state")
        if value.get("action") == "configure_voting" and set(value) == {"revision", "action", "policy", "parameters"}:
            if self.simulation.current.round != 0 or self.simulation.manual_interventions:
                raise ElectionError("voting choice is only available before the first step/edit; restart for another episode")
            configured = configure_voting(self.simulation.scenario, value["policy"], value["parameters"])
            # Preserve explicit verification purpose across HTTP worker threads;
            # clients cannot enable it through a command or scenario field.
            reason = self.simulation.verification_reason
            owner = self.simulation.state_recorder.owner if self.simulation.state_recorder else None
            recording_token = active_recordings.set(owner)
            try:
                with verification_scope(reason) if reason is not None else nullcontext():
                    self.simulation = Simulation(configured)
            finally:
                active_recordings.reset(recording_token)
        elif value.get("action") == "step" and set(value) == {"revision", "action"}:
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
        def _send(self, status: int, data: bytes, content_type: str, filename: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if filename is not None:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status: int, value: Any) -> None:
            self._send(status, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            if url.path in ("/", "/app.js", "/edit.js", "/download.js", "/inspector.js", "/style.css") and not url.query:
                name = {"/": "index.html", "/app.js": "app.js", "/edit.js": "edit.js", "/download.js": "download.js", "/inspector.js": "inspector.js", "/style.css": "style.css"}[url.path]
                payload = resources.files("multi_agent_election").joinpath("web", name).read_bytes()
                if name == "index.html":
                    payload = payload.replace(b"__SESSION_TOKEN__", session.token.encode())
                kind = {"index.html": "text/html", "app.js": "text/javascript", "edit.js": "text/javascript", "download.js": "text/javascript", "inspector.js": "text/javascript", "style.css": "text/css"}[name]
                self._send(200, payload, kind + "; charset=utf-8")
            elif url.path == "/state" and not url.query:
                if self.headers.get("X-Session-Token") != session.token:
                    self._json(403, {"error": "invalid session token"}); return
                with session.lock:
                    self._json(200, session.snapshot())
            elif url.path == "/checkpoint":
                if self.headers.get("X-Session-Token") != session.token:
                    self._json(403, {"error": "invalid session token"}); return
                try:
                    revision = None
                    if url.query:
                        query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True, max_num_fields=2)
                        if set(query) != {"revision"} or len(query["revision"]) != 1:
                            raise ElectionError("invalid checkpoint parameters")
                        revision = int(query["revision"][0])
                    with session.lock:
                        if revision is not None and revision != session.revision:
                            raise ElectionError("stale revision; reload current state")
                        self._json(200, session.simulation.checkpoint())
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
            elif url.path == "/export":
                if self.headers.get("X-Session-Token") != session.token:
                    self._json(403, {"error": "invalid session token"}); return
                try:
                    query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True, max_num_fields=5)
                    if set(query) - {"format", "revision", "frame", "stride", "fps"} or any(len(values) != 1 for values in query.values()):
                        raise ElectionError("invalid export parameters")
                    kind = query.get("format", [""])[0]
                    if kind not in {"csv", "plot-svg", "plot-png", "network-png", "gif"}:
                        raise ElectionError("unsupported export format")
                    if "revision" not in query:
                        raise ElectionError("export requires a revision")
                    revision = int(query["revision"][0])
                    frame_number = int(query.get("frame", ["0"])[0])
                    stride = int(query.get("stride", ["1"])[0])
                    fps = int(query.get("fps", ["5"])[0])
                    if stride < 1 or not 1 <= fps <= 100:
                        raise ElectionError("stride must be positive; fps must be 1..100")
                    with session.lock:
                        if revision != session.revision:
                            raise ElectionError("stale revision; reload current state")
                        scenario = session.simulation.scenario
                        frames = tuple(session.simulation.frames)
                        if not 0 <= frame_number < len(frames):
                            raise ElectionError("frame index is out of range")
                    formats = {"csv": ("metrics.csv", "text/csv; charset=utf-8"),
                               "plot-svg": ("shares.svg", "image/svg+xml"),
                               "plot-png": ("shares.png", "image/png"),
                               "network-png": ("network.png", "image/png"), "gif": ("evolution.gif", "image/gif")}
                    filename, content_type = formats[kind]
                    with tempfile.TemporaryDirectory(prefix="eclipse-export-") as directory:
                        path = Path(directory) / filename
                        if kind == "csv":
                            write_metrics_csv(path, scenario, series(scenario, frames))
                        else:
                            from .render import export_gif, export_network, export_plot
                            if kind == "plot-svg": export_plot(scenario, frames, path, "svg")
                            elif kind == "plot-png": export_plot(scenario, frames, path, "png")
                            elif kind == "network-png": export_network(scenario, frames[frame_number], path)
                            else: export_gif(scenario, frames, path, stride, fps)
                        data = path.read_bytes()
                    self._send(200, data, content_type, "eclipse-" + filename)
                except (ValueError, OSError, ElectionError) as exc:
                    self._json(400, {"error": str(exc)})
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

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.session = session
    return server
