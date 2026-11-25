"""Serve hs-decide-1-flash with per-request timing.

Wraps the vendor's Transformers server (hindsight_decision.server.app). Each /v1/systemone
request appends one JSON line: total wall seconds seen by the server (parse + compute +
serialize), compute seconds inside DecisionModel.answer, and input tokens from the response.
"""
import argparse, json, os, time, threading
import torch
from hindsight_decision.model import DecisionModel
from hindsight_decision.server import app
from starlette.middleware.base import BaseHTTPMiddleware

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--port", type=int, default=39981)
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--api-key", default="gap-local")
p.add_argument("--device", default="cpu")
p.add_argument("--dtype", default=None)
p.add_argument("--threads", type=int, default=8)
p.add_argument("--log", required=True)
p.add_argument("--dump", default=None, help="append each request body as a JSON line (scratch only)")
p.add_argument("--max-request-tokens", type=int, default=None)
a = p.parse_args()
torch.set_num_threads(a.threads)
decider = DecisionModel.from_pretrained(a.model, device=a.device, dtype=a.dtype,
                                        max_request_tokens=a.max_request_tokens)
lock = threading.Lock()
inner = decider.answer
last = {}  # the server answers one request at a time, so a plain dict is safe

def timed_answer(request):
    t = time.perf_counter()
    out = inner(request)
    last['compute'] = time.perf_counter() - t
    last['tokens'] = (out.get("usage") or {}).get("input_tokens")
    return out
decider.answer = timed_answer

server = app(decider, a.model, None, a.api_key)

class Timing(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        t = time.perf_counter()
        if a.dump and request.url.path == "/v1/systemone":
            body = await request.body()
            with lock, open(a.dump, "ab") as f: f.write(body.replace(b"\n", b" ") + b"\n")
        resp = await call_next(request)
        if request.url.path == "/v1/systemone":
            rec = {"t": time.time(), "wall_s": time.perf_counter() - t, "status": resp.status_code,
                   "compute_s": last.get("compute"), "input_tokens": last.get("tokens")}
            with lock, open(a.log, "a") as f:
                f.write(json.dumps(rec) + "\n")
        return resp
server.add_middleware(Timing)
import uvicorn
print(f"{a.model} on {decider.device} {decider.dtype} threads={a.threads}", flush=True)
uvicorn.run(server, host=a.host, port=a.port, log_level="warning")
