import time
import statistics
from typing import List
from inferbench.adapters.base import Response
from inferbench.workloads.base import Request
from inferbench.metrics.collector import MetricsCollector

def compute_performance(responses: List[Response], collector: MetricsCollector) -> dict:
    if not responses:
        return {}

    valid_responses = [r for r in responses if not r.error]
    error_count = len(responses) - len(valid_responses)
    
    if not valid_responses:
        return {
            "throughput_aggregate": 0.0,
            "throughput_per_request_p50": 0.0,
            "throughput_per_request_p95": 0.0,
            "latency_ttft_p50": 0.0,
            "latency_ttft_p95": 0.0,
            "latency_ttft_p99": 0.0,
            "latency_inter_token_p50": 0.0,
            "latency_inter_token_p95": 0.0,
            "latency_inter_token_p99": 0.0,
            "memory_peak_kv": 0,
            "memory_peak_total": 0,
            "error_count": error_count,
            "oom": False # Need to extract logic for actual OOM
        }

    total_output_tokens = sum(r.output_tokens for r in valid_responses)
    wall_clock_time = collector.end_time - collector.start_time
    throughput_aggregate = total_output_tokens / wall_clock_time if wall_clock_time > 0 else 0.0

    per_req_throughputs = [r.output_tokens / (r.complete_time - r.send_time) for r in valid_responses if (r.complete_time - r.send_time) > 0]
    
    ttfts = [(r.first_token_time - r.send_time) * 1000 for r in valid_responses if r.first_token_time]

    def pctl(data, p):
        if not data: return 0.0
        return statistics.quantiles(data, n=100, method='inclusive')[p-1] if len(data) > 1 else data[0]
        
    return {
        "throughput_aggregate": throughput_aggregate,
        "throughput_per_request_p50": pctl(per_req_throughputs, 50),
        "throughput_per_request_p95": pctl(per_req_throughputs, 95),
        "latency_ttft_p50": pctl(ttfts, 50),
        "latency_ttft_p95": pctl(ttfts, 95),
        "latency_ttft_p99": pctl(ttfts, 99),
        "latency_inter_token_p50": 0.0, # N/A for non-streaming mock
        "latency_inter_token_p95": 0.0,
        "latency_inter_token_p99": 0.0,
        "memory_peak_kv": 0, # Mocked
        "memory_peak_total": 0,
        "error_count": error_count,
        "oom": False
    }
