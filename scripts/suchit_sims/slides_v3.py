"""v3 deck: original slides + two experiments (watchdog, echo-chamber campaigns),
three slides each in plain language, as PDF and as PPTX with playable GIFs.

Experiment 5 = watchdog study; Experiment 6 = echo-chamber campaign study
(Experiment 8 in v2).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfReader, PdfWriter

from slides_part2 import CSS, EDGE, ORIGINAL, OUT, block, figure_left, foot, kicker, right, slide, title
from slides_pptx import BG, GREY, INK2, NAVY, PURPLE, background, text

DOCS = OUT.parent
PPTX_ORIGINAL = Path.home() / "Downloads" / "Who Wins Depends on Who You Hear.pptx"

GIFS = {
    "exp5": ("Experiment 5 · watch it happen", "A blitz is loud, a slow drip is quiet",
             [("watchdog/W1_issue_space.gif", "Blitz: Cyd jumps 14 points in round 1. Every alarm fires at once."),
              ("watchdog/W5_issue_space.gif", "Slow drip: Cyd creeps up a few points a round and still takes the lead.")],
             "Belief space · ▲ pushed voters · ★ candidates · colour = current vote · 'ALERT' appears when the 3-round alarm fires"),
    "exp6": ("Experiment 6 · watch it happen", "Nobody campaigns vs everyone invades",
             [("echo_chambers/echo_pass_pass_pass.gif", "Nobody campaigns: neighbourhoods seal themselves and A wins."),
              ("echo_chambers/echo_infi_infi_infi.gif", "Everyone invades: follow links tear A's area open and B takes the lead.")],
             "Town map · ▲ campaigners · ● copycats · ⬢ committed · arrows = follow links bought by campaigners"),
}

NOTES = {
    "divider": "Part 2 asks a different question. Part 1 changed how people reason and whom they hear. Here someone "
               "deliberately tries to steer the result. We look at two cases: an attacker the public can only spot "
               "through vote totals, and parties that campaign by changing who hears whom.",
    "question": "Two experiments. In each, every run has a twin town that is identical except that nobody manipulates, "
                "so any difference is caused by the manipulation.",
    "exp5_setup": "100 people, three candidates. Cyd starts third with 23 votes. An attacker has a budget to nudge chosen "
                  "voters' beliefs toward Cyd, a little each round. The watchdog never sees beliefs or the attacker, only "
                  "the vote totals each round, like an election monitor. It wins if it raises the alarm before Cyd wins "
                  "three rounds in a row. The built-in alarm fires when the target jumps more than 5 points in one round.",
    "exp5_result": "Fast attacks are loud: Cyd jumps 10 to 14 points in one round and the built-in alarm catches them. "
                   "Slow attacks add only 4 or 5 points a round, never enough to trip a one-round alarm, yet they still win "
                   "by round 9 or 10. The built-in alarm caught 20 of 25 winning attacks on new test towns. We tried 101 "
                   "rules that use only the totals. The best: alarm if the target rose more than 4 points over the last 3 "
                   "rounds. It caught 25 of 25 with zero false alarms in 40 untouched towns. We then let the attacker try "
                   "36 plans; none won without being caught first. Lowering the one-round bar to 3 points also works.",
    "exp5_gif": "Left: a blitz. Many triangles move toward Cyd at once and the colours flip in round 1. Right: the slow "
                "drip, in a noisier town. Nothing dramatic happens in any one round, but by round 10 Cyd is ahead. That is "
                "exactly why the watchdog has to look at a trend, not a single jump.",
    "exp6_setup": "Three neighbourhoods, one per party. Most residents copy the most common vote among the 4 or 5 neighbours "
                  "they can see, so each area becomes an echo chamber. Each party has 4 campaigners who move faster, can poll "
                  "a wide area, and can make up to 6 voters follow them, which puts the campaigner's vote in front of those "
                  "voters. Each party picks one of five playbooks. We ran all 125 combinations, 3 towns each.",
    "exp6_result": "Party A, the biggest, should invade: it is the best reply in 19 of 25 match-ups and gains 3.3 points on "
                   "average. Party B should defend its home; doing nothing costs it 1.7 points. Party C, the smallest, can "
                   "barely move: at best 0.3 points, and it never won any of the 375 elections. There is no combination where "
                   "everyone is happy: best replies go round in a loop. The closest to stable is everyone invading. That breaks "
                   "the echo chambers, from 79% to 55% voting with their own area, but the winner barely changes.",
    "exp6_gif": "Left: nobody campaigns. Each area turns almost entirely one colour. Right: everyone invades. Campaigners "
                "walk into rival areas and the arrows are their follow links. A's area is invaded from both sides and "
                "splinters, and B takes the lead in this town. Across 3 towns, B won 1.",
    "takeaways": "Two lessons: watch the trend, not the jump; and campaign wars change who hears whom without changing who wins.",
}


def gif_page_html(key):
    kick, head, gifs, footer = GIFS[key]
    tiles = []
    for j, (path, caption) in enumerate(gifs):
        with Image.open(DOCS / path) as im:
            im.seek(int(im.n_frames * 0.6))  # a representative mid-run frame for the static PDF
            png = OUT / f"v3_{key}_{j}.png"
            im.convert("RGB").save(png)
            ratio = im.width / im.height
        height = 4.15
        width = height * ratio
        left = 0.89 + j * 6.0 + (5.6 - width) / 2
        tiles.append(f'<img class="abs" src="{png.as_uri()}" style="left:{left:.2f}in; top:2.0in; width:{width:.2f}in">'
                     f'<div class="abs cap" style="left:{0.89 + j * 6.0}in; top:6.22in; width:5.6in">{caption}</div>')
    return slide(kicker(kick) + title(head) + "".join(tiles) + foot(footer + " · in the PowerPoint these play as animations"))


PAGES = [
    ("divider", slide(
        '<div class="abs kicker dk-kicker" style="top:2.26in">Multi-agent election lab · Part 2</div>'
        '<div class="abs big" style="left:.89in; top:2.74in; width:11.6in">Who steers the winner on purpose</div>'
        '<div class="abs sub" style="left:.89in; top:4.56in; width:10in">Two deliberate manipulations, each run against an '
        'untouched twin town: who wins, how, and can anyone catch them?</div>'
        '<div class="abs foot" style="color:#BFC6D6">Team Eclipse · Experiments 5 and 6 · towns of 100 people, same engine</div>', "dark")),
    ("question", slide(
        '<div class="abs kicker" style="top:1.64in">The question</div>'
        '<div class="abs title" style="top:2.18in; width:11in; font-size:30pt; line-height:1.3">'
        'If someone steers the result on purpose, does it work, and can anyone catch them?</div>' +
        "".join(f'<div class="abs card" style="left:{x}in; top:4.06in; width:5.75in; height:1.8in">'
                f'<div class="lab">{k}</div><div class="h">{h}</div><div class="s">{s}</div></div>'
                for x, (k, h, s) in zip((0.89, 6.95), (
                    ("Experiment 5", "A watchdog that only sees the vote totals",
                     "An attacker slowly changes voters' minds. 10 attack styles, 420 runs."),
                    ("Experiment 6", "Campaigns vs echo chambers",
                     "Three parties pick a campaign playbook. All 125 combinations × 3 towns.")))) +
        foot("Every manipulated town is compared with a twin that is identical except that nobody manipulates"), "cream")),
    ("exp5_setup", slide(
        kicker("Setup for Experiment 5") + title("Can a watchdog catch a slow takeover?") +
        figure_left("fig5a_watchdog_setup.png",
                    "<b>One attack, start and end.</b> Triangles are the voters being pushed. Over 30 rounds they drift toward "
                    "Cyd, and Cyd goes from third (23 votes) to first (46).", width=5.85) +
        right([block("The town", "100 people, three candidates: <b>Ana 42, Ben 35, Cyd 23</b>. Everyone votes for the "
                     "candidate closest to their views."),
               block("The attacker", "Has a budget to nudge chosen voters' views toward Cyd, a little every round. "
                     "We tried 10 styles: fast or slow, few or many voters."),
               block("The watchdog", "Sees <b>only the vote totals</b>, like an election monitor. It wins if it sounds "
                     "the alarm <b>before Cyd wins three rounds in a row</b>.", "got"),
               block("The built-in alarm", "Fires if the target jumps more than 5 points in a single round.")]) +
        foot("Views also drift a little on their own every round · 30 rounds · every attack has an untouched twin town"))),
    ("exp5_result", slide(
        kicker("Experiment 5") + title("Watch the trend, not the jump") +
        figure_left("fig5b_watchdog_timelines.png",
                    "<b>Purple:</b> Cyd's vote share. <b>Yellow:</b> how much it rose that round. The blitz jumps at once; "
                    "the slow drip never rises more than 5 in a round, yet wins by round 9.", width=5.85) +
        right([block("What we got", "The one-round alarm caught <b>20 of 25</b> winning attacks: it misses slow, patient ones. "
                     "Our best rule, <b>“alarm if the target rose more than 4 points over 3 rounds”</b>, caught "
                     "<b>25 of 25</b>, with <b>no false alarms</b> in 40 untouched towns.", "got"),
               block("Can the attacker dodge it?", "We let the attacker try 36 plans. Against the one-round alarm, a slow "
                     "drip wins every time unseen. Against the 3-round rule, <b>none</b> got through."),
               block("Our real-world reading", "Monitors that only look for sudden swings miss patient manipulation. "
                     "Looking a few rounds back is enough to catch it.", "read")]) +
        foot("Best rule picked from 101 candidates on one set of towns, then tested on new ones · a 3-point one-round bar also works"))),
    ("exp5_gif", gif_page_html("exp5")),
    ("exp6_setup", slide(
        kicker("Setup for Experiment 6") + title("Campaigners who change who you hear") +
        figure_left("fig8a_echo_setup.png",
                    "<b>Everyone invades.</b> Campaigners walk into rival neighbourhoods and get voters to follow them. "
                    "By round 40 only 50% still vote with their neighbourhood.", width=5.95) +
        right([block("The town", "Three neighbourhoods, one per party: <b>A 34, B 30, C 24</b>. Most residents are copycats: "
                     "they vote like the 4 or 5 neighbours they see, so each area becomes an <b>echo chamber</b>."),
               block("The campaigners", "4 per party. They move fast, can poll a wide area, and can get up to 6 voters to "
                     "<b>follow</b> them, so those voters see the campaigner's vote.", "got"),
               block("The playbooks", "<b>Do nothing</b> · <b>defend</b> your home area · <b>invade</b> the biggest rival "
                     "area · <b>work the border</b> · <b>random</b> followers. Every party picks one.")], left=7.05, width=5.6) +
        foot("All 125 combinations of playbooks × 3 towns × 40 rounds · score: a party's vote share over the last 10 rounds"))),
    ("exp6_result", slide(
        kicker("Experiment 6") + title("Attack if you lead, defend if you chase") +
        figure_left("fig8b_echo_gains.png",
                    "<b>Each bar:</b> how much a playbook earns a party on average, against every combination of its rivals' "
                    "playbooks. “Fortify” is defend; “infiltrate” is invade.", width=5.85) +
        right([block("What we got", "<b>A</b> (biggest) should <b>invade</b>: +3.3 points. <b>B</b> should <b>defend</b>; "
                     "doing nothing costs it 1.7. <b>C</b> (smallest) can't move the needle and won <b>0 of 375</b> "
                     "elections.", "got"),
               block("Does anyone settle?", "No. Each party keeps switching to beat the others, in a loop. The closest to "
                     "stable is <b>everyone invading</b>."),
               block("Our real-world reading", "Campaign wars break echo chambers (79% → 55% vote with their area) "
                     "but barely change who wins.", "read")]) +
        foot("Across all 375 elections: A wins 348, B 27, C 0 · B's only upset route is working the border while A stays home"))),
    ("exp6_gif", gif_page_html("exp6")),
    ("takeaways", slide(
        '<div class="abs kicker dk-kicker" style="top:1.85in">Takeaways · Part 2</div>'
        '<div class="abs" style="left:.89in; top:2.32in; width:11.6in">'
        '<div class="take">5. Watch the trend, not the jump:<span> a 3-round look-back caught 25 of 25 slow takeovers, '
        'with no false alarms.</span></div>'
        '<div class="take">6. Campaign wars change who you hear, not who wins:<span> the leader invades, the challenger '
        'defends, nobody settles, and the underdog won 0 of 375.</span></div></div>', "dark")),
]


def build_pdf():
    html = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(p for _, p in PAGES)}</body></html>'
    page = OUT / "v3_part2.html"
    page.write_text(html, encoding="utf-8")
    pdf = OUT / "v3_part2.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                    f"--print-to-pdf={pdf}", page.as_uri()], check=True, capture_output=True, timeout=180)
    part = PdfReader(str(pdf))
    assert len(part.pages) == len(PAGES), (len(part.pages), len(PAGES))
    original = PdfReader(str(ORIGINAL))
    writer = PdfWriter()
    for i in range(12):
        writer.add_page(original.pages[i])
    for i in range(len(PAGES) - 1):
        writer.add_page(part.pages[i])
    writer.add_page(original.pages[12])
    writer.add_page(part.pages[len(PAGES) - 1])
    writer.add_page(original.pages[13])
    out = OUT / "Who Wins Depends on Who You Hear-v3.pdf"
    with open(out, "wb") as handle:
        writer.write(handle)
    print("pdf pages:", len(writer.pages), out)
    return pdf


def build_pptx(part_pdf):
    prs = Presentation(str(PPTX_ORIGINAL))
    blank = prs.slide_layouts[0]
    pdf = pdfium.PdfDocument(str(part_pdf))
    tmp = OUT / "v3_pages"
    tmp.mkdir(exist_ok=True)

    def new_slide():
        s = prs.slides.add_slide(blank)
        for shape in list(s.placeholders):
            shape._element.getparent().remove(shape._element)
        return s

    for i, (key, _) in enumerate(PAGES):
        s = new_slide()
        if key in ("exp5_gif", "exp6_gif"):
            kick, head, gifs, footer = GIFS[key[:4]]
            background(s, BG)
            text(s, 0.89, 0.89, 11.9, 0.3, kick.upper(), 13, PURPLE, bold=True)
            text(s, 0.89, 1.30, 11.9, 0.6, head, 28, NAVY, bold=True, font="Libre Baskerville")
            for j, (path, caption) in enumerate(gifs):
                with Image.open(DOCS / path) as im:
                    ratio = im.width / im.height
                height = 4.15
                width = height * ratio
                left = 0.89 + j * 6.0 + (5.6 - width) / 2
                s.shapes.add_picture(str(DOCS / path), Inches(left), Inches(2.0), Inches(width), Inches(height))
                text(s, 0.89 + j * 6.0, 6.22, 5.6, 0.5, caption, 12, INK2)
            text(s, 0.89, 6.86, 11.9, 0.3, footer, 11, GREY)
        else:
            png = tmp / f"{i:02d}.png"
            pdf[i].render(scale=2.5).to_pil().save(png)
            s.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
        s.notes_slide.notes_text_frame.text = NOTES[key]

    ids = prs.slides._sldIdLst
    entries = list(ids)
    original, added = entries[:14], entries[14:]
    order = original[:12] + added[:-1] + [original[12], added[-1], original[13]]
    for e in entries:
        ids.remove(e)
    for e in order:
        ids.append(e)
    out = OUT / "Who Wins Depends on Who You Hear-v3.pptx"
    prs.save(out)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print("pptx slides:", len(order), out, round(out.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    build_pptx(build_pdf())
