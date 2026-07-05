import time
from typing import List, Dict, Any, Optional
from inferbench.adapters.base import ServerAdapter
from inferbench.workloads.base import Workload
from inferbench.config.defaults import ContextBand
from inferbench.metrics.collector import MetricsCollector
from inferbench.metrics.performance import compute_performance
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from inferbench.adapters.base import Response

def run_cell_with_pacing(adapter: ServerAdapter, requests: list, concurrency: int, timeout_seconds: int = 600, band_name: str = "UNKNOWN") -> dict:
    collector = MetricsCollector()
    collector.start()
    
    start_time = time.time()
    deadline = start_time + timeout_seconds
    
    import random
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = []
        for req in requests:
            # Pacing: sleep until send_at_offset + small jitter to avoid thundering herd on uvicorn
            jitter = random.uniform(0, 0.05)
            time_to_wait = (req.send_at_offset + jitter) - (time.time() - start_time)
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            futures.append(pool.submit(adapter.send, req))
        
        responses = []
        for f in futures:
            remaining = deadline - time.time()
            if remaining <= 0:
                f.cancel()
                responses.append(Response(request_id=-1, text="", first_token_time=0.0, complete_time=0.0, prompt_tokens=0, completion_tokens=0, error=f"Cell Timeout (>{timeout_seconds}s, band={band_name})"))
            else:
                try:
                    responses.append(f.result(timeout=remaining))
                except TimeoutError:
                    f.cancel()
                    responses.append(Response(request_id=-1, text="", first_token_time=0.0, complete_time=0.0, prompt_tokens=0, completion_tokens=0, error=f"Cell Timeout (>{timeout_seconds}s, band={band_name})"))
    
    collector.stop()
    return compute_performance(responses, collector)

def find_cliff(
    adapter: ServerAdapter,
    workload: Workload,
    context_band: ContextBand,
    concurrency_ladder: List[int],
    timeout_seconds: int = 600,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Runs the given workload across increasing concurrencies until the system breaks.
    "Breaks" is defined as:
    - OOM (Server returns memory error or crashes)
    - Error rate > 10%
    - Latency spike (P99 ttft > 10x the LIGHT baseline)
    (Needle accuracy to be added when quality metrics are implemented)
    """
    curve = []
    baseline_ttft_p99 = None
    cliff_concurrency = None
    failure_mode = None
    
    for concurrency in concurrency_ladder:
        requests = workload.schedule(seed=seed, band=context_band, concurrency=concurrency)
        
        perf = run_cell_with_pacing(adapter, requests, concurrency, timeout_seconds, context_band.name)
        
        ttft_p99 = perf.get("latency_ttft_p99", 0)
        if concurrency == 1:
            baseline_ttft_p99 = ttft_p99
            
        error_rate = perf.get("error_count", 0) / len(requests) if requests else 1.0
        
        curve_point = {
            "concurrency": concurrency,
            "throughput": perf.get("throughput_aggregate", 0),
            "ttft_p99": ttft_p99,
            "error_rate": error_rate
        }
        
        # Check breaking conditions
        if perf.get("oom", False):
            failure_mode = "OOM or Crash"
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        if error_rate == 1.0:
            errors = perf.get("errors", [])
            err_str = errors[0] if errors else "Unknown Error"
            
            if "maximum context length" in err_str.lower() or "too many tokens" in err_str.lower():
                failure_mode = f"Configuration Limit (Context Exceeded)"
            elif "connection" in err_str.lower() or "timeout" in err_str.lower():
                failure_mode = "Server Overwhelmed (Connection/Timeout)"
            else:
                failure_mode = f"100% Error Rate: {err_str[:60]}"
                
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        if error_rate > workload.config.cliff_error_threshold:
            failure_mode = f"High Error Rate (>{workload.config.cliff_error_threshold*100:.0f}%)"
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        if baseline_ttft_p99 and baseline_ttft_p99 > 0 and ttft_p99 > workload.config.cliff_latency_multiplier * baseline_ttft_p99:
            failure_mode = f"Latency Spike (>{workload.config.cliff_latency_multiplier}x baseline)"
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        curve.append(curve_point)
        
    return {
        "workload": type(workload).__name__.replace("Workload", "").lower(),
        "context_band": context_band.name,
        "curve": curve,
        "oom_threshold": cliff_concurrency if cliff_concurrency is not None else max(concurrency_ladder),
        "failure_mode": failure_mode
    }
