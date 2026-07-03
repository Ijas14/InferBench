# inferbench — Metric Definitions

**Status:** Frozen. Every metric has a precise definition. No ambiguity.

---

## Why this document exists

A benchmark is only as good as its metric definitions. If "throughput" means "tokens generated" to one person and "tokens including prompt" to another, comparisons are meaningless. This document defines every metric inferbench reports, with the exact formula. If the code computes something different from this document, the code is wrong.

---

## 1. Performance metrics

### 1.1 `throughput_aggregate`

**Definition:** Total output tokens generated across all requests in a cell, divided by the wall-clock time from first request send to last request complete.

**Formula:**
```
throughput_aggregate = sum(output_tokens[i] for i in requests) / (last_complete_time - first_send_time)
```

**Units:** tokens/second

**Notes:**
- Output tokens only. Prompt tokens are NOT included. This is generation throughput, not prefill throughput.
- Wall-clock time, not CPU time. The denominator is real elapsed seconds.
- If any request errored, its output_tokens = 0 but it still counts in the time span.

### 1.2 `throughput_per_request_p50`, `throughput_per_request_p95`

**Definition:** Per-request throughput, reported as percentiles across all requests in the cell.

**Per-request throughput formula:**
```
per_request_throughput[i] = output_tokens[i] / (complete_time[i] - send_time[i])
```

**Units:** tokens/second

**Notes:**
- This is the throughput experienced by a single user, not the aggregate.
- P50 is the median. P95 means 95% of requests achieved at least this throughput.
- Errored requests are excluded from this calculation (they have no meaningful throughput).

### 1.3 `latency_ttft_p50`, `latency_ttft_p95`, `latency_ttft_p99`

**Definition:** Time to first token, reported as percentiles.

**Formula:**
```
ttft[i] = first_token_time[i] - send_time[i]
```

**Units:** milliseconds

**Notes:**
- `first_token_time` is when the first token of the response was received.
- For streaming responses, this is the timestamp of the first chunk.
- For non-streaming, this equals `complete_time` (TTFT is not meaningful for non-streaming; report it anyway).
- P99 is included because tail latency is where serving systems often fail.

### 1.4 `latency_inter_token_p50`, `latency_inter_token_p95`, `latency_inter_token_p99`

**Definition:** Inter-token latency during generation, reported as percentiles.

**Formula per request:**
```
inter_token_latencies[i] = [token_time[i][j] - token_time[i][j-1] for j in 1..n]
```
Then pool all inter-token latencies across all requests and compute percentiles.

**Units:** milliseconds

**Notes:**
- This is the latency the user experiences during generation. It's the most user-perceivable metric.
- Only computed for streaming responses. Non-streaming responses have N/A.
- The first token's latency is TTFT, not inter-token. Exclude it.

### 1.5 `memory_peak_kv`

**Definition:** Peak KV cache memory usage during the cell, in bytes.

**Source (in priority order):**
1. Server metrics endpoint (if available) — most accurate
2. Estimated from model architecture + active context lengths — fallback

**Estimation formula (fallback):**
```
kv_bytes = 2 * num_layers * num_kv_heads * head_dim * 2 * total_active_tokens * bytes_per_element
```
Where:
- `2` (first) = K and V
- `2` (second) = bytes per BF16 element (or 1 for FP8, 0.5 for INT4)
- `total_active_tokens` = sum of (prompt + generated) tokens across concurrent requests

**Units:** bytes

**Notes:**
- The estimation formula is approximate. It assumes uniform precision. If the server uses mixed precision, the estimate is wrong. Prefer the metrics endpoint.
- Report both the source and the value. `memory_peak_kv_source: "metrics" | "estimated"`

### 1.6 `memory_peak_total`

**Definition:** Peak total GPU memory usage during the cell, in bytes.

**Source:**
- NVIDIA: `nvidia-smi --query-gpu=memory.used --format=csv`
- AMD: `rocm-smi --showmeminfo vram`
- Polled at 100ms intervals during the cell. Peak value reported.

**Units:** bytes

---

## 2. Quality metrics

Quality is measured separately from performance, on a fixed eval set. The eval set is the same for every run, so quality is comparable across systems and configurations.

### 2.1 `quality_retention`

**Definition:** Perplexity of the server's output on a fixed eval set, relative to the BF16 baseline perplexity.

**Formula:**
```
quality_retention = baseline_perplexity / measured_perplexity
```

**Eval set:** 1000 samples from WikiText-103 test split, each truncated to the cell's context band length.

**Procedure:**
1. Send each eval sample to the server as a prompt with `max_tokens=1`.
2. Record the logprob the server assigns to the actual next token.
3. Compute perplexity: `exp(-sum(logprobs) / num_tokens)`.
4. Compute `quality_retention` relative to the baseline (run once, cached).

**Units:** ratio (1.0 = identical to baseline, <1.0 = worse)

**Notes:**
- This requires the server to return logprobs. If the server doesn't support logprobs, this metric is N/A.
- The baseline is BF16 on the same model. Run once, store the number, reuse.
- A quality_retention of 0.95 means the server's output is 5% worse than BF16 in perplexity terms.

### 2.2 `needle_accuracy`

**Definition:** Accuracy on the Needle-in-a-Haystack task, at four depths.

**Procedure:**
1. Insert a random "needle" sentence into a haystack of filler text at 25%, 50%, 75%, or 100% depth.
2. Ask the server to retrieve the needle.
3. Score: did the response contain the needle information? (Exact match on key fact.)

**Eval set:** 200 samples per depth × 4 depths = 800 samples. Fixed seed.

**Formula:**
```
needle_accuracy = correct_retrievals / total_queries
```

**Units:** ratio (0.0 to 1.0)

**Notes:**
- Depth 100% means the needle is at the very end of the context. This is the easiest.
- Depth 25% means the needle is near the beginning. This is the hardest for many systems.
- Report per-depth AND aggregate.

### 2.3 `longbench_score`

**Definition:** Accuracy on a 5-task subset of LongBench.

**Tasks:**
1. NarrativeQA (long-document QA)
2. QMSum (meeting summarization)
3. PassageRetrieval (passage retrieval)
4. TriviaQA (trivia QA with long context)
5. LSHT (long-document classification)

**Eval set:** 100 samples per task × 5 tasks = 500 samples. Fixed.

**Scoring:** Per LongBench's official scoring (F1 for QA, ROUGE for summarization, accuracy for retrieval/classification).

**Formula:**
```
longbench_score = mean(task_scores)
```

**Units:** ratio (0.0 to 1.0)

---

## 3. Derived metrics

These are computed from the performance and quality metrics. They are the signature of inferbench.

### 3.1 `degradation_curve`

**Definition:** Throughput as a function of concurrency, for a fixed (workload × context band).

**Computation:**
1. Run the workload at each concurrency in `[1, 8, 32, 128]`.
2. Record `throughput_aggregate` for each.
3. The curve is the sequence of (concurrency, throughput) points.

**Output format:**
```json
{
  "workload": "concurrent_uniform",
  "context_band": "long",
  "curve": [
    {"concurrency": 1, "throughput": 45.2},
    {"concurrency": 8, "throughput": 312.8},
    {"concurrency": 32, "throughput": 890.1},
    {"concurrency": 128, "throughput": 412.3, "note": "OOM at 96, recovered"}
  ]
}
```

**Notes:**
- The curve is the most valuable single output. It shows where the system scales linearly, where it plateaus, and where it breaks.
- Include annotations for OOM events, error spikes, and quality drops.

### 3.2 `oom_threshold`

**Definition:** The maximum concurrency the system sustained without OOM or quality collapse, for a fixed (workload × context band).

**Failure conditions (any one triggers):**
- Server returns HTTP 503/507 (out of memory)
- `error_count / total_requests > 0.1` (more than 10% errors)
- `needle_accuracy < 0.5` (quality collapse)
- `latency_ttft_p99 > 10 * baseline_ttft_p99` (latency spike)

**Units:** integer (concurrency count)

**Notes:**
- If the system survives all concurrencies in the ladder, `oom_threshold` = max concurrency tested.
- This is the single number most people want: "how many concurrent users can I serve?"

### 3.3 `recovery_time`

**Definition:** Time for the server to return to healthy operation after a STRESS run that triggered errors or OOM.

**Procedure:**
1. After the STRESS concurrency cell completes, immediately send LIGHT (1 concurrent) requests.
2. Measure time until 10 consecutive requests succeed with `latency_ttft < 2 * baseline_ttft_p50`.
3. That time is `recovery_time`.

**Units:** seconds

**Notes:**
- If the server never recovers (10 consecutive successes never achieved within 300 seconds), `recovery_time` = 300 and `recovered` = false.
- This metric separates systems that crash from systems that degrade and recover. Crash = bad. Degrade-and-recover = acceptable.

---

## 4. Error metrics

### 4.1 `oom`

**Definition:** Boolean. Did the server return an out-of-memory error during this cell?

**Detection:**
- HTTP 503 with "memory" in the error message
- HTTP 507
- Server crash (health check fails)
- Process-level OOM killer invocation (check dmesg if accessible)

### 4.2 `error_count`

**Definition:** Number of requests that returned an error response (HTTP non-200, timeout, or malformed response).

**Units:** integer

### 4.3 `error_rate`

**Definition:** `error_count / total_requests`

**Units:** ratio

---

## 5. Fingerprint metrics

Not performance metrics, but mandatory metadata. Every result includes these.

### 5.1 Hardware fingerprint

```yaml
hardware:
  gpu: "AMD Instinct MI300X"       # exact model string
  vram_gb: 192                      # total VRAM in GB
  driver: "rocm-6.1"                # driver version
  cpu: "AMD EPYC 9654"              # CPU model
  ram_gb: 1536                      # system RAM in GB
  num_gpus: 1                       # GPU count
```

### 5.2 Software fingerprint

```yaml
software:
  os: "Ubuntu 22.04"
  kernel: "5.15.0-91-generic"
  python: "3.12.3"
  torch: "2.4.0+rocm61"
  server: "sglang"                  # sglang | vllm | tensorrt-llm | tgi | lmdeploy
  server_version: "0.3.5"
  model: "Qwen/Qwen3-235B-A22B-Thinking-2507"
  quantization: "none"              # none | fp8 | int4 | nf4 | gptq | awq
  kv_precision: "bf16"              # bf16 | fp8 | int4
  max_model_len: 262144
  gpu_memory_utilization: 0.9
```

---

## 6. Reporting rules

### 6.1 What gets reported

Every (workload × context band × concurrency × seed) cell produces a `Result` with all metrics. A full run produces ~240 Results (5 workloads × 4 bands × 4 concurrencies × 3 seeds).

### 6.2 Aggregation across seeds

For metrics reported as percentiles (P50, P95, P99), aggregate across seeds by taking the median. For metrics reported as scalars (throughput_aggregate, memory_peak), aggregate by taking the mean.

### 6.3 What gets exported

- `results.json` — all Results, full fidelity
- `results.md` — human-readable summary, one table per workload
- `degradation_curves.png` — the cliff finder visualization
- `fingerprint.yaml` — the hardware + software fingerprint
- `leaderboard_entry.md` — a single Markdown file suitable for PR submission to the leaderboard

### 6.4 What does NOT get reported

- Individual request prompts (privacy, size)
- Individual request responses (privacy, size)
- Server logs (too large, server-specific)
- Raw timing arrays (only aggregates, to keep result size manageable)

---

## 7. The "no ambiguity" checklist

Before shipping v1, verify every metric has:

- [ ] A precise formula (not "we measure throughput")
- [ ] Defined units
- [ ] Defined aggregation method (across requests, across seeds)
- [ ] Defined handling of errors (errored requests included or excluded?)
- [ ] Defined handling of edge cases (empty responses, timeouts, non-streaming)
- [ ] A test that verifies the computation matches the definition

If any metric lacks one of these, it's not ready. Fix the definition before shipping.

---

## 8. The signature

Three metrics are the signature of inferbench:

1. **`degradation_curve`** — the curve, not the peak
2. **`oom_threshold`** — where it breaks
3. **`recovery_time`** — how it recovers

Every other benchmark reports peak throughput. inferbench reports the cliff. That's the difference.
