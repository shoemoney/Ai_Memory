import sys
import chromadb

c = chromadb.PersistentClient(path="./chroma-data")
t = c.get_or_create_collection("memories", embedding_function=None)
if sys.argv[1] == "write":
    t.add(
        ids=["1", "2"],
        documents=["likes databases", "travel to Paris"],
        embeddings=[[1., 0., 0., 0.], [0., 1., 0., 0.]],
        metadatas=[{"user_id": "alice"}, {"user_id": "bob"}],
    )
    sys.exit(0)
out = t.query(
    query_embeddings=[[1., 0., 0., 0.]], n_results=2,
    where={"user_id": "alice"}, include=["documents", "distances"],
)
assert out["ids"] == [["1"]]
print(out["documents"], out["distances"])
