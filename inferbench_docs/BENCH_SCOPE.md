# inferbench — Scope (Locked Decisions)

**Status:** Frozen. Changes require a design review.
**Purpose:** One page. Every decision that prevents scope creep.

---

## The one-sentence definition

`inferbench` measures how LLM serving systems behave under realistic long-context concurrent load, with explicit focus on **graceful degradation** — what breaks, when, and how the system recovers.

---

## The six locked decisions

### 1. Context-length bands

Fixed. No custom values in v1.

```
SHORT     4k tokens
MEDIUM    32k tokens
LONG      128k tokens
EXTREME   256k tokens (or max supported, whichever is lower)
```

Every workload runs at all four bands. No "let me try 17k" — the bands exist so results are comparable across runs and across systems.

### 2. Concurrency bands

Fixed.

```
LIGHT     1 concurrent request
NORMAL    8 concurrent requests
HEAVY     32 concurrent requests
STRESS    128 concurrent requests (or OOM, whichever comes first)
```

STRESS is the band that matters most. It's where systems either degrade gracefully or crash. Most benchmarks stop at NORMAL. We go to STRESS because that's where the interesting behavior lives.

### 3. Workload classes

Five. Each is a precisely specified request pattern.

| Class | Code | Description |
|---|---|---|
| Single long | `single_long` | One request, fixed context, measure throughput/latency |
| Concurrent uniform | `concurrent_uniform` | N requests, same context length, measure scaling |
| Shared prefix | `shared_prefix` | N requests with 80% prefix overlap, measure reuse efficiency |
| Agent session | `agent_session` | Long-running session with pauses and tool-call patterns |
| Mixed | `mixed` | Realistic mix of the above (the "production" workload) |

Full specifications in `BENCH_WORKLOADS.md`.

### 4. Quality metrics

Three. Each has a precise definition.

| Metric | What it measures |
|---|---|
| `quality_retention` | Perplexity on fixed eval set, relative to BF16 baseline |
| `needle_accuracy` | Needle-in-haystack recall at 25%, 50%, 75%, 100% of context |
| `longbench_subset` | Accuracy on 5-task LongBench subset (QA, summary, extraction) |

Quality is measured **under compression**, not just at BF16. This is what makes inferbench different — we test what breaks when you enable FP8/INT4.

Full definitions in `BENCH_METRICS.md`.

### 5. Performance metrics

Six. Each reported per (workload × context band × concurrency band).

```
throughput_aggregate     tokens/sec across all requests
throughput_per_request   tokens/sec per request (P50, P95)
latency_ttft             time to first token (P50, P95, P99)
latency_inter_token      inter-token latency (P50, P95, P99)
memory_peak_kv           peak KV cache memory (bytes)
memory_peak_total        peak total GPU memory (bytes)
```

Plus three derived metrics that are the signature of inferbench:

```
degradation_curve        throughput vs concurrency (the cliff finder)
oom_threshold            max concurrency before OOM or quality collapse
recovery_time            time to return to normal after STRESS
```

### 6. Hardware reporting

Every result includes a hardware fingerprint. No fingerprint = not a valid result.

```yaml
hardware:
  gpu: "AMD Instinct MI300X"
  vram_gb: 192
  driver: "rocm-6.1"
  cpu: "AMD EPYC 9654"
  ram_gb: 1536

software:
  os: "Ubuntu 22.04"
  python: "3.12"
  torch: "2.4.0+rocm61"
  server: "sglang-0.3.5"
  model: "Qwen/Qwen3-235B-A22B-Thinking-2507"
  quantization: "none"
  kv_precision: "bf16"
```

Results without this block are rejected from the leaderboard.

---

## The one command

```bash
inferbench run --config configs/qwen36_mi300x.yaml --workload all --output results/
```

This runs every workload at every band, produces a structured report, and emits a leaderboard entry. No flags, no tuning, no "let me try this config." One command, one result.

---

## What is explicitly OUT of scope (v1)

- Multi-GPU testing (v2)
- Speculative decoding evaluation (v2)
- Training benchmarks (never — inference only)
- Custom model architectures (use whatever the server supports)
- Cost analysis (v2, cloud pricing varies too much)
- Energy efficiency (v2, needs hardware support)

If a feature isn't in this document, it's not in v1. Resist scope creep.

---

## The signature

Three things make inferbench distinct from every existing benchmark:

1. **Pressure-indexed reporting.** We don't report "max throughput." We report the curve of throughput vs concurrency, with the cliff explicitly identified. Most benchmarks report a single number. We report the cliff.

2. **Quality-under-compression.** We test what breaks when you enable FP8/INT4. Most benchmarks measure speed OR quality. We measure quality AS A FUNCTION OF compression level. This is the axis nobody else covers.

3. **Hybrid-model awareness.** We report per-layer-type breakdown. "DeltaNet layers take 40% of time but are 75% of layers." This is novel because hybrid models are new and no benchmark accounts for them yet.

These three are the signature. If a future contributor removes any of them, they've broken inferbench.

---

## Exit criteria for v1

- [ ] One command reproduces a full benchmark run
- [ ] All five workload classes implemented
- [ ] All four context bands × four concurrency bands tested
- [ ] All nine metrics reported per (workload × band × concurrency) cell
- [ ] Hardware fingerprint generated automatically
- [ ] Results export to JSON + Markdown
- [ ] Baseline results published for at least one (model, GPU) combination
- [ ] Documentation sufficient for a stranger to reproduce

When all eight are checked, v1 ships.
