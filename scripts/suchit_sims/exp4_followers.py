"""Experiment 4-style viewer scenarios: an organised minority with an audience.

60 voters, parties Left / Right / Centre. Centre is almost everyone's second choice.
6 loyal Centre fans (10%) always vote Centre. In the "followers" versions each fan
also gets F random followers: directed links that show the fan's vote to that voter
every round, like a social-media audience. Everyone else uses one of the four voter
types (sincere, front-runner Top-2, copycat, pivot-seeker), hears neighbours within
0.2 and walks.

    python exp4_followers.py -> exp4_no_followers.toml, exp4_followers.toml, exp4_big_audience.toml

Over 30 random seeds Centre wins 10, 21 and 29 times with 0, 8 and 20 followers per fan.
Seed 19 (default) is a clear demo: Centre third without followers, leading from round 19
with 8, and dominant with 20.
"""

import random
from pathlib import Path

from common import to_toml

PARTIES = ["Left", "Right", "Centre"]


def build(followers: int, seed: int = 19, n: int = 60, loyal: int = 6) -> dict:
    rng = random.Random(seed)
    rankings = ([["Left", "Centre", "Right"]] * 24 + [["Right", "Centre", "Left"]] * 20 +
                [["Centre", "Right", "Left"]] * 9 + [["Centre", "Left", "Right"]] * 7)
    people = []
    centre_fans = []
    order = list(range(n))
    rng.shuffle(order)
    for idx, i in enumerate(order):
        ranking = rankings[i]
        pid = f"v{idx:02d}"
        if ranking[0] == "Centre" and len(centre_fans) < loyal:
            group = "loyal_centre"
            centre_fans.append(pid)
        else:
            u = rng.random()
            group = "sincere" if u < 0.4 else "front_runner" if u < 0.7 else "copycat" if u < 0.9 else "pivot_seeker"
        people.append({"id": pid, "group": group, "preference": list(ranking),
                       "position": [round(rng.uniform(.03, .97), 4), round(rng.uniform(.03, .97), 4)]})
    others = [p["id"] for p in people if p["id"] not in centre_fans]
    edges = []
    for fan in centre_fans:
        for follower in rng.sample(others, followers):
            edges.append([fan, follower])
    walk = {"movement": "random_walk", "max_step": 0.03, "proximity_radius": 0.2}
    sensing = {"capabilities": {"sense_public_ballots": True}}
    return {
        "parties": PARTIES, "k": 1, "seed": seed, "rounds": 40,
        "groups": {
            "loyal_centre": {"voting": "sincere", **walk},
            "sincere": {"voting": "sincere", **walk},
            "front_runner": {"voting": "top_k", **walk, "parameters": {"voting": {"top_k": 2}}, **sensing},
            "copycat": {"voting": "sensed_plurality", **walk, **sensing},
            "pivot_seeker": {"voting": "pivotal", **walk, **sensing},
        },
        "network": {"radius": 0.2, "persistent_edges": edges},
        "people": people,
    }


VERSIONS = {"exp4_no_followers": 0, "exp4_followers": 8, "exp4_big_audience": 20}

if __name__ == "__main__":
    here = Path(__file__).parent
    for name, f in VERSIONS.items():
        (here / f"{name}.toml").write_text(to_toml(build(f)), encoding="utf-8")
        print(f"{name}.toml  ({f} followers per loyal fan)")
