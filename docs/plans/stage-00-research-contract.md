# Stage 00: Research contract

Status: baseline specification; no model results. Date: 2026-11-05.

## Current scope

- Engine, tests, CLI and examples exist; [status](../implementation-status-report.md).
- Corpus31 reviewed works/36 PDFs. Only supported actual schemas/artifacts establish replay compatibility.
- Adopted plurality, TOML/Python plugins, stdlib browser and optional Pillow.
- Normal outcome runs N>=100; the baseline below is a tiny formal/unit oracle only.

## Hand-worked baseline

Parties `A,B,C`; tie order `A,B,C`; `k=2`; sincere ballots = first two
entries of each private ranking; plurality counts the first ballot entry.

| Person | Private ranking | Ballot |
| --- | --- | --- |
| 1 | A > B > C | A > B |
| 2 | A > C > B | A > C |
| 3 | B > C > A | B > C |
| 4 | B > A > C | B > A |

Expected counts: `A=2, B=2, C=0`; winner `A` by tie order. Zero-based
winner ranks: `0,0,2,1`; mean `0.75`. Honest repeated rounds with stationary
agents and no interventions retain ballots, counts and winner. If person 2
submits `C>A`, counts become `A=1,B=2,C=1`; winner `B`. A separate zero-change
intervention must reproduce the honest result exactly.

Replay gate: identical configuration, software/plugins and named random keys
produce identical committed states/events; checkpoint/resume reproduces the
uninterrupted suffix, including pending messages, policy memory and RNG keys.

## Research register

Each question compares matched electorate, graph, schedule and exogenous draws.
Win/share refer to the designated target; measure per-seed deltas and report
cycles/cutoffs. S-numbers reference the [survey](../election-manipulation-literature-survey.md).

| Mechanism / prior | Falsifiable question | Allowed action / observation | Control | Primary outcome |
| --- | --- | --- | --- | --- |
| 1 proximity; S9-S10,S28-S29 | Does edge turnover change winner frequency at matched exposure? | Bounded movement; local observations | Static degree/exposure-matched graph | Winner-change rate |
| 2 coalition; S8,S18,S27 | Does each capability change target wins at fixed coalition size? | Scoped sight, private messages, false reports, sensing | No capability / one-at-a-time | Target-win delta |
| 3 edges; S11,S15-S16 | Does strategic edge selection outperform equal-budget random selection? | Budgeted edges; controller's declared view | Zero and random edges | Target-win delta |
| 4 polls; S12-S14 | Do epistemic and poll-confident responses differ under matched distorted polls? | Bounded public count report; true aggregate visible only to controller/evaluator | Truthful/random report; matched voter rules | Target-win difference |
| 5 nomination; S22,S29-S30 | Does nominee composition change winner alignment? | Network nomination; allowed neighbor/self positions | Exogenous equal-sized set; same-nominee equivalence | Winner distance |
| 6 detective; S18,S22-S23,S29 | Can aggregate-only detection precede three wins without excess false alarms? | Bounded voter-ideal shifts; detective sees aggregate history | Drift/no attack; random shifts | Early-alert recall + false-positive rate |
| 7 leader; S22,S30 | Do indirect signals of hidden adaptation change votes? | Bounded leader movement; public behavior signals | Fixed/no-signal leader | Winner-change rate |

## Transition and information contract

Round zero: initial state and sincere ballots. Thereafter: boundary interventions;
simultaneous movement/proximity rebuild; ordered controller actions; authorized
observations and prior-round messages; simultaneous ballot choices; tally,
detector and commit. New messages arrive next round. Strategies receive only
declared observations, immutable/copied from truth; researcher inspection is not
policy input. Truthful observations and untrusted reports are distinct.

| Actor | Default observation | Allowed action |
| --- | --- | --- |
| Voter | Own ranking/state, permitted local reports, public signal | Ballot, authorized movement/message/graph actions |
| Coalition | Member observations plus explicitly enabled capability | Budgeted sight, private message, report or sensing |
| Edge controller | Declared public/controller view | Insert eligible campaign edges |
| Poll controller | True last completed aggregate, not private rankings | Publish bounded report |
| Leader | Public history, own state | Bounded own alignment shift |
| Detective | Declared aggregate ballot history only | Passive alert; no hidden attack labels |
| Evaluator | Full truth, outputs and costs | Metrics only; never feeds hidden truth to policies |

Separate budgets: sight targets, messages, added directed edges, poll transfers
`L1/2`, voter-alignment path length, leader-alignment path length; sensing radius
is a distinct capability bound. Log requested/accepted/rejected actions and
costs. Shared paired exogenous draws use stable named streams keyed by process,
actor and round; an identical seed alone does not guarantee pairing.

## Stage gates and setup

- Each stage: hand-worked and adversarial tests, information/budget boundaries,
  zero-action equivalence, replay/resume, matched controls, cumulative integration;
  record config/seed/versions, outputs, evidence and unresolved limits in its file.
- Python >=3.11; observed 3.14.4. Stage 01 core uses the standard library;
  optional image export pins Pillow in `requirements-visualization.txt`.
  Check: `PYTHONPATH=src python3 -m unittest discover -s tests -v`; require
  nonzero tests. Record setup and validation in Stage 01.
- Treat empirical findings and novelty as unverified until matched experiments;
  missing prior code is a compatibility limitation, not a scientific blocker.
