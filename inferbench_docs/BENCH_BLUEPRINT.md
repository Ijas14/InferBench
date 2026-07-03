# inferbench — Architecture Blueprint

**For:** the builder (you) and future contributors
**Status:** Phase 0 design. Build against this spec.

---

## 1. What you are building

`inferbench` is a benchmark for LLM serving systems that measures **behavior under realistic long-context concurrent load**, with explicit focus on graceful degradation. It is not a throughput benchmark. It is not a quality benchmark. It is the benchmark that tells you **when a serving system breaks and what happens when it does.**

The benchmark defines:
- Fixed workload classes (realistic request patterns)
- Fixed context and concurrency bands (comparable across runs)
- Fixed metric definitions (no ambiguity in what's measured)
- Fixed hardware reporting (results without fingerprints are invalid)
- One command to reproduce (no tuning, no flags)

The benchmark does NOT define:
- Which server is "best" (it reports, it doesn't rank subjectively)
- Optimal configurations (it tests what you configure, doesn't tune)
- Cost efficiency (v2)
- Energy use (v2)

---

## 2. The architectural principles

Same discipline as ASH-KV. These are non-negotiable.

### Principle 0 — Configuration is interpreted, runs are compiled

A benchmark config (YAML) is parsed once at startup. The run is then a static schedule — no config reads during measurement. This guarantees reproducibility: the same config + the same seed = the same run.

### Principle 1 — The measurement loop never blocks on config

The hot loop (sending requests, recording timestamps) reads no config. It reads closures compiled at startup. If a request-sending function reads a YAML value, you've broken reproducibility.

### Principle 2 — One command, one result

```bash
inferbench run --config configs/qwen36_mi300x.yaml
```

No `--concurrency 16 --context 32k --workload shared_prefix --enable-fp8`. The config file specifies everything. CLI flags are for path overrides only (`--output`, `--dry-run`).

### Principle 3 — Hardware fingerprints are mandatory

Every result file includes a hardware + software fingerprint block. If the fingerprint is missing or incomplete, the result is rejected. No exceptions. This is what makes results comparable across the community.

### Principle 4 — Workloads are deterministic given a seed

Same seed → same request sequence → same timing pattern (within OS scheduler jitter). Random workloads use a seeded PRNG. No `time.time()` as a seed.

### Principle 5 — The server is a black box

inferbench talks to the server via its HTTP API (OpenAI-compatible `/v1/completions` or `/v1/chat/completions`). It does not import the server's code. It does not read the server's internal state (except via optional metrics scraping for memory reporting). This means inferbench works with any compliant server: SGLang, vLLM, TensorRT-LLM, TGI, lmdeploy.

### Principle 6 — The cliff finder is the signature feature

The most valuable output is not "throughput was X tokens/sec." It's "throughput was X at concurrency 8, Y at 32, Z at 64, then the system OOMed at 72." That cliff is the data. The cliff finder automates this discovery.

---

## 3. The system architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CONFIG (YAML)                         │
│  target, workloads, bands, model, hardware fingerprint   │
└──────────────────────┬──────────────────────────────────┘
                       │ (parsed once)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  RUN COMPILER (cold)                     │
│  validates config, builds workload schedule,             │
│  compiles measurement closures                          │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  WORKLOAD   │ │  ADAPTER    │ │  METRICS    │
│  ENGINE     │ │  (HTTP)     │ │  COLLECTOR  │
│             │ │             │ │             │
│ generates   │ │ sends       │ │ records     │
│ requests    │ │ requests    │ │ timestamps  │
│ per schedule│ │ collects    │ │ + memory    │
│             │ │ responses   │ │ + quality   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  RESULT ASSEMBLER                       │
│  aggregates metrics, computes derived metrics,          │
│  generates fingerprint, writes JSON + Markdown          │
└──────────────────────┬──────────────────────────────────┘
                       ▼
              ┌─────────────────┐
              │   results.json  │
              │   results.md    │
              │   leaderboard/  │
              └─────────────────┘
```

---

## 4. Repository layout

```
inferbench/
├── inferbench/                    # the package
│   ├── __init__.py
│   ├── cli.py                     # entry point: `inferbench run`
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py              # config dataclass, validation
│   │   └── defaults.py            # default bands, workload defs
│   │
│   ├── compiler/
│   │   ├── __init__.py
│   │   ├── run_compiler.py        # config → RunSchedule
│   │   └── workload_compiler.py   # config → WorkloadSchedule
│   │
│   ├── workloads/
│   │   ├── __init__.py
│   │   ├── base.py                # Workload protocol
│   │   ├── single_long.py
│   │   ├── concurrent_uniform.py
│   │   ├── shared_prefix.py
│   │   ├── agent_session.py
│   │   └── mixed.py
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # ServerAdapter protocol
│   │   ├── openai_api.py          # OpenAI-compatible (works with SGLang, vLLM, TGI)
│   │   └── metrics_scraper.py     # optional server-specific memory scraping
│   │
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── collector.py           # timestamp + memory recording
│   │   ├── performance.py         # throughput, latency, memory computations
│   │   ├── quality.py             # perplexity, NIAH, longbench
│   │   └── derived.py             # degradation curve, cliff finder, recovery
│   │
│   ├── results/
│   │   ├── __init__.py
│   │   ├── assembler.py           # aggregate metrics → result object
│   │   ├── fingerprint.py         # hardware + software fingerprint
│   │   ├── json_exporter.py
│   │   └── markdown_exporter.py
│   │
│   └── cliff/
│       ├── __init__.py
│       └── finder.py              # the signature feature: automated cliff discovery
│
├── configs/
│   ├── qwen36_mi300x.yaml         # example configs
│   ├── qwen25_72b_h100.yaml
│   └── llama8b_a100.yaml
│
├── workloads/                     # workload definition files (data, not code)
│   ├── prompts/
│   │   ├── single_long.jsonl
│   │   ├── shared_prefix_system.txt
│   │   └── agent_session_trace.jsonl
│   └── eval_sets/
│       ├── niah.jsonl             # needle in haystack eval set
│       ├── longbench_subset.jsonl
│       └── perplexity_wikitext.jsonl
│
├── leaderboard/                   # published results
│   └── README.md                  # community-submitted results
│
├── tests/
│   ├── test_config.py
│   ├── test_workloads.py
│   ├── test_metrics.py
│   ├── test_cliff_finder.py
│   └── test_reproducibility.py    # same seed → same schedule
│
├── docs/
│   ├── BENCH_SCOPE.md
│   ├── BENCH_BLUEPRINT.md         # this file
│   ├── BENCH_METRICS.md
│   └── BENCH_WORKLOADS.md
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 5. Core interfaces

### 5.1 Workload protocol

```python
class Workload(Protocol):
    """Generates a deterministic sequence of requests given a seed."""

    def schedule(self, seed: int) -> list[Request]:
        """Return a list of Request objects to send.

        The schedule MUST be deterministic given the seed. Same seed
        → same schedule, always. No time.time(), no os.urandom().
        """
        ...

@dataclass(frozen=True, slots=True)
class Request:
    """A single benchmark request."""
    request_id: int
    prompt: str
    max_tokens: int          # generation length
    send_at_offset: float    # seconds after run start (for pacing)
    metadata: dict           # workload-specific (prefix_id, session_id, etc.)
```

### 5.2 ServerAdapter protocol

```python
class ServerAdapter(Protocol):
    """Talks to the serving system. Black-box interface."""

    def send(self, request: Request) -> Response:
        """Send a request, block until complete, return response.

        Records timestamps: send_time, first_token_time, complete_time.
        Never raises. On error, returns Response with error field set.
        """
        ...

    def health(self) -> bool:
        """Is the server responding?"""
        ...

    def metrics(self) -> dict | None:
        """Optional: scrape server metrics (memory, KV cache size).

        Returns None if server doesn't expose metrics. The metrics
        collector falls back to estimation in that case.
        """
        ...
```

### 5.3 RunSchedule

```python
@dataclass(frozen=True, slots=True)
class RunSchedule:
    """The compiled output of the run compiler. Static after construction."""
    config: BenchConfig
    workloads: list[tuple[str, Workload]]   # (name, workload) pairs
    bands: list[ContextBand]
    concurrencies: list[int]
    seeds: list[int]                        # one per repeat
```

### 5.4 Result

```python
@dataclass(frozen=True, slots=True)
class Result:
    """The output of a single (workload × band × concurrency × seed) cell."""
    workload: str
    context_band: str
    concurrency: int
    seed: int

    # Performance
    throughput_aggregate: float
    throughput_per_request_p50: float
    throughput_per_request_p95: float
    latency_ttft_p50: float
    latency_ttft_p95: float
    latency_ttft_p99: float
    latency_inter_token_p50: float
    latency_inter_token_p95: float
    latency_inter_token_p99: float
    memory_peak_kv: int
    memory_peak_total: int

    # Quality (may be None if not measured for this cell)
    quality_retention: float | None
    needle_accuracy: float | None
    longbench_score: float | None

    # Derived
    oom: bool
    error_count: int

    # Fingerprint
    hardware: dict
    software: dict
```

---

## 6. The cliff finder (signature feature)

The cliff finder is what makes inferbench different. It automatically discovers where the system breaks.

```python
def find_cliff(
    adapter: ServerAdapter,
    workload: Workload,
    context_band: ContextBand,
    concurrency_ladder: list[int],  # e.g., [1, 4, 8, 16, 32, 64, 128]
) -> CliffReport:
    """Run the workload at increasing concurrency until the system breaks.

    "Breaks" is defined as:
    - OOM (server returns 503 or equivalent)
    - Quality collapse (needle_accuracy drops below 0.5)
    - Latency spike (P99 ttft > 10x the LIGHT baseline)
    - Error rate > 10%

    Returns the concurrency at which the cliff occurs, the failure mode,
    and the throughput/latency/quality curve up to that point.
    """
```

The cliff finder output is the most valuable single artifact inferbench produces. It's the answer to "how many users can this server handle at 128k context before it falls apart?"

---

## 7. The run loop

This is the hot path. It must be tight.

```python
def run_cell(
    schedule: RunSchedule,
    workload_name: str,
    workload: Workload,
    band: ContextBand,
    concurrency: int,
    seed: int,
    adapter: ServerAdapter,
    collector: MetricsCollector,
) -> Result:
    """Run one (workload × band × concurrency × seed) cell."""

    # 1. Generate the request schedule (deterministic)
    requests = workload.schedule(seed=seed, band=band, concurrency=concurrency)

    # 2. Open the metrics collector
    collector.start()

    # 3. Send requests with pacing, respecting concurrency limit
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = []
        for req in requests:
            # Pace according to send_at_offset
            wait_until(req.send_at_offset)
            futures.append(pool.submit(adapter.send, req))
        responses = [f.result() for f in futures]

    # 4. Close the collector
    collector.stop()

    # 5. Compute metrics
    perf = compute_performance(responses, collector)
    quality = compute_quality(responses, workload)  # may be None

    # 6. Assemble result with fingerprint
    return Result(
        workload=workload_name,
        context_band=band.name,
        concurrency=concurrency,
        seed=seed,
        **perf,
        **quality,
        hardware=fingerprint_hardware(),
        software=fingerprint_software(schedule.config),
    )
```

The entire benchmark is this loop run across the cross product of (workloads × bands × concurrencies × seeds). For 5 workloads × 4 bands × 4 concurrencies × 3 seeds = 240 cells. At ~1 minute per cell, that's 4 hours for a full run. Acceptable.

---

## 8. Config schema

```yaml
# configs/qwen36_mi300x.yaml
target:
  endpoint: "http://localhost:30000/v1"
  model: "Qwen/Qwen3-235B-A22B-Thinking-2507"
  api_style: "openai"  # openai | anthropic | custom
  metrics_endpoint: "http://localhost:30000/metrics"  # optional, for memory scraping

model:
  context_window: 262144
  quantization: "none"  # none | fp8 | int4 | nf4
  kv_precision: "bf16"  # bf16 | fp8 | int4

hardware:
  gpu: "AMD Instinct MI300X"
  vram_gb: 192
  driver: "rocm-6.1"

workloads:
  - single_long
  - concurrent_uniform
  - shared_prefix
  - agent_session
  - mixed

bands: [short, medium, long, extreme]   # 4k, 32k, 128k, 256k
concurrencies: [1, 8, 32, 128]
seeds: [42, 1337, 9999]
repeats: 1   # number of full passes

quality:
  enabled: true
  eval_sets: [niah, longbench_subset]
  perplexity: true

output:
  dir: "results/"
  formats: [json, markdown]
```

The config is intentionally small. ~20 fields. No 50-knob tuning surface. If you can't describe your benchmark in this config, you're overcomplicating it.

---

## 9. What makes this buildable in 2–3 weeks

The scope is bounded:

- **Week 1:** Config schema, run compiler, workload base + 2 workloads (single_long, concurrent_uniform), OpenAI adapter, basic metrics (throughput, latency, memory). Run end-to-end on SGLang with Qwen.
- **Week 2:** Remaining 3 workloads, quality metrics (NIAH, longbench subset), cliff finder, hardware fingerprint, JSON + Markdown exporters.
- **Week 3:** Reproducibility tests, baseline results, README, leaderboard scaffolding, ship v0.1.

You're not building a serving system. You're building a measurement instrument. The complexity is in the metric definitions and the workload specs, not in the code. The code is straightforward: send HTTP requests, record timestamps, compute aggregates.

The hard part is getting the metric definitions right (see `BENCH_METRICS.md`). The code is just plumbing.

---

## 10. What to read next

1. **`BENCH_SCOPE.md`** — the locked decisions (read first)
2. **`BENCH_METRICS.md`** — exact metric definitions (read before writing metrics code)
3. **`BENCH_WORKLOADS.md`** — workload specifications (read before writing workload code)

Build in this order:
1. Config schema + validation
2. OpenAI adapter
3. single_long workload + basic metrics
4. Run end-to-end (this proves the loop works)
5. Add remaining workloads
6. Add quality metrics
7. Add cliff finder
8. Add fingerprinting + exporters
9. Reproducibility tests
10. Ship

---

## 11. The one-paragraph summary

`inferbench` is a benchmark that measures LLM serving behavior under concurrent long-context load, with focus on graceful degradation. It has five workload classes, four context bands, four concurrency bands, nine metrics, mandatory hardware fingerprinting, one-command reproducibility, and a signature cliff-finder feature that automatically discovers where systems break. The architecture is cold-config-compiled-to-static-run, the server is a black box accessed via HTTP, and the entire tunable surface is ~20 config fields. Build it in three weeks. Ship v0.1. Use it to validate ASH-KV. Move on.
