"""Foreign-intelligence study: sleeper cells spreading targeted disinformation.

100 agents. Residents either trust reports from contacts (``local_plurality``)
or watch ballots directly through trusted sensors (``sensed_plurality``).
Spies keep a cover ballot and spend a per-cell budget on fabricated reports
that claim support for target B. Four attack variants differ only in how much
intelligence decides *who* is lied to:

F1 blind -> F2 + preference sight -> F3 + eavesdropping (all 15 spies = 15%),
F4 = F3 run by a half-size network of 8 spies.
Each variant is paired with a no-disinformation control (same spies, same seeds).
"""

from __future__ import annotations

import math
import random
import statistics as stats

import numpy as np

from common import (DOCS, pin_uniform_walk, INK, INK2, MUTED, PALETTE, Style, plt, run_config, save_fig, save_gif, save_snapshots,
                    share_plot, write_json)

OUT = DOCS / "foreign_intelligence"
PARTIES = ["A", "B", "C"]
TARGET = "B"
COLORS = {"A": PALETTE[0], "B": PALETTE[6], "C": PALETTE[1]}
ROUNDS = 25
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
SHOW = 1


def layout(n_spies: int, seed: int = 7):
    rng = random.Random(seed)
    n_res = 100 - n_spies
    people, residents = [], []
    for i in range(n_res):
        first = rng.choices(PARTIES, weights=[0.40, 0.37, 0.23])[0]
        rest = [p for p in PARTIES if p != first]
        rng.shuffle(rest)
        u = rng.random()
        profile = "committed" if u < 0.4 else "trusting" if u < 0.8 else "sensor"
        pid = f"r{i:02d}"
        residents.append(pid)
        people.append({"id": pid, "group": profile, "preference": [first] + rest,
                       "position": [round(rng.uniform(0.03, 0.97), 4), round(rng.uniform(0.03, 0.97), 4)]})
    pos = {p["id"]: p["position"] for p in people}
    # ten community chats: a seed resident plus its six nearest neighbours
    chats = {}
    centres = rng.sample(residents, 10)
    for c, centre in enumerate(centres):
        near = sorted(residents, key=lambda r: math.dist(pos[r], pos[centre]))[:7]
        chats[f"chat{c}"] = near
    spies = []
    for s in range(n_spies):
        anchor = rng.choice(residents)
        position = [round(min(0.97, max(0.03, pos[anchor][0] + rng.uniform(-0.05, 0.05))), 4),
                    round(min(0.97, max(0.03, pos[anchor][1] + rng.uniform(-0.05, 0.05))), 4)]
        cover = rng.choice(["A", "C"])  # sleepers pose as A or C supporters
        sid = f"spy{s:02d}"
        spies.append(sid)
        people.append({"id": sid, "group": "spies", "preference": [cover, "B", "C" if cover == "A" else "A"],
                       "position": position})
        pos[sid] = position
    return people, residents, spies, chats, pos


RATE, TOTAL = 4, 100


def build(variant: str, n_spies: int, seed: int, rate: int | None = None, total: int | None = None) -> dict:
    rate = RATE if rate is None else rate
    total = TOTAL if total is None else total
    people, residents, spies, chats, pos = layout(n_spies)
    chats = {k: list(v) for k, v in chats.items()}
    sight = variant in ("sight", "sight_eavesdrop")
    eaves = variant == "sight_eavesdrop"
    attack = variant != "control"
    persistent, coalitions = [], []
    for spy in spies:
        local = sorted(residents, key=lambda r: math.dist(pos[r], pos[spy]))[:15]
        persistent += [[spy, r] for r in local]  # the cell's local followers
        ordered = sorted(chats, key=lambda c: min(math.dist(pos[m], pos[spy]) for m in chats[c]))
        chats[ordered[0]].append(spy)  # infiltrate the nearest community chat
        cell = {"id": f"cell_{spy}", "members": [spy], "target": TARGET,
                "report_budget_per_round": rate if attack else 0, "report_budget_total": total if attack else 0}
        if sight:
            cell.update({"sight_targets": local, "sight_budget_per_round": len(local), "sight_budget_total": len(local)})
        if eaves:
            cell.update({"eavesdrop_channels": ordered[1:3], "eavesdrop_budget_per_round": 8, "eavesdrop_budget_total": 200})
        coalitions.append(cell)
    spy_group = {"voting": "sincere", "movement": "random_walk", "max_step": 0.01,
                 "communication": "python:spy_comms:disinform" if attack else "none",
                 "parameters": {"target": TARGET, "mode": variant if attack else "blind"},
                 "capabilities": {"observe_target_preferences": sight, "intercept_private_reports": eaves,
                                  "receive_private_reports": True, "send_private_reports": True}}
    return pin_uniform_walk({
        "parties": PARTIES, "k": 1, "seed": seed, "rounds": ROUNDS,
        "groups": {
            "committed": {"voting": "sincere", "movement": "random_walk", "max_step": 0.015, "communication": "truthful"},
            "trusting": {"voting": "local_plurality", "movement": "random_walk", "max_step": 0.015, "communication": "truthful"},
            "sensor": {"voting": "sensed_plurality", "movement": "random_walk", "max_step": 0.015, "communication": "truthful",
                       "capabilities": {"sense_public_ballots": True}},
            "spies": spy_group,
        },
        "network": {"radius": 0.12, "persistent_edges": persistent, "private_channels": chats},
        "coalitions": coalitions,
        "people": people,
    })


VARIANTS = [
    ("F1", "Blind disinformation (15 spies)", "blind", 15),
    ("F2", "Sight-targeted lies (15 spies)", "sight", 15),
    ("F3", "Sight + eavesdropping (15 spies)", "sight_eavesdrop", 15),
    ("F4", "Half-size network: sight + eavesdrop (8 spies)", "sight_eavesdrop", 8),
]


def lies(run):
    return [len(f.deceptive_reports) for f in run.frames]


def flips(run, profiles):
    first, last = dict(run.frames[0].ballots), dict(run.frames[-1].ballots)
    out = {}
    for person, prof in profiles.items():
        if prof == "spy":
            continue
        if first[person][0] != TARGET and last[person][0] == TARGET:
            out[prof] = out.get(prof, 0) + 1
    return out


def style(run, title):
    groups = {p["id"]: p["group"] for p in run.config["people"]}
    names = {"committed": "committed partisan", "trusting": "report-trusting resident", "sensor": "sensor-checking resident", "spies": "spy"}

    def edges(frame):
        return [(s, r, PALETTE[7]) for _, s, r, ch, _ in frame.deceptive_reports if ch == "public"]
    return Style(lambda p: names[groups[p]],
                 {"committed partisan": "D", "report-trusting resident": "o", "sensor-checking resident": "s", "spy": "^"}, COLORS,
                 {"spy": 70, "sensor-checking resident": 30, "report-trusting resident": 30, "committed partisan": 24},
                 edge_layers=("proximity",), highlight_edges=edges, title=title)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for vid, label, mode, n in VARIANTS:
        att = [run_config(f"{vid}_seed{s}", build(mode, n, s), OUT / "configs" if s == SHOW else None) for s in SEEDS]
        ctl = [run_config(f"{vid}_control_seed{s}", build("control", n, s), OUT / "configs" if s == SHOW else None) for s in SEEDS]
        results[vid] = (att, ctl)

    rows = []
    for vid, label, mode, n in VARIANTS:
        att, ctl = results[vid]
        profiles = {p["id"]: ("spy" if p["group"] == "spies" else p["group"]) for p in att[0].config["people"]}
        gain = [a.shares(TARGET)[-1] - c.shares(TARGET)[-1] for a, c in zip(att, ctl)]
        total_lies = [sum(lies(a)) for a in att]
        fl = [flips(a, profiles) for a in att]
        fl_ctl = [flips(c, profiles) for c in ctl]
        rows.append({
            "id": vid, "variant": label, "spies": n,
            "target_win_rate_attack": sum(a.frames[-1].winner == TARGET for a in att) / len(att),
            "target_win_rate_control": sum(c.frames[-1].winner == TARGET for c in ctl) / len(ctl),
            "rounds_target_leading_attack": stats.mean(sum(w == TARGET for w in a.winners()) for a in att),
            "final_target_share_attack": round(stats.mean(a.shares(TARGET)[-1] for a in att), 3),
            "final_target_share_control": round(stats.mean(c.shares(TARGET)[-1] for c in ctl), 3),
            "paired_share_gain_mean": round(stats.mean(gain), 3),
            "paired_run_mean_share_gain": round(stats.mean(stats.mean(a.shares(TARGET)) - stats.mean(c.shares(TARGET)) for a, c in zip(att, ctl)), 3),
            "rounds_target_leading_control": stats.mean(sum(w == TARGET for w in c.winners()) for c in ctl), "paired_share_gain_min": round(min(gain), 3),
            "paired_share_gain_max": round(max(gain), 3),
            "lies_sent_mean": stats.mean(total_lies),
            "votes_gained_per_100_lies": round(100 * stats.mean(gain) * 100 / max(1, stats.mean(total_lies)), 2),
            "sight_events": stats.mean(sum(len(f.preference_sight) for f in a.frames) for a in att),
            "intercepted_reports": stats.mean(sum(len(f.overheard_reports) for f in a.frames) for a in att),
            "flipped_to_target_trusting": stats.mean(f.get("trusting", 0) for f in fl),
            "flipped_to_target_sensor": stats.mean(f.get("sensor", 0) for f in fl),
            "extra_conversions_vs_control_trusting": stats.mean(a.get("trusting", 0) - c.get("trusting", 0) for a, c in zip(fl, fl_ctl)),
            "extra_conversions_vs_control_sensor": stats.mean(a.get("sensor", 0) - c.get("sensor", 0) for a, c in zip(fl, fl_ctl)),
            "extra_conversions_vs_control_committed": stats.mean(a.get("committed", 0) - c.get("committed", 0) for a, c in zip(fl, fl_ctl)),
        })
    write_json(OUT / "summary.json", {"rows": rows, "seeds": SEEDS, "rounds": ROUNDS,
                                      "runs": sum(2 * len(SEEDS) for _ in VARIANTS)})

    # ---------------------------------------------------------------- figures
    fig, axes = plt.subplots(1, 4, figsize=(18, 4), sharey=True)
    for ax, (vid, label, *_) in zip(axes, VARIANTS):
        att, ctl = results[vid]
        for runs, col, lab in ((ctl, MUTED, "control (no lies)"), (att, PALETTE[6], "attack")):
            arr = np.array([r.shares(TARGET) for r in runs])
            ax.plot(range(arr.shape[1]), arr.mean(0), color=col, lw=2, label=lab)
            ax.fill_between(range(arr.shape[1]), arr.min(0), arr.max(0), color=col, alpha=0.15, lw=0)
        lead = np.array([r.shares("A") for r in att]).mean(0)
        ax.plot(range(len(lead)), lead, color=COLORS["A"], lw=1.2, ls=":", label="A share (attack)")
        ax.set_title(f"{vid}: {label}", fontsize=9.5)
        ax.set_xlabel("Round")
        ax.set_ylim(0.15, 0.6)
    axes[0].set_ylabel("Target (B) first-choice share")
    axes[0].legend(fontsize=7.5, loc="upper left")
    fig.suptitle(f"Target share, mean and min–max over {len(SEEDS)} seeds", x=0.01, ha="left", fontweight="bold")
    save_fig(fig, OUT / "f01_target_share.png")

    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    x = np.arange(len(rows))
    names = [r["id"] for r in rows]
    axes[0].bar(x - 0.2, [r["final_target_share_control"] for r in rows], 0.38, color=MUTED, label="control")
    axes[0].bar(x + 0.2, [r["final_target_share_attack"] for r in rows], 0.38, color=PALETTE[6], label="attack")
    for i, r in enumerate(rows):
        axes[0].text(i + 0.2, r["final_target_share_attack"] + 0.01, f"win {r['target_win_rate_attack']:.0%}", ha="center", fontsize=8)
    axes[0].set_xticks(x, names)
    axes[0].set_title("Final target share and win rate")
    axes[0].legend(fontsize=8, loc="lower right")
    axes[1].bar(x - 0.2, [r["rounds_target_leading_control"] for r in rows], 0.38, color=MUTED, label="control")
    axes[1].bar(x + 0.2, [r["rounds_target_leading_attack"] for r in rows], 0.38, color=PALETTE[6], label="attack")
    for i, r in enumerate(rows):
        axes[1].text(i + 0.2, r["rounds_target_leading_attack"] + 0.3, f"+{r['paired_run_mean_share_gain'] * 100:.1f} pts", ha="center", fontsize=8)
    axes[1].set_xticks(x, names)
    axes[1].set_ylabel(f"Rounds (of {ROUNDS + 1})")
    axes[1].set_ylim(0, ROUNDS + 1)
    axes[1].set_title("Rounds B leads (label: mean share gain over run)")
    axes[1].legend(fontsize=8, loc="upper right")
    axes[2].bar(x - 0.26, [r["extra_conversions_vs_control_trusting"] for r in rows], 0.24, color=PALETTE[0], label="report-trusting")
    axes[2].bar(x, [r["extra_conversions_vs_control_sensor"] for r in rows], 0.24, color=PALETTE[3], label="sensor-checking")
    axes[2].bar(x + 0.26, [r["extra_conversions_vs_control_committed"] for r in rows], 0.24, color=PALETTE[2], label="committed")
    axes[2].axhline(0, color=INK2, lw=0.8)
    axes[2].set_xticks(x, names)
    axes[2].set_title("Extra residents ending on B vs paired control")
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="x", visible=False)
    save_fig(fig, OUT / "f02_outcomes.png")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for (vid, *_), col in zip(VARIANTS, PALETTE):
        arr = np.cumsum(np.array([lies(a) for a in results[vid][0]]), axis=1).mean(0)
        ax.plot(range(len(arr)), arr, lw=2, color=col, label=vid)
    ax.set_xlabel("Round")
    ax.set_ylabel("Cumulative fabricated reports")
    ax.set_title(f"Disinformation spend over time (budget {RATE}/round, {TOTAL} per cell)")
    ax.legend(fontsize=8)
    save_fig(fig, OUT / "f03_spend.png")

    for vid, label, mode, n in VARIANTS:
        run = results[vid][0][SEEDS.index(SHOW)]
        st = style(run, f"{vid}")
        save_gif(run, st, OUT / f"{vid}_network.gif")
        save_snapshots(run, st, OUT / f"{vid}_snapshots.png", [0, 3, 10, ROUNDS])
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    share_plot(axes[0], results["F2"][0][0], COLORS, "F2 sight-targeted lies, seed 1")
    share_plot(axes[1], results["F2"][1][0], COLORS, "Paired control (spies silent), seed 1")
    save_fig(fig, OUT / "f04_f2_vs_control.png")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
