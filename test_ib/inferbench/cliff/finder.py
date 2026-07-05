import time
from typing import List, Dict, Any, Optional
from inferbench.adapters.base import ServerAdapter
from inferbench.workloads.base import Workload
from inferbench.config.defaults import ContextBand
from inferbench.metrics.collector import MetricsCollector
from inferbench.metrics.performance import compute_performance
from concurrent.futures import ThreadPoolExecutor

def run_cell_with_pacing(adapter: ServerAdapter, requests: list, concurrency: int) -> dict:
    collector = MetricsCollector()
    collector.start()
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = []
        for req in requests:
            # Pacing: sleep until send_at_offset
            time_to_wait = req.send_at_offset - (time.time() - start_time)
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            futures.append(pool.submit(adapter.send, req))
        
        responses = [f.result() for f in futures]
    
    collector.stop()
    return compute_performance(responses, collector)

def find_cliff(
    adapter: ServerAdapter,
    workload: Workload,
    context_band: ContextBand,
    concurrency_ladder: List[int],
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
        
        perf = run_cell_with_pacing(adapter, requests, concurrency)
        
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
        if perf.get("oom", False) or error_rate == 1.0:
            failure_mode = "OOM or Crash"
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        if error_rate > 0.1:
            failure_mode = "High Error Rate (>10%)"
            curve_point["note"] = failure_mode
            curve.append(curve_point)
            cliff_concurrency = concurrency
            break
            
        if baseline_ttft_p99 and baseline_ttft_p99 > 0 and ttft_p99 > 10 * baseline_ttft_p99:
            failure_mode = "Latency Spike (>10x baseline)"
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
