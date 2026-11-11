"""Run every engine setting of the talk (see experiments.py) on the team's unchanged engine.

From the repository root:

    PYTHONPATH=src:presentation python3 presentation/run_all.py             # everything
    PYTHONPATH=src:presentation python3 presentation/run_all.py --only e3_  # names starting with e3_
    PYTHONPATH=src:presentation python3 presentation/run_all.py --seeds 0 1 # quick check

Each finished run is appended to presentation/results/runs.jsonl, so an interrupted
run resumes where it stopped. Votes are stored per round as a string with one letter
per voter (L, R, C), in voter-id order, so any later measure can be computed without
rerunning the engine.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from experiments import all_settings  # noqa: E402
from town import build_town, minority_members, preferences, tie_order, types  # noqa: E402

RESULTS = HERE / "results"
LETTER = {"Left": "L", "Right": "R", "Centre": "C"}


def run_one(job: tuple[str, int]) -> dict:
    from multi_agent_election.engine import Simulation
    from multi_agent_election.model import make_scenario

    name, seed = job
    experiment, town, _ = all_settings()[name]
    raw = build_town(town, seed)
    started = time.time()
    sim = Simulation(make_scenario(raw))
    sim.run()
    frames = sim.frames
    ids = sorted(p["id"] for p in raw["people"])
    votes = ["".join(LETTER[dict(f.ballots)[i][0]] for i in ids) for f in frames]
    degree = [Counter(r for _, r in f.proximity_edges) for f in frames]
    labels = types(town, seed)
    for m in minority_members(town, seed):
        labels[m] = "minority"
    return {
        "setting": name, "experiment": experiment, "seed": seed,
        "radius": town.radius, "walking": town.walking, "mix": dict(town.mix),
        "minority": town.minority, "minority_party": town.minority_party or "", "followers": town.followers,
        "tie_order": raw["parties"],
        "types": "".join({"sincere": "s", "frontrunner": "f", "copycat": "c", "pivot": "p", "minority": "m"}[t]
                         for t in labels),
        "favourites": "".join(LETTER[p[0]] for p in preferences(town, seed)),
        "votes": votes,
        "counts": [dict(f.counts) for f in frames],
        "winners": [f.winner for f in frames],
        # number of people each voter hears through proximity (walking: changes every round)
        "mean_neighbours": [sum(d.values()) / len(ids) for d in degree],
        "degree_hist_round1": dict(sorted(Counter(degree[1].get(i, 0) for i in ids).items())) if len(degree) > 1 else {},
        "persistent_edges": len(raw["network"].get("persistent_edges", [])),
        "runtime_s": round(time.time() - started, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--seeds", type=int, nargs="*")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "runs.jsonl"
    done = set()
    packed = RESULTS / "runs.jsonl.gz"
    if not out.exists() and packed.exists():   # the branch ships the runs compressed
        import gzip
        out.write_bytes(gzip.decompress(packed.read_bytes()))
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["setting"], r["seed"]))
    jobs = [(name, seed) for name, (_, _, seeds) in all_settings().items() if name.startswith(args.only)
            for seed in (args.seeds if args.seeds is not None else seeds) if (name, seed) not in done]
    # slowest first (full information is quadratic), so the pool stays busy
    jobs.sort(key=lambda j: -all_settings()[j[0]][1].radius)
    print(f"{len(jobs)} runs to do, {len(done)} already done", flush=True)
    started = time.time()
    with Pool(args.workers) as pool, out.open("a") as fh:
        for i, row in enumerate(pool.imap_unordered(run_one, jobs), 1):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if i % 20 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} done, {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
