"""Test-only policy used to exercise in-flight browser controls."""

import time


def vote(observation, parameters, memory, rng):
    time.sleep(3)
    return {"ballot": list(observation.own_preference[:observation.k]), "memory": None}
