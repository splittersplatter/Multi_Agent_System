"""Permission-filtered ballot sensing; reports remain a separate input channel."""

from collections import defaultdict


def sense_ballots(edges, channels, permissions, ballots, source_round):
    """Return completed ballots only through each receiver's authorized channels."""
    if not any(cap.sense_public_ballots or cap.sense_private_ballots for cap in permissions.values()):
        return {}
    result = defaultdict(list)
    for sender, recipient in sorted(edges):
        if permissions[recipient].sense_public_ballots:
            result[recipient].append((sender, "public", source_round, ballots[sender]))
    for name, members in sorted(channels.items()):
        members = sorted(members)
        for recipient in members:
            if permissions[recipient].sense_private_ballots:
                result[recipient].extend((sender, name, source_round, ballots[sender])
                                         for sender in members if sender != recipient)
    return {person: tuple(sorted(records)) for person, records in result.items()}
