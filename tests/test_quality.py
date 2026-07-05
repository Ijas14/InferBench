import pytest
import os
import json
from unittest.mock import MagicMock, patch
from inferbench.config.defaults import ContextBand
from inferbench.metrics.quality import evaluate_niah
from inferbench.adapters.base import ServerAdapter, Response
from inferbench.workloads.base import Request

class MockQualityAdapter(ServerAdapter):
    def __init__(self):
        self.requests_seen = []
        self.fail_depth = None
        
    def send(self, request: Request) -> Response:
        self.requests_seen.append(request)
        
        depth = request.metadata.get("depth", 0.0)
        
        # We will parse the prompt to verify the needle is actually inserted.
        # The quality.py fallback needles look like: "The magic number is {i}."
        # And facts look like: "{i}"
        # Let's extract the fact from the prompt by finding the needle.
        fact = "0"
        if "magic number is " in request.prompt:
            idx = request.prompt.find("magic number is ") + len("magic number is ")
            fact = request.prompt[idx:request.prompt.find(".", idx)]
            
        # Optional: Simulate a failure at a specific depth
        if self.fail_depth and abs(depth - self.fail_depth) < 0.01:
            fact = "wrong_answer"
            
        return Response(
            request=request,
            send_time=0.0,
            first_token_time=0.1,
            complete_time=0.2,
            output_tokens=10,
            token_times=[],
            text=fact,
            error=None
        )
        
    def health(self) -> bool: return True
    def metrics(self) -> dict: return {}
    def get_max_model_len(self) -> int: return 32000


def test_niah_needle_insertion_depths():
    """
    Tests that the evaluate_niah function actually inserts needles
    at the correct relative depths in the prompt, and computes accuracy correctly.
    """
    adapter = MockQualityAdapter()
    
    # Mock FillerCorpus to avoid tiktoken downloading
    mock_corpus = MagicMock()
    mock_corpus.sample.return_value = "This is some dummy haystack text to pad out the context length so we can test the needle insertion." * 10
    
    # Run NIAH with a very small samples count for speed
    with patch('inferbench.metrics.quality.FillerCorpus', return_value=mock_corpus):
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False # Force fallback needles
            
            result = evaluate_niah(adapter, ContextBand.SHORT, samples_per_depth=2)
        
    assert result["workload"] == "niah"
    assert result["context_band"] == "SHORT"
    assert result["needle_accuracy"] == 1.0 # The mock adapter returns the correct fact always
    
    # We should have tested 4 depths * 2 samples = 8 requests
    assert len(adapter.requests_seen) == 8
    
    # Verify the insertion logic placed the needle approximately at the right depth
    # The prompt ends with "\n\nQuestion: What is the magic number?\nAnswer:"
    for req in adapter.requests_seen:
        depth = req.metadata.get("depth")
        words = req.prompt.split()
        
        # Find the needle in the words list
        # We look for "magic" which is part of "The magic number is X."
        needle_idx = -1
        for i, w in enumerate(words):
            if "magic" in w and "number" in words[min(i+1, len(words)-1)]:
                # Avoid the question at the end
                if "Question:" not in words[max(0, i-2):i]:
                    needle_idx = i
                    break
                    
        assert needle_idx != -1, f"Needle not found in prompt for depth {depth}"
        
        # Expected insertion index was int(len(words) * depth)
        # However, len(words) is slightly larger because we appended the question.
        # But during insertion, it was based on the haystack size.
        # The needle itself is 5 words ("The", "magic", "number", "is", "X.")
        # So the actual relative position should be roughly close to the depth.
        
        relative_pos = needle_idx / len(words)
        
        if depth == 0.25:
            assert 0.15 <= relative_pos <= 0.35
        elif depth == 0.50:
            assert 0.40 <= relative_pos <= 0.60
        elif depth == 0.75:
            assert 0.65 <= relative_pos <= 0.85
        elif depth == 1.0:
            # depth 1.0 inserts at len(words) - 1 of the haystack, then the question is appended
            # so it should be near the very end, just before the question
            assert relative_pos >= 0.85


def test_niah_accuracy_calculation():
    """
    Tests that evaluate_niah correctly aggregates accuracy when some depths fail.
    """
    adapter = MockQualityAdapter()
    adapter.fail_depth = 0.50 # Fail all samples at 50% depth
    
    mock_corpus = MagicMock()
    mock_corpus.sample.return_value = "This is some dummy haystack text to pad out the context length so we can test the needle insertion." * 10
    
    with patch('inferbench.metrics.quality.FillerCorpus', return_value=mock_corpus):
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False # Force fallback needles
            
            result = evaluate_niah(adapter, ContextBand.SHORT, samples_per_depth=5)
        
    # Depths: 0.25 (100%), 0.50 (0%), 0.75 (100%), 1.0 (100%)
    # Overall: 15 / 20 = 75%
    
    assert result["needle_accuracy"] == 0.75
    assert result["depth_scores"]["depth_25"] == 1.0
    assert result["depth_scores"]["depth_50"] == 0.0
    assert result["depth_scores"]["depth_75"] == 1.0
    assert result["depth_scores"]["depth_100"] == 1.0
