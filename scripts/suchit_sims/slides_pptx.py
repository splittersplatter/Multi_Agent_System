"""PowerPoint version of the v2 deck with playable GIFs.

Original slides stay native and editable (copied from the team .pptx). The
Part 2 slides are inserted as full-slide images rendered from part2_slides.pdf,
and each experiment gets a "watch it happen" slide with two animated GIFs
(PowerPoint plays animated GIFs in slideshow and normal view).
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "suchit_sims"
OUT = DOCS / "slides"
ORIGINAL = Path.home() / "Downloads" / "Who Wins Depends on Who You Hear.pptx"

PURPLE, NAVY, INK2, GREY, BG = "5B4BC4", "14213D", "3F4756", "6B7280", "FBFAF6"

GIF_SLIDES = {  # inserted after this Part 2 page index (0-based within part2_slides.pdf)
    4: ("Experiment 5 · watch it happen", "A blitz is loud, a slow drip is quiet",
        [("watchdog/W1_issue_space.gif", "W1 blitz: Cyd jumps in round 1, and every alarm fires at once."),
         ("watchdog/W5_issue_space.gif", "W5 slow drip hidden in extra drift: no single round looks unusual.")],
        "Belief space · ▲ nudged voters · ★ candidates · colour = current vote · 'ALERT' shows the 3-round alarm"),
    6: ("Experiment 6 · watch it happen", "Blind lies vs lies with a dossier",
        [("foreign_intelligence/F1_network.gif", "F1 blind: lies (red arrows) spread across whoever follows the spy."),
         ("foreign_intelligence/F2_network.gif", "F2 dossier: lies go to hidden B fans who can tip, and B pulls ahead.")],
        "Town map · ▲ spy · ● trusting · ■ checker · ◆ committed · colour = current vote · seed 1 of 8"),
    7: ("Experiment 7 · watch it happen", "Broad and shallow vs swing voters",
        [("propaganda/P1_issue_space.gif", "P1: 60 voters nudged a little; the whole map slides toward Cyd."),
         ("propaganda/P2_issue_space.gif", "P2: 20 swing voters pushed hard; Cyd leads by round 5.")],
        "Belief space · ▲ targeted voters · ★ candidates · 60 rounds · seed 1 of 5"),
    10: ("Experiment 8 · watch it happen", "Nobody campaigns vs everyone invades",
         [("echo_chambers/echo_pass_pass_pass.gif", "Nobody campaigns: copycats seal their neighbourhoods; A wins."),
          ("echo_chambers/echo_infi_infi_infi.gif", "Everyone invades: follow links tear A's area open; B takes the lead.")],
         "Town map · ▲ campaigners · ● copycats · ⬢ committed · arrows = follow links bought by campaigners · seed 1 of 3"),
}


def text(slide, x, y, w, h, value, size, color, bold=False, font="Public Sans", italic=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, side, 0)
    run = frame.paragraphs[0].add_run()
    run.text = value
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    run.font.color.rgb = RGBColor.from_string(color)
    return box


def background(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(color)


def main():
    prs = Presentation(str(ORIGINAL))
    blank = prs.slide_layouts[0]
    pdf = pdfium.PdfDocument(str(OUT / "part2_slides.pdf"))
    images = OUT / "pptx_pages"
    images.mkdir(exist_ok=True)
    new_ids = []
    for i in range(len(pdf)):
        png = images / f"part2_{i + 1:02d}.png"
        pdf[i].render(scale=2.5).to_pil().save(png)
        slide = prs.slides.add_slide(blank)
        for shape in list(slide.placeholders):
            shape._element.getparent().remove(shape._element)
        slide.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
        new_ids.append(("part2", i, slide))
        if i in GIF_SLIDES:
            kick, title, gifs, footer = GIF_SLIDES[i]
            g = prs.slides.add_slide(blank)
            for shape in list(g.placeholders):
                shape._element.getparent().remove(shape._element)
            background(g, BG)
            text(g, 0.89, 0.89, 11.9, 0.3, kick.upper(), 13, PURPLE, bold=True)
            text(g, 0.89, 1.30, 11.9, 0.6, title, 28, NAVY, bold=True, font="Libre Baskerville")
            for j, (path, caption) in enumerate(gifs):
                with Image.open(DOCS / path) as im:
                    ratio = im.width / im.height
                height = 4.15
                width = height * ratio
                left = 0.89 + j * 6.0 + (5.6 - width) / 2
                g.shapes.add_picture(str(DOCS / path), Inches(left), Inches(2.0), Inches(width), Inches(height))
                text(g, 0.89 + j * 6.0, 6.22, 5.6, 0.5, caption, 12, INK2)
            text(g, 0.89, 6.86, 11.9, 0.3, footer, 11, GREY)
            new_ids.append(("gif", i, g))

    # reorder: original 1-12, Part 2 pages 1-11 (+ GIF slides), original 13, Part 2 page 12, original 14
    id_list = prs.slides._sldIdLst
    entries = list(id_list)
    original = entries[:14]
    added = entries[14:]
    part2_last = added[-1]          # Part 2 takeaways is the last page added
    order = original[:12] + added[:-1] + [original[12], part2_last, original[13]]
    for e in entries:
        id_list.remove(e)
    for e in order:
        id_list.append(e)
    out = OUT / "Who Wins Depends on Who You Hear-v2.pptx"
    prs.save(out)
    print("slides:", len(order), out, round(out.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
