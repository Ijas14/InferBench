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
        self.api_style = config.target.api_style
        self.metrics_endpoint = config.target.metrics_endpoint

    def send(self, request: Request) -> Response:
        send_time = time.time()
        
        is_chat = (self.api_style == "openai_chat")
        
        if is_chat:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "stream": False
            }
            url = self.endpoint + "/chat/completions"
        else:
            payload = {
                "model": self.model,
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "stream": False
            }
            url = self.endpoint + "/completions"
            
        try:
            res = requests.post(url, json=payload, timeout=600)
            res.raise_for_status()
            data = res.json()
            complete_time = time.time()
            text = ""
            if "choices" in data and len(data["choices"]) > 0:
                if is_chat:
                    text = data["choices"][0].get("message", {}).get("content", "")
                else:
                    text = data["choices"][0].get("text", "")
                    
            return Response(
                request=request,
                send_time=send_time,
                first_token_time=complete_time, 
                complete_time=complete_time,
                output_tokens=data.get("usage", {}).get("completion_tokens", request.max_tokens),
                token_times=[],
                text=text
            )
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_msg = f"{e.response.status_code} {e.response.reason}: {error_json['error']['message']}"
            except Exception:
                pass
                
            if e.response.status_code in [400, 404]:
                raise ValueError(f"FATAL CONFIGURATION ERROR: The server rejected the request with a {e.response.status_code}. Details: {error_msg}")
            return Response(
                request=request,
                send_time=send_time,
                first_token_time=None,
                complete_time=time.time(),
                output_tokens=0,
                token_times=[],
                error=error_msg
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

    def get_max_model_len(self) -> Optional[int]:
        try:
            # Assumes endpoint is /v1, so models endpoint is /v1/models
            url = self.endpoint.rstrip("/")
            if url.endswith("/v1"):
                url += "/models"
            else:
                url += "/v1/models"
                
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for m in data.get("data", []):
                    if m.get("id") == self.model and "max_model_len" in m:
                        return m.get("max_model_len")
        except Exception:
            pass
        return None

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
