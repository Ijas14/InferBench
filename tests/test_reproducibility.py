import pytest
from inferbench.config.schema import BenchConfig, TargetConfig, ModelConfig, HardwareConfig
from inferbench.config.defaults import ContextBand
from inferbench.workloads.single_long import SingleLongWorkload

def test_single_long_deterministic():
    config = BenchConfig(
        target=TargetConfig(endpoint="http://localhost", model="test"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=["single_long"],
        bands=["short"],
        concurrencies=[1],
        seeds=[42]
    )
    
    w = SingleLongWorkload(config)
    s1 = w.schedule(seed=42, band=ContextBand.SHORT, concurrency=1)
    s2 = w.schedule(seed=42, band=ContextBand.SHORT, concurrency=1)
    
    assert len(s1) == 5
    assert len(s2) == 5
    for r1, r2 in zip(s1, s2):
        assert r1.request_id == r2.request_id
        assert r1.prompt == r2.prompt
        assert r1.max_tokens == r2.max_tokens
        assert r1.send_at_offset == r2.send_at_offset
        assert r1.metadata == r2.metadata

def test_single_long_different_seeds_different():
    config = BenchConfig(
        target=TargetConfig(endpoint="http://localhost", model="test"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=["single_long"],
        bands=["short"],
        concurrencies=[1],
        seeds=[42]
    )
    
    w = SingleLongWorkload(config)
    s1 = w.schedule(seed=42, band=ContextBand.SHORT, concurrency=1)
    s2 = w.schedule(seed=43, band=ContextBand.SHORT, concurrency=1)
    
    # Should be different prompts for different seeds
    assert s1[0].prompt != s2[0].prompt

from inferbench.workloads.concurrent_uniform import ConcurrentUniformWorkload
from inferbench.workloads.shared_prefix import SharedPrefixWorkload
from inferbench.workloads.mixed import MixedWorkload

def test_concurrent_uniform_deterministic():
    config = BenchConfig(
        target=TargetConfig(endpoint="http://localhost", model="test"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=[], bands=[], concurrencies=[], seeds=[]
    )
    w = ConcurrentUniformWorkload(config)
    s1 = w.schedule(seed=42, band=ContextBand.MEDIUM, concurrency=4)
    s2 = w.schedule(seed=42, band=ContextBand.MEDIUM, concurrency=4)
    
    assert len(s1) == 4
    assert [r.prompt for r in s1] == [r.prompt for r in s2]
    assert [r.send_at_offset for r in s1] == [r.send_at_offset for r in s2]

def test_shared_prefix_deterministic():
    config = BenchConfig(
        target=TargetConfig(endpoint="http://localhost", model="test"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=[], bands=[], concurrencies=[], seeds=[]
    )
    w = SharedPrefixWorkload(config)
    s1 = w.schedule(seed=1337, band=ContextBand.LONG, concurrency=8)
    s2 = w.schedule(seed=1337, band=ContextBand.LONG, concurrency=8)
    
    assert len(s1) == 8
    assert [r.prompt for r in s1] == [r.prompt for r in s2]

def test_mixed_deterministic():
    config = BenchConfig(
        target=TargetConfig(endpoint="http://localhost", model="test"),
        model=ModelConfig(context_window=32768),
        hardware=HardwareConfig(gpu="test", vram_gb=1, driver="1"),
        workloads=[], bands=[], concurrencies=[], seeds=[]
    )
    w = MixedWorkload(config)
    s1 = w.schedule(seed=999, band=ContextBand.SHORT, concurrency=4)
    s2 = w.schedule(seed=999, band=ContextBand.SHORT, concurrency=4)
    
    # Concurrency 4 means 40 requests total for mixed workload
    assert len(s1) == 40
    assert [r.prompt for r in s1] == [r.prompt for r in s2]
    assert [r.send_at_offset for r in s1] == [r.send_at_offset for r in s2]
