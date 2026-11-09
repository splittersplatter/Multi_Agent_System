"""Optional streaming of committed frames for later browser playback."""

from contextvars import ContextVar
import json
from pathlib import Path

from .model import ElectionError

active_recordings = ContextVar("eclipse_round_recordings", default=None)


class RecordingGroup:
    def __init__(self, prefix):
        self.prefix = Path(prefix)
        self.recorders = []

    def register(self, simulation):
        index = len(self.recorders) + 1
        suffix = "" if index == 1 else f"-{index:04d}"
        path = self.prefix.with_name(self.prefix.name + suffix + ".jsonl")
        recorder = RoundRecorder(path, simulation)
        self.recorders.append(recorder)
        return recorder

    def close(self):
        error = None
        for recorder in self.recorders:
            try:
                recorder.close()
            except OSError as exc:
                error = exc
        if error:
            raise error


class RoundRecorder:
    def __init__(self, path, simulation):
        self.path = path
        self.owner = active_recordings.get()
        self.previous = None
        self.scenario = simulation.scenario
        self.handle = path.open("x", encoding="utf-8")
        try:
            self._write({"type": "header", "record_type": "eclipse.round-states", "version": 1,
                         "scenario": simulation.scenario.as_dict(), "manifest": simulation.runtime_manifest,
                         "verification_reason": simulation.verification_reason,
                         "purpose": "recorded browser playback; use full checkpoints for verified resume"})
            self.append(simulation.current)
        except BaseException:
            self.handle.close()
            raise

    def _write(self, value):
        data = json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n"
        offset = self.handle.tell()
        try:
            self.handle.write(data)
            self.handle.flush()
        except OSError:
            # Best-effort removal of a partial record; retain earlier completed lines.
            try:
                self.handle.seek(offset)
                self.handle.truncate()
                self.handle.flush()
            except OSError:
                pass
            raise

    def append(self, frame):
        from .metrics import frame_metrics
        if self.previous is not None and frame.round != self.previous.round + 1:
            raise ElectionError("state recording requires consecutive committed rounds")
        self._write({"type": "frame", "data": frame.as_dict(),
                     "metric": frame_metrics(self.scenario, frame, self.previous)})
        self.previous = frame

    def truncate(self, frame):
        self._write({"type": "truncate", "after_round": frame.round})
        self.previous = frame

    def close(self):
        if not self.handle.closed:
            try:
                self._write({"type": "end", "last_round": self.previous.round})
            finally:
                self.handle.close()
