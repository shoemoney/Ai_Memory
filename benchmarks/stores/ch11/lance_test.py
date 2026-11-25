import sys
import lancedb
from lancedb.index import FTS

db = lancedb.connect("./lance-data")
if sys.argv[1] == "write":
    t = db.create_table("memories", data=[
        {"id": 1, "text": "agent memory databases",
         "vector": [1., 0., 0., 0.]},
        {"id": 2, "text": "Paris travel plans",
         "vector": [0., 1., 0., 0.]},
    ])
    t.create_index("text", config=FTS())
    sys.exit(0)
t = db.open_table("memories")
rows = t.search([1., 0., 0., 0.]).limit(2).to_list()
assert [r["id"] for r in rows] == [1, 2]
for r in rows:
    print("vector", r["id"], r["_distance"])
rows = t.search("memory", query_type="fts").limit(2).to_list()
assert [r["id"] for r in rows] == [1]
for r in rows:
    print("fts", r["id"], r["_score"])
