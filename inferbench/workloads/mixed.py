import random
from typing import List
from inferbench.workloads.base import Request, Workload
from inferbench.config.defaults import ContextBand, BAND_MAP
from inferbench.config.schema import BenchConfig
from inferbench.workloads.single_long import FillerCorpus

class MixedWorkload(Workload):
    def __init__(self, config: BenchConfig):
        self.config = config
        self.corpus = FillerCorpus()

    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        # "N total requests (N = concurrency band * 10)"
        # Mix: 40% short, 30% medium, 20% long, 10% extreme
        # Arrivals: Poisson process with rate = N / 60
        
        total_requests = concurrency * 10
        rng = random.Random(seed)
        requests = []
        
        current_offset = 0.0
        
        for i in range(total_requests):
            r = rng.random()
            if r < 0.4:
                req_band = ContextBand.SHORT
            elif r < 0.7:
                req_band = ContextBand.MEDIUM
            elif r < 0.9:
                req_band = ContextBand.LONG
            else:
                req_band = ContextBand.EXTREME
                
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
