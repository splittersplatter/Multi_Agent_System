"""Validated immutable inputs and committed election frames."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping, TYPE_CHECKING
import math
import json

if TYPE_CHECKING:
    from .majority import MajorityConfig, MajorityState


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
    ideal: tuple[float, ...] | None = None
    grid_position: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Policy-facing permissions; legacy scenarios retain their existing behavior."""
    observe_public_neighbors: bool = True
    observe_private_channels: bool = True
    observe_electorate: bool = False
    sense_public_ballots: bool = False
    sense_private_ballots: bool = False
    observe_target_preferences: bool = False
    intercept_private_reports: bool = False
    observe_public_signal: bool = False
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
    proximity_radius: float | None = None


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
class Coalition:
    id: str
    members: tuple[str, ...]
    target: str
    report_budget_per_round: int
    report_budget_total: int
    sight_targets: tuple[str, ...] = ()
    sight_budget_per_round: int = 0
    sight_budget_total: int = 0
    eavesdrop_channels: tuple[str, ...] = ()
    eavesdrop_budget_per_round: int = 0
    eavesdrop_budget_total: int = 0


@dataclass(frozen=True, slots=True)
class CampaignController:
    target: str
    policy: str
    lifetime_budget: int
    per_round_budget: int
    max_candidates: int = 100000


@dataclass(frozen=True, slots=True)
class SignalController:
    target: str
    policy: str
    schedule: str
    per_broadcast_budget: int
    lifetime_budget: int


@dataclass(frozen=True, slots=True)
class Nomination:
    mode: str
    m: int
    eligible: tuple[str, ...]
    nominees: tuple[str, ...]
    votes: tuple[tuple[str, str | None], ...]
    counts: tuple[tuple[str, int], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "m": self.m, "eligible": list(self.eligible),
                "nominees": list(self.nominees), "votes": dict(self.votes), "counts": dict(self.counts)}


@dataclass(frozen=True, slots=True)
class AlignmentAttack:
    target: str
    policy: str
    targets: tuple[str, ...]
    per_person_round: float
    total_budget: float
    observe_target_ideals: bool


@dataclass(frozen=True, slots=True)
class Alignment:
    drift_max_step: float
    attack: AlignmentAttack


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    target: str
    threshold: float


@dataclass(frozen=True, slots=True)
class DetectorState:
    share_change: float | None
    alert: bool
    first_alert_round: int | None
    target_win_streak: int
    first_triple_win_round: int | None


@dataclass(frozen=True, slots=True)
class LeaderConfig:
    policy: str
    adaptors: tuple[str, ...]
    per_round_step: float
    lifetime_budget: float
    signal_mode: str
    signal_noise: float
    perception_weight: float


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
    convergence_case: str | None = None
    proximity_mode: str = "dynamic"
    static_proximity_edges: tuple[tuple[str, str], ...] = ()
    coalitions: tuple[Coalition, ...] = ()
    campaign_controller: CampaignController | None = None
    signal_controller: SignalController | None = None
    nomination: Nomination | None = None
    alignment: Alignment | None = None
    detector: DetectorConfig | None = None
    leaders: LeaderConfig | None = None
    majority_estimation: "MajorityConfig | None" = None
    stochastic_case: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "parties": list(self.parties), "k": self.k, "seed": self.seed, "rounds": self.rounds,
            "groups": {g.id: {"voting": g.voting, "movement": g.movement, "max_step": g.max_step,
                               "communication": g.communication, "graph": g.graph,
                               "parameters": json.loads(g.parameters),
                               "capabilities": asdict(g.capabilities),
                               **({"proximity_radius": g.proximity_radius} if g.proximity_radius is not None else {})} for g in self.groups},
            "people": [{"id": p.id, "group": p.group, "preference": list(p.preference),
                        **({"grid_position": list(p.grid_position)} if p.grid_position is not None else {"position": list(p.position)}),
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
        if self.proximity_mode != "dynamic":
            result["network"]["proximity_mode"] = self.proximity_mode
        if self.proximity_mode == "static":
            result["network"]["static_proximity_edges"] = [list(edge) for edge in self.static_proximity_edges]
        if self.convergence_case is not None:
            result["convergence"] = {"case": self.convergence_case}
        if self.coalitions:
            result["coalitions"] = [{"id": c.id, "members": list(c.members), "target": c.target,
                                     "report_budget_per_round": c.report_budget_per_round,
                                     "report_budget_total": c.report_budget_total,
                                     **({"sight_targets":list(c.sight_targets), "sight_budget_per_round":c.sight_budget_per_round,
                                         "sight_budget_total":c.sight_budget_total} if c.sight_targets else {}),
                                     **({"eavesdrop_channels":list(c.eavesdrop_channels),
                                         "eavesdrop_budget_per_round":c.eavesdrop_budget_per_round,
                                         "eavesdrop_budget_total":c.eavesdrop_budget_total} if c.eavesdrop_channels else {})} for c in self.coalitions]
        if self.campaign_controller is not None:
            result["campaign_controller"] = asdict(self.campaign_controller)
        if self.signal_controller is not None:
            result["signal_controller"] = asdict(self.signal_controller)
        if self.nomination is not None:
            result.pop("parties")
            result["nomination"] = {"mode": self.nomination.mode, "m": self.nomination.m,
                                    "eligible": list(self.nomination.eligible),
                                    **({"nominees": list(self.nomination.nominees)} if self.nomination.mode == "fixed" else {})}
            for person, serialized in zip(self.people, result["people"]):
                serialized.pop("preference")
                serialized["ideal"] = list(person.ideal)
        if self.alignment is not None:
            result["alignment"] = asdict(self.alignment)
            result["alignment"]["attack"]["targets"] = list(self.alignment.attack.targets)
        if self.detector is not None:
            result["detector"] = asdict(self.detector)
        if self.leaders is not None:
            result["leaders"] = asdict(self.leaders)
            result["leaders"]["adaptors"] = list(self.leaders.adaptors)
        if self.majority_estimation is not None:
            result["majority_estimation"] = self.majority_estimation.as_dict()
        if self.stochastic_case is not None:
            result["stochastic_stability"] = {"case": self.stochastic_case}
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
    coalition_report_spend: tuple[tuple[str, int], ...] = ()
    deceptive_reports: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = ()
    coalition_sight_spend: tuple[tuple[str, int], ...] = ()
    preference_sight: tuple[tuple[str, str, str, tuple[str, ...]], ...] = ()
    coalition_eavesdrop_spend: tuple[tuple[str, int], ...] = ()
    overheard_reports: tuple[tuple[str, str, str, str, str, tuple[str, ...]], ...] = ()
    campaign_controller_purchased: tuple[tuple[str, str], ...] | None = None
    campaign_controller_added: tuple[tuple[str, str], ...] = ()
    campaign_controller_eligible: tuple[tuple[str, str], ...] | None = None
    signal_spend: int | None = None
    # (source round, broadcast round, reported counts, true source counts)
    signal_latest: tuple[int, int, tuple[int, ...], tuple[int, ...]] | None = None
    signal_broadcast_cost: int | None = None
    alignment_ideals: tuple[tuple[str, tuple[float, ...]], ...] | None = None
    alignment_spend: float | None = None
    # (person, prior ideal, after drift, after attack, attack cost)
    alignment_changes: tuple[tuple[str, tuple[float, ...], tuple[float, ...], tuple[float, ...], float], ...] = ()
    detector: DetectorState | None = None
    leader_true: tuple[tuple[str, tuple[float, ...]], ...] | None = None
    leader_perceived: tuple[tuple[str, tuple[float, ...]], ...] | None = None
    leader_spend: tuple[tuple[str, float], ...] | None = None
    # (leader, last direction index, public support before that action)
    leader_memory: tuple[tuple[str, int | None, int | None], ...] = ()
    leader_signals: tuple[tuple[str, tuple[float, ...]], ...] | None = None
    majority_states: tuple[tuple[str, "MajorityState"], ...] = ()
    majority_config: "MajorityConfig | None" = None
    majority_parties: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result = {"round": self.round, "ballots": {p: list(b) for p, b in self.ballots},
                "counts": dict(self.counts), "winner": self.winner,
                "positions": {p: list(pos) for p, pos in self.positions},
                "persistent_edges": [list(edge) for edge in self.persistent_edges],
                "proximity_edges": [list(edge) for edge in self.proximity_edges],
                "campaign_edges": [list(edge) for edge in self.campaign_edges],
                "delivered": [[a, b, channel, list(ballot)] for a, b, channel, ballot in self.delivered],
                "pending": [[a, b, channel, list(ballot)] for a, b, channel, ballot in self.pending],
                "report_provenance": {
                    "delivered": [{"sender": a, "recipient": b, "channel": channel, "ballot": list(ballot),
                                   "source_round": self.round - 2, "generated_round": self.round - 1,
                                   "delivered_round": self.round} for a, b, channel, ballot in self.delivered],
                    "pending": [{"sender": a, "recipient": b, "channel": channel, "ballot": list(ballot),
                                 "source_round": self.round - 1, "generated_round": self.round,
                                 "delivered_round": None} for a, b, channel, ballot in self.pending]},
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
        if self.majority_config is not None:
            result["majority_estimation"] = {p: state.as_dict(self.majority_parties, self.majority_config)
                                              for p, state in self.majority_states}
        if self.coalition_report_spend:
            result["coalition_report_spend"] = dict(self.coalition_report_spend)
            result["deceptive_reports"] = [{"coalition": coalition, "sender": sender, "recipient": recipient,
                                             "channel": channel, "ballot": list(ballot)}
                                            for coalition,sender,recipient,channel,ballot in self.deceptive_reports]
        if self.coalition_sight_spend:
            result["coalition_sight_spend"] = dict(self.coalition_sight_spend)
            result["preference_sight"] = [{"coalition":coalition,"observer":observer,"target":target,
                                           "round":self.round,"preference":list(preference)}
                                          for coalition,observer,target,preference in self.preference_sight]
        if self.coalition_eavesdrop_spend:
            result["coalition_eavesdrop_spend"] = dict(self.coalition_eavesdrop_spend)
            result["overheard_reports"] = [{"coalition":coalition,"observer":observer,"sender":sender,
                                             "recipient":recipient,"channel":channel,"ballot":list(ballot),
                                             "reference_round":self.round-2,"generated_round":self.round-1,
                                             "intercepted_round":self.round}
                                            for coalition,observer,sender,recipient,channel,ballot in self.overheard_reports]
        if self.campaign_controller_purchased is not None:
            result["campaign_controller"] = {"spent":len(self.campaign_controller_purchased),
                "purchased":[list(edge) for edge in self.campaign_controller_purchased],
                "eligible":None if self.campaign_controller_eligible is None else [list(edge) for edge in self.campaign_controller_eligible],
                "proposed":[list(edge) for edge in self.campaign_controller_added],
                "accepted":[list(edge) for edge in self.campaign_controller_added]}
        if self.signal_spend is not None:
            latest = self.signal_latest
            result["public_signal"] = {"spend":self.signal_spend, "broadcast_cost":self.signal_broadcast_cost,
                "latest":None if latest is None else {"source_round":latest[0],"broadcast_round":latest[1],
                                                        "report":list(latest[2]),"source_truth":list(latest[3])}}
        if self.alignment_ideals is not None:
            result["alignment"] = {"ideals": {p: list(v) for p, v in self.alignment_ideals},
                                   "attack_spend": self.alignment_spend,
                                   "changes": [{"person": p, "before": list(before), "after_drift": list(drift),
                                                "after_attack": list(after), "attack_cost": cost}
                                               for p, before, drift, after, cost in self.alignment_changes]}
        if self.detector is not None:
            result["detector"] = asdict(self.detector)
        if self.leader_true is not None:
            result["leaders"] = {"true": {p: list(v) for p, v in self.leader_true},
                                 "perceived": {p: list(v) for p, v in self.leader_perceived},
                                 "spend": dict(self.leader_spend),
                                 "memory": {p: {"last_direction": d, "support_before": s} for p, d, s in self.leader_memory},
                                 "signals": None if self.leader_signals is None else {p: list(v) for p, v in self.leader_signals}}
        return result


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ElectionError(f"{label} must be finite and in [{minimum}, {maximum}]")
    return float(value)


def _make_group(group: str, policy: Mapping[str, Any]) -> Group:
    from .voting import VOTING_POLICIES, COALITION_POLICIES, SIGNAL_POLICIES, CERTIFIED_POLICIES, STRATEGIC, validate_parameters
    from .epistemic import EPISTEMIC_POLICIES, validate_epistemic_parameters
    _id(group, "group")
    if not isinstance(policy, dict) or set(policy) - {"voting", "movement", "max_step", "proximity_radius", "communication", "graph", "parameters", "capabilities"} or not isinstance(policy.get("voting"), str) or not (policy["voting"] in VOTING_POLICIES + COALITION_POLICIES + SIGNAL_POLICIES + CERTIFIED_POLICIES + EPISTEMIC_POLICIES or policy["voting"].startswith("python:")):
        raise ElectionError(f"group {group!r}: expected supported voting and movement")
    movement = policy.get("movement", "stationary")
    if not isinstance(movement, str) or not (movement in ("stationary", "random_walk", "grid_walk") or movement.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported movement {movement!r}")
    max_step = _number(policy.get("max_step", 0), "max_step", 0, 1)
    proximity_radius = _number(policy["proximity_radius"], "proximity_radius", 0, math.sqrt(2)) if "proximity_radius" in policy else None
    communication = policy.get("communication", "none")
    if not isinstance(communication, str) or not (communication in ("none", "truthful", "target_report") or communication.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported communication {communication!r}")
    graph = policy.get("graph", "none")
    if not isinstance(graph, str) or not (graph == "none" or graph.startswith("python:")):
        raise ElectionError(f"group {group!r}: unsupported graph policy {graph!r}")
    params = policy.get("parameters", {})
    if not isinstance(params, dict):
        raise ElectionError(f"group {group!r}: parameters must be a table")
    if movement == "random_walk":
        from .network import validate_walk_parameters
        validate_walk_parameters(params.get("movement", {}), max_step)
    if movement == "grid_walk" and (max_step != .025 or params.get("movement", {}) != {}):
        raise ElectionError("grid_walk requires max_step=.025 and no movement parameters")
    if policy["voting"] in STRATEGIC:
        validate_parameters(params.get("voting", {}))
    if policy["voting"] in EPISTEMIC_POLICIES:
        validate_epistemic_parameters(params.get("voting", {}), policy["voting"])
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
    return Group(group, policy["voting"], movement, max_step, communication, graph, encoded, capabilities, proximity_radius)


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
                                 **({"proximity_radius": group.proximity_radius} if group.proximity_radius is not None else {}),
                                 **changes, "capabilities": capabilities})


def make_scenario(raw: Mapping[str, Any]) -> Scenario:
    """Validate and normalize a TOML/JSON-compatible explicit electorate."""
    if not isinstance(raw, Mapping):
        raise ElectionError("scenario must be a table")
    if "nomination" in raw:
        from .nomination import make_nominated_scenario
        return make_nominated_scenario(raw)
    allowed = {"parties", "k", "seed", "rounds", "groups", "people", "network", "interventions", "convergence", "coalitions", "campaign_controller", "signal_controller", "detector", "majority_estimation", "stochastic_stability"}
    unknown = set(raw) - allowed
    if unknown:
        raise ElectionError(f"unknown scenario keys: {sorted(unknown)}")
    stochastic = raw.get("stochastic_stability")
    if "stochastic_stability" in raw:
        from .grid import CASE
        if not isinstance(stochastic, dict) or set(stochastic) != {"case"} or stochastic["case"] != CASE:
            raise ElectionError("stochastic_stability requires case=finite_grid_occupation_v1")
    party_data = raw.get("parties")
    if not isinstance(party_data, list) or not party_data:
        raise ElectionError("parties must be a non-empty list")
    parties = tuple(_id(x, "party") for x in party_data)
    if len(set(parties)) != len(parties):
        raise ElectionError("parties must be unique")
    from .majority import parse_config
    majority = parse_config(raw["majority_estimation"], parties) if "majority_estimation" in raw else None
    detector_raw = raw.get("detector")
    detector = None
    if "detector" in raw:
        if not isinstance(detector_raw, dict) or set(detector_raw) != {"target", "threshold"}:
            raise ElectionError("detector requires target and threshold")
        if not isinstance(detector_raw["target"], str) or detector_raw["target"] not in parties:
            raise ElectionError("detector target must be a known party")
        detector = DetectorConfig(detector_raw["target"], _number(detector_raw["threshold"], "detector threshold", 0, 1))
    controller_raw = raw.get("campaign_controller")
    controller = None
    if "campaign_controller" in raw:
        required = {"target", "policy", "lifetime_budget", "per_round_budget"}
        if not isinstance(controller_raw,dict) or not required <= set(controller_raw) or set(controller_raw) - required - {"max_candidates"}:
            raise ElectionError("campaign_controller requires target, policy and budgets")
        if not isinstance(controller_raw["target"],str) or controller_raw["target"] not in parties:
            raise ElectionError("campaign controller target must be a known party")
        if controller_raw["policy"] not in ("none","random","target_heuristic"):
            raise ElectionError("campaign controller policy must be none, random or target_heuristic")
        lifetime = _int(controller_raw["lifetime_budget"], "campaign lifetime_budget", 0)
        per_round = _int(controller_raw["per_round_budget"], "campaign per_round_budget", 0)
        maximum = _int(controller_raw.get("max_candidates",100000), "campaign max_candidates", 1)
        if maximum > 1000000:
            raise ElectionError("campaign max_candidates cannot exceed 1000000")
        controller = CampaignController(controller_raw["target"],controller_raw["policy"],lifetime,per_round,maximum)
    signal_raw = raw.get("signal_controller")
    signal_controller = None
    if "signal_controller" in raw:
        required = {"target","policy","schedule","per_broadcast_budget","lifetime_budget"}
        if not isinstance(signal_raw,dict) or set(signal_raw) != required:
            raise ElectionError("signal_controller requires target, policy, schedule and budgets")
        if not isinstance(signal_raw["target"],str) or signal_raw["target"] not in parties:
            raise ElectionError("signal controller target must be a known party")
        if signal_raw["policy"] not in ("truthful","bounded_random","target_biased"):
            raise ElectionError("signal controller policy must be truthful, bounded_random or target_biased")
        if signal_raw["schedule"] not in ("initial","repeated"):
            raise ElectionError("signal controller schedule must be initial or repeated")
        signal_controller = SignalController(signal_raw["target"],signal_raw["policy"],signal_raw["schedule"],
                _int(signal_raw["per_broadcast_budget"],"signal per_broadcast_budget",0),
                _int(signal_raw["lifetime_budget"],"signal lifetime_budget",0))
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
        if not isinstance(item, dict) or not {"id", "group", "preference"} <= set(item) or set(item) - {"id", "group", "preference", "position", "grid_position", "overrides"}:
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
        grid_position = None
        if "grid_position" in item:
            from .grid import physical
            if "position" in item:
                raise ElectionError("choose grid_position or position, not both")
            coords = physical(item["grid_position"])
            grid_position = tuple(item["grid_position"])
        position = item.get("position", [0.5, 0.5])
        if not isinstance(position, list) or len(position) != 2:
            raise ElectionError(f"person {person_id!r}: position must have two coordinates")
        if grid_position is None:
            coords = tuple(_number(value, "coordinate", 0, 1) for value in position)
        overrides = _overrides(item.get("overrides", {}))
        apply_overrides(groups_by_id[group], overrides)
        people.append(Person(person_id, group, tuple(pref), coords, overrides, grid_position=grid_position))
    if len({person.id for person in people}) != len(people):
        raise ElectionError("person ids must be unique")
    network = raw.get("network", {})
    if not isinstance(network, dict) or set(network) - {"radius", "proximity_mode", "static_proximity_edges", "persistent_edges", "campaign_edges", "private_channels"}:
        raise ElectionError("network must contain only supported network options")
    radius = _number(network["radius"], "radius", 0, math.sqrt(2)) if "radius" in network else None
    proximity_mode = network.get("proximity_mode", "dynamic")
    if not isinstance(proximity_mode, str) or proximity_mode not in ("dynamic", "frozen", "static"):
        raise ElectionError("proximity_mode must be dynamic, frozen or static")
    if ("static_proximity_edges" in network) != (proximity_mode == "static"):
        raise ElectionError("static mode requires static_proximity_edges; other modes forbid it")
    ids = {person.id for person in people}
    coalition_data = raw.get("coalitions", [])
    if not isinstance(coalition_data, list):
        raise ElectionError("coalitions must be a list")
    coalitions = []; coalition_ids = set(); assigned = set()
    for item in coalition_data:
        required = {"id", "members", "target", "report_budget_per_round", "report_budget_total"}
        sight_fields = {"sight_targets", "sight_budget_per_round", "sight_budget_total"}
        eavesdrop_fields = {"eavesdrop_channels", "eavesdrop_budget_per_round", "eavesdrop_budget_total"}
        if (not isinstance(item, dict) or not required <= set(item) or set(item) - required - sight_fields - eavesdrop_fields
                or (set(item) & sight_fields and not sight_fields <= set(item))
                or (set(item) & eavesdrop_fields and not eavesdrop_fields <= set(item))):
            raise ElectionError("coalition requires id, members, target and report budgets")
        identity = _id(item["id"], "coalition id")
        members = item["members"]
        if (identity in coalition_ids or not isinstance(members, list) or not members
                or any(not isinstance(member,str) or member not in ids for member in members)
                or len(set(members)) != len(members) or assigned.intersection(members)):
            raise ElectionError("coalition IDs and member assignments must be unique and members must be known")
        if not isinstance(item["target"],str) or item["target"] not in parties:
            raise ElectionError("coalition target must be a known party")
        per_round = _int(item["report_budget_per_round"], "report_budget_per_round", 0)
        total = _int(item["report_budget_total"], "report_budget_total", 0)
        targets = item.get("sight_targets", [])
        if (not isinstance(targets,list) or ("sight_targets" in item and not targets)
                or any(not isinstance(target,str) or target not in ids for target in targets)
                or len(set(targets)) != len(targets)):
            raise ElectionError("sight_targets must be nonempty unique known people when configured")
        sight_round = _int(item.get("sight_budget_per_round",0), "sight_budget_per_round", 0)
        sight_total = _int(item.get("sight_budget_total",0), "sight_budget_total", 0)
        listened = item.get("eavesdrop_channels", [])
        if (not isinstance(listened,list) or ("eavesdrop_channels" in item and not listened)
                or any(not isinstance(channel,str) or not channel or channel == "public" for channel in listened)
                or len(set(listened)) != len(listened)):
            raise ElectionError("eavesdrop_channels must be nonempty unique private channel names when configured")
        eavesdrop_round = _int(item.get("eavesdrop_budget_per_round",0), "eavesdrop_budget_per_round", 0)
        eavesdrop_total = _int(item.get("eavesdrop_budget_total",0), "eavesdrop_budget_total", 0)
        coalitions.append(Coalition(identity, tuple(sorted(members)), item["target"], per_round, total,
                                    tuple(sorted(targets)), sight_round, sight_total,
                                    tuple(sorted(listened)), eavesdrop_round, eavesdrop_total))
        coalition_ids.add(identity); assigned.update(members)
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
    normalized_static = edges_for_layer("static_proximity_edges")
    channels = network.get("private_channels", {})
    if not isinstance(channels, dict):
        raise ElectionError("private_channels must be a table")
    normalized_channels = []
    for channel, members in channels.items():
        _id(channel, "channel")
        if channel == "public" or not isinstance(members, list) or any(not isinstance(x, str) or x not in ids for x in members) or len(set(members)) != len(members):
            raise ElectionError(f"channel {channel!r}: members must be unique known people; name public is reserved")
        normalized_channels.append((channel, tuple(sorted(members))))
    if any(not set(coalition.eavesdrop_channels) <= set(channels) for coalition in coalitions):
        raise ElectionError("eavesdrop_channels must name configured private channels")
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
    convergence = raw.get("convergence")
    if "convergence" in raw and convergence is None:
        raise ElectionError("convergence must be a table")
    if convergence is not None and (not isinstance(convergence, dict) or set(convergence) != {"case"}
                                    or convergence["case"] not in ("direct_best_response", "source_local_dominance", "certified_conformity")):
        raise ElectionError("convergence requires a supported case")
    effective_groups = [apply_overrides(groups_by_id[p.group], p.overrides) for p in people]
    if any(group.voting == "memory_pivotal" for group in effective_groups):
        if majority is None or k != 1:
            raise ElectionError("memory_pivotal requires enabled majority_estimation and k=1")
        if any(json.loads(group.parameters).get("voting", {}) != {} for group in effective_groups if group.voting == "memory_pivotal"):
            raise ElectionError("memory_pivotal takes no voting parameters; configure majority_estimation instead")
    from .epistemic import validate_signal_epistemic_group
    for group in effective_groups:
        validate_signal_epistemic_group(group, signal_controller, len(people), len(parties))
    if any(group.voting == "signal_confident" and (signal_controller is None or not group.capabilities.observe_public_signal)
           for group in effective_groups):
        raise ElectionError("signal_confident requires a signal controller and public-signal permission")
    sight_coalition = {member:coalition for coalition in coalitions for member in coalition.members}
    if any((group.capabilities.observe_target_preferences or group.voting in ("sight_plurality", "coalition_fusion"))
           and (person.id not in sight_coalition or not group.capabilities.observe_target_preferences
                or not sight_coalition[person.id].sight_targets)
           for person, group in zip(people,effective_groups)):
        raise ElectionError("preference sight requires coalition membership, sight targets and sight permission")
    if any((group.capabilities.intercept_private_reports or group.voting in ("overheard_plurality", "coalition_fusion"))
           and (person.id not in sight_coalition or not group.capabilities.intercept_private_reports
                or not sight_coalition[person.id].eavesdrop_channels)
           for person,group in zip(people,effective_groups)):
        raise ElectionError("eavesdropping requires coalition membership, private channels and interception permission")
    if convergence is None:
        if any(g.voting in ("direct_best_response", "source_local_dominance", "certified_conformity") for g in effective_groups):
            raise ElectionError("certified voting requires a convergence case")
    else:
        case = convergence["case"]
        if controller is not None:
            raise ElectionError("certified convergence excludes campaign controllers")
        if signal_controller is not None:
            raise ElectionError("certified convergence excludes public-signal controllers")
        if coalitions:
            raise ElectionError("certified convergence excludes coalition capabilities")
        if k != 1:
            raise ElectionError("certified convergence requires k=1")
        if normalized_interventions:
            if case not in ("direct_best_response", "certified_conformity"):
                raise ElectionError("this certified convergence case excludes scheduled interventions")
            if any(a.group is not None or a.position is not None or a.overrides is not None or
                   a.add_edges or a.remove_edges or a.add_channels or a.remove_channels or
                   a.add_campaign_edges or a.remove_campaign_edges for a in normalized_interventions):
                raise ElectionError("certified interventions permit only ballot or preference changes")
        if any(g.voting != case or g.movement != "stationary"
               or g.graph != "none" or g.communication != "none" for g in effective_groups):
            raise ElectionError("certified convergence requires homogeneous voters, stationary movement, no graph actions or messages")
        parameters = [json.loads(g.parameters).get("voting", {}) for g in effective_groups]
        if case == "direct_best_response" and any(not isinstance(p, dict) or p for p in parameters):
            raise ElectionError("direct_best_response takes no voting parameters")
        if case == "certified_conformity":
            from .network import proximity_edges
            radii = {person.id: group.proximity_radius if group.proximity_radius is not None else radius
                     for person, group in zip(people, effective_groups)}
            proximity = normalized_static if proximity_mode == "static" else proximity_edges({p.id: p.position for p in people}, radius, radii)
            edges = set(normalized_edges) | set(normalized_campaign) | set(proximity)
            if any((target, source) not in edges for source, target in edges):
                raise ElectionError("certified_conformity requires an undirected public graph")
            if any(not g.capabilities.sense_public_ballots or g.capabilities.sense_private_ballots for g in effective_groups):
                raise ElectionError("certified_conformity requires public ballot sensing only")
            if any(not isinstance(p, dict) or p for p in parameters):
                raise ElectionError("certified_conformity takes no voting parameters")
        if case == "source_local_dominance":
            if len(parties) > 32:
                raise ElectionError("source_local_dominance supports at most 32 parties")
            if any(not isinstance(p, dict) or set(p) - {"radius", "max_states"}
                   or type(p.get("radius", 0)) is not int or not 0 <= p.get("radius", 0) <= 20
                   or type(p.get("max_states", 200000)) is not int or not 1 <= p.get("max_states", 200000) <= 1000000
                   for p in parameters):
                raise ElectionError("source_local_dominance requires integer radius 0..20 and max_states 1..1000000")
            if len({p.get("radius", 0) for p in parameters}) != 1:
                raise ElectionError("source_local_dominance requires a common radius")
    result = Scenario(parties, k, tuple(people), seed, rounds, tuple(normalized_groups), radius,
                    normalized_edges, tuple(sorted(normalized_channels)),
                    tuple(sorted(normalized_interventions, key=lambda action: (action.round, action.person))), normalized_campaign,
                    convergence["case"] if convergence else None, proximity_mode, normalized_static,
                    tuple(sorted(coalitions, key=lambda coalition: coalition.id)), controller, signal_controller,
                    detector=detector, majority_estimation=majority, stochastic_case=stochastic["case"] if stochastic else None)
    from .grid import validate_domain
    validate_domain(result)
    return result
