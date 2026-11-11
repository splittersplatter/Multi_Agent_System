"""Does the town settle under full information? Proof certificate plus empirical checks.

Freeze lemma (proved in the write-up, checked here on every run):
  call a round's count *clear* when the leader is at least 3 votes ahead of the runner-up
  and the runner-up at least 2 ahead of the third candidate. In a clear round no single
  voter can change who leads or who is in the top two, so every type's next vote depends
  only on (leader, runner-up):
      sincere -> favourite;  copycat -> leader;  pivot-seeker -> stays;
      front-runner -> stays if already on the leader or runner-up, else its preferred of the two
      (with an even number of other voters: always its preferred of the two).
  Applying that map twice gives the same votes as applying it once. Hence: if two
  consecutive rounds are clear with the same leader and runner-up, nobody ever moves again.

This module
  1. checks the certificate (rounds 0 and 1 clear, same top two) for any set of towns;
  2. enumerates every town of up to `max_small` voters (all types x all six rankings);
  3. simulates many random 300-voter towns, including deliberately near-tied ones.

Run:  PYTHONPATH=src:presentation python3 presentation/convergence.py
"""
from __future__ import annotations

import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

from fullinfo import all_small_towns, counts_of, simulate, step
from town import Town, all_mixes, preferences, tie_order, types

KINDS = ("sincere", "frontrunner", "copycat", "pivot")


def gaps(c: dict[str, int]) -> tuple[int, int]:
    v = sorted(c.values(), reverse=True)
    return v[0] - v[1], v[1] - v[2]


def clear(c: dict[str, int]) -> bool:
    g1, g2 = gaps(c)
    return g1 >= 3 and g2 >= 2


def top_two(c: dict[str, int], order: list[str]) -> tuple[str, str]:
    s = sorted(order, key=lambda p: (-c[p], order.index(p)))
    return s[0], s[1]


def certificate(prefs, kinds, order) -> dict:
    """Rounds 0 and 1 clear with the same leader and runner-up => frozen from round 1 (freeze lemma)."""
    r0 = [p[0] for p in prefs]
    r1 = step(r0, prefs, kinds, order)
    c0, c1 = counts_of(r0, order), counts_of(r1, order)
    ok = clear(c0) and clear(c1) and top_two(c0, order) == top_two(c1, order)
    return {"certified": ok, "round0": c0, "round1": c1, "gaps0": gaps(c0), "gaps1": gaps(c1),
            "leader": top_two(c1, order)[0]}


def lemma_violations(hist, order) -> int:
    bad = 0
    for t in range(len(hist) - 2):
        c0, c1 = counts_of(hist[t], order), counts_of(hist[t + 1], order)
        if clear(c0) and clear(c1) and top_two(c0, order) == top_two(c1, order) and hist[t + 2] != hist[t + 1]:
            bad += 1
    return bad


def exhaustive(max_small: int) -> list[dict]:
    order = ["A", "B", "C"]
    rows = []
    for n in range(2, max_small + 1):
        tally, movers, worst_gap, longest, viol = Counter(), Counter(), 0, 0, 0
        for prefs, kinds in all_small_towns(n):
            hist, cyc = simulate(prefs, kinds, order, rounds=60)
            viol += lemma_violations(hist, order)
            if cyc == 0:
                tally["settled"] += 1
                longest = max(longest, len(hist) - 1)
            elif cyc:
                tally["cycle"] += 1
                loop = hist[-1 - cyc:]
                moving = tuple(sorted({kinds[i] for i in range(n) if len({h[i] for h in loop}) > 1}))
                movers["+".join(moving)] += 1
                worst_gap = max(worst_gap, max(min(gaps(counts_of(h, order))) for h in loop))
            else:
                tally["undecided"] += 1
        total = sum(tally.values())
        rows.append({"voters": n, "towns": total, "settled": tally["settled"], "cycles": tally["cycle"],
                     "undecided": tally["undecided"], "cycle_share": tally["cycle"] / total,
                     "longest_settle_rounds": longest, "lemma_violations": viol,
                     "largest_smaller_gap_on_any_cycle": worst_gap, "who_moves_on_cycles": dict(movers.most_common())})
        print(rows[-1], flush=True)
    return rows


def random_large(towns: int, n: int, seed: int, near_tie: bool) -> dict:
    """Random mixes and random ranking distributions. With near_tie, sincere counts of the two
    largest parties are forced within 2 votes of each other (the case the lemma does not cover)."""
    rng = random.Random(f"large-{n}-{seed}-{near_tie}")
    rankings = [list(r) for r in itertools.permutations(("A", "B", "C"))]
    tally, settle, viol, cyc_gaps = Counter(), Counter(), 0, Counter()
    certified = 0
    for _ in range(towns):
        w = [rng.random() for _ in KINDS]
        kinds = rng.choices(KINDS, weights=w, k=n)
        rw = [rng.random() for _ in rankings]
        prefs = [list(r) for r in rng.choices(rankings, weights=rw, k=n)]
        if near_tie:   # move voters between the top two favourites until they are within 2
            for _ in range(n):
                c = Counter(p[0] for p in prefs)
                (a, ca), (b, cb) = c.most_common(2)
                if ca - cb <= 2:
                    break
                i = next(i for i, p in enumerate(prefs) if p[0] == a)
                prefs[i] = [b] + [x for x in prefs[i] if x != b]   # promote b, keep the rest of the order
        order = ["A", "B", "C"]
        rng.shuffle(order)
        cert = certificate(prefs, kinds, order)
        certified += cert["certified"]
        hist, cyc = simulate(prefs, kinds, order, rounds=200)
        viol += lemma_violations(hist, order)
        if cyc == 0:
            tally["settled"] += 1
            settle[len(hist) - 1] += 1
        elif cyc:
            tally["cycle"] += 1
            loop = hist[-1 - cyc:]
            cyc_gaps[max(min(gaps(counts_of(h, order))) for h in loop)] += 1
        else:
            tally["undecided"] += 1
    return {"voters": n, "towns": towns, "near_tie": near_tie, "certified_by_rounds_0_1": certified,
            "settled": tally["settled"], "cycles": tally["cycle"], "undecided": tally["undecided"],
            "settle_rounds": dict(sorted(settle.items())), "lemma_violations": viol,
            "cycles_by_largest_smaller_gap": dict(sorted(cyc_gaps.items()))}


def talk_towns(seeds=range(30)) -> dict:
    """Certificate for the default mix and for every one of the 84 mixes, on the talk's 30 towns."""
    out = {"default": [], "mixes": {}}
    for seed in seeds:
        t = Town()
        out["default"].append({"seed": seed, **certificate(preferences(t, seed), types(t, seed), tie_order(seed))})
    for mix in all_mixes():
        t = Town(mix=mix)
        key = "/".join(f"{round(s * 100)}" for _, s in mix)
        out["mixes"][key] = sum(certificate(preferences(t, s), types(t, s), tie_order(s))["certified"] for s in seeds)
    return out


def main(out_dir: Path, max_small: int = 6, large: int = 5000):
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"talk_towns": talk_towns()}
    d = result["talk_towns"]["default"]
    print("default mix certified:", sum(r["certified"] for r in d), "of", len(d),
          "smallest gaps round 0:", min(r["gaps0"][0] for r in d), min(r["gaps0"][1] for r in d),
          "round 1:", min(r["gaps1"][0] for r in d), min(r["gaps1"][1] for r in d), flush=True)
    print("mixes fully certified:", sum(v == 30 for v in result["talk_towns"]["mixes"].values()), "of 84", flush=True)
    result["exhaustive"] = exhaustive(max_small)
    result["random_300"] = [random_large(large, 300, 0, False), random_large(large, 300, 1, True)]
    for r in result["random_300"]:
        print(r, flush=True)
    (out_dir / "convergence.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main(Path(__file__).parent / "results", *map(int, sys.argv[1:]))
