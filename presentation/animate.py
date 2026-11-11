"""Short clips for the slides, rendered from the team's engine (unchanged).

    PYTHONPATH=src:presentation python3 presentation/animate.py [clip ...]

Every clip replays a real engine run of one of the 30 towns (town 8, or town 19 for the
propaganda clip); nothing is drawn by hand. Each clip is an H.264 .mp4 (1600x900, 24 fps,
loops on the slide) plus a .png still that the deck shows wherever video cannot play.

Clips:
  town_spaces    one town's 300 voters in belief space, then flying to their map spots
  exp1_round     full information: who moves in round 1, and nobody after (Experiment 1)
  hearing        one copycat's hearing circle moving with it; what it hears; how it votes
  walk_vs_still  same town, same hearing radius: standing still vs walking, 80 rounds
  propaganda     the same 30 loyal Centre fans with no followers vs 5 followers each, 40 rounds
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyse import run_lines  # noqa: E402
from town import PLATFORMS, Town, build_town, opinions, positions, preferences, types  # noqa: E402

OUT = HERE / "results" / "animations"
W, H, FPS = 1600, 900, 24
BG, INK, INK2, MUTED, GRID = "#FBFAF6", "#14213D", "#3F4756", "#A9A8A2", "#E6E5E1"
PARTIES = ["Left", "Right", "Centre"]
COL = {"Left": "#2a78d6", "Right": "#eb6834", "Centre": "#1baf7a"}
RGB = np.array([matplotlib.colors.to_rgb(COL[p]) for p in PARTIES])
LETTER = {"L": 0, "R": 1, "C": 2}
SEED, SEED_PROP = 8, 19

plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": BG, "axes.facecolor": BG,
                     "savefig.facecolor": BG, "text.color": INK})


# ------------------------------------------------------------------ plumbing

class Clip:
    """Pipe matplotlib frames into ffmpeg; keep one frame as the still."""

    def __init__(self, name: str):
        OUT.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / f"{name}.mp4")],
            stdin=subprocess.PIPE)
        self.frames = 0

    def grab(self, n: int = 1, still: bool = False):
        self.fig.canvas.draw()
        rgb = np.asarray(self.fig.canvas.buffer_rgba())[:, :, :3].copy()
        for _ in range(n):
            self.proc.stdin.write(rgb.tobytes())
        self.frames += n
        if still:
            plt.imsave(OUT / f"{self.name}.png", rgb)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()
        plt.close(self.fig)
        print(f"{self.name}: {self.frames} frames, {self.frames / FPS:.1f} s")


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def runs_record(setting: str, seed: int) -> dict:
    for line in run_lines():
        if f'"setting": "{setting}"' in line and f'"seed": {seed},' in line:
            r = json.loads(line)
            if r["setting"] == setting and r["seed"] == seed:
                return r
    raise KeyError((setting, seed))


def engine_run(town: Town, seed: int):
    """Positions (rounds x N x 2), votes (rounds x N, 0/1/2), proximity edges per round, raw scenario."""
    from multi_agent_election.engine import Simulation
    from multi_agent_election.model import make_scenario
    raw = build_town(town, seed)
    sim = Simulation(make_scenario(raw))
    sim.run()
    ids = sorted(p["id"] for p in raw["people"])
    index = {pid: k for k, pid in enumerate(ids)}
    pos = np.array([[dict(f.positions)[pid] for pid in ids] for f in sim.frames], dtype=float)
    votes = np.array([[PARTIES.index(dict(f.ballots)[pid][0]) for pid in ids] for f in sim.frames])
    edges = [[(index[s], index[r]) for s, r in f.proximity_edges] for f in sim.frames]
    return raw, index, pos, votes, edges


def map_axes(fig, rect, title=None):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(MUTED); s.set_linewidth(1.2)
    ax.set_facecolor("#FFFFFF")
    if title:
        ax.set_title(title, fontsize=22, color=INK, loc="left", pad=12, fontweight="bold")
    return ax


def legend_row(fig, x, y, size=17, counts=None, step=0.085):
    for k, p in enumerate(PARTIES):
        fig.text(x + step * k, y, "●", color=COL[p], fontsize=size + 4, va="center")
        label = p if counts is None else f"{p} {counts[k]}"
        fig.text(x + step * k + 0.017, y, label, color=INK2, fontsize=size, va="center")


def count_strip(fig, rect, votes, rounds):
    """Counts of each party by round, revealed as time passes."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, rounds); ax.set_ylim(0, 200)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=13)
    ax.set_yticks([0, 100, 200])
    ax.grid(axis="y", color=GRID, lw=0.8)
    counts = np.stack([(votes == k).sum(axis=1) for k in range(3)], axis=1)
    lines = [ax.plot([], [], color=COL[p], lw=2.6)[0] for p in PARTIES]
    marker = ax.axvline(0, color=INK2, lw=1, alpha=0.6)
    return ax, counts, lines, marker


def update_strip(strip, t):
    ax, counts, lines, marker = strip
    t_int = int(np.floor(t))
    xs = np.arange(t_int + 1)
    for k, ln in enumerate(lines):
        ln.set_data(xs, counts[: t_int + 1, k])
    marker.set_xdata([t, t])


# ------------------------------------------------------------------ 1. two spaces

def clip_town_spaces():
    t = Town()
    belief = np.array(opinions(t, SEED)); start = np.array(positions(t, SEED))
    fav = np.array([PARTIES.index(p[0]) for p in preferences(t, SEED)])
    clip = Clip("town_spaces"); fig = clip.fig
    axL = map_axes(fig, [0.04, 0.19, 0.42, 0.66], "Belief space: whom you like")
    axR = map_axes(fig, [0.54, 0.19, 0.42, 0.66], "Map: whom you hear")
    axL.set_xlabel("issue 1", fontsize=16, color=INK2); axL.set_ylabel("issue 2", fontsize=16, color=INK2)
    for p, (x, y) in PLATFORMS.items():
        axL.scatter([x], [y], s=520, marker="*", color=COL[p], edgecolors=INK, linewidths=1.4, zorder=5)
        axL.text(x, y + 0.055, p, ha="center", fontsize=17, fontweight="bold", color=INK, zorder=6,
                 bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.8))
    axL.scatter(belief[:, 0], belief[:, 1], s=34, c=RGB[fav], alpha=0.85, linewidths=0, zorder=3)
    fig.text(0.04, 0.94, f"Town {SEED} of 30: each voter has two places", fontsize=30, fontweight="bold", color=INK)
    first = np.bincount(fav, minlength=3)
    fig.text(0.255, 0.095, "First choices in this town:", fontsize=18, color=INK2, va="center")
    legend_row(fig, 0.465, 0.095, size=18, counts=first, step=0.105)
    caption = fig.text(0.5, 0.025, "", ha="center", fontsize=20, color=INK2)
    fig.canvas.draw()
    to_fig = fig.transFigure.inverted()
    a = to_fig.transform(axL.transData.transform(belief))
    b = to_fig.transform(axR.transData.transform(start))
    overlay = fig.add_axes([0, 0, 1, 1]); overlay.set_xlim(0, 1); overlay.set_ylim(0, 1); overlay.axis("off")
    flyers = overlay.scatter(a[:, 0], a[:, 1], s=34, c=RGB[fav], alpha=0.0, linewidths=0, zorder=10)
    rng = np.random.default_rng(1)
    delay = rng.uniform(0, 0.35, len(fav))
    clip.grab(36)
    n = 84
    for f in range(n):
        u = ease((f / (n - 1) - delay) / 0.65)
        flyers.set_offsets(a + (b - a) * u[:, None])
        flyers.set_alpha(0.9)
        clip.grab()
    caption.set_text("Same 300 people. Where you stand on the map says nothing about what you believe.")
    clip.grab(96, still=True)
    clip.close()


# ------------------------------------------------------------------ 2. experiment 1

def clip_exp1_round():
    r = runs_record("e1", SEED)
    ty = np.array(list(r["types"])); fav = np.array([LETTER[c] for c in r["favourites"]])
    V = np.array([[LETTER[c] for c in v] for v in r["votes"]])
    blocks = [("s", "Sincere", "40%"), ("f", "Front-runner", "30%"), ("c", "Copycat", "20%"), ("p", "Pivot-seeker", "10%")]
    cols, pitch = 30, 1.0
    xy, order = np.zeros((len(fav), 2)), []
    y = 0.0
    label_y = {}
    for code, name, share in blocks:
        members = [i for i in range(len(fav)) if ty[i] == code]
        members.sort(key=lambda i: (fav[i], V[1][i]))
        rows = int(np.ceil(len(members) / cols))
        label_y[code] = -(y + (rows - 1) / 2)
        for k, i in enumerate(members):
            xy[i] = (k % cols * pitch, -(y + k // cols))
        y += rows + 1.2
    clip = Clip("exp1_round"); fig = clip.fig
    ax = fig.add_axes([0.20, 0.10, 0.44, 0.72]); ax.axis("off")
    ax.set_xlim(-0.8, cols - 0.2); ax.set_ylim(-(y - 0.6), 1.0)
    for code, name, share in blocks:
        ax.text(-1.6, label_y[code], f"{name}\n{share}", ha="right", va="center", fontsize=19, color=INK,
                linespacing=1.15, clip_on=False)
    dots = ax.scatter(xy[:, 0], xy[:, 1], s=150, c=RGB[V[0]], linewidths=0)
    rings = ax.scatter(xy[:, 0], xy[:, 1], s=420, facecolors="none", edgecolors=INK, linewidths=2.2, alpha=0)
    bx = fig.add_axes([0.70, 0.14, 0.27, 0.64]); bx.set_xlim(-0.6, 2.6); bx.set_ylim(0, 200); bx.axis("off")
    counts = np.stack([(V == k).sum(axis=1) for k in range(3)], axis=1)
    bars = bx.bar(range(3), counts[0], color=[COL[p] for p in PARTIES], width=0.66)
    vals = [bx.text(k, counts[0][k] + 4, str(counts[0][k]), ha="center", fontsize=24, fontweight="bold", color=INK) for k in range(3)]
    for k, p in enumerate(PARTIES):
        bx.text(k, -12, p, ha="center", va="top", fontsize=19, color=INK2)
    head = fig.text(0.04, 0.92, "", fontsize=29, fontweight="bold", color=INK)
    sub = fig.text(0.04, 0.865, "", fontsize=19, color=INK2)
    rnd = fig.text(0.97, 0.92, "", ha="right", fontsize=26, color=INK2)
    fig.text(0.04, 0.035, f"Town {SEED} of 30 · everyone hears everyone · mix 40/30/20/10 · replayed from the engine",
             fontsize=16, color=INK2)

    def show(round_, colours, cvals):
        dots.set_facecolors(colours)
        for k in range(3):
            bars[k].set_height(cvals[k]); vals[k].set_y(cvals[k] + 4); vals[k].set_text(f"{cvals[k]:.0f}")
        rnd.set_text(f"Round {round_}")

    head.set_text("Round 0: everyone votes for their favourite")
    sub.set_text("Each dot is one voter, grouped by type, coloured by today's vote")
    show(0, RGB[V[0]], counts[0]); clip.grab(60)
    changed = V[1] != V[0]
    n_copy, n_front = int(((ty == "c") & changed).sum()), int(((ty == "f") & changed).sum())
    head.set_text(f"Round 1: everyone reacts to round 0's count; {int(changed.sum())} switch")
    sub.set_text(f"{n_copy} copycats join the leader. {n_front} front-runners leave Centre for one of the top two.")
    n = 40
    for f in range(n):
        u = ease(f / (n - 1))
        col = RGB[V[0]] * (1 - u) + RGB[V[1]] * u
        show(1, col, counts[0] * (1 - u) + counts[1] * u)
        rings.set_alpha(None)
        rings.set_edgecolors([(*matplotlib.colors.to_rgb(INK), 0.9 * np.sin(np.pi * u) if c else 0) for c in changed])
        clip.grab()
    rings.set_edgecolors([(0, 0, 0, 0)] * len(changed))
    clip.grab(36)
    head.set_text("Rounds 2 to 40: nobody moves again")
    sub.set_text("Left leads clearly and the top two stay the same, so no one has a reason to switch")
    for rr in range(2, len(V)):
        show(rr, RGB[V[rr]], counts[rr]); clip.grab(2)
    clip.grab(48, still=True)
    clip.close()


# ------------------------------------------------------------------ 3. the hearing circle

def pick_listener(votes, edges, ty, pos, rounds=12):
    best, score = None, -1
    for i, code in enumerate(ty):
        if code != "copycat":
            continue
        if pos[: rounds + 1, i].min() < 0.12 or pos[: rounds + 1, i].max() > 0.88:
            continue
        changes = sum(votes[t][i] != votes[t - 1][i] for t in range(1, rounds + 1))
        heard = [sum(1 for s, r in edges[t] if r == i) for t in range(1, rounds + 1)]
        if min(heard) < 4 or max(heard) > 14:
            continue
        if changes > score:
            best, score = i, changes
    return best


def clip_hearing(rounds=12):
    town = Town(radius=0.1)
    raw, index, pos, V, E = engine_run(town, SEED)
    ty = types(town, SEED); prefs = preferences(town, SEED)
    me = pick_listener(V, E, ty, pos, rounds)
    clip = Clip("hearing"); fig = clip.fig
    ax = map_axes(fig, [0.03, 0.05, 0.47, 0.86])
    dots = ax.scatter(pos[0][:, 0], pos[0][:, 1], s=46, c=RGB[V[0]], linewidths=0, alpha=0.9, zorder=2)
    nb = ax.scatter([], [], s=120, facecolors="none", edgecolors=INK, linewidths=1.8, zorder=4)
    lines = LineCollection([], colors=INK, linewidths=1.3, alpha=0.55, zorder=3); ax.add_collection(lines)
    ring = Circle(pos[0][me], 0.1, fill=True, facecolor=(0.08, 0.13, 0.24, 0.06), edgecolor=INK, lw=2.4, ls="--", zorder=3)
    ax.add_patch(ring)
    meDot = ax.scatter([pos[0][me][0]], [pos[0][me][1]], s=330, c=[RGB[V[0][me]]], edgecolors=INK, linewidths=3, zorder=6)
    trail, = ax.plot([], [], color=INK, lw=1.4, alpha=0.35, zorder=2)
    fig.text(0.55, 0.88, "One copycat's hearing circle", fontsize=29, fontweight="bold", color=INK)
    fig.text(0.55, 0.80, f"Town {SEED} of 30, radius 0.1, people walking.\nThis copycat ranks {' > '.join(prefs[me])}.",
             fontsize=19, color=INK2, linespacing=1.3)
    rnd = fig.text(0.55, 0.70, "", fontsize=26, color=INK2)
    heard_t = fig.text(0.55, 0.63, "", fontsize=21, color=INK)
    bx = fig.add_axes([0.62, 0.36, 0.30, 0.24]); bx.set_xlim(0, 10); bx.set_ylim(-0.6, 2.6); bx.axis("off")
    bars = bx.barh([2, 1, 0], [0, 0, 0], color=[COL[p] for p in PARTIES], height=0.62)
    blabel = [bx.text(-0.3, 2 - k, p, ha="right", va="center", fontsize=20, color=INK2) for k, p in enumerate(PARTIES)]
    bval = [bx.text(0.2, 2 - k, "", va="center", fontsize=21, fontweight="bold", color=INK) for k in range(3)]
    verdict = fig.text(0.55, 0.25, "", fontsize=24, fontweight="bold", color=INK, linespacing=1.3)
    note = fig.text(0.55, 0.17, "", fontsize=18, color=INK2)
    fig.text(0.55, 0.06, "Everyone else follows their own rule at the same time.\nReplayed from the engine.",
             fontsize=16, color=INK2, linespacing=1.3)
    path = [pos[0][me]]

    def tally(t):
        senders = [s for s, r in E[t] if r == me]
        c = np.bincount(V[t - 1][senders], minlength=3) if senders else np.zeros(3, int)
        return senders, c

    def set_bars(c):
        for k in range(3):
            bars[k].set_width(c[k]); bval[k].set_x(c[k] + 0.25); bval[k].set_text(str(int(c[k])))

    still_round = next(t for t in range(3, rounds + 1) if sorted(tally(t)[1])[-1] > sorted(tally(t)[1])[-2])
    rnd.set_text("Round 0: everyone votes for their favourite")
    clip.grab(36)
    for t in range(1, rounds + 1):
        rnd.set_text(f"Round {t}")
        # 1. everyone takes a small random step
        lines.set_segments([]); nb.set_offsets(np.empty((0, 2)))
        verdict.set_text(""); note.set_text(""); heard_t.set_text("Everyone takes a small random step...")
        for f in range(12):
            u = ease(f / 11)
            P = pos[t - 1] * (1 - u) + pos[t] * u
            dots.set_offsets(P); meDot.set_offsets([P[me]]); ring.center = P[me]
            trail.set_data(*np.array(path + [P[me]]).T)
            clip.grab()
        path.append(pos[t][me])
        # 2. it hears last round's votes of the people now inside its circle
        senders, c = tally(t)
        lines.set_segments([[pos[t][me], pos[t][s]] for s in senders])
        nb.set_offsets(pos[t][senders] if senders else np.empty((0, 2)))
        heard_t.set_text(f"It hears {len(senders)} people's votes from round {t - 1}:")
        set_bars(c)
        choice = PARTIES[V[t][me]]
        verdict.set_text(f"Most common: {choice}\n→ it votes {choice}")
        top = c.max()
        tied = [PARTIES[k] for k in range(3) if c[k] == top]
        note.set_text("A tie: it picks the one it likes more" if len(tied) > 1 else "")
        assert choice in tied, (t, c, choice)
        clip.grab(16, still=(t == still_round))   # still: ring colours = the votes it hears
        # 3. everyone's new vote appears
        for f in range(8):
            u = ease(f / 7)
            dots.set_facecolors(RGB[V[t - 1]] * (1 - u) + RGB[V[t]] * u)
            meDot.set_facecolors([RGB[V[t - 1][me]] * (1 - u) + RGB[V[t][me]] * u])
            clip.grab()
        clip.grab(4)
    clip.grab(24)
    clip.close()
    return me


# ------------------------------------------------------------------ 4. walking vs standing still

def clip_walk_vs_still(rounds=80, per_round=3):
    still = engine_run(Town(radius=0.1, walking=False, rounds=rounds), SEED)
    walk = engine_run(Town(radius=0.1, walking=True, rounds=rounds), SEED)
    clip = Clip("walk_vs_still"); fig = clip.fig
    panels = []
    for k, (name, (raw, index, pos, V, E)) in enumerate([("Standing still", still), ("Walking", walk)]):
        x0 = 0.05 + 0.49 * k
        ax = map_axes(fig, [x0, 0.30, 0.40, 0.56], name)
        dots = ax.scatter(pos[0][:, 0], pos[0][:, 1], s=34, c=RGB[V[0]], linewidths=0, alpha=0.95)
        strip = count_strip(fig, [x0 + 0.02, 0.085, 0.38, 0.13], V, rounds)
        lead = fig.text(x0, 0.255, "", fontsize=19, color=INK)
        panels.append((pos, V, dots, strip, lead))
    rnd = fig.text(0.5, 0.955, "", ha="center", fontsize=24, color=INK2)
    fig.text(0.5, 0.012, f"Town {SEED} of 30 · mix 40/30/20/10 · radius 0.1, about 9 heard · only difference: do people move?",
             ha="center", fontsize=17, color=INK2)
    legend_row(fig, 0.05, 0.955)

    def draw(t):
        ti = int(np.floor(t)); u = t - ti
        for pos, V, dots, strip, lead in panels:
            P = pos[ti] if ti >= len(pos) - 1 else pos[ti] * (1 - u) + pos[ti + 1] * u
            dots.set_offsets(P); dots.set_facecolors(RGB[V[ti]])
            update_strip(strip, ti)
            c = np.bincount(V[ti], minlength=3)
            lead.set_text(f"Leading: {PARTIES[int(np.argmax(c))]}  ({c.max()} votes)")
        rnd.set_text(f"Round {ti}")

    draw(0); clip.grab(24)
    for f in range(rounds * per_round + 1):
        draw(f / per_round); clip.grab()
    draw(rounds); clip.grab(48, still=True)
    clip.close()


# ------------------------------------------------------------------ 5. propaganda

def clip_propaganda(rounds=40, per_round=4, followers=5, seed=SEED_PROP):
    """Both maps have the same 30 loyal Centre fans; the only difference is their followers."""
    def loyal(f):
        return Town(radius=0.2, rounds=rounds, minority=30, minority_party="Centre", followers=f)
    alone = engine_run(loyal(0), seed)
    prop = engine_run(loyal(followers), seed)
    raw, index, _, _, _ = prop
    links = [(index[s], index[r]) for s, r in raw["network"]["persistent_edges"]]
    members = sorted({s for s, _ in links})
    for name, run in (("e4_f0", alone), (f"e4_f{followers}", prop)):   # the replay must match the stored run
        rec = runs_record(name, seed)
        stored = [[c.get(p, 0) for p in PARTIES] for c in rec["counts"]]
        replayed = [np.bincount(v, minlength=3).tolist() for v in run[3]]
        assert stored == replayed, name
    clip = Clip("propaganda"); fig = clip.fig
    panels = []
    titles = ["Loyal 10%, no followers", f"Loyal 10%, {followers} followers each"]
    for k, (title, (raw_, index_, pos, V, E)) in enumerate(zip(titles, [alone, prop])):
        x0 = 0.05 + 0.49 * k
        ax = map_axes(fig, [x0, 0.30, 0.40, 0.56], title)
        lc = None
        if k == 1:
            lc = LineCollection([], colors=COL["Centre"], linewidths=1.1, alpha=0.38, zorder=1); ax.add_collection(lc)
        dots = ax.scatter(pos[0][:, 0], pos[0][:, 1], s=30, c=RGB[V[0]], linewidths=0, alpha=0.95, zorder=2)
        ring = ax.scatter(pos[0][members, 0], pos[0][members, 1], s=150, facecolors="none", edgecolors=INK,
                          linewidths=1.8, zorder=3)
        strip = count_strip(fig, [x0 + 0.02, 0.085, 0.38, 0.13], V, rounds)
        lead = fig.text(x0, 0.255, "", fontsize=19, color=INK)
        panels.append((pos, V, dots, strip, lead, lc, ring))
    rnd = fig.text(0.5, 0.955, "", ha="center", fontsize=24, color=INK2)
    legend_row(fig, 0.05, 0.955)
    fig.text(0.5, 0.012, f"Town {seed} of 30 · radius 0.2, about 32 heard, walking · ringed: the same 30 loyal Centre fans in both"
             f" · green: their {len(links)} follower links",
             ha="center", fontsize=17, color=INK2)

    def draw(t):
        ti = int(np.floor(t)); u = t - ti
        for pos, V, dots, strip, lead, lc, ring in panels:
            P = pos[ti] if ti >= len(pos) - 1 else pos[ti] * (1 - u) + pos[ti + 1] * u
            dots.set_offsets(P); dots.set_facecolors(RGB[V[ti]])
            if lc is not None:
                lc.set_segments([[P[s], P[r]] for s, r in links])
            ring.set_offsets(P[members])
            update_strip(strip, ti)
            c = np.bincount(V[ti], minlength=3)
            top = [PARTIES[k] for k in range(3) if c[k] == c.max()]
            lead.set_text(f"Leading: {top[0]}  ({c.max()} votes)" if len(top) == 1
                          else f"Level: {' and '.join(top)}  ({c.max()} each)")
        rnd.set_text(f"Round {ti}")

    draw(0); clip.grab(30)
    for f in range(rounds * per_round + 1):
        draw(f / per_round); clip.grab()
    draw(rounds); clip.grab(48, still=True)
    clip.close()


CLIPS = {"town_spaces": clip_town_spaces, "exp1_round": clip_exp1_round, "hearing": clip_hearing,
         "walk_vs_still": clip_walk_vs_still, "propaganda": clip_propaganda}

if __name__ == "__main__":
    for name in sys.argv[1:] or CLIPS:
        CLIPS[name]()
