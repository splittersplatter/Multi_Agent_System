"""Echo chambers under strategic party campaigns.

100 agents: 88 residents in three spatial chambers (A 34, B 30, C 24) plus four
campaigners per party. Each chamber is 65% loyal to its party. Residents are 60% conformists (vote the plurality of the
ballots they can see through trusted sensors) and 40% committed partisans.
Campaigners have stronger powers than residents: faster movement (0.06/round),
a wide sensing radius (0.30, i.e. local polling), the electorate roster, and the
right to add their own outgoing "follow" edges (max 6 live, 2 new per round),
which put the campaigner's ballot in front of chosen voters.

Each party picks one of five strategies (see plugins/echo_campaign.py). We run
the full 5x5x5 factorial over three seeds, then a showcase set with GIFs, so
every party's payoff is known against every opponent combination: best
responses, pure Nash equilibria and the echo-chamber metrics follow from it.
"""

from __future__ import annotations

import itertools
import math
import random
import statistics as stats
from collections import Counter

import numpy as np

from common import DOCS, pin_uniform_walk, INK, INK2, MUTED, PALETTE, Style, plt, run_config, save_fig, save_gif, save_snapshots, share_plot, write_json

OUT = DOCS / "echo_chambers"
PARTIES = ["A", "B", "C"]
COLORS = {"A": PALETTE[0], "B": PALETTE[1], "C": PALETTE[2]}
CHAMBERS = {"A": ((0.22, 0.28), 34), "B": ((0.78, 0.28), 30), "C": ((0.50, 0.78), 24)}
RIVAL = {"A": "B", "B": "A", "C": "A"}  # largest rival chamber
STRATEGIES = ["passive", "fortify", "infiltrate", "bridge", "broadcast"]
ROUNDS = 40
SEEDS = [1, 2, 3]
SHOW_SEED = 1
LAST = 10  # payoff window: mean share over the last 10 rounds
STRAT_SHAPES = {"fortify": "s", "infiltrate": "^", "bridge": "D", "broadcast": "P", "passive": "v"}


LOYAL = 0.65          # share of a chamber whose sincere favourite is the chamber's party
RESIDENT_RADIUS = 0.08


def layout(seed: int = 5):
    rng = random.Random(seed)
    people, chamber_of = [], {}
    n = 0
    for party, ((cx, cy), size) in CHAMBERS.items():
        loyal = round(LOYAL * size)
        others = [p for p in PARTIES if p != party]
        firsts = [party] * loyal + [others[i % 2] for i in range(size - loyal)]
        rng.shuffle(firsts)
        for first in firsts:
            rest = [p for p in PARTIES if p != first]
            rng.shuffle(rest)
            pid = f"r{n:02d}"
            n += 1
            chamber_of[pid] = party
            people.append({"id": pid, "group": "conformist" if rng.random() < 0.6 else "committed",
                           "preference": [first] + rest,
                           "position": [round(min(0.98, max(0.02, rng.gauss(cx, 0.09))), 4),
                                        round(min(0.98, max(0.02, rng.gauss(cy, 0.09))), 4)]})
    campaigners = []
    for party, ((cx, cy), _) in CHAMBERS.items():
        for i in range(4):
            cid = f"camp{party}{i}"
            campaigners.append(cid)
            rest = [p for p in PARTIES if p != party]
            people.append({"id": cid, "group": f"camp_{party}", "preference": [party] + rest,
                           "position": [round(cx + rng.uniform(-0.04, 0.04), 4), round(cy + rng.uniform(-0.04, 0.04), 4)]})
    return people, chamber_of, campaigners


PEOPLE, CHAMBER_OF, CAMPAIGNERS = layout()


def build(strategies: dict, seed: int, max_active: int = 6, new_per_round: int = 2) -> dict:
    groups = {
        "conformist": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.01,
                       "proximity_radius": RESIDENT_RADIUS, "capabilities": {"sense_public_ballots": True}},
        "committed": {"voting": "sincere", "movement": "random_walk", "max_step": 0.01, "proximity_radius": RESIDENT_RADIUS},
    }
    for party in PARTIES:
        strategy = strategies[party]
        groups[f"camp_{party}"] = {
            "voting": "sincere", "movement": "python:echo_campaign:move", "max_step": 0.06,
            "graph": "python:echo_campaign:link", "proximity_radius": 0.30,
            "parameters": {"strategy": strategy, "party": party, "home": list(CHAMBERS[party][0]),
                           "rival": list(CHAMBERS[RIVAL[party]][0]), "max_step": 0.06, "max_active": max_active,
                           "new_per_round": new_per_round, "campaigners": CAMPAIGNERS},
            "capabilities": {"sense_public_ballots": True, "observe_electorate": True, "modify_persistent_edges": True},
        }
    return pin_uniform_walk({"parties": PARTIES, "k": 1, "seed": seed, "rounds": ROUNDS, "groups": groups,
            "network": {"radius": RESIDENT_RADIUS}, "people": PEOPLE})


def key(s):
    return f"A={s['A']} B={s['B']} C={s['C']}"


# ------------------------------------------------------------------ metrics
def payoff(run, party):
    return stats.mean(run.shares(party)[-LAST:])


def purity(frame):
    """Share of residents voting their own chamber's party (100% = sealed echo chambers)."""
    ballots = dict(frame.ballots)
    return stats.mean(ballots[p][0] == c for p, c in CHAMBER_OF.items())


def exposure(frame):
    """Share of conformists whose trusted sensors show at least one ballot unlike their own."""
    ballots = dict(frame.ballots)
    conformists = {p["id"] for p in PEOPLE if p["group"] == "conformist"}
    seen = {p: set() for p in conformists}
    for observer, sender, source, _, ballot in frame.ballot_sensors:
        if observer in seen:
            seen[observer].add(ballot[0])
    return stats.mean(any(b != ballots[p][0] for b in seen[p]) for p in conformists)


def campaign_edges(frame):
    return sum(1 for a, b in frame.persistent_edges if a in CAMPAIGNERS)


def style(run, title):
    strategies = {party: run.config["groups"][f"camp_{party}"]["parameters"]["strategy"] for party in PARTIES}
    groups = {p["id"]: p["group"] for p in PEOPLE}

    def profile(p):
        g = groups[p]
        if g.startswith("camp_"):
            party = g[-1]
            return f"{party} campaigner ({strategies[party]})"
        return "conformist resident" if g == "conformist" else "committed partisan"
    shapes = {"conformist resident": "o", "committed partisan": "h"}
    sizes = {"conformist resident": 26, "committed partisan": 26}
    for party in PARTIES:
        shapes[f"{party} campaigner ({strategies[party]})"] = STRAT_SHAPES[strategies[party]]
        sizes[f"{party} campaigner ({strategies[party]})"] = 90

    def edges(frame):
        return [(a, b, COLORS[a[4]]) for a, b in frame.persistent_edges if a in CAMPAIGNERS]
    return Style(profile, shapes, COLORS, sizes, edge_layers=("proximity",), highlight_edges=edges, title=title)


# ------------------------------------------------------------------ analysis
def nash(table):
    """Pure-strategy Nash equilibria of the 3-party game with payoff = own mean late share."""
    eq = []
    for combo in itertools.product(STRATEGIES, repeat=3):
        stable = True
        for i, party in enumerate(PARTIES):
            here = table[combo][party]
            for alt in STRATEGIES:
                dev = list(combo)
                dev[i] = alt
                if table[tuple(dev)][party] > here + 1e-9:
                    stable = False
                    break
            if not stable:
                break
        if stable:
            eq.append(combo)
    return eq


def regret(table, combo):
    """Largest gain any single party could get by switching strategy (0 = exact Nash)."""
    worst = 0.0
    for i, party in enumerate(PARTIES):
        for alt in STRATEGIES:
            dev = list(combo)
            dev[i] = alt
            worst = max(worst, table[tuple(dev)][party] - table[combo][party])
    return worst


def best_response_path(table, start=("passive",) * 3, limit=30):
    """Sequential best-response dynamics (A, then B, then C); stops at a fixed point or a repeat."""
    path, combo = [start], start
    for _ in range(limit):
        for i, party in enumerate(PARTIES):
            options = {s: tuple(list(combo[:i]) + [s] + list(combo[i + 1:])) for s in STRATEGIES}
            best = max(STRATEGIES, key=lambda s: table[options[s]][party])
            if table[options[best]][party] > table[combo][party] + 1e-9:
                combo = options[best]
        if combo in path:
            return path + [combo], combo == path[-1]
        path.append(combo)
    return path, False


def game_analysis(table):
    ranked = sorted(table, key=lambda c: regret(table, c))
    path, converged = best_response_path(table)
    return {
        "approximate_equilibria": [{"A": c[0], "B": c[1], "C": c[2], "epsilon": regret(table, c), "payoffs": table[c]}
                                   for c in ranked[:8]],
        "best_response_path": [list(c) for c in path], "best_response_converged": converged,
    }


def analyse_saved():
    """Recompute the game analysis from an existing summary.json (no simulations)."""
    import json
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    table = {}
    for name, value in summary["factorial"].items():
        combo = tuple(part.split("=")[1] for part in name.split())
        table[combo] = value["payoffs"]
    summary["game"] = game_analysis(table)
    write_json(OUT / "summary.json", summary)
    equilibrium_figure(summary["game"], table)
    purity_tab = {c: summary["factorial"][f"A={c[0]} B={c[1]} C={c[2]}"]["chamber_purity"] for c in table}
    exposure_tab = {c: summary["factorial"][f"A={c[0]} B={c[1]} C={c[2]}"]["cross_exposure"] for c in table}
    wins = {c: Counter(summary["factorial"][f"A={c[0]} B={c[1]} C={c[2]}"]["winners"]) for c in table}
    purity_figure(table, purity_tab, exposure_tab)
    symmetric_figure(table, wins, purity_tab, exposure_tab)
    return summary["game"]


def equilibrium_figure(game, table):
    rows = game["approximate_equilibria"][:8]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.4), gridspec_kw={"width_ratios": [1.15, 1]})
    labels = [f"A {r['A']} / B {r['B']} / C {r['C']}" for r in rows]
    eps = [r["epsilon"] * 100 for r in rows]
    axes[0].barh(range(len(rows)), eps, color=PALETTE[6], height=0.6)
    axes[0].set_yticks(range(len(rows)), labels, fontsize=8.5)
    axes[0].invert_yaxis()
    axes[0].axvline(1.0, color=INK2, ls="--", lw=1)
    axes[0].text(1.02, len(rows) - 0.6, "1 voter", fontsize=8, color=INK2)
    for i, e in enumerate(eps):
        axes[0].text(e + 0.03, i, f"{e:.2f}", va="center", fontsize=8)
    axes[0].set_xlabel("ε: best unilateral gain available (pts of vote share)")
    axes[0].set_title("Most stable strategy profiles (ε = 0 would be an exact Nash equilibrium)", fontsize=10)
    axes[0].grid(axis="y", visible=False)
    path = [tuple(c) for c in game["best_response_path"]]
    for j, p in enumerate(PARTIES):
        axes[1].plot(range(len(path)), [table[c][p] * 100 for c in path], marker="o", lw=2, color=COLORS[p], label=p)
    axes[1].set_xticks(range(len(path)), ["\n".join(s[:5] for s in c) for c in path], fontsize=7.5)
    axes[1].set_ylabel("Late vote share (%)")
    axes[1].set_title("Best-response dynamics from all-passive " + ("(converges)" if game["best_response_converged"] else "(cycles)"), fontsize=10)
    axes[1].legend(fontsize=8)
    save_fig(fig, OUT / "e08_equilibria.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    table, wins, purity_tab, exposure_tab = {}, {}, {}, {}
    showcase_runs = {}
    combos = list(itertools.product(STRATEGIES, repeat=3))
    for combo in combos:
        strategies = dict(zip(PARTIES, combo))
        runs = [run_config(f"echo_{'_'.join(combo)}_s{s}", build(strategies, s)) for s in SEEDS]
        table[combo] = {p: stats.mean(payoff(r, p) for r in runs) for p in PARTIES}
        wins[combo] = Counter(r.frames[-1].winner for r in runs)
        purity_tab[combo] = stats.mean(purity(r.frames[-1]) for r in runs)
        exposure_tab[combo] = stats.mean(exposure(r.frames[-1]) for r in runs)
        if combo in SHOWCASE_COMBOS:
            showcase_runs[combo] = runs

    base = table[("passive",) * 3]
    gains = {p: {s: stats.mean(table[c][p] - base[p] for c in combos if c[PARTIES.index(p)] == s) for s in STRATEGIES}
             for p in PARTIES}
    best_response = {}
    for i, party in enumerate(PARTIES):
        counts = Counter()
        for others in itertools.product(STRATEGIES, repeat=2):
            def with_s(s):
                c = list(others)
                c.insert(i, s)
                return tuple(c)
            counts[max(STRATEGIES, key=lambda s: table[with_s(s)][party])] += 1
        best_response[party] = dict(counts)
    equilibria = nash(table)
    symmetric = {s: table[(s, s, s)] for s in STRATEGIES}

    # budget sweep for the underdog C against fortifying rivals
    sweep = {}
    for strategy in ("infiltrate", "bridge", "broadcast", "fortify"):
        for cap in (2, 4, 6, 10, 14):
            runs = [run_config("sweep", build({"A": "fortify", "B": "fortify", "C": strategy}, s, max_active=cap)) for s in SEEDS]
            sweep[(strategy, cap)] = stats.mean(payoff(r, "C") for r in runs)

    summary = {
        "baseline_passive_payoffs": base,
        "mean_gain_by_strategy": gains,
        "best_response_counts": best_response,
        "pure_nash_equilibria": [{"A": c[0], "B": c[1], "C": c[2], "payoffs": table[c], "winners": dict(wins[c]),
                                  "chamber_purity": purity_tab[c], "cross_exposure": exposure_tab[c]} for c in equilibria],
        "symmetric_profiles": {s: {"payoffs": v, "winners": dict(wins[(s, s, s)]), "chamber_purity": purity_tab[(s, s, s)],
                                   "cross_exposure": exposure_tab[(s, s, s)]} for s, v in symmetric.items()},
        "underdog_C_budget_sweep": {f"{k[0]}|{k[1]}": v for k, v in sweep.items()},
        "factorial": {key(dict(zip(PARTIES, c))): {"payoffs": table[c], "winners": dict(wins[c]),
                                                   "chamber_purity": purity_tab[c], "cross_exposure": exposure_tab[c]}
                      for c in combos},
        "game": game_analysis(table),
        "runs": len(combos) * len(SEEDS) + len(sweep) * len(SEEDS),
        "seeds": SEEDS, "rounds": ROUNDS, "payoff": f"mean first-choice share over the last {LAST} rounds",
    }
    write_json(OUT / "summary.json", summary)
    figures(table, wins, purity_tab, exposure_tab, gains, best_response, equilibria, sweep, showcase_runs, base)
    equilibrium_figure(summary["game"], table)
    print("baseline", base)
    print("gains", {p: {s: round(v, 3) for s, v in g.items()} for p, g in gains.items()})
    print("best responses", best_response)
    print("nash", [(c, {p: round(v, 3) for p, v in table[c].items()}) for c in equilibria])
    print("symmetric", {s: {p: round(x, 3) for p, x in v.items()} for s, v in symmetric.items()})
    print("sweep", {k: round(v, 3) for k, v in sweep.items()})


SHOWCASE_COMBOS = [
    ("passive", "passive", "passive"),
    ("fortify", "fortify", "fortify"),
    ("infiltrate", "infiltrate", "infiltrate"),
    ("bridge", "bridge", "bridge"),
    ("broadcast", "broadcast", "broadcast"),
    ("fortify", "infiltrate", "bridge"),
    ("passive", "passive", "infiltrate"),
    ("fortify", "fortify", "bridge"),
]


def symmetric_figure(table, wins, purity_tab, exposure_tab):
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
    x = np.arange(len(STRATEGIES))
    for i, p in enumerate(PARTIES):
        axes[0].bar(x + (i - 1) * 0.26, [table[(s, s, s)][p] * 100 for s in STRATEGIES], 0.24, color=COLORS[p], label=p)
    for j, s in enumerate(STRATEGIES):
        w = wins[(s, s, s)]
        axes[0].text(j, 52, "wins " + " ".join(f"{k}{v}" for k, v in sorted(w.items())), ha="center", fontsize=7.5)
    axes[0].set_xticks(x, STRATEGIES)
    axes[0].set_ylim(0, 56)
    axes[0].set_ylabel("Late vote share (%)")
    axes[0].set_title("All three parties play the same strategy")
    axes[0].legend(fontsize=8, loc="upper left", bbox_to_anchor=(0.0, 0.9), ncol=3)
    axes[0].grid(axis="x", visible=False)
    axes[1].bar(x - 0.2, [purity_tab[(s, s, s)] * 100 for s in STRATEGIES], 0.38, color=PALETTE[6], label="chamber purity")
    axes[1].bar(x + 0.2, [exposure_tab[(s, s, s)] * 100 for s in STRATEGIES], 0.38, color=PALETTE[3], label="cross-cutting exposure")
    axes[1].set_xticks(x, STRATEGIES)
    axes[1].set_ylabel("% of residents")
    axes[1].set_title("Echo-chamber strength at round 40")
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="x", visible=False)
    save_fig(fig, OUT / "e03_symmetric_profiles.png")


def purity_figure(table, purity_tab, exposure_tab):
    combos = list(table)
    fig, ax = plt.subplots(figsize=(8, 5))
    for c in combos:
        winner = max(PARTIES, key=lambda p: table[c][p])
        ax.scatter(exposure_tab[c] * 100, purity_tab[c] * 100, color=COLORS[winner], s=22, alpha=0.75)
    for c in sorted(table, key=lambda c: regret(table, c))[:2]:
        ax.scatter(exposure_tab[c] * 100, purity_tab[c] * 100, s=170, facecolors="none", edgecolors=INK, lw=1.5)
    ax.scatter([exposure_tab[("passive",) * 3] * 100], [purity_tab[("passive",) * 3] * 100], marker="X", s=140, color=INK)
    ax.annotate("all passive", (exposure_tab[("passive",) * 3] * 100, purity_tab[("passive",) * 3] * 100), xytext=(8, -12), textcoords="offset points", fontsize=8.5)
    ax.set_xlabel("Cross-cutting exposure (% conformists seeing another party)")
    ax.set_ylabel("Chamber purity (% voting own chamber's party)")
    ax.set_title("125 strategy profiles: colour = leading party; rings = most stable profiles (ε < 0.25 pts)")
    ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=COLORS[p], label=f"{p} leads") for p in PARTIES], fontsize=8)
    save_fig(fig, OUT / "e04_purity_vs_exposure.png")



def figures(table, wins, purity_tab, exposure_tab, gains, best_response, equilibria, sweep, showcase_runs, base):
    combos = list(table)
    # 1. mean gain by own strategy, per party
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(STRATEGIES))
    for i, p in enumerate(PARTIES):
        vals = [gains[p][s] * 100 for s in STRATEGIES]
        ax.bar(x + (i - 1) * 0.26, vals, 0.24, color=COLORS[p], label=f"party {p}")
        for j, v in enumerate(vals):
            ax.text(j + (i - 1) * 0.26, v + (0.3 if v >= 0 else -1.2), f"{v:+.1f}", ha="center", fontsize=7.5)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, STRATEGIES)
    ax.set_ylabel("Δ late vote share vs all-passive (pts)")
    ax.set_title("Average payoff of each campaign strategy (averaged over all 25 opponent combinations)")
    ax.legend(fontsize=8.5)
    ax.grid(axis="x", visible=False)
    save_fig(fig, OUT / "e01_strategy_gains.png")

    # 2. payoff heatmaps: party's own strategy vs. (other two) for each party
    fig, axes = plt.subplots(1, 3, figsize=(19, 6.2))
    for ax, (i, p) in zip(axes, enumerate(PARTIES)):
        others = list(itertools.product(STRATEGIES, repeat=2))
        M = np.zeros((len(STRATEGIES), len(others)))
        for a, s in enumerate(STRATEGIES):
            for b, o in enumerate(others):
                c = list(o)
                c.insert(i, s)
                M[a, b] = table[tuple(c)][p] * 100
        im = ax.imshow(M, cmap="viridis", aspect="auto")
        best = M.argmax(0)
        for b in range(len(others)):
            ax.add_patch(plt.Rectangle((b - 0.5, best[b] - 0.5), 1, 1, fill=False, edgecolor="white", lw=1.6))
        ax.set_yticks(range(len(STRATEGIES)), STRATEGIES)
        other_names = [q for q in PARTIES if q != p]
        ax.set_xticks(range(len(others)), [f"{o[0][:3]}/{o[1][:3]}" for o in others], rotation=90, fontsize=7)
        ax.set_xlabel(f"Opponents' strategies ({other_names[0]}/{other_names[1]})")
        ax.set_title(f"Party {p}: late share (%) — white box = best response", fontsize=10)
        ax.grid(False)
        fig.colorbar(im, ax=ax, fraction=0.03)
    save_fig(fig, OUT / "e02_payoff_heatmaps.png")

    symmetric_figure(table, wins, purity_tab, exposure_tab)

    purity_figure(table, purity_tab, exposure_tab)

    # 5. underdog budget sweep
    fig, ax = plt.subplots(figsize=(8, 4))
    for (strategy), col in zip(("infiltrate", "bridge", "broadcast", "fortify"), (PALETTE[0], PALETTE[1], PALETTE[3], PALETTE[2])):
        caps = (2, 4, 6, 10, 14)
        ax.plot(caps, [sweep[(strategy, c)] * 100 for c in caps], marker="o", lw=2, color=col, label=strategy)
    ax.axhline(table[("fortify", "fortify", "passive")]["C"] * 100, color=MUTED, ls="--", lw=1)
    ax.text(2, table[("fortify", "fortify", "passive")]["C"] * 100 + 0.4, "C passive", fontsize=8, color=INK2)
    ax.set_xlabel("Max live edges per campaigner")
    ax.set_ylabel("C late vote share (%)")
    ax.set_title("Underdog C vs two fortifying rivals: strategy × edge budget")
    ax.legend(fontsize=8.5)
    save_fig(fig, OUT / "e05_underdog_budget.png")

    # 6. time series, network GIFs and snapshots for showcase profiles
    fig, axes = plt.subplots(2, 4, figsize=(19, 7.5), sharey=True)
    for ax, combo in zip(axes.flat, SHOWCASE_COMBOS):
        runs = showcase_runs[combo]
        for p in PARTIES:
            arr = np.array([r.shares(p) for r in runs])
            ax.plot(arr.mean(0), color=COLORS[p], lw=2, label=p)
            ax.fill_between(range(arr.shape[1]), arr.min(0), arr.max(0), color=COLORS[p], alpha=0.12, lw=0)
        ax.set_title(f"A={combo[0]}  B={combo[1]}  C={combo[2]}", fontsize=9)
        ax.set_ylim(0, 0.6)
        ax.set_xlabel("Round")
    axes[0][0].set_ylabel("Vote share")
    axes[1][0].set_ylabel("Vote share")
    axes[0][0].legend(fontsize=8)
    fig.suptitle("Showcase strategy profiles (mean and range over 3 seeds)", x=0.01, ha="left", fontweight="bold")
    save_fig(fig, OUT / "e06_showcase_timeseries.png")
    for combo in SHOWCASE_COMBOS:
        run = showcase_runs[combo][SEEDS.index(SHOW_SEED)]
        name = "_".join(s[:4] for s in combo)
        st = style(run, f"A {combo[0]} | B {combo[1]} | C {combo[2]} ")
        save_gif(run, st, OUT / f"echo_{name}.gif", fps=5, size=5.8)
        save_snapshots(run, st, OUT / f"echo_{name}_snapshots.png", [0, 5, 15, ROUNDS])
    fig, ax = plt.subplots(figsize=(8, 3.8))
    runs = showcase_runs[SHOWCASE_COMBOS[-3]]
    for combo, col in zip(SHOWCASE_COMBOS[:5], PALETTE):
        r = showcase_runs[combo][0]
        ax.plot([purity(f) * 100 for f in r.frames], color=col, lw=2, label="all " + combo[0])
    ax.set_xlabel("Round")
    ax.set_ylabel("Chamber purity (%)")
    ax.set_title("Echo chambers close up under conformity; campaigns pry them open (seed 1)")
    ax.legend(fontsize=8)
    save_fig(fig, OUT / "e07_purity_over_time.png")


if __name__ == "__main__":
    import sys
    if "--analyse" in sys.argv:
        print(analyse_saved())
    else:
        main()
