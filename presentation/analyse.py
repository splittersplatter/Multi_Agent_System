"""Turn results/runs.jsonl (engine runs) and the fast simulator into the numbers of the talk.

    PYTHONPATH=src:presentation python3 presentation/analyse.py

Writes results/summary.json (every number quoted on the slides and in the write-up)
and results/summary.md (the same, readable), plus results/mixes.csv (Experiment 2).
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from experiments import (E4_PARTY, E4_RADIUS, FOLLOWERS, LONG_FOLLOWERS, LONG_RADII, RADII, SEEDS,  # noqa: E402
                         mix_name)
from fullinfo import counts_of, simulate, step  # noqa: E402
from measures import (borda_scores, condorcet_winner, effective_parties, head_to_head,  # noqa: E402
                      instant_runoff, plurality)
from town import FULL, Town, all_mixes, preferences, tie_order, types  # noqa: E402

RESULTS = HERE / "results"
NAME = {"L": "Left", "R": "Right", "C": "Centre"}
TYPE = {"s": "sincere", "f": "frontrunner", "c": "copycat", "p": "pivot", "m": "minority"}
PARTIES = ["Centre", "Left", "Right"]
TAIL = 10   # "settled" = no change during the last TAIL rounds


def med(xs):
    return st.median(xs)


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, round(p * (len(xs) - 1))))]


def load_runs() -> dict[str, list[dict]]:
    by = defaultdict(list)
    for line in run_lines():
        r = json.loads(line)
        by[r["setting"]].append(r)
    for rows in by.values():
        rows.sort(key=lambda r: r["seed"])
    return by


def run_lines() -> list[str]:
    """results/runs.jsonl, or the compressed copy shipped with the branch (runs.jsonl.gz)."""
    plain, packed = RESULTS / "runs.jsonl", RESULTS / "runs.jsonl.gz"
    if plain.exists():
        return plain.read_text().splitlines()
    import gzip
    return gzip.decompress(packed.read_bytes()).decode().splitlines()


def switches(r) -> list[int]:
    v = r["votes"]
    return [sum(a != b for a, b in zip(v[t - 1], v[t])) for t in range(1, len(v))]


def last_change(seq) -> int:
    """Last round whose value differs from the round before (0 if never)."""
    return max((t for t in range(1, len(seq)) if seq[t] != seq[t - 1]), default=0)


def period(votes, max_p=4):
    """Smallest p with votes[t] == votes[t-p] for every t in the last TAIL rounds; None if none <= max_p."""
    n = len(votes)
    for p in range(1, max_p + 1):
        if all(votes[t] == votes[t - p] for t in range(n - TAIL, n)):
            return p
    return None


def moved_by_type(r) -> dict:
    """Final vote of each type, split by favourite -> final choice."""
    out = defaultdict(Counter)
    for t, fav, fin in zip(r["types"], r["favourites"], r["votes"][-1]):
        out[TYPE[t]][f"{NAME[fav]}->{NAME[fin]}"] += 1
    return {k: dict(v) for k, v in out.items()}


# ---------------------------------------------------------------- the town

def town_facts() -> dict:
    rows = []
    for s in SEEDS:
        pr = preferences(Town(), s)
        fav = Counter(p[0] for p in pr)
        rows.append({"seed": s, "first_choices": {p: fav[p] for p in PARTIES},
                     "plurality": plurality(pr, PARTIES, tie_order(s)), "instant_runoff": instant_runoff(pr, PARTIES),
                     "condorcet": condorcet_winner(pr, PARTIES), "borda": borda_scores(pr, PARTIES),
                     "centre_beats_left": head_to_head(pr, "Centre", "Left")[0],
                     "centre_beats_right": head_to_head(pr, "Centre", "Right")[0],
                     "right_beats_left": head_to_head(pr, "Right", "Left")[0],
                     "centre_fans_prefer_left": sum(1 for p in pr if p[0] == "Centre" and p[1] == "Left")})
    borda_w = Counter(max(r["borda"], key=r["borda"].get) for r in rows)
    return {
        "first_choices_median": {p: med([r["first_choices"][p] for r in rows]) for p in PARTIES},
        "first_choices_range": {p: (min(r["first_choices"][p] for r in rows), max(r["first_choices"][p] for r in rows)) for p in PARTIES},
        "left_biggest": sum(max(r["first_choices"], key=r["first_choices"].get) == "Left" for r in rows),
        "winners_by_rule": {
            "plurality (sincere)": dict(Counter(r["plurality"] for r in rows)),
            "instant runoff": dict(Counter(r["instant_runoff"] for r in rows)),
            "Borda": dict(borda_w),
            "Condorcet": dict(Counter(r["condorcet"] or "none" for r in rows)),
        },
        "head_to_head_median": {"Centre vs Left": med([r["centre_beats_left"] for r in rows]),
                                "Centre vs Right": med([r["centre_beats_right"] for r in rows]),
                                "Right vs Left": med([r["right_beats_left"] for r in rows])},
        "centre_fans_prefer_left_share": sum(r["centre_fans_prefer_left"] for r in rows) / sum(r["first_choices"]["Centre"] for r in rows),
        "enp_sincere_median": med([effective_parties(r["first_choices"]) for r in rows]),
    }


# ---------------------------------------------------------------- experiment 1

def exp1(runs) -> dict:
    rows = runs["e1"]
    conv = json.loads((RESULTS / "convergence.json").read_text())
    cert = conv["talk_towns"]["default"]
    # cross-check: the fast simulator reproduces every round of every engine run
    mismatches = 0
    for r in rows:
        t = Town()
        pr, ty, order = preferences(t, r["seed"]), types(t, r["seed"]), tie_order(r["seed"])
        v = [p[0] for p in pr]
        for want in r["votes"]:
            mismatches += "".join(x[0] if x != "Centre" else "C" for x in v) != want
            v = step(v, pr, ty, order)
    moved = defaultdict(Counter)
    for r in rows:
        for k, d in moved_by_type(r).items():
            moved[k].update(d)
    return {
        "towns": len(rows), "rounds": len(rows[0]["votes"]) - 1,
        "winner_final": dict(Counter(r["winners"][-1] for r in rows)),
        "winner_round0": dict(Counter(r["winners"][0] for r in rows)),
        "last_vote_change_round": dict(Counter(last_change(r["votes"]) for r in rows)),
        "switchers_round1_median": med([switches(r)[0] for r in rows]),
        "round0_median": {p: med([r["counts"][0][p] for r in rows]) for p in PARTIES},
        "final_median": {p: med([r["counts"][-1][p] for r in rows]) for p in PARTIES},
        "final_range": {p: (min(r["counts"][-1][p] for r in rows), max(r["counts"][-1][p] for r in rows)) for p in PARTIES},
        "enp_round0_median": med([effective_parties(r["counts"][0]) for r in rows]),
        "enp_final_median": med([effective_parties(r["counts"][-1]) for r in rows]),
        "certified_frozen_from_round1": sum(c["certified"] for c in cert),
        "smallest_gaps_round0": (min(c["gaps0"][0] for c in cert), min(c["gaps0"][1] for c in cert)),
        "smallest_gaps_round1": (min(c["gaps1"][0] for c in cert), min(c["gaps1"][1] for c in cert)),
        "fast_simulator_round_mismatches": mismatches,
        "final_vote_by_type_all_towns": {k: dict(v.most_common()) for k, v in moved.items()},
    }


# ---------------------------------------------------------------- experiment 2

def exp2(runs) -> dict:
    table = []
    engine_mismatch = engine_checked = 0
    for mix in all_mixes():
        t = Town(mix=mix)
        name = mix_name(mix)
        res = []
        for s in SEEDS:
            pr, ty, order = preferences(t, s), types(t, s), tie_order(s)
            hist, cyc = simulate(pr, ty, order, rounds=100)
            c = counts_of(hist[-1], order)
            w = max(order, key=lambda p: (c[p], -order.index(p)))
            moved_pivots = sum(1 for i, k in enumerate(ty) if k == "pivot" and any(h[i] != hist[0][i] for h in hist))
            res.append({"winner": w, "counts": c, "settle": len(hist) - 1 if cyc == 0 else None, "cycle": cyc,
                        "moved_pivots": moved_pivots, "round0_second": sorted(order, key=lambda p: -counts_of(hist[0], order)[p])[1]})
        for r in runs.get(f"e2_check_{name}", []):
            engine_checked += 1
            pr, ty, order = preferences(t, r["seed"]), types(t, r["seed"]), tie_order(r["seed"])
            v = [p[0] for p in pr]
            for want in r["votes"]:
                engine_mismatch += "".join("C" if x == "Centre" else x[0] for x in v) != want
                v = step(v, pr, ty, order)
        m = dict(mix)
        wins = Counter(x["winner"] for x in res)
        table.append({"mix": name, **{k: round(v * 100) for k, v in m.items()},
                      "anchored": round((m["sincere"] + m["pivot"]) * 100),
                      "left_wins": wins["Left"], "right_wins": wins["Right"], "centre_wins": wins["Centre"],
                      "left_median": med([x["counts"]["Left"] for x in res]),
                      "right_median": med([x["counts"]["Right"] for x in res]),
                      "centre_median": med([x["counts"]["Centre"] for x in res]),
                      "enp_median": round(med([effective_parties(x["counts"]) for x in res]), 3),
                      "max_settle_round": max(x["settle"] for x in res if x["settle"] is not None) if any(x["settle"] is not None for x in res) else None,
                      "cycles": sum(1 for x in res if x["cycle"]),
                      "moved_pivots": sum(x["moved_pivots"] for x in res),
                      "upsets_when_centre_second_in_round0": sum(1 for x in res if x["winner"] == "Centre" and x["round0_second"] == "Centre")})
    with (RESULTS / "mixes.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    # does splitting the anchored share between sincere and pivot matter?
    by_anchor = defaultdict(list)
    for row in table:
        by_anchor[(row["frontrunner"], row["copycat"])].append(row["left_median"])
    spread = max(max(v) - min(v) for v in by_anchor.values())
    total = len(table) * len(SEEDS)
    upsets = [row for row in table if row["left_wins"] < len(SEEDS)]
    return {"mixes": len(table), "elections": total,
            "left_wins": sum(r["left_wins"] for r in table), "right_wins": sum(r["right_wins"] for r in table),
            "centre_wins": sum(r["centre_wins"] for r in table),
            "mixes_where_left_always_wins": sum(r["left_wins"] == len(SEEDS) for r in table),
            "upset_mixes": [{k: r[k] for k in ("mix", "left_wins", "right_wins", "centre_wins")} for r in upsets],
            "cycles": sum(r["cycles"] for r in table), "max_settle_round": max(r["max_settle_round"] for r in table),
            "pivots_that_ever_moved": sum(r["moved_pivots"] for r in table),
            "max_left_median_spread_across_sincere_pivot_splits": spread,
            "left_median_range": (min(r["left_median"] for r in table), max(r["left_median"] for r in table)),
            "centre_median_range": (min(r["centre_median"] for r in table), max(r["centre_median"] for r in table)),
            "engine_check_runs": engine_checked, "engine_check_round_mismatches": engine_mismatch}


# ---------------------------------------------------------------- experiment 3

def exp3(runs) -> dict:
    out = {}
    e1 = runs["e1"]
    for walking in (True, False):
        for r_ in [FULL] + RADII:
            rows = e1 if r_ == FULL else runs.get(f"e3_r{r_}_{'walk' if walking else 'still'}", [])
            if not rows:
                continue
            key = f"{'full' if r_ == FULL else r_}_{'walk' if walking else 'still'}"
            sw = [switches(r) for r in rows]
            n = len(rows[0]["votes"][0])
            cop_left = []
            for r in rows:   # copycats' round-1 vote = the most common favourite in their neighbourhood
                idx = [i for i, t in enumerate(r["types"]) if t == "c"]
                cop_left.append(sum(r["votes"][1][i] == "L" for i in idx) / len(idx))
            periods = Counter(period(r["votes"]) for r in rows)
            out[key] = {
                "radius": r_, "walking": walking, "towns": len(rows),
                "mean_neighbours": round(st.mean(st.mean(r["mean_neighbours"][1:]) for r in rows), 1),
                "winner_final": dict(Counter(r["winners"][-1] for r in rows)),
                "left_win_share": sum(r["winners"][-1] == "Left" for r in rows) / len(rows),
                "winner_same_last10": sum(len(set(r["winners"][-TAIL:])) == 1 for r in rows),
                "winner_changes_median": med([sum(r["winners"][t] != r["winners"][t - 1] for t in range(1, len(r["winners"]))) for r in rows]),
                "votes_frozen_last10": sum(all(x == 0 for x in s[-TAIL:]) for s in sw),
                "switch_share_last10_median": med([st.mean(s[-TAIL:]) / n for s in sw]),
                "end_period": {str(k): v for k, v in periods.items()},
                "final_median": {p: med([r["counts"][-1][p] for r in rows]) for p in PARTIES},
                "enp_final_median": round(med([effective_parties(r["counts"][-1]) for r in rows]), 3),
                "copycats_seeing_left_round1_median": round(med(cop_left), 3),
                "lead_final_median": med([sorted(r["counts"][-1].values())[-1] - sorted(r["counts"][-1].values())[-2] for r in rows]),
                "degree_hist_round1_pooled": dict(sorted(sum((Counter({int(k): v for k, v in r["degree_hist_round1"].items()}) for r in rows), Counter()).items())),
            }
    return out


# ---------------------------------------------------------------- experiment 4

def exp4(runs) -> dict:
    out = {}
    for f in FOLLOWERS:
        rows = runs.get(f"e4_f{f}", [])
        if not rows:
            continue
        party = E4_PARTY[0]
        conv = defaultdict(int)
        for r in rows:
            for t, fav, fin in zip(r["types"], r["favourites"], r["votes"][-1]):
                if t != "m" and fav != party and fin == party:
                    conv[TYPE[t]] += 1
        out[f"f{f}"] = {
            "followers_per_member": f, "towns": len(rows),
            "extra_links": rows[0]["persistent_edges"],
            "member_votes_heard_per_listener": round(rows[0]["persistent_edges"] / (len(rows[0]["types"]) - rows[0]["types"].count("m")), 2),
            "winner_final": dict(Counter(r["winners"][-1] for r in rows)),
            "party_win_share": sum(r["winners"][-1] == E4_PARTY for r in rows) / len(rows),
            "party_wins_all_last10": sum(all(w == E4_PARTY for w in r["winners"][-TAIL:]) for r in rows),
            "party_final_median": med([r["counts"][-1][E4_PARTY] for r in rows]),
            "party_final_iqr": (q([r["counts"][-1][E4_PARTY] for r in rows], .25), q([r["counts"][-1][E4_PARTY] for r in rows], .75)),
            "final_median": {p: med([r["counts"][-1][p] for r in rows]) for p in PARTIES},
            "converts_by_type_mean_per_town": {k: round(v / len(rows), 1) for k, v in sorted(conv.items())},
        }
    return {"radius": E4_RADIUS, "party": E4_PARTY, "settings": out}


CHECKPOINTS = [1, 10, 20, 40, 70, 100, 150]


def exp3_checks(runs) -> dict:
    """Long runs (150 rounds, walking) and the 301-voter runs where front-runners are not sticky."""
    long_ = {}
    for r_ in LONG_RADII:
        rows = runs.get(f"e3long_r{r_}_walk", [])
        if not rows:
            continue
        n = len(rows[0]["winners"]) - 1
        long_[str(r_)] = {
            "towns": len(rows), "rounds": n,
            "winners_at": {str(t): dict(Counter(r["winners"][t] for r in rows)) for t in CHECKPOINTS if t <= n},
            "median_votes_at": {str(t): {p: med([r["counts"][t][p] for r in rows]) for p in PARTIES} for t in CHECKPOINTS if t <= n},
            "left_win_share_by_round": [sum(r["winners"][t] == "Left" for r in rows) / len(rows) for t in range(n + 1)],
            "winner_same_last50": sum(len(set(r["winners"][-50:])) == 1 for r in rows),
            "switch_share_last10_median": med([st.mean(switches(r)[-TAIL:]) / len(r["types"]) for r in rows]),
        }
    odd = {}
    for r_ in RADII:
        rows = runs.get(f"e3odd_r{r_}_walk", [])
        if rows:
            odd[str(r_)] = {"towns": len(rows), "winner_final": dict(Counter(r["winners"][-1] for r in rows)),
                            "final_median": {p: med([r["counts"][-1][p] for r in rows]) for p in PARTIES},
                            "winner_same_last10": sum(len(set(r["winners"][-TAIL:])) == 1 for r in rows),
                            "votes_frozen_last10": sum(all(x == 0 for x in switches(r)[-TAIL:]) for r in rows)}
    return {"long_runs": long_, "voters_301": odd}


def exp4_checks(runs) -> dict:
    odd, long_ = {}, {}
    for f in FOLLOWERS:
        rows = runs.get(f"e4odd_f{f}", [])
        if rows:
            odd[f"f{f}"] = {"winner_final": dict(Counter(r["winners"][-1] for r in rows)),
                            "party_final_median": med([r["counts"][-1][E4_PARTY] for r in rows])}
    for f in LONG_FOLLOWERS:
        rows = runs.get(f"e4long_f{f}", [])
        if rows:
            n = len(rows[0]["winners"]) - 1
            long_[f"f{f}"] = {"winners_at": {str(t): dict(Counter(r["winners"][t] for r in rows)) for t in CHECKPOINTS if t <= n},
                              "party_median_at": {str(t): med([r["counts"][t][E4_PARTY] for r in rows]) for t in CHECKPOINTS if t <= n},
                              "party_wins_every_round_101_150": sum(all(w == E4_PARTY for w in r["winners"][101:]) for r in rows)}
    base = runs.get(f"e3_r{E4_RADIUS}_walk", [])
    return {"voters_301": odd, "long_runs": long_,
            "no_minority_same_radius": {"winner_final": dict(Counter(r["winners"][-1] for r in base)),
                                        "party_final_median": med([r["counts"][-1][E4_PARTY] for r in base]) if base else None}}


def main() -> None:
    runs = load_runs()
    summary = {"town": town_facts(), "exp1": exp1(runs), "exp2": exp2(runs), "exp3": exp3(runs), "exp4": exp4(runs),
               "exp3_checks": exp3_checks(runs), "exp4_checks": exp4_checks(runs),
               "convergence": {k: v for k, v in json.loads((RESULTS / "convergence.json").read_text()).items() if k != "talk_towns"}}
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1))
    lines = ["# Results summary", "", "Generated by analyse.py from results/runs.jsonl and the fast simulator. "
             "Medians over the 30 towns unless stated.", ""]
    for section, body in summary.items():
        lines += [f"## {section}", "", "```", json.dumps(body, indent=1)[:20000], "```", ""]
    (RESULTS / "summary.md").write_text("\n".join(lines))
    print(json.dumps({k: v for k, v in summary.items() if k != "convergence"}, indent=1)[:6000])


if __name__ == "__main__":
    main()
