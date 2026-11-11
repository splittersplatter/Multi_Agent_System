"""Checks for the presentation code. From the repository root:

    PYTHONPATH=src:presentation python3 -m pytest presentation/test_presentation.py -q
"""
from __future__ import annotations

import itertools
import random
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from convergence import certificate, clear, top_two  # noqa: E402
from fullinfo import counts_of, simulate, step  # noqa: E402
from measures import borda, condorcet_winner, effective_parties, instant_runoff, plurality  # noqa: E402
from town import FULL, Town, all_mixes, build_town, minority_members, preferences, tie_order, types  # noqa: E402


def engine_votes(raw):
    from multi_agent_election.engine import Simulation
    from multi_agent_election.model import make_scenario
    sim = Simulation(make_scenario(raw))
    sim.run()
    ids = sorted(p["id"] for p in raw["people"])
    return [tuple(dict(f.ballots)[i][0] for i in ids) for f in sim.frames]


def fast_votes(town, seed):
    prefs, kinds, order = preferences(town, seed), types(town, seed), tie_order(seed)
    v = [p[0] for p in prefs]
    out = [tuple(v)]
    for _ in range(town.rounds):
        v = step(v, prefs, kinds, order)
        out.append(tuple(v))
    return out


@pytest.mark.parametrize("town,seed", [(Town(rounds=3), 0), (Town(voters=301, rounds=3), 1),
                                       (Town(mix=all_mixes()[-1], rounds=3), 2), (Town(mix=all_mixes()[40], rounds=3), 3)])
def test_fast_simulator_matches_engine(town, seed):
    assert fast_votes(town, seed) == engine_votes(build_town(town, seed))


def test_the_spoiler_town():
    for seed in range(30):
        prefs = preferences(Town(), seed)
        parties = ["Centre", "Left", "Right"]
        first = Counter(p[0] for p in prefs)
        assert max(first, key=first.get) == "Left"
        assert condorcet_winner(prefs, parties) == "Centre"
        assert plurality(prefs, parties) == "Left"
        assert borda(prefs, parties) == "Centre"
        assert instant_runoff(prefs, parties) in {"Right", "Centre"}


def test_mixes_and_types():
    mixes = all_mixes()
    assert len(mixes) == 84 and len(set(mixes)) == 84
    for mix in mixes:
        shares = dict(mix)
        assert abs(sum(shares.values()) - 1) < 1e-9 and min(shares.values()) >= 0.1 - 1e-9
    counts = Counter(types(Town(), 0))
    assert counts == {"sincere": 120, "frontrunner": 90, "copycat": 60, "pivot": 30}


def test_minority_and_followers():
    town = Town(radius=0.2, minority=30, minority_party="Centre", followers=10)
    raw = build_town(town, 4)
    members = minority_members(town, 4)
    prefs = preferences(town, 4)
    assert len(members) == 30 and all(prefs[m][0] == "Centre" for m in members)
    edges = raw["network"]["persistent_edges"]
    assert len(edges) == 300 and len({tuple(e) for e in edges}) == 300
    member_ids = {f"{m:04d}" for m in members}
    assert all(s in member_ids and r not in member_ids for s, r in edges)
    assert sum(p["group"] == "minority" for p in raw["people"]) == 30


def test_followers_hear_the_minority():
    """A copycat whose only contacts are three members copies their vote (persistent edges are heard)."""
    town = Town(radius=0.001, walking=False, rounds=1, minority=30, minority_party="Centre", followers=0)
    raw = build_town(town, 0)
    members = [f"{m:04d}" for m in minority_members(town, 0)]
    listener = next(p for p in raw["people"] if p["group"] == "copycat" and p["preference"][0] != "Centre")
    raw["network"]["persistent_edges"] = [[m, listener["id"]] for m in members[:3]]
    ids = sorted(p["id"] for p in raw["people"])
    final = engine_votes(raw)[-1]
    assert final[ids.index(listener["id"])] == "Centre"


def test_freeze_lemma_on_random_profiles():
    """Two consecutive clear rounds with the same top two => the next round repeats (both parities)."""
    rng = random.Random(7)
    rankings = [list(r) for r in itertools.permutations("ABC")]
    checked = 0
    for _ in range(3000):
        n = rng.choice([40, 41, 120, 121])
        kinds = rng.choices(["sincere", "frontrunner", "copycat", "pivot"], k=n)
        prefs = [list(r) for r in rng.choices(rankings, weights=[rng.random() for _ in rankings], k=n)]
        order = list("ABC"); rng.shuffle(order)
        v0 = [rng.choice(p[:2]) for p in prefs]          # an arbitrary current profile
        v1 = step(v0, prefs, kinds, order)
        c0, c1 = counts_of(v0, order), counts_of(v1, order)
        if clear(c0) and clear(c1) and top_two(c0, order) == top_two(c1, order):
            checked += 1
            assert step(v1, prefs, kinds, order) == v1
    assert checked > 300


def test_default_towns_are_certified():
    for seed in range(30):
        t = Town()
        assert certificate(preferences(t, seed), types(t, seed), tie_order(seed))["certified"]


def test_cycles_exist_at_a_knife_edge():
    order = ["A", "B"]
    two = simulate([["A", "B"], ["B", "A"]], ["copycat", "copycat"], order, rounds=10)
    assert two[1] == 2
    prefs = [["A", "B"]] * 150 + [["B", "A"]] * 150
    big = simulate(prefs, ["copycat"] * 300, order, rounds=10)
    assert big[1] == 2


def test_measures():
    prefs = [["A", "B", "C"]] * 4 + [["B", "C", "A"]] * 3 + [["C", "B", "A"]] * 2
    assert plurality(prefs, ["A", "B", "C"]) == "A"
    assert instant_runoff(prefs, ["A", "B", "C"]) == "B"
    assert condorcet_winner(prefs, ["A", "B", "C"]) == "B"
    assert borda(prefs, ["A", "B", "C"]) == "B"
    assert abs(effective_parties({"A": 50, "B": 50}) - 2) < 1e-12


def test_full_radius_covers_the_map():
    assert FULL ** 2 * 1.0 >= 1.99 and FULL <= 2 ** 0.5
