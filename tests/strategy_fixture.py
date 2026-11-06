"""Test-only plugin exercising independent JSON memory."""

def vote(observation, parameters, memory, rng):
    memory = {"calls": 0} if memory is None else memory
    memory["calls"] += 1
    choice = parameters.get("choice", observation.own_preference[0])
    ballot = [choice] + [x for x in observation.own_preference if x != choice]
    return {"ballot": ballot[:observation.k], "memory": memory}


def invalid(observation, parameters, memory, rng):
    return {"ballot": ["bad"], "memory": float("nan")}


def invalid_ballot(observation, parameters, memory, rng):
    return {"ballot": ["bad"], "memory": None}


def illegal_mutation(observation, parameters, memory, rng):
    observation.own_preference = ("C", "B", "A")
    return {"ballot": ["C"], "memory": None}


def observe(observation, parameters, memory, rng):
    return {"ballot": list(observation.own_preference[:observation.k]),
            "memory": {"messages": observation.messages, "own_preference": observation.own_preference}}


def move(observation, parameters, memory, rng):
    x, y = observation.own_position
    return {"position": [x + 0.05, y], "memory": (memory or 0) + 1}


def graph(observation, parameters, memory, rng):
    target = parameters["target"]
    return {"add_edges": [] if target in observation.public_neighbors else [target], "memory": (memory or 0) + 1}


def communicate(observation, parameters, memory, rng):
    reports = [{"recipient": neighbor, "channel": "public", "ballot": observation.own_previous_ballot}
               for neighbor in observation.public_neighbors]
    return {"reports": reports, "memory": (memory or 0) + 1}


def teleport(observation, parameters, memory, rng):
    return {"position": [1, 1], "memory": None}


def bad_graph(observation, parameters, memory, rng):
    return {"add_edges": ["unknown"], "memory": None}


def bad_communication(observation, parameters, memory, rng):
    return {"reports": [{"recipient": "unknown", "channel": "public", "ballot": observation.own_previous_ballot}], "memory": None}


def capture_scope(observation, parameters, memory, rng):
    return {"ballot": list(observation.own_preference[:observation.k]),
            "memory": {"neighbors": observation.public_neighbors, "channels": observation.own_channels,
                       "messages": observation.messages}}


def join_channel(observation, parameters, memory, rng):
    return {"add_channels": [parameters["channel"]], "memory": None}


def capture_movement(observation, parameters, memory, rng):
    return {"position": list(observation.own_position), "memory": {"messages": observation.messages}}


def capture_sensors(observation, parameters, memory, rng):
    return {"ballot": list(observation.own_preference[:observation.k]),
            "memory": {"reports": observation.messages, "sensed": observation.sensed_ballots}}


def capture_sensor_movement(observation, parameters, memory, rng):
    return {"position": list(observation.own_position), "memory": {"sensed": observation.sensed_ballots}}


def forbidden_campaign(observation, parameters, memory, rng):
    return {"add_campaign_edges": [parameters["target"]], "memory": None}


def rng_burn(observation, parameters, memory, rng):
    for _ in range(100):
        rng.random()
    return {"ballot": list(observation.own_preference[:observation.k]), "memory": None}


def rng_echo(observation, parameters, memory, rng):
    return {"ballot": list(observation.own_preference[:observation.k]), "memory": {"draw": rng.random()}}
