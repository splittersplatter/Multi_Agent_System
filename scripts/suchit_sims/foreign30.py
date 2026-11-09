"""30-person foreign-intelligence scenarios for the browser viewer: 25 residents + 5 spies.

Seed 6 was chosen from 40 as a clear demonstration (silent spies: A wins; blind lies: A wins;
dossier-guided lies: B leads 26 of 30 rounds). It is a showcase, not a representative sample;
see docs/suchit_sims/foreign_intelligence for the averaged 100-person results.

Writes four TOML files next to this script (same town, same seed):
    foreign30_silent.toml          spies present but silent (control)
    foreign30_blind.toml           lies to random followers
    foreign30_sight.toml           lies guided by a preference dossier
    foreign30_sight_eavesdrop.toml dossier + listening to a nearby group chat
"""

import math
import random
from pathlib import Path

from common import to_toml

PARTIES = ["A", "B", "C"]
TARGET = "B"


def build(mode: str, seed: int = 6) -> dict:
    rng = random.Random(seed)
    people, residents = [], []
    firsts = ["A"] * 10 + ["B"] * 9 + ["C"] * 6   # close race: A leads, B is the underdog the spies back
    rng.shuffle(firsts)
    for i, first in enumerate(firsts):
        rest = [p for p in PARTIES if p != first]
        rng.shuffle(rest)
        u = rng.random()
        group = "committed" if u < 0.4 else "trusting" if u < 0.8 else "sensor"
        pid = f"r{i:02d}"
        residents.append(pid)
        people.append({"id": pid, "group": group, "preference": [first] + rest,
                       "position": [round(rng.uniform(.05, .95), 4), round(rng.uniform(.05, .95), 4)]})
    pos = {p["id"]: p["position"] for p in people}
    chats = {}
    for c, centre in enumerate(rng.sample(residents, 5)):
        chats[f"chat{c}"] = sorted(residents, key=lambda r: math.dist(pos[r], pos[centre]))[:5]
    attack = mode != "silent"
    sight = mode in ("sight", "sight_eavesdrop")
    eaves = mode == "sight_eavesdrop"
    persistent, coalitions = [], []
    for s in range(5):
        anchor = rng.choice(residents)
        position = [round(min(.95, max(.05, pos[anchor][0] + rng.uniform(-.05, .05))), 4),
                    round(min(.95, max(.05, pos[anchor][1] + rng.uniform(-.05, .05))), 4)]
        cover = rng.choice(["A", "C"])
        sid = f"spy{s}"
        people.append({"id": sid, "group": "spies", "preference": [cover, "B", "C" if cover == "A" else "A"], "position": position})
        pos[sid] = position
        followers = sorted(residents, key=lambda r: math.dist(pos[r], position))[:6]
        persistent += [[sid, r] for r in followers]
        ordered = sorted(chats, key=lambda c: min(math.dist(pos[m], position) for m in chats[c] if m in residents))
        chats[ordered[0]].append(sid)
        cell = {"id": f"cell_{sid}", "members": [sid], "target": TARGET,
                "report_budget_per_round": 2 if attack else 0, "report_budget_total": 40 if attack else 0}
        if sight:
            cell.update({"sight_targets": followers, "sight_budget_per_round": len(followers), "sight_budget_total": len(followers)})
        if eaves:
            cell.update({"eavesdrop_channels": [ordered[1]], "eavesdrop_budget_per_round": 4, "eavesdrop_budget_total": 80})
        coalitions.append(cell)
    return {
        "parties": PARTIES, "k": 1, "seed": seed, "rounds": 30,
        "groups": {
            "committed": {"voting": "sincere", "movement": "random_walk", "max_step": 0.015, "communication": "truthful"},
            "trusting": {"voting": "local_plurality", "movement": "random_walk", "max_step": 0.015, "communication": "truthful"},
            "sensor": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.015, "communication": "truthful",
                       "capabilities": {"sense_public_ballots": True}},
            "spies": {"voting": "sincere", "movement": "random_walk", "max_step": 0.01,
                      "communication": "python:spy_comms:disinform" if attack else "none",
                      "parameters": {"target": TARGET, "mode": mode if attack else "blind"},
                      "capabilities": {"observe_target_preferences": sight, "intercept_private_reports": eaves,
                                       "receive_private_reports": True, "send_private_reports": True}},
        },
        "network": {"radius": 0.22, "persistent_edges": persistent, "private_channels": chats},
        "coalitions": coalitions,
        "people": people,
    }


if __name__ == "__main__":
    here = Path(__file__).parent
    for mode in ("silent", "blind", "sight", "sight_eavesdrop"):
        out = here / f"foreign30_{mode}.toml"
        out.write_text(to_toml(build(mode)), encoding="utf-8")
        print(out.name)
