# Stage 01 scale measurements

Status: preliminary, individual runs; not performance guarantees. Historical
and current-code measurements are identified below. Updated 2026-11-06.
Machine: Intel i7-12700H, x86_64 Linux 7.0.0, CPython 3.14.4.
Original measurement core SHA-256: `629c342418714bd502d75a7393c9f88856e7e1efbeadc80649aac8ca5251b259`.
Shared, non-isolated machine; some other test activity overlapped the CLI run.

## Workload and reproduction

Three parties, `k=3`, seed 2026, random fixed positions, stationary/sincere
agents, no communication/interventions, proximity radius chosen for nominal
mean degree 12. Actual directed mean degree: 11.7932 (10k), 10.94 (500).
Each run validates its final round; generated data stay in temporary storage.

```bash
python3 scripts/benchmark_simulator.py cli --agents 10000 --rounds 100 --seed 2026
python3 scripts/benchmark_simulator.py http --agents 500 --rounds 100 --seed 2026
python3 scripts/benchmark_simulator.py generate --agents 500 --rounds 100 --seed 2026 --output /tmp/eclipse-500.toml
PYTHONPATH=src python3 -m multi_agent_election.cli visual /tmp/eclipse-500.toml --port 0
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

## Recheck: current browser and pipeline

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
