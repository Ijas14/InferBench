#!/bin/bash
set -e

echo "Starting llama.cpp server with Qwen2.5-0.5B..."
# Start llama-server in the background with the 0.5B model, max 16k context, and bind to port 8080
GGML_VULKAN_DEVICE=1 ./llama.cpp/build/bin/llama-server \
  -m llama.cpp/models/qwen2.5-0.5b-instruct-q8_0.gguf \
  -c 32768 \
  -ngl 99 \
  --port 8081 \
  --parallel 4 \
  > llama_server.log 2>&1 &

SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

echo "Waiting for server to initialize (this takes ~10-20 seconds on CPU)..."
# Simple wait loop until port 8081 is reachable
while ! curl -s http://localhost:8081/health > /dev/null; do
    sleep 2
done

echo "Server is ready! Launching inferbench wizard..."
echo "================================================"
echo "WARNING: Port 8000 is taken by Lemonade App!"
echo "When asked for the endpoint, you MUST TYPE:"
echo "http://localhost:8081/v1"
echo "================================================"

python -m inferbench wizard

echo "Cleaning up..."
kill $SERVER_PID
echo "Done."
