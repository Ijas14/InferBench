import argparse
import json
import os
from inferbench.config.schema import BenchConfig
from inferbench.config.defaults import BAND_MAP
from inferbench.workloads.single_long import SingleLongWorkload
from inferbench.workloads.concurrent_uniform import ConcurrentUniformWorkload
from inferbench.workloads.shared_prefix import SharedPrefixWorkload
from inferbench.workloads.mixed import MixedWorkload
from inferbench.adapters.openai_api import OpenAIAdapter
from inferbench.metrics.collector import MetricsCollector
from inferbench.metrics.performance import compute_performance
from inferbench.cliff.finder import find_cliff, run_cell_with_pacing
from inferbench.results.fingerprint import get_hardware_fingerprint
from inferbench.results.markdown_exporter import export_markdown

def main():
    parser = argparse.ArgumentParser(description="Inferbench Runner")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--config", required=True, help="Path to config YAML")
    args = parser.parse_args()

    if args.command == "run":
        config = BenchConfig.from_yaml(args.config)
        
        adapter = OpenAIAdapter(config)
        all_results = []
        curves = []

        print(f"Starting inferbench E2E with {config.target.endpoint}")

        max_model_len = adapter.get_max_model_len()
        if max_model_len:
            print(f"Detected max_model_len = {max_model_len}")

        for w_name in config.workloads:
            if w_name == "single_long":
                workload = SingleLongWorkload(config)
            elif w_name == "concurrent_uniform":
                workload = ConcurrentUniformWorkload(config)
            elif w_name == "shared_prefix":
                workload = SharedPrefixWorkload(config)
            elif w_name == "mixed":
                workload = MixedWorkload(config)
            else:
                print(f"Skipping unknown workload {w_name}")
                continue

            for band_str in config.bands:
                band = BAND_MAP[band_str.lower()]
                
                # Check model limits
                if max_model_len and band.value > max_model_len:
                    print(f"Skipping band {band.name} because its length ({band.value}) exceeds max_model_len ({max_model_len})")
                    continue
                
                # If it's concurrent_uniform, we want to run the cliff finder
                if w_name == "concurrent_uniform":
                    print(f"Running cliff finder for {w_name} | Band: {band.name}")
                    cliff_res = find_cliff(adapter, workload, band, config.concurrencies, seed=config.seeds[0])
                    curves.append(cliff_res)
                    # We can also log the curve into the results list
                    all_results.append(cliff_res)
                    continue
                
                for concurrency in config.concurrencies:
                    for seed in config.seeds:
                        for _ in range(config.repeats):
                            print(f"Running {w_name} | Band: {band.name} | Concurrency: {concurrency} | Seed: {seed}")
                            requests = workload.schedule(seed=seed, band=band, concurrency=concurrency)
                            
                            perf_metrics = run_cell_with_pacing(adapter, requests, max(1, concurrency))
                            
                            result = {
                                "workload": w_name,
                                "context_band": band.name,
                                "concurrency": concurrency,
                                "seed": seed,
                                **perf_metrics
                            }
                            all_results.append(result)
        
        os.makedirs(config.output.dir, exist_ok=True)
        
        fingerprint = get_hardware_fingerprint()
        
        if "json" in config.output.formats:
            out_path = os.path.join(config.output.dir, "results.json")
            with open(out_path, "w") as f:
                json.dump({
                    "fingerprint": fingerprint,
                    "results": all_results
                }, f, indent=2)
            print(f"Wrote JSON to {out_path}")
            
        if "markdown" in config.output.formats:
            md_path = os.path.join(config.output.dir, "results.md")
            export_markdown(all_results, fingerprint, md_path)
            print(f"Wrote Markdown to {md_path}")
            
        print(f"Done.")

if __name__ == "__main__":
    main()
