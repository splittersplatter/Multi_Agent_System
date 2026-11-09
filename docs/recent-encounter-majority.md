# Recent-encounter majority estimator

Opt-in plurality belief; the estimator alone does not change ballots. The
`memory_pivotal` voter can use it to decide ballots. No convergence,
population-representativeness or calibrated-confidence claim.
[Maintained plan](plans/recent-encounter-majority.md).
[Implementation/results report](majority-estimation-report.md).

## Configure/run

Add to an ordinary scenario; counts follow its `parties` order:

```toml
[majority_estimation]
poll_counts = [40, 35, 25] # supplied initial poll; never silently derived census
memory_rounds = 10
poll_refresh_rounds = 10 # optional; periodic completed tallies + linear decay
poll_round = 0
```

Omit table or set `enabled=false` to disable. Window: positive integer; weight:
finite `[0,1]`; poll: nonnegative integers, positive total, one count/party.
Without `poll_refresh_rounds`, the poll stays fixed and `poll_weight` (default
0.5) controls the blend. With `poll_refresh_rounds = 10`, the poll begins at the
explicit supplied sample; the completed election tally is published after every
10th round. For decisions in rounds 1–10 the poll weights are 1.0, 0.9, …, 0.1;
the completed round-10 tally resets the weight to 1.0 for round 11. Subsequent
cycles repeat. `poll_weight` is used only in fixed-poll mode. With no remembered
contacts the latest poll is used alone. Public-signal controller reports remain
separate and do not replace this scheduled truthful tally. Inspector fields
`poll_weight` and `effective_poll_weight` distinguish scheduled weight from the
100% poll fallback when no contacts are cached.

From repository root:

```bash
# Interactive network; select a node and inspect majority_estimation.
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000
# Browser: http://127.0.0.1:8000

# Exploratory strategic voting based on this estimate.
PYTHONPATH=src python3 -m multi_agent_election.cli visual examples/recent-majority.toml --port 8000 --voting memory_pivotal

# Efficient CLI; frames discarded, estimator state retained.
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/recent-majority.toml --summary

# Full history/checkpoint; output must not exist.
PYTHONPATH=src python3 -m multi_agent_election.cli run examples/recent-majority.toml --checkpoint outputs/recent-majority.json
PYTHONPATH=src python3 -m multi_agent_election.cli resume outputs/recent-majority.json --rounds 10 --output outputs/recent-majority-resumed.json
PYTHONPATH=src python3 -m multi_agent_election.cli export outputs/recent-majority.json --csv outputs/recent-majority.csv

# Built-in matched pilot, five seeds × three cases × two movement conditions.
PYTHONPATH=src python3 -m multi_agent_election.cli estimate-majority --pilot --sensitivity --output-dir outputs/majority-pilot-new

# Evaluate the configured periodic scenario too.
PYTHONPATH=src python3 -m multi_agent_election.cli estimate-majority examples/recent-majority.toml --seeds 101 102 --output-dir outputs/majority-custom-new
```

`outputs` must exist (`mkdir -p outputs`); directories/files are exclusive, never overwritten.
Browser example: **200 distinct voters**; built-in pilots also use 200.
All normal simulations require **at least 100** people. Smaller legacy examples
are verification fixtures, not runnable outcome scenarios; no automatic padding.

## Semantics/state

- Round zero: poll only; no initial encounters.
- Round r: after movement, incoming proximity arcs expose completed ballots r−1.
  Receiver radius controls reach; no self, outgoing-only or remote-layer observations.
- Estimator-only visibility is explicit opt-in; existing ballot-sensing permissions
  and policy observations are unchanged. Private rankings are never read.
- One latest first choice/neighbor, with encounter/source rounds. Repeated contacts
  refresh but never increase that person's weight; changed votes replace counts.
- Retain encounters `[r−memory_rounds+1,r]`; expire even without new contacts.
  Entries' IDs are the visited-neighbor set. No full-ballot/lifetime visit history.
- Delayed/old records cannot refresh; equal-source conflicting first choices fail.
- Cache reads do not refresh; committed records are immutable. Voting-policy edits
  preserve cache. Rewind restores state; edits replace the future.
- Checkpoint23 carries periodic polls; checkpoint22 carries fixed-poll estimator
  state. Disabled histories retain version21;
  older supported histories replay without inventing observations. Source changes
  still require explicit environment-migration approval after review.

For n cached people, `recent_share(c)=count(c)/n` and w is the current poll weight:

`estimate(c)=w×poll_share(c)+(1−w)×recent_share(c)`.

Empty cache uses poll alone, including when w=0. No smoothing/age weighting.
Exact integer-score comparison preserves leader ties; exported shares are floats.
Per-agent JSON/inspector exposes shares, leaders, sample size, counts, entries,
encounter/ballot ages, poll age and timestamps. CSV exposes aggregate cache size
and empty fraction; full per-person records remain in JSON/JSONL/checkpoints.

## Complexity/limits

Active state per person: O(U+m), U retained unique neighbors, m parties. Map
updates/expiry expected O(1)/record; immutable snapshot copying O(U); canonical
ordering O(d log d) worst case for unordered d observations (engine contacts already
ordered). Full update is not constant time. Dense population memory can be O(N²).
Full-history/checkpoints duplicate state; `--summary` discards frames, not current cache.

The initial sample can be biased; between publications the tally can become stale.
Clustering/repeated encounters are not
independent random population samples. Finite memory and movement can oscillate;
stable beliefs/strategic-voting convergence are not certified.

## Pilot artifacts/evaluation

- `context.json`: command, environment/source hashes, seeds, RNG convention.
- Per run: `scenario.json`, `sampling.json`, compressed `trace.jsonl.gz`,
  `predictions.jsonl.gz`; `results.json` lists statuses and SHA-256/byte sizes.
- Raw prediction arrays follow header person/party order. Truth belongs only to
  evaluator; round-r estimates are compared with actual ballots r−1.
- Controls: poll-only (no cache), current-contact/window-only (w=0), blend.
  Empty-contact/window controls fall back to poll, explicitly.
- Cases: 80A/70B/50C; two initial clusters 70/20/10 and 10/50/40;
  shift20A→B committed round50. Moving step≤.025, radius .12; cluster membership
  is initial spatial placement, not a permanently enforced community.
- Poll: initial sample100 without replacement, independent keyed RNG; stationary
  and moving versions share layout, preferences and sampled IDs.
- Four base arms; optional K5/20 and w.25/.75 extend K10/w.5 one factor at a time.
  For periodic input, poll-only uses the most recently published tally;
  current/window-only use contact weight 1, falling back to that poll if empty;
  window sensitivity uses linear decay; fixed-weight sensitivity uses the latest
  published tally with the specified fixed weight. Headers record these semantics.
- Metrics: exact leader-set match, ambiguity, total-variation share error,
  coverage/ages, cache entries, median/p95 population update and engine-round times.
- Recovery: first correct leader-set match after source round50, delay0 allowed;
  not sustained recovery. Report recovered-only delay plus unrecovered fraction.
- Serialized frame bytes include initial/final frames but exclude checkpoint wrapper.
  RSS is process-lifetime high-water, including evaluator—not per-arm allocation.
  Timings include immutable copying and exclude compression/statistics for arm updates.
- Five-seed pilot is exploratory; formal selection requires disjoint calibration,
  frozen parameters, ≥30 held-out seeds/scenario and run-level uncertainty.

## Verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p test_majority.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
node tests/playback_harness.js
```

Tests challenge window boundaries, refresh/expiry, independent randomized oracle,
ties, stale/conflicting data, hidden-information access, directed/coincident contacts,
transaction failure, policy changes, replay/tampering, HTTP/CSV and inspector parity.
Current suite/evidence: [status](implementation-status-report.md#verification).
Actual200-node browser rendering must be checked separately from HTTP/JS tests.
