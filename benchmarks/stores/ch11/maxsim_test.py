import sys
from qdrant_client import QdrantClient, models

c = QdrantClient(url="http://127.0.0.1:39110")
if sys.argv[1] == "write":
    c.create_collection(
        "pages",
        vectors_config={
            "dense": models.VectorParams(size=4, distance=models.Distance.COSINE),
            "patches": models.VectorParams(
                size=4, distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM),
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
    )
    # Each page has 16 patch vectors; every vector has 4 dimensions.
    page_a = [[1., 0., 0., 0.], [0., 1., 0., 0.]] * 8
    page_b = [[0., 0., 1., 0.], [0., 0., 0., 1.]] * 8
    c.upsert("pages", wait=True, points=[
        models.PointStruct(id=101,
            vector={"dense": [1., 0., 0., 0.], "patches": page_a},
            payload={"page_id": "page-a"}),
        models.PointStruct(id=102,
            vector={"dense": [0., 0., 1., 0.], "patches": page_b},
            payload={"page_id": "page-b"}),
    ])
    sys.exit(0)
saved = c.retrieve("pages", ids=[101, 102], with_vectors=True)
assert len(saved) == 2
assert all(len(p.vector["patches"]) == 16 for p in saved)
query = [[1., 0., 0., 0.], [0., 1., 0., 0.]]
hits = c.query_points("pages", query=query, using="patches", limit=2,
    prefetch=models.Prefetch(query=[1., 0., 0., 0.], using="dense", limit=2),
    search_params=models.SearchParams(exact=True),
    with_payload=True).points
assert [p.id for p in hits] == [101, 102]
assert [round(p.score, 6) for p in hits] == [2., 0.]
for p in hits:
    print(p.payload["page_id"], p.score)
c.close()
