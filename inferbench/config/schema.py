import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class TargetConfig:
    endpoint: str
    model: str
    api_style: str = "openai"
    metrics_endpoint: Optional[str] = None

@dataclass(frozen=True)
class ModelConfig:
    context_window: int
    quantization: str = "none"
    kv_precision: str = "bf16"

@dataclass(frozen=True)
class HardwareConfig:
    gpu: str
    vram_gb: int
    driver: str
    cpu: Optional[str] = None
    ram_gb: Optional[int] = None
    num_gpus: int = 1

@dataclass(frozen=True)
class QualityConfig:
    enabled: bool = False
    eval_sets: List[str] = field(default_factory=list)
    perplexity: bool = False

@dataclass(frozen=True)
class OutputConfig:
    dir: str = "results/"
    formats: List[str] = field(default_factory=lambda: ["json", "markdown"])

@dataclass(frozen=True)
class BenchConfig:
    target: TargetConfig
    model: ModelConfig
    hardware: HardwareConfig
    workloads: List[str]
    bands: List[str]
    concurrencies: List[int]
    seeds: List[int]
    repeats: int = 1
    quality: QualityConfig = field(default_factory=QualityConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    cliff_latency_multiplier: float = 10.0
    cliff_error_threshold: float = 0.1

    @classmethod
    def from_yaml(cls, path: str) -> "BenchConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        config = cls(
            target=TargetConfig(**data.get("target", {})),
            model=ModelConfig(**data.get("model", {})),
            hardware=HardwareConfig(**data.get("hardware", {})),
            workloads=data.get("workloads", []),
            bands=data.get("bands", []),
            concurrencies=data.get("concurrencies", []),
            seeds=data.get("seeds", [42]),
            repeats=data.get("repeats", 1),
            quality=QualityConfig(**data.get("quality", {})) if "quality" in data else QualityConfig(),
            output=OutputConfig(**data.get("output", {})) if "output" in data else OutputConfig(),
            cliff_latency_multiplier=float(data.get("cliff_latency_multiplier", 10.0)),
            cliff_error_threshold=float(data.get("cliff_error_threshold", 0.1))
        )
        config.validate()
        return config

    def validate(self):
        if not isinstance(self.concurrencies, list):
            raise ValueError(f"Config Error: 'concurrencies' must be a list, got {type(self.concurrencies).__name__} ({self.concurrencies}). Did you mean: concurrencies: [{self.concurrencies}]?")
        if not isinstance(self.bands, list):
            raise ValueError(f"Config Error: 'bands' must be a list, got {type(self.bands).__name__}.")
        if not isinstance(self.workloads, list):
            raise ValueError(f"Config Error: 'workloads' must be a list, got {type(self.workloads).__name__}.")
        if not isinstance(self.seeds, list):
            raise ValueError(f"Config Error: 'seeds' must be a list, got {type(self.seeds).__name__}.")
        
        valid_workloads = {"single_long", "concurrent_uniform", "shared_prefix", "mixed"}
        for w in self.workloads:
            if w not in valid_workloads:
                raise ValueError(f"Config Error: Unknown workload '{w}'. Valid workloads are {list(valid_workloads)}")
        
        valid_bands = {"short", "medium", "long", "extreme"}
        for b in self.bands:
            if str(b).lower() not in valid_bands:
                raise ValueError(f"Config Error: Unknown band '{b}'. Valid bands are {list(valid_bands)}")
