"""Deterministic plurality baseline and explicit committed rounds."""

from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
import json
import math
from typing import Any, Mapping, Sequence
from .model import ElectionError, Frame, Scenario, Intervention, apply_overrides, make_scenario
from .network import proximity_edges, random_walk
from .policies import Observation, canonical_json, load_plugin, policy_rng
from .provenance import manifest
from .voting import STRATEGIC, decide, validate_parameters


def count_plurality(parties: Sequence[str], k: int, ballots: Mapping[str, Sequence[str]]) -> tuple[tuple[tuple[str, int], ...], str]:
    """Count first choices; order of parties breaks ties."""
    if isinstance(parties, (str, bytes)) or not isinstance(parties, (list, tuple)) or not parties or any(not isinstance(party, str) or not party.strip() for party in parties) or len(set(parties)) != len(parties):
        raise ElectionError("party order must be non-empty and unique")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(parties):
        raise ElectionError("invalid ballot length")
    if not isinstance(ballots, Mapping) or not ballots:
        raise ElectionError("at least one ballot is required")
    counts = Counter()
    for person, ballot in ballots.items():
        if not isinstance(person, str) or not person.strip():
            raise ElectionError("ballot person id must be a non-empty string")
        if isinstance(ballot, (str, bytes)) or not isinstance(ballot, (list, tuple)):
            raise ElectionError(f"{person}: ballot must be a sequence of parties")
        if len(ballot) != k or any(not isinstance(x, str) for x in ballot) or len(set(ballot)) != k or not set(ballot) <= set(parties):
            raise ElectionError(f"{person}: ballot must contain exactly {k} distinct known parties")
        counts[ballot[0]] += 1
    winner = max(parties, key=lambda party: counts[party])
    return tuple((party, counts[party]) for party in parties), winner


def _graph_after(frame: Frame, actions: Sequence[Intervention]) -> tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, set[str]]]:
    persistent = set(frame.persistent_edges)
    campaign = set(frame.campaign_edges)
    channels = {name: set(members) for name, members in frame.private_channels}
    for action in actions:
        for target in action.remove_edges:
            if (action.person, target) not in persistent:
                raise ElectionError(f"round {action.round}: cannot remove absent edge {action.person!r}->{target!r}")
            persistent.remove((action.person, target))
        for target in action.add_edges:
            if (action.person, target) in persistent:
                raise ElectionError(f"round {action.round}: cannot add existing edge {action.person!r}->{target!r}")
            persistent.add((action.person, target))
        for target in action.remove_campaign_edges:
            if (action.person, target) not in campaign:
                raise ElectionError(f"round {action.round}: cannot remove absent campaign edge {action.person!r}->{target!r}")
            campaign.remove((action.person, target))
        for target in action.add_campaign_edges:
            if (action.person, target) in campaign:
                raise ElectionError(f"round {action.round}: cannot add existing campaign edge {action.person!r}->{target!r}")
            campaign.add((action.person, target))
        for channel in action.remove_channels:
            if action.person not in channels[channel]:
                raise ElectionError(f"round {action.round}: person not in channel {channel!r}")
            channels[channel].remove(action.person)
        for channel in action.add_channels:
            if action.person in channels[channel]:
                raise ElectionError(f"round {action.round}: person already in channel {channel!r}")
            channels[channel].add(action.person)
    return persistent, campaign, channels


class Simulation:
    """Honest stationary baseline; every step commits one validated frame."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self._runtime_manifest = manifest()
        self.manual_interventions: tuple[Intervention, ...] = ()
        self.plugins = self._load_plugins(())
        ballots = {person.id: person.preference[:scenario.k] for person in scenario.people}
        counts, winner = count_plurality(scenario.parties, scenario.k, ballots)
        self.initial_poll = tuple(count for _, count in counts)
        groups = {g.id: g for g in scenario.groups}
        for person in scenario.people:
            group = apply_overrides(groups[person.group], person.overrides)
            if group.voting in STRATEGIC:
                validate_parameters(json.loads(group.parameters).get("voting", {}), scenario.parties, len(scenario.people))
        positions = {person.id: person.position for person in scenario.people}
        self.frames = [Frame(0, tuple(ballots.items()), counts, winner, tuple(positions.items()),
                             scenario.persistent_edges, proximity_edges(positions, scenario.radius), (), (),
                             tuple((p.id, p.preference) for p in scenario.people),
                             tuple((p.id, p.group) for p in scenario.people), (),
                             tuple((p.id, "null") for p in scenario.people),
                             tuple((p.id, p.overrides) for p in scenario.people), scenario.private_channels, (), (), scenario.campaign_edges)]

    def _load_plugins(self, manual: Sequence[Intervention]) -> dict:
        references = {getattr(g, field) for g in self.scenario.groups for field in ("voting", "movement", "graph", "communication")}
        for encoded in [p.overrides for p in self.scenario.people] + [a.overrides for a in (*self.scenario.interventions, *manual) if a.overrides is not None]:
            overrides = json.loads(encoded)
            references.update(overrides[field] for field in ("voting", "movement", "graph", "communication") if field in overrides)
        existing = getattr(self, "plugins", {})
        return {reference: existing[reference] if reference in existing else load_plugin(reference)
                for reference in sorted(references) if reference.startswith("python:")}

    @property
    def current(self) -> Frame:
        return self.frames[-1]

    @property
    def runtime_manifest(self) -> dict[str, str | int]:
        return dict(self._runtime_manifest)

    def _assert_runtime_unchanged(self) -> None:
        if manifest() != self._runtime_manifest:
            raise ElectionError("runtime or core source changed during run; save history and restart")

    def step(self) -> Frame:
        self._assert_runtime_unchanged()
        previous = dict(self.current.positions)
        preferences = dict(self.current.preferences)
        memberships = dict(self.current.groups)
        overrides = dict(self.current.overrides)
        actions = (tuple(replace(a, origin="scheduled") for a in self.scenario.interventions if a.round == self.current.round + 1)
                   + tuple(replace(a, origin="interactive") for a in self.manual_interventions if a.round == self.current.round + 1))
        persistent, campaign, channels = _graph_after(self.current, actions)
        for action in actions:
            if action.position is not None:
                previous[action.person] = action.position
            if action.preference is not None:
                preferences[action.person] = action.preference
            if action.group is not None:
                memberships[action.person] = action.group
            if action.overrides is not None:
                overrides[action.person] = action.overrides
        groups = {group.id: group for group in self.scenario.groups}
        prior_groups = dict(self.current.groups)
        prior_overrides = dict(self.current.overrides)
        effective = {}
        def policy(group_id: str, encoded: str):
            key = (group_id, encoded)
            if key not in effective:
                effective[key] = apply_overrides(groups[group_id], encoded)
            return effective[key]
        permissions = {person.id: policy(memberships[person.id], overrides[person.id]).capabilities
                       for person in self.scenario.people}
        def can_receive(person: str, channel: str) -> bool:
            capabilities = permissions[person]
            return capabilities.receive_public_reports if channel == "public" else capabilities.receive_private_reports
        for reference, (_, digest, path) in self.plugins.items():
            try:
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ElectionError(f"policy source changed during run: {reference}")
            except OSError as exc:
                raise ElectionError(f"cannot verify policy source {reference}: {exc}") from exc
        phase_memory = {(person, phase): data for person, phase, data in self.current.phase_memory}
        prior_inbox = defaultdict(list)
        for sender, recipient, channel, ballot in self.current.delivered:
            if can_receive(recipient, channel):
                prior_inbox[recipient].append((sender, channel, ballot))
        previous_ballots = dict(self.current.ballots)
        sensing_enabled = any(cap.sense_public_ballots or cap.sense_private_ballots for cap in permissions.values())
        def sensed(edges, private_channels):
            """Completed ballots visible through current authorized channels."""
            if not sensing_enabled:
                return {}
            result = defaultdict(list)
            for sender, recipient in sorted(edges):
                if permissions[recipient].sense_public_ballots:
                    result[recipient].append((sender, "public", self.current.round, previous_ballots[sender]))
            for name, members in sorted(private_channels.items()):
                members = sorted(members)
                for recipient in members:
                    if permissions[recipient].sense_private_ballots:
                        result[recipient].extend((sender, name, self.current.round, previous_ballots[sender])
                                                 for sender in members if sender != recipient)
            return {person: tuple(sorted(records)) for person, records in result.items()}
        old_public = defaultdict(set)
        old_edges = set(self.current.persistent_edges) | set(self.current.proximity_edges) | set(self.current.campaign_edges)
        for sender, recipient in old_edges:
            old_public[sender].add(recipient)
        old_sensors = defaultdict(list)
        for observer, sender, source, timestamp, ballot in self.current.ballot_sensors:
            capability = permissions[observer]
            if (source == "public" and capability.sense_public_ballots or
                    source != "public" and capability.sense_private_ballots):
                old_sensors[observer].append((sender, source, timestamp, ballot))
        def observation(person, position, messages, public, private, sensors):
            capabilities = permissions[person]
            return Observation(person, self.current.round + 1, self.scenario.parties, self.scenario.k,
                               preferences[person], position, tuple(messages), previous_ballots[person],
                               tuple(sorted(public)) if capabilities.observe_public_neighbors else (),
                               tuple(sorted(private)) if capabilities.observe_private_channels else (),
                               tuple(sensors.get(person, ())))
        def call_phase(person, group, phase, obs):
            reference = getattr(group, phase)
            function, _, _ = self.plugins[reference]
            old = policy(prior_groups[person], prior_overrides[person])
            key = (person, phase)
            try:
                previous_memory = json.loads(phase_memory.get(key, "null")) if (getattr(old, phase), old.parameters) == (reference, group.parameters) else None
                result = function(obs, json.loads(group.parameters), previous_memory,
                                  policy_rng(self.scenario.seed, person, self.current.round + 1, phase))
                if not isinstance(result, dict) or "memory" not in result:
                    raise ElectionError("policy must return an object containing memory")
                phase_memory[key] = canonical_json(result["memory"], f"{phase} memory")
                return result
            except Exception as exc:
                raise ElectionError(f"person {person!r}, round {self.current.round + 1}, {phase}: {exc}") from exc
        prior_channels = {person.id: tuple(name for name, members in self.current.private_channels if person.id in members)
                          for person in self.scenario.people}
        positions = {}
        for person in self.scenario.people:
            group = policy(memberships[person.id], overrides[person.id])
            pos = previous[person.id]
            if group.movement == "random_walk":
                phase_memory.pop((person.id, "movement"), None)
                positions[person.id] = random_walk(pos, group.max_step, self.scenario.seed, person.id, self.current.round + 1)
            elif group.movement.startswith("python:"):
                result = call_phase(person.id, group, "movement", observation(person.id, pos, prior_inbox[person.id], old_public[person.id], prior_channels[person.id], old_sensors))
                candidate = result.get("position")
                if set(result) != {"position", "memory"} or not isinstance(candidate, (list, tuple)) or len(candidate) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1 for x in candidate) or math.dist(pos, candidate) > group.max_step + 1e-12:
                    raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, movement: invalid or over-budget position")
                positions[person.id] = tuple(float(x) for x in candidate)
            else:
                positions[person.id] = pos
                phase_memory.pop((person.id, "movement"), None)
            if not group.capabilities.move and positions[person.id] != pos:
                raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, movement: capability denied")
        public_before_graph = persistent | campaign | set(proximity_edges(positions, self.scenario.radius))
        outgoing_before = defaultdict(set)
        for sender, recipient in public_before_graph:
            outgoing_before[sender].add(recipient)
        graph_sensors = sensed(public_before_graph, channels)
        graph_channels = {person.id: tuple(name for name, members in channels.items() if person.id in members)
                          for person in self.scenario.people}
        graph_actions = []
        ids = {person.id for person in self.scenario.people}
        for person in sorted(self.scenario.people, key=lambda p: p.id):
            group = policy(memberships[person.id], overrides[person.id])
            if not group.graph.startswith("python:"):
                phase_memory.pop((person.id, "graph"), None)
                continue
            result = call_phase(person.id, group, "graph", observation(person.id, positions[person.id], prior_inbox[person.id], outgoing_before[person.id], graph_channels[person.id], graph_sensors))
            keys = {"add_edges", "remove_edges", "add_channels", "remove_channels"}
            if set(result) - (keys | {"memory"}):
                raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, graph: unsupported action")
            values = {}
            for key in keys:
                items = result.get(key, [])
                allowed = (ids - {person.id}) if key.endswith("edges") else set(channels)
                if not isinstance(items, list) or any(not isinstance(x, str) or x not in allowed for x in items) or len(set(items)) != len(items):
                    raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, graph: invalid {key}")
                values[key] = tuple(sorted(items))
            if set(values["add_edges"]) & set(values["remove_edges"]) or set(values["add_channels"]) & set(values["remove_channels"]):
                raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, graph: conflicting actions")
            if ((values["add_edges"] or values["remove_edges"]) and not group.capabilities.modify_persistent_edges
                    or (values["add_channels"] or values["remove_channels"]) and not group.capabilities.modify_private_channels):
                raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, graph: capability denied")
            if any(values.values()):
                action = Intervention(self.current.round + 1, person.id, **values, origin="policy")
                temporary = replace(self.current, persistent_edges=tuple(sorted(persistent)),
                                    campaign_edges=tuple(sorted(campaign)),
                                    private_channels=tuple((name, tuple(sorted(members))) for name, members in sorted(channels.items())))
                persistent, campaign, channels = _graph_after(temporary, (action,))
                graph_actions.append(action)
        actions += tuple(graph_actions)
        public_edges = persistent | campaign | set(proximity_edges(positions, self.scenario.radius))
        outgoing = defaultdict(set)
        for sender, recipient in public_edges:
            outgoing[sender].add(recipient)
        voting_sensors = sensed(public_edges, channels)
        membership_channels = {person.id: tuple(name for name, members in channels.items() if person.id in members)
                               for person in self.scenario.people}
        pending = []
        delivered = tuple(message for message in self.current.pending if can_receive(message[1], message[2]))
        inbox = defaultdict(list)
        for sender, recipient, channel, ballot in delivered:
            inbox[recipient].append((sender, channel, ballot))
        for person in self.scenario.people:
            sender = person.id
            group = policy(memberships[sender], overrides[sender])
            allowed = {(recipient, "public") for recipient in outgoing[sender]} if group.capabilities.send_public_reports else set()
            if group.capabilities.send_private_reports:
                allowed.update((recipient, channel) for channel in membership_channels[sender] for recipient in channels[channel] if recipient != sender)
            if group.communication == "truthful":
                pending.extend((sender, recipient, channel, previous_ballots[sender]) for recipient, channel in sorted(allowed))
                phase_memory.pop((sender, "communication"), None)
            elif group.communication.startswith("python:"):
                result = call_phase(sender, group, "communication", observation(sender, positions[sender], inbox[sender], outgoing[sender], membership_channels[sender], voting_sensors))
                reports = result.get("reports")
                if set(result) != {"reports", "memory"} or not isinstance(reports, list):
                    raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: expected reports list")
                seen = set()
                for report in reports:
                    if not isinstance(report, dict) or set(report) != {"recipient", "channel", "ballot"} or not isinstance(report["recipient"], str) or not isinstance(report["channel"], str) or (report["recipient"], report["channel"]) not in allowed or (report["recipient"], report["channel"]) in seen or not isinstance(report["ballot"], (list, tuple)) or tuple(report["ballot"]) != previous_ballots[sender]:
                        raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: unauthorized, duplicate or untruthful report")
                    seen.add((report["recipient"], report["channel"]))
                    pending.append((sender, report["recipient"], report["channel"], previous_ballots[sender]))
            else:
                phase_memory.pop((sender, "communication"), None)
        ballots = {}
        memory = dict(self.current.policy_memory)
        for p in self.scenario.people:
            group = policy(memberships[p.id], overrides[p.id])
            preference = preferences[p.id]
            messages = inbox[p.id]
            if group.voting in STRATEGIC:
                old_policy = policy(prior_groups[p.id], prior_overrides[p.id])
                previous_memory = json.loads(memory[p.id]) if (old_policy.voting, old_policy.parameters) == (group.voting, group.parameters) else None
                observed = observation(p.id, positions[p.id], messages, outgoing[p.id], membership_channels[p.id], voting_sensors)
                try:
                    voting_params = json.loads(group.parameters).get("voting", {})
                    if previous_memory is None and self.current.round > 0 and (group.voting == "pivotal" or voting_params.get("information_source") == "poll"):
                        raise ElectionError("poll-based voting must be configured at episode start; cannot reconstruct unseen past deviations")
                    ballots[p.id], trace = decide(group.voting, observed, voting_params,
                                                 previous_memory, policy_rng(self.scenario.seed, p.id, self.current.round + 1),
                                                 len(self.scenario.people), self.initial_poll)
                    memory[p.id] = canonical_json(trace, "voting decision")
                except ElectionError as exc:
                    raise ElectionError(f"person {p.id!r}, round {self.current.round + 1}, voting: {exc}") from exc
            elif group.voting == "local_plurality" and messages:
                counts = Counter(ballot[0] for _, _, ballot in messages)
                highest = max(counts.values())
                choice = next(party for party in preference if counts[party] == highest)
                ballots[p.id] = (choice,) + tuple(x for x in preference if x != choice)[:self.scenario.k - 1]
                memory[p.id] = "null"
            elif group.voting == "sensed_plurality" and voting_sensors.get(p.id):
                # Multiple channels to the same person are not multiple votes.
                by_sender = {sender: ballot for sender, _, _, ballot in voting_sensors[p.id]}
                counts = Counter(ballot[0] for ballot in by_sender.values())
                highest = max(counts.values())
                choice = next(party for party in preference if counts[party] == highest)
                ballots[p.id] = (choice,) + tuple(x for x in preference if x != choice)[:self.scenario.k - 1]
                memory[p.id] = "null"
            elif group.voting.startswith("python:"):
                function, _, _ = self.plugins[group.voting]
                try:
                    observed = observation(p.id, positions[p.id], messages, outgoing[p.id], membership_channels[p.id], voting_sensors)
                    old_policy = policy(prior_groups[p.id], prior_overrides[p.id])
                    previous_memory = json.loads(memory[p.id]) if (old_policy.voting, old_policy.parameters) == (group.voting, group.parameters) else None
                    result = function(observed, json.loads(group.parameters), previous_memory,
                                      policy_rng(self.scenario.seed, p.id, self.current.round + 1))
                    if not isinstance(result, dict) or set(result) != {"ballot", "memory"}:
                        raise ElectionError("policy must return ballot and memory")
                    memory[p.id] = canonical_json(result["memory"], "policy memory")
                    count_plurality(self.scenario.parties, self.scenario.k, {p.id: result["ballot"]})
                    ballots[p.id] = result["ballot"]
                except Exception as exc:
                    raise ElectionError(f"person {p.id!r}, round {self.current.round + 1}, voting: {exc}") from exc
            else:
                ballots[p.id] = preference[:self.scenario.k]
                memory[p.id] = "null"
        for action in actions:
            if action.ballot is not None:
                ballots[action.person] = action.ballot
        counts, winner = count_plurality(self.scenario.parties, self.scenario.k, ballots)
        result = Frame(self.current.round + 1, tuple((p, tuple(ballot)) for p, ballot in ballots.items()), counts, winner, tuple(positions.items()),
                       tuple(sorted(persistent)), proximity_edges(positions, self.scenario.radius), delivered,
                       tuple(sorted(pending)), tuple(preferences.items()), tuple(memberships.items()), actions,
                       tuple(memory.items()), tuple(overrides.items()),
                       tuple((name, tuple(sorted(members))) for name, members in sorted(channels.items())),
                       tuple((person, phase, data) for (person, phase), data in sorted(phase_memory.items())),
                       tuple((observer, sender, source, timestamp, ballot)
                             for observer, observations in sorted(voting_sensors.items())
                             for sender, source, timestamp, ballot in observations), tuple(sorted(campaign)))
        self.frames.append(result)
        return result

    def run(self, rounds: int | None = None) -> tuple[Frame, ...]:
        count = self.scenario.rounds if rounds is None else rounds
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ElectionError("rounds must be a non-negative integer")
        for _ in range(count):
            self.step()
        return tuple(self.frames)

    def checkpoint(self) -> dict[str, Any]:
        """Capture the exact replayable history for the currently implemented policies."""
        return {"version": 10, "manifest": self.runtime_manifest, "scenario": self.scenario.as_dict(),
                "policy_digests": {name: digest for name, (_, digest, _) in sorted(self.plugins.items())},
                "manual_interventions": [self._action_dict(a) for a in self.manual_interventions],
                "frames": [frame.as_dict() for frame in self.frames]}

    @staticmethod
    def _action_dict(action: Intervention) -> dict[str, Any]:
        return {"round": action.round, "person": action.person,
                **({"group": action.group} if action.group is not None else {}),
                **({"preference": list(action.preference)} if action.preference is not None else {}),
                **({"position": list(action.position)} if action.position is not None else {}),
                **({"ballot": list(action.ballot)} if action.ballot is not None else {}),
                **({"overrides": json.loads(action.overrides)} if action.overrides is not None else {}),
                **({"add_edges": list(action.add_edges)} if action.add_edges else {}),
                **({"remove_edges": list(action.remove_edges)} if action.remove_edges else {}),
                **({"add_channels": list(action.add_channels)} if action.add_channels else {}),
                **({"remove_channels": list(action.remove_channels)} if action.remove_channels else {}),
                **({"add_campaign_edges": list(action.add_campaign_edges)} if action.add_campaign_edges else {}),
                **({"remove_campaign_edges": list(action.remove_campaign_edges)} if action.remove_campaign_edges else {})}

    def edit_after(self, round_number: int, person: str, **changes: Any) -> None:
        """Rewind to a committed frame and queue an atomic edit for its next boundary."""
        self._assert_runtime_unchanged()
        if isinstance(round_number, bool) or not isinstance(round_number, int) or not 0 <= round_number < len(self.frames):
            raise ElectionError("edit round must name a committed frame")
        if not changes or set(changes) - {"group", "preference", "position", "ballot", "overrides", "add_edges", "remove_edges", "add_channels", "remove_channels", "add_campaign_edges", "remove_campaign_edges"} or any(value is None for value in changes.values()):
            raise ElectionError("edit requires supported, non-null changes")
        proposed = {"round": round_number + 1, "person": person, **changes}
        raw = self.scenario.as_dict()
        raw["interventions"] = [proposed]
        action = make_scenario(raw).interventions[0]
        # Multiple queued edits at the latest boundary merge per-person; rewinding
        # discards every edit generated after the retained frame.
        same_boundary = round_number == self.current.round
        kept = [a for a in self.manual_interventions if a.round <= round_number or (same_boundary and a.round == round_number + 1)]
        existing = next((a for a in kept if a.round == action.round and a.person == action.person), None)
        if existing:
            action = replace(existing,
                             group=action.group if action.group is not None else existing.group,
                             preference=action.preference if action.preference is not None else existing.preference,
                             position=action.position if action.position is not None else existing.position,
                             ballot=action.ballot if action.ballot is not None else existing.ballot,
                             overrides=action.overrides if action.overrides is not None else existing.overrides,
                             add_edges=tuple(sorted(set(existing.add_edges) | set(action.add_edges))),
                             remove_edges=tuple(sorted(set(existing.remove_edges) | set(action.remove_edges))),
                             add_channels=tuple(sorted(set(existing.add_channels) | set(action.add_channels))),
                             remove_channels=tuple(sorted(set(existing.remove_channels) | set(action.remove_channels))),
                             add_campaign_edges=tuple(sorted(set(existing.add_campaign_edges) | set(action.add_campaign_edges))),
                             remove_campaign_edges=tuple(sorted(set(existing.remove_campaign_edges) | set(action.remove_campaign_edges))))
            if (set(action.add_edges) & set(action.remove_edges) or set(action.add_channels) & set(action.remove_channels)
                    or set(action.add_campaign_edges) & set(action.remove_campaign_edges)):
                raise ElectionError("conflicting queued graph edits; rewind and reapply")
            kept.remove(existing)
        updated = tuple(sorted((*kept, action), key=lambda a: (a.round, a.person)))
        scheduled = tuple(a for a in self.scenario.interventions if a.round == round_number + 1)
        _graph_after(self.frames[round_number], scheduled + tuple(a for a in updated if a.round == round_number + 1))
        plugins = self._load_plugins(updated)
        self.frames = self.frames[:round_number + 1]
        self.manual_interventions = updated
        self.plugins = plugins

    @classmethod
    def from_checkpoint(cls, payload: Mapping[str, Any], *, allow_environment_change: bool = False) -> "Simulation":
        """Recompute and verify history before accepting a checkpoint."""
        if not isinstance(payload, Mapping) or type(payload.get("version")) is not int or payload["version"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            raise ElectionError("unsupported or invalid checkpoint")
        expected = {"version", "scenario", "frames"} | ({"manual_interventions"} if payload["version"] >= 2 else set()) | ({"policy_digests"} if payload["version"] >= 3 else set()) | ({"manifest"} if payload["version"] >= 6 else set())
        if set(payload) != expected:
            raise ElectionError("invalid checkpoint fields")
        if payload["version"] >= 6 and payload["manifest"] != manifest() and not allow_environment_change:
            raise ElectionError("checkpoint runtime or core source changed; explicitly allow migration after review")
        frames = payload["frames"]
        if not isinstance(frames, list) or not frames:
            raise ElectionError("checkpoint must contain an initial frame")
        simulation = cls(make_scenario(payload["scenario"]))
        raw = simulation.scenario.as_dict()
        raw["interventions"] = payload.get("manual_interventions", [])
        simulation.manual_interventions = make_scenario(raw).interventions
        simulation.plugins = simulation._load_plugins(simulation.manual_interventions)
        if payload["version"] < 3 and simulation.plugins:
            raise ElectionError("legacy checkpoints cannot validate plugin sources")
        if payload["version"] >= 3 and payload["policy_digests"] != simulation.checkpoint()["policy_digests"]:
            raise ElectionError("checkpoint plugin source digest changed")
        if any(a.round > len(frames) for a in simulation.manual_interventions):
            raise ElectionError("manual intervention is beyond the next boundary")
        simulation.run(len(frames) - 1)
        expected_frames = simulation.checkpoint()["frames"]
        if payload["version"] < 3:
            for frame in expected_frames:
                frame.pop("policy_memory")
        if payload["version"] < 4:
            for frame in expected_frames:
                frame.pop("overrides")
        if payload["version"] < 5:
            for frame in expected_frames:
                frame.pop("private_channels")
        if payload["version"] < 7:
            for frame in expected_frames:
                frame.pop("phase_memory")
        if payload["version"] < 8:
            for frame in expected_frames:
                frame.pop("ballot_sensors")
        if payload["version"] < 9:
            for frame in expected_frames:
                frame.pop("campaign_edges")
        if payload["version"] < 10:
            for frame in expected_frames:
                for event in frame["interventions"]:
                    event.pop("origin", None)
        if payload["version"] == 1 and frames:
            layouts = [
                {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges"},
                {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges", "delivered", "pending"},
                {"round", "ballots", "counts", "winner", "positions", "persistent_edges", "proximity_edges", "delivered", "pending", "preferences", "groups", "interventions"},
            ]
            if not isinstance(frames[0], dict) or set(frames[0]) not in layouts or any(not isinstance(f, dict) or set(f) != set(frames[0]) for f in frames):
                raise ElectionError("unknown version 1 frame layout")
            expected_frames = [{key: frame[key] for key in frames[0]} for frame in expected_frames]
        if expected_frames != frames:
            raise ElectionError("checkpoint history does not match the scenario and seed")
        return simulation
