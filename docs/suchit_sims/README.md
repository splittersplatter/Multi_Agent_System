# Scenario studies (branch `suchit-sims`)

Four manipulation scenarios, each run on the project's own engine with at most 100
agents. In every network figure and GIF, **shape = agent profile** and **colour =
current vote**. Each study folder holds a report (`README.md`), figures, GIFs,
`summary.json`, and the exact TOML configs of the showcase runs, so any of them
can be replayed with the CLI.

**Slides:** [Who Wins Depends on Who You Hear-v2.pdf](slides/Who%20Wins%20Depends%20on%20Who%20You%20Hear-v2.pdf)
is the team deck with these studies added as Experiments 5–8 (26 pages; the new-only pages are in
[part2_slides.pdf](slides/part2_slides.pdf)). Rebuild with `scripts/suchit_sims/slides_figs.py` then `slides_part2.py`.

Code and run instructions: [`scripts/suchit_sims/`](../../scripts/suchit_sims/README.md) ·
Change log: [suchit-sims-changes.md](../suchit-sims-changes.md) ·
MARL interface: [marl-interface.md](../marl-interface.md)

| Study | Simulations | Headline result |
| --- | --- | --- |
| [Watchdog](watchdog/README.md) | 10 attacks with paired controls; 420 runs in total | The engine's single-round detector catches only **80%** of winning attacks: slow drips slip under it. The best watchdog strategy found, **"alert if the target rose more than 4 points over 3 rounds"**, catches **100%** before the third win with **0%** false alarms on held-out data. In a 36-strategy grid the attacker found no way to win undetected. |
| [Foreign intelligence](foreign_intelligence/README.md) | 4 spy-cell variants with paired controls × 8 seeds (64 runs) | With the same 1,500 lies, **knowing whom to lie to** (preference sight) lifts B's win rate from **25% to 62%**; blind lies reach only 38%. Eavesdropping adds nothing beyond sight. Residents who check real ballots are almost immune. |
| [Long-term propaganda](propaganda/README.md) | 4 equal-budget campaigns plus control × 5 seeds (25 runs) | **Swing-focused** propaganda wins by round 5 and holds about 92% of rounds. **Broad, shallow** propaganda builds a 63% majority. Random pushes do nothing. Effects persist after spending stops, and the winner ends up **24% further from voters' original views** while looking closer to their manipulated ones. |
| [Echo chambers + strategic campaigns](echo_chambers/README.md) | Full 5×5×5 strategy factorial × 3 seeds plus budget sweep (435 runs) | The front-runner should **infiltrate**, the challenger should **fortify**, and the underdog **never wins** (0 of 375). There is no exact Nash equilibrium: best responses cycle. The stable outcome is a **mutual-invasion arms race** that breaks the chambers (purity 79% → 55%) but barely changes the result. |

## Agent shapes used

| Study | Shapes |
| --- | --- |
| Watchdog, propaganda | ★ candidate platform · ▲ attacked/targeted voter · ● other voter (drawn in issue space) |
| Foreign intelligence | ▲ spy · ● report-trusting · ■ sensor-checking · ◆ committed partisan; red arrows = lies this round |
| Echo chambers | ● conformist · ⬢ committed partisan · campaigners ■ fortify, ▲ infiltrate, ◆ bridge, ✚ broadcast, ▼ passive; arrows = campaign edges by party |

## Common caveats

- These are synthetic electorates of up to 100 agents with stylised behaviour (sincere, conformist or report-following voting). The results compare strategies inside this model; they are not predictions about real elections.
- Seed counts are modest (3–8 per configuration). Large differences are robust; differences of one or two voters are not.
- Every attack and campaign obeys the engine's permission and budget rules. The watchdog's detectors use only public vote counts.
