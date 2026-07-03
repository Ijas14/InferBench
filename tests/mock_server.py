import http.server
import socketserver
import json
import time

class MockOpenAIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/metrics":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"gpu_memory_used_bytes": 1000000}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/completions":
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length))
            
            # Simulate processing delay
            time.sleep(0.05)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {
                "id": "cmpl-mock",
                "object": "text_completion",
                "created": int(time.time()),
                "model": body.get("model", "mock-model"),
                "choices": [
                    {
                        "text": "This is a mock response.",
                        "index": 0,
                        "logprobs": None,
                        "finish_reason": "length"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(body.get("prompt", "").split()),
                    "completion_tokens": body.get("max_tokens", 256),
                    "total_tokens": len(body.get("prompt", "").split()) + body.get("max_tokens", 256)
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    PORT = 30001
    with ThreadedTCPServer(("", PORT), MockOpenAIHandler) as httpd:
        print("Mock server running at port", PORT)
        httpd.serve_forever()
