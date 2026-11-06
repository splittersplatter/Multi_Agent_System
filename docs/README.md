# Project documentation

## Plan

- [Roadmap: scope, invariants, deliverables](project-roadmap.md)
- [Stage plans: dependencies, acceptance, cumulative progress](plans/README.md)

## Current state

Checked 6 November 2026. Stage 00 verified; Stage 01 in progress. Current Python
source/tests cover ranked ballots, group policies, movement, scoped messages,
edits, replay, exports and browser commands. The older deleted implementation
and its artifacts remain absent. Core uses the standard library; optional image
exports pin Pillow in `requirements-visualization.txt`.

Record progress, checks, setup and decisions in each stage's progress table.
Stage 01 remains in verification; 1A–1C verified, 1D–1G and Stages 02–11 pending. The 91 current tests
pass; earlier deleted-baseline results are historical, not current evidence.
Current [simulator guide](simulator-guide.md).

## Research

- [Literature survey and candidate gaps](election-manipulation-literature-survey.md)
- [Historical epistemic API reference](paper-implementation.md)

Use [README](../README.md) for current commands and [Stage 01 progress](plans/stage-01-political-simulator.md#progress) for verified scope.
