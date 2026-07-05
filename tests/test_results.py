import pytest
import os
import json
from unittest.mock import patch, MagicMock
from inferbench.results.fingerprint import get_hardware_fingerprint
from inferbench.results.markdown_exporter import export_markdown

def test_fingerprint_parses_nvidia_smi():
    """
    Tests that the hardware fingerprint correctly extracts GPU name, 
    VRAM (in GB), and driver version from nvidia-smi csv output.
    """
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="NVIDIA A100-SXM4-80GB, 81920, 535.129.03\n")
        
        fp = get_hardware_fingerprint()
        
        assert fp["gpu_name"] == "NVIDIA A100-SXM4-80GB"
        assert fp["gpu_vram_gb"] == 80.0
        assert fp["gpu_driver"] == "535.129.03"

def test_fingerprint_parses_rocm_smi():
    """
    Tests that hardware fingerprint falls back to rocm-smi if nvidia-smi fails.
    Since rocm-smi parsing is currently a mock placeholder in the code,
    we just verify it doesn't crash when providing valid JSON.
    """
    with patch('subprocess.run') as mock_run:
        def side_effect(*args, **kwargs):
            if 'nvidia-smi' in args[0]:
                return MagicMock(returncode=127) # not found
            elif 'rocm-smi' in args[0]:
                return MagicMock(returncode=0, stdout='{"card0": {"VRAM Total Memory (B)": "17179869184"}}')
            return MagicMock(returncode=1)
        mock_run.side_effect = side_effect
        
        fp = get_hardware_fingerprint()
        # Since rocm parsing isn't fully implemented yet, it defaults to Unknown
        assert fp["gpu_name"] == "Unknown"

def test_markdown_exporter(tmp_path):
    """
    Tests that export_markdown correctly generates a Markdown table
    for both standard results and cliff finder curve results.
    """
    results = [
        {
            "workload": "single_long",
            "context_band": "SHORT",
            "concurrency": 8,
            "throughput_aggregate": 150.5,
            "latency_ttft_p99": 0.45,
            "error_count": 0
        },
        {
            "workload": "concurrent_uniform",
            "context_band": "MEDIUM",
            "failure_mode": "Server Overwhelmed (Connection/Timeout)",
            "oom_threshold": 32,
            "curve": [
                {
                    "concurrency": 8,
                    "throughput": 200.0,
                    "ttft_p99": 0.5,
                    "error_rate": 0.0
                },
                {
                    "concurrency": 32,
                    "throughput": 5.0,
                    "ttft_p99": 5.0,
                    "error_rate": 1.0,
                    "note": "Server Overwhelmed (Connection/Timeout)"
                }
            ]
        }
    ]
    
    fingerprint = {"gpu_name": "Test GPU", "gpu_vram_gb": 80.0}
    out_file = tmp_path / "results.md"
    
    export_markdown(results, fingerprint, str(out_file))
    
    content = out_file.read_text()
    
    # Verify Fingerprint section
    assert "| gpu_name | Test GPU |" in content
    assert "| gpu_vram_gb | 80.0 |" in content
    
    # Verify Standard Workload table row
    assert "| single_long | SHORT | 8 | 150.50 | 0.45 | 0 |" in content
    
    # Verify Cliff Finder curve rows
    assert "| concurrent_uniform | MEDIUM | 8 | 200.00 | 0.50 | 0.0% |" in content
    assert "| concurrent_uniform | MEDIUM | 32 | 5.00 | 5.00 | 100.0% (Server Overwhelmed (Connection/Timeout)) |" in content
    
    # Verify Cliff Finder Analysis section
    assert "### concurrent_uniform (MEDIUM)" in content
    assert "- **OOM / Cliff Threshold:** Concurrency 32" in content
    assert "- **Failure Mode:** Server Overwhelmed (Connection/Timeout)" in content
