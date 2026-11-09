"""Research-only memory_pivotal specification and convergence refutation.

This research checker is not the simulator policy, an experiment runner, or a
convergence certificate. The separate simulator policy is available for exploration.
Uses the real cache/motion helpers and a separate exact decision kernel. A complete
proximity invariant makes the ballot projection autonomous even as positions and
absolute timestamps keep changing. Output distinguishes proof from finite checks.
"""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
from itertools import permutations, product
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multi_agent_election.majority import MajorityConfig, MajorityState, _scores, advance_population, parse_config
from multi_agent_election.model import ElectionError
from multi_agent_election.network import proximity_edges, random_walk
from multi_agent_election.provenance import manifest


@dataclass(frozen=True)
class Decision:
    current: str
    choice: str
    baseline_winner: str
    predicted_winners: tuple[tuple[str, str], ...]
    strict_improvement: bool
    other_scores: tuple[tuple[int, int], ...]


def decision(parties, preference, current, population, state, config):
    """Declared observations only; exact rational estimated-other-score response."""
    if (not isinstance(parties, tuple) or not parties or any(not isinstance(c, str) or not c for c in parties)
            or len(set(parties)) != len(parties) or not isinstance(preference, tuple)
            or any(not isinstance(c, str) for c in preference)
            or len(preference) != len(parties) or set(preference) != set(parties)
            or not isinstance(current, str) or current not in parties
            or type(population) is not int or population < 1
            or not isinstance(state, MajorityState) or not isinstance(config, MajorityConfig)):
        raise ElectionError("invalid memory proof-model decision input")
    parse_config(config.as_dict(), parties)
    if (type(state.round) is not int or state.round < 0 or not isinstance(state.entries, tuple)
            or len(state.counts) != len(parties) or any(type(n) is not int or n < 0 for n in state.counts)
            or sum(state.counts) != len(state.entries) or len(state.entries) > population - 1):
        raise ElectionError("invalid memory proof-model cache counts")
    seen_ids = set()
    actual_counts = Counter()
    for entry in state.entries:
        if not isinstance(entry, tuple) or len(entry) != 4:
            raise ElectionError("invalid memory proof-model cache entry")
        person, choice, seen, source = entry
        if (not isinstance(person, str) or not person.strip() or person in seen_ids
                or not isinstance(choice, str) or choice not in parties
                or type(seen) is not int or type(source) is not int
                or not 1 <= seen <= state.round or source != seen - 1
                or state.round - seen >= config.memory_rounds):
            raise ElectionError("invalid memory proof-model cache entry")
        seen_ids.add(person)
        actual_counts[choice] += 1
    if tuple(actual_counts[c] for c in parties) != state.counts:
        raise ElectionError("memory proof-model cache histogram disagreement")
    support, denominator = _scores(state, config)
    other = tuple((population - 1) * s for s in support)
    winners = tuple(parties[max(range(len(parties)), key=lambda c:
                               (other[c] + denominator * (c == action), -c))]
                    for action in range(len(parties)))
    baseline = winners[parties.index(current)]
    best = next(c for c in preference if c in winners)
    improve = preference.index(best) < preference.index(baseline)
    choice = best if improve else current
    if improve and winners[parties.index(choice)] != choice:
        raise AssertionError("direct vote must elect its predicted winner")
    return Decision(current, choice, baseline, tuple(zip(parties, winners)), improve,
                    tuple((v.numerator, v.denominator) for v in (Fraction(s, denominator) for s in other)))


def normalized_cache(states, current_round):
    """Only valid for the stated projection: source/encounter ages, not raw clocks."""
    return tuple((p, tuple((q, c, current_round - seen, current_round - source)
                          for q, c, seen, source in state.entries), state.counts)
                 for p, state in states)


def witness(rounds=40, seed=101, window=10):
    if type(rounds) is not int or rounds < 4:
        raise ElectionError("witness requires at least four validation rounds")
    if type(seed) is not int or seed < 0 or type(window) is not int or window < 1:
        raise ElectionError("invalid witness seed/window")
    parties = ("A", "B", "C")
    people = ("v1", "v2", "v3", "v4")
    preferences = (("A", "B", "C"), ("A", "B", "C"), ("B", "C", "A"), ("C", "B", "A"))
    poll = (2, 1, 1)
    config = MajorityConfig(poll, memory_rounds=window)
    ballots = tuple(p[0] for p in preferences)
    assert tuple(Counter(ballots)[c] for c in parties) == poll  # Accurate initial census.
    integer_preferences = tuple(tuple(parties.index(c) for c in p) for p in preferences)
    assert complete_transition((0, 0, 1, 2), integer_preferences, poll, Fraction(1, 2)) == (0, 0, 2, 1)
    assert complete_transition((0, 0, 2, 1), integer_preferences, poll, Fraction(1, 2)) == (0, 0, 1, 2)
    positions = dict(zip(people, ((0.2, 0.2), (0.2, 0.8), (0.8, 0.2), (0.8, 0.8))))
    radius, max_step = math.sqrt(2), 0.025
    complete = tuple((s, r) for s in people for r in people if s != r)
    states = tuple((p, MajorityState.initial(parties)) for p in people)
    traces, projections = [], []
    moved = False
    for tick in range(1, rounds + 1):
        new_positions = {p: random_walk(positions[p], max_step, seed, p, tick) for p in people}
        assert all(0 <= v <= 1 for xy in new_positions.values() for v in xy)
        assert all(math.dist(positions[p], new_positions[p]) <= max_step + 1e-12 for p in people)
        moved |= new_positions != positions
        positions = new_positions
        edges = proximity_edges(positions, radius)
        assert edges == complete
        states = advance_population(states, parties, config, tick, edges,
                                    {p: (b,) for p, b in zip(people, ballots)})
        choices = tuple(decision(parties, preference, current, 4, state, config)
                        for preference, current, (_, state) in zip(preferences, ballots, states))
        successor = tuple(d.choice for d in choices)
        expected = ("A", "A", "C", "B") if tick % 2 else ("A", "A", "B", "C")
        assert successor == expected
        assert [d.strict_improvement for d in choices] == [False, False, True, True]
        assert [d.baseline_winner for d in choices[2:]] == ["A", "A"]
        assert all(len(state.entries) == 3 and all(seen == tick and source == tick - 1
                   for _, _, seen, source in state.entries) for _, state in states)
        ballots = successor
        projections.append((ballots, normalized_cache(states, tick)))
        if len(projections) >= 3:
            assert projections[-1] == projections[-3]
        if tick <= 4:
            traces.append({"round": tick, "positions": positions.copy(), "ballots": dict(zip(people, ballots)),
                           "normalized_cache": normalized_cache(states, tick),
                           "decisions": {p: asdict(d) for p, d in zip(people, choices)}})
    assert moved
    return {"status": "verified_inductive_counterexample", "population": 4, "parties": parties,
            "preferences": dict(zip(people, preferences)), "initial_ballots": [p[0] for p in preferences],
            "truthful_initial_poll": poll, "configuration": config.as_dict(), "seed": seed,
            "motion": {"policy": "implemented_keyed_random_walk", "max_step": max_step, "radius": radius},
            "ballot_period": 2, "normalized_projection_period": 2, "full_physical_state_repetition_claimed": False,
            "validated_rounds": rounds, "genuine_movement_observed": moved, "first_rounds": traces,
            "proof": ["Unit-square positions and radius sqrt(2) imply every incoming non-self edge for all future times.",
                      "Every cache is fully refreshed from the preceding completed ballots, for any positive memory window.",
                      "Thus estimated-other scores depend only on preceding ballots and the fixed truthful poll.",
                      "Exact transition maps AABC to AACB and AACB to AABC; v3/v4 strictly improve their predicted winner.",
                      "Induction gives two switches every round forever, independently of seed, positions or future motion."],
            "scope": "Refutes universal and almost-sure ballot absorption for this proposed rule at default w=.5/K10; existing simulator policies unchanged.",
            "winner_stable": "A", "stage_c": "exploration_allowed_convergence_uncertified"}


def complete_transition(ballots, preferences, poll, weight):
    """Independent integer complete-observation reduction, with no cache helper."""
    n, m, total = len(ballots), len(poll), sum(poll)
    counts = Counter(ballots)
    numerator, denominator = Fraction(weight).as_integer_ratio()
    result = []
    for current, preference in zip(ballots, preferences):
        other = tuple((n - 1) * numerator * poll[c] + (denominator - numerator) * total * (counts[c] - (current == c))
                      for c in range(m))
        winners = tuple(max(range(m), key=lambda c: (other[c] + denominator * total * (action == c), -c))
                        for action in range(m))
        before = winners[current]
        best = next(c for c in preference if c in winners)
        result.append(best if preference.index(best) < preference.index(before) else current)
    return tuple(result)


def enumerate_complete():
    """Exhaust a declared finite family, not all graphs/motions/polls/initial states."""
    rows = []
    for n in (2, 3, 4, 5):
        for m in (2, 3):
            for weight in (0, Fraction(1, 2), 1):
                counts = Counter(profiles=0, fixed_points=0, cycles=0, maximum_period=0)
                for preferences in product(tuple(permutations(range(m))), repeat=n):
                    initial = tuple(p[0] for p in preferences)
                    poll = tuple(initial.count(c) for c in range(m))
                    seen, history, current = {}, [], initial
                    while current not in seen:
                        seen[current] = len(history)
                        history.append(current)
                        current = complete_transition(current, preferences, poll, weight)
                        assert len(history) <= m**n
                    period = len(history) - seen[current]
                    counts["profiles"] += 1
                    counts["fixed_points" if period == 1 else "cycles"] += 1
                    counts["maximum_period"] = max(counts["maximum_period"], period)
                rows.append({"n": n, "m": m, "weight": str(weight), "windows_covered_by_refresh_invariant": [1, 2, 10], **counts})
    return {"family": "complete incoming observation, sincere start, accurate initial census, all strict preference profiles",
            "not_exhausted": "arbitrary polls/cache states/geometric graphs/motion trajectories; no general positive theorem",
            "directly_enumerated_orbits": sum(r["profiles"] for r in rows),
            "window_parameter_cases_covered": sum(3 * r["profiles"] for r in rows), "rows": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="exclusive new JSON evidence file; stdout if omitted")
    parser.add_argument("--witness-only", action="store_true", help="skip finite complete-observation enumeration")
    parser.add_argument("--witness-rounds", type=int, default=40)
    args = parser.parse_args(argv)
    if args.witness_rounds < 4:
        parser.error("witness-rounds must be >= 4")
    if args.output is not None and (args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir()):
        parser.error("output must be new with an existing parent")
    result = {"record_type": "eclipse.memory-voting-proof-audit", "record_version": 1,
              "manifest": manifest(), "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "counterexample": witness(args.witness_rounds)}
    if not args.witness_only:
        result["enumeration"] = enumerate_complete()
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
        print(json.dumps({"output": str(args.output), "gate": "refuted", "stage_c": "exploration_allowed_convergence_uncertified",
                          "enumerated_orbits": result.get("enumeration", {}).get("directly_enumerated_orbits", 0)}))
    else:
        print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
