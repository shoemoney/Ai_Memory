from math import sqrt

# Synthetic vectors: demonstrate a gate, not embedding-model quality.
cached = {"query": "Cancel my order", "vector": [1., 0.],
          "scope": "tenant-a:policy-v1", "answer": "Use order cancellation."}
queries = [
    ("Please cancel the order", [0.999, 0.045], "tenant-a:policy-v1", True),
    ("Cancel my subscription", [0.98, 0.20], "tenant-a:policy-v1", False),
    ("Please cancel the order", [0.999, 0.045], "tenant-b:policy-v1", False),
]
accepted = correct = 0
checks = []
for text, vector, scope, expected in queries:
    distance = 1 - vector[0] / sqrt(sum(x*x for x in vector))
    hit = scope == cached["scope"] and distance <= 0.01  # LOWER is stricter
    checks.append(hit == expected)
    accepted += hit
    correct += hit and expected
    print(text, scope, f"distance={distance:.4f}",
          cached["answer"] if hit else "MISS: compute fresh answer")
print(f"hit precision: {correct}/{accepted}")
assert all(checks), "unexpected semantic decision"
