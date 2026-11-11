"""The four experiments of the talk, as named settings of the spoiler town.

Every setting is run on the same 30 towns (seeds 0-29). Changing a setting changes one
switch; opinions, map positions, voter types and the tie order stay the same per seed.

  e1        default mix (40% sincere, 30% front-runner, 20% copycat, 10% pivot-seeker),
            everyone hears everyone (full information), 40 rounds.
  e2_check  Experiment 2 runs on the fast exact simulator (fullinfo.py) for all 84 mixes;
            this engine check reruns every mix on two towns for 6 rounds to confirm the match.
  e3_r{r}_{walk|still}   hearing radius r for everyone, people walking or standing still.
  e4_f{n}   a 30-voter minority that always votes for its party; each member is followed by
            n random listeners anywhere in town (propaganda reach); everyone else hears locally.
"""
from __future__ import annotations

from town import FULL, Town, all_mixes

SEEDS = list(range(30))
RADII = [0.4, 0.2, 0.1, 0.07, 0.05]
LONG_RADII, LONG_ROUNDS = [0.4, 0.2, 0.1, 0.05], 150
LONG_FOLLOWERS = [0, 20, 40]
FOLLOWERS = [0, 5, 10, 20, 40, 80]
E4_RADIUS = 0.2          # chosen from Experiment 3: about 32 neighbours; Left wins 23 of 30 and the winner settles
E4_PARTY = "Centre"      # the Condorcet winner, squeezed to third under local hearing
E4_SIZE = 30             # 10% of the town


def mix_name(mix) -> str:
    return "-".join(f"{round(s * 100)}" for _, s in mix)


def all_settings() -> dict[str, tuple[str, Town, list[int]]]:
    """name -> (experiment, town, seeds)."""
    s: dict[str, tuple[str, Town, list[int]]] = {"e1": ("e1", Town(), SEEDS)}
    for mix in all_mixes():
        s[f"e2_check_{mix_name(mix)}"] = ("e2_check", Town(mix=mix, rounds=6), [0, 1])
    for r in RADII:
        for walking in (True, False):
            s[f"e3_r{r}_{'walk' if walking else 'still'}"] = ("e3", Town(radius=r, walking=walking), SEEDS)
    # Experiment 3 checks: longer runs (does the walking town ever settle?) and 301 voters,
    # where the engine's front-runner rule loses its stickiness (see fullinfo.py, parity note).
    for r in LONG_RADII:
        s[f"e3long_r{r}_walk"] = ("e3long", Town(radius=r, rounds=LONG_ROUNDS), SEEDS)
    for r in RADII:
        s[f"e3odd_r{r}_walk"] = ("e3odd", Town(voters=301, radius=r), SEEDS)
    for n in FOLLOWERS:
        s[f"e4_f{n}"] = ("e4", Town(radius=E4_RADIUS, minority=E4_SIZE, minority_party=E4_PARTY, followers=n), SEEDS)
        s[f"e4odd_f{n}"] = ("e4odd", Town(voters=301, radius=E4_RADIUS, minority=E4_SIZE, minority_party=E4_PARTY,
                                          followers=n), SEEDS)
    for n in LONG_FOLLOWERS:   # does the propaganda result hold over 150 rounds?
        s[f"e4long_f{n}"] = ("e4long", Town(radius=E4_RADIUS, rounds=LONG_ROUNDS, minority=E4_SIZE, minority_party=E4_PARTY,
                                            followers=n), SEEDS)
    return s


assert FULL > max(RADII)
