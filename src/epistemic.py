"""Finite, factive knowledge profiles for explicit plurality ballot worlds.

Worlds carry private preferences and submitted ballots separately. Observation
labels define an equivalence partition per voter; the model never guesses a
partition from researcher-only truth. Public announcements must be true at the
pointed world. No probabilistic belief or dishonest announcement is implied.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping
import json
import itertools
import math

from .model import ElectionError


def _json(value: Any, label: str) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ElectionError(f"{label} must be finite JSON data") from exc


@dataclass(frozen=True, slots=True)
class World:
    id: str
    preferences: tuple[tuple[str, tuple[str, ...]], ...]
    ballots: tuple[tuple[str, tuple[str, ...]], ...]
    observations: tuple[tuple[str, str], ...]
    public_signal: str
    public_history: str

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "preferences": {a: list(p) for a, p in self.preferences},
                "ballots": {a: list(b) for a, b in self.ballots},
                "observations": dict(self.observations), "public_signal": json.loads(self.public_signal),
                "public_history": json.loads(self.public_history)}


@dataclass(frozen=True, slots=True)
class KnowledgeModel:
    parties: tuple[str, ...]
    k: int
    agents: tuple[str, ...]
    worlds: tuple[World, ...]
    actual: str
    max_worlds: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], *, max_worlds: int = 10000) -> "KnowledgeModel":
        if type(max_worlds) is not int or not 1 <= max_worlds <= 1000000:
            raise ElectionError("max_worlds must be an integer in [1, 1000000]")
        if not isinstance(raw, Mapping) or set(raw) != {"parties", "k", "agents", "worlds", "actual"}:
            raise ElectionError("knowledge model requires parties, k, agents, worlds and actual")
        parties, agents = raw["parties"], raw["agents"]
        for name, values in (("parties", parties), ("agents", agents)):
            if (not isinstance(values, list) or not values or
                    any(not isinstance(x, str) or not x.strip() for x in values) or len(set(values)) != len(values)):
                raise ElectionError(f"{name} must be a nonempty list of unique nonempty strings")
        k = raw["k"]
        if type(k) is not int or not 1 <= k <= len(parties):
            raise ElectionError("knowledge model k must be between 1 and party count")
        worlds = raw["worlds"]
        if not isinstance(worlds, list) or not worlds or len(worlds) > max_worlds:
            raise ElectionError("worlds must be a nonempty list within max_worlds")
        normalized = []
        for item in worlds:
            if (not isinstance(item, dict) or not {"id", "preferences", "ballots", "observations"} <= set(item)
                    or set(item) - {"id", "preferences", "ballots", "observations", "public_signal", "public_history"}):
                raise ElectionError("world requires id, preferences, ballots and observations")
            wid = item["id"]
            if not isinstance(wid, str) or not wid.strip():
                raise ElectionError("world id must be a nonempty string")
            prefs, ballots, observations = item["preferences"], item["ballots"], item["observations"]
            if any(not isinstance(v, dict) or set(v) != set(agents) for v in (prefs, ballots, observations)):
                raise ElectionError("each world must specify every agent exactly once")
            for actor in agents:
                pref, ballot, label = prefs[actor], ballots[actor], observations[actor]
                if (not isinstance(pref, list) or len(pref) != len(parties) or
                        any(not isinstance(p, str) for p in pref) or set(pref) != set(parties)):
                    raise ElectionError(f"world {wid!r}: preference must rank every party")
                if (not isinstance(ballot, list) or len(ballot) != k or any(not isinstance(p, str) for p in ballot)
                        or len(set(ballot)) != k or not set(ballot) <= set(parties)):
                    raise ElectionError(f"world {wid!r}: ballot must contain k distinct known parties")
                if not isinstance(label, str) or not label.strip():
                    raise ElectionError(f"world {wid!r}: observation labels must be nonempty strings")
            history = item.get("public_history", [])
            if not isinstance(history, list):
                raise ElectionError("public_history must be a list")
            normalized.append(World(wid, tuple((a, tuple(prefs[a])) for a in agents),
                                    tuple((a, tuple(ballots[a])) for a in agents),
                                    tuple((a, observations[a]) for a in agents),
                                    _json(item.get("public_signal"), "public signal"),
                                    _json(history, "public history")))
        ids = [world.id for world in normalized]
        if len(set(ids)) != len(ids) or raw["actual"] not in ids:
            raise ElectionError("world IDs must be unique and include the actual world")
        # An agent knows their own preference/ballot and public observations.
        for actor in agents:
            seen = {}
            for world in normalized:
                label = dict(world.observations)[actor]
                visible = (dict(world.preferences)[actor], dict(world.ballots)[actor],
                           world.public_signal, world.public_history)
                if label in seen and seen[label] != visible:
                    raise ElectionError(f"agent {actor!r}: indistinguishable worlds disagree on known own/public data")
                seen[label] = visible
        return cls(tuple(parties), k, tuple(agents), tuple(normalized), raw["actual"], max_worlds)

    def as_dict(self) -> dict[str, Any]:
        return {"parties": list(self.parties), "k": self.k, "agents": list(self.agents),
                "worlds": [world.as_dict() for world in self.worlds], "actual": self.actual}

    def world(self, world_id: str | None = None) -> World:
        target = self.actual if world_id is None else world_id
        for world in self.worlds:
            if world.id == target:
                return world
        raise ElectionError(f"unknown world {target!r}")

    def information_set(self, agent: str, world_id: str | None = None) -> tuple[World, ...]:
        if agent not in self.agents:
            raise ElectionError(f"unknown agent {agent!r}")
        label = dict(self.world(world_id).observations)[agent]
        return tuple(world for world in self.worlds if dict(world.observations)[agent] == label)

    def knows(self, agent: str, proposition: Callable[[World], bool], world_id: str | None = None) -> bool:
        return all(proposition(world) for world in self.information_set(agent, world_id))

    def possible(self, agent: str, proposition: Callable[[World], bool], world_id: str | None = None) -> bool:
        return any(proposition(world) for world in self.information_set(agent, world_id))

    def announce(self, proposition: Callable[[World], bool]) -> "KnowledgeModel":
        """Truthful public announcement restricts all agents' relations uniformly."""
        kept = tuple(world for world in self.worlds if proposition(world))
        if not any(world.id == self.actual for world in kept):
            raise ElectionError("public announcement is false at the actual world")
        return KnowledgeModel(self.parties, self.k, self.agents, kept, self.actual, self.max_worlds)

    def winner(self, world: World, agent: str | None = None, choice: str | None = None) -> str:
        if agent is not None and (agent not in self.agents or choice not in self.parties):
            raise ElectionError("replacement requires a known agent and party")
        if agent is None and choice is not None:
            raise ElectionError("replacement requires an agent")
        ballots = dict(world.ballots)
        counts = {party: 0 for party in self.parties}
        for actor, ballot in ballots.items():
            counts[choice if actor == agent else ballot[0]] += 1
        return min(self.parties, key=lambda party: (-counts[party], self.parties.index(party)))

    def analyze(self, agent: str, world_id: str | None = None) -> dict[str, Any]:
        """Exact decision properties over an agent's current information set.

        Baselines are submitted ballots in each world. A replacement changes
        only the actor's first choice under plurality; private rankings remain fixed.
        """
        possible = self.information_set(agent, world_id)
        preference = dict(possible[0].preferences)[agent]
        current = dict(possible[0].ballots)[agent][0]
        ranks = {party: index for index, party in enumerate(preference)}
        baseline = [ranks[self.winner(world)] for world in possible]
        results = {party: [ranks[self.winner(world, agent, party)] for world in possible]
                   for party in self.parties}
        strict = {party: [a < b for a, b in zip(outcomes, baseline)]
                  for party, outcomes in results.items()}
        dere = [party for party in preference if all(strict[party])]
        dominant = [party for party in preference if all(a <= b for a, b in zip(results[party], baseline))
                    and any(strict[party])]
        pessimistic = [party for party in preference if max(results[party]) < max(baseline)]
        return {"agent": agent, "world_count": len(possible), "world_ids": [w.id for w in possible],
                "current_first_choice": current, "de_dicto": all(any(strict[p][i] for p in self.parties)
                                                                   for i in range(len(possible))),
                "de_re": dere, "dominant": dominant, "pessimistic": pessimistic,
                "baseline_winners": [preference[r] for r in baseline],
                "action_winners": {party: [preference[r] for r in results[party]] for party in self.parties}}

    def information_classes(self) -> dict[str, dict[str, tuple[World, ...]]]:
        """All nonempty equivalence classes, including classes outside the actual world."""
        grouped = {actor: {} for actor in self.agents}
        for world in self.worlds:
            for actor, label in world.observations:
                grouped[actor].setdefault(label, []).append(world)
        return {actor: {label: tuple(grouped[actor][label]) for label in sorted(grouped[actor])}
                for actor in self.agents}

    def _conditional_profile(self, profile: Mapping[str, Any], classes) -> dict[str, dict[str, str]]:
        if not isinstance(profile, Mapping) or set(profile) != set(self.agents):
            raise ElectionError("conditional profile must specify every agent exactly once")
        result = {}
        for actor in self.agents:
            choices = profile[actor]
            if not isinstance(choices, Mapping) or set(choices) != set(classes[actor]):
                raise ElectionError(f"agent {actor!r}: conditional profile must cover every information label")
            if any(not isinstance(choice, str) or choice not in self.parties for choice in choices.values()):
                raise ElectionError("conditional actions must be known first-choice parties")
            result[actor] = {label: choices[label] for label in classes[actor]}
        return result

    @staticmethod
    def _work_limit(max_evaluations: int) -> int:
        if type(max_evaluations) is not int or not 1 <= max_evaluations <= 10000000:
            raise ElectionError("max_evaluations must be an integer in [1, 10000000]")
        return max_evaluations

    def conditional_equilibrium(self, profile: Mapping[str, Any], *, max_evaluations: int = 1000000) -> dict[str, Any]:
        """Check all virtual voters under pessimistic first-choice deviations.

        Profile maps each agent and each observation label to a plurality first
        choice. Other voters' choices may differ across worlds according to their
        own labels. The labels are pre-decision observations, not post-vote facts.
        """
        limit = self._work_limit(max_evaluations)
        work = len(self.agents) * len(self.worlds) * (len(self.parties) + 1)
        if work > limit:
            raise ElectionError(f"conditional equilibrium requires {work} outcome evaluations, exceeding max_evaluations={limit}")
        classes = self.information_classes()
        choices = self._conditional_profile(profile, classes)

        def outcome(world, replacement_agent=None, replacement_party=None):
            labels = dict(world.observations)
            counts = {party: 0 for party in self.parties}
            for actor in self.agents:
                selected = replacement_party if actor == replacement_agent else choices[actor][labels[actor]]
                counts[selected] += 1
            return min(self.parties, key=lambda party: (-counts[party], self.parties.index(party)))

        evaluations = []
        for actor in self.agents:
            for label, worlds in classes[actor].items():
                preference = dict(worlds[0].preferences)[actor]
                ranks = {party: i for i, party in enumerate(preference)}
                baseline = [outcome(world) for world in worlds]
                worst = max(baseline, key=ranks.__getitem__)
                action_worst = {party: max((outcome(world, actor, party) for world in worlds),
                                           key=ranks.__getitem__)
                                for party in self.parties}
                deviations = [party for party in preference if ranks[action_worst[party]] < ranks[worst]]
                evaluations.append({"agent": actor, "observation": label, "world_ids": [w.id for w in worlds],
                                    "action": choices[actor][label], "baseline_winners": baseline,
                                    "baseline_worst": worst, "action_worst": action_worst,
                                    "pessimistic_deviations": deviations})
        return {"equilibrium": all(not row["pessimistic_deviations"] for row in evaluations),
                "profile": choices, "information_sets": evaluations, "outcome_evaluations": work,
                "criterion": "pessimistic", "action_space": "plurality first choice"}

    def solve_conditional_equilibria(self, *, max_profiles: int = 10000,
                                    max_evaluations: int = 1000000) -> dict[str, Any]:
        """Exhaustively enumerate all equilibria or fail before returning partial results."""
        if type(max_profiles) is not int or not 1 <= max_profiles <= 1000000:
            raise ElectionError("max_profiles must be an integer in [1, 1000000]")
        limit = self._work_limit(max_evaluations)
        per_profile = len(self.agents) * len(self.worlds) * (len(self.parties) + 1)
        if per_profile > limit:
            raise ElectionError("conditional equilibrium search exceeds max_evaluations")
        classes = self.information_classes()
        slots = [(actor, label) for actor in self.agents for label in classes[actor]]
        total = 1
        for _ in slots:
            if total > max_profiles // len(self.parties):
                raise ElectionError("conditional profile count exceeds max_profiles")
            total *= len(self.parties)
        if total * per_profile > limit:
            raise ElectionError("conditional equilibrium search exceeds max_evaluations")
        equilibria = []
        for actions in itertools.product(self.parties, repeat=len(slots)):
            profile = {actor: {} for actor in self.agents}
            for (actor, label), action in zip(slots, actions):
                profile[actor][label] = action
            if self.conditional_equilibrium(profile, max_evaluations=per_profile)["equilibrium"]:
                equilibria.append(profile)
        return {"criterion": "pessimistic", "action_space": "plurality first choice",
                "profiles_checked": total, "outcome_evaluations": total * per_profile,
                "equilibria": equilibria}

    def announce_with_profile(self, proposition: Callable[[World], bool], profile: Mapping[str, Any]):
        """Apply a truthful announcement and restrict the conditional profile."""
        choices = self._conditional_profile(profile, self.information_classes())
        updated = self.announce(proposition)
        classes = updated.information_classes()
        restricted = {actor: {label: choices[actor][label] for label in classes[actor]}
                      for actor in self.agents}
        return updated, restricted


SIGNAL_EPISTEMIC_POLICIES = ("epistemic_signal_dere", "epistemic_signal_dominant", "epistemic_signal_pessimistic")
EPISTEMIC_POLICIES = ("epistemic_dere", "epistemic_dominant", "epistemic_pessimistic") + SIGNAL_EPISTEMIC_POLICIES


def validate_epistemic_parameters(parameters, policy=None):
    allowed = {"max_worlds", "remember_observations", "max_history"}
    if policy in SIGNAL_EPISTEMIC_POLICIES:
        allowed.add("signal_distortion_bound")
    if not isinstance(parameters, dict) or set(parameters) - allowed:
        raise ElectionError("unsupported epistemic parameters")
    if policy in SIGNAL_EPISTEMIC_POLICIES:
        bound = parameters.get("signal_distortion_bound")
        if type(bound) is not int or not 0 <= bound <= 1000000:
            raise ElectionError("signal_distortion_bound must be an integer in [0, 1000000]")
    maximum = parameters.get("max_worlds", 10000)
    if type(maximum) is not int or not 1 <= maximum <= 1000000:
        raise ElectionError("epistemic max_worlds must be an integer in [1, 1000000]")
    remember = parameters.get("remember_observations", False)
    if type(remember) is not bool:
        raise ElectionError("remember_observations must be boolean")
    if "max_history" in parameters and not remember:
        raise ElectionError("max_history requires remember_observations=true")
    history_limit = parameters.get("max_history", 1000)
    if type(history_limit) is not int or not 1 <= history_limit <= 100000:
        raise ElectionError("max_history must be an integer in [1, 100000]")
    return maximum


def validate_signal_epistemic_group(group, controller, population, party_count):
    """Reject unsound declared bounds using only fixed public configuration."""
    if group.voting not in SIGNAL_EPISTEMIC_POLICIES:
        return
    if controller is None or not group.capabilities.observe_public_signal or not group.capabilities.observe_electorate:
        raise ElectionError("signal epistemic voting requires a signal controller, public-signal and electorate permissions")
    params = json.loads(group.parameters).get("voting", {})
    validate_epistemic_parameters(params, group.voting)
    required = (0 if controller.policy == "truthful" or party_count == 1 else
                min(controller.per_broadcast_budget, controller.lifetime_budget, population))
    if params["signal_distortion_bound"] < required:
        raise ElectionError(f"signal_distortion_bound must be at least the configured controller bound {required}")


def _signal_profiles(obs, observed, unknown, maximum, bound):
    """Return compatible other-voter score vectors and exact logical multiplicity."""
    signal = obs.public_signal
    if (not isinstance(signal, (tuple, list)) or len(signal) != 3
            or type(signal[0]) is not int or type(signal[1]) is not int
            or signal[0] < 0 or signal[1] != signal[0] + 1 or signal[1] > obs.round
            or not isinstance(signal[2], (tuple, list)) or len(signal[2]) != len(obs.parties)
            or any(type(v) is not int or v < 0 for v in signal[2])
            or sum(signal[2]) != len(obs.electorate)):
        raise ElectionError("signal epistemic voting requires a valid public-signal report and provenance")
    fresh = signal[0] == obs.round - 1
    report = signal[2]
    known = [sum(ballot[0] == p for ballot in observed.values()) for p in obs.parties]
    own = obs.parties.index(obs.own_previous_ballot[0])
    full_known = [n + (i == own) for i, n in enumerate(known)]
    factor = 1
    for _ in range(len(obs.electorate) - 1):
        factor *= math.factorial(len(obs.parties))
        if factor > maximum:
            raise ElectionError("epistemic information set exceeds max_worlds")
    for _ in unknown:
        factor *= math.perm(len(obs.parties) - 1, obs.k - 1)
        if factor > maximum:
            raise ElectionError("epistemic information set exceeds max_worlds")
    profiles = []
    represented = 0
    nodes = 0
    def visit(index, remaining, distance, allocation, multiplicity):
        nonlocal represented, nodes
        nodes += 1
        if nodes > 1000000:
            raise ElectionError("signal epistemic score search exceeds 1000000 nodes")
        if index == len(obs.parties):
            if remaining:
                return
            represented += multiplicity
            if represented > maximum // factor:
                raise ElectionError("epistemic information set exceeds max_worlds")
            profiles.append(tuple(known[j] + allocation[j] for j in range(len(known))))
            return
        choices = (remaining,) if index == len(obs.parties) - 1 else range(remaining + 1)
        for amount in choices:
            new_distance = distance + abs(full_known[index] + amount - report[index]) if fresh else 0
            residual = remaining - amount
            if fresh:
                minimum_rest = abs(sum(full_known[index + 1:]) + residual - sum(report[index + 1:]))
                if new_distance + minimum_rest > 2 * bound:
                    continue
            allocation.append(amount)
            visit(index + 1, residual, new_distance, allocation, multiplicity * math.comb(remaining, amount))
            allocation.pop()
    visit(0, len(unknown), 0, [], 1)
    if not profiles:
        raise ElectionError("empty epistemic information set: signal bound conflicts with trusted observations")
    return profiles, represented, represented * factor, fresh


def response_from_observation(policy, obs, parameters, previous_memory=None):
    """Exact own-information decision, factored by outcome-equivalent worlds.

    Unknown other preferences range over all strict rankings, and unknown ballots
    range over all k-permutations. Trusted completed-ballot sensors fix entire
    observed ballots. For first-choice plurality only the first choices affect
    decisions, so equal-outcome worlds are represented by one score profile.
    The logical world-count limit applies *before* this projection.
    """
    if policy not in EPISTEMIC_POLICIES:
        raise ElectionError("unknown epistemic voting policy")
    maximum = validate_epistemic_parameters(parameters, policy)
    parties, roster = obs.parties, obs.electorate
    if (not parties or any(not isinstance(c, str) or not c for c in parties)
            or len(set(parties)) != len(parties) or type(obs.k) is not int or not 1 <= obs.k <= len(parties)
            or len(obs.own_preference) != len(parties) or any(not isinstance(c, str) for c in obs.own_preference)
            or set(obs.own_preference) != set(parties)
            or len(obs.own_previous_ballot) != obs.k or any(not isinstance(c, str) for c in obs.own_previous_ballot)
            or len(set(obs.own_previous_ballot)) != obs.k
            or not set(obs.own_previous_ballot) <= set(parties)):
        raise ElectionError("invalid own preference, ballot or party information")
    if not roster or obs.person not in roster:
        raise ElectionError("epistemic voting requires observe_electorate capability")
    if len(set(roster)) != len(roster) or any(not isinstance(a, str) or not a for a in roster):
        raise ElectionError("epistemic electorate must contain unique known IDs")
    if len(parties) > 32:
        raise ElectionError("epistemic voting supports at most 32 parties")
    history = None
    if parameters.get("remember_observations", False):
        if previous_memory is not None and (not isinstance(previous_memory, dict) or previous_memory.get("policy") != policy
                                            or not isinstance(previous_memory.get("observation_history"), list)):
            raise ElectionError("invalid epistemic observation history")
        history = list(previous_memory["observation_history"]) if previous_memory is not None else []
        if history and (not isinstance(history[-1], dict) or type(history[-1].get("round")) is not int
                        or history[-1]["round"] != obs.round - 1):
            raise ElectionError("epistemic observation history is not consecutive")
        if len(history) >= parameters.get("max_history", 1000):
            raise ElectionError("epistemic observation history exceeds max_history")
    observed = {}
    for sender, source, timestamp, ballot in obs.sensed_ballots:
        if (sender not in roster or sender == obs.person or not isinstance(source, str) or not source
                or type(timestamp) is not int or timestamp != obs.round - 1 or
                len(ballot) != obs.k or any(not isinstance(c, str) for c in ballot)
                or len(set(ballot)) != obs.k or not set(ballot) <= set(parties)):
            raise ElectionError("invalid trusted ballot observation")
        if sender in observed and observed[sender] != ballot:
            raise ElectionError("conflicting trusted ballot observations")
        observed[sender] = ballot
    others = tuple(actor for actor in roster if actor != obs.person)
    unknown = tuple(actor for actor in others if actor not in observed)
    signal_aware = policy in SIGNAL_EPISTEMIC_POLICIES
    if signal_aware:
        profiles, projected_count, world_count, fresh = _signal_profiles(
            obs, observed, unknown, maximum, parameters["signal_distortion_bound"])
    else:
        ranking_count = math.factorial(len(parties))
        ballot_count = math.perm(len(parties), obs.k)
        world_count = 1
        for actor in others:
            for factor in (ranking_count, ballot_count if actor in unknown else 1):
                if world_count > maximum // factor:
                    raise ElectionError("epistemic information set exceeds max_worlds")
                world_count *= factor
        known = [ballot[0] for ballot in observed.values()]
        profiles = (tuple(sum(choice == party for choice in (*known, *unknown_choices)) for party in parties)
                    for unknown_choices in itertools.product(parties, repeat=len(unknown)))
        projected_count = len(parties) ** len(unknown)
    current = obs.own_previous_ballot[0]
    rank = {party: index for index, party in enumerate(obs.own_preference)}
    preference = obs.own_preference
    baseline = []
    actions = {party: [] for party in parties}
    for profile in profiles:
        counts = dict(zip(parties, profile))
        for choice in parties:
            counts[choice] += 1
            winner = min(parties, key=lambda c: (-counts[c], parties.index(c)))
            actions[choice].append(rank[winner])
            counts[choice] -= 1
        baseline.append(actions[current][-1])
    strict = {party: [a < b for a, b in zip(actions[party], baseline)] for party in parties}
    dere = [party for party in preference if all(strict[party])]
    dominant = [party for party in preference if all(a <= b for a, b in zip(actions[party], baseline))
                and any(strict[party])]
    pessimistic = [party for party in preference if max(actions[party]) < max(baseline)]
    base_policy = policy.replace("epistemic_signal_", "epistemic_")
    candidates = {"epistemic_dere": dere, "epistemic_dominant": dominant,
                  "epistemic_pessimistic": pessimistic}[base_policy]
    if base_policy == "epistemic_pessimistic" and candidates:
        best_worst = min(max(actions[party]) for party in candidates)
        candidates = [party for party in candidates if max(actions[party]) == best_worst]
    choice = candidates[0] if candidates else current
    ballot = ((choice,) + tuple(party for party in preference if party != choice)[:obs.k - 1]
              if candidates else obs.own_previous_ballot)
    trace = {"policy": policy, "information": "own preference, own ballot, roster and trusted completed ballots",
             "world_count": world_count, "projected_ballot_profiles": projected_count,
             "observed_ballots": {actor: list(observed[actor]) for actor in sorted(observed)},
             "unobserved_voters": list(unknown), "unobserved_preferences": list(others),
             "de_dicto": all(any(strict[party][i] for party in parties) for i in range(len(baseline))),
             "de_re": dere, "dominant": dominant, "pessimistic": pessimistic,
             "previous": current, "choice": choice, "switched": choice != current,
             "semantics": "factive ballot-profile projection; no higher-order claim"}
    if signal_aware:
        trace["information"] += ", bounded public signal"
        trace["signal"] = {"source_round": obs.public_signal[0], "broadcast_round": obs.public_signal[1],
                           "report": list(obs.public_signal[2]), "distortion_bound": parameters["signal_distortion_bound"],
                           "use": "current_count_constraint" if fresh else "stale_unconstrained"}
        trace["projected_score_profiles"] = len(baseline)
        trace["semantics"] = "factive under declared controller bound; stale signal does not constrain current ballots"
    if history is not None:
        if obs.report_provenance and len(obs.report_provenance) != len(obs.messages):
            raise ElectionError("report provenance does not match delivered reports")
        reports = []
        for index, (sender, channel, report_ballot) in enumerate(obs.messages):
            generated = source_round = delivered = None
            if obs.report_provenance:
                source_sender, source_channel, generated, source_round, delivered, source_ballot = obs.report_provenance[index]
                if ((source_sender, source_channel, source_ballot) != (sender, channel, report_ballot)
                        or any(type(value) is not int for value in (generated, source_round, delivered))
                        or source_round < 0 or generated != source_round + 1 or delivered != generated + 1
                        or delivered != obs.round):
                    raise ElectionError("invalid report provenance")
            reports.append({"sender": sender, "channel": channel, "ballot": list(report_ballot),
                            "source_round": source_round, "generated_round": generated, "delivered_round": delivered})
        history.append({"round": obs.round, "own_preference": list(obs.own_preference),
                        "own_previous_ballot": list(obs.own_previous_ballot), "own_position": list(obs.own_position),
                        "electorate": list(roster), "public_neighbors": list(obs.public_neighbors),
                        "private_channels": list(obs.own_channels),
                        "trusted_ballots": [{"sender": sender, "source": source, "completed_round": timestamp,
                                             "ballot": list(ballot)}
                                            for sender, source, timestamp, ballot in obs.sensed_ballots],
                        "received_reports": reports})
        if signal_aware:
            history[-1]["public_signal"] = dict(trace["signal"])
        trace["observation_history"] = history
        trace["history_scope"] = "observations since policy activation; current worlds allow arbitrary intervening changes"
    return ballot, trace
