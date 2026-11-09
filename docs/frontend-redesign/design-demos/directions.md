# Simulator frontend: design spec and direction cards

Following the huashu-design three-direction gate. Drafts in this folder use one real
40-round run (`demo-data.json`, from `scripts/suchit_sims/showcase100.toml`).

## Spec (what it must say, not how it looks)

- **Product:** Eclipse, a research simulator of elections where 100+ agents move, hear
  neighbours inside a radius, follow campaigners, and change votes. Two pages to build later:
  an **experiment setup** page (interactive config, copy/paste import/export, seed, initial
  positions and beliefs) and a **simulator** page (this draft).
- **Audience:** the research team and course reviewers, on laptops. They watch dynamics,
  inspect individual agents, and edit groups of agents during a run.
- **Core messages on the simulator page:** who hears whom right now (radius, incoming and
  outgoing neighbours, ego subgraph, edge types: proximity, follow links bought by campaigners,
  paid campaign links); who holds which powers; how the election evolves over time
  (many synced plots); and that a group of agents can be selected and acted on together.
- **Tone:** precise and calm; the network is the hero, not decoration.
- **Format:** desktop web page, 1440×900 first screen; must remain usable at narrower widths.
- **Known constraints:** no build step (plain HTML/JS served by the Python server); party
  colours stay distinguishable (A blue, B orange, C green family); text ≥14px, labels ≥12px,
  contrast ≥4.5:1; hit targets for controls ≥44px.

## Six candidates

| # | Logic and source | What is borrowed | Hero material | Skeleton | Where the boldness goes | Form comes from |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Best designer, bold: **Nicky Case** (explorable explanations; *Parable of the Polygons*, *The Wisdom and Madness of Crowds*). Not viewed directly this session. | Plain-language questions as headings, chunky direct-manipulation controls, friendly geometric agents with thick outlines | The town itself, big | Question-led: one large town, a "what you're looking at" rail, two big annotated charts | Agents drawn large and friendly; plain-English captions that change with hover | Elections are social: "who do you hear?" is the question |
| 2 | Best designer, restrained: **Stamen Design** (cartographic data viz). Not viewed directly. | Map plate with coordinate ticks, quiet basemap, small multiples, labels in place | Town as a map plate | Plate left, 3×3 small-multiple wall right, slim timeline | The wall of nine synced sparklines | The map is literal: position decides who you hear |
| 3 | Real reference: **Kepler.gl** (spatio-temporal analysis tool). Not viewed directly. | Full-bleed dark canvas, layer panel, brushed time bar | Network glowing on dark | Canvas centre, layers left, inspector right | Edge layers as light | Layers of hearing |
| 4 | Real reference: **Ableton Live arrangement view**. Not viewed directly. | Stacked track lanes under one shared playhead | Time-series lanes | Canvas top, 6–8 synced lanes bottom | One playhead through every plot | Rounds are a timeline |
| 5 | Roulette, web No. 8 **Cinematic sound-viz** | Black field, white type, waveform motif | Vote shares as waveforms | Giant waveform band under the town | Shares rendered as audio-like waves | The election "sounds" over time |
| 6 | Roulette, East Asian No. 12 **Japanese magazine, dense** | Annotated map with numbered dots and handwritten notes; bold-ruled 3×3 data grid | Annotated town map | Map left, ruled data grid right | Handwritten annotations | A field notebook of the town |

## Three chosen for full drafts

- **dir-1 Observatory** = candidates 3 + 4 merged (instrument: dark canvas, layers, shared-playhead track lanes). Bold, dark.
- **dir-2 Atlas** = candidate 2 (map plate + small-multiple wall). Quiet, light.
- **dir-3 Explorable** = candidate 1 (question-led, friendly, large). Warm, playful.

Candidates 5 and 6 are kept as alternates in `thumbs.html`. Candidate 5 is the "overdone"
risk (removing the waveform metaphor makes the shares clearer), so it was not built in full.
