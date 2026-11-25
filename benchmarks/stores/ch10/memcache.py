import hashlib, json, struct, sys, time, uuid
from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheError, MemcacheServerError

options = dict(default_noreply=False, connect_timeout=1, timeout=1, ignore_exc=True)
c = Client(("127.0.0.1", 39100), **options)
c2 = Client(("127.0.0.1", 39101), **options)

def response_key(version):
    fields = ["demo-model-v1", {"temperature": 0}, "FAQ hours?", "public", version]
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()

if sys.argv[-1] == "read":
    assert c.get(response_key("faq-v1")) == b"summary"
    assert c.get("month") == b"retained"
    print("fresh-process read OK")
    c.close()
    c2.close()
    sys.exit(0)
print("set/get TTL", c.set(response_key("faq-v1"), "summary", expire=60),
      c.get(response_key("faq-v1")))
assert c.get(response_key("faq-v2")) is None
print("version bump: MISS")
expiry = int(time.time()) + 31 * 24 * 60 * 60
assert c.set("month", "retained", expire=expiry)
print("absolute expiry", c.get("month"))
large_key = "large:" + uuid.uuid4().hex
try:
    c.set(large_key, b"x" * (1024 * 1024 + 1))
except MemcacheServerError as e:
    assert e.args[0] == b"object too large for cache"
    print("default rejection", type(e).__name__, str(e))
else:
    raise AssertionError("oversized item accepted")
assert c2.set("check", b"ok")
print("raised limit", c2.set(large_key, b"x" * (1024 * 1024 + 1)),
      len(c2.get(large_key)))

def embedding_cache(revision, text, compute):
    key = hashlib.sha256((revision + "\0" + text).encode()).hexdigest()
    cached = c.get(key)
    if cached is not None:
        return list(struct.unpack("<" + "f" * (len(cached) // 4), cached))
    vector = compute(text)
    try:
        if not c.set(key, struct.pack("<" + "f" * len(vector), *vector), expire=3600):
            print("cache set failed", file=sys.stderr)
    except (OSError, MemcacheError) as error:
        print("cache set failed:", error, file=sys.stderr)
    return vector

def must_not_run(text):
    raise RuntimeError("must not compute")

revision = "demo-v1:prep1:" + uuid.uuid4().hex
print("cache miss", embedding_cache(revision, "hello", lambda text: [1., 0., 0., 0.]))
assert embedding_cache(revision, "hello", must_not_run) == [1., 0., 0., 0.]
print("cache hit", embedding_cache(revision, "hello", must_not_run))
c.close()
c2.close()
