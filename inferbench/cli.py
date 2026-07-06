import argparse
import json
import os
import sys
import time

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

WORKLOAD_FACTORY = {
    "single_long": SingleLongWorkload,
    "concurrent_uniform": ConcurrentUniformWorkload,
    "shared_prefix": SharedPrefixWorkload,
    "mixed": MixedWorkload,
}

def safe_join(base_directory, user_path):
    base = os.path.abspath(os.path.realpath(base_directory))
    target = os.path.abspath(os.path.realpath(os.path.join(base, user_path)))
    if os.path.commonpath([base, target]) != base:
        raise ValueError("Path traversal detected in output directory.")
    return target

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
        sys.exit(1)
        
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

BAND_TIMEOUTS = {
    "SHORT": 120,
    "MEDIUM": 300,
    "LONG": 600,
    "EXTREME": 900,
}

def execute_cliff_finder(adapter: OpenAIAdapter, workload, config: BenchConfig, all_results: list, save_checkpoint, max_model_len: int, max_tokens: int) -> list:
    results = []
    
    for band_str in config.bands:
        band = BAND_MAP[band_str.lower()]
        if max_model_len and (band.value + max_tokens) > max_model_len:
            print(f"Skipping band {band.name} because its length + max_tokens ({band.value + max_tokens}) exceeds max_model_len ({max_model_len})")
            continue
            
        timeout_seconds = BAND_TIMEOUTS.get(band.name, config.cell_timeout_seconds)
        print(f"Running cliff finder for {workload.__class__.__name__} | Band: {band.name}")
        cliff_res = find_cliff(adapter, workload, config, band, config.concurrencies, timeout_seconds, seed=config.seeds[0])
        all_results.append(cliff_res)
        results.append(cliff_res)
        save_checkpoint()
    return results

def execute_standard_workload(adapter: OpenAIAdapter, workload, w_name: str, config: BenchConfig, all_results: list, save_checkpoint, max_model_len: int, max_tokens: int) -> list:
    results = []
    
    for band_str in config.bands:
        band = BAND_MAP[band_str.lower()]
        if max_model_len and (band.value + max_tokens) > max_model_len:
            print(f"Skipping band {band.name} because its length + max_tokens ({band.value + max_tokens}) exceeds max_model_len ({max_model_len})")
            continue
            
        timeout_seconds = BAND_TIMEOUTS.get(band.name, config.cell_timeout_seconds)
        for concurrency in config.concurrencies:
            for seed in config.seeds:
                for _ in range(config.repeats):
                    print(f"Running {w_name} | Band: {band.name} | Concurrency: {concurrency} | Seed: {seed}")
                    requests = workload.schedule(seed=seed, band=band, concurrency=concurrency)
                    
                    perf_metrics = run_cell_with_pacing(adapter, requests, max(1, concurrency), timeout_seconds, band.name)
                    
                    result = {
                        "workload": w_name,
                        "context_band": band.name,
                        "concurrency": concurrency,
                        "seed": seed,
                        **perf_metrics
                    }
                    all_results.append(result)
                    results.append(result)
                    save_checkpoint()
    return results

def warmup_server(adapter, max_tokens: int):
    """
    Sends concurrent dummy requests to force Triton JIT compilation for various block sizes
    and batch configurations before the timed benchmark starts.
    """
    from inferbench.workloads.base import Request
    import concurrent.futures
    print("Warming up server (forcing Triton JIT compilations)... ", end="", flush=True)
    
    # Send a heavy batch of requests to trigger standard, batch, and large prefix kernels
    # Varying prompt lengths forces Triton to compile different shape configurations
    reqs = []
    for i in range(16):
        # Generate prompt lengths from small (50 tokens) to large (16,000 tokens)
        length_multiplier = (i % 4 + 1) * 500
        reqs.append(
            Request(request_id=-i-1, prompt="A " * length_multiplier, max_tokens=max_tokens, send_at_offset=0.0, metadata={})
        )
    
    try:
        # High concurrency to trigger batched prefill and decode kernels
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(adapter.send, r) for r in reqs]
            concurrent.futures.wait(futures)
        print("Done.")
    except Exception as e:
        print(f"Failed ({e}). Continuing anyway.")
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
    
    timeout_s = 600
    print(f"Waiting for inference server at {config.target.endpoint} (timeout: {timeout_s}s)... ", end="", flush=True)
    deadline = time.time() + timeout_s
    ready = False
    attempt = 1
    
    while time.time() < deadline:
        if adapter.health():
            ready = True
            break
        print(".", end="", flush=True)
        time.sleep(2)
        attempt += 1
        
    if not ready:
        print(f"\n[FATAL ERROR] Server did not become ready after {timeout_s} seconds (Attempted {attempt} times). Aborting.")
        sys.exit(1)
        
    print(" Ready.\nBeginning benchmark...")

    max_model_len = adapter.get_max_model_len() or config.model.context_window
    max_tokens = 256
    print(f"Global Context Limit: {max_model_len} tokens")
    
    warmup_server(adapter, max_tokens)

    try:
        # Default base is current working directory
        safe_out_dir = safe_join(os.getcwd(), config.output.dir)
    except ValueError as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)

    os.makedirs(safe_out_dir, exist_ok=True)
    fingerprint = get_hardware_fingerprint()
    
    def save_checkpoint():
        if "json" in config.output.formats:
            out_path = os.path.join(safe_out_dir, "results.json")
            with open(out_path, "w") as f:
                json.dump({
                    "fingerprint": fingerprint,
                    "results": all_results
                }, f, indent=2)
                
        if "markdown" in config.output.formats:
            md_path = os.path.join(safe_out_dir, "results.md")
            export_markdown(all_results, fingerprint, md_path)

    for w_name in config.workloads:
        if w_name not in WORKLOAD_FACTORY:
            print(f"Skipping unknown workload {w_name}")
            continue
            
        workload = WORKLOAD_FACTORY[w_name](config, max_model_len, max_tokens)
        
        if w_name == "concurrent_uniform":
            res = execute_cliff_finder(adapter, workload, config, all_results, save_checkpoint, max_model_len, max_tokens)
            curves.extend(res)
        else:
            execute_standard_workload(adapter, workload, w_name, config, all_results, save_checkpoint, max_model_len, max_tokens)
    
    if "json" in config.output.formats:
        out_path = os.path.join(safe_out_dir, "results.json")
        with open(out_path, "w") as f:
            json.dump({
                "fingerprint": fingerprint,
                "results": all_results
            }, f, indent=2)
        print(f"Wrote JSON to {out_path}")
        
    if "markdown" in config.output.formats:
        md_path = os.path.join(safe_out_dir, "results.md")
        export_markdown(all_results, fingerprint, md_path)
        print(f"Wrote Markdown to {md_path}")
        
    print(f"Done.")

if __name__ == "__main__":
    main()
