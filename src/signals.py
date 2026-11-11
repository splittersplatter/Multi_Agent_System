"""Bounded aggregate-report generation and explicitly trusting voter response."""


def generate_signal(controller, parties, truth, remaining, rng):
    report = list(truth)
    limit = min(controller.per_broadcast_budget, remaining)
    if controller.policy == "truthful" or limit == 0 or len(parties) < 2:
        return tuple(report), 0
    destination = parties.index(controller.target) if controller.policy == "target_biased" else rng.randrange(len(parties))
    moved = 0
    while moved < limit:
        sources = [i for i,value in enumerate(report) if i != destination and value > 0]
        if not sources:
            break
        source = (max(sources,key=lambda i:(report[i],-i)) if controller.policy == "target_biased"
                  else rng.choice(sources))
        report[source] -= 1; report[destination] += 1; moved += 1
    return tuple(report), moved


def trusting_response(parties, preference, ballot, signal):
    """One-step plurality response to a report; inconsistent reports retain ballot."""
    if signal is None:
        return ballot, {"status":"unavailable", "choice":ballot[0]}
    source_round, broadcast_round, reported = signal
    current = ballot[0]; current_index = parties.index(current)
    scores = list(reported)
    if scores[current_index] == 0:
        return ballot, {"status":"inconsistent_own_ballot", "choice":current,
                        "source_round":source_round,"broadcast_round":broadcast_round,"report":list(reported)}
    scores[current_index] -= 1
    def winner(choice):
        return max(parties,key=lambda party:(scores[parties.index(party)] + (party == choice),-parties.index(party)))
    before = winner(current)
    reachable = {winner(party) for party in parties}
    best = next(party for party in preference if party in reachable)
    choice = best if preference.index(best) < preference.index(before) else current
    chosen = ((choice,) + tuple(party for party in preference if party != choice)[:len(ballot)-1]
              if choice != current else ballot)
    return chosen, {"status":"trusting_report", "previous":current,"choice":choice,
                    "source_round":source_round,"broadcast_round":broadcast_round,
                    "report":list(reported),"baseline_winner":before,"predicted_winner":winner(choice)}
