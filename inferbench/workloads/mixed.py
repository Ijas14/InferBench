import random
from typing import List
from inferbench.workloads.base import Request, Workload
from inferbench.config.defaults import ContextBand, BAND_MAP
from inferbench.config.schema import BenchConfig
from inferbench.workloads.single_long import FillerCorpus

class MixedWorkload(Workload):
    def __init__(self, config: BenchConfig, max_model_len: int = None, max_tokens: int = 256):
        self.config = config
        self.max_model_len = max_model_len
        self.max_tokens = max_tokens
        self.corpus = FillerCorpus()

    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        # "N total requests (N = concurrency band * 3)"
        # Mix: 40% short, 30% medium, 20% long, 10% extreme
        # Arrivals: Poisson process with rate = N / 60
        
        total_requests = concurrency * 3
        rng = random.Random(seed)
        requests = []
        
        available_bands = []
        weights = []
        limit = self.max_model_len if self.max_model_len else float('inf')
        
        if limit >= ContextBand.SHORT.value + self.max_tokens:
            available_bands.append(ContextBand.SHORT); weights.append(0.4)
        if limit >= ContextBand.MEDIUM.value + self.max_tokens:
            available_bands.append(ContextBand.MEDIUM); weights.append(0.3)
        if limit >= ContextBand.LONG.value + self.max_tokens:
            available_bands.append(ContextBand.LONG); weights.append(0.2)
        if limit >= ContextBand.EXTREME.value + self.max_tokens:
            available_bands.append(ContextBand.EXTREME); weights.append(0.1)
            
        if not available_bands:
            # Fallback if the limit is insanely small
            available_bands.append(ContextBand.SHORT)
            weights.append(1.0)
        
        current_offset = 0.0
        
        for i in range(total_requests):
            req_band = rng.choices(available_bands, weights=weights, k=1)[0]
                
            # Cap the band to the requested max band (to respect hardware constraints)
            if req_band.value > band.value:
                req_band = band
                
            prompt = self.corpus.sample(seed=seed + i, target_tokens=req_band.value)
            
            # Poisson arrival offset: exponential distribution of inter-arrival times
            # mean inter-arrival time = 1.0 / rate = 60.0 / total_requests
            rate = total_requests / 60.0
            inter_arrival = rng.expovariate(rate) if rate > 0 else 0
            current_offset += inter_arrival
            
            requests.append(Request(
                request_id=i,
                prompt=prompt,
                max_tokens=256,
                send_at_offset=current_offset,
                metadata={"band": req_band.name, "concurrency": concurrency, "workload": "mixed"}
            ))
            
        return requests
