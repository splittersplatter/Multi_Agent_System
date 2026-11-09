"""Merged deck: Aryan's deck (main format) + Experiment 5 (watchdog) in the main
talk + appendix with Rishi's mathematical slides (re-typeset in Aryan's style)
and the echo-chamber study as an extra experiment. Outputs PDF and PPTX (GIFs play).
"""

from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfReader, PdfWriter

from slides_part2 import CSS, EDGE, OUT, block, figure_left, foot, kicker, right, slide, title
from slides_v3 import GIFS, NOTES, PAGES as V3

DOCS = OUT.parent
ARYAN = Path.home() / "Downloads" / "Who_Wins_Depends_on_Who_You_Hear-Aryan.pptx"
NAME = "Who Wins Depends on Who You Hear-merged"

# Aryan's deck is the template rendered with Liberation Serif / Liberation Sans.
CSS_A = CSS + """
body, .txt, .lab, .kicker, .foot, .cap, .card .h, .card .s, .tile .l, .sub, .small { font-family: 'Liberation Sans', Arial, sans-serif; }
.title, .big, .take, .tile .n { font-family: 'Liberation Serif', 'Times New Roman', serif; }
.mrow { display: grid; grid-template-columns: 2.35in 1fr; gap: .2in; border-top: 1px solid #E2DED3; padding: .1in 0; }
.mrow:last-child { border-bottom: 1px solid #E2DED3; }
.ml { font-weight: 700; font-size: 12pt; color: #5B4BC4; font-family: 'Liberation Sans', Arial, sans-serif; }
.ml small { display: block; font-weight: 400; font-size: 10.5pt; color: #6B7280; margin-top: .03in; }
.mv { font-family: 'Cambria Math', 'Cambria', 'Times New Roman', serif; font-size: 14pt; color: #14213D; line-height: 1.4; }
.pcard { background: #F2EFE6; border-radius: .12in; padding: .2in .24in; }
.pcard h4 { font-family: 'Liberation Sans', Arial, sans-serif; font-size: 14pt; color: #14213D; margin-bottom: .08in; }
.pcard .mv { font-size: 13.5pt; }
.pcard p { font-size: 12pt; color: #3F4756; line-height: 1.4; margin-top: .08in; font-family: 'Liberation Sans', Arial, sans-serif; }
.step { display: flex; gap: .14in; align-items: center; background: #F2EFE6; border-radius: .08in; padding: .1in .16in; margin-bottom: .09in; font-size: 13pt; color: #14213D; }
.step b { color: #5B4BC4; font-size: 14pt; width: .2in; }
table.kp { border-collapse: collapse; margin: .1in 0; font-size: 12.5pt; }
table.kp td, table.kp th { border: 1px solid #D8D4C8; padding: .05in .14in; text-align: right; color: #14213D; }
table.kp th { background: #E9E5DA; }
"""


def m(text):
    """Unicode subscripts -> <sub> so formulas render consistently."""
    table = {"ᵢ": "i", "ⱼ": "j", "ₖ": "k"}
    return re.sub("[ᵢⱼₖ]", lambda x: f"<sub>{table[x.group()]}</sub>", text)


def rows(items):
    out = []
    for label, value in items:
        sub = ""
        if isinstance(label, tuple):
            label, sub = label
            sub = f"<small>{sub}</small>"
        out.append(f'<div class="mrow"><div class="ml">{label}{sub}</div><div class="mv">{m(value)}</div></div>')
    return "".join(out)


def table_slide(kick, head, items, footer="", top=2.0, extra=""):
    return slide(kicker(kick) + title(head) +
                 f'<div class="abs" style="left:.89in; top:{top}in; width:11.75in">{rows(items)}{extra}</div>' +
                 (foot(footer) if footer else ""))


# --------------------------------------------------------------------------- Aryan replacements
QUESTION = slide(
    '<div class="abs kicker" style="top:1.64in">The question</div>'
    '<div class="abs title" style="top:2.18in; width:9.6in; font-size:30pt; line-height:1.3">'
    'Does the winner depend only on what people prefer, or also on how they reason and what they can see?</div>' +
    "".join(f'<div class="abs card" style="left:{0.89 + i * 2.33}in; top:4.06in; width:2.17in; height:1.95in">'
            f'<div class="lab">{k}</div><div class="h" style="font-size:14pt">{h}</div><div class="s">{s}</div></div>'
            for i, (k, h, s) in enumerate((
                ("Experiment 1", "Everyone sees everything", "Full information · 30 towns · 40 rounds"),
                ("Experiment 2", "How voters reason", "84 voter mixes × 30 towns"),
                ("Experiment 3", "Who they can hear", "5 hearing radii, walking or still, × 30 towns"),
                ("Experiment 4", "Who tries to sway them", "A loyal 10% with 0 to 80 followers × 30 towns"),
                ("Experiment 5", "Who catches them", "A watchdog that sees only vote totals · 10 attack styles")))),
    "cream")

TAKEAWAYS = slide(
    '<div class="abs kicker dk-kicker" style="top:1.6in">Takeaways</div>'
    '<div class="abs" style="left:.89in; top:2.05in; width:11.6in">' + "".join(
        f'<div class="take" style="font-size:18pt; margin-bottom:.18in">{a}<span>{b}</span></div>' for a, b in (
            ("1. With shared information the first leader locks in: in all 30 towns after one round, proved for each.", ""),
            ("2. The mix of voters moves the margin, almost never the winner: ", "19 upsets in 2,520 elections."),
            ("3. Changing contacts make the winner unstable, even with fixed beliefs: ",
             "with 32 heard, Left leads in 29 of 30 towns after round 1, 10 by round 150."),
            ("4. A loyal minority with even a small audience can decide the result: ",
             "with 5 followers each, Centre goes from 2 to 23 of 30 towns."),
            ("5. A watchdog must watch the trend, not the jump: ",
             "a 3-round look-back caught 25 of 25 slow takeovers, with no false alarms."))) + "</div>",
    "dark")

# --------------------------------------------------------------------------- appendix
APPENDIX = slide(
    '<div class="abs kicker" style="top:1.64in">Appendix</div>'
    '<div class="abs title" style="top:2.12in; font-size:34pt">Everything behind the results</div>' +
    "".join(f'<div class="abs card" style="left:{x}in; top:3.5in; width:3.75in; height:2.05in">'
            f'<div class="lab">{k}</div><div class="h">{h}</div><div class="s">{s}</div></div>'
            for x, (k, h, s) in zip((0.89, 4.83, 8.77), (
                ("Mathematical model", "The town as equations",
                 "Preferences, hearing, the four decision rules, the parity effect and the full dynamics, in five parts"),
                ("Proofs and theory", "Why it locks in, why it wanders",
                 "The one-step lock-in proof, small-sample odds and stability, and the memory-based voter"),
                ("Extra experiment", "Campaigns vs echo chambers",
                 "Three parties, five campaign playbooks, all 125 combinations")))) +
    foot("Mathematical slides adapted from Rishi's version · extra experiment run on a separate town of 100 people"), "cream")

MATH = [
    ("math0", table_slide("Appendix · Mathematical formulation", "The model in one slide", [
        ("Preferences", "n = 300, C = {Left, Right, Centre}:  c ≻ᵢ c′ ⇔ ‖θᵢ − κ(c)‖ < ‖θᵢ − κ(c′)‖"),
        ("Hearing set", "Hᵢ(t) = { j ≠ i : ‖xᵢ(t) − xⱼ(t)‖ ≤ r }, plus follower links in Experiment 4"),
        ("Observation", "oᵢ(t) = { bⱼ(t − 1) : j ∈ Hᵢ(t) }: last round’s ballots only"),
        ("Policy", "bᵢ(t) = σᵢ(oᵢ(t)),  σᵢ ∈ {sincere, copycat, front-runner, pivot-seeker}"),
        ("Outcome", "s(c, t) = |{ i : bᵢ(t) = c }|,  winner W(t) = arg max<sub>c</sub> s(c, t)"),
        ("Process", "X(t+1) = Φ( X(t), ξ(t) ): a Markov chain whose only randomness is walking")],
        "The next five slides spell out each part")),
    ("math1", table_slide("Appendix · Mathematical model · 1 of 5", "Voters, preferences and the plurality rule", [
        ("Agents, candidates", "N = {1, …, n}, n = 300 · C = {Left, Right, Centre}, m = 3"),
        ("Preferences", "Ideal point θᵢ, platform κ(c) in [0,1]²:  c ≻ᵢ c′ ⇔ ‖θᵢ − κ(c)‖ < ‖θᵢ − κ(c′)‖"),
        ("Utility", "uᵢ(c) = (m − 1 − rankᵢ(c)) / (m − 1) ∈ {1, ½, 0};  rank 0 = favourite"),
        ("Ballot, tally", "bᵢ(t) ∈ C,  s(c, t) = |{ i : bᵢ(t) = c }|,  bᵢ(0) = topᵢ"),
        ("Winner", "W(s) = arg max<sub>c</sub> s(c); ties broken by a fixed party order"),
        ("Town generator", "θ ~ Normal((0.25, 0.45), 0.1²I) for 120 voters, Normal((0.64, 0.50), 0.1²I) for 180; "
                           "xᵢ(0) ~ Uniform[0,1]²; random type · 30 independent towns")])),
    ("math2", table_slide("Appendix · Mathematical model · 2 of 5", "Information: who hears whom", [
        ("Walking", "xᵢ(t+1) = reflect( xᵢ(t) + ℓ·(cos φ, sin φ) ),  φ ~ U[0, 2π),  ℓ ~ U[0, 0.03]; standing still: no step"),
        ("Hearing graph", "j → i in G(t) ⇔ j ≠ i and ‖xᵢ(t) − xⱼ(t)‖ ≤ r;  full information = complete graph"),
        ("Followers (Exp. 4)", "Fixed edges F ⊂ Λ × N: each loyal voter λ ∈ Λ gets f uniformly random followers"),
        ("Hearing set", "Hᵢ(t) = { j : j → i in G(t) } ∪ { λ : (λ, i) ∈ F }"),
        ("Observation", "oᵢ(t) = { (j, bⱼ(t−1)) : j ∈ Hᵢ(t) },  nᵢ(c, t) = |{ j ∈ Hᵢ(t) : bⱼ(t−1) = c }|")],
        "Hearing size ≈ (n − 1)πr²: 9.4 at r = 0.1 (measured ≈ 9) · map edges cut big circles: 150 predicted at r = 0.4, 104 measured")),
    ("math3", table_slide("Appendix · Mathematical model · 3 of 5", "Decision rules: each agent’s policy", [
        (("Sincere", "40% · control"), "bᵢ(t) = topᵢ, the first choice in ≻ᵢ, every round"),
        (("Copycat", "20% · local majority"), "bᵢ(t) = arg max<sub>c</sub> nᵢ(c, t), ties to the earlier candidate in ≻ᵢ;  sincere if Hᵢ(t) = ∅"),
        (("Front-runner", "30% · Top-2, next slide"), "Restrict to the two apparent leaders Tᵢ(t); weigh each by the chance that a tie between them makes your vote decisive"),
        (("Pivot-seeker", "10% · pivotal voter"), "Belief ŝᵢ = round-0 tally, updated with every observed switch.  Outcome wᵢ(c) = W(ŝᵢ − e(bᵢ) + e(c)).  "
                                                  "Switch to c* = arg max uᵢ(wᵢ(c)) only if uᵢ(wᵢ(c*)) > uᵢ(wᵢ(bᵢ))")],
        "Engine policies: sincere, sensed_plurality, top_k (K = 2), pivotal · e(c) = unit vector for candidate c · types assigned independently of opinion")),
    ("math4", slide(kicker("Appendix · Mathematical model · 4 of 5") + title("The front-runner rule and a parity effect") +
        '<div class="abs" style="left:.89in; top:2.0in; width:6.9in">' + rows([
            ("1 · Smoothed local estimate", "p̂ᵢ(c) = (nᵢ(c) + 1) / (|Hᵢ| + m)"),
            ("2 · Apparent leaders", "Tᵢ = {x, y}, the two largest p̂ᵢ;  q = p̂ᵢ(x) / (p̂ᵢ(x) + p̂ᵢ(y))"),
            ("3 · Chance your vote decides", "π(x, y) = P[ Binomial(n − 1, q) = (n − 1)/2 ]"),
            ("4 · Score and choice", "Vᵢ(x) = π(x, y)·(uᵢ(x) − uᵢ(y));  Vᵢ = −∞ outside Tᵢ.  Keep bᵢ if it attains max Vᵢ, else the best by ≻ᵢ")]) +
        '</div><div class="abs pcard" style="left:8.1in; top:2.0in; width:4.55in">'
        '<h4>Why 300 and 301 voters differ</h4>'
        '<div class="mv">n = 300: 299 others, an odd number, so an exact tie is impossible and π = 0.</div>'
        '<p>Inertia decides: stay if already on a leader, else take your preferred leader. A <b>sticky</b> front-runner.</p>'
        '<div class="mv" style="margin-top:.1in">n = 301: π &gt; 0, so you always take your preferred leader.</div></div>')),
    ("math5", slide(kicker("Appendix · Mathematical model · 5 of 5") + title("Dynamics: one round and the process") +
        '<div class="abs" style="left:.89in; top:2.0in; width:4.2in"><div class="lab" style="margin-bottom:.1in">One round, t → t + 1</div>' +
        "".join(f'<div class="step"><b>{i}</b><span>{s}</span></div>' for i, s in enumerate((
            "Move: new positions x(t+1)", "Rebuild G(t+1) and hearing sets", "Observe last round’s ballots b(t)",
            m("All decide at once: bᵢ(t+1) = σᵢ(oᵢ)"), "Tally s(t+1), winner W"), 1)) +
        '</div><div class="abs" style="left:5.5in; top:2.0in; width:7.15in">' + rows([
            ("State", "X(t) = ( x(t), b(t), ŝ(t) ): positions, ballots, pivot beliefs"),
            ("Transition", "X(t+1) = Φ( X(t), ξ(t) ),  ξ = walking noise: a Markov chain; deterministic if standing still"),
            ("Game view", "⟨ N, Aᵢ = C, oᵢ, Φ, uᵢ(W) ⟩ with fixed strategies σᵢ"),
            ("Measured over towns k = 1…30", "wins(c) = Σₖ 1[ W(sₖ(T)) = c ];  switch rate ρ(t) = |{ i : bᵢ(t) ≠ bᵢ(t−1) }| / n")]) +
        "</div>")),
    ("math6", slide(kicker("Appendix · Experiment 1 · why it stops") + title("One-step lock-in under full information") +
        '<div class="abs pcard" style="left:.89in; top:2.0in; width:5.4in"><h4>Proposition</h4>'
        '<div class="mv">Full information, n = 300. If s(1) has the same leader and the same top two as s(0), with gaps of at least 2 '
        'so that no single ballot changes either, then b(2) = b(1), and so b(t) = b(1) for all t ≥ 1.</div>'
        '<p>Checked in all 30 towns: round 1 keeps round 0’s top two (Left–Right in 27, Left–Centre in 3).</p></div>'
        '<div class="abs" style="left:6.7in; top:2.0in; width:5.95in"><div class="lab" style="margin-bottom:.08in">Proof, type by type</div>' + rows([
            ("Sincere", "Ballot never changes."),
            ("Copycat", "Copies the leader; same leader, same vote."),
            ("Front-runner", "With π = 0 it depends only on T; its round-1 vote is already in T, so it stays."),
            ("Pivot-seeker", "Gap ≥ 2: no vote is decisive, so it stays.")]) +
        '<div class="small" style="margin-top:.12in">Same ballots give the same observations, so by induction the profile is a fixed point.</div></div>' +
        foot("Not automatic: with near-ties the same rules can cycle forever, which is why the condition is checked town by town"))),
    ("math7", slide(kicker("Appendix · Experiment 3 · why") + title("Why: small samples, moving samples") +
        '<div class="abs pcard" style="left:.89in; top:2.0in; width:3.75in; height:3.9in"><h4>Local samples</h4>'
        '<p style="margin-top:0">P(Left is the strict leader among k heard), round-0 shares:</p>'
        '<table class="kp"><tr><th>k</th><th>2</th><th>9</th><th>32</th><th>104</th></tr>'
        '<tr><td>P</td><td>16%</td><td>41%</td><td>52%</td><td>63%</td></tr></table>'
        '<p>Most copycats see another leader, so Left’s bandwagon never forms.</p></div>'
        '<div class="abs pcard" style="left:4.84in; top:2.0in; width:3.75in; height:3.9in"><h4>Standing still</h4>'
        '<div class="mv">X(t+1) = Φ(X(t)) on a finite set: 3<sup>n</sup> ballot profiles × bounded beliefs.</div>'
        '<p>So every run is eventually periodic, guaranteed. We observe period 1 or 2, as for majority rules on symmetric graphs (Goles &amp; Olivos 1980).</p></div>'
        '<div class="abs pcard" style="left:8.79in; top:2.0in; width:3.86in; height:3.9in"><h4>Walking</h4>'
        '<div class="mv">Random contacts: no absorbing profile need exist.</div>'
        '<p>On a finite grid the chain is finite, so the share of rounds each candidate leads converges almost surely (ergodic theorem). '
        'The stable object is a frequency, not a winner.</p></div>' +
        foot("Probabilities: multinomial with median round-0 shares 118.5 / 98 / 83 of 300 · finite-grid result: the engine’s stochastic-stability track"))),
    ("math8", slide(kicker("Appendix · Ongoing engine work") + title("A voter with memory and a fading poll") +
        '<div class="abs" style="left:.89in; top:2.0in; width:7.3in">' + rows([
            ("Recent memory, K = 10", "qᵢ(c) = share of c among the latest ballots of everyone met in the last K rounds"),
            ("Poll every L = 10 rounds", "fading weight w(t) = (L − d + 1)/L,  d = 1 + ((t − 1) mod L): 1, 0.9, …, 0.1"),
            ("Blended estimate", "p̂ᵢ(c) = w·P(c)/ΣP + (1 − w)·qᵢ(c)"),
            ("Decision", "F(a) = W((n − 1)p̂ᵢ + e(a)); vote for your favourite reachable winner c* only if c* ≻ᵢ F(bᵢ)")]) +
        '</div><div class="abs col" style="left:8.55in; top:2.0in; width:4.1in">'
        '<div class="pcard"><h4>Convergence</h4><p style="margin-top:0">A 4-voter cycle refutes the original version; no guarantee for n ≥ 100.</p></div>'
        '<div class="pcard"><h4>Finite grid</h4><p style="margin-top:0">On a 41 × 41 lattice, long-run frequencies converge almost surely.</p></div>'
        '<div class="pcard"><h4>Pilot, 200 voters, 5 seeds</h4><p style="margin-top:0">Share error, moving town: poll 0.024, blend 0.085, memory alone 0.167.</p></div></div>')),
]

MATH_NOTES = {
    "math0": "The whole model on one slide: fixed preferences from distances in belief space, a hearing set from the map, "
             "observations of last round's ballots only, a decision rule per voter, plurality counting, and a Markov chain "
             "whose only randomness is walking.",
    "math1": "Voters and the plurality rule. Each voter ranks candidates by distance in belief space; utility is 1, a half or 0 "
             "by rank. Round 0 everyone votes their favourite. Ties go to a fixed party order. Towns are drawn from two camps.",
    "math2": "Who hears whom. Walking is a bounded random step reflected at the edges. You hear everyone within radius r, plus, "
             "in Experiment 4, the loyal voters you follow. Hearing size grows with the circle's area, cut by the map's edges.",
    "math3": "The four decision rules as formulas. Sincere never changes. Copycats take the local majority. Front-runners keep "
             "only the two apparent leaders. Pivot-seekers keep a belief about the full tally and switch only if their vote "
             "changes the winner to someone they prefer.",
    "math4": "How the front-runner chooses, and why 300 voters behave differently from 301: with an even number of voters an "
             "exact tie among the others is impossible, so the rule never sees a decisive vote and just keeps its current choice "
             "if that is one of the two leaders.",
    "math5": "One round in five steps, then the whole process as a Markov chain over positions, ballots and beliefs. We measure "
             "wins across the 30 towns and the share of voters who switch each round.",
    "math6": "Why Experiment 1 freezes. If round 1 keeps the same leader and top two with gaps of at least 2, nobody has a reason "
             "to switch again, type by type, so the ballots are a fixed point. The condition is checked in every town.",
    "math7": "Why Experiment 3 wanders. Small hearing samples often show a different leader. Standing still, the system must "
             "eventually repeat; walking, there may be no resting state, so the right summary is how often each candidate leads.",
    "math8": "Ongoing engine work: a voter who remembers recent contacts and blends that memory with a poll whose weight fades "
             "between polls. Early pilot numbers; no convergence guarantee in general.",
}


def gif_page(key, kick):
    _, head, gifs, footer = GIFS[key]
    tiles, placements = [], []
    for j, (path, caption) in enumerate(gifs):
        with Image.open(DOCS / path) as im:
            im.seek(int(im.n_frames * 0.6))
            png = OUT / f"merge_{key}_{j}.png"
            im.convert("RGB").save(png)
            ratio = im.width / im.height
        height, width = 4.15, 4.15 * ratio
        left = 0.89 + j * 6.0 + (5.6 - width) / 2
        placements.append((DOCS / path, left, 2.0, width, height))
        tiles.append(f'<img class="abs" src="{png.as_uri()}" style="left:{left:.3f}in; top:2.0in; width:{width:.3f}in; height:{height:.3f}in">'
                     f'<div class="abs cap" style="left:{0.89 + j * 6.0}in; top:6.22in; width:5.6in">{caption}</div>')
    return slide(kicker(kick) + title(head) + "".join(tiles) + foot(footer)), placements


def v3(key):
    return dict(V3)[key]


def appendix_version(html):
    return (html.replace("Setup for Experiment 6", "Appendix · Extra experiment · setup")
                .replace(">Experiment 6<", ">Appendix · Extra experiment<"))


EXP5_GIF, EXP5_GIF_POS = gif_page("exp5", "Experiment 5 · watch it happen")
EXTRA_GIF, EXTRA_GIF_POS = gif_page("exp6", "Appendix · Extra experiment · watch it happen")

# (kind, payload, notes, gif placements)
SEQUENCE = [("aryan", 1), ("html", QUESTION), *[("aryan", n) for n in range(3, 13)],
            ("html", v3("exp5_setup")), ("html", v3("exp5_result")), ("html", EXP5_GIF),
            ("html", TAKEAWAYS), ("aryan", 14), ("html", APPENDIX),
            *[("html", html) for _, html in MATH],
            ("html", appendix_version(v3("exp6_setup"))), ("html", appendix_version(v3("exp6_result"))), ("html", EXTRA_GIF)]


def build():
    aryan = Presentation(str(ARYAN))
    aryan_notes = [s.notes_slide.notes_text_frame.text if s.has_notes_slide else "" for s in aryan.slides]
    aryan_png = []
    for s in aryan.slides:
        pic = [x for x in s.shapes if x.shape_type == 13][0]
        aryan_png.append(Image.open(io.BytesIO(pic.image.blob)).convert("RGB"))

    notes = {
        "QUESTION": aryan_notes[1] + " Experiment 5 adds a watchdog: someone who sees only the vote totals and tries to catch "
                                     "a deliberate slow takeover.",
        "TAKEAWAYS": aryan_notes[12] + " Five: a watchdog has to watch the trend, not the jump; looking back three rounds caught "
                                       "every slow takeover we tried, with no false alarms.",
        "APPENDIX": "The appendix has the full mathematical model and proofs, adapted from Rishi's slides, and one extra experiment "
                    "on campaigns and echo chambers.",
    }
    html_pages, html_notes, gif_pos = [], [], {}
    for kind, payload in SEQUENCE:
        if kind != "html":
            continue
        idx = len(html_pages)
        html_pages.append(payload)
        if payload is QUESTION:
            html_notes.append(notes["QUESTION"])
        elif payload is TAKEAWAYS:
            html_notes.append(notes["TAKEAWAYS"])
        elif payload is APPENDIX:
            html_notes.append(notes["APPENDIX"])
        elif payload is EXP5_GIF:
            html_notes.append(NOTES["exp5_gif"]); gif_pos[idx] = EXP5_GIF_POS
        elif payload is EXTRA_GIF:
            html_notes.append(NOTES["exp6_gif"]); gif_pos[idx] = EXTRA_GIF_POS
        else:
            key = next((k for k, h in MATH if h is payload), None)
            if key:
                html_notes.append(MATH_NOTES[key])
            else:
                key = next(k for k, h in V3 if h == payload or appendix_version(h) == payload)
                html_notes.append(NOTES[key])

    page = OUT / "merged_pages.html"
    page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS_A}</style></head><body>{"".join(html_pages)}</body></html>',
                    encoding="utf-8")
    pdf_path = OUT / "merged_pages.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                    f"--print-to-pdf={pdf_path}", page.as_uri()], check=True, capture_output=True, timeout=240)
    html_pdf = PdfReader(str(pdf_path))
    assert len(html_pdf.pages) == len(html_pages), (len(html_pdf.pages), len(html_pages))
    rendered = pdfium.PdfDocument(str(pdf_path))
    html_png = [rendered[i].render(scale=2).to_pil().convert("RGB") for i in range(len(html_pages))]  # 1920x1080

    # ---------------- PDF
    writer = PdfWriter()
    tmp = OUT / "merge_tmp"
    tmp.mkdir(exist_ok=True)
    h = 0
    for kind, payload in SEQUENCE:
        if kind == "aryan":
            f = tmp / f"aryan{payload}.pdf"
            aryan_png[payload - 1].save(f, "PDF", resolution=144.0)
            writer.add_page(PdfReader(str(f)).pages[0])
        else:
            writer.add_page(html_pdf.pages[h])
            h += 1
    out_pdf = OUT / f"{NAME}.pdf"
    with open(out_pdf, "wb") as handle:
        writer.write(handle)

    # ---------------- PPTX (start from Aryan's file to keep his master and notes)
    prs = Presentation(str(ARYAN))
    blank = prs.slide_layouts[0]
    original_ids = list(prs.slides._sldIdLst)
    new_entries, h = [], 0
    for kind, payload in SEQUENCE:
        if kind == "aryan":
            new_entries.append(original_ids[payload - 1])
            continue
        s = prs.slides.add_slide(blank)
        for shape in list(s.placeholders):
            shape._element.getparent().remove(shape._element)
        png = tmp / f"html{h:02d}.png"
        html_png[h].save(png)
        s.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
        for path, left, top, width, height in gif_pos.get(h, []):
            s.shapes.add_picture(str(path), Inches(left), Inches(top), Inches(width), Inches(height))
        s.notes_slide.notes_text_frame.text = html_notes[h]
        new_entries.append(prs.slides._sldIdLst[-1])
        h += 1
    id_list = prs.slides._sldIdLst
    dropped = [e for e in original_ids if e not in new_entries]  # Aryan's old question and takeaways slides
    for e in list(id_list):
        id_list.remove(e)
    for e in new_entries:
        id_list.append(e)
    for e in dropped:  # remove relationship so the replaced slides are not left orphaned in the package
        prs.part.drop_rel(e.rId)
    out_pptx = OUT / f"{NAME}.pptx"
    prs.save(out_pptx)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print("pdf pages:", len(writer.pages), "| pptx slides:", len(new_entries), "|", round(out_pptx.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    build()
