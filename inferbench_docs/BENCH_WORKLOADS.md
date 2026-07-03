# inferbench — Workload Specifications

**Status:** Frozen. Every workload has a precise spec. No "use your judgment."

---

## Why this document exists

A benchmark's value comes from workload reproducibility. If "concurrent uniform" means "send 32 requests at once" to one person and "send 32 requests over 5 seconds" to another, the numbers aren't comparable. This document specifies every workload with enough precision that two independent implementations produce the same request schedule given the same seed.

---

## Common definitions

### Context bands

```
SHORT     4,096 tokens
MEDIUM    32,768 tokens
LONG      131,072 tokens
EXTREME   262,144 tokens (or model max, whichever is lower)
```

### Generation length

Every request generates exactly **256 tokens**. Not "up to 256" — exactly 256. This keeps the generation phase consistent across requests so inter-token latency is comparable.

### Prompt composition

Prompts are built from a fixed corpus (`workloads/prompts/`). The corpus is committed to the repo. Same seed → same prompts.

```
workloads/prompts/
├── filler.jsonl              # neutral filler text (Wikipedia passages)
├── shared_prefix_system.txt  # system prompt for shared_prefix workload
├── agent_session_trace.jsonl # agent session patterns
├── niah_needles.jsonl        # needle sentences for NIAH
└── longbench_subset.jsonl    # LongBench eval samples
```

### Tokenization

All token counts are measured in the **target model's tokenizer**. inferbench loads the tokenizer from the model ID and counts tokens precisely. No "approximately 4k characters = 1k tokens." Token-precise.

### Pacing

Every request has a `send_at_offset` (seconds from run start). The scheduler waits until that offset before sending. This decouples request generation from request timing — you can have 128 requests scheduled to send at offset 0.0 (all at once) or staggered.

---

## Workload 1: `single_long`

**Purpose:** Measure single-request behavior at each context band. The baseline.

**Schedule:**
- 1 request at a time
- 5 repeats per context band (for variance estimation)
- No concurrency (concurrency = 1 always, even in HEAVY/STRESS bands)

**Request construction:**
```
prompt = filler_corpus.sample(seed=seed, target_tokens=band_tokens)
max_tokens = 256
send_at_offset = repeat_index * 30.0   # 30 seconds between repeats
```

**What it measures:**
- TTFT at each context length (prefill cost)
- Inter-token latency at each context length (decode cost)
- Peak KV memory for a single request at each context length
- Throughput per request (the upper bound — no contention)

**Why it exists:** Establishes the single-request baseline. Every other workload's numbers are compared against this. If concurrent_uniform at concurrency=1 doesn't match single_long, something is wrong.

**Output cells:** 4 (one per context band). All at concurrency=1.

---

## Workload 2: `concurrent_uniform`

**Purpose:** Measure scaling under uniform concurrent load. The workhorse.

**Schedule:**
- N requests (N = concurrency band: 1, 8, 32, 128)
- All requests have the same context length (the band's length)
- All requests sent at offset 0.0 (simultaneous arrival)
- 3 repeats per (band × concurrency) cell

**Request construction:**
```
for i in range(N):
    prompt[i] = filler_corpus.sample(seed=seed+i, target_tokens=band_tokens)
    max_tokens[i] = 256
    send_at_offset[i] = 0.0   # all at once
```

**What it measures:**
- Aggregate throughput vs concurrency (the degradation curve)
- Per-request throughput vs concurrency
- TTFT distribution under load (P50, P95, P99)
- Peak KV memory under load
- OOM threshold (where does it break?)

**Why it exists:** This is the core scalability test. The degradation curve from this workload is the primary output of inferbench. Most existing benchmarks report peak throughput from this kind of test; we report the full curve including the cliff.

**Output cells:** 4 bands × 4 concurrencies = 16 cells.

---

## Workload 3: `shared_prefix`

**Purpose:** Measure prefix caching efficiency. Does the server actually reuse KV?

**Schedule:**
- N requests (N = concurrency band)
- All requests share a common prefix (80% of context length)
- Each request has a unique suffix (20% of context length)
- All sent at offset 0.0

**Request construction:**
```
prefix = shared_prefix_system + filler_corpus.sample(seed=fixed, target_tokens=0.8 * band_tokens)
for i in range(N):
    suffix[i] = filler_corpus.sample(seed=seed+i, target_tokens=0.2 * band_tokens)
    prompt[i] = prefix + suffix[i]
    max_tokens[i] = 256
    send_at_offset[i] = 0.0
```

**What it measures:**
- Prefix reuse efficiency: does TTFT drop for requests 2..N vs request 1?
- KV memory savings: is peak KV ~1x prefix + Nx suffix, or Nx full context?
- Throughput vs concurrent_uniform (should be higher if prefix caching works)

**Derived metric:**
```
prefix_efficiency = ttft_request_1 / mean(ttft_requests_2_to_N)
```
- `prefix_efficiency > 1.0` = caching works (later requests are faster)
- `prefix_efficiency ≈ 1.0` = no caching
- `prefix_efficiency < 1.0` = something is wrong

**Why it exists:** Every server claims prefix caching. This workload proves whether it actually works and how much it helps. The derived `prefix_efficiency` metric is the proof.

**Output cells:** 4 bands × 4 concurrencies = 16 cells.

---

## Workload 4: `agent_session`

**Purpose:** Measure behavior under agent-like workloads. Long sessions with pauses.

**Schedule:**
- 1 session = 10 turns
- Each turn: prompt (growing context) → generate 256 tokens → pause → next turn
- Pause durations: [1.0, 5.0, 10.0, 2.0, 8.0, 3.0, 15.0, 1.0, 4.0] seconds (fixed pattern)
- Multiple sessions run concurrently (N = concurrency band)

**Request construction (per session):**
```
session_context = system_prompt
for turn in range(10):
    user_message = filler_corpus.sample(seed=seed+turn, target_tokens=500)
    session_context += user_message
    prompt[turn] = session_context
    max_tokens[turn] = 256
    send_at_offset[turn] = previous_complete_time + pause_pattern[turn]
    session_context += generated_response  # add to context for next turn
```

**What it measures:**
- KV persistence: does the server reuse KV across turns, or recompute?
- TTFT growth: does turn 10 have higher TTFT than turn 1? (It shouldn't, if KV is persisted)
- Memory growth: how does KV grow over a 10-turn session?
- Concurrent session handling: do N sessions interfere?

**Derived metrics:**
```
kv_persistence_ratio = ttft_turn_1 / mean(ttft_turns_2_to_10)
```
- `> 1.0` = KV is persisted (later turns faster, no recompute)
- `≈ 1.0` = no persistence (full recompute each turn)

```
ttft_growth = ttft_turn_10 / ttft_turn_1
```
- `≈ 1.0` = no growth (good)
- `> 1.0` = linear growth (KV not being managed)
- `>> 1.0` = exponential growth (broken)

**Why it exists:** Agent workloads are the future and no benchmark tests them. This is a first-mover advantage. The `kv_persistence_ratio` metric is novel — nobody else measures it.

**Output cells:** 4 bands × 4 concurrencies = 16 cells. (Each cell = N concurrent 10-turn sessions.)

---

## Workload 5: `mixed`

**Purpose:** The "production" workload. Realistic mix of request patterns.

**Schedule:**
- N total requests (N = concurrency band × 10)
- Mix: 40% short prompts (4k), 30% medium (32k), 20% long (128k), 10% extreme (256k)
- Arrivals: Poisson process with rate = N / 60 (N requests per minute)
- Each request generates 256 tokens

**Request construction:**
```
for i in range(N):
    r = seeded_random(seed, i)
    if r < 0.4:
        band = SHORT
    elif r < 0.7:
        band = MEDIUM
    elif r < 0.9:
        band = LONG
    else:
        band = EXTREME

    prompt[i] = filler_corpus.sample(seed=seed+i, target_tokens=band_tokens)
    max_tokens[i] = 256
    # Poisson arrivals
    inter_arrival = exponential_random(seed=seed+i, rate=N/60.0)
    send_at_offset[i] = previous_offset + inter_arrival
```

**What it measures:**
- Real-world throughput under mixed load
- How short requests are affected by long requests (head-of-line blocking)
- Tail latency in realistic conditions
- Whether the server's scheduler is fair or starves some requests

**Derived metrics:**
```
short_request_ttft_p99 = P99 TTFT of requests where context_band == SHORT
long_request_ttft_p99 = P99 TTFT of requests where context_band == EXTREME
fairness_ratio = short_request_ttft_p99 / long_request_ttft_p99
```
- `≈ 1.0` = fair scheduling
- `> 1.0` = short requests are starved (bad)
- `< 1.0` = long requests are starved (also bad, different problem)

**Why it exists:** The other workloads isolate variables. This one tests whether the system handles the messiness of real traffic. A system that's great at concurrent_uniform but terrible at mixed has a scheduler problem, not a memory problem.

**Output cells:** 4 concurrency bands (context band is mixed within each) = 4 cells.

---

## Workload implementation contract

Every workload implementation must:

1. **Be deterministic given a seed.** Same seed → same request schedule. No exceptions.
2. **Use the fixed corpus.** No random internet text. No generated text. The corpus is committed.
3. **Respect the context band.** Prompts must be within 1% of the band's token count.
4. **Generate exactly 256 tokens.** Not 255, not 257.
5. **Implement the `Workload` protocol** from the blueprint.
6. **Be testable in isolation.** `workload.schedule(seed=42)` returns a list of `Request` objects. No network calls during scheduling.

### The `Workload` protocol (repeated from blueprint)

```python
class Workload(Protocol):
    def schedule(
        self,
        seed: int,
        band: ContextBand,
        concurrency: int,
    ) -> list[Request]:
        """Generate the request schedule for one cell.

        Deterministic. Same seed → same schedule.
        """
        ...
```

---

## Why five workloads, not fifty

Each workload isolates one variable:

| Workload | Variable isolated |
|---|---|
| `single_long` | Context length (no contention) |
| `concurrent_uniform` | Concurrency (uniform load) |
| `shared_prefix` | Prefix reuse |
| `agent_session` | Session persistence |
| `mixed` | Realistic mix (no isolation — the reality check) |

Adding more workloads doesn't add more signal; it adds more noise. If a future contributor wants to add "code_completion" or "rag_retrieval" workloads, the answer is no — those are application-specific. inferbench measures serving system behavior, not application performance. Five is enough.

---

## The corpus

### `filler.jsonl`

10,000 passages from Wikipedia (English), each 500–2000 tokens. Used as filler for prompts. The same corpus is used by every workload. Committed to the repo (~50 MB).

Why Wikipedia: public domain, diverse topics, neutral tone, well-tokenized by most tokenizers.

### `shared_prefix_system.txt`

A fixed 2000-token system prompt. Generic assistant instructions. Used as the shared prefix in `shared_prefix` workload.

### `agent_session_trace.jsonl`

100 agent session traces, each 10 turns. Each turn is a (user message, expected response pattern) pair. Used by `agent_session` workload to make sessions realistic (not just filler).

### `niah_needles.jsonl`

200 needle sentences (random facts). Used by the NIAH quality metric. Each needle has a key fact that's checkable.

### `longbench_subset.jsonl`

500 samples (100 per task × 5 tasks) from LongBench. Used by the `longbench_score` quality metric.

---

## The one-paragraph summary

Five workloads, each isolating one variable: context length, concurrency, prefix reuse, session persistence, and realistic mix. Every workload is deterministic given a seed, uses a fixed committed corpus, respects the four context bands, and generates exactly 256 tokens. The workloads produce 56 output cells (4 + 16 + 16 + 16 + 4) which, combined with 3 seeds, give 168 measured cells per full run. The derived metrics — `prefix_efficiency`, `kv_persistence_ratio`, `ttft_growth`, `fairness_ratio` — are the novel measurements that no other benchmark provides.
