import os
from typing import List
from inferbench.workloads.base import Request, Workload
from inferbench.config.defaults import ContextBand
from inferbench.config.schema import BenchConfig
from inferbench.workloads.single_long import FillerCorpus

class SharedPrefixWorkload(Workload):
    def __init__(self, config: BenchConfig):
        self.config = config
        self.corpus = FillerCorpus()
        
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        system_path = os.path.join(base_dir, "data", "prompts", "shared_prefix_system.txt")
        if os.path.exists(system_path):
            with open(system_path, "r") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = "You are a helpful AI assistant. " * 100

    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        # "All requests share a common prefix (80% of context length)"
        # "Each request has a unique suffix (20% of context length)"
        
        # We need the prefix to be exactly 80% of band.value.
        # Approximation: we'll sample the corpus for 80% and append it to system_prompt
        # Wait, the spec says `prefix = shared_prefix_system + filler_corpus.sample(seed=fixed, target_tokens=0.8 * band_tokens)`
        # `fixed` means we don't vary the prefix across the same cell. We can just use `seed` for the prefix so it's consistent.
        
        target_prefix_tokens = int(0.8 * band.value)
        target_suffix_tokens = int(0.2 * band.value)
        
        filler_prefix = self.corpus.sample(seed=seed + 9999, target_tokens=target_prefix_tokens)
        shared_prefix = self.system_prompt + "\n\n" + filler_prefix
        
        requests = []
        for i in range(concurrency):
            suffix = self.corpus.sample(seed=seed + i, target_tokens=target_suffix_tokens)
            prompt = shared_prefix + "\n\n" + suffix
            requests.append(Request(
                request_id=i,
                prompt=prompt,
                max_tokens=256,
                send_at_offset=0.0,
                metadata={"band": band.name, "concurrency": concurrency, "workload": "shared_prefix"}
            ))
            
        return requests
