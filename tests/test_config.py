import os
import pytest
from inferbench.config.schema import BenchConfig

def test_parse_valid_yaml(tmp_path):
    yaml_content = """
target:
  endpoint: "http://localhost:30000/v1"
  model: "Qwen/Qwen3-235B-A22B-Thinking-2507"
  api_style: "openai"

model:
  context_window: 262144
  quantization: "none"
  kv_precision: "bf16"

hardware:
  gpu: "AMD Instinct MI300X"
  vram_gb: 192
  driver: "rocm-6.1"

workloads:
  - single_long
  - concurrent_uniform

bands: [short, medium]
concurrencies: [1, 8]
seeds: [42]
repeats: 1
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content)

    config = BenchConfig.from_yaml(str(config_file))
    
    assert config.target.endpoint == "http://localhost:30000/v1"
    assert config.model.context_window == 262144
    assert config.hardware.gpu == "AMD Instinct MI300X"
    assert config.workloads == ["single_long", "concurrent_uniform"]
    assert config.bands == ["short", "medium"]
    assert config.concurrencies == [1, 8]
    assert config.seeds == [42]
