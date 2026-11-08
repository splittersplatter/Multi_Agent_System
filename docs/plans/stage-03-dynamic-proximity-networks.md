# 03: Dynamic proximity — mechanism 1

Proposed; inherits 02. [Gates](README.md).
References: survey S9-S12, S28-S29.

## Deliverables

- [ ] Extend existing mobility hooks: stationary/bounded random walk, per-group
  speed/radius, reproducible draws; physical != ideological space.
- [ ] Validate per-round proximity; preserve persistent/campaign/private layers.
- [ ] Controls: frozen initial graph, dynamic contacts, static degree/exposure-matched
  graph; report residual mismatch.
- [ ] Compare sincere/strategic outcomes, exposure and turnover:
  |E_t Δ E_previous| / |E_t ∪ E_previous|; empty union -> 0.
- [ ] Radius/layer overlays; round-indexed movement GIFs/contact plots; reproducible scheduled edits.

## Acceptance

Radius equality, reflection, coincident/isolated people; zero-movement static equivalence;
spatial-index/brute-force agreement; layer persistence; renderer matches engine.
Matched movement streams; no pure-turnover claim with uncontrolled exposure.
Cumulative run: prior policies/groups/messages + moving graph + replay/edit/export.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Early extension: directed proximity/public edge additions, removals, turnover and mean proximity in-degree; contact/turnover sidebar plots | Hand-calculated overlap, empty union and missing-round tests; export and JS harness checks | Frame metrics, JSON/JSONL/CSV and existing playback; certified cases remain separate | Stage 02 incomplete; per-group radius, matched controls and causal comparisons pending; live browser check blocked by approval usage limit |
| 8 Nov 2026 | Group/person receiver radii + selected-radius overlay | [Example](../../examples/group-radius.toml); [tests](../../tests/test_network.py): brute-force directed oracle, equality/coincident/tiny radii, invalid settings, sensing, group change, rewind/replay, F3 asymmetry guard; JS playback overlay checks | Global-radius default preserved; movement, channels, all graph layers, checkpoint, CLI and browser session share engine | Stage 02 incomplete; frozen/exposure-matched controls, causal comparisons and exported radius overlay pending; live browser interaction unverified |
| 8 Nov 2026 | Frozen initial proximity + paired dynamic/frozen comparison | [Tests](../../tests/test_network.py): hand-worked directed exposure residual, motion parity, zero movement, changing radii/positions, replay, malformed configs, retained failed pair, CLI/summary parity; [browser harness](../../tests/playback_harness.js) verifies initial-position overlay | Frozen layer stays separate; existing movement, sensors, other layers, checkpoints and certified guards retained | Not exposure/partner/timing matched; static degree/exposure-matched control and causal comparisons still pending; live browser interaction unverified |
| 8 Nov 2026 | Frozen-control integration regression | Full suite 183 pass; `python3 -S`: 180 pass, 3 image skips; HTTP state/step and JS overlay checks pass | Existing scenarios, prior proofs, CLI/export/replay remain available | Stage 02 and remaining Stage 03–11 gates incomplete; browser interaction still unverified |
| 8 Nov 2026 | Calibration-built static directed control | [Network tests](../../tests/test_network.py): brute-force 64 static graphs, independent calibration/evaluation, deterministic ties, held-out exposure/timing residual, rejection of overlapping seeds and future topology edits, replay/CLI, F3 directed-graph guard | Same engine, per-round metrics, explicit static proximity and all existing layers; no exposure or convergence claim without evidence | Calibration-optimal exposure is not guaranteed on evaluation; partner/timing/public-layer mismatch and causal identification remain; full stage gates and browser interaction pending |
| 8 Nov 2026 | Calibrated-control integration regression | Full suite: 186 pass; `python3 -S`: 183 pass, 3 image skips; JS overlay and diff checks pass | Existing frozen/dynamic controls, certified guards and stage scenarios retained | Stage 02 and remaining Stage 03–11 gates incomplete; no comparative research conclusion |
