import sys
from qdrant_client import QdrantClient, models

c = QdrantClient(url="http://127.0.0.1:39110")
if sys.argv[1] == "write":
    c.create_collection(
        "memories",
        vectors_config=models.VectorParams(
            size=4, distance=models.Distance.COSINE),
    )
    c.create_payload_index("memories", "user_id",
        field_schema=models.KeywordIndexParams(
            type="keyword", is_tenant=True), wait=True)
    c.upsert("memories", wait=True, points=[
        models.PointStruct(id=1, vector=[1., 0., 0., 0.],
            payload={"user_id": "alice", "content": "likes databases"}),
        models.PointStruct(id=2, vector=[0., 1., 0., 0.],
            payload={"user_id": "bob"}),
    ])
    sys.exit(0)
only_alice = models.Filter(must=[models.FieldCondition(
    key="user_id", match=models.MatchValue(value="alice"))])
res = c.query_points("memories", query=[1., 0., 0., 0.],
    query_filter=only_alice, with_payload=True, limit=3)
assert [p.id for p in res.points] == [1]
for p in res.points:
    print(p.id, p.score, p.payload)
