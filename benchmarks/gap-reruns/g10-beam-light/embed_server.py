"""Tiny embedding server for the model host: POST /embed {"model": str, "texts": [str], "normalize": bool} -> {"embeddings": [[...]]}.
Models load lazily into HF_HOME. Binds to localhost only."""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from sentence_transformers import SentenceTransformer
models, lock = {}, threading.Lock()
def get(name):
    with lock:
        if name not in models: models[name] = SentenceTransformer(name, device="cpu")
        return models[name]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        m = get(req["model"])
        emb = m.encode(req["texts"], normalize_embeddings=req.get("normalize", False), batch_size=32, show_progress_bar=False)
        body = json.dumps({"embeddings": emb.tolist()}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
