"""Deterministic plurality baseline and explicit committed rounds."""

from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
import json
import math
from typing import Any, Mapping, Sequence
from .model import ElectionError, Frame, Scenario, Intervention, apply_overrides, make_scenario
from .network import proximity_edges, random_walk
from .campaign import select_campaign_edges
from .signals import generate_signal, trusting_response
from .alignment import advance_alignment
from .detector import update_detector
from .leaders import advance_leaders, perceived_preferences
from .policies import Observation, canonical_json, load_plugin, policy_rng
from .provenance import manifest
from .voting import STRATEGIC, decide, validate_parameters, direct_best_response, source_local_dominance, certified_conformity
from .epistemic import EPISTEMIC_POLICIES, SIGNAL_EPISTEMIC_POLICIES, response_from_observation, validate_signal_epistemic_group


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
        if scenario.convergence_case is not None or scenario.nomination is not None:
            # Dataclass replacement bypasses the public parser; revalidate every
            # certified composition before any convergence status is emitted.
            if make_scenario(scenario.as_dict()) != scenario:
                raise ElectionError("certified or nomination scenario is not canonically validated")
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
            if group.voting in EPISTEMIC_POLICIES and not group.capabilities.observe_electorate:
                raise ElectionError(f"person {person.id!r}: epistemic voting requires observe_electorate capability")
            validate_signal_epistemic_group(group, scenario.signal_controller, len(scenario.people), len(scenario.parties))
        positions = {person.id: person.position for person in scenario.people}
        radii = {person.id: apply_overrides(groups[person.group], person.overrides).proximity_radius
                 for person in scenario.people}
        radii = {person: value if value is not None else scenario.radius for person, value in radii.items()}
        self._initial_proximity = (scenario.static_proximity_edges if scenario.proximity_mode == "static"
                                   else proximity_edges(positions, scenario.radius, radii))
        self.frames = [Frame(0, tuple(ballots.items()), counts, winner, tuple(positions.items()),
                             scenario.persistent_edges, self._initial_proximity, (), (),
                             tuple((p.id, p.preference) for p in scenario.people),
                             tuple((p.id, p.group) for p in scenario.people), (),
                             tuple((p.id, "null") for p in scenario.people),
                             tuple((p.id, p.overrides) for p in scenario.people), scenario.private_channels, (), (), scenario.campaign_edges,
                             tuple((coalition.id,0) for coalition in scenario.coalitions), (),
                             tuple((coalition.id,0) for coalition in scenario.coalitions if coalition.sight_targets), (),
                             tuple((coalition.id,0) for coalition in scenario.coalitions if coalition.eavesdrop_channels), (),
                             () if scenario.campaign_controller is not None else None,
                             signal_spend=0 if scenario.signal_controller is not None else None,
                             alignment_ideals=tuple((p.id, p.ideal) for p in scenario.people) if scenario.alignment else None,
                             alignment_spend=0.0 if scenario.alignment else None,
                             detector=update_detector(scenario.detector, scenario.parties, dict(counts), 0) if scenario.detector else None,
                             leader_true=tuple((party, next(p.ideal for p in scenario.people if p.id == party)) for party in scenario.parties) if scenario.leaders else None,
                             leader_perceived=tuple((party, next(p.ideal for p in scenario.people if p.id == party)) for party in scenario.parties) if scenario.leaders else None,
                             leader_spend=tuple((party, 0.0) for party in scenario.parties) if scenario.leaders else None,
                             leader_memory=tuple((party, None, None) for party in scenario.parties) if scenario.leaders else ())]

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
        if self.scenario.convergence_case and self.manual_interventions:
            raise ElectionError("certified convergence episodes exclude interactive interventions")
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
        leader_true = leader_perceived = leader_spend = leader_memory = leader_signals = None
        if self.scenario.leaders is not None:
            if any(action.preference is not None for action in actions):
                raise ElectionError("leader scenarios derive preferences; ordinal preference interventions are unsupported")
            leader_true, leader_perceived, leader_spend, leader_memory, leader_signals = advance_leaders(
                self.scenario.leaders, self.scenario.seed, self.current.round + 1, self.scenario.parties,
                dict(self.current.counts), dict(self.current.leader_true), dict(self.current.leader_perceived),
                dict(self.current.leader_spend), {p: (d, s) for p, d, s in self.current.leader_memory})
        alignment_ideals = None; alignment_spend = None; alignment_changes = ()
        if self.scenario.alignment is not None:
            if any(action.preference is not None for action in actions):
                raise ElectionError("alignment scenarios derive preferences; ordinal preference interventions are unsupported")
            alignment_ideals, alignment_spend, alignment_changes, preferences = advance_alignment(
                self.scenario, dict(self.current.alignment_ideals), self.current.alignment_spend, self.current.round + 1,
                dict(self.current.leader_perceived)[self.scenario.alignment.attack.target] if self.scenario.leaders else None)
        if self.scenario.leaders is not None:
            ideals = alignment_ideals if alignment_ideals is not None else {p.id: p.ideal for p in self.scenario.people}
            preferences = perceived_preferences(self.scenario.parties, ideals, leader_perceived)
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
        coalition_by_member = {member: coalition for coalition in self.scenario.coalitions for member in coalition.members}
        for person in self.scenario.people:
            group = policy(memberships[person.id],overrides[person.id])
            validate_signal_epistemic_group(group, self.scenario.signal_controller, len(self.scenario.people), len(self.scenario.parties))
            coalition = coalition_by_member.get(person.id)
            if (group.capabilities.observe_target_preferences or group.voting in ("sight_plurality", "coalition_fusion")) and (
                    coalition is None or not coalition.sight_targets or not group.capabilities.observe_target_preferences):
                raise ElectionError(f"person {person.id!r}: preference sight requires coalition membership, sight targets and sight permission")
            if (group.capabilities.intercept_private_reports or group.voting in ("overheard_plurality", "coalition_fusion")) and (
                    coalition is None or not coalition.eavesdrop_channels or not group.capabilities.intercept_private_reports):
                raise ElectionError(f"person {person.id!r}: eavesdropping requires coalition membership, private channels and interception permission")
            if group.voting == "signal_confident" and (self.scenario.signal_controller is None or not group.capabilities.observe_public_signal):
                raise ElectionError(f"person {person.id!r}: signal_confident requires a signal controller and public-signal permission")
        sighted = defaultdict(list)
        overheard = defaultdict(list)
        latest_signal = self.current.signal_latest
        electorate = (tuple(sorted(p.id for p in self.scenario.people))
                      if any(cap.observe_electorate for cap in permissions.values()) else ())
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
        def observation(person, position, messages, public, private, sensors, report_delivery_round, coalition_budget=None, include_sight=False, include_signal=False):
            capabilities = permissions[person]
            return Observation(person, self.current.round + 1, self.scenario.parties, self.scenario.k,
                               preferences[person], position, tuple(messages), previous_ballots[person],
                               tuple(sorted(public)) if capabilities.observe_public_neighbors else (),
                               tuple(sorted(private)) if capabilities.observe_private_channels else (),
                               tuple(sensors.get(person, ())),
                               electorate if capabilities.observe_electorate else (),
                               tuple((sender, channel, report_delivery_round - 1, report_delivery_round - 2,
                                      report_delivery_round, ballot) for sender, channel, ballot in messages), coalition_budget,
                               tuple(sighted[person]) if include_sight else (),
                               tuple(overheard[person]) if include_sight else (),
                               (latest_signal[0],latest_signal[1],latest_signal[2])
                               if (include_sight or include_signal) and capabilities.observe_public_signal and latest_signal is not None else None,
                               ideals[person] if self.scenario.leaders else None,
                               tuple((party, leader_perceived[party]) for party in self.scenario.parties) if self.scenario.leaders else ())
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
                result = call_phase(person.id, group, "movement", observation(person.id, pos, prior_inbox[person.id], old_public[person.id], prior_channels[person.id], old_sensors, self.current.round))
                candidate = result.get("position")
                if set(result) != {"position", "memory"} or not isinstance(candidate, (list, tuple)) or len(candidate) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1 for x in candidate) or math.dist(pos, candidate) > group.max_step + 1e-12:
                    raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, movement: invalid or over-budget position")
                positions[person.id] = tuple(float(x) for x in candidate)
            else:
                positions[person.id] = pos
                phase_memory.pop((person.id, "movement"), None)
            if not group.capabilities.move and positions[person.id] != pos:
                raise ElectionError(f"person {person.id!r}, round {self.current.round + 1}, movement: capability denied")
        radii = {person.id: policy(memberships[person.id], overrides[person.id]).proximity_radius
                 for person in self.scenario.people}
        radii = {person: value if value is not None else self.scenario.radius for person, value in radii.items()}
        proximity = (self._initial_proximity if self.scenario.proximity_mode in ("frozen", "static")
                     else proximity_edges(positions, self.scenario.radius, radii))
        public_before_graph = persistent | campaign | set(proximity)
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
            result = call_phase(person.id, group, "graph", observation(person.id, positions[person.id], prior_inbox[person.id], outgoing_before[person.id], graph_channels[person.id], graph_sensors, self.current.round))
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
        public_edges = persistent | campaign | set(proximity)
        controller = self.scenario.campaign_controller
        purchased = set(self.current.campaign_controller_purchased or ())
        controller_eligible = None; controller_added = ()
        if controller is not None:
            controller_eligible, controller_added = select_campaign_edges(
                controller, {person:ballot[0] for person,ballot in previous_ballots.items()}, public_edges,
                purchased, policy_rng(self.scenario.seed,"campaign-controller",self.current.round + 1,"campaign"))
            campaign.update(controller_added)
            purchased.update(controller_added)
            public_edges.update(controller_added)
        signal_controller = self.scenario.signal_controller
        signal_spend = self.current.signal_spend
        signal_broadcast_cost = None
        if signal_controller is not None and (signal_controller.schedule == "repeated" or latest_signal is None):
            truth = tuple(dict(self.current.counts)[party] for party in self.scenario.parties)
            report, signal_broadcast_cost = generate_signal(signal_controller,self.scenario.parties,truth,
                signal_controller.lifetime_budget - signal_spend,
                policy_rng(self.scenario.seed,"public-signal",self.current.round + 1,"signal"))
            signal_spend += signal_broadcast_cost
            latest_signal = (self.current.round,self.current.round + 1,report,truth)
        outgoing = defaultdict(set)
        for sender, recipient in public_edges:
            outgoing[sender].add(recipient)
        voting_sensors = sensed(public_edges, channels)
        membership_channels = {person.id: tuple(name for name, members in channels.items() if person.id in members)
                               for person in self.scenario.people}
        pending = []
        total_spend = dict(self.current.coalition_report_spend)
        round_spend = {coalition.id:0 for coalition in self.scenario.coalitions}
        sight_spend = dict(self.current.coalition_sight_spend)
        sight_round_spend = {coalition.id:0 for coalition in self.scenario.coalitions if coalition.sight_targets}
        sight_events = []
        for coalition in self.scenario.coalitions:
            if not coalition.sight_targets:
                continue
            for observer in coalition.members:
                if not permissions[observer].observe_target_preferences:
                    continue
                for target in coalition.sight_targets:
                    if target == observer:
                        continue
                    if (sight_round_spend[coalition.id] >= coalition.sight_budget_per_round
                            or sight_spend[coalition.id] >= coalition.sight_budget_total):
                        break
                    sight_round_spend[coalition.id] += 1; sight_spend[coalition.id] += 1
                    sighted[observer].append((target,self.current.round + 1,preferences[target]))
                    sight_events.append((coalition.id,observer,target,preferences[target]))
        eavesdrop_spend = dict(self.current.coalition_eavesdrop_spend)
        eavesdrop_round_spend = {coalition.id:0 for coalition in self.scenario.coalitions if coalition.eavesdrop_channels}
        overheard_events = []
        for coalition in self.scenario.coalitions:
            if not coalition.eavesdrop_channels:
                continue
            for observer in coalition.members:
                if not permissions[observer].intercept_private_reports:
                    continue
                for sender,recipient,channel,payload in sorted(self.current.pending):
                    if channel not in coalition.eavesdrop_channels or observer in (sender,recipient):
                        continue
                    if (eavesdrop_round_spend[coalition.id] >= coalition.eavesdrop_budget_per_round
                            or eavesdrop_spend[coalition.id] >= coalition.eavesdrop_budget_total):
                        break
                    eavesdrop_round_spend[coalition.id] += 1; eavesdrop_spend[coalition.id] += 1
                    overheard[observer].append((sender,recipient,channel,self.current.round,
                                               self.current.round-1,self.current.round+1,payload))
                    overheard_events.append((coalition.id,observer,sender,recipient,channel,payload))
        deceptive_reports = []
        delivered = tuple(message for message in self.current.pending if can_receive(message[1], message[2]))
        inbox = defaultdict(list)
        for sender, recipient, channel, ballot in delivered:
            inbox[recipient].append((sender, channel, ballot))
        communication_order = (sorted(self.scenario.people, key=lambda person:person.id)
                               if self.scenario.coalitions else self.scenario.people)
        for person in communication_order:
            sender = person.id
            group = policy(memberships[sender], overrides[sender])
            allowed = {(recipient, "public") for recipient in outgoing[sender]} if group.capabilities.send_public_reports else set()
            if group.capabilities.send_private_reports:
                allowed.update((recipient, channel) for channel in membership_channels[sender] for recipient in channels[channel] if recipient != sender)
            coalition = coalition_by_member.get(sender)
            budget = ((coalition.id, coalition.target,
                       coalition.report_budget_per_round - round_spend[coalition.id],
                       coalition.report_budget_total - total_spend[coalition.id]) if coalition else None)
            if group.communication == "truthful":
                pending.extend((sender, recipient, channel, previous_ballots[sender]) for recipient, channel in sorted(allowed))
                phase_memory.pop((sender, "communication"), None)
            elif group.communication == "target_report" or group.communication.startswith("python:"):
                if group.communication == "target_report":
                    if coalition is None:
                        raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: target_report requires coalition membership")
                    fabricated = (coalition.target,) + tuple(p for p in preferences[sender] if p != coalition.target)[:self.scenario.k-1]
                    remaining = min(budget[2], budget[3])
                    reports = []
                    for recipient, channel in sorted(allowed):
                        use_false = fabricated != previous_ballots[sender] and remaining > 0
                        reports.append({"recipient":recipient,"channel":channel,
                                        "ballot":fabricated if use_false else previous_ballots[sender]})
                        remaining -= int(use_false)
                    phase_memory.pop((sender, "communication"), None)
                else:
                    result = call_phase(sender, group, "communication", observation(sender, positions[sender], inbox[sender], outgoing[sender], membership_channels[sender], voting_sensors, self.current.round + 1, budget, True))
                    reports = result.get("reports")
                    if set(result) != {"reports", "memory"} or not isinstance(reports, list):
                        raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: expected reports list")
                seen = set()
                for report in reports:
                    if not isinstance(report, dict) or set(report) != {"recipient", "channel", "ballot"} or not isinstance(report["recipient"], str) or not isinstance(report["channel"], str) or (report["recipient"], report["channel"]) not in allowed or (report["recipient"], report["channel"]) in seen or not isinstance(report["ballot"], (list, tuple)):
                        raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: unauthorized, duplicate or untruthful report")
                    count_plurality(self.scenario.parties, self.scenario.k, {sender:report["ballot"]})
                    payload = tuple(report["ballot"])
                    if payload != previous_ballots[sender]:
                        if coalition is None:
                            raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: unauthorized, duplicate or untruthful report")
                        if round_spend[coalition.id] >= coalition.report_budget_per_round or total_spend[coalition.id] >= coalition.report_budget_total:
                            raise ElectionError(f"person {sender!r}, round {self.current.round + 1}, communication: coalition report budget exceeded")
                        round_spend[coalition.id] += 1; total_spend[coalition.id] += 1
                        deceptive_reports.append((coalition.id,sender,report["recipient"],report["channel"],payload))
                    seen.add((report["recipient"], report["channel"]))
                    pending.append((sender, report["recipient"], report["channel"], payload))
            else:
                phase_memory.pop((sender, "communication"), None)
        ballots = {}
        memory = dict(self.current.policy_memory)
        active = (sorted(p.id for p in self.scenario.people)[self.current.round % len(self.scenario.people)]
                  if self.scenario.convergence_case else None)
        for p in self.scenario.people:
            group = policy(memberships[p.id], overrides[p.id])
            preference = preferences[p.id]
            messages = inbox[p.id]
            if active is not None:
                old_choice = previous_ballots[p.id][0]
                choice = old_choice
                if p.id == active:
                    if self.scenario.convergence_case == "direct_best_response":
                        choice = direct_best_response(self.scenario.parties, dict(self.current.counts), old_choice, preference)
                    elif self.scenario.convergence_case == "source_local_dominance":
                        params = json.loads(group.parameters).get("voting", {})
                        choice = source_local_dominance(self.scenario.parties, dict(self.current.counts), old_choice,
                                                        preference, params.get("radius", 0), params.get("max_states", 200000))
                    else:
                        choice = certified_conformity(preference, [ballot for _, _, _, ballot in voting_sensors.get(p.id, ())])
                ballots[p.id] = (choice,)
                if p.id == active:
                    memory[p.id] = canonical_json({"policy": self.scenario.convergence_case, "previous": old_choice,
                                                   "choice": choice, "switched": choice != old_choice,
                                                   "information": "current public neighbors" if self.scenario.convergence_case == "certified_conformity" else "current public aggregate"}, "voting decision")
            elif group.voting in EPISTEMIC_POLICIES:
                observed = observation(p.id, positions[p.id], messages, outgoing[p.id], membership_channels[p.id], voting_sensors, self.current.round + 1,
                                       include_signal=group.voting in SIGNAL_EPISTEMIC_POLICIES)
                try:
                    old_policy = policy(prior_groups[p.id], prior_overrides[p.id])
                    previous_memory = json.loads(memory[p.id]) if (old_policy.voting, old_policy.parameters) == (group.voting, group.parameters) else None
                    ballots[p.id], trace = response_from_observation(group.voting, observed,
                                                                    json.loads(group.parameters).get("voting", {}), previous_memory)
                    memory[p.id] = canonical_json(trace, "epistemic voting decision")
                except ElectionError as exc:
                    raise ElectionError(f"person {p.id!r}, round {self.current.round + 1}, voting: {exc}") from exc
            elif group.voting in STRATEGIC:
                old_policy = policy(prior_groups[p.id], prior_overrides[p.id])
                previous_memory = json.loads(memory[p.id]) if (old_policy.voting, old_policy.parameters) == (group.voting, group.parameters) else None
                observed = observation(p.id, positions[p.id], messages, outgoing[p.id], membership_channels[p.id], voting_sensors, self.current.round + 1)
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
            elif group.voting == "sight_plurality" and sighted.get(p.id):
                counts = Counter(ranking[0] for _,_,ranking in sighted[p.id])
                highest = max(counts.values())
                choice = next(party for party in preference if counts[party] == highest)
                ballots[p.id] = (choice,) + tuple(x for x in preference if x != choice)[:self.scenario.k - 1]
                memory[p.id] = "null"
            elif group.voting == "overheard_plurality" and overheard.get(p.id):
                by_sender = defaultdict(set)
                for sender,_,_,_,_,_,payload in overheard[p.id]: by_sender[sender].add(payload[0])
                counts = Counter(next(iter(choices)) for choices in by_sender.values() if len(choices) == 1)
                if counts:
                    highest = max(counts.values())
                    choice = next(party for party in preference if counts[party] == highest)
                    ballots[p.id] = (choice,) + tuple(x for x in preference if x != choice)[:self.scenario.k - 1]
                else:
                    ballots[p.id] = preference[:self.scenario.k]
                memory[p.id] = "null"
            elif group.voting == "coalition_fusion":
                known = {target:ranking[0] for target,_,ranking in sighted.get(p.id,())}
                reports_by_sender = defaultdict(set)
                for sender,_,_,_,_,_,payload in overheard.get(p.id,()):
                    if sender not in known: reports_by_sender[sender].add(payload[0])
                reports = {sender:next(iter(choices)) for sender,choices in reports_by_sender.items() if len(choices) == 1}
                conflicts = sorted(sender for sender,choices in reports_by_sender.items() if len(choices) > 1)
                counts = Counter((*known.values(),*reports.values()))
                highest = max(counts.values(),default=0)
                choice = next((party for party in preference if counts[party] == highest), preference[0]) if counts else preference[0]
                ballots[p.id] = (choice,) + tuple(party for party in preference if party != choice)[:self.scenario.k-1]
                memory[p.id] = canonical_json({"policy":"coalition_fusion", "sighted_first_choices":known,
                                               "overheard_first_choices":reports,"conflicting_senders":conflicts,
                                               "choice":choice}, "coalition fusion decision")
            elif group.voting == "signal_confident":
                signal = (latest_signal[0],latest_signal[1],latest_signal[2]) if latest_signal is not None else None
                ballots[p.id], trace = trusting_response(self.scenario.parties,preference,previous_ballots[p.id],signal)
                trace.update(policy="signal_confident", stale=signal is not None and signal[0] != self.current.round)
                memory[p.id] = canonical_json(trace,"signal voting decision")
            elif group.voting.startswith("python:"):
                function, _, _ = self.plugins[group.voting]
                try:
                    observed = observation(p.id, positions[p.id], messages, outgoing[p.id], membership_channels[p.id], voting_sensors, self.current.round + 1, include_sight=True)
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
        detector = (update_detector(self.scenario.detector, self.scenario.parties, dict(counts), self.current.round + 1,
                                    self.current.detector, dict(self.current.counts)) if self.scenario.detector else None)
        result = Frame(self.current.round + 1, tuple((p, tuple(ballot)) for p, ballot in ballots.items()), counts, winner, tuple(positions.items()),
                       tuple(sorted(persistent)), proximity, delivered,
                       tuple(sorted(pending)), tuple(preferences.items()), tuple(memberships.items()), actions,
                       tuple(memory.items()), tuple(overrides.items()),
                       tuple((name, tuple(sorted(members))) for name, members in sorted(channels.items())),
                       tuple((person, phase, data) for (person, phase), data in sorted(phase_memory.items())),
                       tuple((observer, sender, source, timestamp, ballot)
                             for observer, observations in sorted(voting_sensors.items())
                             for sender, source, timestamp, ballot in observations), tuple(sorted(campaign)),
                       tuple(sorted(total_spend.items())),tuple(deceptive_reports),
                       tuple(sorted(sight_spend.items())),tuple(sight_events),
                       tuple(sorted(eavesdrop_spend.items())),tuple(overheard_events),
                       tuple(sorted(purchased)) if controller is not None else None, controller_added, controller_eligible,
                       signal_spend=signal_spend,signal_latest=latest_signal,signal_broadcast_cost=signal_broadcast_cost,
                       alignment_ideals=tuple(alignment_ideals.items()) if alignment_ideals is not None else None,
                       alignment_spend=alignment_spend, alignment_changes=alignment_changes, detector=detector,
                       leader_true=tuple(leader_true.items()) if leader_true is not None else None,
                       leader_perceived=tuple(leader_perceived.items()) if leader_perceived is not None else None,
                       leader_spend=tuple(leader_spend.items()) if leader_spend is not None else None,
                       leader_memory=tuple((p, *leader_memory[p]) for p in self.scenario.parties) if leader_memory is not None else (),
                       leader_signals=tuple(leader_signals.items()) if leader_signals is not None else None)
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
        return {"version": 21, "manifest": self.runtime_manifest, "scenario": self.scenario.as_dict(),
                **({"nomination": self.scenario.nomination.as_dict()} if self.scenario.nomination else {}),
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
        if self.scenario.convergence_case:
            raise ElectionError("certified convergence episodes exclude interactive interventions; start an unrestricted scenario to edit")
        if (self.scenario.alignment is not None or self.scenario.leaders is not None) and "preference" in changes:
            raise ElectionError("spatial dynamic scenarios derive preferences; ordinal preference interventions are unsupported")
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
        if not isinstance(payload, Mapping) or type(payload.get("version")) is not int or payload["version"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21):
            raise ElectionError("unsupported or invalid checkpoint")
        expected = {"version", "scenario", "frames"} | ({"manual_interventions"} if payload["version"] >= 2 else set()) | ({"policy_digests"} if payload["version"] >= 3 else set()) | ({"manifest"} if payload["version"] >= 6 else set())
        if isinstance(payload.get("scenario"), Mapping) and "nomination" in payload["scenario"] and (payload["version"] >= 18 or "nomination" in payload):
            expected.add("nomination")
        if set(payload) != expected:
            raise ElectionError("invalid checkpoint fields")
        if payload["version"] >= 6 and payload["manifest"] != manifest() and not allow_environment_change:
            raise ElectionError("checkpoint runtime or core source changed; explicitly allow migration after review")
        frames = payload["frames"]
        if not isinstance(frames, list) or not frames:
            raise ElectionError("checkpoint must contain an initial frame")
        simulation = cls(make_scenario(payload["scenario"]))
        if payload["version"] < 21 and simulation.scenario.leaders is not None:
            raise ElectionError("leader adaptation requires checkpoint version 21")
        if payload["version"] < 20 and simulation.scenario.detector is not None:
            raise ElectionError("detectors require checkpoint version 20")
        if payload["version"] < 19 and simulation.scenario.alignment is not None:
            raise ElectionError("alignment scenarios require checkpoint version 19")
        if payload["version"] < 18 and simulation.scenario.nomination is not None:
            raise ElectionError("nomination scenarios require checkpoint version 18")
        if simulation.scenario.nomination is not None and payload["nomination"] != simulation.scenario.nomination.as_dict():
            raise ElectionError("checkpoint nomination record does not match the scenario")
        if payload["version"] < 12 and simulation.scenario.coalitions:
            raise ElectionError("coalitions require checkpoint version 12")
        if payload["version"] < 13 and any(c.sight_targets for c in simulation.scenario.coalitions):
            raise ElectionError("preference sight requires checkpoint version 13")
        if payload["version"] < 14 and any(c.eavesdrop_channels for c in simulation.scenario.coalitions):
            raise ElectionError("private-report interception requires checkpoint version 14")
        if payload["version"] < 15 and simulation.scenario.campaign_controller is not None:
            raise ElectionError("campaign controllers require checkpoint version 15")
        if payload["version"] < 16 and simulation.scenario.signal_controller is not None:
            raise ElectionError("public-signal controllers require checkpoint version 16")
        if simulation.scenario.convergence_case and payload.get("manual_interventions"):
            raise ElectionError("certified checkpoints cannot contain interactive interventions")
        raw = simulation.scenario.as_dict()
        raw["interventions"] = payload.get("manual_interventions", [])
        simulation.manual_interventions = make_scenario(raw).interventions
        if payload["version"] < 17:
            references = {group.voting for group in simulation.scenario.groups}
            overrides = ([person.overrides for person in simulation.scenario.people] +
                         [action.overrides for action in (*simulation.scenario.interventions, *simulation.manual_interventions)
                          if action.overrides is not None])
            references.update(json.loads(value).get("voting") for value in overrides)
            if references.intersection(SIGNAL_EPISTEMIC_POLICIES):
                raise ElectionError("signal epistemic policies require checkpoint version 17")
        simulation.plugins = simulation._load_plugins(simulation.manual_interventions)
        if payload["version"] < 3 and simulation.plugins:
            raise ElectionError("legacy checkpoints cannot validate plugin sources")
        if payload["version"] >= 3 and payload["policy_digests"] != simulation.checkpoint()["policy_digests"]:
            raise ElectionError("checkpoint plugin source digest changed")
        if any(a.round > len(frames) for a in simulation.manual_interventions):
            raise ElectionError("manual intervention is beyond the next boundary")
        simulation.run(len(frames) - 1)
        expected_frames = simulation.checkpoint()["frames"]
        if payload["version"] < 11:
            groups = {group.id: group for group in simulation.scenario.groups}
            for frame in expected_frames:
                for actor, memory in frame["policy_memory"].items():
                    effective = apply_overrides(groups[frame["groups"][actor]], canonical_json(frame["overrides"][actor], "overrides"))
                    if effective.voting in EPISTEMIC_POLICIES and isinstance(memory, dict):
                        for event in memory.get("observation_history", []):
                            for report in event.get("received_reports", []):
                                report.pop("generated_round", None)
                                report.pop("delivered_round", None)
                                report["source_round"] = None
                frame.pop("report_provenance")
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
