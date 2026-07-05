import json
from typing import List
from inferbench.workloads.base import Request, Workload
from inferbench.config.defaults import ContextBand
from inferbench.config.schema import BenchConfig
from inferbench.workloads.single_long import FillerCorpus

class ConcurrentUniformWorkload(Workload):
    def __init__(self, config: BenchConfig):
        self.config = config
        self.corpus = FillerCorpus()

    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        # "N requests (N = concurrency band)"
        # "All requests have the same context length (the band's length)"
        # "All requests sent at offset 0.0"
        requests = []
        for i in range(concurrency):
            prompt = self.corpus.sample(seed=seed + i, target_tokens=band.value)
            requests.append(Request(
                request_id=i,
                prompt=prompt,
                max_tokens=256,
                send_at_offset=0.0,
                metadata={"band": band.name, "concurrency": concurrency}
            ))
        return requests
