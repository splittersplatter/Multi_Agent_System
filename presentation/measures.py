"""Election measures used in the analysis. Pure functions, no engine imports."""
from __future__ import annotations

from collections import Counter


def effective_parties(counts: dict[str, int]) -> float:
    """Laakso-Taagepera effective number of parties: 1 / sum of squared vote shares."""
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("no votes")
    return 1.0 / sum((v / total) ** 2 for v in counts.values())


def first_choice_counts(preferences: list[list[str]], parties: list[str]) -> dict[str, int]:
    tally = Counter(p[0] for p in preferences)
    return {party: tally.get(party, 0) for party in parties}


def head_to_head(preferences: list[list[str]], a: str, b: str) -> tuple[int, int]:
    """Voters ranking a above b, and b above a."""
    a_wins = sum(1 for p in preferences if p.index(a) < p.index(b))
    return a_wins, len(preferences) - a_wins


def condorcet_winner(preferences: list[list[str]], parties: list[str]) -> str | None:
    """The party that strictly beats every other party head to head, if one exists."""
    for a in parties:
        if all(head_to_head(preferences, a, b)[0] > head_to_head(preferences, a, b)[1]
               for b in parties if b != a):
            return a
    return None


def plurality(preferences, parties, order=None) -> str:
    c = first_choice_counts(preferences, parties)
    order = order or parties
    return max(order, key=lambda p: (c[p], -order.index(p)))


def instant_runoff(preferences, parties) -> str:
    """Drop the party with the fewest first choices (name breaks ties) until one has a majority."""
    alive = list(parties)
    while True:
        c = Counter(next(p for p in pref if p in alive) for pref in preferences)
        top = max(alive, key=lambda p: (c[p], p))
        if c[top] * 2 > len(preferences) or len(alive) == 1:
            return top
        alive.remove(min(alive, key=lambda p: (c[p], p)))


def borda(preferences, parties) -> str:
    m = len(parties)
    score = Counter()
    for pref in preferences:
        for i, p in enumerate(pref):
            score[p] += m - 1 - i
    return max(sorted(parties), key=lambda p: score[p])


def borda_scores(preferences, parties) -> dict[str, int]:
    m = len(parties)
    score = Counter()
    for pref in preferences:
        for i, p in enumerate(pref):
            score[p] += m - 1 - i
    return {p: score[p] for p in parties}
