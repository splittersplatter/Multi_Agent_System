# Eclipse roadmap

Status: Stage 00 verified; Stage 01 acceptance open; Stages 02–10 partly implemented;
Stage 11 pending. [Stage plans](plans/README.md) · [Code audit](code-audit-and-refinement-report.md).

[Heuristic evaluation](plans/heuristic-evaluation.md): audit/metrics specified;
restricted [convergent foundation](convergence-foundations.md) adopted for future
studies; full-model guarantee remains refuted. F1–F3 and scheduled F4/F5 implemented;
research experiments and remaining stage gates pending.

## Scope

- One cumulative simulator; seven controlled mechanism studies; integrated ablations; reproducible report.
- People: group policies, capability permissions, movement, messaging, ranked voting.
- Ballots: exactly `k` distinct ranked parties per voter; global `1 <= k <= |C|`.
- CLI + local browser; editable timeline; network/per-agent views; stats; plots/GIFs.
- Rewind + edit replaces future; no automatic branching.
- Shared information boundaries; selected exact finite epistemic checks.
- Hidden leader alignment observable only through indirect public behavior signals.

Adopted Stage 01 defaults: first-choice plurality over ranked ballots;
TOML configuration + Python plugins; optional image-render dependency.
Planned: counting-rule adapter;
10k CLI / 500 visual-agent benchmark targets, not achieved guarantees.

Sources: [final proposal](</home/dhruv/Downloads/Eclipse-MAS-Proposal.pdf>),
[literature survey](election-manipulation-literature-survey.md).

## Stages / deliverables

| Stage | Added deliverable |
| --- | --- |
| 00 | Baseline audit; compatibility; research protocol |
| 01 | Repeated simulator; groups; ranked ballots; graphs; CLI/browser; plots/GIFs |
| 02 | Observation boundaries; epistemic policies; exact checks; response baselines |
| 03 / mechanism 1 | Dynamic proximity experiments; exposure-matched controls |
| 04 / mechanism 2 | Coalition sight, coordination, deception, eavesdropping |
| 05 / mechanism 3 | Budgeted campaign edges |
| 06 / mechanism 4 | Bounded public-report distortion |
| 07 / mechanism 5 | Alignment preferences; in-network nomination |
| 08 / mechanism 6 | Voter-alignment attacks; aggregate-only detective |
| 09 / mechanism 7 | Hidden leader adaptation; public signals/perceptions |
| 10 | All-enabled model; isolated controls; leave-one-out ablations |
| 11 | Frozen experiments; uncertainty; report; reproducible package |

Stage 00 contract verified; Stage 01 baseline and initial engine implemented;
integrate epistemics in Stage 02; later stages validate mechanisms.

## Invariants

- Private preferences, submitted ballots, reports, public counts and perceptions remain separate.
- Graph layers: persistent, proximity, campaign, private channels; explicit permissions.
- Separate sight/message/edge/signal/alignment budgets; log proposed, accepted and rejected actions.
- Nominate before round zero; stable candidate IDs thereafter; candidate count >= k.
- Isolated mechanism 7: preselected leaders; combined model: nominated leaders.
- One winner per round; passive detective alerts before third consecutive target win.
- Knowledge factive; false reports not truthful announcements; approximate beliefs labelled.

## Completion

Follow [shared stage gates/progress](plans/README.md#shared-gates).
Metrics: target-win frequency, paired share/margin changes, winner rank, switching,
contact exposure, realized costs, cycles/cutoffs, runtime; detector false alarms/recall/delay.
Changing preferences: evaluate initial and current ideals.
Null results valid; claims require evidence.
