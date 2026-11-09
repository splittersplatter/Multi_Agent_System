# Changes on branch `suchit-sims`

Branch created from `main` at `86de48b` on 9 November 2026.

## 1. Scenario studies (new, no engine change needed)

| Added | Purpose |
| --- | --- |
| `scripts/suchit_sims/common.py` | TOML writer, runner, drawing (shape = agent profile, colour = current ballot), GIF and snapshot helpers |
| `scripts/suchit_sims/spatial.py` | 100-person issue-space electorate (3 nominees) for the watchdog and propaganda studies |
| `scripts/suchit_sims/watchdog.py` | 10 attack simulations plus paired controls, detector search on calibration seeds, held-out validation, attacker best-response grid |
| `scripts/suchit_sims/foreign_intel.py` | 4 spy-cell variants plus paired controls, 8 seeds each |
| `scripts/suchit_sims/propaganda.py` | 4 equal-budget propaganda allocations plus a drift-only control, 5 seeds each |
| `scripts/suchit_sims/echo_chambers.py` | Echo chambers with three strategic campaign parties: full 5×5×5 strategy factorial, Nash analysis, budget sweep, showcase GIFs |
| `scripts/suchit_sims/plugins/spy_comms.py` | Communication plugin: sleeper-cell disinformation guided by sight and eavesdropping |
| `scripts/suchit_sims/plugins/echo_campaign.py` | Movement and graph plugins: fortify, infiltrate, bridge and broadcast campaigns |
| `scripts/suchit_sims/marl_demo.py` | 75-agent, 11-spy rollout through the new MARL environment |
| `scripts/suchit_sims/README.md` | How to run everything |
| `scripts/suchit_sims/slides_figs.py`, `slides_part2.py` | Slide figures and Experiments 5–8 slides in the team deck's format, merged into `docs/suchit_sims/slides/Who Wins Depends on Who You Hear-v2.pdf` |
| `docs/suchit_sims/` | Results: one folder per study with a `README.md` report, figures, GIFs, `summary.json` and the saved TOML configs |

The studies use only existing engine features and plugin hooks. The plugins
follow the engine's permission and budget rules (sight, eavesdropping and
report budgets are enforced by the engine; edge budgets by the campaign plugin).

## 2. MARL interface (small engine change)

See [marl-interface.md](marl-interface.md).

- `model.py`: new movement mode `"external"`.
- `engine.py`: `Simulation.step(external_moves=None)` validates moves and records
  them as replayable position interventions, rolling back on failure. The
  previous `step()` body moved unchanged into `_step()`.
- `marl.py` (new): `MovementEnv`, a PettingZoo-style parallel environment with
  observations, actions, rewards and seeding, standard library only.
- `provenance.py`: `marl.py` added to the pipeline fingerprint.
- `tests/test_marl.py`: 11 new tests.

Because `engine.py` and `model.py` changed, the core source hash changed.
Checkpoints saved with the old code need the usual
`--allow-environment-change` review to replay.

## 3. Verification

- `tests/test_marl.py`: 11/11 pass.
- Full suite on Windows (Python 3.13): **329 run, 9 errors, 2 skipped**. The same
  9 errors occur on an untouched `main` checkout on this machine (318 run, 9
  errors), so they are pre-existing Windows issues, not regressions:
  - `test_majority` and `test_combined_benchmark` import the Unix-only `resource` module;
  - the CLI/benchmark subprocess tests set `PYTHONPATH="src:examples"`, which uses the Unix `:` separator.

  On Linux these tests pass (343/343 earlier on `main`). The branch was not re-run on Linux.
- All study artefacts were regenerated on the final engine code in one pass, so they share a single manifest.

## 4. Local environment

- `.venv/` (already git-ignored) holds matplotlib, Pillow and numpy for the figures. The simulator core still needs only the standard library.

## 5. Merge of `main` into `suchit-sims` (9 November 2026)

Merged `main` at `fba9b08` (commits `f6638a5`, `c207e9c`, `fba9b08`): Gaussian
random-walk movement, `memory_pivotal` voting with periodic polls, state recording
and `view` playback, the 100-person minimum, checkpoint version 25 and many test updates.

Conflicts resolved:

| File | Resolution |
| --- | --- |
| `src/multi_agent_election/model.py` | Kept `main`'s retired-`grid_walk` guard and added `"external"` to the allowed movement modes |
| `src/multi_agent_election/provenance.py` | Pipeline fingerprint lists both `main`'s new modules (`playback.py`, `occupation.py`) and `marl.py` |
| `docs/README.md` | Took `main`'s rewritten index and added rows for the scenario studies, MARL interface and this change log |

`engine.py` merged automatically: `main`'s state recorder runs inside `_step()`, and
`step(external_moves=...)` wraps it, so recorded runs include external moves.

Changes made to stay compatible with `main`:

- **Uniform walk pinned.** `main` made truncated-normal step lengths the `random_walk`
  default. Every suchit-sims scenario that walks now sets
  `parameters.movement = {distribution = "uniform"}` (`common.pin_uniform_walk`), the same code
  path as before, so published results reproduce exactly. Verified on the merged engine:
  foreign-intelligence F2 win rates (62.5% vs 25%) and seed-1 counts (A 38, B 41, C 21),
  echo-chamber all-passive and all-infiltrate payoffs (identical to 4 decimals), watchdog
  W1/W4 and propaganda P2. The 8 saved foreign-intelligence configs were patched the same way.
  The watchdog and propaganda studies use stationary voters and are unaffected.
- **100-person minimum.** `main` rejects simulations with fewer than 100 people outside
  unit-test verification scope. Changes:
  - `showcase70` became `showcase100` (88 residents + 12 campaigners);
  - the Experiment 4 demo became 100 voters with 10 loyal fans and 0/5/20 followers
    (Centre wins 16/22/29 of 30 seeds; demo seed 20);
  - `marl_demo.py` became 100 agents (85 residents + 15 spies);
  - the 30-person foreign-intelligence demo (`foreign30*`) was removed; use the 100-person
    configs in `docs/suchit_sims/foreign_intelligence/configs/` instead.
- **Tests.** `tests/test_marl.py` uses `VerificationTestCase`, since its fixtures have 5 people.

Verification on Windows (Python 3.13): the merged branch runs 402 tests (`main`'s 391 plus
the 11 MARL tests). The same 12 tests error on an untouched `main` checkout on this machine, so
the merge adds no regressions. All 12 are Windows-only issues: the Unix-only `resource` module
(5) and subprocess tests that set `PYTHONPATH` with `:` (7). The merged browser server starts and
records states for `showcase100.toml`.

## Set up and Watch pages (Explorable redesign)

Two new browser pages, served alongside the classic page; full guide in
[frontend-redesign/README.md](frontend-redesign/README.md).

- `/setup` builds a scenario by clicking. It covers:
  - parties, ballot size, rounds and seed;
  - group cards: voting rule, movement, hearing range, powers;
  - a draggable map of every person's starting spot and beliefs, with box-select, make-group, bulk edit and seeded add-people;
  - optional campaign, poll and watchdog controls.

  Scenarios import and export as TOML or JSON (copy, paste or file) and are checked live by the real engine. Exports list every person explicitly, so seed plus file reproduces a run exactly.
- `/sim` is the new watch view:
  - hearing-range halo, incoming and outgoing ego network by edge type;
  - new and broken links per round, plus an optional two-steps-out subgraph;
  - a plain-English "Right now" card and per-group vote mixes;
  - up to 11 time-series charts that click to seek;
  - all-or-nothing bulk edits mid-run, and handing a crowd back to `/setup` as a new group.
- Server additions in `visual.py`:
  - `GET /scenario` and `POST /scenario/{convert,validate,launch}`;
  - a `bulk_edit` command that rebuilds the exact pre-edit history if any edit fails.

  New module `scenario_io.py` (TOML writer and TOML/JSON parser). The new files are registered in the provenance manifest.
- The design direction was chosen via the huashu-design three-draft gate:
  [frontend-redesign/direction-approved.md](frontend-redesign/direction-approved.md).
- Tests:
  - `tests/test_setup_pages.py` (7 tests). The full suite is now 409 tests, with the same 12 Windows-only errors as `main`.
  - `scripts/frontend/e2e.mjs` runs 31 browser checks through both pages in headless Edge; all pass with no page errors.
