"""Explicit plurality response models; no access to researcher-only current state.

See docs/voting-heuristics.md for source mappings and departures from the papers.
"""

from collections import Counter
from bisect import bisect_left
from functools import lru_cache
from itertools import combinations
import math
from typing import TYPE_CHECKING

from .model import ElectionError, make_scenario
from .epistemic import EPISTEMIC_POLICIES, validate_epistemic_parameters

if TYPE_CHECKING:
    from .policies import Observation


STRATEGIC = ("pivotal", "expected_utility", "top_k", "max_m", "tie_u", "tie_h",
             "tie_r", "poisson", "local_dominance", "maximin")
VOTING_POLICIES = ("sincere", "local_plurality", "sensed_plurality", "memory_pivotal") + STRATEGIC
COALITION_POLICIES = ("sight_plurality", "overheard_plurality", "coalition_fusion")
SIGNAL_POLICIES = ("signal_confident",)
CERTIFIED_POLICIES = ("direct_best_response", "source_local_dominance", "certified_conformity")
DEFAULTS = {"utility_mode": "rank", "top_k": 2, "samples": 200,
            "uncertainty_radius": 2, "max_states": 200000,
            "poll": "initial_truthful", "information_source": "native"}


def validate_parameters(parameters, parties=None, population=None):
    if parties is not None and len(parties) > 32:
        raise ElectionError("strategic policies support at most 32 parties; baseline policies remain unrestricted")
    allowed = set(DEFAULTS) | {"utilities", "initial_poll", "possible_scores"}
    if not isinstance(parameters, dict) or set(parameters) - allowed:
        raise ElectionError("strategic parameters contain unsupported fields")
    p = {**DEFAULTS, **parameters}
    if p["utility_mode"] not in ("rank", "explicit"):
        raise ElectionError("utility_mode must be rank or explicit")
    if p["information_source"] not in ("native", "poll"):
        raise ElectionError("information_source must be native or poll")
    for key, low, high in (("top_k", 1, 100), ("samples", 1, 100000),
                           ("uncertainty_radius", 0, 20), ("max_states", 1, 1000000)):
        if type(p[key]) is not int or not low <= p[key] <= high:
            raise ElectionError(f"{key} must be an integer in [{low}, {high}]")
    if p["poll"] not in ("initial_truthful", "explicit"):
        raise ElectionError("poll must be initial_truthful or explicit")
    if p["poll"] == "explicit" and "initial_poll" not in p:
        raise ElectionError("explicit poll requires initial_poll")
    if p["utility_mode"] == "explicit" and "utilities" not in p:
        raise ElectionError("explicit utility_mode requires utilities for every party")
    if "utilities" in p:
        values = p["utilities"]
        if (not isinstance(values, dict) or not values or
                any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e6 for x in values.values()) or
                (parties is not None and set(values) != set(parties))):
            raise ElectionError("utilities must map every party to finite values within +/-1e6")
        if p["utility_mode"] != "explicit":
            raise ElectionError("utilities require utility_mode=explicit")
    if "initial_poll" in p:
        values = p["initial_poll"]
        if (not isinstance(values, list) or not values or any(type(x) is not int or x < 0 for x in values) or
                (parties is not None and len(values) != len(parties)) or
                (population is not None and sum(values) != population)):
            raise ElectionError("initial_poll must be nonnegative counts in party order summing to population")
        if p["poll"] != "explicit":
            raise ElectionError("initial_poll requires poll=explicit")
    if "possible_scores" in p:
        states = p["possible_scores"]
        if not isinstance(states, list) or not states or len(states) > p["max_states"]:
            raise ElectionError("possible_scores must be a nonempty bounded list")
        for state in states:
            if (not isinstance(state, list) or not state or any(type(x) is not int or x < 0 for x in state) or
                    (parties is not None and len(state) != len(parties)) or
                    (population is not None and sum(state) != population - 1)):
                raise ElectionError("possible_scores states exclude own ballot and must sum to population-1")
    return p


def configure_voting(scenario, policy, parameters=None):
    """Explicit episode-wide choice; preserve movement, capabilities and schedules.

    Individual/scheduled voting parameter overrides are replaced intentionally.
    Capabilities are never granted by choosing a policy.
    """
    if policy not in VOTING_POLICIES + COALITION_POLICIES + SIGNAL_POLICIES + EPISTEMIC_POLICIES:
        raise ElectionError("unknown voting policy")
    if not isinstance(parameters if parameters is not None else {}, dict):
        raise ElectionError("voting parameters must be an object")
    params = validate_parameters(parameters or {}, scenario.parties, len(scenario.people)) if policy in STRATEGIC else parameters or {}
    if policy in EPISTEMIC_POLICIES:
        validate_epistemic_parameters(params, policy)
    if policy not in STRATEGIC + EPISTEMIC_POLICIES and params:
        raise ElectionError("baseline voting selection takes no strategic parameters")
    raw = scenario.as_dict()
    for group in raw["groups"].values():
        existing = group["parameters"]
        group["parameters"] = {**existing, "voting": params}
        group["voting"] = policy
    for item in [*raw["people"], *raw["interventions"]]:
        overrides = item.get("overrides")
        if overrides is not None:
            overrides.pop("voting", None)
            if "parameters" in overrides:
                overrides["parameters"] = {**overrides["parameters"], "voting": params}
    return make_scenario(raw)


def winner(scores, ballot):
    return max(range(len(scores)), key=lambda c: (scores[c] + (c == ballot), -c))


def memory_pivotal(parties, preference, current, population, state, config):
    """Strict predicted-winner improvement using exact estimated other-voter scores."""
    from .majority import _scores, estimate, leader_indices, poll_weight_ratio

    scores, denominator = _scores(state, config)
    other = tuple((population - 1) * value for value in scores)
    predicted = tuple(parties[max(range(len(parties)), key=lambda c:
                      (other[c] + denominator * (c == action), -c))]
                      for action in range(len(parties)))
    baseline = predicted[parties.index(current)]
    best = next(party for party in preference if party in predicted)
    choice = best if preference.index(best) < preference.index(baseline) else current
    return choice, {"policy": "memory_pivotal", "previous": current, "choice": choice,
                    "switched": choice != current, "baseline_winner": baseline,
                    "predicted_winners": dict(zip(parties, predicted)),
                    "estimated_shares": dict(zip(parties, estimate(state, config))),
                    "estimated_leaders": [parties[i] for i in leader_indices(state, config)],
                    "sample_size": len(state.entries), "observation_round": state.round,
                    "ballot_source_round": max(0, state.round - 1),
                    **({"poll_counts": list(state.published_poll if state.published_poll is not None else config.poll_counts),
                        "poll_source_round": state.published_round,
                        "poll_weight": poll_weight_ratio(state, config)[0] / poll_weight_ratio(state, config)[1],
                        "effective_poll_weight": (poll_weight_ratio(state, config)[0] / poll_weight_ratio(state, config)[1]
                                                  if state.entries else 1.0)}
                       if config.poll_refresh_rounds is not None else {}),
                    "information": "initial poll and recent incoming proximity ballots",
                    "strict_improvement": choice != current,
                    "convergence": "uncertified"}


def direct_best_response(parties, counts, current, preference):
    """Source direct best reply given the current public aggregate and own ballot."""
    own = parties.index(current)
    scores = [counts[party] - (index == own) for index, party in enumerate(parties)]
    current_winner = parties[winner(scores, own)]
    achievable = {parties[winner(scores, candidate)] for candidate in range(len(parties))}
    best = next(party for party in preference if party in achievable)
    return best if preference.index(best) < preference.index(current_winner) else current


def source_local_dominance(parties, counts, current, preference, radius, max_states):
    """S6 variable-total L1 worlds around actual other-voter scores."""
    center = tuple(counts[p] - (p == current) for p in parties)
    worlds = []

    def visit(index, remaining, partial):
        if index == len(center):
            worlds.append(tuple(partial))
            if len(worlds) > max_states:
                raise ElectionError("source local dominance world count exceeds max_states")
            return
        for delta in range(-min(center[index], remaining), remaining + 1):
            partial.append(center[index] + delta)
            visit(index + 1, remaining - abs(delta), partial)
            partial.pop()

    visit(0, radius, [])
    rank = {party: index for index, party in enumerate(preference)}
    outcomes = {party: [rank[parties[winner(world, index)]] for world in worlds]
                for index, party in enumerate(parties)}
    baseline = outcomes[current]
    for party in preference:
        values = outcomes[party]
        if all(a <= b for a, b in zip(values, baseline)) and any(a < b for a, b in zip(values, baseline)):
            return party
    return current


def certified_conformity(preference, observed_ballots):
    """Most common observed first choice, with private-ranking tie order."""
    counts = Counter(ballot[0] for ballot in observed_ballots)
    highest = max(counts.values(), default=0)
    return next(party for party in preference if counts[party] == highest)


def compositions(total, size):
    if size == 1:
        yield (total,)
    else:
        for value in range(total + 1):
            for rest in compositions(total - value, size - 1):
                yield (value,) + rest


def log_probability(scores, probabilities):
    return (math.lgamma(sum(scores) + 1) - sum(math.lgamma(x + 1) for x in scores)
            + sum(x * math.log(p) for x, p in zip(scores, probabilities) if x))


def _bounded_size(total, size, limit):
    count = math.comb(total + size - 1, size - 1)
    if count > limit:
        raise ElectionError(f"exact outcome space {count} exceeds max_states={limit}; use a sampled policy or raise the explicit limit")


@lru_cache(maxsize=64)
def _exact_scores(total, probabilities, utilities, limit):
    _bounded_size(total, len(probabilities), limit)
    values = [0.0] * len(probabilities)
    for state in compositions(total, len(probabilities)):
        weight = math.exp(log_probability(state, probabilities))
        for choice in range(len(values)):
            values[choice] += weight * utilities[winner(state, choice)]
    return tuple(values)


@lru_cache(maxsize=64)
def _exact_gains(total, probabilities, utilities, limit):
    """Exact expected-utility differences; skip states where no vote can matter.

    Any pivotal profile has two leaders separated by at most one vote. Include
    multiway ties, deduplicate profiles, and subtract the abstention outcome,
    which is constant across ballot choices. This is not a sampling shortcut.
    """
    size=len(probabilities)
    _bounded_size(total,size,limit)
    states=set(); visits=0
    for x,y in combinations(range(size),2):
        others=[c for c in range(size) if c not in (x,y)]
        for gap in (-1,0,1):
            for left in range(max(0,total//size-1),total//2+2):
                right=left+gap; remainder=total-left-right
                if right<0 or remainder<0:continue
                allocations=compositions(remainder,len(others)) if others else ([()] if remainder==0 else [])
                for rest in allocations:
                    visits+=1
                    if visits>limit*max(1,size):
                        raise ElectionError("exact pivotal enumeration exceeds max_states work budget")
                    if any(v>max(left,right) for v in rest):continue
                    state=[0]*size;state[x]=left;state[y]=right
                    for c,v in zip(others,rest):state[c]=v
                    states.add(tuple(state))
    values=[0.0]*size
    for state in sorted(states):
        baseline=max(range(size),key=lambda c:(state[c],-c))
        weight=math.exp(log_probability(state,probabilities))
        for choice in range(size):
            values[choice]+=weight*(utilities[winner(state,choice)]-utilities[baseline])
    return tuple(values)


def _pivot_states(total, size, x, y):
    others = [c for c in range(size) if c not in (x, y)]
    low = (total + 2 * size - 3) // size
    for tied in range(low, total // 2 + 1):
        if not others:
            if 2 * tied == total:
                yield tuple(tied for _ in range(size))
            continue
        for rest in compositions(total - 2 * tied, len(others)):
            if any(v >= tied for v in rest):
                continue
            state = [0] * size
            state[x] = state[y] = tied
            for c, count in zip(others, rest):
                state[c] = count
            yield tuple(state)


@lru_cache(maxsize=512)
def _binomial_cdf(total, probability):
    # Inverse-CDF sampling; log PMFs avoid underflow at large n or skewed p.
    logs=[math.lgamma(total+1)-math.lgamma(k+1)-math.lgamma(total-k+1)
          + k*math.log(probability)+(total-k)*math.log1p(-probability)
          for k in range(total+1)]
    shift=max(logs); weights=[math.exp(v-shift) for v in logs]
    norm=sum(weights); acc=0.0; cdf=[]
    for weight in weights:
        acc+=weight/norm;cdf.append(min(1.0,acc))
    cdf[-1]=1.0
    return tuple(cdf)


def _sample_multinomial(total, probabilities, rng):
    # Multinomial factorization into conditional binomials, not an approximation.
    counts=[]; remaining=total; mass=1.0
    for probability in probabilities[:-1]:
        if remaining == 0:
            counts.append(0); mass-=probability
            continue
        conditional=min(1.0,max(0.0,probability/mass))
        if conditional==0:draw=0
        elif conditional==1:draw=remaining
        else:draw=bisect_left(_binomial_cdf(remaining,conditional),rng.random())
        counts.append(draw);remaining-=draw;mass-=probability
    return counts+[remaining]


def _pivot_weights(total, probabilities, method, samples, limit, rng):
    size = len(probabilities)
    weights = [[0.0] * size for _ in range(size)]
    if size == 1:
        return weights
    if method in ("tie_h", "tie_u", "tie_r") and samples * size * size > limit * 10:
        raise ElectionError("pivot sampling workload exceeds max_states*10; reduce samples/parties")
    if method == "tie_r":
        if samples * max(1, total) > limit * 20:
            raise ElectionError("TieR draw workload exceeds max_states*20; reduce samples/population")
        for _ in range(samples):
            state = _sample_multinomial(total, probabilities, rng)
            leaders = [c for c in range(size) if state[c] == max(state)]
            if len(leaders) == 2:
                x, y = leaders
                weights[x][y] += 1 / samples; weights[y][x] += 1 / samples
        return weights
    if method == "poisson":
        return _poisson_weights(total, probabilities, limit)
    # TieU must enumerate pivot states; exact Top-k/Max-M also bounded upfront.
    if method != "tie_h":
        _bounded_size(total, size, limit)
    for x, y in combinations(range(size), 2):
        if method == "tie_h":
            states = []
            others = [c for c in range(size) if c not in (x, y)]
            low, high = (total + 2 * size - 3) // size, total // 2
            if low > high:
                continue
            for _ in range(samples):
                tied = rng.randint(low, high)
                rest, order = total - 2 * tied, others[:]
                rng.shuffle(order)
                state = [0] * size; state[x] = state[y] = tied
                for pos, c in enumerate(order):
                    remaining = len(order) - pos - 1
                    count = rng.randint(max(0, rest - remaining * (tied - 1)), min(rest, tied - 1))
                    state[c] = count; rest -= count
                if rest == 0:
                    states.append(tuple(state))
        else:
            states = list(_pivot_states(total, size, x, y))
            correction = 0.0
            if method == "tie_u" and len(states) > samples:
                correction = math.log(len(states) / samples)
                states = rng.sample(states, samples)
        if states:
            # Work in logs: relative weights remain meaningful for rare pivots.
            weights[x][y] = [log_probability(s, probabilities) + (correction if method == "tie_u" else 0.0) for s in states]
            weights[y][x] = weights[x][y]
    logs = [v for row in weights for cell in row if isinstance(cell, list) for v in cell]
    if logs:
        shift = max(logs)
        for x, y in combinations(range(size), 2):
            cell = weights[x][y]
            value = sum(math.exp(v - shift) for v in cell) if isinstance(cell, list) else 0.0
            weights[x][y] = weights[y][x] = value
    return weights


@lru_cache(maxsize=64)
def _poisson_weights(total, probabilities, limit):
    """Two-way winning-tie probabilities for independent Poisson counts.

    Twelve-sigma + 50 cutoff; not the paper's asymptotic Skellam formula.
    All terms accumulated in log space before common rescaling.
    """
    means = [total * p for p in probabilities]
    cutoff = math.ceil(max(means) + 12 * math.sqrt(max(means) + 1) + 50)
    if (cutoff + 1) * len(means) ** 2 > limit:
        raise ElectionError("Poisson summation exceeds max_states; raise limit or reduce population")
    pmf, cdf = [], []
    for mean in means:
        logp = [(-mean + k * math.log(mean) - math.lgamma(k + 1)) if mean else (0.0 if k == 0 else -math.inf)
                for k in range(cutoff + 1)]
        pmf.append(logp)
        running, values = 0.0, []
        for value in logp:
            running += math.exp(value); values.append(min(1.0, running))
        cdf.append(values)
    pairlogs = {}
    for x, y in combinations(range(len(means)), 2):
        terms = []
        for tied in range(cutoff + 1):
            others = [cdf[c][tied - 1] if tied else 0.0 for c in range(len(means)) if c not in (x, y)]
            if all(v > 0 for v in others):
                term = pmf[x][tied] + pmf[y][tied] + sum(math.log(v) for v in others)
                if math.isfinite(term):
                    terms.append(term)
        if terms:
            shift = max(terms)
            pairlogs[x, y] = shift + math.log(sum(math.exp(v - shift) for v in terms))
    weights = [[0.0] * len(means) for _ in means]
    if pairlogs:
        shift = max(pairlogs.values())
        for (x, y), value in pairlogs.items():
            weights[x][y] = weights[y][x] = math.exp(value - shift)
    return weights


def _center(total, probabilities):
    raw = [p * total for p in probabilities]
    result = [math.floor(v) for v in raw]
    for c in sorted(range(len(raw)), key=lambda c: (-(raw[c] - result[c]), c))[:total - sum(result)]:
        result[c] += 1
    return tuple(result)


def uncertainty_states(center, radius, limit):
    """Fixed-electorate L1 ball; explicit modelling choice, not DEL worlds."""
    states = []
    def visit(index, budget, delta, prefix):
        if index == len(center) - 1:
            value = center[index] - delta
            if value >= 0 and abs(delta) <= budget:
                states.append(tuple(prefix + [value]))
                if len(states) > limit:
                    raise ElectionError("uncertainty set exceeds max_states")
            return
        for change in range(-min(center[index], budget), budget + 1):
            visit(index + 1, budget - abs(change), delta + change, prefix + [center[index] + change])
    visit(0, radius, 0, [])
    return tuple(states)


def decide(policy, obs: "Observation", parameters, memory, rng, population, initial_poll):
    if policy not in STRATEGIC:
        raise ElectionError("unknown strategic voting policy")
    p = validate_parameters(parameters, obs.parties, population)
    parties = obs.parties; m = len(parties)
    rank = [parties.index(c) for c in obs.own_preference]
    utilities = tuple(float(p["utilities"][c]) for c in parties) if p["utility_mode"] == "explicit" else tuple((m - 1 - rank.index(c)) / max(1, m - 1) for c in range(m))
    if any(utilities[rank[i]] < utilities[rank[i+1]] for i in range(m-1)):
        raise ElectionError("utilities must agree with the agent's private ranking")
    current = parties.index(obs.own_previous_ballot[0])
    observed = {sender: parties.index(ballot[0]) for sender, _, _, ballot in obs.sensed_ballots}
    counts = Counter(observed.values())
    probabilities = tuple((counts[c] + 1) / (len(observed) + m) for c in range(m))
    trace = {"policy": policy, "observed": len(observed), "utilities": list(utilities)}
    old = memory or {}
    if policy == "pivotal" or p["information_source"] == "poll":
        poll = list(old.get("scores", p.get("initial_poll", initial_poll)))
        last = old.get("last_observed", {})
        for sender, choice in observed.items():
            if sender in last and last[sender] != choice:
                poll[last[sender]] -= 1; poll[choice] += 1
        own_last = old.get("last_own", current)
        if own_last != current:
            poll[own_last] -= 1; poll[current] += 1
        if any(v < 0 for v in poll):
            raise ElectionError("poll belief became negative; inconsistent explicit poll/observed history")
        others = poll[:]; others[current] -= 1
        if others[current] < 0:
            raise ElectionError("poll belief excludes the agent's own ballot")
        trace.update(scores=poll, last_observed={**last, **observed}, last_own=current)
        probabilities = tuple((v+1)/(population-1+m) for v in others)
    information = "initial public poll plus observed ballot changes" if "scores" in trace else "Laplace-smoothed neighbor sample"
    if policy == "pivotal":
        outcomes = [utilities[winner(others, c)] for c in range(m)]
        best = max(range(m), key=lambda c: (outcomes[c], -rank.index(c)))
        choice = best if outcomes[best] > outcomes[current] else current
        trace.update(outcome_utilities=outcomes)
    elif policy == "expected_utility":
        values = _exact_gains(population-1, probabilities, utilities, p["max_states"])
        choice = _choose(values, current, rank)
        trace.update(response_scores=values, response_score_kind="expected utility gain over abstention")
    elif policy in ("local_dominance", "maximin"):
        center = tuple(others) if "scores" in trace else _center(population-1, probabilities)
        states = tuple(tuple(s) for s in p["possible_scores"]) if "possible_scores" in p else uncertainty_states(center, p["uncertainty_radius"], p["max_states"])
        values = [tuple(utilities[winner(s, c)] for s in states) for c in range(m)]
        if policy == "maximin":
            worst = [min(row) for row in values]
            choice = _choose(worst, current, rank)
            trace["worst_utilities"] = worst
        else:
            def dominates(a, b):
                return all(x >= y for x, y in zip(values[a], values[b])) and any(x > y for x, y in zip(values[a], values[b]))
            candidates = [c for c in rank if dominates(c, current) and not any(dominates(d, c) for d in range(m))]
            choice = candidates[0] if candidates else current
            trace["dominating_candidates"] = [parties[c] for c in candidates]
        trace.update(state_count=len(states), center=center,
                     uncertainty="explicit score worlds" if "possible_scores" in p else "fixed-population L1 score worlds")
    else:
        active = sorted(range(m), key=lambda c: (-probabilities[c], rank.index(c)))[:min(m, p["top_k"])] if policy == "top_k" else list(range(m))
        norm = sum(probabilities[c] for c in active)
        probs = tuple(probabilities[c] / norm for c in active)
        weights = _pivot_weights(population-1, probs, policy, p["samples"], p["max_states"], rng)
        values = [-math.inf] * m
        for ix, x in enumerate(active):
            gains = [weights[ix][iy] * (utilities[x] - utilities[y]) for iy, y in enumerate(active) if y != x]
            values[x] = max(gains, default=0.0) if policy == "max_m" else sum(gains)
        choice = _choose(values, current, rank)
        trace.update(response_scores=[None if not math.isfinite(v) else v for v in values],
                     considered=[parties[c] for c in active], pivot_model="two-way winning ties only")
    trace.update(choice=parties[choice], previous=parties[current], switched=choice != current, information=information)
    ballot = (parties[choice],) + tuple(c for c in obs.own_preference if c != parties[choice])[:obs.k-1]
    return ballot, trace


def _choose(values, current, rank):
    # Inertia on utility ties; explicit preference ordering otherwise.
    best = max(values)
    if values[current] >= best - 1e-12:
        return current
    return next(c for c in rank if values[c] >= best - 1e-12)
