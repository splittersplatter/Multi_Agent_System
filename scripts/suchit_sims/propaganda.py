"""Long-term propaganda: slow, budgeted shifts of voters' issue positions.

Same 100-person spatial electorate as the watchdog study (3 nominees, target
cyd starts third). Every campaign has the same total budget (18 units of L2
push, roughly 30 rounds of activity) over a 60-round horizon with natural
drift, so we can see (a) which allocation wins, (b) whether the effect persists
once spending stops, and (c) the representation cost: distance from the winner
to voters' *original* versus *current* views.
"""

from __future__ import annotations

import math
import statistics as stats

import numpy as np

from common import DOCS, INK, INK2, MUTED, PALETTE, Style, plt, run_config, save_fig, save_gif, save_snapshots, share_plot, write_json
import spatial as sp

OUT = DOCS / "propaganda"
ROUNDS = 60
DRIFT = 0.015
SEEDS = [1, 2, 3, 4, 5]
SHOW = 1
COLORS = {"ana": PALETTE[0], "ben": PALETTE[1], "cyd": PALETTE[6]}
PEOPLE = sp.electorate()
SWING = sp.swing_order(PEOPLE)
CORE = sp.core_order(PEOPLE)
BUDGET = 18.0

VARIANTS = [
    ("P1", "Broad & shallow: 60 voters x 0.01", SWING[:60], 0.01, "toward_target"),
    ("P2", "Swing-focused: 20 swing voters x 0.03", SWING[:20], 0.03, "toward_target"),
    ("P3", "Convert the opposition core: 20 x 0.03", CORE[:20], 0.03, "toward_target"),
    ("P4", "Chaos: random pushes on 20 swing x 0.03", SWING[:20], 0.03, "random"),
]


def config(targets, step, policy, seed):
    attack = {"target": sp.TARGET, "policy": policy, "targets": list(targets), "per_person_round": step,
              "total_budget": BUDGET if policy != "none" else 0.0, "observe_target_ideals": True}
    return sp.base_config(PEOPLE, seed, ROUNDS, DRIFT, attack)


def winner_distance(run, frame, initial=True):
    ideals = dict(run.frames[0].alignment_ideals if initial else frame.alignment_ideals)
    platform = sp.CANDIDATES[frame.winner]
    return stats.mean(math.dist(v, platform) for p, v in ideals.items() if p not in sp.CANDIDATES)


def stop_round(run):
    """First round after which the attack never spends again (None if it spends to the end)."""
    last = None
    for f in run.frames[1:]:
        if any(cost > 1e-12 for *_, cost in f.alignment_changes):
            last = f.round
    return None if last is None or last >= ROUNDS else last


def style(run, title):
    targeted = set(run.config["alignment"]["attack"]["targets"]) if run.config["alignment"]["attack"]["policy"] != "none" else set()
    return Style(lambda p: "candidate platform" if p in sp.CANDIDATES else ("targeted by propaganda" if p in targeted else "resident"),
                 {"resident": "o", "targeted by propaganda": "^", "candidate platform": "*"}, COLORS,
                 {"candidate platform": 260, "targeted by propaganda": 46}, edge_layers=(), title=title)


def positions(frame):
    pos = sp.ideal_positions(frame)
    pos.update(sp.CANDIDATES)
    return pos


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    control = [run_config(f"control_seed{s}", config(SWING[:1], 0.0, "none", s), OUT / "configs" if s == SHOW else None) for s in SEEDS]
    runs = {v[0]: [run_config(f"{v[0]}_seed{s}", config(v[2], v[3], v[4], s), OUT / "configs" if s == SHOW else None) for s in SEEDS]
            for v in VARIANTS}

    rows = []
    for vid, label, targets, step, policy in VARIANTS:
        rs = runs[vid]
        stops = [stop_round(r) for r in rs]
        stop = int(stats.mean(s for s in stops if s is not None)) if any(stops) else None
        after = [r.shares(sp.TARGET)[-1] - r.shares(sp.TARGET)[stop] for r in rs] if stop else []
        rows.append({
            "id": vid, "variant": label, "targets": len(targets), "per_person_round": step,
            "spending_ends_round": stop,
            "target_win_rate_final": sum(r.frames[-1].winner == sp.TARGET for r in rs) / len(rs),
            "rounds_target_wins_mean": stats.mean(sum(w == sp.TARGET for w in r.winners()) for r in rs),
            "first_target_win_mean": stats.mean([next((f.round for f in r.frames if f.winner == sp.TARGET), ROUNDS + 1) for r in rs]),
            "target_share_at_stop": round(stats.mean(r.shares(sp.TARGET)[stop] for r in rs), 3) if stop else None,
            "target_share_final": round(stats.mean(r.shares(sp.TARGET)[-1] for r in rs), 3),
            "control_target_share_final": round(stats.mean(c.shares(sp.TARGET)[-1] for c in control), 3),
            "share_change_after_spending_stops": round(stats.mean(after), 3) if after else None,
            "winner_distance_to_initial_views": round(stats.mean(winner_distance(r, r.frames[-1], True) for r in rs), 3),
            "winner_distance_to_current_views": round(stats.mean(winner_distance(r, r.frames[-1], False) for r in rs), 3),
            "control_winner_distance_to_initial_views": round(stats.mean(winner_distance(c, c.frames[-1], True) for c in control), 3),
            "mean_displacement_targeted": round(stats.mean(stats.mean(math.dist(dict(r.frames[0].alignment_ideals)[p], dict(r.frames[-1].alignment_ideals)[p]) for p in targets) for r in rs), 3),
        })
    write_json(OUT / "summary.json", {"rows": rows, "seeds": SEEDS, "rounds": ROUNDS, "drift": DRIFT, "budget": BUDGET,
                                      "runs": len(SEEDS) * (len(VARIANTS) + 1)})

    # -------------------------------------------------------------- figures
    fig, axes = plt.subplots(1, 4, figsize=(18, 4), sharey=True)
    carr = np.array([c.shares(sp.TARGET) for c in control])
    for ax, (vid, label, *_), row in zip(axes, VARIANTS, rows):
        arr = np.array([r.shares(sp.TARGET) for r in runs[vid]])
        ax.plot(carr.mean(0), color=MUTED, lw=1.6, ls="--", label="control (drift only)")
        ax.fill_between(range(arr.shape[1]), arr.min(0), arr.max(0), color=PALETTE[6], alpha=0.15, lw=0)
        ax.plot(arr.mean(0), color=PALETTE[6], lw=2, label="target cyd")
        for party in ("ana", "ben"):
            ax.plot(np.array([r.shares(party) for r in runs[vid]]).mean(0), color=COLORS[party], lw=1.1, label=party)
        if row["spending_ends_round"]:
            ax.axvline(row["spending_ends_round"], color=INK2, ls=":", lw=1)
            ax.text(row["spending_ends_round"] + 0.5, 0.95, "spending ends", fontsize=7.5, color=INK2, transform=ax.get_xaxis_transform())
        ax.set_title(f"{vid}: {label}", fontsize=9.5)
        ax.set_xlabel("Round")
        ax.set_ylim(0, 0.75)
    axes[0].set_ylabel("First-choice share (mean of 5 seeds)")
    axes[0].legend(fontsize=7.5, loc="upper left")
    save_fig(fig, OUT / "p01_shares.png")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    x = np.arange(len(rows))
    axes[0].bar(x, [r["rounds_target_wins_mean"] for r in rows], color=PALETTE[6], width=0.6)
    for i, r in enumerate(rows):
        axes[0].text(i, r["rounds_target_wins_mean"] + 0.6, f"final win {r['target_win_rate_final']:.0%}", ha="center", fontsize=8.5)
    axes[0].set_xticks(x, [r["id"] for r in rows])
    axes[0].set_ylabel(f"Rounds won by cyd (of {ROUNDS + 1})")
    axes[0].set_title("Same budget, different allocation")
    axes[0].grid(axis="x", visible=False)
    axes[1].bar(x - 0.2, [r["winner_distance_to_initial_views"] for r in rows], 0.38, color=PALETTE[0], label="to voters' original views")
    axes[1].bar(x + 0.2, [r["winner_distance_to_current_views"] for r in rows], 0.38, color=PALETTE[3], label="to voters' current views")
    axes[1].axhline(rows[0]["control_winner_distance_to_initial_views"], color=INK2, ls="--", lw=1)
    axes[1].text(-0.4, rows[0]["control_winner_distance_to_initial_views"] + 0.005, "control winner", fontsize=8, color=INK2)
    axes[1].set_xticks(x, [r["id"] for r in rows])
    axes[1].set_ylabel("Mean voter–winner issue distance")
    axes[1].set_title("Representation cost of the final winner")
    axes[1].legend(fontsize=8, loc="lower right")
    axes[1].grid(axis="x", visible=False)
    save_fig(fig, OUT / "p02_outcomes.png")

    # migration arrows for the showcase seed of the best allocation
    best = max(rows, key=lambda r: r["rounds_target_wins_mean"])["id"]
    run = runs[best][SEEDS.index(SHOW)]
    targets = set(run.config["alignment"]["attack"]["targets"])
    first, last = dict(run.frames[0].alignment_ideals), dict(run.frames[-1].alignment_ideals)
    fig, ax = plt.subplots(figsize=(6.2, 6))
    for p in first:
        if p in sp.CANDIDATES:
            continue
        col = PALETTE[6] if p in targets else MUTED
        ax.annotate("", xy=last[p], xytext=first[p], arrowprops=dict(arrowstyle="->", color=col, lw=0.9, alpha=0.8))
    for c, xy in sp.CANDIDATES.items():
        ax.scatter(*xy, marker="*", s=320, color=COLORS[c], edgecolors=INK, zorder=5)
        ax.text(xy[0] + 0.02, xy[1] + 0.02, c, fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_title(f"{best}: issue-space migration over {ROUNDS} rounds\n(purple = targeted voters, grey = natural drift only)", fontsize=10)
    save_fig(fig, OUT / "p03_migration.png")

    for vid, label, *_ in VARIANTS:
        r = runs[vid][SEEDS.index(SHOW)]
        st = style(r, f"{vid} issue space")
        save_gif(r, st, OUT / f"{vid}_issue_space.gif", positions_fn=positions, fps=6)
        save_snapshots(r, st, OUT / f"{vid}_snapshots.png", [0, 15, 30, ROUNDS], positions)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    share_plot(ax, control[0], COLORS, "Control: natural drift only (seed 1)")
    save_fig(fig, OUT / "p04_control.png")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
