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
                return fingerprint
    except Exception:
        pass
        
    try:
        # Try rocm-smi
        result = subprocess.run(
            ['rocm-smi', '--showproductname', '--showdriverversion', '--showmeminfo', 'vram', '--json'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            rocm_data = json.loads(result.stdout)
            card_key = next((k for k in rocm_data.keys() if k.startswith("card")), None)
            if card_key:
                card = rocm_data[card_key]
                # Try both capitalizations just in case different ROCm versions differ
                gpu_name = card.get("Card Series", card.get("Card series", "Unknown"))
                
                # If we get garbage, try GFX Version which is highly reliable for AMD
                if gpu_name in ["Unknown", "N/A", ""]:
                    gfx = card.get("GFX Version", "")
                    if gfx == "gfx942":
                        gpu_name = "AMD Instinct MI300X"
                    elif gfx == "gfx941":
                        gpu_name = "AMD Instinct MI300A"
                    elif gfx == "gfx90a":
                        gpu_name = "AMD Instinct MI250X"
                    else:
                        gpu_name = card.get("Card Model", "Unknown")
                        if gpu_name in ["Unknown", "N/A", ""]:
                            gpu_name = gfx or "Unknown"

                fingerprint["gpu_name"] = gpu_name
                
                # Driver version is usually at the root "system" level
                if "system" in rocm_data:
                    fingerprint["gpu_driver"] = rocm_data["system"].get("Driver version", "Unknown")
                else:
                    fingerprint["gpu_driver"] = card.get("Driver version", "Unknown")
                
                vram_bytes = card.get("VRAM Total Memory (B)")
                if vram_bytes and str(vram_bytes).isdigit():
                    fingerprint["gpu_vram_gb"] = round(int(vram_bytes) / (1024**3))
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
