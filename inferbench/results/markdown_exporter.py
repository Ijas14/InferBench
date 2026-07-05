import json
from typing import List, Dict, Any

def export_markdown(results: List[Dict[str, Any]], fingerprint: Dict[str, Any], output_path: str):
    md = ["# Inferbench Results\n"]
    
    # Fingerprint Section
    md.append("## Hardware & Environment Fingerprint")
    md.append("| Property | Value |")
    md.append("|---|---|")
    for k, v in fingerprint.items():
        md.append(f"| {k} | {v} |")
    md.append("\n")
    
    # Summary Table Section
    md.append("## Summary")
    md.append("| Workload | Context Band | Concurrency | Throughput (tokens/s) | P99 TTFT (ms) | Error Rate |")
    md.append("|---|---|---|---|---|---|")
    
    for r in results:
        # Check if this is a standard result or a cliff finder curve result
        if "curve" in r:
            # It's a cliff finder result
            for point in r["curve"]:
                err = f"{point['error_rate'] * 100:.1f}%"
                if "note" in point:
                    err += f" ({point['note']})"
                md.append(f"| {r['workload']} | {r['context_band']} | {point['concurrency']} | {point['throughput']:.2f} | {point['ttft_p99']:.2f} | {err} |")
        else:
            md.append(f"| {r['workload']} | {r['context_band']} | {r['concurrency']} | {r.get('throughput_aggregate', 0):.2f} | {r.get('latency_ttft_p99', 0):.2f} | {r.get('error_count', 0)} |")
            
    md.append("\n> **Note on Metrics (v0.1.3)**: Memory metrics (`memory_peak_kv`, etc.) are not currently scraped in this version. Per-request throughput includes prefill time (v0.1.4 fix).")
    md.append("\n")
    
    # Cliff Finder Highlights
    cliff_results = [r for r in results if "curve" in r and r.get("failure_mode")]
    if cliff_results:
        md.append("## Cliff Finder Analysis")
        for r in cliff_results:
            md.append(f"### {r['workload']} ({r['context_band']})")
            md.append(f"- **OOM / Cliff Threshold:** Concurrency {r['oom_threshold']}")
            md.append(f"- **Failure Mode:** {r['failure_mode']}")
            md.append("")
    
    with open(output_path, "w") as f:
        f.write("\n".join(md))
