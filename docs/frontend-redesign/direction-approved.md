# Approved direction: 3 · Explorable

Chosen on 2026-11-10 from the three full drafts in [design-demos/](design-demos/) (Observatory, Atlas, Explorable). The alternates were a sound-wave view and a dense annotated magazine page.

## What the direction is

Based on Nicky Case's explorable explanations: a white page, soft rounded cards, one plain question per section, large type and large hit targets. The page talks to the reader in sentences ("r12 copies the most common vote they hear. They hear 9 people…") instead of tables of fields.

| Token | Value |
|---|---|
| Background / card / ink | `#ffffff` / `#f1f4f9` / `#20232c` |
| Muted text | `#565b6b` (≥ 4.5:1 on white and on the card) |
| Parties | `#2f7df6`, `#ff7433`, `#21ad6b`, `#a35be8`, `#d99a00`, `#e8336d`, `#13a0b2`, `#7d6a52`, then evenly spaced hues |
| Edge types | nearby `#9aa3b5`, follow `#8a4fe6`, paid `#e8336d`; new links glow amber, broken links are dotted |
| Display / text type | Bricolage Grotesque 800 / Atkinson Hyperlegible 400–700 |
| Sizes | body 16px, labels ≥ 14px, buttons ≥ 44px tall |

## Rules kept from the skill

- No warm cream, no serif headlines, no uppercase kickers, no 01/02/03 numbering. Section numbers are filled black pills next to a question.
- Shapes carry group identity (circle, square, diamond, triangle, hexagon, star, pentagon, cross, in group order). Colour carries party, so the two never compete.
- Every chart is a control: clicking or dragging it seeks to that round.

## Where it lives

`src/multi_agent_election/web/eclipse.css` (tokens and components), shared by `setup.html` and `sim.html`. The classic page (`index.html`, `style.css`) is unchanged apart from two links.
