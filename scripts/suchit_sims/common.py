"""Shared helpers for the suchit-sims scenario studies.

Scenarios are built as plain dictionaries, written to TOML (so every run can be
reproduced with the ordinary CLI), parsed back with ``tomllib`` and executed by
the unmodified engine. Plotting uses matplotlib; GIFs are assembled with Pillow.
"""

from __future__ import annotations

import io
import json
import math
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PLUGINS = Path(__file__).resolve().parent / "plugins"
DOCS = ROOT / "docs" / "suchit_sims"
for path in (SRC, PLUGINS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from PIL import Image  # noqa: E402

from multi_agent_election.engine import Simulation  # noqa: E402
from multi_agent_election.model import make_scenario  # noqa: E402

# Validated categorical palette (dataviz reference instance, light mode).
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#9a9993", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 140,
})


# --------------------------------------------------------------------------- TOML
def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        text = repr(round(value, 6))
        return text if ("." in text or "e" in text) else text + ".0"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    if isinstance(value, Mapping):
        return "{ " + ", ".join(f"{k} = {_toml_value(v)}" for k, v in value.items()) + " }"
    raise TypeError(f"unsupported TOML value {value!r}")


def to_toml(data: Mapping[str, Any]) -> str:
    """Serialise the scenario subset of TOML used here (tables, arrays of tables, inline tables)."""
    lines: list[str] = []
    scalars = {k: v for k, v in data.items() if not isinstance(v, Mapping) and not _is_table_list(v)}
    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_value(value)}")

    def table(prefix: str, body: Mapping[str, Any]) -> None:
        simple = {k: v for k, v in body.items() if not (isinstance(v, Mapping) and _is_nested_table(v))}
        nested = {k: v for k, v in body.items() if isinstance(v, Mapping) and _is_nested_table(v)}
        lines.append("")
        lines.append(f"[{prefix}]")
        for k, v in simple.items():
            lines.append(f"{k} = {_toml_value(v)}")
        for k, v in nested.items():
            table(f"{prefix}.{k}", v)

    for key, value in data.items():
        if isinstance(value, Mapping):
            if key == "groups":
                for gid, group in value.items():
                    table(f"groups.{gid}", group)
            else:
                table(key, value)
    for key, value in data.items():
        if _is_table_list(value):
            for item in value:
                lines.append("")
                lines.append(f"[[{key}]]")
                for k, v in item.items():
                    lines.append(f"{k} = {_toml_value(v)}")
    return "\n".join(lines) + "\n"


def _is_table_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, Mapping) for v in value)


def _is_nested_table(value: Mapping[str, Any]) -> bool:
    # Large sub-tables (e.g. alignment.attack) become [a.b] tables; small ones stay inline.
    return any(isinstance(v, (list, Mapping)) for v in value.values()) or len(value) > 3


# --------------------------------------------------------------------------- running
@dataclass
class Run:
    name: str
    config: dict
    frames: list
    seconds: float
    toml_path: Path | None = None
    meta: dict = field(default_factory=dict)

    @property
    def parties(self) -> tuple[str, ...]:
        return tuple(p for p, _ in self.frames[0].counts)

    def shares(self, party: str) -> list[float]:
        return [dict(f.counts)[party] / sum(dict(f.counts).values()) for f in self.frames]

    def winners(self) -> list[str]:
        return [f.winner for f in self.frames]


def run_config(name: str, config: dict, out_dir: Path | None = None, rounds: int | None = None) -> Run:
    """Write ``config`` as TOML, parse it back and run it on the shared engine."""
    text = to_toml(config)
    toml_path = None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        toml_path = out_dir / f"{name}.toml"
        toml_path.write_text(text, encoding="utf-8")
    scenario = make_scenario(tomllib.loads(text))
    start = time.perf_counter()
    sim = Simulation(scenario)
    for _ in range(scenario.rounds if rounds is None else rounds):
        sim.step()
    return Run(name, config, list(sim.frames), time.perf_counter() - start, toml_path)


# --------------------------------------------------------------------------- drawing
SHAPES = ["o", "^", "s", "D", "P", "*", "v", "X", "p", "h"]


@dataclass
class Style:
    """How agents are drawn: shape by profile, colour by current first-choice ballot."""
    profile_of: Callable[[str], str]
    profile_shapes: Mapping[str, str]
    party_colors: Mapping[str, str]
    profile_sizes: Mapping[str, float] = field(default_factory=dict)
    edge_layers: Sequence[str] = ("proximity",)
    highlight_edges: Callable[[Any], Iterable[tuple[str, str, str]]] | None = None  # (a, b, colour)
    title: str = ""

    def legend_handles(self) -> list[Line2D]:
        handles = [Line2D([], [], marker=shape, linestyle="", markersize=8, markerfacecolor="white",
                          markeredgecolor=INK, label=profile) for profile, shape in self.profile_shapes.items()]
        handles += [Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=c,
                           markeredgecolor="white", label=f"votes {p}") for p, c in self.party_colors.items()]
        return handles


def draw_network(ax, frame, style: Style, positions: Mapping[str, Sequence[float]] | None = None,
                 subtitle: str = "") -> None:
    pos = positions if positions is not None else dict(frame.positions)
    ax.clear()
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_aspect("equal")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(GRID)
    ax.set_xticks([])
    ax.set_yticks([])
    if "proximity" in style.edge_layers:
        for a, b in frame.proximity_edges:
            ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#d9d8d3", lw=0.5, zorder=1)
    if "persistent" in style.edge_layers:
        for a, b in frame.persistent_edges:
            ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#9fb6cf", lw=0.6, zorder=1)
    if style.highlight_edges is not None:
        for a, b, colour in style.highlight_edges(frame):
            ax.annotate("", xy=pos[b], xytext=pos[a],
                        arrowprops=dict(arrowstyle="-|>", color=colour, lw=0.9, alpha=0.75, mutation_scale=7), zorder=2)
    ballots = dict(frame.ballots)
    by_profile: dict[str, list[str]] = {}
    for person in pos:
        by_profile.setdefault(style.profile_of(person), []).append(person)
    for profile, people in by_profile.items():
        shape = style.profile_shapes.get(profile, "o")
        size = style.profile_sizes.get(profile, 34)
        ax.scatter([pos[p][0] for p in people], [pos[p][1] for p in people], marker=shape, s=size,
                   c=[style.party_colors.get(ballots[p][0], MUTED) for p in people],
                   edgecolors=INK if profile != "resident" else "white", linewidths=0.8 if profile != "resident" else 0.5,
                   zorder=4 if profile != "resident" else 3)
    counts = dict(frame.counts)
    text = "   ".join(f"{p} {counts[p]}" for p in counts)
    ax.set_title(f"{style.title}  round {frame.round}\n{text}   winner {frame.winner}{subtitle}", fontsize=9.5)


def save_gif(run: Run, style: Style, path: Path, positions_fn: Callable[[Any], Mapping] | None = None,
             subtitle_fn: Callable[[Any], str] | None = None, fps: int = 4, size: float = 5.4) -> Path:
    """Animate every recorded frame; shapes encode agent profile, colours the current ballot."""
    images = []
    for frame in run.frames:
        fig = plt.figure(figsize=(size, size + 0.9))
        ax = fig.add_axes([0.02, 0.15, 0.96, 0.75])
        draw_network(ax, frame, style, positions_fn(frame) if positions_fn else None,
                     subtitle_fn(frame) if subtitle_fn else "")
        fig.legend(handles=style.legend_handles(), loc="lower center", ncol=4, fontsize=7.5, handletextpad=0.3,
                   columnspacing=0.9)
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=78)
        plt.close(fig)
        buffer.seek(0)
        images.append(Image.open(buffer).convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT))
    path.parent.mkdir(parents=True, exist_ok=True)
    durations = [int(1000 / fps)] * (len(images) - 1) + [1800]
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True)
    return path


def save_snapshots(run: Run, style: Style, path: Path, rounds: Sequence[int],
                   positions_fn: Callable[[Any], Mapping] | None = None) -> Path:
    fig, axes = plt.subplots(1, len(rounds), figsize=(3.6 * len(rounds), 4.3))
    for ax, r in zip(axes, rounds):
        frame = run.frames[min(r, len(run.frames) - 1)]
        draw_network(ax, frame, style, positions_fn(frame) if positions_fn else None)
    fig.legend(handles=style.legend_handles(), loc="lower center", ncol=min(8, len(style.legend_handles())), fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def share_plot(ax, run: Run, colors: Mapping[str, str], title: str = "", marks: Mapping[str, int] | None = None) -> None:
    rounds = [f.round for f in run.frames]
    for party in run.parties:
        ax.plot(rounds, run.shares(party), lw=2, color=colors.get(party, MUTED), label=party)
    for label, r in (marks or {}).items():
        if r is not None:
            ax.axvline(r, color=INK2, ls="--", lw=1)
            ax.text(r + 0.2, 0.97, label, fontsize=8, color=INK2, va="top", transform=ax.get_xaxis_transform())
    ax.set_ylim(0, 1)
    ax.set_xlabel("Round")
    ax.set_ylabel("First-choice share")
    ax.set_title(title or run.name)
    ax.legend(loc="upper right", ncol=len(run.parties), fontsize=8)


def save_fig(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
