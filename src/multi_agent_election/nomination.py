"""Pre-election spatial nomination; issue and physical coordinates are separate."""

from collections import Counter
from dataclasses import replace
import hashlib
import math
import random

from .model import ElectionError, Nomination, _id, _int, _make_group, _number, _overrides, apply_overrides, make_scenario
from .network import proximity_edges


def make_nominated_scenario(raw):
    """Resolve one immutable leader set before compiling the ordinary scenario."""
    allowed = {"k", "seed", "rounds", "groups", "people", "network", "interventions", "convergence",
               "coalitions", "campaign_controller", "signal_controller", "nomination", "alignment", "detector", "leaders", "majority_estimation"}
    if set(raw) - allowed:
        raise ElectionError("nomination scenarios derive parties; unsupported scenario fields")
    spec = raw["nomination"]
    if (not isinstance(spec, dict) or not {"mode", "m", "eligible"} <= set(spec)
            or set(spec) - {"mode", "m", "eligible", "nominees"}):
        raise ElectionError("nomination requires mode, m and eligible")
    mode = spec["mode"]
    if mode not in ("endogenous", "fixed", "random"):
        raise ElectionError("nomination mode must be endogenous, fixed or random")
    if ("nominees" in spec) != (mode == "fixed"):
        raise ElectionError("fixed nomination requires nominees; other modes forbid them")
    people = raw.get("people")
    if not isinstance(people, list) or not people:
        raise ElectionError("nomination requires a nonempty electorate")
    groups_raw = raw.get("groups")
    if not isinstance(groups_raw, dict) or not groups_raw:
        raise ElectionError("groups must be a non-empty table")
    groups = {name: _make_group(name, value) for name, value in groups_raw.items()}
    ideals = {}; positions = {}; radii = {}; serialized = []
    dimension = None
    for item in people:
        if (not isinstance(item, dict) or not {"id", "group", "ideal"} <= set(item)
                or set(item) - {"id", "group", "ideal", "position", "overrides"}):
            raise ElectionError("nomination person requires id, group and ideal; preference is derived")
        person = _id(item["id"], "person id")
        if person in ideals:
            raise ElectionError("person ids must be unique")
        group_id = _id(item["group"], "person group")
        if group_id not in groups:
            raise ElectionError(f"person {person!r}: unknown group")
        vector = item["ideal"]
        if not isinstance(vector, list) or not vector or (dimension is not None and len(vector) != dimension):
            raise ElectionError("issue ideals must be nonempty vectors of equal dimension")
        dimension = len(vector)
        ideals[person] = tuple(_number(v, "issue coordinate", 0, 1) for v in vector)
        position = item.get("position", [0.5, 0.5])
        if not isinstance(position, list) or len(position) != 2:
            raise ElectionError("position must have two coordinates")
        positions[person] = tuple(_number(v, "coordinate", 0, 1) for v in position)
        group = apply_overrides(groups[group_id], _overrides(item.get("overrides", {})))
        radii[person] = group.proximity_radius
        serialized.append({key: value for key, value in item.items() if key != "ideal"})
    eligible = spec["eligible"]
    if (not isinstance(eligible, list) or not eligible or any(not isinstance(p, str) or p not in ideals for p in eligible)
            or len(set(eligible)) != len(eligible)):
        raise ElectionError("nomination eligible must contain unique known people")
    eligible = tuple(sorted(eligible))
    m = _int(spec["m"], "nomination m", 1)
    k = _int(raw.get("k"), "k", 1)
    if not k <= m <= len(eligible):
        raise ElectionError("nomination requires k <= m <= eligible population")
    seed = _int(raw.get("seed", 0), "seed", 0)
    network = raw.get("network", {})
    if not isinstance(network, dict) or set(network) - {"radius", "proximity_mode", "static_proximity_edges", "persistent_edges", "campaign_edges", "private_channels"}:
        raise ElectionError("invalid nomination network")
    radius = _number(network["radius"], "radius", 0, math.sqrt(2)) if "radius" in network else None
    effective_radii = {p: r if r is not None else radius for p, r in radii.items()}
    proximity_mode = network.get("proximity_mode", "dynamic")
    if proximity_mode not in ("dynamic", "frozen", "static") or ("static_proximity_edges" in network) != (proximity_mode == "static"):
        raise ElectionError("invalid nomination proximity mode or static edges")
    def edges(name):
        values = network.get(name, [])
        if (not isinstance(values, list) or any(not isinstance(e, list) or len(e) != 2
                or any(not isinstance(p, str) or p not in ideals for p in e) or e[0] == e[1] for e in values)):
            raise ElectionError(f"invalid {name}")
        result = tuple(tuple(e) for e in values)
        if len(set(result)) != len(result):
            raise ElectionError(f"{name} edges must be unique")
        return result
    persistent = edges("persistent_edges"); campaign = edges("campaign_edges")
    proximity = edges("static_proximity_edges") if proximity_mode == "static" else proximity_edges(positions, radius, effective_radii)
    public = set(persistent) | set(campaign) | set(proximity)
    def distance(a, b):
        return math.fsum((x - y) ** 2 for x, y in zip(ideals[a], ideals[b]))
    votes = []
    for person in sorted(ideals):
        candidates = [candidate for candidate in eligible if candidate == person or (candidate, person) in public]
        votes.append((person, min(candidates, key=lambda candidate: (distance(person, candidate), candidate)) if candidates else None))
    totals = Counter(candidate for _, candidate in votes if candidate is not None)
    if mode == "endogenous":
        winners = sorted(eligible, key=lambda candidate: (-totals[candidate], candidate))[:m]
    elif mode == "fixed":
        winners = spec["nominees"]
        if (not isinstance(winners, list) or len(winners) != m or any(not isinstance(p, str) or p not in eligible for p in winners)
                or len(set(winners)) != m):
            raise ElectionError("fixed nominees must be m unique eligible people")
    else:
        key = f"{seed}\0nomination\0random-nominees-v1".encode()
        winners = random.Random(int.from_bytes(hashlib.sha256(key).digest(), "big")).sample(eligible, m)
    winners = tuple(sorted(winners))
    for item in serialized:
        person = item["id"]
        item["preference"] = sorted(winners, key=lambda candidate: (distance(person, candidate), candidate))
    resolved = {key: value for key, value in raw.items() if key not in ("nomination", "alignment", "leaders")}
    resolved["parties"] = list(winners)
    resolved["people"] = serialized
    scenario = make_scenario(resolved)
    nomination = Nomination(mode, m, eligible, winners, tuple(votes), tuple((p, totals[p]) for p in eligible))
    scenario = replace(scenario, people=tuple(replace(person, ideal=ideals[person.id]) for person in scenario.people))
    if "alignment" in raw:
        from .alignment import parse_alignment
        scenario = replace(scenario, alignment=parse_alignment(raw["alignment"], scenario))
    if "leaders" in raw:
        from .leaders import parse_leaders
        scenario = replace(scenario, leaders=parse_leaders(raw["leaders"], scenario))
    return replace(scenario, nomination=nomination)
