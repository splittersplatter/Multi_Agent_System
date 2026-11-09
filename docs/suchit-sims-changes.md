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
