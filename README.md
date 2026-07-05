# inferbench

Most LLM serving benchmarks report peak throughput. That's the wrong question.

The right question is: **when does the system break, and what happens when it does?**

`inferbench` measures LLM serving behavior under realistic long-context concurrent load, with explicit focus on graceful degradation. It runs fixed workloads across fixed context and concurrency bands, finds the cliff where the system fails, names the failure mode, and produces a hardware-fingerprinted report that's comparable across runs, servers, and hardware.

## What makes it different

Three things:

1. **The cliff finder.** Instead of reporting "max throughput = X tokens/sec," inferbench reports the curve of throughput vs concurrency, with the cliff explicitly identified. You learn not just how fast the system goes, but how many users it can handle before it falls apart.

2. **Quality-under-compression.** inferbench measures quality (NIAH accuracy) AS A FUNCTION OF compression level. Most benchmarks measure speed OR quality. This one measures what breaks when you enable FP8/INT4 — the axis nobody else covers.

3. **Hardware-fingerprinted results.** Every result includes a full hardware + software fingerprint. No fingerprint = not a valid result. Results are comparable across the community.

## Installation

```bash
git clone https://github.com/Ijas14/inferbench.git
cd inferbench
pip install -e .
```

## Quick start

There are three ways to run `inferbench`, ranging from zero-config to fully customized YAML.

### 1. Zero-Config (The fastest way)
If you just want to blast the standard benchmark against a running server:
```bash
python -m inferbench run --target http://localhost:8000/v1 --model qwen2.5-7b
```
This automatically tests all workloads and context bands (up to the model's actual `max_model_len`).

### 2. The Interactive Wizard
If you want to pick specific concurrencies or workloads without writing YAML:
```bash
python -m inferbench wizard
```
This launches a clean terminal UI to guide you through the setup and optionally saves your configuration for later.

### 3. Advanced Configuration (YAML)
For CI/CD and strict reproducible runs, you can provide a YAML configuration file. 
```bash
python -m inferbench run --config configs/mock_test.yaml
```

All methods produce a hardware-fingerprinted `results/results.json` and `results/results.md`.

## Commands

| Command | Description |
|---------|-------------|
| `python -m inferbench run --target <url> --model <name>` | Blast the standard benchmark against a running server |
| `python -m inferbench wizard` | Launch interactive setup wizard |
| `python -m inferbench run --config <path.yaml>` | Run strict reproducible benchmark from YAML |
| `pytest tests/` | Run the test suite |

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

## Architecture

The project is structured around a modular pipeline:
1. **Configuration (`inferbench/config/`)**: Strictly typed using Python `dataclasses` and parsed from YAML or the wizard.
2. **Adapters (`inferbench/adapters/`)**: Isolates server-specific implementations (e.g., OpenAI compatible APIs) from the core logic. Supports streaming TTFT.
3. **Workloads (`inferbench/workloads/`)**: Extensible workload generators that yield precisely tokenized requests.
4. **Orchestrator (`inferbench/cli.py` & `cliff/`)**: The execution engine that handles concurrent dispatching via a ThreadPool and identifies failure cliffs based on configurable thresholds.

> Technical decisions and tradeoffs are recorded as Architecture Decision Records (ADRs) in the `docs/decisions/` directory (Coming in v0.2).

## Submitting Your Results

When you run Inferbench against a real SGLang or vLLM instance serving any model (e.g., LLaMA, Qwen), you can submit your `results.json` and `results.md` to our central leaderboard. Open a PR with your `.md` and `.json` files in the `baseline_results/` directory!

> **Note on LongBench (v0.1)**:
> The initial version (v0.1) relies exclusively on the NIAH (Needle in a Haystack) task for testing quality retention during compression. LongBench tasks will be evaluated and integrated in v0.2.

> **Note on Metrics (v0.1)**: 
> Memory metrics (`memory_peak_kv`, etc.) are not currently scraped in this version. TTFT (Time-To-First-Token) metrics on non-streaming servers are equivalent to complete response time. Real TTFT latency requires a streaming-enabled adapter.

## Contributing

We welcome contributions! To get started:
1. Fork and clone the repository.
2. Install dependencies: `pip install -e .[dev]`
3. Run the tests to ensure your environment is clean:
   ```bash
   env PYTHONPATH="" PYTHONNOUSERSITE=1 python -m pytest tests/
   ```
4. Follow the existing architectural patterns (Adapters for APIs, Workloads for request generation).
5. Open a Pull Request with a clear description of the problem and the proposed solution.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
