"""Compare trusted Git-baseline orchestration with current code using one engine."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multi_agent_election import make_scenario
from multi_agent_election import combined, experiments
from multi_agent_election.provenance import manifest
from multi_agent_election.population import verification_scope


def fingerprint(value):
    """Only measured wall time is excluded; retain all scientific/model fields."""
    if isinstance(value, dict):
        return {k: fingerprint(v) for k, v in value.items() if k != "runtime_seconds"}
    if isinstance(value, list):
        return [fingerprint(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def baseline_module(commit, name):
    source = subprocess.run(["git", "show", f"{commit}:src/multi_agent_election/{name}.py"],
                            cwd=ROOT, check=True, capture_output=True, text=True).stdout
    module = types.ModuleType("multi_agent_election._audit_" + name)
    module.__package__ = "multi_agent_election"
    exec(compile(source, f"{commit}:{name}.py", "exec"), module.__dict__)
    return module


def load(name):
    return make_scenario(tomllib.loads((ROOT / "examples" / (name + ".toml")).read_text()))


@verification_scope("comparison orchestration regression, not outcome study")
def audit(commit):
    old = baseline_module(commit, "experiments")
    old_combined = baseline_module(commit, "combined")
    seeds = [1, 2]
    cases = [
        ("batch", (load("network"), seeds, "A"), {}),
        ("compare_heuristics", (load("heuristics"), seeds, ["sincere", "top_k", "maximin"]), {"rounds": 3}),
        ("compare_proximity", (load("group-radius"), seeds), {"calibration_seeds": [10, 11]}),
        ("coalition_ablations", (load("coalition-combined"), seeds), {}),
        ("compare_campaign_policies", (load("campaign-controller"), seeds), {}),
        ("exhaustive_one_round_campaign", (load("campaign-exhaustive"),), {}),
        ("compare_signal_responses", (load("epistemic-public-signal"), seeds, ["signal_voter"], 1), {}),
        ("compare_nominations", (load("nomination"), seeds), {}),
        ("compare_alignment", (load("alignment-attack"), seeds), {}),
        ("calibrate_and_evaluate_detector", (load("detector"), [10, 11], seeds, 0.2), {}),
        ("compare_leaders", (load("leader-adaptation"), seeds), {}),
        ("combined_ablation", (load("all-enabled"), seeds, "alice"), {}),
    ]
    rows = []
    for name, args, kwargs in cases:
        before_module, after_module = (old_combined, combined) if name == "combined_ablation" else (old, experiments)
        row = {"name": name}
        try:
            before = fingerprint(getattr(before_module, name)(*args, **kwargs))
            after = fingerprint(getattr(after_module, name)(*args, **kwargs))
            row.update(status="same" if before == after else "changed",
                       baseline_sha256=digest(before), current_sha256=digest(after))
        except Exception as exc:
            row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    return {"record_type": "eclipse.comparison-orchestration-audit", "record_version": 1,
            "baseline_commit": commit, "manifest": manifest(), "seeds": seeds,
            "scope": "Trusted baseline functions and current functions both use the current engine; wall time excluded.",
            "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True, help="trusted local Git revision; its Python functions are executed")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be new, with an existing parent directory")
    commit = subprocess.run(["git", "rev-parse", "--verify", "--end-of-options", args.baseline_ref + "^{commit}"],
                            cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    result = audit(commit)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    failures = [row["name"] for row in result["rows"] if row["status"] != "same"]
    print(json.dumps({"comparisons": len(result["rows"]), "different_or_failed": failures, "output": str(args.output)}))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
