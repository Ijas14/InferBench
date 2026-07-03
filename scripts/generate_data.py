import os
import json
import random

def generate_filler():
    print("Generating filler.jsonl...")
    words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "artificial", "intelligence", "server", "benchmark", "context", "throughput", "latency"]
    with open("inferbench/data/prompts/filler.jsonl", "w") as f:
        for _ in range(10000):
            trunc_len = random.randint(500, 2000)
            passage = " ".join(random.choices(words, k=trunc_len))
            f.write(json.dumps({"text": passage}) + "\n")
    print("Generated 10000 filler passages.")

def generate_needles():
    print("Generating niah_needles.jsonl...")
    with open("inferbench/data/eval_sets/niah_needles.jsonl", "w") as f:
        for _ in range(200):
            magic_num = random.randint(1000000, 9999999)
            text = f"The magic number is {magic_num}."
            f.write(json.dumps({"needle": text, "fact": str(magic_num)}) + "\n")
    print("Generated 200 needles.")

def generate_longbench():
    print("Generating longbench_subset.jsonl...")
    tasks = ["narrativeqa", "qmsum", "triviaqa", "lsht", "passageretrieval"]
    with open("inferbench/data/eval_sets/longbench_subset.jsonl", "w") as f:
        for task in tasks:
            for _ in range(100):
                f.write(json.dumps({
                    "task": task,
                    "context": "Context for task.",
                    "input": "Question?",
                    "answers": ["Answer."]
                }) + "\n")
    print("Generated 500 LongBench samples.")

def generate_wikitext():
    print("Generating perplexity_wikitext.jsonl...")
    with open("inferbench/data/eval_sets/perplexity_wikitext.jsonl", "w") as f:
        for _ in range(1000):
            f.write(json.dumps({"text": "WikiText passage."}) + "\n")
    print("Generated 1000 wikitext samples.")

def generate_agent_traces():
    print("Generating agent_session_trace.jsonl...")
    with open("inferbench/data/prompts/agent_session_trace.jsonl", "w") as f:
        for s_id in range(100):
            session = []
            for t_id in range(10):
                session.append({
                    "turn": t_id,
                    "user_message": f"User message turn {t_id}.",
                    "expected_response": f"Assistant response turn {t_id}."
                })
            f.write(json.dumps({"session_id": s_id, "turns": session}) + "\n")
    print("Generated 100 agent traces.")

def generate_shared_prefix():
    print("Generating shared_prefix_system.txt...")
    system_prompt = "You are a helpful AI assistant. " * 500
    with open("inferbench/data/prompts/shared_prefix_system.txt", "w") as f:
        f.write(system_prompt)
    print("Generated shared_prefix_system.txt")

if __name__ == "__main__":
    os.makedirs("inferbench/data/prompts", exist_ok=True)
    os.makedirs("inferbench/data/eval_sets", exist_ok=True)
    generate_filler()
    generate_needles()
    generate_shared_prefix()
    generate_agent_traces()
    generate_wikitext()
    generate_longbench()
    print("Data generation complete.")
