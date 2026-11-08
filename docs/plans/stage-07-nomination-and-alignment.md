# 07: Nomination / alignment — mechanism 5

Proposed; inherits 06. [Gates](README.md).
References: survey S22-S23, S29-S30.

## Deliverables

- [x] Issue vectors in [0,1]^d; physical positions separate.
  Euclidean distance -> full ranking; party-order ties; ordinal-input adapter.
- [x] Proposed nomination: each person chooses closest eligible public neighbor/self;
  top m nomination counts win; stable ID ties including zero-count fill.
  Validate k <= m <= eligible population.
- [x] Nominate before round 0; stable leader/party mapping; fixed membership.
  Leaders remain single-vote people. Baseline leader positions public/fixed;
  voter ideals private.
- [x] Endogenous, identical-nominee exogenous, equal-size random-nominee controls; track composition.
- [x] Nomination ballots/counts/winners; leader badges; physical/issue views; representation-distance metrics.

## Acceptance

Dimensions/bounds/ties; self/isolated nomination; insufficient eligible people;
m=k; valid length-k ballots; stable IDs/replay; manual edits logged.
Same nominees + no nomination information effect -> equivalent voting.
Report selected IDs, representation distances and winner effects; representativeness measured.
Cumulative run: nominees + earlier network/coalition/edge/poll mechanisms;
CLI/browser/plots/checkpoints.

## Progress

| Date | Work/status | Evidence | Prior integration | Remaining |
| --- | --- | --- | --- | --- |
| 8 Nov 2026 | Spatial nomination, controls and representation metrics | [Example](../../examples/nomination.toml), [contract](../simulator-guide.md#spatial-nomination), [tests](../../tests/test_nomination.py), JS harness: initial public-neighbor/ID ties, abstention, zero fill, fixed/random controls, ideal distances, CLI/HTTP/CSV/replay | Shared engine; prior ordinal scenarios, coalition sight, campaign edges, signals and restricted F1 retained | Full stage/shared gates and live browser verification pending; no validated research effect, preference-drift or leader-adaptation implementation |
| 8 Nov 2026 | Nomination integration regression | Full suite 268 pass; `python3 -S`: 265 pass + 3 optional-image skips; proof checker, playback harness and `git diff --check` pass; checkpoint v18 validates nomination record | Preserves historical cases, bound-signal responses, earlier checkpoint migration and seeded control replay | Stage 01/shared acceptance, live browser check, spatial attacks, adaptation and formal evaluation remain open |
