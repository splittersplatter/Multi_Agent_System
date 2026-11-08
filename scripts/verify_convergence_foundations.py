"""Exhaustive tiny-model proof checks; NOT a simulator or engine certification.

Standard library, deterministic, no files/network/RNG. Checks every enabled
singleton transition, not just one favourable scheduler path. See
docs/convergence-foundations.md for domains and mathematical guarantees.
"""
from collections import Counter
from functools import lru_cache
from itertools import combinations, permutations, product
import json


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def winner(ballots, m):
    counts = Counter(ballots)
    return max(range(m), key=lambda c: (counts[c], -c))


def replace(ballots, i, choice):
    return ballots[:i] + (choice,) + ballots[i + 1:]


def direct_moves(ballots, preferences):
    m = len(preferences[0])
    current = winner(ballots, m)
    for i, preference in enumerate(preferences):
        reachable = {winner(replace(ballots, i, c), m) for c in range(m)}
        best = next(c for c in preference if c in reachable)
        if preference.index(best) < preference.index(current):
            successor = replace(ballots, i, best)
            require(winner(successor, m) == best, "Direct reply must elect voted candidate")
            yield successor


def depth_checker(moves):
    active = set()

    @lru_cache(maxsize=None)
    def depth(state):
        require(state not in active, f"Nonterminal cycle: {state}")
        active.add(state)
        result = max((1 + depth(other) for other in moves(state)), default=0)
        active.remove(state)
        return result

    return depth


@lru_cache(maxsize=None)
def l1_worlds(center, radius):
    # Source L1 allows varying total voter counts; NOT current fixed-total engine.
    return tuple(tuple(c + d for c, d in zip(center, delta))
                 for delta in product(range(-radius, radius + 1), repeat=len(center))
                 if sum(abs(d) for d in delta) <= radius
                 and all(c + d >= 0 for c, d in zip(center, delta)))


def score_winner(scores, vote):
    return max(range(len(scores)), key=lambda c: (scores[c] + (c == vote), -c))


def dominance_moves(ballots, preferences, radius):
    m = len(preferences[0])
    for i, preference in enumerate(preferences):
        center = tuple(sum(b == c for j, b in enumerate(ballots) if i != j)
                       for c in range(m))
        worlds = l1_worlds(center, radius)
        rank = {c: r for r, c in enumerate(preference)}
        outcomes = {c: tuple(rank[score_winner(s, c)] for s in worlds) for c in range(m)}
        current = outcomes[ballots[i]]
        dominators = [c for c in preference
                      if all(a <= b for a, b in zip(outcomes[c], current))
                      and any(a < b for a, b in zip(outcomes[c], current))]
        if dominators:
            yield replace(ballots, i, dominators[0])


def conformity_choice(ballots, preference, neighbors):
    counts = Counter(ballots[j] for j in neighbors)
    maximum = max(counts.values(), default=0)
    return next(c for c in preference if counts[c] == maximum)


def potential(ballots, preferences, edges):
    m = len(preferences[0])
    agreement = sum(ballots[i] == ballots[j] for i, j in edges)
    preference_score = sum(m - 1 - p.index(b) for p, b in zip(preferences, ballots))
    return m * agreement + preference_score


def verify():
    summary = {"scope": "Abstract proof oracles, not current engine certification"}
    cases = states = longest = 0
    for n, m in ((1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3), (4, 3)):
        for prefs in product(tuple(permutations(range(m))), repeat=n):
            depth = depth_checker(lambda b: direct_moves(b, prefs))
            for state in product(range(m), repeat=n):
                steps = depth(state)
                require(steps <= m * m * n * n, "S4 arbitrary-start bound exceeded")
                longest = max(longest, steps)
                states += 1
            truthful = tuple(p[0] for p in prefs)
            require(depth(truthful) <= m * n, "S4 truthful-start bound exceeded")
            cases += 1
    summary["direct_best_response"] = dict(profiles=cases, states=states, maximum_path=longest)

    cases = longest = 0
    for n, m in ((1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3), (4, 3)):
        for prefs in product(tuple(permutations(range(m))), repeat=n):
            for radius in (0, 1, 2):
                depth = depth_checker(lambda b: dominance_moves(b, prefs, radius))
                steps = depth(tuple(p[0] for p in prefs))
                require(steps <= n * (m - 1), "S6 truthful-start bound exceeded")
                longest = max(longest, steps)
                cases += 1
    summary["homogeneous_local_dominance"] = dict(profile_radius_cases=cases, maximum_path=longest)

    cases = transitions = 0
    for n, m in ((1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3)):
        possible = tuple(combinations(range(n), 2))
        for mask in range(1 << len(possible)):
            edges = tuple(e for k, e in enumerate(possible) if mask & (1 << k))
            neighbors = tuple(tuple(j for j in range(n) if (min(i, j), max(i, j)) in edges)
                              for i in range(n))
            for prefs in product(tuple(permutations(range(m))), repeat=n):
                cases += 1
                for state in product(range(m), repeat=n):
                    old = potential(state, prefs, edges)
                    for i in range(n):
                        choice = conformity_choice(state, prefs[i], neighbors[i])
                        if choice != state[i]:
                            require(potential(replace(state, i, choice), prefs, edges) > old,
                                    "Conformity potential failed to increase")
                            transitions += 1
    summary["sequential_undirected_conformity"] = dict(graph_preference_cases=cases,
                                                        changing_transitions=transitions)

    # Negative controls must violate the attempted unrestricted certification.
    prefs = ((0, 1), (1, 0))
    state = (0, 1)
    synchronous = tuple(conformity_choice(state, prefs[i], (1 - i,)) for i in range(2))
    require(synchronous == (1, 0), "Synchronous counterexample missing")
    require(tuple(conformity_choice(synchronous, prefs[i], (1 - i,)) for i in range(2)) == state,
            "Synchronous two-cycle missing")
    require(potential(state, prefs, ((0, 1),)) > potential(synchronous, prefs, ((0, 1),)),
            "Potential must reject simultaneous-rule generalization")
    directed_cycle = ((0, 1, 0), (1, 1, 0), (1, 0, 0), (1, 0, 1),
                      (0, 0, 1), (0, 1, 1), (0, 1, 0))
    sources = (1, 2, 0)
    for before, after in zip(directed_cycle, directed_cycle[1:]):
        changed = [i for i in range(3) if before[i] != after[i]]
        require(len(changed) == 1 and after[changed[0]] == before[sources[changed[0]]],
                "Directed singleton-copy cycle is not legal")
    successor = dict(zip(directed_cycle, directed_cycle[1:]))
    try:
        depth_checker(lambda b: (successor[b],))(directed_cycle[0])
    except AssertionError as exc:
        require("Nonterminal cycle" in str(exc), "Unexpected cycle-check failure")
    else:
        raise AssertionError("Depth checker failed to reject a known cycle")
    # S4 Example 4a: better replies that need not vote for the new winner can cycle.
    better_cycle = ((0, 1, 2), (0, 1, 1), (0, 2, 1), (0, 2, 2), (0, 1, 2))
    better_prefs = ((0, 1, 2), (0, 1, 2), (2, 1, 0))
    for before, after in zip(better_cycle, better_cycle[1:]):
        changed = [i for i in range(3) if before[i] != after[i]]
        require(len(changed) == 1, "Expected unilateral better reply")
        p = better_prefs[changed[0]]
        require(p.index(winner(after, 3)) < p.index(winner(before, 3)),
                "Source better-reply cycle must strictly improve each mover's outcome")
    require(any(after not in tuple(direct_moves(before, better_prefs))
                for before, after in zip(better_cycle, better_cycle[1:])),
            "Better-reply counterexample must violate the direct-reply restriction")
    require((0, 0) in l1_worlds((1, 0), 1), "Must not silently constrain source L1 totals")
    summary["negative_controls"] = ["simultaneous two-cycle", "directed singleton six-cycle",
                                     "nondirect better-reply cycle",
                                     "variable-total source L1 preserved"]
    return summary


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
