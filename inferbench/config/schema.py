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

    @classmethod
    def from_yaml(cls, path: str) -> "BenchConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        return cls(
            target=TargetConfig(**data.get("target", {})),
            model=ModelConfig(**data.get("model", {})),
            hardware=HardwareConfig(**data.get("hardware", {})),
            workloads=data.get("workloads", []),
            bands=data.get("bands", []),
            concurrencies=data.get("concurrencies", []),
            seeds=data.get("seeds", []),
            repeats=data.get("repeats", 1),
            quality=QualityConfig(**data.get("quality", {})) if "quality" in data else QualityConfig(),
            output=OutputConfig(**data.get("output", {})) if "output" in data else OutputConfig()
        )
