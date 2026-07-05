import platform
import os
import json
import subprocess
from typing import Dict, Any

def get_hardware_fingerprint() -> Dict[str, Any]:
    """
    Captures the underlying hardware and software fingerprint to ensure 
    benchmark results are citeable and comparable.
    """
    fingerprint = {
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "cpu": platform.processor() or "Unknown CPU",
    }
    
    # RAM
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'MemTotal' in line:
                    kb = int(line.split()[1])
                    fingerprint["ram_gb"] = round(kb / (1024 * 1024), 2)
                    break
    except:
        fingerprint["ram_gb"] = "Unknown"

    # GPU
    fingerprint["gpu_name"] = "Unknown"
    fingerprint["gpu_vram_gb"] = "Unknown"
    fingerprint["gpu_driver"] = "Unknown"
    
    try:
        # Try nvidia-smi
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.split(',')]
            if len(parts) >= 3:
                fingerprint["gpu_name"] = parts[0]
                fingerprint["gpu_vram_gb"] = round(int(parts[1]) / 1024, 2)
                fingerprint["gpu_driver"] = parts[2]
        else:
            # Try rocm-smi
            result = subprocess.run(
                ['rocm-smi', '--showproductname', '--showdriverversion', '--json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                rocm_data = json.loads(result.stdout)
                if "card0" in rocm_data:
                    card = rocm_data["card0"]
                    fingerprint["gpu_name"] = card.get("Card series", "Unknown")
                    fingerprint["gpu_driver"] = card.get("Driver version", "Unknown")
                    # VRAM stays "Unknown" for v0.1.2 unless we add --showmeminfo
    except Exception:
        pass

    # Software versions
    try:
        import torch
        fingerprint["pytorch_version"] = torch.__version__
    except ImportError:
        fingerprint["pytorch_version"] = "Not Installed"
        
    try:
        import sglang
        fingerprint["sglang_version"] = sglang.__version__
    except ImportError:
        fingerprint["sglang_version"] = "Not Installed"
        
    try:
        import vllm
        fingerprint["vllm_version"] = vllm.__version__
    except ImportError:
        fingerprint["vllm_version"] = "Not Installed"

    return fingerprint
