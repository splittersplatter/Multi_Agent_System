"""An exact, fast re-implementation of the four voter rules under FULL information.

With full information every voter sees everyone else's last vote, so a round
depends only on the vote counts. This module reproduces the engine's rules
exactly in that case (cross-checked against the engine in test_presentation.py)
and runs thousands of towns per second, which makes two things possible:

* the 84-mix sweep of Experiment 2 on all 30 towns;
* the convergence checks: every possible small town, and many random 300-voter towns.

Rules, as the engine implements them (k = 1 ballots, ties between candidates broken
by the scenario's party order, own vote never seen by oneself):

* sincere (and the minority): favourite, always.
* copycat (sensed_plurality): the most common vote among the others; own ranking breaks ties.
* front-runner (top_k, K = 2): rank candidates by smoothed counts (n_c + 1)/(N - 1 + m),
  own ranking breaking ties, keep the top two. The engine scores each by the chance of an
  exact two-way tie among the N - 1 others. When N - 1 is odd no exact tie exists, both
  scores are 0, and the voter keeps its current vote if it is one of the top two, otherwise
  moves to its preferred one of the two. When N - 1 is even it always moves to its
  preferred one of the two.
* pivot-seeker (pivotal): with the others' counts, try every vote; switch only if some vote
  makes a strictly better candidate win (rank utilities), choosing the best such outcome and,
  among equal outcomes, its most preferred ballot.
"""
from __future__ import annotations

import itertools
import random
from collections import Counter


def _winner(counts: dict[str, int], order: list[str]) -> str:
    return max(order, key=lambda p: (counts[p], -order.index(p)))


def step(votes, prefs, types, order):
    n, m = len(votes), len(order)
    counts = Counter(votes)
    new = []
    for cur, pref, kind in zip(votes, prefs, types):
        if kind in ("sincere", "minority"):
            new.append(pref[0]); continue
        others = {p: counts[p] - (cur == p) for p in order}
        if kind == "copycat":
            new.append(max(order, key=lambda p: (others[p], -pref.index(p))))
        elif kind == "frontrunner":
            active = sorted(order, key=lambda p: (-others[p], pref.index(p)))[:2]
            preferred = min(active, key=pref.index)
            if (n - 1) % 2 == 1:            # no exact two-way tie possible: inertia inside the top two
                new.append(cur if cur in active else preferred)
            else:
                new.append(preferred)
        elif kind == "pivot":
            util = {p: (m - 1 - pref.index(p)) / (m - 1) for p in order}
            outcome = {}
            for c in order:
                trial = dict(others); trial[c] += 1
                outcome[c] = util[_winner(trial, order)]
            best = max(order, key=lambda c: (outcome[c], -pref.index(c)))
            new.append(best if outcome[best] > outcome[cur] else cur)
        else:
            raise ValueError(kind)
    return new


def simulate(prefs, types, order, rounds=40):
    """Return the list of vote profiles, round 0 (sincere) to `rounds`, stopping early at a fixed point.

    Also returns the cycle length if the profile repeats without being fixed (0 if it settles)."""
    votes = [p[0] for p in prefs]
    history = [tuple(votes)]
    seen = {history[0]: 0}
    for t in range(1, rounds + 1):
        votes = step(votes, prefs, types, order)
        key = tuple(votes)
        if key == history[-1]:
            return history, 0
        if key in seen:
            history.append(key)
            return history, t - seen[key]
        seen[key] = t
        history.append(key)
    return history, None   # neither settled nor repeated within `rounds`


def counts_of(profile, order):
    c = Counter(profile)
    return {p: c[p] for p in order}


# ---------- convergence checks ----------

RANKINGS = None


def all_small_towns(n: int, kinds=("sincere", "frontrunner", "copycat", "pivot"), parties=("A", "B", "C")):
    """Every multiset of n voters over (type, ranking) classes; yields (prefs, types)."""
    rankings = [list(r) for r in itertools.permutations(parties)]
    classes = [(k, tuple(r)) for k in kinds for r in rankings]
    for combo in itertools.combinations_with_replacement(range(len(classes)), n):
        types = [classes[i][0] for i in combo]
        prefs = [list(classes[i][1]) for i in combo]
        yield prefs, types


def check_small(n: int, order=("A", "B", "C")):
    """Exhaustive: how many n-voter towns settle, cycle, or neither within 50 rounds."""
    order = list(order)
    tally = Counter(); longest = 0; example = None
    for prefs, types in all_small_towns(n):
        hist, cyc = simulate(prefs, types, order, rounds=50)
        if cyc == 0:
            tally["settled"] += 1; longest = max(longest, len(hist) - 1)
        elif cyc:
            tally[f"cycle of length {cyc}"] += 1
            if example is None:
                example = (prefs, types, hist[-3:])
        else:
            tally["undecided"] += 1
    return tally, longest, example


def margins(counts: dict[str, int]) -> tuple[int, int]:
    """Gap between 1st and 2nd, and between 2nd and 3rd."""
    v = sorted(counts.values(), reverse=True) + [0, 0]
    return v[0] - v[1], v[1] - v[2]


def check_random(towns: int, n: int, seed: int = 0, rounds: int = 60):
    """Random n-voter towns with random rankings and random type mixes."""
    rng = random.Random(seed)
    rankings = [list(r) for r in itertools.permutations(("A", "B", "C"))]
    tally = Counter(); settle_rounds = Counter(); cycles = []
    for _ in range(towns):
        w = [rng.random() for _ in range(4)]
        kinds = rng.choices(["sincere", "frontrunner", "copycat", "pivot"], weights=w, k=n)
        rw = [rng.random() ** 2 for _ in range(6)]
        prefs = [list(r) for r in rng.choices(rankings, weights=rw, k=n)]
        order = ["A", "B", "C"]; rng.shuffle(order)
        hist, cyc = simulate(prefs, kinds, order, rounds=rounds)
        if cyc == 0:
            tally["settled"] += 1; settle_rounds[len(hist) - 1] += 1
        else:
            tally["cycle" if cyc else "undecided"] += 1
            # record the tightest margins seen along the run
            worst = min(min(margins(counts_of(h, order))) for h in hist)
            cycles.append({"cycle": cyc, "tightest_margin": worst})
    return tally, settle_rounds, cycles
