"""Party campaigners that strategise around echo chambers.

Two phase plugins share one strategy parameter:

* ``move`` (movement phase): walk toward the strategy's post at ``max_step``.
* ``link`` (graph phase): add/remove the campaigner's own outgoing persistent
  edges. An edge campaigner -> voter makes the campaigner's ballot visible to
  that voter's trusted ballot sensors, i.e. one more "neighbour" in their
  conformity count. Budgets are enforced here: ``new_per_round`` new edges per
  round and at most ``max_active`` live edges.

Campaigners only use what the engine shows them in the graph phase: the
electorate roster, their own outgoing neighbours and the previous-round ballots
of everyone inside their (wide) sensing radius. Campaigners work in pairs: the two
partners rank equally attractive voters identically, so each target gets two edges. Chamber centres are public
census knowledge passed as parameters.

Strategies
----------
``fortify``    stay home; link to home voters who defected, then to wavering own voters.
``infiltrate`` move into the largest rival chamber; link to its voters who back others.
``bridge``     sit on the border with a rival chamber; link to voters seen switching
               ballots (volatile swing voters), then to rival voters near the border.
``broadcast``  stay home; link to random roster members (untargeted spray).
``passive``    no movement, no edges (campaigner only votes).
"""

import math


def _post(params):
    strategy = params["strategy"]
    home = params["home"]
    rival = params["rival"]
    if strategy == "infiltrate":
        return rival
    if strategy == "bridge":
        return [home[0] + 0.55 * (rival[0] - home[0]), home[1] + 0.55 * (rival[1] - home[1])]
    return home


def move(obs, params, memory, rng):
    if params["strategy"] == "passive":
        return {"position": list(obs.own_position), "memory": None}
    goal = _post(params)
    x, y = obs.own_position
    dx, dy = goal[0] - x, goal[1] - y
    distance = math.hypot(dx, dy)
    step = params["max_step"] * 0.999
    if distance <= step:
        return {"position": [goal[0], goal[1]], "memory": None}
    return {"position": [x + dx / distance * step, y + dy / distance * step], "memory": None}


def link(obs, params, memory, rng):
    memory = memory or {"edges": [], "history": {}}
    strategy = params["strategy"]
    party = params["party"]
    if strategy == "passive":
        return {"memory": memory}
    seen = {}
    for sender, source, _, ballot in obs.sensed_ballots:
        if source == "public":
            seen[sender] = ballot[0]
    for person, choice in seen.items():
        past = memory["history"].setdefault(person, [])
        past.append(choice)
        del past[:-4]
    campaigners = set(params.get("campaigners", []))
    edges = list(memory["edges"])
    cap, per_round = params["max_active"], params["new_per_round"]

    team = int(obs.person[-1]) // 2  # campaigners work in pairs: partners focus on the same voters

    def spread(person):
        return sum(ord(ch) * (i + 7) for i, ch in enumerate(person + str(team))) % 997

    def volatile(person):
        past = memory["history"].get(person, [])
        return len(set(past)) > 1

    if strategy == "broadcast":
        pool = [p for p in obs.electorate if p != obs.person and p not in campaigners and p not in edges]
        rng.shuffle(pool)
        candidates = pool
    else:
        pool = [p for p in seen if p not in campaigners and p not in edges and p != obs.person]
        if strategy == "fortify":
            candidates = sorted(pool, key=lambda p: (seen[p] == party, not volatile(p), spread(p)))
        elif strategy == "infiltrate":
            candidates = sorted((p for p in pool if seen[p] != party), key=lambda p: (not volatile(p), spread(p)))
        else:  # bridge
            candidates = sorted((p for p in pool if seen[p] != party or volatile(p)), key=lambda p: (not volatile(p), seen[p] == party, spread(p)))

    remove = []
    # Retire edges whose target now votes for us and is stable (pressure no longer needed),
    # except for fortify, which keeps its base linked.
    if strategy in ("infiltrate", "bridge"):
        for p in edges:
            if seen.get(p) == party and not volatile(p) and len(edges) - len(remove) >= cap - per_round:
                remove.append(p)
    free = cap - (len(edges) - len(remove))
    if free <= 0 and strategy != "fortify":
        oldest = [p for p in edges if p not in remove][: per_round]
        remove += oldest
        free = cap - (len(edges) - len(remove))
    add = [p for p in candidates if p not in remove][: max(0, min(per_round, free))]
    memory["edges"] = [p for p in edges if p not in remove] + add
    return {"memory": memory, "add_edges": add, "remove_edges": remove}
