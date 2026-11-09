# Historical scale measurements

Status: preliminary, individual runs; not performance guarantees. All
measurements below predate the current runtime. Last measurement update:2026-11-08.
Machine: Intel i7-12700H, x86_64 Linux 7.0.0, CPython 3.14.4.
Original measurement core SHA-256: `629c342418714bd502d75a7393c9f88856e7e1efbeadc80649aac8ca5251b259`.
Shared, non-isolated machine; some other test activity overlapped the CLI run.

[Current status](../implementation-status-report.md). Current runs require N>=100;
all measured workload sizes below satisfy that floor. Use new output paths.

## Workload and reproduction

Three parties, `k=3`, seed 2026, random fixed positions, stationary/sincere
agents, no communication/interventions, proximity radius chosen for nominal
mean degree 12. Actual directed mean degree: 11.7932 (10k), 10.94 (500).
Each run validates its final round; generated data stay in temporary storage.

```bash
python3 scripts/benchmark_simulator.py cli --agents 10000 --rounds 100 --seed 2026
python3 scripts/benchmark_simulator.py http --agents 500 --rounds 100 --seed 2026
python3 scripts/benchmark_simulator.py generate --agents 500 --rounds 100 --seed 2026 --output outputs/eclipse-500.toml
PYTHONPATH=src python3 -m multi_agent_election.cli visual outputs/eclipse-500.toml --port 0
```

Generate requires a new output path. Browser measurement: open printed URL,
select 5x, play past round 100, pause, then time ten individually stepped rounds.
Elapsed time includes browser automation/control overhead; 5x caps playback at
one step per 200 ms plus processing. Rendering was enabled for all 5,470 links.

## Observations

| Path | Result | Scope |
| --- | --- | --- |
| CLI summary, 10k x 100 | 36.912 s; 27,092 agent-rounds/s; 111,932 KiB peak child RSS | Includes input, initialization, metrics and JSON serialization; no retained frames or browser |
| Local HTTP, 500 x 100 | mean 19.25 ms, p95 23.79 ms, max 27.39 ms; 97,132 KiB peak process RSS | Loopback client + server, JSON, engine, metrics, retained full history; excludes browser |
| Browser, 500 x 124 | 34.213 s (~3.62 rounds/s); 5x playback | Actual browser rendering + pacing + automation; final pause observed at round 124 |
| Browser, ten manual steps | mean 321.4 ms, max 433 ms | Click-to-visible-round including automation overhead; sample too small for a reliable tail estimate |

Browser RSS was **not measured**. The HTTP RSS is a separate process that also
contains its test client; it is not browser memory or total system memory.
Peak RSS is Linux `ru_maxrss`, not allocation per round. No expensive policies,
messages, GIF exports, simultaneous clients or larger densities were measured.

## Recheck: capabilities and trusted sensors

Core SHA-256: `7fa721f42b5e94a45bc9f115b5d86729ffcc51876f95f305db65ab5f8d446679`.
Same hardware, seed and graph; one run each. Simple CLI, 10k x 100: 36.801 s,
115,500 KiB peak child RSS. Local HTTP, 500 x 100: sensors off mean/p95
19.42/23.88 ms, 97,584 KiB peak; sensors on mean/p95 33.40/43.27 ms,
163,580 KiB peak, 5,470 trusted readings in final round. Add `--sensors` to
the HTTP command above; all agents use `sensed_plurality` and public sensors.
Both HTTP figures include client/server/retained history, not browser. Earlier
browser figures use the original core; browser RSS and sensor-enabled browser
performance remain unmeasured.

## Recheck: 6 November browser and pipeline

2026-11-06; same machine, 500 agents, 100 HTTP rounds, seed 2026, one run each.
Measured before the subsequent browser checkpoint revision guard; rebenchmark
the changed pipeline before Stage 01 completion.
Core SHA-256: `7a9d50bbee51cafbec45ea32142559836db92408f2cb5ff029b3d29c915b5947`;
pipeline SHA-256: `069fbf7b5a30649df4b79e9937d978ea9be56993f5dcf0ceff10ca4932b45cc3`.

| Path | Result | Scope |
| --- | --- | --- |
| HTTP, sensors off | mean 19.33 ms; p95 24.87 ms; max 28.97 ms; 97,000 KiB | Client + server + retained history; 100 rounds |
| HTTP, sensors on | mean 32.61 ms; p95 39.98 ms; max 43.65 ms; 160,904 KiB | Same; 5,470 readings in final round |
| Browser, sensors off | 155 rounds / 43.285 s, ~3.58 rounds/s at 5×; 5,470 links rendered | Includes pacing and browser-control overhead |
| Browser, ten paused steps | mean 307.3 ms; max 349 ms | Rounds 156–165; click to visible round, includes automation overhead |

HTTP p95/RSS and browser step maximum fall below the provisional budgets below;
these are single runs, not proof of a stable performance bound. Browser RSS,
sensor-enabled browser rendering, costly policies and dense graphs remain unmeasured.

## Provisional regression budgets

For this workload and comparable hardware only: CLI <= 75 s and <= 225 MiB;
HTTP p95 <= 50 ms and process peak <= 200 MiB; browser manual-step maximum
<= 900 ms. These ~2x single-run guardrails are **proposals**, not validated
service levels. Repeat independent runs under controlled load, measure browser
memory and denser/expensive policies, then set defensible budgets before Stage 01
completion. Do not extrapolate to other policies, machines, or populations.

## Combined-mechanism measurements — 8 November 2026

Linux x86-64, Python 3.14.4, Intel i7-12700H, 20 logical CPUs. Sequential isolated
workers; one repetition each; seed 2026. Timing includes other uncontrolled
machine activity; these are workload samples, not service guarantees.

| Workload | Result | Time | Linux peak RSS |
| --- | --- | --- | --- |
| Combined CLI, 1,000 × 10 | Completed | 0.757 s total | 44,108 KiB child |
| Combined CLI, 10,000 × 100, before numeric repair | Failed: movement rounding limit | 64.299 s worker lifetime | Unavailable on failure |
| Same 10,000 × 100 after repair | Completed | 90.768 s CLI; ~11,017 agent-rounds/s | 217,372 KiB child |
| Combined HTTP, 500 × 100 after repair | Completed | Mean 76.81 ms / p95 104.12 ms / max 115.93 ms per step | 263,932 KiB process |

CLI uses summary recording; HTTP retains all frames and includes loopback,
engine, metrics and JSON encoding/decoding. HTTP mean response size: 3,355,812
bytes (~3.20 MiB). Browser rendering, browser memory and interactive usability
are unmeasured; the large payload/history cost deserves optimization before
claiming a responsive visual workload.

Generator: two nominees, `k=2`, near-Alice added ideals, directed star links,
moving sparse proximity, ~10% added voters sense public ballots. Initial mean
public out-degree: 12.793 at 10k; 11.904 at 500. One fixed coalition, leader and
alignment target; adversarial population does not scale with electorate size.
This differs from Stage 01's proposed three-party/full-ballot workload.

10k realized activity: 10,569,302 proximity arc additions/removals; 1,290,334
trusted observations; 100 sight events; 99 interceptions; 100 false reports;
100 campaign purchases; signal spend 100; ideal-shift spend ~0.5; leader spend
~0.1. Zero ballot switches/alerts in this lopsided electorate: execution evidence,
not evidence that interventions are effective or that convergence is guaranteed.

Raw measurements retain generator/template/scenario hashes, manifests, per-round
metrics and the original failure: `combined-*-fixed.json`,
`combined-cli-10000x100.json` in the artifact directory.


Combined records: `outputs/code-audit-2026-11-08/`. These source-stamped samples
are not current-source benchmarks. Browser rendering and memory remain unmeasured
for the combined workload. Current benchmark scripts: `scripts/benchmark_simulator.py`
and `scripts/benchmark_combined.py`; inspect `--help`, use N>=100 and new output paths.
