# Who wins depends on who you hear: the talk's experiments

Everything behind the 10-minute talk of 9 November 2026. It is a thin layer on top of
the team's engine in `src/multi_agent_election/`, which is used **unchanged**: the code
here builds towns, runs them, checks the engine with an independent fast simulator,
proves what can be proved, and draws the charts. The first version of the talk is
archived in `v1/`.

## The question

Plurality voting, one name per voter. When people react to the votes they see, who wins?
Four experiments, each changing one thing:

1. **Everyone hears everyone.** Does the town settle, and on whom? (Proved: it settles in one round.)
2. **The voter mix.** 84 mixes of the four voter types.
3. **Hearing only neighbours.** Hearing radius from the whole map down to about 2 people,
   with people walking or standing still. When does it settle?
4. **Propaganda.** An organised 10% minority that always votes for its candidate, with
   extra listeners spread across town.

## The town

| Ingredient | Setting |
| --- | --- |
| Voters | 300 (301 in the robustness runs) |
| Opinions | fixed points in [0,1]^2; 40% around (0.25, 0.45), 60% around (0.64, 0.50), sd 0.10 |
| Candidates | Left (0.25, 0.45), Right (0.72, 0.40), Centre (0.55, 0.62); voters rank them by distance |
| Why this town | Left has the most first choices (about 118), Right beats Left head to head, Centre beats both (Condorcet winner in all 30 towns) |
| Map | the engine's 1x1 square, positions unrelated to opinions; random walk, step <= 0.03 per round, or standing still |
| Hearing | last round's votes of everyone within radius r (1.4142 = whole map) |
| Rounds | round 0 sincere; 40 rounds (150 in long-run checks) |
| Ties | party order shuffled once per town |
| Towns | seeds 0-29; for a seed, opinions, positions, types and tie order are fixed across settings |

Voter types (default mix 40/30/20/10):

| Type | Engine policy | Rule |
| --- | --- | --- |
| Sincere | `sincere` | favourite, always |
| Front-runner | `top_k`, K = 2 | finds the two leaders among the votes it hears; stays if its vote is one of them, otherwise moves to the one it prefers |
| Copycat | `sensed_plurality` | most common vote among the people it hears; ties by own ranking |
| Pivot-seeker | `pivotal` | switches only if its single vote makes a preferred candidate win |
| Minority (Exp. 4) | `sincere` | members always vote for their candidate |

**Engine detail worth knowing.** `top_k` scores the two leaders by the chance of an exact
two-way tie among the other N - 1 voters, counting only splits between the two. When
N - 1 is odd (N = 300) that chance is zero for both, and the engine's inertia rule keeps
the current vote: front-runners are sticky. With N = 301 they always pick their preferred
leader. `fullinfo.py` reproduces both cases exactly. Experiments 3 and 4 are rerun with 301
voters to show which conclusions depend on it.

## Files

| File | What it does |
| --- | --- |
| `town.py` | builds the spoiler town as a raw scenario for `make_scenario` |
| `experiments.py` | every engine setting, by name |
| `run_all.py` | runs the settings on the engine (2 workers), appends to `results/runs.jsonl`, resumable (finished runs are skipped) |
| `fullinfo.py` | exact, fast re-implementation of the four rules under full information |
| `convergence.py` | the freeze-lemma certificate, exhaustive small towns, random 300-voter towns |
| `measures.py` | effective number of parties, head to head, Condorcet, instant runoff, Borda |
| `analyse.py` | every number in the talk and write-up -> `results/summary.json`, `summary.md`, `mixes.csv` |
| `plots.py` | the charts -> `results/figures/` (`slide_*.png` are the bigger-type versions on the slides) |
| `animate.py` | the slide clips, replayed from engine runs -> `results/animations/` (.mp4 + .png still each) |
| `test_presentation.py` | engine vs fast simulator, the town, the builder, the lemma, the measures |

## Reproduce

From the repository root:

```
PYTHONPATH=src:presentation python3 presentation/convergence.py 6 4000   # about 2 min
PYTHONPATH=src:presentation python3 presentation/run_all.py              # about 35 min on 2 cores
PYTHONPATH=src:presentation python3 presentation/analyse.py              # about 1 min
PYTHONPATH=src:presentation python3 presentation/plots.py
PYTHONPATH=src:presentation python3 presentation/animate.py           # about 1 min, needs ffmpeg
PYTHONPATH=src:presentation python3 -m pytest presentation/test_presentation.py -q
```

`results/runs.jsonl.gz` (the branch ships it compressed; `run_all.py` unpacks it to `runs.jsonl` and appends new runs) stores, for every run, each voter's vote in every round (one letter per
voter), the counts, the winner, and how many people each voter heard, so new measures need
no rerun. Full-information runs are the slow ones (about 13 s for 40 rounds).

## Headline results

See `results/summary.md` for every number. In short:

1. **Everyone hears everyone:** all 30 default-mix towns freeze after round 1, proved by the freeze lemma
   (two consecutive clear counts with the same top two => no one moves again) and its
   certificate on each town. Left wins 30 of 30; Centre falls from a median of 83 to 41 votes.
2. **Mix:** Left wins 2,501 of 2,520 elections. Copycats set the margin; front-runners and
   copycats squeeze the third candidate; pivot-seekers act almost exactly like sincere voters.
3. **Neighbours only:** standing still, 149 of 150 towns end in a fixed point or a two-round
   flip-flop and the winner is fixed in 148. Walking with 32 or fewer people heard, votes never
   settle and the first count's leader loses its grip: with 32 heard, Left leads in 29 of 30 towns
   after round 1 and 10 by round 150. The third candidate is no longer squeezed (80-106 votes).
4. **Propaganda:** 30 loyal Centre voters alone lift Centre from 2 to 16 wins in 30 towns (radius
   0.2); with just 5 followers each (150 links: about 2 in 5 voters see a member's vote) Centre
   wins 23; with 20 followers each (each voter hears about 2 extra Centre votes) 29; with 40,
   all 30. With 301 voters: 13, 15, 24 and 30. The slide clip (town 19) compares the same loyal
   group with no followers and with 5 each.

The full write-up (proofs, tables, robustness) is a shared document; its numbers all come from
`results/summary.json`. The freeze lemma and its proof are also in the docstring of `convergence.py`.
