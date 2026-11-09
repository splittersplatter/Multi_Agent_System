"""Sleeper-cell disinformation policy (communication phase plugin).

A spy keeps its cover ballot (it votes like a local) and spends its cell's
report budget on fabricated reports claiming to support the target. It only
uses what the engine lets it observe:

* ``coalition_report_budget``: remaining cell budget this round / episode;
* ``sighted_preferences``: preference sight bought by the cell (``sight`` modes);
* ``overheard_reports``: intercepted private-channel reports (``eavesdrop`` mode);
* ``public_neighbors`` and senders of received private messages as recipients.

Modes: ``blind`` (random recipients), ``sight`` (latent target supporters first: report
followers break local ties by their own ranking, so they tip with the fewest lies) and ``sight_eavesdrop`` (adds what
intercepted channel chatter reveals about each recipient's social context).
Eavesdropping also profiles behaviour: a person whose chat reports change over time is
swayed by contacts (prioritised), and one already reporting the target is skipped. Recipients that are not lied to receive nothing (the spy stays quiet rather than
revealing its non-target cover vote).
"""


def disinform(obs, params, memory, rng):
    memory = memory or {"sighted": {}, "overheard": {}, "peers": {}}
    target = params["target"]
    mode = params.get("mode", "blind")
    for person, _, ranking in obs.sighted_preferences:
        memory["sighted"][person] = list(ranking)
    memory.setdefault("said", {})
    for sender, recipient, channel, _, _, _, payload in obs.overheard_reports:
        memory["overheard"].setdefault(recipient, {})[sender] = payload[0]
        previous = memory["said"].get(sender)
        if previous is not None and previous != payload[0]:
            memory.setdefault("volatile", {})[sender] = True  # changed vote: swayed by what they hear
        memory["said"][sender] = payload[0]  # what this person currently tells their chat
    for sender, channel, _ in obs.messages:
        if channel != "public":
            memory["peers"].setdefault(channel, [])
            if sender not in memory["peers"][channel]:
                memory["peers"][channel].append(sender)
    budget = obs.coalition_report_budget
    if budget is None:
        return {"reports": [], "memory": memory}
    remaining = max(0, min(budget[2], budget[3]))
    destinations = [(p, "public") for p in obs.public_neighbors]
    for channel in obs.own_channels:
        destinations += [(p, channel) for p in memory["peers"].get(channel, []) if p != obs.person]

    def score(person):
        ranking = memory["sighted"].get(person)
        if mode == "blind":
            return rng.random()
        s = 1.0
        if ranking is not None:
            # Report-followers break local ties by their own ranking, so latent target
            # supporters who currently conform elsewhere tip first, then 2nd-choice voters.
            s = {0: 4.0, 1: 2.0}.get(ranking.index(target), 0.3)
        if mode == "sight_eavesdrop":
            if memory["said"].get(person) == target:
                return None  # chatter shows they already switched: save the lie
            if memory.get("volatile", {}).get(person):
                s += 3.0  # behavioural profile: this person follows what their contacts say
            heard = memory["overheard"].get(person, {})
            if heard:
                share = sum(choice == target for choice in heard.values()) / len(heard)
                s += 2.0 * share  # peers already lean to the target: one more voice can tip it
        return s + rng.random() * 1e-3

    ranked = []
    for person, channel in destinations:
        value = score(person)
        if value is not None:
            ranked.append((value, person, channel))
    ranked.sort(reverse=True)
    reports, used = [], set()
    for _, person, channel in ranked:
        if remaining <= 0:
            break
        if (person, channel) in used:
            continue
        used.add((person, channel))
        reports.append({"recipient": person, "channel": channel, "ballot": [target]})
        remaining -= 1
    return {"reports": reports, "memory": memory}
