"""Slide charts from results/runs.jsonl, results/mixes.csv and results/summary.json.

    PYTHONPATH=src:presentation python3 presentation/plots.py

Writes PNGs to results/figures/. Lines are medians over the 30 towns, bands the middle
half of towns (25th-75th percentile). Colours follow the party, never its rank:
Left blue, Right orange, Centre green. Text is always in ink colours.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiments import E4_PARTY, FOLLOWERS, RADII  # noqa: E402
from town import PLATFORMS, Town, opinions, preferences  # noqa: E402

RESULTS = HERE / "results"
FIGS = RESULTS / "figures"
SURFACE, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#a9a8a2"
PARTY = {"Left": "#2a78d6", "Right": "#eb6834", "Centre": "#1baf7a"}
ORDER = ["Left", "Right", "Centre"]
BLUES = ["#eaf2fc", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
DPI = 200

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 12,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "lines.linewidth": 2.2, "legend.frameon": False, "font.family": "DejaVu Sans",
})


def load() -> dict[str, list[dict]]:
    from analyse import run_lines
    by = defaultdict(list)
    for line in run_lines():
        r = json.loads(line)
        by[r["setting"]].append(r)
    for rows in by.values():
        rows.sort(key=lambda r: r["seed"])
    return by


def votes(rows, party) -> np.ndarray:
    return np.array([[c[party] for c in r["counts"]] for r in rows], dtype=float)


def band(ax, values, colour, lw=2.2, ls="-", alpha=0.16, x=None):
    x = np.arange(values.shape[1]) if x is None else x
    lo, mid, hi = np.percentile(values, [25, 50, 75], axis=0)
    if alpha:
        ax.fill_between(x, lo, hi, color=colour, alpha=alpha, linewidth=0)
    ax.plot(x, mid, color=colour, lw=lw, ls=ls)
    return mid


def end_labels(ax, x, items, min_gap, dx=0.4):
    """items: [(y, text, colour)]; draws a short coloured tick and ink text, spread apart."""
    placed = []
    for y, text, colour in sorted(items):
        yl = y if not placed or y - placed[-1] >= min_gap else placed[-1] + min_gap
        placed.append(yl)
        ax.plot([x + dx * 0.3, x + dx], [yl, yl], color=colour, lw=3, solid_capstyle="round", clip_on=False)
        ax.text(x + dx * 1.4, yl, text, va="center", color=INK, fontsize=12, clip_on=False)


def save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name, dpi=DPI, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


# ------------------------------------------------------------------ the town

def fig_town():
    t = Town()
    pts, prefs = opinions(t, 0), preferences(t, 0)
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    for p in ORDER:
        xs = [x for (x, y), pr in zip(pts, prefs) if pr[0] == p]
        ys = [y for (x, y), pr in zip(pts, prefs) if pr[0] == p]
        ax.scatter(xs, ys, s=22, color=PARTY[p], alpha=0.75, linewidths=0, label=f"favourite: {p} ({len(xs)})")
    for p, (x, y) in PLATFORMS.items():
        ax.scatter([x], [y], s=260, marker="*", color=PARTY[p], edgecolors=SURFACE, linewidths=1.6, zorder=5)
        ax.annotate(p, (x, y), xytext=(0, 14), textcoords="offset points", ha="center", fontsize=13,
                    fontweight="bold", color=INK, zorder=6)
    ax.set_xlim(0, 1); ax.set_ylim(0.05, 0.95); ax.set_aspect("equal")
    ax.set_xlabel("opinion, first issue"); ax.set_ylabel("opinion, second issue")
    ax.legend(loc="lower left", fontsize=10.5, handletextpad=0.2, borderaxespad=0.2)
    save(fig, "town.png")


# ------------------------------------------------------------------ experiment 1

def fig_e1(runs):
    rows = runs["e1"]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    upto = 10
    items = []
    for p in ORDER:
        mid = band(ax, votes(rows, p)[:, :upto + 1], PARTY[p])
        items.append((mid[-1], f"{p} {mid[-1]:.0f}", PARTY[p]))
        ax.text(-0.25, mid[0], f"{mid[0]:.0f}", ha="right", va="center", fontsize=11, color=INK2)
    end_labels(ax, upto, items, 14)
    ax.axvspan(1, upto, color=GRID, alpha=0.35, linewidth=0)
    ax.text(5.5, 285, "frozen from round 1 in all 30 towns (proved)", ha="center", va="top", fontsize=12, color=INK2)
    ax.set_xlim(-0.9, upto); ax.set_ylim(0, 300); ax.set_xticks(range(0, upto + 1))
    ax.set_xlabel("round (0 = everyone votes sincerely; runs go to 40, nothing changes after 1)")
    ax.set_ylabel("votes (of 300)")
    save(fig, "e1_full_information.png")


# ------------------------------------------------------------------ experiment 2

def fig_e2():
    rows = list(csv.DictReader((RESULTS / "mixes.csv").open()))
    # collapse sincere/pivot splits: same front-runner and copycat share -> mean of medians, sum of upsets
    cell = defaultdict(lambda: {"left": [], "upsets": 0, "n": 0})
    for r in rows:
        k = (int(r["frontrunner"]), int(r["copycat"]))
        cell[k]["left"].append(float(r["left_median"]))
        cell[k]["upsets"] += 30 - int(r["left_wins"])
        cell[k]["n"] += 30
    fs = sorted({k[0] for k in cell}); cs = sorted({k[1] for k in cell})
    grid = np.full((len(fs), len(cs)), np.nan)
    for (f, c), d in cell.items():
        grid[fs.index(f), cs.index(c)] = np.mean(d["left"])
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    fig, ax = plt.subplots(figsize=(7.4, 5.6))
    ax.grid(False)
    im = ax.imshow(grid, origin="lower", cmap=cmap, vmin=100, vmax=260, aspect="auto")
    for (f, c), d in cell.items():
        v = np.mean(d["left"])
        txt = f"{v:.0f}"
        if d["upsets"]:
            txt += f"\n{d['upsets']} upsets\nin {d['n']}"
        ax.text(cs.index(c), fs.index(f), txt, ha="center", va="center", fontsize=10.5 if not d["upsets"] else 9,
                color="white" if v > 195 else INK, fontweight="bold" if d["upsets"] else "normal")
    ax.set_xticks(range(len(cs)), [f"{c}%" for c in cs]); ax.set_yticks(range(len(fs)), [f"{f}%" for f in fs])
    ax.set_xlabel("copycats"); ax.set_ylabel("front-runners")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("Left's final votes (of 300), median of towns", color=INK2); cb.outline.set_visible(False)
    save(fig, "e2_mixes.png")


# ------------------------------------------------------------------ experiment 3

def e3_rows(runs, r, walking, prefix="e3"):
    return runs["e1"] if r == "full" else runs.get(f"{prefix}_r{r}_{'walk' if walking else 'still'}", [])


def fig_e3(runs, summary):
    s3 = summary["exp3"]
    keys = ["full"] + RADII
    labels = [f"{s3[f'{k}_walk']['mean_neighbours']:.0f}" for k in keys]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.4, 4.9), gridspec_kw={"wspace": 0.72, "width_ratios": [1.25, 1]})
    # A: how long does the first count's leader stay ahead? (walking, 150 rounds)
    lines = [("full", runs["e1"], BLUES[5])] + [(r, runs.get(f"e3long_r{r}_walk", []), c)
                                                 for r, c in zip([0.4, 0.2, 0.1, 0.05], [BLUES[4], BLUES[3], BLUES[2], BLUES[1]])]
    items = []
    for r_, rows, colour in lines:
        if not rows:
            continue
        n = 150
        share = []
        for t in range(n + 1):
            share.append(100 * sum((r["winners"][t] if t < len(r["winners"]) else r["winners"][-1]) == "Left" for r in rows) / len(rows))
        # 5-round moving average keeps single-town flips from dominating the picture
        sm = np.convolve(share, np.ones(5) / 5, mode="same")
        sm[:2], sm[-2:] = share[:2], np.mean(share[-5:])
        a1.plot(range(n + 1), sm, color=colour, lw=2.4)
        k = "full" if r_ == "full" else r_
        items.append((sm[-1], f"{s3[f'{k}_walk']['mean_neighbours']:.0f} heard", colour))
    end_labels(a1, 150, items, 7, dx=4)
    a1.axhline(100 / 3, color=MUTED, lw=1, ls=":")
    a1.text(3, 30, "one in three", color=INK2, fontsize=10.5, va="top")
    a1.set_xlim(0, 150); a1.set_ylim(0, 104); a1.set_xticks([0, 25, 50, 75, 100, 125, 150])
    a1.set_xlabel("round (people walking)"); a1.set_ylabel("% of the 30 towns where Left leads")
    a1.set_title("The first count's leader loses its grip")
    # B: is it settled
    for walking, ls in ((True, "-"), (False, "--")):
        tag = "walk" if walking else "still"
        w = [100 * s3[f"{k}_{tag}"]["winner_same_last10"] / 30 for k in keys]
        v = [100 * s3[f"{k}_{tag}"]["votes_frozen_last10"] / 30 for k in keys]
        a2.plot(range(len(keys)), w, ls=ls, color=BLUES[5], marker="o", ms=7)
        a2.plot(range(len(keys)), v, ls=ls, color=BLUES[1], marker="o", ms=7)
    a2.set_xticks(range(len(keys)), labels); a2.set_xlabel("people each voter hears (average)")
    a2.set_ylabel("% of towns, rounds 31-40"); a2.set_ylim(-4, 104); a2.set_title("Does it settle by round 40?")
    from matplotlib.lines import Line2D
    a2.legend([Line2D([], [], color=BLUES[5], lw=2.2), Line2D([], [], color=BLUES[1], lw=2.2),
               Line2D([], [], color=INK2, lw=2.2), Line2D([], [], color=INK2, lw=2.2, ls="--")],
              ["same winner every round", "nobody changes vote", "walking", "standing still"],
              ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=11)
    save(fig, "e3_hearing.png")


def fig_e3_winners(runs, summary):
    """Who leads at round 40 and at round 150, walking, by people heard."""
    s3 = summary["exp3"]; lr = summary["exp3_checks"]["long_runs"]
    keys = ["full", 0.4, 0.2, 0.1, 0.05]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw={"wspace": 0.18}, sharey=True)
    for ax, rnd in zip(axes, ("40", "150")):
        bottom = np.zeros(len(keys))
        for p in ORDER:
            vals = np.array([30 if (k == "full" and p == "Left") else 0 if k == "full" else lr[str(k)]["winners_at"][rnd].get(p, 0) for k in keys])
            ax.bar(range(len(keys)), vals, bottom=bottom, color=PARTY[p], width=0.62, edgecolor=SURFACE, linewidth=2, label=p)
            for i, (v, b) in enumerate(zip(vals, bottom)):
                if v >= 3:
                    ax.text(i, b + v / 2, f"{v}", ha="center", va="center", color="white", fontsize=11, fontweight="bold")
            bottom += vals
        ax.set_xticks(range(len(keys)), [f"{s3[f'{k}_walk']['mean_neighbours']:.0f}" for k in keys])
        ax.set_xlabel("people each voter hears (average)"); ax.set_title(f"Who leads at round {rnd}")
        ax.set_ylim(0, 30)
    axes[0].set_ylabel("towns (of 30)")
    axes[0].legend(ncol=3, loc="upper center", bbox_to_anchor=(1.05, -0.2), fontsize=11)
    save(fig, "e3_winners.png")


def fig_e3_centre(runs):
    """Centre's votes over time with ~9 people heard: sticky front-runners (300 voters) vs not (301)."""
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    full = votes(runs["e1"], "Centre")
    full = np.hstack([full, np.repeat(full[:, -1:], 150 - full.shape[1] + 1, axis=1)])   # proved frozen after round 1
    mid_full = band(ax, full, BLUES[5], alpha=0.12)
    walk = votes(runs.get("e3long_r0.1_walk") or runs["e3_r0.1_walk"], "Centre")
    mid_walk = band(ax, walk, PARTY["Centre"], alpha=0.14)
    odd_rows = runs.get("e3odd_r0.1_walk", [])
    if odd_rows:
        odd = votes(odd_rows, "Centre")
        mid_odd = band(ax, odd, INK2, alpha=0.10, ls="--")
        ax.text(odd.shape[1] + 1, mid_odd[-1] - 14, f"~9 heard, walking, 301 voters\n(front-runners not sticky): {mid_odd[-1]:.0f} at round 40",
                fontsize=10.5, color=INK, va="center")
    end_labels(ax, walk.shape[1] - 1, [(mid_walk[-1], f"~9 heard, walking: {mid_walk[-1]:.0f}", PARTY["Centre"]),
                                       (mid_full[-1], f"everyone hears everyone: {mid_full[-1]:.0f}", BLUES[5])], 12, dx=3)
    ax.axhline(83, color=MUTED, lw=1, ls=":")
    ax.text(118, 79, "sincere first choices (83)", fontsize=10.5, color=INK2, va="top")
    ax.set_xlim(0, 150); ax.set_ylim(0, 160)
    ax.set_xlabel("round"); ax.set_ylabel("Centre's votes, median of 30 towns")
    save(fig, "e3_centre.png")


def fig_degree(runs):
    rows = runs["e3_r0.1_walk"]
    pooled = Counter()
    for r in rows:
        pooled.update({int(k): v for k, v in r["degree_hist_round1"].items()})
    total = sum(pooled.values())
    xs = list(range(0, max(pooled) + 1))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(xs, [100 * pooled.get(x, 0) / total for x in xs], color="#5598e7", width=0.8, edgecolor=SURFACE, linewidth=1.5)
    mean = sum(k * v for k, v in pooled.items()) / total
    ax.axvline(mean, color=INK2, lw=1.2, ls="--")
    ax.text(mean + 0.4, ax.get_ylim()[1] * 0.92, f"average {mean:.1f}", color=INK2, fontsize=11)
    ax.set_xlabel("people a voter hears (radius 0.1, round 1, all 30 towns)"); ax.set_ylabel("% of voters")
    save(fig, "degree_r0.1.png")


# ------------------------------------------------------------------ experiment 4

def fig_e4(runs, summary):
    s4 = summary["exp4"]["settings"]
    fs = [f for f in FOLLOWERS if f"f{f}" in s4]
    if not fs:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"wspace": 0.3})
    x = np.arange(len(fs))
    bottom = np.zeros(len(fs))
    for p in ORDER:
        vals = np.array([s4[f"f{f}"]["winner_final"].get(p, 0) for f in fs])
        a1.bar(x, vals, bottom=bottom, color=PARTY[p], width=0.62, edgecolor=SURFACE, linewidth=2, label=p)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v >= 3:
                a1.text(i, b + v / 2, f"{v}", ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        bottom += vals
    a1.set_xticks(x, [str(f) for f in fs]); a1.set_xlabel("followers per minority member")
    a1.set_ylabel("towns won (of 30), round 40"); a1.set_ylim(0, 30); a1.set_title("Who wins")
    a1.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=11)
    items = []
    for p in ORDER:
        rows = [runs[f"e4_f{f}"] for f in fs]
        mid = [np.median([r["counts"][-1][p] for r in rr]) for rr in rows]
        lo = [np.percentile([r["counts"][-1][p] for r in rr], 25) for rr in rows]
        hi = [np.percentile([r["counts"][-1][p] for r in rr], 75) for rr in rows]
        a2.fill_between(x, lo, hi, color=PARTY[p], alpha=0.15, linewidth=0)
        a2.plot(x, mid, color=PARTY[p], marker="o", ms=7)
        items.append((mid[-1], f"{p} {mid[-1]:.0f}", PARTY[p]))
    end_labels(a2, x[-1], items, 12, dx=0.25)
    a2.set_xticks(x, [str(f) for f in fs]); a2.set_xlabel("followers per minority member")
    a2.set_ylabel("final votes (of 300)"); a2.set_ylim(0, 200); a2.set_title("Final votes")
    save(fig, "e4_propaganda.png")


def main():
    runs = load()
    summary = json.loads((RESULTS / "summary.json").read_text())
    fig_town(); fig_e1(runs); fig_e2(); fig_e3(runs, summary); fig_e3_winners(runs, summary); fig_e3_centre(runs); fig_degree(runs); fig_e4(runs, summary)
    slide_e2(); slide_e3(runs, summary); slide_e4(runs, summary)   # bigger-type versions used on the slides
    print("figures in", FIGS)



# ------------------------------------------------------------------ slide versions (bigger type, one panel)

def _slide_rc():
    plt.rcParams.update({"font.size": 18, "axes.titlesize": 20, "axes.labelsize": 18,
                         "xtick.labelsize": 17, "ytick.labelsize": 17, "legend.fontsize": 17})


def slide_e2():
    _slide_rc()
    rows = list(csv.DictReader((RESULTS / "mixes.csv").open()))
    cell = defaultdict(lambda: {"left": [], "upsets": 0, "n": 0})
    for r in rows:
        k = (int(r["frontrunner"]), int(r["copycat"]))
        cell[k]["left"].append(float(r["left_median"]))
        cell[k]["upsets"] += 30 - int(r["left_wins"])
        cell[k]["n"] += 30
    fs = sorted({k[0] for k in cell}); cs = sorted({k[1] for k in cell})
    grid = np.full((len(fs), len(cs)), np.nan)
    for (f, c), d in cell.items():
        grid[fs.index(f), cs.index(c)] = np.mean(d["left"])
    fig, ax = plt.subplots(figsize=(8.6, 6.6))
    ax.grid(False)
    ax.imshow(grid, origin="lower", cmap=LinearSegmentedColormap.from_list("blues", BLUES), vmin=100, vmax=260, aspect="auto")
    for (f, c), d in cell.items():
        v = np.mean(d["left"])
        txt = f"{v:.0f}" + (f"\n{d['upsets']}/{d['n']} upsets" if d["upsets"] else "")
        ax.text(cs.index(c), fs.index(f), txt, ha="center", va="center", fontsize=12.5 if d["upsets"] else 17,
                color="white" if v > 195 else INK, fontweight="bold" if d["upsets"] else "normal")
    ax.set_xticks(range(len(cs)), [f"{c}%" for c in cs]); ax.set_yticks(range(len(fs)), [f"{f}%" for f in fs])
    ax.set_xlabel("copycats"); ax.set_ylabel("front-runners")
    ax.set_title("Left's final votes, median of 30 towns\n84 mixes \u00d7 30 towns, full information", loc="left", fontsize=18)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "slide_e2.png")


def slide_e3(runs, summary):
    _slide_rc()
    s3 = summary["exp3"]
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    lines = [("full", runs["e1"], BLUES[5])] + [(r, runs.get(f"e3long_r{r}_walk", []), c)
                                                 for r, c in zip([0.4, 0.2, 0.1, 0.05], [BLUES[4], BLUES[3], BLUES[2], BLUES[1]])]
    items = []
    for r_, rows, colour in lines:
        share = [100 * sum((r["winners"][t] if t < len(r["winners"]) else r["winners"][-1]) == "Left" for r in rows) / len(rows)
                 for t in range(151)]
        sm = np.convolve(share, np.ones(5) / 5, mode="same")
        sm[:2], sm[-2:] = share[:2], np.mean(share[-5:])
        ax.plot(range(151), sm, color=colour, lw=3)
        k = "full" if r_ == "full" else r_
        at = [sum((r["winners"][t] if t < len(r["winners"]) else r["winners"][-1]) == "Left" for r in rows) for t in (1, 40, 150)]
        items.append((sm[-1], f"{s3[f'{k}_walk']['mean_neighbours']:.0f} heard:  {at[0]} \u2192 {at[1]} \u2192 {at[2]}", colour))
    end_labels(ax, 150, items, 8, dx=4)
    ax.text(158, 112, "towns with Left ahead\nat rounds 1 \u2192 40 \u2192 150", fontsize=15, color=INK2, va="bottom", clip_on=False)
    ax.axvline(40, color=MUTED, lw=1.2, ls="--")
    ax.text(41.5, 3, "round 40", fontsize=15, color=INK2)
    ax.axhline(100 / 3, color=MUTED, lw=1.2, ls=":")
    ax.text(3, 30, "one in three", color=INK2, fontsize=16, va="top")
    ax.set_xlim(0, 150); ax.set_ylim(0, 104); ax.set_xticks([0, 25, 50, 75, 100, 125, 150])
    ax.set_xlabel("round (people walking)"); ax.set_ylabel("% of the 30 towns where Left leads")
    ax.set_title("Walking, 30 towns per line, 150 rounds", loc="left", pad=14)
    save(fig, "slide_e3.png")


def slide_e4(runs, summary):
    _slide_rc()
    s4 = summary["exp4"]["settings"]
    base = summary["exp3"]["0.2_walk"]["winner_final"]
    labels = ["no group"] + [str(f) for f in FOLLOWERS]
    data = [base] + [s4[f"f{f}"]["winner_final"] for f in FOLLOWERS]
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    x = np.arange(len(labels)); bottom = np.zeros(len(labels))
    for p in ORDER:
        vals = np.array([d.get(p, 0) for d in data])
        ax.bar(x, vals, bottom=bottom, color=PARTY[p], width=0.66, edgecolor=SURFACE, linewidth=2, label=p)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v >= 3:
                ax.text(i, b + v / 2, f"{v}", ha="center", va="center", color="white", fontsize=18, fontweight="bold")
        bottom += vals
    centre = [summary["exp3"]["0.2_walk"]["final_median"]["Centre"]] + [s4[f"f{f}"]["party_final_median"] for f in FOLLOWERS]
    for i, v in enumerate(centre):
        ax.text(i, 30.8, f"{v:g}", ha="center", va="bottom", fontsize=17, color=INK, fontweight="bold")
    ax.text(-0.45, 33.2, "Centre's median votes (of 300):", ha="left", va="bottom", fontsize=16, color=INK2)
    ax.axvline(0.5, color=MUTED, lw=1.2, ls=":")
    ax.set_xticks(x, labels); ax.set_xlabel("followers per member of the loyal 10%")
    ax.set_ylabel("towns won (of 30), round 40"); ax.set_ylim(0, 30)
    ax.set_yticks([0, 5, 10, 15, 20, 25, 30])
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    save(fig, "slide_e4.png")


def slides():
    runs = load()
    summary = json.loads((RESULTS / "summary.json").read_text())
    slide_e2(); slide_e3(runs, summary); slide_e4(runs, summary)


if __name__ == "__main__":
    main()
