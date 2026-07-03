# inferbench

Most LLM serving benchmarks report peak throughput. That's the wrong question.

The right question is: **when does the system break, and what happens when it does?**

`inferbench` measures LLM serving behavior under realistic long-context concurrent load, with explicit focus on graceful degradation. It runs fixed workloads across fixed context and concurrency bands, finds the cliff where the system fails, names the failure mode, and produces a hardware-fingerprinted report that's comparable across runs, servers, and hardware.

## What makes it different

Three things:

1. **The cliff finder.** Instead of reporting "max throughput = X tokens/sec," inferbench reports the curve of throughput vs concurrency, with the cliff explicitly identified. You learn not just how fast the system goes, but how many users it can handle before it falls apart.

2. **Quality-under-compression.** inferbench measures quality (NIAH accuracy) AS A FUNCTION OF compression level. Most benchmarks measure speed OR quality. This one measures what breaks when you enable FP8/INT4 — the axis nobody else covers.

3. **Hardware-fingerprinted results.** Every result includes a full hardware + software fingerprint. No fingerprint = not a valid result. Results are comparable across the community.

## Quick start

```bash
git clone https://github.com/yourname/inferbench.git
cd inferbench
pip install -e .

# Start the mock server in another terminal:
python tests/mock_server.py

# Run inferbench
inferbench run --config configs/mock_test.yaml
```

Produces `results/results.json` and `results/results.md`.

## Workloads

| Workload | What it isolates |
|---|---|
| `single_long` | Context length (no contention) |
| `concurrent_uniform` | Concurrency (uniform load) |
| `shared_prefix` | Prefix reuse efficiency |
| `mixed` | Realistic mix (the reality check) |

Each runs across four context bands (4k / 32k / 128k / 256k) and four concurrency bands (1 / 8 / 32 / 128).

## The cliff finder

The signature feature. For each (workload × context band), inferbench ramps concurrency until the system breaks:

- OOM (server returns memory error)
- Error rate > 10%
- P99 TTFT > 10× baseline
- Needle accuracy < 0.5

Then it reports the cliff point, the failure mode, and the full curve up to that point.

## Submitting Your Results

When you run Inferbench against a real SGLang or vLLM instance serving any model (e.g., LLaMA, Qwen), you can submit your `results.json` and `results.md` to our central leaderboard. Open a PR with your `.md` and `.json` files in the `baseline_results/` directory!

> **Note on LongBench (v0.1)**:
> The initial version (v0.1) relies exclusively on the NIAH (Needle in a Haystack) task for testing quality retention during compression. LongBench tasks will be evaluated and integrated in v0.2.

> **Note on Metrics (v0.1)**: 
> Memory metrics (`memory_peak_kv`, etc.) are not currently scraped in this version. TTFT (Time-To-First-Token) metrics on non-streaming servers are equivalent to complete response time. Real TTFT latency requires a streaming-enabled adapter.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
