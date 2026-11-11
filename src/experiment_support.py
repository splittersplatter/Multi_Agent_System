"""Shared run lifecycle: provenance consistency and retained partial failures."""

from .engine import Simulation
from .metrics import series
from .model import ElectionError, Scenario, make_scenario
from .provenance import manifest


class RuntimeMismatch(ElectionError):
    """A comparison cannot combine different implementations."""


class ExperimentRunner:
    """One source/runtime identity across every arm in a comparison."""

    def __init__(self, label):
        self.label = label
        self.manifest = None

    def _check_manifest(self, current):
        if self.manifest is not None and current != self.manifest:
            raise RuntimeMismatch(f"runtime or core source changed between {self.label} runs")

    def execute(self, configuration):
        selected = None
        simulation = None
        # Check outside the recoverable failure handler, including after the last arm.
        self._check_manifest(manifest())
        try:
            selected = configuration if isinstance(configuration, Scenario) else make_scenario(configuration)
            simulation = Simulation(selected)
            self._check_manifest(simulation.runtime_manifest)
            self.manifest = simulation.runtime_manifest
            simulation.run()
            error = None
        except RuntimeMismatch:
            raise
        except ElectionError as exc:
            error = str(exc)
        self._check_manifest(manifest())
        record = {"status": "ok" if error is None else "failed",
                  "scenario": selected.as_dict() if selected is not None else configuration,
                  "frames": [frame.as_dict() for frame in simulation.frames] if simulation is not None else [],
                  "metrics": series(selected, simulation.frames) if simulation is not None else [],
                  "policy_digests": {name: digest for name, (_, digest, _) in simulation.plugins.items()}
                                    if simulation is not None else {}}
        if error is not None:
            record.update(error=error, completed_round=simulation.current.round if simulation is not None else None)
        return record, simulation


def movement_matched(run, control):
    """No prefix-only match: every timestamp and position must agree."""
    if control["status"] != "ok":
        return None
    return (len(run["frames"]) == len(control["frames"]) and
            all(a["round"] == b["round"] and a["positions"] == b["positions"]
                for a, b in zip(run["frames"], control["frames"])))
