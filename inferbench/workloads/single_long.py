import json
import random
import os
from typing import List
from inferbench.workloads.base import Request, Workload
from inferbench.config.defaults import ContextBand
from inferbench.config.schema import BenchConfig

class FillerCorpus:
    def __init__(self, filepath: str = None, model_name: str = "gpt-3.5-turbo"):
        if filepath is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(base_dir, "data", "prompts", "filler.jsonl")
        self.passages = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                for line in f:
                    data = json.loads(line)
                    self.passages.append(data["text"])
        
        # If no passages (or fallback), populate with a large varied synthetic set
        if not self.passages:
            words = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa"]
            for i in range(100):
                # Pseudo-random passages to ensure choice() is diverse
                passage = " ".join([words[(i + j) % len(words)] for j in range(50)])
                self.passages.append(passage)

        self.tokenizer_func = None
        self.decode_func = None
        
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
            self.tokenizer_func = enc.encode
            self.decode_func = enc.decode
        except ImportError:
            raise ImportError("Please install tiktoken: pip install tiktoken")

    def sample(self, seed: int, target_tokens: int) -> str:
        rng = random.Random(seed)
        
        # Start building words until we have enough to cover the token count
        # We overshoot significantly because a word is multiple tokens
        overshoot_words = int(target_tokens * 1.5) + 100
        words = []
        while len(words) < overshoot_words:
            words.extend(rng.choice(self.passages).split())
            
        full_text = " ".join(words)
        
        # Exact tokenization truncation
        tokens = self.tokenizer_func(full_text)
        truncated_tokens = tokens[:target_tokens]
        return self.decode_func(truncated_tokens)

class SingleLongWorkload(Workload):
    def __init__(self, config: BenchConfig):
        self.config = config
        self.corpus = FillerCorpus()

    def schedule(self, seed: int, band: ContextBand, concurrency: int) -> List[Request]:
        # "1 request at a time, 5 repeats per context band"
        # Since the framework asks for a `concurrency` parameter, we just generate the schedule
        # but single_long always uses concurrency = 1 (we just schedule them sequentially).
        # Wait, the spec says "5 repeats per context band".
        requests = []
        for repeat_index in range(5):
            prompt = self.corpus.sample(seed=seed + repeat_index, target_tokens=band.value)
            send_at_offset = repeat_index * 0.1
            requests.append(Request(
                request_id=repeat_index,
                prompt=prompt,
                max_tokens=256,
                send_at_offset=send_at_offset,
                metadata={"repeat": repeat_index, "band": band.name}
            ))
        return requests
