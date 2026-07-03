# inferbench v0.1.0

First public release.

## What's included

- **4 workloads:** single_long, concurrent_uniform, shared_prefix, mixed
- **Cliff finder:** automated discovery of concurrency limits with failure mode classification
- **Quality metric:** Needle-in-a-Haystack (NIAH) accuracy at 4 depths
- **Hardware fingerprinting:** mandatory for all results
- **Token-precise context bands:** uses target model's tokenizer (transformers/tiktoken fallback)
- **Markdown + JSON export:** human-readable reports + machine-parseable data
- **7 passing tests** including reproducibility (same seed → same schedule)
- **Mock server** for local development without GPU

## What's not included (v0.2 roadmap)

- `agent_session` workload (long-running stateful sessions)
- LongBench quality subset
- Memory metrics scraping (currently 0, noted in reports)
- Streaming inter-token latency (requires streaming server)

## Known limitations

- Memory metrics (`memory_peak_kv`, `memory_peak_total`) are not scraped in v0.1
- Inter-token latency requires streaming; non-streaming TTFT equals complete time
- Mock server is single-threaded; use a real server for valid cliff finder results

## Tested against

- Mock server (format verification only — not a valid baseline)

## What's needed next

Real silicon baselines. If you run inferbench against your serving stack, submit results to the leaderboard.
