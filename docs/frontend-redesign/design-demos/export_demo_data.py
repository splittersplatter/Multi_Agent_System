"""Export one real showcase100 run (40 rounds) as compact JSON for the design drafts.

    python docs/frontend-redesign/design-demos/export_demo_data.py
"""

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts" / "suchit_sims" / "plugins")]

from multi_agent_election.engine import Simulation  # noqa: E402
from multi_agent_election.model import apply_overrides, make_scenario  # noqa: E402

ROUNDS = 40
scenario = make_scenario(tomllib.loads((ROOT / "scripts/suchit_sims/showcase100.toml").read_text(encoding="utf-8")))
sim = Simulation(scenario)
for _ in range(ROUNDS):
    sim.step()

groups = {g.id: g for g in scenario.groups}
people = []
for p in scenario.people:
    g = apply_overrides(groups[p.group], p.overrides)
    radius = g.proximity_radius if g.proximity_radius is not None else scenario.radius
    caps = g.capabilities
    powers = [name for name, on in (("senses ballots", caps.sense_public_ballots), ("reads poll", caps.observe_public_signal),
                                     ("buys follow links", caps.modify_persistent_edges), ("sees roster", caps.observe_electorate)) if on]
    people.append({"id": p.id, "group": p.group, "pref": list(p.preference), "radius": radius,
                   "voting": g.voting, "movement": g.movement.replace("python:echo_campaign:", "campaign "), "powers": powers})

index = {p["id"]: i for i, p in enumerate(people)}
frames = []
for f in sim.frames:
    pos = dict(f.positions)
    ballots = dict(f.ballots)
    signal = f.signal_latest
    frames.append({
        "r": f.round,
        "xy": [[round(pos[p["id"]][0], 4), round(pos[p["id"]][1], 4)] for p in people],
        "v": "".join(ballots[p["id"]][0] for p in people),
        "counts": dict(f.counts),
        "follow": [[index[a], index[b]] for a, b in f.persistent_edges],
        "campaign": [[index[a], index[b]] for a, b in f.campaign_edges],
        "signal": None if signal is None else {"report": list(signal[2]), "truth": list(signal[3])},
        "spend": f.signal_spend,
        "det": None if f.detector is None else {"change": f.detector.share_change, "alert": f.detector.alert},
    })

out = {"parties": list(scenario.parties), "groups": sorted(groups), "people": people, "frames": frames,
       "source": "scripts/suchit_sims/showcase100.toml, seed 7, rounds 0-40, merged engine"}
target = Path(__file__).with_name("demo-data.json")
target.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(target, round(target.stat().st_size / 1024), "KB")
