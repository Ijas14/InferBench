import pytest
import json
from unittest.mock import patch, MagicMock
from inferbench.config.schema import BenchConfig, TargetConfig, ModelConfig, HardwareConfig
from inferbench.adapters.openai_api import OpenAIAdapter
from inferbench.workloads.base import Request
import requests

@pytest.fixture
def config():
    return BenchConfig(
        target=TargetConfig(endpoint="http://localhost:8000/v1", model="test-model", api_style="openai_chat"),
        model=ModelConfig(context_window=32000),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=[], bands=[], concurrencies=[], seeds=[]
    )

@pytest.fixture
def adapter(config):
    return OpenAIAdapter(config)

def test_vllm_sse_format_and_empty_chunk(adapter):
    """
    Tests exact vLLM SSE streaming format including:
    1. A role-only first chunk (should NOT set first_token_time)
    2. Delta content parsing
    3. The [DONE] marker
    4. Usage statistics parsing
    """
    req = Request(request_id=1, prompt="Hello", max_tokens=10, send_at_offset=0.0, metadata={})
    
    mock_chunks = [
        b'data: {"id":"chatcmpl-1","choices":[{"index":0,"delta":{"role":"assistant"},"logprobs":null,"finish_reason":null}]}',
        b'data: {"id":"chatcmpl-1","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}',
        b'data: {"id":"chatcmpl-1","choices":[{"index":0,"delta":{"content":" world"},"logprobs":null,"finish_reason":null}]}',
        b'data: {"id":"chatcmpl-1","choices":[],"usage":{"prompt_tokens":1,"total_tokens":3,"completion_tokens":2}}',
        b'data: [DONE]'
    ]
    
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = mock_chunks
        mock_post.return_value = mock_resp
        
        response = adapter.send(req)
        
        assert response.text == "Hello world"
        assert response.output_tokens == 2
        # Verify first_token_time was set
        assert response.first_token_time is not None
        assert response.complete_time is not None
        assert len(response.token_times) == 2 # 2 chunks with actual content

def test_400_error_json_extraction(adapter):
    """
    Tests that HTTP 400 errors with JSON bodies correctly extract the error message
    into the Response.error field without raising an exception.
    """
    req = Request(request_id=2, prompt="Too long", max_tokens=10, send_at_offset=0.0, metadata={})
    
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.reason = "Bad Request"
        mock_resp.json.return_value = {
            "error": {
                "message": "This model's maximum context length is 262144 tokens. However, your request has 262145 tokens.",
                "type": "invalid_request_error"
            }
        }
        err = requests.exceptions.HTTPError("400 Bad Request", response=mock_resp)
        mock_resp.raise_for_status.side_effect = err
        mock_post.return_value = mock_resp
        
        response = adapter.send(req)
        
        assert response.error is not None
        assert "maximum context length is 262144 tokens" in response.error
        assert response.output_tokens == 0
