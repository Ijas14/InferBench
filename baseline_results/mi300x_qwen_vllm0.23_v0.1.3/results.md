# Inferbench Results

## Hardware & Environment Fingerprint
| Property | Value |
|---|---|
| os | Linux-6.8.0-124-generic-x86_64-with-glibc2.35 |
| python_version | 3.12.13 |
| cpu | x86_64 |
| ram_gb | 235.95 |
| gpu_name | AMD Instinct MI300X |
| gpu_vram_gb | 192 |
| gpu_driver | 6.16.13 |
| pytorch_version | 2.10.0+git8514f05 |
| sglang_version | Not Installed |
| vllm_version | 0.23.0 |


## Summary
| Workload | Context Band | Concurrency | Throughput (tokens/s) | P99 TTFT (ms) | Error Rate |
|---|---|---|---|---|---|
| single_long | SHORT | 1 | 38.81 | 555.33 | 0 |
| single_long | SHORT | 8 | 146.86 | 599.10 | 0 |
| single_long | SHORT | 32 | 147.02 | 595.01 | 0 |
| single_long | SHORT | 64 | 147.20 | 582.32 | 0 |
| single_long | MEDIUM | 1 | 8.91 | 7129.80 | 0 |
| single_long | MEDIUM | 8 | 47.63 | 3137.07 | 0 |
| single_long | MEDIUM | 32 | 48.26 | 2881.58 | 0 |
| single_long | MEDIUM | 64 | 48.27 | 2882.87 | 0 |
| single_long | LONG | 1 | 1.39 | 72909.38 | 1 |
| single_long | LONG | 8 | 15.20 | 7043.07 | 0 |
| single_long | LONG | 32 | 15.20 | 7024.33 | 0 |
| single_long | LONG | 64 | 15.21 | 7048.28 | 0 |
| concurrentuniform | SHORT | 1 | 40.88 | 207.75 | 0.0% |
| concurrentuniform | SHORT | 8 | 192.78 | 3170.62 | 0.0% (Latency Spike (>10.0x baseline)) |
| concurrentuniform | MEDIUM | 1 | 11.48 | 642.97 | 0.0% |
| concurrentuniform | MEDIUM | 8 | 22.69 | 65430.27 | 0.0% (Latency Spike (>10.0x baseline)) |
| concurrentuniform | LONG | 1 | 3.34 | 1636.65 | 0.0% |
| concurrentuniform | LONG | 8 | 0.00 | 0.00 | 100.0% (Cell Timeout (>600s, band=LONG)) |
| shared_prefix | SHORT | 1 | 28.44 | 1109.63 | 0 |
| shared_prefix | SHORT | 8 | 175.06 | 2284.08 | 0 |
| shared_prefix | SHORT | 32 | 434.53 | 8821.18 | 0 |
| shared_prefix | SHORT | 64 | 560.82 | 17320.83 | 0 |
| shared_prefix | MEDIUM | 1 | 8.11 | 7993.80 | 0 |
| shared_prefix | MEDIUM | 8 | 21.31 | 71189.41 | 0 |
| shared_prefix | MEDIUM | 32 | 31.47 | 234305.36 | 0 |
| shared_prefix | MEDIUM | 64 | 0.00 | 0.00 | 64 |
| shared_prefix | LONG | 1 | 1.65 | 78075.81 | 0 |
| shared_prefix | LONG | 8 | 3.62 | 479475.79 | 0 |
| shared_prefix | LONG | 32 | 0.00 | 0.00 | 32 |
| shared_prefix | LONG | 64 | 0.00 | 0.00 | 64 |
| mixed | SHORT | 1 | 22.10 | 774.71 | 0 |
| mixed | SHORT | 8 | 130.41 | 1771.60 | 0 |
| mixed | SHORT | 32 | 258.63 | 3557.63 | 0 |
| mixed | SHORT | 64 | 255.35 | 3659.62 | 64 |
| mixed | MEDIUM | 1 | 11.96 | 7121.36 | 0 |
| mixed | MEDIUM | 8 | 20.85 | 52245.12 | 0 |
| mixed | MEDIUM | 32 | 16.26 | 108280.27 | 64 |
| mixed | MEDIUM | 64 | 26.41 | 18685.24 | 128 |
| mixed | LONG | 1 | 11.78 | 7419.55 | 0 |
| mixed | LONG | 8 | 0.58 | 642.84 | 22 |
| mixed | LONG | 32 | 0.00 | 0.00 | 96 |
| mixed | LONG | 64 | 0.00 | 0.00 | 192 |

> **Note on Metrics (v0.1.3)**: Memory metrics (`memory_peak_kv`, etc.) are not currently scraped in this version. Per-request throughput includes prefill time (v0.1.4 fix).


## Cliff Finder Analysis
### concurrentuniform (SHORT)
- **OOM / Cliff Threshold:** Concurrency 8
- **Failure Mode:** Latency Spike (>10.0x baseline)

### concurrentuniform (MEDIUM)
- **OOM / Cliff Threshold:** Concurrency 8
- **Failure Mode:** Latency Spike (>10.0x baseline)

### concurrentuniform (LONG)
- **OOM / Cliff Threshold:** Concurrency 8
- **Failure Mode:** Cell Timeout (>600s, band=LONG)
