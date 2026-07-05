import json
from inferbench.config.schema import BenchConfig
from inferbench.config.defaults import ContextBand
from inferbench.workloads.concurrent_uniform import ConcurrentUniformWorkload
from inferbench.adapters.openai_api import OpenAIAdapter
from inferbench.cliff.finder import find_cliff

def test_cliff_finder():
    config = BenchConfig.from_yaml("configs/mock_test.yaml")
    
    # We want to force a latency spike or error to test the cliff finder logic.
    # The mock server always takes ~50ms, so P99 ttft will always be ~50ms.
    # This means it will never hit the 10x latency spike or error out unless we mock the adapter.
    
    class SpikeMockAdapter(OpenAIAdapter):
        def __init__(self, config):
            super().__init__(config)
            self.call_count = 0
            
        def send(self, request):
            self.call_count += 1
            c = request.metadata.get("concurrency", 1)
            
            from inferbench.adapters.base import Response
            
            import time
            now = time.time()
            # Simulate basic response
            resp = Response(
                request=request,
                send_time=now,
                first_token_time=now + 0.05,
                complete_time=now + 0.05 + (100 * 0.01),
                output_tokens=100,
                token_times=[],
                error=None,
                text="Mocked response"
            )
            
            if c >= 32:
                # Trigger error rate > 10%
                resp.error = "Simulated OOM"
                resp.output_tokens = 0
            
            return resp

    adapter = SpikeMockAdapter(config)
    workload = ConcurrentUniformWorkload(config)
    
    print("Running Cliff Finder test on SHORT band...")
    result = find_cliff(
        adapter=adapter,
        workload=workload,
        context_band=ContextBand.SHORT,
        concurrency_ladder=[1, 8, 32, 128],
        seed=42
    )
    
    print(json.dumps(result, indent=2))
    
    assert result["oom_threshold"] == 32
    assert "Simulated OOM" in result["failure_mode"]
    print("Cliff Finder test passed!")

def test_cliff_finder_reproducibility():
    config = BenchConfig.from_yaml("configs/mock_test.yaml")
    
    class DetMockAdapter(OpenAIAdapter):
        def __init__(self, config):
            super().__init__(config)
            
        def send(self, request):
            c = request.metadata.get("concurrency", 1)
            from inferbench.adapters.base import Response
            
            # Pure deterministic response based on concurrency to trigger a cliff predictably
            resp = Response(
                request=request,
                send_time=0.0,
                first_token_time=0.05 if c < 32 else 0.5, # 10x spike at 32
                complete_time=0.1 if c < 32 else 0.6,
                output_tokens=100,
                token_times=[],
                error=None,
                text="Mocked"
            )
            return resp

    adapter = DetMockAdapter(config)
    workload = ConcurrentUniformWorkload(config)
    
    res1 = find_cliff(adapter, workload, ContextBand.SHORT, [1, 8, 32], seed=999)
    res2 = find_cliff(adapter, workload, ContextBand.SHORT, [1, 8, 32], seed=999)
    
    assert res1["oom_threshold"] == res2["oom_threshold"]
    assert res1["failure_mode"] == res2["failure_mode"]
    for c1, c2 in zip(res1["curve"], res2["curve"]):
        assert c1["concurrency"] == c2["concurrency"]
        assert c1["error_rate"] == c2["error_rate"]
        assert c1["ttft_p99"] == c2["ttft_p99"]

if __name__ == "__main__":
    test_cliff_finder()
