"""Passive detector whose entire input is public aggregate ballot counts."""

import math

from .model import DetectorConfig, DetectorState, ElectionError


def update_detector(config, parties, counts, round_number, previous=None, previous_counts=None):
    if (not isinstance(config, DetectorConfig) or isinstance(config.threshold, bool)
            or not isinstance(config.threshold, (int, float)) or not math.isfinite(config.threshold)
            or not 0 <= config.threshold <= 1
            or type(round_number) is not int or round_number < 0 or not parties or len(set(parties)) != len(parties)
            or config.target not in parties or not isinstance(counts, dict) or set(counts) != set(parties)
            or any(type(value) is not int or value < 0 for value in counts.values()) or sum(counts.values()) == 0):
        raise ElectionError("invalid aggregate detector input")
    population = sum(counts.values())
    winner = min(parties, key=lambda p: (-counts[p], parties.index(p)))
    if previous is None:
        if round_number != 0 or previous_counts is not None:
            raise ElectionError("detector initial state must be round zero")
        return DetectorState(None, False, None, int(winner == config.target), None)
    if (not isinstance(previous, DetectorState) or round_number == 0 or not isinstance(previous_counts, dict)
            or set(previous_counts) != set(parties) or any(type(v) is not int or v < 0 for v in previous_counts.values())
            or sum(previous_counts.values()) != population):
        raise ElectionError("invalid previous aggregate detector input")
    change = (counts[config.target] - previous_counts[config.target]) / population
    alert = change > config.threshold
    first_alert = previous.first_alert_round if previous.first_alert_round is not None else (round_number if alert else None)
    streak = previous.target_win_streak + 1 if winner == config.target else 0
    first_triple = previous.first_triple_win_round
    if first_triple is None and streak >= 3:
        first_triple = round_number
    return DetectorState(change, alert, first_alert, streak, first_triple)
