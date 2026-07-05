# Inferbench Results

## Hardware & Environment Fingerprint
| Property | Value |
|---|---|
| os | Linux-6.8.0-124-generic-x86_64-with-glibc2.35 |
| python_version | 3.12.13 |
| cpu | x86_64 |
| ram_gb | 235.95 |
| gpu_name | AMD Instinct MI300X |
| gpu_vram_gb | 192.0 |
| gpu_driver | 6.1.1 |
| pytorch_version | 2.10.0+git8514f05 |
| sglang_version | Not Installed |
| vllm_version | 0.23.0 |


## Summary
| Workload | Context Band | Concurrency | Throughput (tokens/s) | P99 TTFT (ms) | Error Rate |
|---|---|---|---|---|---|
| single_long | SHORT | 1 | 35.75 | 3715.52 | 0 |
| single_long | SHORT | 8 | 144.55 | 1002.75 | 0 |
| single_long | SHORT | 32 | 148.10 | 585.73 | 0 |
| single_long | SHORT | 64 | 147.74 | 604.57 | 0 |
| single_long | MEDIUM | 1 | 8.93 | 7093.29 | 0 |
| single_long | MEDIUM | 8 | 47.75 | 3111.25 | 0 |
| single_long | MEDIUM | 32 | 47.75 | 3110.97 | 0 |
| single_long | MEDIUM | 64 | 48.41 | 2860.14 | 0 |
| single_long | LONG | 1 | 1.39 | 72566.88 | 1 |
| single_long | LONG | 8 | 15.24 | 6988.92 | 0 |
| single_long | LONG | 32 | 15.24 | 7039.51 | 0 |
| single_long | LONG | 64 | 15.23 | 7049.86 | 0 |
| single_long | EXTREME | 1 | 0.00 | 0.00 | 5 |
| single_long | EXTREME | 8 | 0.00 | 0.00 | 5 |
| single_long | EXTREME | 32 | 0.00 | 0.00 | 5 |
| single_long | EXTREME | 64 | 0.00 | 0.00 | 5 |
| concurrentuniform | SHORT | 1 | 41.28 | 242.87 | 0.0% |
| concurrentuniform | SHORT | 8 | 196.55 | 2998.45 | 0.0% (Latency Spike (>10.0x baseline)) |
| concurrentuniform | MEDIUM | 1 | 11.53 | 652.37 | 0.0% |
| concurrentuniform | MEDIUM | 8 | 22.78 | 65173.04 | 0.0% (Latency Spike (>10.0x baseline)) |
| concurrentuniform | LONG | 1 | 3.35 | 1672.19 | 0.0% |
| concurrentuniform | LONG | 8 | 0.00 | 0.00 | 100.0% (Cell Timeout (>600s, band=LONG)) |
| concurrentuniform | EXTREME | 1 | 0.00 | 0.00 | 100.0% (Configuration Limit (Context Exceeded)) |
| shared_prefix | SHORT | 1 | 28.75 | 1040.11 | 0 |
| shared_prefix | SHORT | 8 | 176.15 | 2255.94 | 0 |
| shared_prefix | SHORT | 32 | 453.00 | 8068.69 | 0 |
| shared_prefix | SHORT | 64 | 563.36 | 17272.71 | 0 |
| shared_prefix | MEDIUM | 1 | 8.14 | 7973.55 | 0 |
| shared_prefix | MEDIUM | 8 | 21.14 | 72007.36 | 0 |
| shared_prefix | MEDIUM | 32 | 31.38 | 235008.65 | 0 |
| shared_prefix | MEDIUM | 64 | 0.00 | 0.00 | 64 |
| shared_prefix | LONG | 1 | 1.66 | 77639.93 | 0 |
| shared_prefix | LONG | 8 | 3.63 | 478825.53 | 0 |
| shared_prefix | LONG | 32 | 0.00 | 0.00 | 32 |
| shared_prefix | LONG | 64 | 0.00 | 0.00 | 64 |
| shared_prefix | EXTREME | 1 | 0.00 | 0.00 | 1 |
| shared_prefix | EXTREME | 8 | 0.00 | 0.00 | 8 |
| shared_prefix | EXTREME | 32 | 0.00 | 0.00 | 32 |
| shared_prefix | EXTREME | 64 | 0.00 | 0.00 | 64 |
| mixed | SHORT | 1 | 22.16 | 909.72 | 0 |
| mixed | SHORT | 8 | 130.53 | 1973.32 | 0 |
| mixed | SHORT | 32 | 261.80 | 3512.65 | 0 |
| mixed | SHORT | 64 | 253.26 | 3446.73 | 64 |
| mixed | MEDIUM | 1 | 12.00 | 7107.94 | 0 |
| mixed | MEDIUM | 8 | 10.28 | 60607.02 | 10 |
| mixed | MEDIUM | 32 | 17.45 | 105637.07 | 64 |
| mixed | MEDIUM | 64 | 22.19 | 18921.30 | 128 |
| mixed | LONG | 1 | 4.04 | 77934.18 | 0 |
| mixed | LONG | 8 | 0.57 | 667.36 | 22 |
| mixed | LONG | 32 | 0.00 | 0.00 | 96 |
| mixed | LONG | 64 | 0.00 | 0.00 | 192 |
| mixed | EXTREME | 1 | 7.29 | 1582.29 | 0 |
| mixed | EXTREME | 8 | 3.83 | 118260.98 | 8 |
| mixed | EXTREME | 32 | 7.05 | 218182.05 | 64 |
| mixed | EXTREME | 64 | 0.00 | 0.00 | 192 |

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

### concurrentuniform (EXTREME)
- **OOM / Cliff Threshold:** Concurrency 1
- **Failure Mode:** Configuration Limit (Context Exceeded)
