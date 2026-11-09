"""Bounded example regression fingerprints; records are not research outcomes."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.metrics import series
from multi_agent_election.provenance import manifest
from multi_agent_election.population import verification_scope


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@verification_scope("bounded example regression audit, not outcome simulation")
def audit(max_rounds):
    rows = []
    for path in sorted((ROOT / "examples").glob("*.toml")):
        row = {"path": str(path.relative_to(ROOT)), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        try:
            scenario = make_scenario(tomllib.loads(path.read_text(encoding="utf-8")))
            horizon = min(max_rounds, scenario.rounds)
            sim = Simulation(scenario)
            sim.run(horizon)
            replay = Simulation.from_checkpoint(sim.checkpoint())
            frames = [frame.as_dict() for frame in sim.frames]
            metrics = series(scenario, sim.frames)
            if replay.frames != sim.frames:
                raise AssertionError("checkpoint replay disagrees")
            expected = sim.step()
            if replay.step() != expected:
                raise AssertionError("resumed next round disagrees")
            row.update(status="ok", people=len(scenario.people), configured_rounds=scenario.rounds,
                       checked_rounds=horizon, frames_sha256=digest(frames), metrics_sha256=digest(metrics),
                       next_frame_sha256=digest(expected.as_dict()), checkpoint_replay=True)
        except Exception as exc:
            row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    return {"record_type": "eclipse.implementation-audit", "record_version": 1,
            "manifest": manifest(), "max_rounds": max_rounds, "rows": rows}


def compare(before, after):
    """Exclude runtime fingerprints only; compare every scenario result field."""
    if before.get("record_type") != after["record_type"] or before.get("record_version") != after["record_version"]:
        raise ValueError("incompatible audit record")
    if before.get("max_rounds") != after["max_rounds"]:
        raise ValueError("audit horizons differ")
    old = {row["path"]: row for row in before["rows"]}
    new = {row["path"]: row for row in after["rows"]}
    return sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args(argv)
    if args.max_rounds < 0:
        parser.error("max-rounds must be nonnegative")
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be new, with an existing parent directory")
    baseline = json.loads(args.compare.read_text()) if args.compare else None
    record = audit(args.max_rounds)
    differences = compare(baseline, record) if baseline is not None else []
    if baseline is not None:
        record["comparison"] = {"path": str(args.compare), "changed_examples": differences}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, allow_nan=False)
        handle.write("\n")
    failed = [row["path"] for row in record["rows"] if row["status"] != "ok"]
    print(json.dumps({"examples": len(record["rows"]), "failures": failed, "changed_examples": differences,
                      "output": str(args.output)}))
    return int(bool(failed or differences))


if __name__ == "__main__":
    raise SystemExit(main())
