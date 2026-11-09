"""Exact, verification-only finite-grid model; NOT a simulator or certificate.

Enumerates reachable tiny states, not outcome trajectories. Independent review and
shared-engine correspondence remain required before production implementation.
"""

import argparse
from collections import Counter, deque
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
import hashlib
from itertools import product
import json
from math import gcd
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multi_agent_election.population import current_verification_reason, verification_scope
from multi_agent_election.provenance import manifest

MOVES = ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0))


@dataclass(frozen=True)
class Model:
    preferences: tuple
    initial_poll: tuple
    window: int = 10
    interval: int = 10
    side: int = 41
    # Inclusive squared radius in integer lattice units: d² <= 576/25.
    radius_squared: Fraction = Fraction(576, 25)

    def __post_init__(self):
        if not isinstance(self.preferences, tuple) or not isinstance(self.initial_poll, tuple):
            raise ValueError("immutable model tuples required")
        n, m = len(self.preferences), len(self.initial_poll)
        if (not isinstance(self.preferences, tuple) or not isinstance(self.initial_poll, tuple)
                or n < 2 or m < 2 or any(type(x) is not int or x < 0 for x in self.initial_poll)
                or not sum(self.initial_poll)
                or any(not isinstance(p, tuple) or len(p) != m or
                       any(type(c) is not int for c in p) or set(p) != set(range(m))
                       for p in self.preferences)
                or any(type(x) is not int or x < 1 for x in (self.window, self.interval))
                or type(self.side) is not int or self.side < 2
                or type(self.radius_squared) is not Fraction or self.radius_squared < 0):
            raise ValueError("invalid finite verification model")


@dataclass(frozen=True)
class State:
    positions: tuple
    ballots: tuple
    # Per observer: (neighbor ID, first choice, encounter age). Source age=age+1.
    caches: tuple
    poll: tuple
    phase: int
    startup: bool


def validate(model, state):
    n, m = len(model.preferences), len(model.initial_poll)
    if (not isinstance(state, State) or any(not isinstance(x, tuple) for x in
            (state.positions, state.ballots, state.caches, state.poll))
            or len(state.positions) != n or len(state.ballots) != n or len(state.caches) != n
            or len(state.poll) != m or any(type(c) is not int or not 0 <= c < m for c in state.ballots)
            or any(type(c) is not int or c < 0 for c in state.poll) or not sum(state.poll)
            or (state.poll != model.initial_poll and sum(state.poll) != n)
            or type(state.phase) is not int or not 0 <= state.phase < model.interval
            or type(state.startup) is not bool):
        raise ValueError("invalid finite verification state")
    for xy in state.positions:
        if not isinstance(xy, tuple) or len(xy) != 2 or any(type(x) is not int or not 0 <= x < model.side for x in xy):
            raise ValueError("invalid integer grid position; no silent snapping")
    for i, cache in enumerate(state.caches):
        if not isinstance(cache, tuple):
            raise ValueError("cache must be an immutable ordered tuple")
        seen, keys = set(), []
        for entry in cache:
            if (not isinstance(entry, tuple) or len(entry) != 3 or any(type(x) is not int for x in entry)):
                raise ValueError("invalid cache record")
            j, c, age = entry
            if not 0 <= j < n or j == i or j in seen or not 0 <= c < m or not 0 <= age < model.window:
                raise ValueError("invalid cache ID, choice or age")
            seen.add(j)
            keys.append((-age, j))
        if keys != sorted(keys):
            raise ValueError("cache recency/ID order violated")
    if state.startup and (state.phase != 0 or any(state.caches) or state.poll != model.initial_poll
                          or state.ballots != tuple(p[0] for p in model.preferences)):
        raise ValueError("startup must be sincere, empty-cache, initial poll and phase zero")


def initial(model, positions):
    state = State(positions, tuple(p[0] for p in model.preferences),
                  ((),) * len(model.preferences), model.initial_poll, 0, True)
    validate(model, state)
    return state


def move(xy, proposal, side):
    dx, dy = MOVES[proposal]
    x, y = xy[0] + dx, xy[1] + dy
    return (x, y) if 0 <= x < side and 0 <= y < side else xy


def choice(preference, current, population, poll, cache, weight):
    """Pure exact decision; deliberately no other agents' rankings/ballots input."""
    shares = tuple(Fraction(p, sum(poll)) for p in poll)
    if cache:
        counts = Counter(c for _, c, _ in cache)
        shares = tuple(weight * p + (1 - weight) * Fraction(counts[c], len(cache))
                       for c, p in enumerate(shares))
    winners = tuple(max(range(len(poll)), key=lambda c: ((population - 1) * shares[c] + (c == a), -c))
                    for a in range(len(poll)))
    best = next(c for c in preference if c in winners)
    return best if preference.index(best) < preference.index(winners[current]) else current


def _commit(model, state, positions):
    n = len(model.preferences)
    caches = []
    for i, (x, y) in enumerate(positions):
        contacts = tuple(j for j, (a, b) in enumerate(positions)
                         if i != j and (a - x)**2 + (b - y)**2 <= model.radius_squared)
        old = tuple((j, c, age + 1) for j, c, age in state.caches[i]
                    if age + 1 < model.window and j not in contacts)
        caches.append(old + tuple((j, state.ballots[j], 0) for j in contacts))
    poll = (tuple(state.ballots.count(c) for c in range(len(state.poll)))
            if state.phase == 0 and not state.startup else state.poll)
    weight = Fraction(model.interval - state.phase, model.interval)
    ballots = tuple(choice(pref, current, n, poll, cache, weight)
                    for pref, current, cache in zip(model.preferences, state.ballots, caches))
    return State(positions, ballots, tuple(caches), poll, (state.phase + 1) % model.interval, False)


def transition(model, state, proposals):
    validate(model, state)
    if (not isinstance(proposals, tuple) or len(proposals) != len(model.preferences)
            or any(type(p) is not int or not 0 <= p < 5 for p in proposals)):
        raise ValueError("one categorical proposal 0..4 required per voter")
    result = _commit(model, state, tuple(move(xy, p, model.side) for xy, p in zip(state.positions, proposals)))
    validate(model, result)
    return result


def kernel(model, state):
    """Aggregate identical boundary proposals exactly, before Cartesian expansion."""
    validate(model, state)
    options = [tuple(Counter(move(xy, p, model.side) for p in range(5)).items()) for xy in state.positions]
    counts = Counter()
    for outcomes in product(*options):
        positions = tuple(xy for xy, _ in outcomes)
        multiplicity = 1
        for _, count in outcomes:
            multiplicity *= count
        counts[_commit(model, state, positions)] += multiplicity
    denominator = 5 ** len(model.preferences)
    return {s: Fraction(count, denominator) for s, count in counts.items()}


def enumerate_states(model, starts, *, max_states=2_000_000, max_edges=2_000_000):
    """Reachability union for explicitly supplied starts; never silently truncate."""
    if not current_verification_reason():
        raise ValueError("enumeration requires explicit verification_scope")
    if any(type(x) is not int or x < 1 for x in (max_states, max_edges)):
        raise ValueError("positive state/edge ceilings required")
    states = list(dict.fromkeys(starts))
    if not states or len(states) > max_states:
        raise ValueError("nonempty starts must fit state ceiling")
    for state in states:
        validate(model, state)
    indices = {s: i for i, s in enumerate(states)}
    rows, edges = [], 0
    for state in states:
        row = kernel(model, state)
        if sum(row.values()) != 1:
            raise ArithmeticError("transition row does not sum to one")
        new = [s for s in row if s not in indices]
        if len(states) + len(new) > max_states or edges + len(row) > max_edges:
            return states, rows, {"status": "resource_cutoff", "discovered_states": len(states),
                                  "completed_rows": len(rows), "edges": edges,
                                  "reason": "state ceiling" if len(states) + len(new) > max_states else "edge ceiling"}
        for successor in new:
            indices[successor] = len(states)
            states.append(successor)
        rows.append({indices[s]: p for s, p in row.items()})
        edges += len(row)
    return states, rows, {"status": "complete", "discovered_states": len(states), "completed_rows": len(rows), "edges": edges}


def recurrent_classes(rows):
    """Iterative Kosaraju: no recursion-depth dependency on reachable graph size."""
    reverse = [[] for _ in rows]
    for i, row in enumerate(rows):
        if not row or any(type(j) is not int or not 0 <= j < len(rows) or p <= 0 for j, p in row.items()) or sum(row.values()) != 1:
            raise ValueError("complete stochastic rows required")
        for j in row:
            reverse[j].append(i)
    seen, order = set(), []
    for root in range(len(rows)):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(rows[root]))]
        while stack:
            v, iterator = stack[-1]
            target = next(iterator, None)
            if target is None:
                order.append(v)
                stack.pop()
            elif target not in seen:
                seen.add(target)
                stack.append((target, iter(rows[target])))
    seen, classes = set(), []
    for root in reversed(order):
        if root in seen:
            continue
        component, stack = set(), [root]
        seen.add(root)
        while stack:
            v = stack.pop()
            component.add(v)
            for target in reverse[v]:
                if target not in seen:
                    seen.add(target)
                    stack.append(target)
        if all(j in component for i in component for j in rows[i]):
            classes.append(tuple(sorted(component)))
    return sorted(classes)


def period(rows, component):
    if not component:
        raise ValueError("nonempty recurrent class required")
    allowed = set(component)
    distance, queue = {component[0]: 0}, deque([component[0]])
    while queue:
        i = queue.popleft()
        for j in rows[i]:
            if j not in allowed:
                raise ValueError("period requires a closed irreducible class")
            if j not in distance:
                distance[j] = distance[i] + 1
                queue.append(j)
    if len(distance) != len(component):
        raise ValueError("class not reachable from its root")
    return reduce(gcd, (abs(distance[i] + 1 - distance[j]) for i in component for j in rows[i]), 0)


def stationary(rows, component):
    """Independent rational linear solve, with residual checks; no numerical tolerance."""
    n = len(component)
    index = {v: i for i, v in enumerate(component)}
    if not n or any(j not in index for i in component for j in rows[i]):
        raise ValueError("closed nonempty class required")
    matrix = [[Fraction(rows[src].get(dst, 0)) - (src == dst) for src in component] + [Fraction(0)]
              for dst in component[:-1]]
    matrix.append([Fraction(1)] * n + [Fraction(1)])
    for col in range(n):
        pivot = next((i for i in range(col, n) if matrix[i][col]), None)
        if pivot is None:
            raise ValueError("stationary class is reducible or singular")
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        matrix[col] = [x / scale for x in matrix[col]]
        for i in range(n):
            if i != col and matrix[i][col]:
                factor = matrix[i][col]
                matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[col])]
    pi = tuple(row[-1] for row in matrix)
    if sum(pi) != 1 or any(x <= 0 for x in pi) or any(
            sum(pi[index[src]] * rows[src].get(dst, 0) for src in component) != pi[index[dst]] for dst in component):
        raise ArithmeticError("stationary residual failed")
    return pi


def audit(model, *, max_states, max_edges, stationary_ceiling):
    coordinates = tuple(product(range(model.side), repeat=2))
    starts = tuple(initial(model, positions) for positions in product(coordinates, repeat=len(model.preferences)))
    states, rows, summary = enumerate_states(model, starts, max_states=max_states, max_edges=max_edges)
    summary.update({"model": {"preferences": model.preferences, "initial_poll": model.initial_poll,
                              "K": model.window, "L": model.interval, "side": model.side,
                              "radius_squared": str(model.radius_squared)},
                    "initial_position_states": len(starts), "claim": "verification_only_not_simulator_certification"})
    if summary["status"] != "complete":
        summary["classes"] = "not computed from incomplete graph"
        return summary
    digest = hashlib.sha256()
    for state, row in zip(states, rows):
        digest.update((repr(state) + repr(sorted((j, str(p)) for j, p in row.items()))).encode())
    summary["kernel_sha256"] = digest.hexdigest()
    classes = recurrent_classes(rows)
    summary["classes"] = []
    for component in classes:
        result = {"size": len(component), "period": period(rows, component)}
        if len(component) > stationary_ceiling:
            result["stationary_status"] = "resource_cutoff"
        else:
            pi = stationary(rows, component)
            phase = tuple(sum(p for i, p in zip(component, pi) if states[i].phase == q) for q in range(model.interval))
            if phase != (Fraction(1, model.interval),) * model.interval:
                raise ArithmeticError("stationary phase mass is not uniform")
            winners = [max(range(len(model.initial_poll)), key=lambda c: (states[i].ballots.count(c), -c)) for i in component]
            frequencies = tuple(sum(p for w, p in zip(winners, pi) if w == c) for c in range(len(model.initial_poll)))
            conditional = tuple(tuple(str(model.interval * sum(p for i, w, p in zip(component, winners, pi)
                                                               if states[i].phase == q and w == c))
                                      for c in range(len(model.initial_poll))) for q in range(model.interval))
            result.update(stationary_status="exact_residual_checked", phase_mass=tuple(map(str, phase)),
                          winner_frequency=tuple(map(str, frequencies)), phase_conditioned_winners=conditional,
                          stationary_sha256=hashlib.sha256(repr(tuple(zip(component, map(str, pi)))).encode()).hexdigest())
        summary["classes"].append(result)
    summary["transient_states"] = len(states) - sum(len(c) for c in classes)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="exclusive new JSON file; stdout if omitted")
    parser.add_argument("--max-states", type=int, default=2_000_000)
    parser.add_argument("--max-edges", type=int, default=2_000_000)
    parser.add_argument("--stationary-ceiling", type=int, default=256)
    parser.add_argument("--population", type=int, choices=(2, 3), nargs="+", default=[2, 3], help="formal fixtures only")
    args = parser.parse_args(argv)
    if any(x < 1 for x in (args.max_states, args.max_edges, args.stationary_ceiling)):
        parser.error("resource ceilings must be positive")
    if args.output is not None and (args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir()):
        parser.error("output must be new with existing parent")
    results = []
    with verification_scope("formal tiny-grid reachability and exact Markov kernels; not outcome simulations"):
        for n, k, interval in product(dict.fromkeys(args.population), (1, 2), (1, 2)):
            preferences = ((0, 1),) * (n - 1) + ((1, 0),)
            model = Model(preferences, (n - 1, 1), k, interval, 2, Fraction(1))
            results.append(audit(model, max_states=args.max_states, max_edges=args.max_edges,
                                 stationary_ceiling=args.stationary_ceiling))
    record = {"record_type": "eclipse.stochastic-stability-verification", "version": 1,
              "manifest": manifest(), "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "command": ["scripts/verify_stochastic_stability.py", *(argv if argv is not None else sys.argv[1:])],
              "scope": "2x2 grid, inclusive squared radius 1, two candidates, one fixed mixed ranking profile per N; all initial positions",
              "not_verified": ["arbitrary rankings/polls/starting caches", "production grid engine (not implemented)",
                               "default K10/L10 enumeration", "independent mathematical review", "finite-horizon outcome study"],
              "ceilings": {"states": args.max_states, "edges": args.max_edges, "stationary_solve": args.stationary_ceiling},
              "cases": results}
    encoded = json.dumps(record, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
        print(json.dumps({"output": str(args.output), "cases": len(results),
                          "complete_cases": sum(r["status"] == "complete" for r in results),
                          "independent_review": "pending", "production_implementation": "gated"}))
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
