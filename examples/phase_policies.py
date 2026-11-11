"""Example trusted group policies: move, connect and send truthful reports."""


def move(observation, parameters, memory, rng):
    x, y = observation.own_position
    step = parameters.get("step", 0.03)
    return {"position": [min(1.0, x + step), y], "memory": (memory or 0) + 1}


def connect(observation, parameters, memory, rng):
    target = parameters["target"]
    additions = [] if target in observation.public_neighbors else [target]
    return {"add_edges": additions, "memory": (memory or 0) + 1}


def communicate(observation, parameters, memory, rng):
    reports = [{"recipient": person, "channel": "public", "ballot": observation.own_previous_ballot}
               for person in observation.public_neighbors]
    return {"reports": reports, "memory": (memory or 0) + 1}
