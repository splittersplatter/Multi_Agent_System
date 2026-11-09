"""Part 2 slides (Experiments 5-8) in the format of 'Who wins depends on who you hear'.

Geometry, fonts and colours are copied from the original .pptx (13.333 x 7.5 in,
Libre Baskerville headings, Public Sans text). Builds HTML, prints it to PDF with
headless Edge, then merges with the original deck:

    original 1-12 · Part 2 (11 slides) · original takeaways · Part 2 takeaways · original extensions
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "suchit_sims" / "slides"
ORIGINAL = Path.home() / "Downloads" / "Who Wins Depends on Who You Hear-v1.pdf"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=block');
@page { size: 13.333in 7.5in; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Public Sans', sans-serif; }
.slide { width: 13.333in; height: 7.5in; position: relative; overflow: hidden; break-after: page; background: #FBFAF6; }
.slide:last-child { break-after: auto; }
.cream { background: #F2EFE6; }
.dark { background: #14213D; }
.abs { position: absolute; }
.kicker { left: .89in; top: .89in; font-weight: 700; font-size: 13pt; letter-spacing: 1.5pt; color: #5B4BC4; text-transform: uppercase; }
.title { left: .89in; top: 1.30in; width: 11.9in; font-family: 'Libre Baskerville', serif; font-weight: 700; font-size: 28pt; color: #14213D; line-height: 1.2; }
.foot { left: .89in; top: 6.82in; width: 11.9in; font-size: 12pt; color: #6B7280; }
.col { display: flex; flex-direction: column; gap: .11in; }
.lab { font-weight: 700; font-size: 12pt; letter-spacing: 1pt; color: #5B4BC4; text-transform: uppercase; margin-bottom: .03in; }
.txt { font-size: 13pt; color: #3F4756; line-height: 1.38; }
.txt b { color: #14213D; }
.got { background: #F2EFE6; border-radius: .1in; padding: .13in .17in .15in; }
.got .txt { color: #14213D; }
.read { border-left: 2.5pt solid #5B4BC4; padding-left: .15in; }
.cap { font-size: 12pt; color: #3F4756; line-height: 1.38; }
.cap b { color: #14213D; }
.fig img { width: 100%; display: block; }
.card { background: #FBFAF6; border-radius: .12in; padding: .22in .22in; }
.card .lab { font-size: 12pt; }
.card .h { font-size: 15pt; color: #14213D; margin: .06in 0 .05in; line-height: 1.3; }
.card .s { font-size: 12pt; color: #6B7280; line-height: 1.35; }
.tile { background: #F2EFE6; border-radius: .12in; padding: .17in .22in; }
.tile .n { font-family: 'Libre Baskerville', serif; font-weight: 700; font-size: 30pt; line-height: 1.1; }
.tile .l { font-size: 12.5pt; color: #3F4756; margin-top: .04in; line-height: 1.3; }
.dk-kicker { color: #B9B0F2; }
.big { font-family: 'Libre Baskerville', serif; font-weight: 700; font-size: 48pt; color: #F4F1EA; line-height: 1.12; }
.sub { font-size: 18pt; color: #BFC6D6; line-height: 1.35; }
.take { font-family: 'Libre Baskerville', serif; font-size: 19pt; color: #F4F1EA; line-height: 1.42; margin-bottom: .22in; }
.take span { color: #B9B0F2; }
.small { font-size: 12pt; color: #3F4756; line-height: 1.4; }
"""


def fig(name):
    return (OUT / name).as_uri()


def slide(body, cls=""):
    return f'<section class="slide {cls}">{body}</section>'


def kicker(text, dark=False):
    return f'<div class="abs kicker{" dk-kicker" if dark else ""}">{text}</div>'


def title(text):
    return f'<div class="abs title">{text}</div>'


def foot(text):
    return f'<div class="abs foot">{text}</div>'


def block(label, text, kind=""):
    inner = f'<div class="lab">{label}</div><div class="txt">{text}</div>'
    if kind == "got":
        return f'<div class="got">{inner}</div>'
    if kind == "read":
        return f'<div class="read">{inner}</div>'
    return f'<div>{inner}</div>'


def figure_left(img, caption, width=5.75, top=1.98):
    return (f'<div class="abs fig" style="left:.89in; top:{top}in; width:{width}in">'
            f'<img src="{fig(img)}"><div class="cap" style="margin-top:.12in">{caption}</div></div>')


def right(blocks, left=6.95, width=5.65, top=1.98):
    return f'<div class="abs col" style="left:{left}in; top:{top}in; width:{width}in">{"".join(blocks)}</div>'


SLIDES = []

# 1 · divider ---------------------------------------------------------------
SLIDES.append(slide(
    '<div class="abs kicker dk-kicker" style="top:2.26in">Multi-agent election lab · Part 2</div>'
    '<div class="abs big" style="left:.89in; top:2.74in; width:11.6in">Who steers the winner on purpose</div>'
    '<div class="abs sub" style="left:.89in; top:4.56in; width:10in">Four deliberate manipulations, each run against an untouched twin. '
    'Who wins, how, and who can catch them.</div>'
    '<div class="abs foot" style="color:#BFC6D6">Team Eclipse · Experiments 5 to 8 · towns of 100 people, same engine</div>', "dark"))

# 2 · the question ----------------------------------------------------------------
cards = [("Experiment 5", "A watchdog that sees only totals", "10 attack styles · 420 runs"),
         ("Experiment 6", "Foreign spies", "15 sleeper cells · 4 tactics × 8 towns"),
         ("Experiment 7", "Changing minds slowly", "4 campaigns, same budget × 5 towns"),
         ("Experiment 8", "Campaigns vs echo chambers", "3 parties × 5 playbooks: 125 match-ups × 3 towns")]
card_html = "".join(
    f'<div class="abs card" style="left:{x}in; top:4.06in; width:2.74in; height:1.95in">'
    f'<div class="lab">{k}</div><div class="h">{h}</div><div class="s">{s}</div></div>'
    for x, (k, h, s) in zip((0.89, 3.83, 6.76, 9.70), cards))
SLIDES.append(slide(
    '<div class="abs kicker" style="top:1.64in">The question</div>'
    '<div class="abs title" style="top:2.18in; width:11in; font-size:30pt; line-height:1.3">'
    'If someone tries to steer the result on purpose, does it work, and can anyone catch them?</div>' + card_html +
    foot("Every attack run is paired with a twin town that is identical except that the attacker stays quiet"), "cream"))

# 3 · setup exp 5 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Setup for Experiment 5") + title("A watchdog that sees only the scoreboard") +
    figure_left("fig5a_watchdog_setup.png",
                "<b>Attack W4, slow drip.</b> Every round the attacker nudges the beliefs of the 25 voters closest to switching "
                "a little toward Cyd. By round 30 Cyd has gone from third (23) to first (46).", width=5.85) +
    right([block("The town", "100 people with beliefs on two issues. Three candidates: <b>Ana 42, Ben 35, Cyd 23</b>. "
                 "Everyone votes for the nearest candidate; beliefs also drift a little by themselves."),
           block("The attacker", "A fixed budget to push chosen voters' beliefs toward Cyd. Ten styles: fast or slow, "
                 "few or many voters, aimed or random."),
           block("The watchdog", "Sees only each round's vote totals. It <b>wins</b> if it raises the alarm before "
                 "Cyd wins three rounds in a row.", "got"),
           block("Built-in alarm", "Fires when the target jumps more than 5 points in one round.")]) +
    foot("Belief drift up to 0.01 per round · 30 rounds · every attack paired with an untouched twin town")))

# 4 · results exp 5 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Experiment 5") + title("Slow attacks slip under a one-round alarm") +
    figure_left("fig5b_watchdog_timelines.png",
                "<b>Purple:</b> Cyd's share. <b>Yellow bars:</b> its rise each round. A blitz jumps 14 points at once; "
                "the slow drip never rises more than 5 in a round, yet wins by round 9.", width=5.85) +
    right([block("What we changed", "Ten ways to spend the attack budget, one town each, each with an untouched twin."),
           block("What we got", "The built-in alarm catches all 3 fast attacks, but <b>misses both slow drips</b>, which still "
                 "win by round 9 and 10. Five attacks never win: wrong targets, random pushes, too little money, "
                 "too few or too many voters.", "got"),
           block("Why", "A drip adds 4 to 5 points a round: always under the one-round bar, but it keeps adding up."),
           block("Our real-world reading", "Watching for sudden jumps misses patient campaigns.", "read")]) +
    foot("No alarm fired in any of the 10 twin towns · the attack only wins on the 25 voters closest to switching")))

# 5 · strategy exp 5 ---------------------------------------------------------------
tiles = [("#EB6834", "20 of 25", "attacks caught by the built-in alarm"),
         ("#1BAF7A", "25 of 25", "caught by the 3-round alarm"),
         ("#5B4BC4", "0 of 40", "false alarms in untouched towns"),
         ("#14213D", "0 of 36", "attack plans that win unseen")]
tile_html = "".join(f'<div class="abs tile" style="left:{x}in; top:1.98in; width:2.78in; height:1.19in">'
                    f'<div class="n" style="color:{c}">{n}</div><div class="l">{l}</div></div>'
                    for x, (c, n, l) in zip((0.89, 3.85, 6.81, 9.77), tiles))
SLIDES.append(slide(
    kicker("Experiment 5 · best strategies") + title("Look back three rounds, not one") + tile_html +
    f'<div class="abs fig" style="left:.89in; top:3.45in; width:7.15in"><img src="{fig("fig5c_attacker_grid.png")}"></div>' +
    right([block("The watchdog's best rule", "We tried 101 rules that use only vote totals and kept the fastest one that "
                 "never fired in 80 untouched towns, even with 50% more natural drift: <b>alarm if the target rose more "
                 "than 4 points over the last 3 rounds</b>."),
           block("The attacker's best reply", "Against the one-round alarm: a slow drip on the 25 swing voters wins "
                 "<b>every time, unseen</b>, around round 17. Against the 3-round rule nothing slips through; the best "
                 "left is a blitz that is flagged in round 1.", "got")], left=8.3, width=4.35, top=3.4) +
    foot("Rule chosen on towns 201–205, tested on new towns 101–105 · lowering the one-round bar to 3 points also catches 25 of 25")))

# 6 · setup exp 6 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Setup for Experiment 6") + title("Sleeper cells in the group chats") +
    f'<div class="abs fig" style="left:.89in; top:1.86in; width:4.0in"><img src="{fig("fig6a_spies_map.png")}"></div>' +
    right([block("The town", "85 residents: <b>A 40%, B 37%, C 23%</b>, chatting with neighbours and in 10 group chats. "
                 "Three kinds of resident:"),
           '<div class="txt" style="margin:-.04in 0 0 .1in">◆ <b>Committed</b> 40%: always vote their favourite.<br>'
           '● <b>Trusting</b> 40%: vote what most contacts say they vote.<br>'
           '■ <b>Checkers</b> 20%: vote what most neighbours actually vote.</div>',
           block("The spies · 15%", "15 sleepers (▲) vote like locals to blend in and send fake “I'm voting B” messages: "
                 "4 a round, 100 each, to their 15 followers and one group chat.", "got"),
           block("Their intelligence", "None (lie at random), a <b>dossier</b> of their followers' true favourites, or "
                 "the dossier plus <b>listening</b> to two nearby group chats.")], left=5.75, width=6.9) +
    foot("Each spy is its own cell with its own budget · 25 rounds · every run paired with a twin whose spies stay silent")))

# 7 · results exp 6 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Experiment 6") + title("Knowing whom to lie to is the weapon") +
    figure_left("fig6b_spies_results.png",
                "<b>8 towns per tactic.</b> Grey: the twin town where the spies stay silent. Purple: the same town with the spies lying. "
                "Every tactic sends the same 1,500 lies.", width=5.85) +
    right([block("What we changed", "Only what the spies know: nothing, a dossier, dossier plus chat listening; then half the network."),
           block("What we got", "B wins 2 of 8 towns with silent spies, <b>3 with blind lies, 5 with a dossier</b>. "
                 "Listening to chats adds nothing. With 8 spies B never leads.", "got"),
           block("Why", "Trusting voters break ties with their own favourite, so hidden B fans who now follow A tip with one or "
                 "two lies. Blind lies land on committed voters and checkers, who never move."),
           block("Our real-world reading", "Targeting data, not volume, is what makes disinformation work; voters who check "
                 "what people do, not what they say, are nearly immune.", "read")]) +
    foot("B's share gain over the silent twin: blind +2.0, dossier +4.8 points · the 8-spy town also starts weaker for B (23% vs 36% in its twin)")))

# 8 · exp 7 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Experiment 7") + title("Changing minds slowly") +
    figure_left("fig7_persuasion.png",
                "<b>Same town as Experiment 5, 60 rounds.</b> Each campaign gets the same budget for pushing beliefs toward Cyd "
                "and spends it in a different way. Mean of 5 towns.", width=5.85) +
    right([block("What we changed", "Where the budget goes: a little on 60 voters, a lot on the 20 swing voters, on 20 of "
                 "the opposition's core, or in random directions."),
           block("What we got", "<b>Swing voters</b>: Cyd leads by round 5 and wins 56 of 61 rounds. <b>Broad and shallow</b>: "
                 "slower, but 63% of the vote. The core works slowly; random pushes do nothing. The gains stay after "
                 "the money stops.", "got"),
           block("Why", "Beliefs drift at random with no pull back, so moved voters stay moved."),
           block("Our real-world reading", "The winner ends up 24% further from what people first believed, yet looks closer "
                 "to what they believe now: successful persuasion hides itself.", "read")]) +
    foot("Average distance from the winner to voters' original beliefs: 0.436 with any successful campaign vs 0.352 without one")))

# 9 · setup exp 8 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Setup for Experiment 8") + title("Campaigners who reshape who you hear") +
    figure_left("fig8a_echo_setup.png",
                "<b>All three parties invade.</b> Campaigners walk into rival neighbourhoods and make voters follow them. "
                "By round 40 only 50% still vote with their neighbourhood, and B has taken the lead.", width=5.95) +
    right([block("The town", "88 residents in three neighbourhoods: <b>A 34, B 30, C 24</b>, 65% loyal to the local party. "
                 "Copycats (60%) hear only 4 or 5 neighbours; the rest are committed."),
           block("The campaigners", "4 per party. They walk 6× faster, poll everyone within 0.3, and can make up to 6 voters "
                 "follow them, 2 new a round.", "got"),
           block("Five playbooks", "<b>Do nothing</b> · <b>fortify</b>: stay home, win back defectors · <b>infiltrate</b>: move "
                 "into the biggest rival area · <b>bridge</b>: sit on the border, chase swing voters · <b>broadcast</b>: "
                 "random followers.")], left=7.05, width=5.6) +
    foot("Every combination of playbooks, 125 in all, × 3 towns × 40 rounds · a party's score: its share over the last 10 rounds")))

# 10 · results exp 8 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Experiment 8") + title("The leader attacks, the challenger defends") +
    figure_left("fig8b_echo_gains.png",
                "<b>Each bar:</b> a party's average gain from one playbook, over all 25 combinations of its rivals' playbooks.", width=5.85) +
    right([block("What we changed", "Every party's playbook, in every combination."),
           block("What we got", "<b>A</b> should infiltrate: best in 19 of 25 match-ups, +3.3 points. <b>B</b> should "
                 "fortify; doing nothing costs it 1.7. <b>C</b> barely moves: +0.3 at best, and wins <b>0 of 375</b> elections.", "got"),
           block("Why", "Invading the biggest rival splits its copycats. The smallest party has no area big enough to tip."),
           block("Our real-world reading", "B's one route to an upset is to work the border while A stays home: then it wins 2 of 3 towns.", "read")]) +
    foot("Across all 375 runs: A wins 348, B 27, C 0 · averages over 3 towns per match-up")))

# 11 · game exp 8 ---------------------------------------------------------------
SLIDES.append(slide(
    kicker("Experiment 8 · best strategies") + title("No resting point, only an arms race") +
    figure_left("fig8c_echo_game.png",
                "<b>Left:</b> every party plays the same playbook. <b>Right:</b> each party in turn switches to its best reply; "
                "the switching never stops.", width=6.35) +
    right([block("What we expected", "One set of playbooks where no party wants to switch."),
           block("What we got", "<b>There is none.</b> The best replies loop forever: A swaps invading for bridging, B swaps "
                 "fortifying for invading. Closest to rest: <b>everyone invades</b>; no party gains even a quarter of a vote by switching.", "got"),
           block("Our real-world reading", "When every side campaigns in its rivals' areas, echo chambers break (79% → 55% vote "
                 "with their neighbourhood; 62% → 76% see the other side), but the winner barely changes.", "read")],
          left=7.45, width=5.2) +
    foot("Most stable mixes: A bridges, B and C invade (best switch gains 0.20 points) and everyone invades (0.23)")))

# 12 · takeaways ---------------------------------------------------------------
takes = [("5. A one-round alarm misses patient attackers:", " a 3-round look-back caught 25 of 25, with no false alarms."),
         ("6. Targeting beats volume:", " the same lies take B from 2 to 5 of 8 towns once spies know whom to lie to."),
         ("7. Slow persuasion sticks and hides itself:", " the winner ends up 24% further from what people first believed."),
         ("8. Campaign wars break echo chambers but not the winner:", " no stable playbook, and the underdog won 0 of 375.")]
SLIDES.append(slide(
    '<div class="abs kicker dk-kicker" style="top:1.85in">Takeaways · Part 2</div>'
    '<div class="abs" style="left:.89in; top:2.32in; width:11.6in">' +
    "".join(f'<div class="take">{a}<span>{b}</span></div>' for a, b in takes) + "</div>", "dark"))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    html = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(SLIDES)}</body></html>'
    page = OUT / "part2_slides.html"
    page.write_text(html, encoding="utf-8")
    pdf = OUT / "part2_slides.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                    f"--print-to-pdf={pdf}", page.as_uri()], check=True, capture_output=True, timeout=180)
    part2 = PdfReader(str(pdf))
    print("part 2 pages:", len(part2.pages))
    original = PdfReader(str(ORIGINAL))
    writer = PdfWriter()
    for i in range(12):                      # title ... experiment 4
        writer.add_page(original.pages[i])
    for i in range(11):                      # part 2 slides
        writer.add_page(part2.pages[i])
    writer.add_page(original.pages[12])      # takeaways 1-4
    writer.add_page(part2.pages[11])         # takeaways 5-8
    writer.add_page(original.pages[13])      # possible extensions
    combined = OUT / "Who Wins Depends on Who You Hear-v2.pdf"
    with open(combined, "wb") as handle:
        writer.write(handle)
    print("combined pages:", len(writer.pages), combined)


if __name__ == "__main__":
    build()
