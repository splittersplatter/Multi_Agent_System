"""Figures for the Part 2 slides, in the style of 'Who wins depends on who you hear'.

Data come from the saved showcase configs and summary.json files; nothing is
re-tuned. Output: docs/suchit_sims/slides/fig_*.png
"""

from __future__ import annotations

import json
import math
import tomllib
from pathlib import Path

import numpy as np

from common import DOCS, PALETTE, plt, run_config
import spatial as sp

OUT = DOCS / "slides"
BG = "#FBFAF6"
INK, INK2, MUTED, GRID = "#14213D", "#3F4756", "#9a9993", "#e4e3df"
PURPLE = "#5B4BC4"
BLUE, ORANGE, GREEN, RED = "#2A78D6", "#EB6834", "#1BAF7A", "#E34948"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
                     "axes.titlecolor": INK, "axes.labelcolor": INK2})


def load(study, name):
    raw = tomllib.loads((DOCS / study / "configs" / f"{name}.toml").read_text(encoding="utf-8"))
    return run_config(name, raw)


def summary(study):
    return json.loads((DOCS / study / "summary.json").read_text(encoding="utf-8"))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def frame_axes(ax):
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect("equal")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("#c8c7c4")


# ---------------------------------------------------------------- experiment 5: watchdog
WD_COL = {"ana": BLUE, "ben": ORANGE, "cyd": PURPLE}


def belief_panel(ax, run, frame, title):
    targets = set(run.config["alignment"]["attack"]["targets"])
    ideals = dict(frame.alignment_ideals)
    ballots = dict(frame.ballots)
    for group, marker, size in (("other", "o", 14), ("attacked", "^", 34)):
        people = [p for p in ideals if p not in sp.CANDIDATES and ((p in targets) == (group == "attacked"))]
        ax.scatter([ideals[p][0] for p in people], [ideals[p][1] for p in people], s=size, marker=marker,
                   c=[WD_COL[ballots[p][0]] for p in people], edgecolors=INK if group == "attacked" else "none", linewidths=0.6)
    for c, xy in sp.CANDIDATES.items():
        ax.scatter(*xy, marker="*", s=260, color=WD_COL[c], edgecolors=INK, linewidths=0.8, zorder=5)
        ax.text(xy[0], xy[1] + 0.05, c.capitalize(), ha="center", fontsize=8.5, fontweight="bold", color=INK)
    counts = dict(frame.counts)
    frame_axes(ax)
    ax.set_title(f"{title}\nAna {counts['ana']} · Ben {counts['ben']} · Cyd {counts['cyd']}", fontsize=9.5, loc="left", color=INK)


def fig_watchdog_setup():
    run = load("watchdog", "W4")
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.1))
    belief_panel(axes[0], run, run.frames[0], "Round 0")
    belief_panel(axes[1], run, run.frames[-1], "Round 30")
    fig.suptitle("Slow drip: 25 swing voters nudged toward Cyd", x=0.02, ha="left", fontweight="bold", color=INK, fontsize=11.5)
    fig.text(0.02, 0.01, "▲ nudged voter   ● other voter   ★ candidate   colour = current vote · belief space, issues 1 and 2",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    save(fig, "fig5a_watchdog_setup.png")


def timeline(ax, run, title):
    s = run.shares("cyd")
    rounds = np.arange(len(s))
    rise = [0] + [s[t] - s[t - 1] for t in range(1, len(s))]
    ax.bar(rounds, np.array(rise) * 100, color="#EDA100", alpha=0.7, width=0.7, label="rise this round (pts)")
    ax.plot(rounds, np.array(s) * 100, color=PURPLE, lw=2.2, label="Cyd's share (%)")
    ax.axhline(5, color="#B07A00", ls=":", lw=1)
    ax.text(29.5, 6, "built-in alarm bar: +5 in one round", ha="right", fontsize=7.5, color="#8a6000")
    one = next((t for t in range(1, len(s)) if s[t] - s[t - 1] > 0.05 + 1e-12), None)
    three = next((t for t in range(1, len(s)) if s[t] - s[max(0, t - 3)] > 0.04 + 1e-12), None)
    t3 = run.frames[-1].detector.first_triple_win_round
    for x, lab, col, y in ((one, "built-in alarm", "#8a6000", 58), (three, "3-round alarm", RED, 52), (t3, "3rd straight win", INK, 46)):
        if x is not None:
            ax.axvline(x, color=col, ls="--", lw=1.1)
            ax.text(x + 0.4, y, f"{lab}: r{x}", fontsize=7.5, color=col)
    if one is None:
        ax.text(29.5, 58, "built-in alarm: never", ha="right", fontsize=7.5, color="#8a6000", fontweight="bold")
    ax.set_ylim(-3, 62)
    ax.set_xlim(-0.5, 30.5)
    ax.set_title(title, fontsize=10, loc="left", color=INK, fontweight="bold")
    ax.set_xlabel("round", fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.grid(axis="x", visible=False)


def fig_watchdog_timelines():
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.5), sharey=True)
    timeline(axes[0], load("watchdog", "W1"), "Blitz: fast and loud")
    timeline(axes[1], load("watchdog", "W4"), "Slow drip: quiet but winning")
    axes[0].legend(fontsize=7.5, loc="center right", frameon=False)
    fig.tight_layout()
    save(fig, "fig5b_watchdog_timelines.png")


def fig_attacker_grid():
    grid = summary("watchdog")["attacker_grid"]
    steps = sorted({float(k.split("|")[0]) for k in grid})
    sizes = sorted({int(k.split("|")[1]) for k in grid})
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.0))
    for ax, key, title in ((axes[0], "engine", "vs built-in alarm (+5 in one round)"),
                           (axes[1], "optimal", "vs 3-round alarm (+4 over 3 rounds)")):
        M = np.array([[sum(o[key] in ("missed", "too late") for o in grid[f"{st}|{n}"]) / len(grid[f"{st}|{n}"])
                       for st in steps] for n in sizes])
        ax.imshow(M, cmap="Purples", vmin=0, vmax=1.2, aspect="auto")
        for i in range(len(sizes)):
            for j in range(len(steps)):
                wins = sum(o["t3"] is not None for o in grid[f"{steps[j]}|{sizes[i]}"])
                txt = f"{M[i, j]:.0%}" if wins else "–"
                ax.text(j, i, txt, ha="center", va="center", fontsize=7.5,
                        color="white" if M[i, j] > 0.5 else INK, fontweight="bold" if M[i, j] > 0 else "normal")
        ax.set_xticks(range(len(steps)), [f"{s:g}" for s in steps], fontsize=7)
        ax.set_yticks(range(len(sizes)), sizes, fontsize=7.5)
        ax.set_xlabel("push per voter per round", fontsize=8)
        ax.set_ylabel("voters pushed", fontsize=8)
        ax.set_title(title, fontsize=9.5, loc="left", color=INK, fontweight="bold")
        ax.grid(False)
    fig.text(0.01, -0.04, "Cell: share of 5 test towns where the attacker wins without being caught first · – = attack never wins",
             fontsize=7.5, color=INK2)
    fig.tight_layout()
    save(fig, "fig5c_attacker_grid.png")


# ---------------------------------------------------------------- experiment 6: spies
FI_COL = {"A": BLUE, "B": PURPLE, "C": ORANGE}


def fig_spies_map():
    run = load("foreign_intelligence", "F2_seed1")
    frame = run.frames[10]
    groups = {p["id"]: p["group"] for p in run.config["people"]}
    pos, ballots = dict(frame.positions), dict(frame.ballots)
    fig, ax = plt.subplots(figsize=(4.6, 4.9))
    for a, b in frame.proximity_edges:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#dcdbd6", lw=0.4, zorder=1)
    for _, s, r, ch, _ in frame.deceptive_reports:
        if ch == "public":
            ax.annotate("", xy=pos[r], xytext=pos[s], arrowprops=dict(arrowstyle="-|>", color=RED, lw=0.9, alpha=0.8, mutation_scale=7), zorder=2)
    for g, marker, size in (("committed", "D", 18), ("trusting", "o", 20), ("sensor", "s", 20), ("spies", "^", 62)):
        people = [p for p in pos if groups[p] == g]
        ax.scatter([pos[p][0] for p in people], [pos[p][1] for p in people], marker=marker, s=size,
                   c=[FI_COL[ballots[p][0]] for p in people], edgecolors=INK if g == "spies" else "none", linewidths=0.8, zorder=4)
    frame_axes(ax)
    counts = dict(frame.counts)
    ax.set_title(f"Round 10 · A {counts['A']} · B {counts['B']} · C {counts['C']}", fontsize=9.5, loc="left", color=INK)
    fig.suptitle("Spy cells with a dossier, one town", x=0.03, ha="left", fontweight="bold", color=INK, fontsize=11.5)
    fig.text(0.03, 0.02, "▲ spy   ● trusts what it's told   ■ checks real votes\n◆ committed   red arrow = a lie this round   colour = vote",
             fontsize=7.8, color=INK2)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    save(fig, "fig6a_spies_map.png")


def fig_spies_results():
    rows = summary("foreign_intelligence")["rows"]
    labels = ["Blind lies\n15 spies", "With dossier\n15 spies", "Dossier +\nchat listening", "Half network\n8 spies"]
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    x = np.arange(len(rows))
    ax.bar(x - 0.19, [r["target_win_rate_control"] * 8 for r in rows], 0.36, color="#c8c7c4", label="silent twin")
    ax.bar(x + 0.19, [r["target_win_rate_attack"] * 8 for r in rows], 0.36, color=PURPLE, label="spies lying")
    for i, r in enumerate(rows):
        ax.text(i + 0.19, r["target_win_rate_attack"] * 8 + 0.15, f"{round(r['target_win_rate_attack'] * 8)}", ha="center", fontsize=10, fontweight="bold", color=INK)
        ax.text(i - 0.19, r["target_win_rate_control"] * 8 + 0.15, f"{round(r['target_win_rate_control'] * 8)}", ha="center", fontsize=9, color=INK2)
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_ylim(0, 8.6)
    ax.set_ylabel("towns B wins (of 8)", fontsize=9)
    ax.set_title("Same 1,500 lies: B's wins by tactic", loc="left", fontweight="bold", fontsize=11, color=INK)
    ax.legend(fontsize=8.5, loc="upper right", frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig6b_spies_results.png")


# ---------------------------------------------------------------- experiment 7: slow persuasion
def fig_persuasion():
    import propaganda as pr
    series = {}
    runs_ctl = [run_config("c", pr.config(pr.SWING[:1], 0.0, "none", s)) for s in pr.SEEDS]
    series["no campaign"] = np.mean([r.shares("cyd") for r in runs_ctl], axis=0)
    names = {"P1": "broad & shallow", "P2": "swing voters", "P3": "opposition core", "P4": "random pushes"}
    for vid, _, targets, step, policy in pr.VARIANTS:
        runs = [run_config(vid, pr.config(targets, step, policy, s)) for s in pr.SEEDS]
        series[names[vid]] = np.mean([r.shares("cyd") for r in runs], axis=0)
    colors = {"no campaign": "#9a9993", "broad & shallow": BLUE, "swing voters": PURPLE, "opposition core": ORANGE, "random pushes": "#EDA100"}
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    nudge = {"opposition core": 2.2, "swing voters": -2.2}
    for name, s in series.items():
        ax.plot(np.arange(len(s)), s * 100, lw=2.4 if name != "no campaign" else 1.6, ls="--" if name == "no campaign" else "-", color=colors[name])
        ax.text(61, s[-1] * 100 + nudge.get(name, 0), f"{name} {s[-1] * 100:.0f}%", fontsize=8, color=colors[name], va="center", fontweight="bold")
    ax.axhline(100 / 3, color="#c8c7c4", lw=0.8)
    ax.set_xlim(0, 60)
    ax.set_ylim(15, 70)
    ax.set_xlabel("round", fontsize=9)
    ax.set_ylabel("Cyd's vote share (%)", fontsize=9)
    ax.set_title("Same budget, four ways to spend it (5 towns each)", loc="left", fontweight="bold", fontsize=11, color=INK)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig7_persuasion.png")


# ---------------------------------------------------------------- experiment 8: echo chambers
EC_COL = {"A": BLUE, "B": ORANGE, "C": GREEN}


def echo_panel(ax, run, frame, title):
    import echo_chambers as ec
    groups = {p["id"]: p["group"] for p in ec.PEOPLE}
    pos, ballots = dict(frame.positions), dict(frame.ballots)
    for a, b in frame.proximity_edges:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#e2e1dc", lw=0.35, zorder=1)
    for a, b in frame.persistent_edges:
        if a in ec.CAMPAIGNERS:
            ax.annotate("", xy=pos[b], xytext=pos[a], arrowprops=dict(arrowstyle="-|>", color=EC_COL[a[4]], lw=0.8, alpha=0.75, mutation_scale=6), zorder=2)
    for g, marker, size in (("conformist", "o", 16), ("committed", "h", 18)):
        people = [p for p in pos if groups[p] == g]
        ax.scatter([pos[p][0] for p in people], [pos[p][1] for p in people], marker=marker, s=size,
                   c=[EC_COL[ballots[p][0]] for p in people], edgecolors="none", zorder=3)
    camp = [p for p in pos if p in ec.CAMPAIGNERS]
    ax.scatter([pos[p][0] for p in camp], [pos[p][1] for p in camp], marker="^", s=70,
               c=[EC_COL[p[4]] for p in camp], edgecolors=INK, linewidths=0.9, zorder=5)
    frame_axes(ax)
    purity = ec.purity(frame) * 100
    counts = dict(frame.counts)
    ax.set_title(f"{title}\nA {counts['A']} · B {counts['B']} · C {counts['C']} · {purity:.0f}% vote with their area",
                 fontsize=9, loc="left", color=INK)


def fig_echo_setup():
    import echo_chambers as ec
    run = run_config("ei", ec.build({"A": "infiltrate", "B": "infiltrate", "C": "infiltrate"}, 1))
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 4.3))
    echo_panel(axes[0], run, run.frames[0], "Round 0")
    echo_panel(axes[1], run, run.frames[-1], "Round 40")
    fig.suptitle("Everyone invades: campaigners move into rival neighbourhoods", x=0.02, ha="left", fontweight="bold", color=INK, fontsize=11.5)
    fig.text(0.02, 0.01, "▲ campaigner (colour = party)   ● copycat   ⬢ committed   arrows = 'follow' links bought by campaigners",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    save(fig, "fig8a_echo_setup.png")


def fig_echo_gains():
    s = summary("echo_chambers")
    gains = s["mean_gain_by_strategy"]
    strategies = ["passive", "fortify", "infiltrate", "bridge", "broadcast"]
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    x = np.arange(len(strategies))
    for i, p in enumerate("ABC"):
        vals = [gains[p][st] * 100 for st in strategies]
        ax.bar(x + (i - 1) * 0.26, vals, 0.24, color=EC_COL[p], label=f"Party {p}")
        for j, v in enumerate(vals):
            if abs(v) >= 1:
                ax.text(j + (i - 1) * 0.26, v + (0.12 if v > 0 else -0.32), f"{v:+.1f}", ha="center", fontsize=7.5, color=INK)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylim(-2.4, 3.9)
    ax.set_xticks(x, ["do nothing", "fortify", "infiltrate", "bridge", "broadcast"], fontsize=9)
    ax.set_ylabel("vote share vs nobody campaigning (pts)", fontsize=8.5)
    ax.set_title("What each playbook earns, averaged over all 25 rival pairings", loc="left", fontweight="bold", fontsize=10.5, color=INK)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig8b_echo_gains.png")


def fig_echo_game():
    s = summary("echo_chambers")
    sym = s["symmetric_profiles"]
    strategies = ["passive", "fortify", "bridge", "broadcast", "infiltrate"]
    names = ["nobody", "all fortify", "all bridge", "all broadcast", "all infiltrate"]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    x = np.arange(len(strategies))
    ax.bar(x - 0.19, [sym[st]["chamber_purity"] * 100 for st in strategies], 0.36, color=PURPLE, label="vote with their area")
    ax.bar(x + 0.19, [sym[st]["cross_exposure"] * 100 for st in strategies], 0.36, color="#EDA100", label="see the other side")
    for i, st in enumerate(strategies):
        ax.text(i - 0.19, sym[st]["chamber_purity"] * 100 + 1.5, f"{sym[st]['chamber_purity'] * 100:.0f}", ha="center", fontsize=8)
        ax.text(i + 0.19, sym[st]["cross_exposure"] * 100 + 1.5, f"{sym[st]['cross_exposure'] * 100:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x, names, fontsize=8)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("% of voters", fontsize=8.5)
    ax.set_title("Every party plays the same way", loc="left", fontweight="bold", fontsize=10, color=INK)
    ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)
    ax.grid(axis="x", visible=False)
    # best-reply loop diagram
    ax = axes[1]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Best replies never settle", loc="left", fontweight="bold", fontsize=10, color=INK)
    boxes = [(0.5, 0.86, "Start: nobody campaigns"), (0.5, 0.62, "A invades · B fortifies · C invades"),
             (0.5, 0.36, "A bridges · B invades · C bridges"), (0.5, 0.10, "A invades · B fortifies · C bridges")]
    for x0, y0, text in boxes:
        ax.text(x0, y0, text, ha="center", va="center", fontsize=8.3, color=INK,
                bbox=dict(boxstyle="round,pad=0.45", fc="#F2EFE6", ec="#c8c7c4"))
    for (x1, y1, _), (x2, y2, _) in zip(boxes[:-1], boxes[1:]):
        ax.annotate("", xy=(x2, y2 + 0.07), xytext=(x1, y1 - 0.07), arrowprops=dict(arrowstyle="-|>", color=PURPLE, lw=1.4))
    ax.annotate("", xy=(0.93, 0.36), xytext=(0.93, 0.10), arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.4, connectionstyle="arc3,rad=-0.5"))
    ax.text(0.99, 0.23, "loops\nforever", fontsize=8, color=RED, ha="left", va="center", fontweight="bold")
    fig.tight_layout()
    save(fig, "fig8c_echo_game.png")


if __name__ == "__main__":
    import sys
    chosen = sys.argv[1:]
    for f in (fig_watchdog_setup, fig_watchdog_timelines, fig_attacker_grid, fig_spies_map, fig_spies_results,
              fig_persuasion, fig_echo_setup, fig_echo_gains, fig_echo_game):
        if chosen and f.__name__ not in chosen:
            continue
        f()
        print("ok", f.__name__, flush=True)
