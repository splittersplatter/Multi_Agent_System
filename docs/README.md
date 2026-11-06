# Project documentation

## Plan

- [Roadmap: scope, invariants, deliverables](project-roadmap.md)
- [Stage plans: dependencies, acceptance, cumulative progress](plans/README.md)
- [Implementation status and browser check commands](implementation-status-report.md)
- [Voting heuristics: startup selection, parameters, experiments](voting-heuristics.md)
- [Heuristic verification: independent checks and test-run results](heuristic-verification-report.md)

## Current state

Checked 6 November 2026. Stage 00 verified; Stage 01 in progress. Current Python
source/tests cover ranked ballots, group policies, movement, scoped messages,
edits, replay, exports and browser commands. The older deleted implementation
and its artifacts remain absent. Core uses the standard library; optional image
exports pin Pillow in `requirements-visualization.txt`.

Record progress, checks, setup and decisions in each stage's progress table.
Stage 01 remains in verification; 1A–1D verified, 1E–1G and Stages 02–11 pending.
Workspace audit: no tracked files missing; local documentation links resolve.
Current suite: 134 tests pass; `python3 -S`: 131 pass, 3 optional-image skips. Browser inspector, keyboard focus, local draft isolation, preference proxy
and overlapping-layer rendering tested. 1E saved-file download handoff remains unverified;
the latest prepared file has a revision-labeled retry link, but the in-app
download-event API also timed out on an independent plain-link probe.
Actual preference beliefs are Stage 02 work. Earlier deleted-baseline results and unavailable
artifacts are historical, not current evidence; do not restore deleted files.
Current [simulator guide](simulator-guide.md).

User-requested extension: ten strategic plurality policies, startup selector and
matched-seed comparison implemented. Source mappings/limits: [voting reference](voting-heuristics.md).
This does not complete Stage 02: full epistemic models and knowledge checks remain pending.

## Research

- [Literature survey and candidate gaps](election-manipulation-literature-survey.md)
- [Paper-by-paper heuristics, metrics and simulator mappings](literature-heuristics-and-metrics.md)
- [Local reference collection / access blockers](../References/README.md)
- [Historical epistemic API reference](paper-implementation.md)

Research audit 7 November 2026: 31/32 works collected/reviewed from full text;
S24 blocked, lawful copy requested. 36 PDFs including five retained versions;
original three unchanged. No simulator changes or new experiments; earlier test
evidence above remains dated 6 November. Methods/metric ambiguities are explicit.

Use [README](../README.md) for current commands and [Stage 01 progress](plans/stage-01-political-simulator.md#progress) for verified scope.
