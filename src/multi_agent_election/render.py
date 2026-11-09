"""Render actual recorded frames; Pillow is an optional visualization dependency."""

import colorsys
import html
import math
from pathlib import Path
from .metrics import series
from .model import ElectionError, Scenario, Frame


def _palette(index: int) -> tuple[int, int, int]:
    hue = ((150 + index * 137.508) % 360) / 360
    return tuple(round(x * 255) for x in colorsys.hls_to_rgb(hue, 0.42, 0.55))


def _pillow():
    try:
        from PIL import Image, ImageDraw
        return Image, ImageDraw
    except ImportError as exc:
        raise ElectionError("PNG/GIF export requires Pillow; install requirements-visualization.txt") from exc


def _save(image, path: Path, fmt: str, **kwargs) -> None:
    with path.open("xb") as handle:
        image.save(handle, format=fmt, **kwargs)


def network_image(scenario: Scenario, frame: Frame):
    Image, ImageDraw = _pillow()
    image = Image.new("RGB", (800, max(600, 565 + ((len(scenario.parties) - 1) // 6) * 16)), "white")
    draw = ImageDraw.Draw(image)
    positions, preferences = dict(frame.positions), dict(frame.preferences)
    def xy(person):
        x, y = positions[person]
        return 55 + int(x * 690), 515 - int(y * 450)
    draw.text((25, 18), f"Eclipse network - round {frame.round} - true first preference", fill="#183c38")
    draw.text((25, 35), "Arrows: sender to recipient; orange = campaign, blue = persistent, gray = proximity", fill="#183c38")
    def arrow(a, b, color, ox=0, oy=0):
        x1, y1 = xy(a); x2, y2 = xy(b)
        distance = math.hypot(x2 - x1, y2 - y1)
        x1 += ox; x2 += ox; y1 += oy; y2 += oy
        if distance <= 12:
            # Coincident/near-coincident nodes cannot show direction at this scale.
            draw.line((x1, y1, x2, y2), fill=color, width=1)
            return
        ux, uy = (x2 - x1) / distance, (y2 - y1) / distance
        tip_x, tip_y = x2 - 8 * ux, y2 - 8 * uy
        base_x, base_y = tip_x - 8 * ux, tip_y - 8 * uy
        draw.line((x1, y1, tip_x, tip_y), fill=color, width=1)
        draw.polygon(((tip_x, tip_y), (base_x - 3 * uy, base_y + 3 * ux),
                      (base_x + 3 * uy, base_y - 3 * ux)), fill=color)
    edges = {}
    for values, color in ((frame.proximity_edges, "#a2aaa6"),
                          (frame.persistent_edges, "#526f91"),
                          (frame.campaign_edges, "#bf6636")):
        for a, b in sorted(values):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b, color))
    for (first, second), layers in sorted(edges.items()):
        ax, ay = xy(first); bx, by = xy(second)
        distance = math.hypot(bx - ax, by - ay)
        nx, ny = (-(by - ay) / distance, (bx - ax) / distance) if distance else (0, 1)
        for index, (a, b, color) in enumerate(layers):
            offset = (index - (len(layers) - 1) / 2) * 6
            arrow(a, b, color, nx * offset, ny * offset)
    for person, position in positions.items():
        x, y = xy(person)
        color = _palette(scenario.parties.index(preferences[person][0]))
        draw.ellipse((x-5, y-5, x+5, y+5), fill=color, outline="#ffffff", width=1)
    for index, party in enumerate(scenario.parties):
        x = 25 + (index % 6) * 125; y = 545 + (index // 6) * 16
        draw.ellipse((x, y, x+9, y+9), fill=_palette(index))
        draw.text((x+13, y-2), party, fill="#183c38")
    return image


def export_network(scenario: Scenario, frame: Frame, path: Path) -> None:
    _save(network_image(scenario, frame), path, "PNG")


def export_gif(scenario: Scenario, frames: list[Frame], path: Path, stride: int, fps: int) -> None:
    if isinstance(stride, bool) or not isinstance(stride, int) or stride < 1:
        raise ElectionError("stride must be a positive integer")
    if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 100:
        raise ElectionError("fps must be an integer between 1 and 100")
    selected = frames[::stride]
    if selected[-1] is not frames[-1]:
        selected.append(frames[-1])
    images = [network_image(scenario, frame) for frame in selected]
    _save(images[0], path, "GIF", save_all=True, append_images=images[1:], duration=round(1000/fps), loop=0)


def export_metric_plot(parties, rows, path: Path) -> None:
    """Plot recorded per-round first-choice shares, including streamed runs."""
    if not rows:
        raise ElectionError("cannot plot a run with no recorded rounds")
    first, last = rows[0]["round"], rows[-1]["round"]
    if any(a["round"] >= b["round"] for a, b in zip(rows, rows[1:])):
        raise ElectionError("plot rounds must be strictly increasing")
    height = max(540, 510 + ((len(parties) - 1) // 6) * 16)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{height}" viewBox="0 0 800 {height}">',
             f'<rect width="800" height="{height}" fill="white"/>',
             '<text x="25" y="30" font-family="sans-serif" font-size="16">First-choice vote share by round</text>',
             '<path d="M55 95 V455 H755" fill="none" stroke="#526b61"/>',
             '<text x="15" y="100" font-family="sans-serif" font-size="12">1.0</text>',
             '<text x="15" y="455" font-family="sans-serif" font-size="12">0.0</text>',
             f'<text x="55" y="472" font-family="sans-serif" font-size="12">Round {first}</text>',
             f'<text x="680" y="472" font-family="sans-serif" font-size="12">Round {last}</text>']
    for i, party in enumerate(parties):
        r, g, b = _palette(i)
        points = [(55 + (row["round"] - first) * 700 / max(1, last - first),
                   455 - row["shares"][party] * 360) for row in rows]
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
        lines.append(f'<polyline points="{coords}" fill="none" stroke="rgb({r},{g},{b})" stroke-width="2"/>')
        if len(points) == 1:
            x, y = points[0]
            lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="rgb({r},{g},{b})"/>')
        lines.append(f'<text x="{55+(i%6)*120}" y="{490+(i//6)*16}" font-family="sans-serif" font-size="12" fill="rgb({r},{g},{b})">{html.escape(party)}</text>')
    lines.append('</svg>')
    with path.open("x", encoding="utf-8") as handle:
        handle.write('\n'.join(lines) + '\n')


def export_plot(scenario: Scenario, frames: list[Frame], path: Path, format: str) -> None:
    if not frames or any(a.round >= b.round for a, b in zip(frames, frames[1:])):
        raise ElectionError("plot frames must have strictly increasing rounds")
    data = series(scenario, frames)
    height = max(540, 510 + ((len(scenario.parties) - 1) // 6) * 16)
    x_at = lambda frame: 55 + (frame.round - frames[0].round) * 700 / max(1, frames[-1].round - frames[0].round)
    points = lambda party: [(x_at(frame), 455 - row["shares"][party] * 360)
                            for frame, row in zip(frames, data)]
    if format == "svg":
        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{height}" viewBox="0 0 800 {height}">',
                 f'<rect width="800" height="{height}" fill="white"/>',
                 '<text x="25" y="30" font-family="sans-serif" font-size="16">First-choice vote share by round</text>',
                 '<path d="M55 95 V455 H755" fill="none" stroke="#526b61"/>',
                 '<text x="15" y="100" font-family="sans-serif" font-size="12">1.0</text>',
                 '<text x="15" y="455" font-family="sans-serif" font-size="12">0.0</text>',
                 f'<text x="55" y="472" font-family="sans-serif" font-size="12">Round {frames[0].round}</text>',
                 f'<text x="680" y="472" font-family="sans-serif" font-size="12">Round {frames[-1].round}</text>']
        for i, party in enumerate(scenario.parties):
            r,g,b = _palette(i)
            coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points(party))
            lines.append(f'<polyline points="{coords}" fill="none" stroke="rgb({r},{g},{b})" stroke-width="2"/>')
            if len(data) == 1:
                x,y=points(party)[0]
                lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="rgb({r},{g},{b})"/>')
            lines.append(f'<text x="{55+(i%6)*120}" y="{490+(i//6)*16}" font-family="sans-serif" font-size="12" fill="rgb({r},{g},{b})">{html.escape(party)}</text>')
        for idx, frame in enumerate(frames):
            if frame.interventions:
                x = x_at(frame)
                lines.append(f'<path d="M{x:.2f} 95 V455" stroke="#555" stroke-dasharray="4 4"><title>Intervention round {frame.round}</title></path>')
        if any(frame.interventions for frame in frames):
            lines.append('<text x="500" y="30" font-family="sans-serif" font-size="11">Dashed line: recorded intervention</text>')
        lines.append('</svg>')
        with path.open("x", encoding="utf-8") as handle:
            handle.write('\n'.join(lines) + '\n')
    elif format == "png":
        Image, ImageDraw = _pillow()
        image = Image.new("RGB", (800, height), "white"); draw = ImageDraw.Draw(image)
        draw.text((25, 20), "First-choice vote share by round", fill="#183c38")
        draw.line((55,95,55,455,755,455), fill="#526b61", width=1)
        draw.text((15,90), "1.0", fill="#183c38"); draw.text((15,450), "0.0", fill="#183c38")
        draw.text((55,458), f"Round {frames[0].round}", fill="#183c38")
        draw.text((680,458), f"Round {frames[-1].round}", fill="#183c38")
        for i, party in enumerate(scenario.parties):
            coords = points(party); color = _palette(i)
            if len(coords) == 1:
                x,y=coords[0]; draw.ellipse((x-2,y-2,x+2,y+2),fill=color)
            else:
                draw.line(coords, fill=color, width=2)
            draw.text((55+(i%6)*120, 475+(i//6)*16), party, fill=color)
        for idx, frame in enumerate(frames):
            if frame.interventions:
                x=x_at(frame)
                draw.line((x,95,x,455), fill="#777777", width=1)
        if any(frame.interventions for frame in frames):
            draw.text((500, 20), "Gray line: recorded intervention", fill="#555555")
        _save(image, path, "PNG")
    else:
        raise ElectionError("plot format must be png or svg")


def export_comparison(result: dict, path: Path, format: str) -> None:
    """Plot seed-paired mean target-share differences by round."""
    target = result["target"]
    rows = result["rows"]
    count = len(rows[0]["control"])
    deltas = [sum(row["treated"][i]["shares"][target] - row["control"][i]["shares"][target]
                  for row in rows) / len(rows) for i in range(count)]
    points = [(55 + i * 700 / max(1, count-1), 275 - value * 180) for i, value in enumerate(deltas)]
    event_rounds = [i for i in range(count) if any(row["treated"][i]["intervention_origin_counts"]["scheduled"] for row in rows)]
    if format == "svg":
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
        lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="520" viewBox="0 0 800 520">',
                 '<rect width="800" height="520" fill="white"/>',
                 f'<text x="25" y="30" font-family="sans-serif" font-size="16">Paired target-share change: {html.escape(target)}</text>',
                 '<path d="M55 95 V455 H755 M55 275 H755" fill="none" stroke="#879c92"/>',
                 '<text x="15" y="100" font-family="sans-serif" font-size="12">+1</text>',
                 '<text x="15" y="280" font-family="sans-serif" font-size="12">0</text>',
                 '<text x="15" y="455" font-family="sans-serif" font-size="12">-1</text>',
                 f'<polyline points="{coords}" fill="none" stroke="#176f55" stroke-width="3"/>']
        if count == 1:
            x,y=points[0]; lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#176f55"/>')
        for i in event_rounds:
            x=55+i*700/max(1,count-1)
            lines.append(f'<path d="M{x:.2f} 95 V455" stroke="#555" stroke-dasharray="4 4"><title>Intervention round {i}</title></path>')
        if event_rounds:
            lines.append('<text x="500" y="48" font-family="sans-serif" font-size="11">Dashed line: scheduled intervention</text>')
        lines += [f'<text x="55" y="480" font-family="sans-serif" font-size="12">Round 0</text>',
                  f'<text x="670" y="480" font-family="sans-serif" font-size="12">Round {count-1}</text>', '</svg>']
        with path.open("x", encoding="utf-8") as handle:
            handle.write('\n'.join(lines) + '\n')
    elif format == "png":
        Image, ImageDraw = _pillow()
        image = Image.new("RGB", (800, 520), "white"); draw = ImageDraw.Draw(image)
        draw.text((25, 20), f"Paired target-share change: {target}", fill="#183c38")
        draw.line((55,95,55,455,755,455), fill="#879c92"); draw.line((55,275,755,275), fill="#879c92")
        for y, label in ((95, "+1"), (275, "0"), (455, "-1")): draw.text((15,y-5), label, fill="#183c38")
        if len(points) == 1:
            x,y=points[0]; draw.ellipse((x-3,y-3,x+3,y+3),fill="#176f55")
        else: draw.line(points, fill="#176f55", width=3)
        for i in event_rounds:
            x=55+i*700/max(1,count-1); draw.line((x,95,x,455), fill="#777777")
        if event_rounds: draw.text((500, 40), "Gray line: scheduled intervention", fill="#555555")
        draw.text((55,465), "Round 0", fill="#183c38"); draw.text((670,465), f"Round {count-1}", fill="#183c38")
        _save(image, path, "PNG")
    else:
        raise ElectionError("plot format must be png or svg")
