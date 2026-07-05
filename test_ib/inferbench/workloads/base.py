from dataclasses import dataclass
from typing import Protocol, List
from inferbench.config.defaults import ContextBand
from inferbench.config.schema import BenchConfig

@dataclass(frozen=True)
class Request:
    request_id: int
    prompt: str
    max_tokens: int
    send_at_offset: float
    metadata: dict

class Workload(Protocol):
    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        ...
