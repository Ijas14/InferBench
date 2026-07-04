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

def get_default_config(endpoint: str, model: str) -> BenchConfig:
    import yaml
    from inferbench.config.schema import TargetConfig, ModelConfig, HardwareConfig, QualityConfig, OutputConfig
    return BenchConfig(
        target=TargetConfig(endpoint=endpoint, model=model, api_style="openai_chat"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="Unknown", vram_gb=0, driver="unknown"),
        workloads=["single_long", "concurrent_uniform", "shared_prefix", "mixed"],
        bands=["short", "medium", "long", "extreme"],
        concurrencies=[1, 8, 32, 128],
        seeds=[42],
        repeats=1,
        quality=QualityConfig(),
        output=OutputConfig()
    )

def run_wizard() -> BenchConfig:
    try:
        import questionary
    except ImportError:
        print("Please install questionary: pip install questionary")
        exit(1)
        
    print("╭─ inferbench setup ────────────────────────────────────────╮")
    from questionary import Choice
    
    endpoint = questionary.text("Server endpoint:", default="http://localhost:8000/v1").ask()
    model = questionary.text("Model name:", default="qwen2.5-7b").ask()
    
    bands = questionary.checkbox(
        "Context bands:",
        choices=[
            Choice("short", checked=True),
            Choice("medium", checked=True),
            Choice("long", checked=True),
            Choice("extreme", checked=True)
        ]
    ).ask()
    
    concurrency_str = questionary.text("Concurrency ladder (comma-separated):", default="1, 8, 32, 128").ask()
    concurrencies = [int(c.strip()) for c in concurrency_str.split(",")]
    
    workloads = questionary.checkbox(
        "Workloads:",
        choices=[
            Choice("single_long", checked=True),
            Choice("concurrent_uniform", checked=True),
            Choice("shared_prefix", checked=True),
            Choice("mixed", checked=True)
        ]
    ).ask()
    
    out_dir = questionary.text("Output directory:", default="results/").ask()
    save_path = questionary.text("Save as config (optional):", default="").ask()
    
    print("╰────────────────────────────────────────────────────────────────────╯")
    
    import yaml
    from inferbench.config.schema import TargetConfig, ModelConfig, HardwareConfig, QualityConfig, OutputConfig
    
    config = BenchConfig(
        target=TargetConfig(endpoint=endpoint, model=model, api_style="openai_chat"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="Unknown", vram_gb=0, driver="unknown"),
        workloads=workloads,
        bands=bands,
        concurrencies=concurrencies,
        seeds=[42],
        repeats=1,
        quality=QualityConfig(),
        output=OutputConfig(dir=out_dir)
    )
    
    if save_path:
        # Minimal dump
        out_dict = {
            "target": {"endpoint": endpoint, "model": model, "api_style": "openai_chat"},
            "model": {"context_window": 32768, "quantization": "none", "kv_precision": "bf16"},
            "hardware": {"gpu": "Unknown", "vram_gb": 0, "driver": "unknown"},
            "workloads": workloads,
            "bands": bands,
            "concurrencies": concurrencies,
            "seeds": [42],
            "repeats": 1,
            "output": {"dir": out_dir, "formats": ["json", "markdown"]}
        }
        with open(save_path, "w") as f:
            yaml.dump(out_dict, f, sort_keys=False)
        print(f"Saved config to {save_path}")
        
    return config

def main():
    parser = argparse.ArgumentParser(description="Inferbench Runner")
    parser.add_argument("command", choices=["run", "wizard"])
    parser.add_argument("--config", required=False, help="Path to config YAML (override)")
    parser.add_argument("--target", required=False, help="Zero-config endpoint (e.g. http://localhost:8000/v1)")
    parser.add_argument("--model", required=False, help="Zero-config model ID")
    args = parser.parse_args()

    config = None
    if args.command == "wizard":
        config = run_wizard()
    elif args.command == "run":
        if args.config:
            config = BenchConfig.from_yaml(args.config)
        elif args.target and args.model:
            config = get_default_config(args.target, args.model)
        else:
            parser.error("run command requires either --config OR both --target and --model")
        
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
