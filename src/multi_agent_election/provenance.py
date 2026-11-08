"""Runtime and implementation identity for reproducible simulation records."""

import hashlib
import platform
from pathlib import Path


def _digest(base: Path, names: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8") + b"\0")
        digest.update((base / name).read_bytes())
    return digest.hexdigest()


def manifest() -> dict[str, str | int]:
    base = Path(__file__).resolve().parent
    core = _digest(base, ("model.py", "engine.py", "network.py", "policies.py", "voting.py", "metrics.py", "epistemic.py", "campaign.py", "signals.py", "nomination.py", "alignment.py", "detector.py", "leaders.py", "provenance.py"))
    pipeline = _digest(base, ("cli.py", "experiments.py", "combined.py", "render.py", "visual.py"))
    return {"manifest_version": 1, "package": "multi-agent-election", "package_version": "0.1.0",
            "python": platform.python_version(), "implementation": platform.python_implementation(),
            "machine": platform.machine(), "core_sha256": core, "pipeline_sha256": pipeline,
            "randomness": "sha256-keyed Python random streams", "rng_schema": "actor-round-phase-v1"}
