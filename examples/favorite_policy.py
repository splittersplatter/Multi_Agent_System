"""Example trusted plugin: choose a configured party and count own invocations."""


def vote(observation, parameters, memory, rng):
    preferred = parameters["party"]
    ranking = [preferred] + [party for party in observation.own_preference if party != preferred]
    count = 1 if memory is None else memory["calls"] + 1
    return {"ballot": ranking[:observation.k], "memory": {"calls": count}}
