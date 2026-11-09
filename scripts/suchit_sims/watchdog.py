"""Watchdog study: can an aggregate-only detector catch a voter-alignment attack
before the target wins three consecutive rounds?

* 10 showcase simulations (seed 11), each an attack variant with a paired
  no-attack control on the same seed and drift.
* A detector-strategy search on separate calibration seeds, validated on
  held-out seeds: single-round threshold (the engine's detector), multi-round
  window and CUSUM detectors. All three read only public aggregate counts,
  exactly the information the engine's passive detector has.
* An attacker best-response grid against the selected watchdog.
"""

from __future__ import annotations

import itertools
import math
import statistics as stats
from pathlib import Path

import numpy as np

from common import (DOCS, INK, INK2, MUTED, PALETTE, Style, plt, run_config, save_fig, save_gif, save_snapshots,
                    share_plot, write_json)
import spatial as sp

OUT = DOCS / "watchdog"
ROUNDS = 30
SHOW_SEED = 11
CAL_SEEDS = [201, 202, 203, 204, 205]
TEST_SEEDS = [101, 102, 103, 104, 105]
CAL_CONTROL_SEEDS = list(range(201, 221))   # 20 seeds x 2 drift levels = 40 controls
TEST_CONTROL_SEEDS = list(range(101, 121))
STRESS_SEEDS = list(range(301, 321))       # safety margin: drift x1.5
ENGINE_THRESHOLD = 0.05
COLORS = {"ana": PALETTE[0], "ben": PALETTE[1], "cyd": PALETTE[6]}

PEOPLE = sp.electorate()
SWING = sp.swing_order(PEOPLE)
CORE = sp.core_order(PEOPLE)

# id, label, targets, per-person step, total budget, policy, drift
VARIANTS = [
    ("W1", "Blitz: 25 swing voters, 0.35/round", SWING[:25], 0.35, 5.0, "toward_target", 0.01),
    ("W2", "Fast: 25 swing, 0.12/round", SWING[:25], 0.12, 5.0, "toward_target", 0.01),
    ("W3", "Steady: 25 swing, 0.05/round", SWING[:25], 0.05, 5.0, "toward_target", 0.01),
    ("W4", "Slow drip: 25 swing, 0.02/round", SWING[:25], 0.02, 5.0, "toward_target", 0.01),
    ("W5", "Hide in noise: slow drip, drift 0.03", SWING[:25], 0.02, 5.0, "toward_target", 0.03),
    ("W6", "Concentrated: 10 swing, 0.15/round", SWING[:10], 0.15, 3.0, "toward_target", 0.01),
    ("W7", "Broad shallow: 50 voters, 0.02/round", SWING[:50], 0.02, 6.0, "toward_target", 0.01),
    ("W8", "Random-direction push", SWING[:25], 0.10, 5.0, "random", 0.01),
    ("W9", "Under-funded: steady, budget 1.0", SWING[:25], 0.05, 1.0, "toward_target", 0.01),
    ("W10", "Wrong targets: 25 core opponents", CORE[:25], 0.05, 5.0, "toward_target", 0.01),
]


def attack(targets, step, budget, policy):
    return {"target": sp.TARGET, "policy": policy, "targets": list(targets), "per_person_round": step,
            "total_budget": budget, "observe_target_ideals": True}


def simulate(name, targets, step, budget, policy, drift, seed, save=False):
    cfg = sp.base_config(PEOPLE, seed, ROUNDS, drift, attack(targets, step, budget, policy), ENGINE_THRESHOLD)
    return run_config(name, cfg, OUT / "configs" if save else None)


def control(drift, seed, save=False, name="control"):
    return simulate(name, SWING[:1], 0.0, 0.0, "none", drift, seed, save)


# ------------------------------------------------------------------ detectors
def target_share(run):
    return run.shares(sp.TARGET)


def detect(series, kind, a, b):
    """First alert round (>=1) using only the public target-share series, or None."""
    if kind == "single":
        tau = a
        for t in range(1, len(series)):
            if series[t] - series[t - 1] > tau + 1e-12:
                return t
    elif kind == "window":
        w, tau = a, b
        for t in range(1, len(series)):
            if series[t] - series[max(0, t - w)] > tau + 1e-12:
                return t
    elif kind == "cusum":
        k, h = a, b
        s = 0.0
        for t in range(1, len(series)):
            s = max(0.0, s + (series[t] - series[t - 1]) - k)
            if s > h + 1e-12:
                return t
    return None


def detector_family():
    fam = [("single", tau, None) for tau in np.round(np.arange(0.0, 0.105, 0.01), 3)]
    fam += [("window", w, tau) for w in (2, 3, 5, 8) for tau in np.round(np.arange(0.02, 0.165, 0.01), 3)]
    fam += [("cusum", k, h) for k in (0.0, 0.005, 0.01) for h in np.round(np.arange(0.01, 0.105, 0.01), 3)]
    return fam


def det_name(d):
    kind, a, b = d
    if kind == "single":
        return f"single-round Δ > {a:.2f}"
    if kind == "window":
        return f"{a}-round rise > {b:.2f}"
    return f"CUSUM k={a:.3f} h={b:.2f}"


def onset(run):
    for f in run.frames[1:]:
        if any(cost > 0 for *_, cost in f.alignment_changes):
            return f.round
    return None


def triple(run):
    return run.frames[-1].detector.first_triple_win_round


def classify(alert, start, t3):
    """Watchdog outcome for an attack run."""
    if start is None:  # attack never spent anything
        return "false alarm" if alert is not None else "quiet (no attack)"
    if alert is not None and alert < start:
        return "false alarm"
    if t3 is None:
        return "caught (attack failed anyway)" if alert is not None else "harmless, no alert"
    if alert is None:
        return "missed"
    return "caught before win" if alert < t3 else "too late"


WIN = {"caught before win", "caught (attack failed anyway)", "harmless, no alert", "quiet (no attack)"}


def evaluate(det, attacks, controls):
    kind, a, b = det
    fa = sum(detect(target_share(c), kind, a, b) is not None for c in controls) / len(controls)
    harmful = [r for r in attacks if triple(r) is not None]
    caught = [r for r in harmful if (al := detect(target_share(r), kind, a, b)) is not None and al < triple(r)]
    delays = [detect(target_share(r), kind, a, b) - onset(r) for r in caught]
    return {"false_alarm_rate": fa, "harmful": len(harmful), "caught": len(caught),
            "catch_rate": len(caught) / len(harmful) if harmful else float("nan"),
            "mean_delay": stats.mean(delays) if delays else None}


def choose(results):
    """Optimal watchdog: silent on calibration controls AND on stress controls with 1.5x natural drift,
    then maximal pre-win catch rate, then fastest detection."""
    ok = [(d, r) for d, r in results if r["false_alarm_rate"] == 0.0 and r["stress_false_alarm_rate"] == 0.0]
    return max(ok, key=lambda x: (x[1]["catch_rate"], -(x[1]["mean_delay"] or 99)))


# ------------------------------------------------------------------ plotting
def style_for(run, title):
    attacked = set(run.config["alignment"]["attack"]["targets"]) if run.config["alignment"]["attack"]["policy"] != "none" else set()

    def profile(p):
        if p in sp.CANDIDATES:
            return "candidate platform"
        return "attacked voter" if p in attacked else "resident"
    return Style(profile, {"resident": "o", "attacked voter": "^", "candidate platform": "*"}, COLORS,
                 {"candidate platform": 260, "attacked voter": 46}, edge_layers=(), title=title)


def issue_positions(frame):
    pos = sp.ideal_positions(frame)
    pos.update({c: p for c, p in sp.CANDIDATES.items()})
    return pos


def detector_panel(ax, run, ctrl, det, title):
    s, c = target_share(run), target_share(ctrl)
    rounds = list(range(len(s)))
    ax.plot(rounds, s, color=PALETTE[6], lw=2, label="target share (attack)")
    ax.plot(rounds, c, color=MUTED, lw=1.5, ls="--", label="target share (control)")
    diffs = [0] + [s[t] - s[t - 1] for t in range(1, len(s))]
    ax.bar(rounds, diffs, color=PALETTE[3], alpha=0.55, width=0.7, label="one-round change")
    ax.axhline(ENGINE_THRESHOLD, color=PALETTE[3], lw=0.9, ls=":")
    al, t3, on = detect(s, *det), triple(run), onset(run)
    for x, lab, col, y in ((on, "onset", INK2, 0.94), (al, "alert", PALETTE[7], 0.86), (t3, "3rd win", INK, 0.78)):
        if x is not None:
            ax.axvline(x, color=col, lw=1.2, ls="--")
            ax.text(x + 0.3, y, f"{lab} r{x}", color=col, fontsize=7.5, transform=ax.get_xaxis_transform())
    ax.set_ylim(-0.12, 0.7)
    ax.set_title(title, fontsize=9.5)
    ax.set_xlabel("Round")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fam = detector_family()

    # ---- 10 showcase simulations + controls
    show, show_ctrl = [], []
    for vid, label, targets, step, budget, policy, drift in VARIANTS:
        show.append(simulate(vid, targets, step, budget, policy, drift, SHOW_SEED, save=True))
        show_ctrl.append(control(drift, SHOW_SEED, save=True, name=f"{vid}_control"))

    # ---- calibration and held-out sets
    cal_att, cal_ctrl, test_att, test_ctrl = [], [], [], []
    for seed in CAL_SEEDS + TEST_SEEDS:
        atts = [simulate(v[0], *v[2:], seed) for v in VARIANTS]
        (cal_att if seed in CAL_SEEDS else test_att).extend(atts)
    drifts = sorted({v[6] for v in VARIANTS})
    cal_ctrl = [control(d, s) for s in CAL_CONTROL_SEEDS for d in drifts]
    test_ctrl = [control(d, s) for s in TEST_CONTROL_SEEDS for d in drifts]

    stress_ctrl = [control(round(d * 1.5, 4), s) for s in STRESS_SEEDS for d in drifts]
    cal = []
    for d in fam:
        r = evaluate(d, cal_att, cal_ctrl)
        r["stress_false_alarm_rate"] = sum(detect(target_share(c), *d) is not None for c in stress_ctrl) / len(stress_ctrl)
        cal.append((d, r))
    best, best_cal = choose(cal)
    engine = ("single", ENGINE_THRESHOLD, None)
    families = {kind: choose([(d, r) for d, r in cal if d[0] == kind]) for kind in ("single", "window", "cusum")}
    test = {name: evaluate(d, test_att, test_ctrl) for name, d in
            [("engine default", engine)] + [(f"best {k}", v[0]) for k, v in families.items()]}

    # ---- outcomes for the 10 showcase simulations
    rows = []
    for run, ctrl, v in zip(show, show_ctrl, VARIANTS):
        s = target_share(run)
        row = {"id": v[0], "variant": v[1], "drift": v[6], "onset": onset(run), "third_win": triple(run),
               "final_target_share": round(s[-1], 2), "max_one_round_jump": round(max(s[t] - s[t - 1] for t in range(1, len(s))), 2),
               "attack_spend": round(run.frames[-1].alignment_spend, 2),
               "engine_alert": run.frames[-1].detector.first_alert_round,
               "engine_outcome": classify(detect(s, *engine), onset(run), triple(run)),
               "optimal_alert": detect(s, *best), "optimal_outcome": classify(detect(s, *best), onset(run), triple(run)),
               "control_false_alarm_engine": detect(target_share(ctrl), *engine) is not None,
               "control_false_alarm_optimal": detect(target_share(ctrl), *best) is not None}
        rows.append(row)

    # ---- attacker best response against the selected watchdog (held-out seeds)
    steps = [0.01, 0.015, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2, 0.35]
    sizes = [10, 25, 40, 60]
    grid = {}
    for step, n in itertools.product(steps, sizes):
        outcomes = []
        for seed in TEST_SEEDS:
            r = simulate("g", SWING[:n], step, 5.0, "toward_target", 0.01, seed)
            s = target_share(r)
            outcomes.append({"t3": triple(r), "engine": classify(detect(s, *engine), onset(r), triple(r)),
                             "optimal": classify(detect(s, *best), onset(r), triple(r))})
        grid[(step, n)] = outcomes

    def undetected_wins(key, det):
        return sum(o[det] in ("missed", "too late") for o in grid[key]) / len(grid[key])
    best_attack = max(grid, key=lambda k: (undetected_wins(k, "optimal"),
                                           -stats.mean([o["t3"] or 99 for o in grid[k]])))
    best_attack_engine = max(grid, key=lambda k: (undetected_wins(k, "engine"),
                                                  -stats.mean([o["t3"] or 99 for o in grid[k]])))

    summary = {
        "showcase": rows,
        "engine_detector": det_name(engine),
        "optimal_detector": det_name(best), "optimal_detector_calibration": best_cal,
        "best_per_family_calibration": {k: {"detector": det_name(v[0]), **v[1]} for k, v in families.items()},
        "held_out": test,
        "attacker_best_response_vs_optimal": {"per_person_round": best_attack[0], "targets": best_attack[1],
                                              "undetected_win_rate": undetected_wins(best_attack, "optimal"),
                                              "mean_third_win_round": stats.mean([o["t3"] or float("nan") for o in grid[best_attack]])},
        "attacker_best_response_vs_engine": {"per_person_round": best_attack_engine[0], "targets": best_attack_engine[1],
                                             "undetected_win_rate": undetected_wins(best_attack_engine, "engine")},
        "attacker_grid": {f"{k[0]}|{k[1]}": v for k, v in grid.items()},
        "runs": {"showcase": 20, "calibration": len(cal_att) + len(cal_ctrl) + len(stress_ctrl), "held_out": len(test_att) + len(test_ctrl),
                 "attacker_grid": len(grid) * len(TEST_SEEDS)},
    }
    write_json(OUT / "summary.json", summary)

    # ================================================================ figures
    # 1. ten panels
    fig, axes = plt.subplots(2, 5, figsize=(19, 7.4), sharey=True)
    for ax, run, ctrl, v, row in zip(axes.flat, show, show_ctrl, VARIANTS, rows):
        detector_panel(ax, run, ctrl, best, f"{v[0]} {v[1]}\n→ {row['optimal_outcome']}")
    axes[0][0].legend(fontsize=7, loc="center right")
    fig.suptitle(f"Ten attack variants (seed {SHOW_SEED}) under the optimal watchdog: {det_name(best)}",
                 x=0.01, ha="left", fontweight="bold")
    save_fig(fig, OUT / "w01_ten_simulations.png")

    # 2. outcome matrix: detectors x showcase runs
    dets = [engine] + [families[k][0] for k in ("single", "window", "cusum")]
    names = ["engine default\n" + det_name(engine)] + [f"best {k}\n" + det_name(families[k][0]) for k in ("single", "window", "cusum")]
    order = ["caught before win", "caught (attack failed anyway)", "harmless, no alert", "too late", "missed", "false alarm"]
    cmap = {"caught before win": "#1baf7a", "caught (attack failed anyway)": "#9edcc4", "harmless, no alert": "#d8eee4",
            "too late": "#eda100", "missed": "#e34948", "false alarm": "#6250d6", "quiet (no attack)": "#eeeeee"}
    fig, ax = plt.subplots(figsize=(13, 3.6))
    for i, d in enumerate(dets):
        for j, (run, ctrl) in enumerate(zip(show, show_ctrl)):
            s = target_share(run)
            out = classify(detect(s, *d), onset(run), triple(run))
            if detect(target_share(ctrl), *d) is not None:
                out = "false alarm"
            ax.add_patch(plt.Rectangle((j, i), 0.96, 0.92, color=cmap[out]))
            al = detect(s, *d)
            ax.text(j + 0.48, i + 0.46, f"alert r{al}" if al is not None else "no alert", ha="center", va="center", fontsize=7.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(len(dets), 0)
    ax.set_xticks([j + 0.48 for j in range(10)], [v[0] for v in VARIANTS])
    ax.set_yticks([i + 0.46 for i in range(len(dets))], names, fontsize=8)
    ax.grid(False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=cmap[k], label=k) for k in order], ncol=6, fontsize=7.5,
              loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_title("Watchdog outcome per attack (cell = alert round; a control false alarm marks the whole cell)")
    save_fig(fig, OUT / "w02_outcome_matrix.png")

    # 3. calibration trade-off
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for k, c, m in (("single", PALETTE[0], "o"), ("window", PALETTE[1], "s"), ("cusum", PALETTE[2], "^")):
        pts = [(r["false_alarm_rate"], r["catch_rate"]) for d, r in cal if d[0] == k]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], color=c, marker=m, s=26, alpha=0.75, label=k)
    ax.scatter([best_cal["false_alarm_rate"]], [best_cal["catch_rate"]], s=180, facecolors="none", edgecolors=INK, lw=1.6)
    ax.annotate(f"selected: {det_name(best)}", (best_cal["false_alarm_rate"], best_cal["catch_rate"]),
                xytext=(0.25, 0.25), textcoords="axes fraction", arrowprops=dict(arrowstyle="->", color=INK2), fontsize=9)
    ax.set_xlabel("False-alarm rate on no-attack controls (calibration seeds)")
    ax.set_ylabel("Share of winning attacks caught before 3rd win")
    ax.set_title("Detector strategies: catch rate vs false alarms")
    ax.legend(title="detector family")
    save_fig(fig, OUT / "w03_detector_tradeoff.png")

    # 4. held-out comparison
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    labels = list(test)
    x = np.arange(len(labels))
    ax.bar(x - 0.2, [test[l]["catch_rate"] for l in labels], 0.38, color=PALETTE[2], label="caught before 3rd win")
    ax.bar(x + 0.2, [test[l]["false_alarm_rate"] for l in labels], 0.38, color=PALETTE[6], label="false-alarm rate")
    for i, l in enumerate(labels):
        ax.text(i - 0.2, test[l]["catch_rate"] + 0.02, f"{test[l]['catch_rate']:.0%}", ha="center", fontsize=8.5)
        ax.text(i + 0.2, test[l]["false_alarm_rate"] + 0.02, f"{test[l]['false_alarm_rate']:.0%}", ha="center", fontsize=8.5)
    ax.set_xticks(x, [l + "\n" + (det_name(engine) if l == "engine default" else det_name(families[l.split()[1]][0])) for l in labels], fontsize=8)
    ax.set_ylim(0, 1.15)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_title(f"Held-out seeds {TEST_SEEDS[0]}–{TEST_SEEDS[-1]}: {len(test_att)} attack + {len(test_ctrl)} control runs")
    save_fig(fig, OUT / "w04_held_out.png")

    # 5. attacker grid
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for ax, key, title in ((axes[0], "engine", f"vs engine default ({det_name(engine)})"),
                           (axes[1], "optimal", f"vs optimal watchdog ({det_name(best)})")):
        M = np.array([[undetected_wins((st, n), key) for st in steps] for n in sizes])
        im = ax.imshow(M, cmap="Reds", vmin=0, vmax=1, aspect="auto")
        for i in range(len(sizes)):
            for j in range(len(steps)):
                t3s = [o["t3"] for o in grid[(steps[j], sizes[i])] if o["t3"]]
                ax.text(j, i, f"{M[i, j]:.0%}\n" + (f"t3≈{stats.mean(t3s):.0f}" if t3s else "no win"), ha="center", va="center", fontsize=7)
        ax.set_xticks(range(len(steps)), steps)
        ax.set_yticks(range(len(sizes)), sizes)
        ax.set_xlabel("Per-voter push per round (L2)")
        ax.set_ylabel("Voters targeted")
        ax.set_title("Undetected attacker wins " + title, fontsize=10)
        ax.grid(False)
    save_fig(fig, OUT / "w05_attacker_best_response.png")

    # 6. what leads to victory / loss
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for row, v in zip(rows, VARIANTS):
        col = cmap.get(row["optimal_outcome"], MUTED)
        ax.scatter(row["max_one_round_jump"], row["third_win"] or ROUNDS + 1, s=140, color=col, edgecolors=INK)
        ax.annotate(v[0], (row["max_one_round_jump"], row["third_win"] or ROUNDS + 1), xytext=(6, 4), textcoords="offset points", fontsize=8.5)
    ax.axvline(families["single"][0][1], color=INK2, ls=":", lw=1)
    ax.text(families["single"][0][1] + 0.003, 1.5, "best single-round threshold", fontsize=8, color=INK2)
    ax.set_xlabel("Largest one-round rise in target share")
    ax.set_ylabel(f"Round of 3rd consecutive target win ({ROUNDS + 1} = never)")
    ax.set_title("Attack pace decides the outcome: fast attacks are loud, slow ones are late")
    ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=cmap[k], markeredgecolor=INK, label=k) for k in order[:5]],
              fontsize=7.5, loc="upper right")
    save_fig(fig, OUT / "w06_pace_vs_outcome.png")

    # 7. GIFs + snapshots for four representative runs
    for idx in (0, 2, 4, 8):
        run = show[idx]
        st = style_for(run, f"{VARIANTS[idx][0]} issue space")
        save_gif(run, st, OUT / f"{VARIANTS[idx][0]}_issue_space.gif", positions_fn=issue_positions,
                 subtitle_fn=lambda f, r=run: "   ALERT" if f.round >= (detect(target_share(r), *best) or 999) else "")
        save_snapshots(run, st, OUT / f"{VARIANTS[idx][0]}_snapshots.png", [0, 3, 8, ROUNDS], issue_positions)
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    share_plot(axes[0], show[3], COLORS, "W4 slow drip: shares", {"3rd win": triple(show[3])})
    share_plot(axes[1], show_ctrl[3], COLORS, "Paired control (no attack)")
    save_fig(fig, OUT / "w07_slow_drip_vs_control.png")
    print({k: summary[k] for k in ("optimal_detector", "optimal_detector_calibration", "held_out",
                                   "attacker_best_response_vs_optimal", "attacker_best_response_vs_engine", "runs")})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
