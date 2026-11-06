"""Validated immutable inputs and committed election frames."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping
import math
import json


class ElectionError(ValueError):
    """A scenario, ballot or simulation command is invalid."""


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ElectionError(f"{label} must be a non-empty string")
    return value


def _int(value: Any, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ElectionError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class Person:
    id: str
    group: str
    preference: tuple[str, ...]
    position: tuple[float, float]
    overrides: str


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Policy-facing permissions; legacy scenarios retain their existing behavior."""
    observe_public_neighbors: bool = True
    observe_private_channels: bool = True
    sense_public_ballots: bool = False
    sense_private_ballots: bool = False
    receive_public_reports: bool = True
    receive_private_reports: bool = True
    send_public_reports: bool = True
    send_private_reports: bool = True
    modify_persistent_edges: bool = True
    modify_private_channels: bool = True
    move: bool = True


@dataclass(frozen=True, slots=True)
class Group:
    id: str
    voting: str
    movement: str
    max_step: float
    communication: str
    graph: str
    parameters: str
    capabilities: Capabilities


@dataclass(frozen=True, slots=True)
class Intervention:
    round: int
    person: str
    group: str | None = None
    preference: tuple[str, ...] | None = None
    position: tuple[float, float] | None = None
    ballot: tuple[str, ...] | None = None
    overrides: str | None = None
    add_edges: tuple[str, ...] = ()
    remove_edges: tuple[str, ...] = ()
    add_channels: tuple[str, ...] = ()
    remove_channels: tuple[str, ...] = ()
    add_campaign_edges: tuple[str, ...] = ()
    remove_campaign_edges: tuple[str, ...] = ()
    origin: str | None = None


@dataclass(frozen=True, slots=True)
class Scenario:
    parties: tuple[str, ...]
    k: int
    people: tuple[Person, ...]
    seed: int
    rounds: int
    groups: tuple[Group, ...]
    radius: float | None
    persistent_edges: tuple[tuple[str, str], ...]
    private_channels: tuple[tuple[str, tuple[str, ...]], ...]
    interventions: tuple[Intervention, ...]
    campaign_edges: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "parties": list(self.parties), "k": self.k, "seed": self.seed, "rounds": self.rounds,
            "groups": {g.id: {"voting": g.voting, "movement": g.movement, "max_step": g.max_step,
                               "communication": g.communication, "graph": g.graph,
                               "parameters": json.loads(g.parameters),
                               "capabilities": asdict(g.capabilities)} for g in self.groups},
            "people": [{"id": p.id, "group": p.group, "preference": list(p.preference), "position": list(p.position),
                        "overrides": json.loads(p.overrides)} for p in self.people],
            "network": {"persistent_edges": [list(e) for e in self.persistent_edges],
                        "campaign_edges": [list(e) for e in self.campaign_edges],
                        "private_channels": {name: list(members) for name, members in self.private_channels}},
            "interventions": [{"round": i.round, "person": i.person,
                               **({"group": i.group} if i.group is not None else {}),
                               **({"preference": list(i.preference)} if i.preference is not None else {}),
                               **({"position": list(i.position)} if i.position is not None else {}),
                               **({"ballot": list(i.ballot)} if i.ballot is not None else {}),
                               **({"overrides": json.loads(i.overrides)} if i.overrides is not None else {}),
                               **({"add_edges": list(i.add_edges)} if i.add_edges else {}),
                               **({"remove_edges": list(i.remove_edges)} if i.remove_edges else {}),
                               **({"add_channels": list(i.add_channels)} if i.add_channels else {}),
                               **({"remove_channels": list(i.remove_channels)} if i.remove_channels else {}),
                               **({"add_campaign_edges": list(i.add_campaign_edges)} if i.add_campaign_edges else {}),
                               **({"remove_campaign_edges": list(i.remove_campaign_edges)} if i.remove_campaign_edges else {})}
                              for i in self.interventions],
        }
        if self.radius is not None:
            result["network"]["radius"] = self.radius
        return result


@dataclass(frozen=True, slots=True)
class Frame:
    round: int
    ballots: tuple[tuple[str, tuple[str, ...]], ...]
    counts: tuple[tuple[str, int], ...]
    winner: str
    positions: tuple[tuple[str, tuple[float, float]], ...]
    persistent_edges: tuple[tuple[str, str], ...]
    proximity_edges: tuple[tuple[str, str], ...]
    delivered: tuple[tuple[str, str, str, tuple[str, ...]], ...]
    pending: tuple[tuple[str, str, str, tuple[str, ...]], ...]
    preferences: tuple[tuple[str, tuple[str, ...]], ...]
    groups: tuple[tuple[str, str], ...]
    interventions: tuple[Intervention, ...]
    policy_memory: tuple[tuple[str, str], ...]
    overrides: tuple[tuple[str, str], ...]
    private_channels: tuple[tuple[str, tuple[str, ...]], ...]
    phase_memory: tuple[tuple[str, str, str], ...]
    ballot_sensors: tuple[tuple[str, str, str, int, tuple[str, ...]], ...]
    campaign_edges: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"round": self.round, "ballots": {p: list(b) for p, b in self.ballots},
                "counts": dict(self.counts), "winner": self.winner,
                "positions": {p: list(pos) for p, pos in self.positions},
                "persistent_edges": [list(edge) for edge in self.persistent_edges],
                "proximity_edges": [list(edge) for edge in self.proximity_edges],
                "campaign_edges": [list(edge) for edge in self.campaign_edges],
                "delivered": [[a, b, channel, list(ballot)] for a, b, channel, ballot in self.delivered],
                "pending": [[a, b, channel, list(ballot)] for a, b, channel, ballot in self.pending],
                "preferences": {p: list(pref) for p, pref in self.preferences}, "groups": dict(self.groups),
                "interventions": [{"round": i.round, "person": i.person,
                                   **({"origin": i.origin} if i.origin is not None else {}),
                                   **({"group": i.group} if i.group is not None else {}),
                                   **({"preference": list(i.preference)} if i.preference is not None else {}),
                                   **({"position": list(i.position)} if i.position is not None else {}),
                                   **({"ballot": list(i.ballot)} if i.ballot is not None else {}),
                                   **({"overrides": json.loads(i.overrides)} if i.overrides is not None else {}),
                                   **({"add_edges": list(i.add_edges)} if i.add_edges else {}),
                                   **({"remove_edges": list(i.remove_edges)} if i.remove_edges else {}),
                                   **({"add_channels": list(i.add_channels)} if i.add_channels else {}),
                                   **({"remove_channels": list(i.remove_channels)} if i.remove_channels else {}),
                                   **({"add_campaign_edges": list(i.add_campaign_edges)} if i.add_campaign_edges else {}),
                                   **({"remove_campaign_edges": list(i.remove_campaign_edges)} if i.remove_campaign_edges else {})}
                                  for i in self.interventions],
                "policy_memory": {person: json.loads(memory) for person, memory in self.policy_memory},
                "overrides": {person: json.loads(value) for person, value in self.overrides},
                "private_channels": {name: list(members) for name, members in self.private_channels},
                "phase_memory": [[person, phase, json.loads(memory)] for person, phase, memory in self.phase_memory],
                "ballot_sensors": [[observer, sender, source, round_number, list(ballot)]
                                   for observer, sender, source, round_number, ballot in self.ballot_sensors]}


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ElectionError(f"{label} must be finite and in [{minimum}, {maximum}]")
    return float(value)


def _make_group(group: str, policy: Mapping[str, Any]) -> Group:
    from .voting import VOTING_POLICIES, STRATEGIC, validate_parameters
    _id(group, "group")
    if not isinstance(policy, dict) or set(policy) - {"voting", "movement", "max_step", "communication", "graph", "parameters", "capabilities"} or not isinstance(policy.get("voting"), str) or not (policy["voting"] in VOTING_POLICIES or policy["voting"].startswith("python:")):
        raise ElectionError(f"group {group!r}: expected supported voting and movement")
    movement = policy.get("movement", "stationary")
    if not isinstance(movement, str) or not (movement in ("stationary", "random_walk") or movement.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported movement {movement!r}")
    max_step = _number(policy.get("max_step", 0), "max_step", 0, 1)
    communication = policy.get("communication", "none")
    if not isinstance(communication, str) or not (communication in ("none", "truthful") or communication.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported communication {communication!r}")
    graph = policy.get("graph", "none")
    if not isinstance(graph, str) or not (graph == "none" or graph.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported graph policy {graph!r}")
    params = policy.get("parameters", {})
    if not isinstance(params, dict):
        raise ElectionError(f"group {group!r}: parameters must be a table")
    if policy["voting"] in STRATEGIC:
        validate_parameters(params.get("voting", {}))
    try:
        encoded = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ElectionError(f"group {group!r}: parameters must be finite JSON data") from exc
    capability_data = policy.get("capabilities", {})
    if (not isinstance(capability_data, dict) or set(capability_data) - set(Capabilities.__dataclass_fields__)
            or any(type(value) is not bool for value in capability_data.values())):
        raise ElectionError(f"group {group!r}: capabilities must contain supported boolean permissions")
    capabilities = Capabilities(**capability_data)
    if capabilities.sense_private_ballots and not capabilities.observe_private_channels:
        raise ElectionError(f"group {group!r}: private ballot sensing requires private channel observation")
    return Group(group, policy["voting"], movement, max_step, communication, graph, encoded, capabilities)


def _overrides(value: Any) -> str:
    if not isinstance(value, dict):
        raise ElectionError("overrides must be a table")
    _make_group("override", {"voting": "sincere", **value})
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ElectionError("overrides must be finite JSON data") from exc


def apply_overrides(group: Group, overrides: str) -> Group:
    if overrides == "{}":
        return group
    changes = json.loads(overrides)
    capabilities = {**asdict(group.capabilities), **changes.pop("capabilities", {})}
    return _make_group(group.id, {"voting": group.voting, "movement": group.movement,
                                 "max_step": group.max_step, "communication": group.communication,
                                 "graph": group.graph, "parameters": json.loads(group.parameters),
                                 **changes, "capabilities": capabilities})


def make_scenario(raw: Mapping[str, Any]) -> Scenario:
    """Validate and normalize a TOML/JSON-compatible explicit electorate."""
    if not isinstance(raw, Mapping):
        raise ElectionError("scenario must be a table")
    allowed = {"parties", "k", "seed", "rounds", "groups", "people", "network", "interventions"}
    unknown = set(raw) - allowed
    if unknown:
        raise ElectionError(f"unknown scenario keys: {sorted(unknown)}")
    party_data = raw.get("parties")
    if not isinstance(party_data, list) or not party_data:
        raise ElectionError("parties must be a non-empty list")
    parties = tuple(_id(x, "party") for x in party_data)
    if len(set(parties)) != len(parties):
        raise ElectionError("parties must be unique")
    k = _int(raw.get("k"), "k", 1)
    if k > len(parties):
        raise ElectionError("k cannot exceed number of parties")
    seed = _int(raw.get("seed", 0), "seed", 0)
    rounds = _int(raw.get("rounds", 1), "rounds", 0)
    groups = raw.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise ElectionError("groups must be a non-empty table")
    normalized_groups = [_make_group(group, policy) for group, policy in groups.items()]
    groups_by_id = {group.id: group for group in normalized_groups}
    raw_people = raw.get("people")
    if not isinstance(raw_people, list) or not raw_people:
        raise ElectionError("people must be a non-empty list")
    people = []
    for item in raw_people:
        if not isinstance(item, dict) or not {"id", "group", "preference"} <= set(item) or set(item) - {"id", "group", "preference", "position", "overrides"}:
            raise ElectionError("each person requires id, group and preference; position and overrides are optional")
        person_id = _id(item["id"], "person id")
        group = _id(item["group"], "person group")
        if group not in groups:
            raise ElectionError(f"person {person_id!r}: unknown group {group!r}")
        pref = item["preference"]
        if not isinstance(pref, list) or len(pref) != len(parties) or any(not isinstance(x, str) for x in pref):
            raise ElectionError(f"person {person_id!r}: preference must rank every party once")
        if set(pref) != set(parties):
            raise ElectionError(f"person {person_id!r}: preference must rank every party once")
        position = item.get("position", [0.5, 0.5])
        if not isinstance(position, list) or len(position) != 2:
            raise ElectionError(f"person {person_id!r}: position must have two coordinates")
        coords = tuple(_number(value, "coordinate", 0, 1) for value in position)
        overrides = _overrides(item.get("overrides", {}))
        apply_overrides(groups_by_id[group], overrides)
        people.append(Person(person_id, group, tuple(pref), coords, overrides))
    if len({person.id for person in people}) != len(people):
        raise ElectionError("person ids must be unique")
    network = raw.get("network", {})
    if not isinstance(network, dict) or set(network) - {"radius", "persistent_edges", "campaign_edges", "private_channels"}:
        raise ElectionError("network must contain only supported network options")
    radius = _number(network["radius"], "radius", 0, math.sqrt(2)) if "radius" in network else None
    ids = {person.id for person in people}
    def edges_for_layer(name: str) -> tuple[tuple[str, str], ...]:
        edges = network.get(name, [])
        if not isinstance(edges, list):
            raise ElectionError(f"{name} must be a list")
        normalized = []
        for edge in edges:
            if not isinstance(edge, list) or len(edge) != 2 or any(not isinstance(x, str) for x in edge) or edge[0] not in ids or edge[1] not in ids or edge[0] == edge[1]:
                raise ElectionError(f"each {name} edge must connect two different known people")
            normalized.append(tuple(edge))
        if len(set(normalized)) != len(normalized):
            raise ElectionError(f"{name} edges must be unique")
        return tuple(sorted(normalized))
    normalized_edges = edges_for_layer("persistent_edges")
    normalized_campaign = edges_for_layer("campaign_edges")
    channels = network.get("private_channels", {})
    if not isinstance(channels, dict):
        raise ElectionError("private_channels must be a table")
    normalized_channels = []
    for channel, members in channels.items():
        _id(channel, "channel")
        if channel == "public" or not isinstance(members, list) or any(not isinstance(x, str) or x not in ids for x in members) or len(set(members)) != len(members):
            raise ElectionError(f"channel {channel!r}: members must be unique known people; name public is reserved")
        normalized_channels.append((channel, tuple(sorted(members))))
    interventions = raw.get("interventions", [])
    if not isinstance(interventions, list):
        raise ElectionError("interventions must be a list")
    normalized_interventions = []
    seen = set()
    for action in interventions:
        changes = {"group", "preference", "position", "ballot", "overrides", "add_edges", "remove_edges", "add_channels", "remove_channels", "add_campaign_edges", "remove_campaign_edges"}
        if not isinstance(action, dict) or not {"round", "person"} <= set(action) or set(action) - ({"round", "person"} | changes) or not set(action) & changes:
            raise ElectionError("intervention requires round, person and supported changes")
        if any(action[key] is None for key in changes if key in action):
            raise ElectionError("intervention changes cannot be null")
        target_round = _int(action["round"], "intervention round", 1)
        target = _id(action["person"], "intervention person")
        if target not in ids or (target_round, target) in seen:
            raise ElectionError("intervention person must exist and be unique within the round")
        seen.add((target_round, target))
        group = action.get("group")
        if group is not None and (not isinstance(group, str) or group not in groups):
            raise ElectionError("intervention group is unknown")
        preference = action.get("preference")
        if preference is not None:
            if not isinstance(preference, list) or len(preference) != len(parties) or any(not isinstance(x, str) for x in preference) or set(preference) != set(parties):
                raise ElectionError("intervention preference must rank every party once")
            preference = tuple(preference)
        position = action.get("position")
        if position is not None:
            if not isinstance(position, list) or len(position) != 2:
                raise ElectionError("intervention position must have two coordinates")
            position = tuple(_number(value, "coordinate", 0, 1) for value in position)
        ballot = action.get("ballot")
        if ballot is not None:
            if not isinstance(ballot, list) or len(ballot) != k or any(not isinstance(x, str) for x in ballot) or len(set(ballot)) != k or not set(ballot) <= set(parties):
                raise ElectionError("intervention ballot must contain exactly k distinct known parties")
            ballot = tuple(ballot)
        overrides = _overrides(action["overrides"]) if "overrides" in action else None
        def targets(key: str, allowed: set[str]) -> tuple[str, ...]:
            value = action.get(key, [])
            if not isinstance(value, list) or any(not isinstance(x, str) or x not in allowed for x in value) or len(set(value)) != len(value):
                raise ElectionError(f"{key} must contain unique known targets")
            return tuple(sorted(value))
        add_edges = targets("add_edges", ids - {target}); remove_edges = targets("remove_edges", ids - {target})
        add_channels = targets("add_channels", set(channels)); remove_channels = targets("remove_channels", set(channels))
        add_campaign = targets("add_campaign_edges", ids - {target}); remove_campaign = targets("remove_campaign_edges", ids - {target})
        if set(add_edges) & set(remove_edges) or set(add_channels) & set(remove_channels) or set(add_campaign) & set(remove_campaign):
            raise ElectionError("cannot add and remove the same target")
        normalized_interventions.append(Intervention(target_round, target, group, preference, position, ballot, overrides,
                                                      add_edges, remove_edges, add_channels, remove_channels, add_campaign, remove_campaign))
    return Scenario(parties, k, tuple(people), seed, rounds, tuple(normalized_groups), radius,
                    normalized_edges, tuple(sorted(normalized_channels)),
                    tuple(sorted(normalized_interventions, key=lambda action: (action.round, action.person))), normalized_campaign)
