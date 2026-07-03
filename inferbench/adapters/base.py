from typing import Protocol, Optional
from dataclasses import dataclass
from inferbench.workloads.base import Request

@dataclass
class Response:
    request: Request
    send_time: float
    first_token_time: Optional[float]
    complete_time: float
    output_tokens: int
    token_times: list[float]
    text: str = ""
    error: Optional[str] = None

class ServerAdapter(Protocol):
    def send(self, request: Request) -> Response:
        ...

    def health(self) -> bool:
        ...

    def metrics(self) -> Optional[dict]:
        ...
