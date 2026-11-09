"""Write a 100-agent showcase scenario for the browser viewer: echo chambers,
three campaign teams with different strategies, a paid campaign controller,
a rigged public poll with poll-trusting voters, and a watchdog alarm.

    python showcase100.py   ->  scripts/suchit_sims/showcase100.toml
"""

import random
from pathlib import Path

from common import pin_uniform_walk, to_toml

PARTIES = ["A", "B", "C"]
CHAMBERS = {"A": ((0.22, 0.28), 34), "B": ((0.78, 0.28), 30), "C": ((0.50, 0.78), 24)}  # 88 residents + 12 campaigners
RIVAL = {"A": "B", "B": "A", "C": "A"}
STRATEGY = {"A": "infiltrate", "B": "bridge", "C": "fortify"}


def build(seed=7):
    rng = random.Random(seed)
    people, campaigners = [], []
    n = 0
    for party, ((cx, cy), size) in CHAMBERS.items():
        loyal = round(0.65 * size)
        others = [p for p in PARTIES if p != party]
        firsts = [party] * loyal + [others[i % 2] for i in range(size - loyal)]
        rng.shuffle(firsts)
        for first in firsts:
            rest = [p for p in PARTIES if p != first]
            rng.shuffle(rest)
            u = rng.random()
            group = "copycats" if u < 0.5 else "committed" if u < 0.85 else "poll_watchers"
            people.append({"id": f"r{n:02d}", "group": group, "preference": [first] + rest,
                           "position": [round(min(.98, max(.02, rng.gauss(cx, .09))), 4),
                                        round(min(.98, max(.02, rng.gauss(cy, .09))), 4)]})
            n += 1
    for party, ((cx, cy), _) in CHAMBERS.items():
        for i in range(4):
            cid = f"camp{party}{i}"
            campaigners.append(cid)
            people.append({"id": cid, "group": f"team_{party}", "preference": [party] + [p for p in PARTIES if p != party],
                           "position": [round(cx + rng.uniform(-.04, .04), 4), round(cy + rng.uniform(-.04, .04), 4)]})
    groups = {
        "copycats": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.012, "proximity_radius": 0.1,
                     "communication": "truthful", "capabilities": {"sense_public_ballots": True}},
        "committed": {"voting": "sincere", "movement": "random_walk", "max_step": 0.012, "proximity_radius": 0.1,
                      "communication": "truthful"},
        "poll_watchers": {"voting": "signal_confident", "movement": "random_walk", "max_step": 0.012, "proximity_radius": 0.1,
                          "communication": "truthful", "capabilities": {"observe_public_signal": True}},
    }
    for party in PARTIES:
        groups[f"team_{party}"] = {
            "voting": "sincere", "movement": "python:echo_campaign:move", "max_step": 0.06,
            "graph": "python:echo_campaign:link", "proximity_radius": 0.3, "communication": "truthful",
            "parameters": {"strategy": STRATEGY[party], "party": party, "home": list(CHAMBERS[party][0]),
                           "rival": list(CHAMBERS[RIVAL[party]][0]), "max_step": 0.06, "max_active": 6,
                           "new_per_round": 2, "campaigners": campaigners},
            "capabilities": {"sense_public_ballots": True, "observe_electorate": True, "modify_persistent_edges": True}}
    return pin_uniform_walk({"parties": PARTIES, "k": 2, "seed": seed, "rounds": 60, "groups": groups,
            "network": {"radius": 0.1},
            "campaign_controller": {"target": "B", "policy": "target_heuristic", "per_round_budget": 1, "lifetime_budget": 15},
            "signal_controller": {"target": "C", "policy": "target_biased", "schedule": "repeated",
                                  "per_broadcast_budget": 3, "lifetime_budget": 60},
            "detector": {"target": "C", "threshold": 0.05},
            "people": people})


if __name__ == "__main__":
    out = Path(__file__).with_name("showcase100.toml")
    out.write_text(to_toml(build()), encoding="utf-8")
    print(out)
