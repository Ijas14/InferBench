import time
import requests
from typing import Optional
from inferbench.adapters.base import ServerAdapter, Response
from inferbench.workloads.base import Request
from inferbench.config.schema import BenchConfig

class OpenAIAdapter(ServerAdapter):
    def __init__(self, config: BenchConfig):
        self.endpoint = config.target.endpoint
        self.model = config.target.model
        self.metrics_endpoint = config.target.metrics_endpoint

    def send(self, request: Request) -> Response:
        send_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "stream": False # Mock server doesn't stream yet, keeping simple for Day 1
        }
        
        try:
            res = requests.post(self.endpoint + "/completions", json=payload, timeout=600)
            res.raise_for_status()
            data = res.json()
            complete_time = time.time()
            text = ""
            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0].get("text", "")
            # For non-streaming, TTFT == complete_time
            return Response(
                request=request,
                send_time=send_time,
                first_token_time=complete_time, 
                complete_time=complete_time,
                output_tokens=data.get("usage", {}).get("completion_tokens", request.max_tokens),
                token_times=[],
                text=text
            )
        except Exception as e:
            return Response(
                request=request,
                send_time=send_time,
                first_token_time=None,
                complete_time=time.time(),
                output_tokens=0,
                token_times=[],
                error=str(e)
            )

    def health(self) -> bool:
        try:
            res = requests.get(self.endpoint.replace("/v1", "/health"), timeout=5)
            return res.status_code == 200
        except:
            return False

    def metrics(self) -> Optional[dict]:
        if not self.metrics_endpoint:
            return None
        try:
            res = requests.get(self.metrics_endpoint, timeout=5)
            return res.json()
        except:
            return None
