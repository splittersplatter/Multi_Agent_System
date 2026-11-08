"""Recent direct encounters, not reports or knowledge, estimate plurality shares."""

from collections import OrderedDict
from dataclasses import dataclass
import math

from .model import ElectionError


@dataclass(frozen=True, slots=True)
class MajorityConfig:
    poll_counts: tuple[int, ...]
    memory_rounds: int = 10
    poll_weight: float = 0.5
    poll_round: int = 0

    def as_dict(self):
        return {"poll_counts": list(self.poll_counts), "memory_rounds": self.memory_rounds,
                "poll_weight": self.poll_weight, "poll_round": self.poll_round}


def parse_config(raw, parties):
    if not isinstance(raw, dict) or set(raw) - {"enabled", "poll_counts", "memory_rounds", "poll_weight", "poll_round"}:
        raise ElectionError("majority_estimation: unsupported configuration")
    if type(raw.get("enabled", True)) is not bool:
        raise ElectionError("majority_estimation enabled must be boolean")
    window = raw.get("memory_rounds", 10)
    weight = raw.get("poll_weight", 0.5)
    poll_round = raw.get("poll_round", 0)
    if type(window) is not int or window < 1:
        raise ElectionError("memory_rounds must be an integer >= 1")
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= 1 or not math.isfinite(weight):
        raise ElectionError("poll_weight must be finite and within [0,1]")
    if type(poll_round) is not int or poll_round != 0:
        raise ElectionError("initial poll_round must be 0")
    counts = raw.get("poll_counts")
    if counts is not None and (not isinstance(counts, list) or len(counts) != len(parties)
                              or any(type(n) is not int or n < 0 for n in counts) or sum(counts) <= 0):
        raise ElectionError("poll_counts must contain nonnegative integers in party order with positive total")
    if not raw.get("enabled", True):
        return None
    if counts is None:
        raise ElectionError("majority_estimation requires explicit initial poll_counts; no census fallback")
    return MajorityConfig(tuple(counts), window, float(weight), poll_round)


@dataclass(frozen=True, slots=True)
class MajorityState:
    round: int
    # Recency order; each person appears exactly once. No full ranked ballots.
    entries: tuple[tuple[str, str, int, int], ...]
    counts: tuple[int, ...]

    @classmethod
    def initial(cls, parties):
        return cls(0, (), (0,) * len(parties))

    def as_dict(self, parties, config):
        shares = estimate(self, config)
        leaders = leader_indices(self, config)
        return {"round": self.round, "ballot_source_round": max(0, self.round - 1),
                "poll_round": config.poll_round, "poll_counts": list(config.poll_counts),
                "poll_age": max(0, self.round - 1) - config.poll_round,
                "memory_rounds": config.memory_rounds, "poll_weight": config.poll_weight,
                "entries": [{"neighbor_id": p, "first_choice": c, "last_seen_round": seen,
                             "ballot_source_round": source, "encounter_age": self.round - seen,
                             "ballot_age": max(0, self.round - 1) - source}
                            for p, c, seen, source in self.entries],
                "counts": dict(zip(parties, self.counts)), "sample_size": len(self.entries),
                "shares": dict(zip(parties, shares)),
                "leaders": [parties[i] for i in leaders],
                "basis": "poll_only" if not self.entries else "poll_and_recent_encounters"}


def estimate(state, config):
    scores, denominator = _scores(state, config)
    return tuple(score / denominator for score in scores)


def _scores(state, config):
    # Exact comparisons for ties; floats are only the exported presentation.
    total = sum(config.poll_counts)
    size = len(state.entries)
    if not size:
        return config.poll_counts, total
    numerator, denominator = float(config.poll_weight).as_integer_ratio()
    return (tuple(numerator * p * size + (denominator - numerator) * n * total
                  for p, n in zip(config.poll_counts, state.counts)), denominator * total * size)


def leader_indices(state, config):
    scores, _ = _scores(state, config)
    highest = max(scores)
    return tuple(i for i, score in enumerate(scores) if score == highest)


def advance(state, *, observer, parties, config, round_number, encounters):
    """Pure atomic update. Encounters: (neighbor, first_choice, source_round).

    Map operations are expected O(1); immutable snapshot copying is O(U).
    All direct samples in a round refer to its prior completed ballot snapshot.
    """
    if type(round_number) is not int or round_number <= state.round:
        raise ElectionError("majority observation rounds must increase")
    index = {party: i for i, party in enumerate(parties)}
    cache = OrderedDict((p, (c, seen, source)) for p, c, seen, source in state.entries)
    counts = list(state.counts)
    # Validate/deduplicate before expiry; malformed updates cannot alter state.
    observations = {}
    for record in encounters:
        if not isinstance(record, (tuple, list)) or len(record) != 3:
            raise ElectionError("invalid majority encounter")
        person, choice, source = record
        if not isinstance(person, str) or not person.strip() or not isinstance(choice, str) or choice not in index or type(source) is not int or not 0 <= source < round_number:
            raise ElectionError("invalid majority encounter")
        if person == observer:
            continue
        if (person, source) in observations and observations[person, source] != choice:
            raise ElectionError("conflicting majority ballots for the same person/source round")
        previous = cache.get(person)
        if previous is not None and source == previous[2] and choice != previous[0]:
            raise ElectionError("conflicting majority ballots for the same person/source round")
        observations[person, source] = choice
    lower = round_number - config.memory_rounds + 1
    while cache and next(iter(cache.values()))[1] < lower:
        _, (choice, _, _) = cache.popitem(last=False)
        counts[index[choice]] -= 1
    # Stable actor ordering also defines same-round recency ties.
    for (person, source), choice in sorted(observations.items()):
        # Delayed/re-delivered observations are not new physical encounters.
        if source != round_number - 1:
            continue
        previous = cache.pop(person, None)
        if previous is not None:
            counts[index[previous[0]]] -= 1
        cache[person] = (choice, round_number, source)
        counts[index[choice]] += 1
    return MajorityState(round_number, tuple((p, *record) for p, record in cache.items()), tuple(counts))


def advance_population(previous, parties, config, round_number, proximity, ballots):
    """Observe only incoming proximity arcs; never inspect preferences/reports."""
    contacts = {person: [] for person, _ in previous}
    for sender, receiver in proximity:
        if sender != receiver:
            contacts[receiver].append((sender, ballots[sender][0], round_number - 1))
    return tuple((person, advance(state, observer=person, parties=parties, config=config,
                                  round_number=round_number, encounters=contacts[person]))
                 for person, state in previous)
