# Inferbench

Inferbench is a robust, deterministic, and highly reproducible benchmark suite designed for evaluating LLM serving engines. Rather than simple throughput testing, Inferbench uses workload simulation (like concurrent arrivals and shared prefixes) paired with a signature "Cliff Finder" feature to find exactly when and how an LLM serving system degrades under pressure.

## Features

- **Cliff Finder**: Automatically identifies the concurrency at which a system fails (OOM, latency spikes, or error rate threshold).
- **Deterministic Scheduling**: Identical seeds always produce the exact same request lengths and timings, ensuring tests are 100% reproducible.
- **Dynamic Workloads**: Includes concurrent uniform, shared prefix, and mixed arrival models.
- **Hardware Fingerprinting**: Automatically logs GPU, Driver, OS, and LLM Framework details into the benchmark output.

## Installation

```bash
git clone https://github.com/yourorg/inferbench.git
cd inferbench
pip install -e .
```

## Running the Benchmark

You define your test through a simple YAML configuration file. We have provided `configs/mock_test.yaml` to run a fast validation test against a mocked API server.

1. Start the mock server (in another terminal):
```bash
python tests/mock_server.py
```

2. Run inferbench:
```bash
python -m inferbench run --config configs/mock_test.yaml
```

The output will automatically generate `results/results.md` containing the hardware fingerprint and a markdown summary of the degradation curves!

## Submitting Your Results

When you run Inferbench against a real SGLang or vLLM instance serving any model (e.g., LLaMA, Qwen), you can submit your `results.json` and `results.md` to our central leaderboard. Open a PR with your `.md` and `.json` files in the `baseline_results/` directory!

> **Note on LongBench (v0.1)**:
> The initial version (v0.1) relies exclusively on the NIAH (Needle in a Haystack) task for testing quality retention during compression. LongBench tasks will be evaluated and integrated in v0.2.

> **Note on Metrics (v0.1)**: 
> Memory metrics (`memory_peak_kv`, etc.) are not currently scraped in this version. TTFT (Time-To-First-Token) metrics on non-streaming servers are equivalent to complete response time. Real TTFT latency requires a streaming-enabled adapter.
