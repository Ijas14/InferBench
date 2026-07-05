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
        
        from urllib.parse import urlparse
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")
        if parsed.hostname in ["169.254.169.254", "metadata.google.internal", "metadata"]:
            raise ValueError(f"Blocked attempt to access cloud metadata endpoint: {parsed.hostname}")

        
        is_chat = (self.api_style == "openai_chat")
        
        if is_chat:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": 0.0,
                "stream": True,
                "stream_options": {"include_usage": True}
            }
            url = self.endpoint + "/chat/completions"
        else:
            payload = {
                "model": self.model,
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "temperature": 0.0,
                "stream": True,
                "stream_options": {"include_usage": True}
            }
            url = self.endpoint + "/completions"
            
        try:
            res = requests.post(url, json=payload, timeout=600, stream=True)
            res.raise_for_status()
            
            import json
            first_token_time = None
            complete_time = None
            output_tokens = 0
            token_times = []
            text_chunks = []
            
            for line in res.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str.strip() == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data_str)
                            now = time.time()
                            
                            if first_token_time is None:
                                first_token_time = now
                                
                            token_times.append(now)
                            
                            if is_chat:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                chunk_text = delta.get("content", "")
                            else:
                                chunk_text = chunk.get("choices", [{}])[0].get("text", "")
                                
                            if chunk_text:
                                text_chunks.append(chunk_text)
                                output_tokens += 1
                                
                            if "usage" in chunk and chunk["usage"]:
                                usage_tokens = chunk["usage"].get("completion_tokens")
                                if usage_tokens is not None:
                                    output_tokens = usage_tokens
                                    
                        except json.JSONDecodeError:
                            pass
                            
            complete_time = time.time()
            text = "".join(text_chunks)
                    
            return Response(
                request=request,
                send_time=send_time,
                first_token_time=first_token_time, 
                complete_time=complete_time,
                output_tokens=output_tokens,
                token_times=token_times,
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
