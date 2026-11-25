"""Drop-in SentenceTransformer that sends encode() to the model host's embedding server (see embed_server.py).
Only the calls BEAM makes are supported: encode(texts, normalize_embeddings=, convert_to_tensor=, ...)."""
import json, os, urllib.request
import numpy as np

ENDPOINT = os.environ.get("EMBED_ENDPOINT", "http://127.0.0.1:39984/embed")

class RemoteST:
    def __init__(self, model_name_or_path, device=None, **kw):
        self.name = str(model_name_or_path).replace("./models/", "")
    def encode(self, texts, normalize_embeddings=False, convert_to_tensor=False, batch_size=32, **kw):
        single = isinstance(texts, str)
        texts = [texts] if single else list(texts)
        out = []
        for i in range(0, len(texts), 64):
            body = json.dumps({"model": self.name, "texts": texts[i:i + 64], "normalize": bool(normalize_embeddings)}).encode()
            req = urllib.request.Request(ENDPOINT, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                out += json.load(r)["embeddings"]
        arr = np.array(out, dtype=np.float32)
        if convert_to_tensor:
            import torch
            arr = torch.from_numpy(arr)
        return arr[0] if single else arr
