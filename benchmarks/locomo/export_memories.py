#!/usr/bin/env python3
"""Export the complete persisted store after the benchmark releases its lock."""
import argparse
import json
from pathlib import Path
from qdrant_client import QdrantClient, models


def export(lab, out):
    client = QdrantClient(path=str(lab / "qdrant"))
    memories = []
    offset = None
    while True:
        points, offset = client.scroll(
            "locomo", limit=1000, offset=offset, with_payload=True, with_vectors=False,
            scroll_filter=models.Filter(must=[models.FieldCondition(
                key="user_id", match=models.MatchValue(value="conversation-0"))]))
        for point in points:
            payload = point.payload
            memories.append({"id": str(point.id), "memory": payload["data"], "payload": payload})
        if offset is None:
            break
    client.close()
    additions = [m for line in (out / "ingest.jsonl").open()
                 for m in json.loads(line)["result"].get("results", [])]
    expected = {m["id"]: m["memory"] for m in additions}
    actual = {m["id"]: m["memory"] for m in memories}
    if not actual or actual != expected:
        raise RuntimeError("Complete store export does not match the reported ADD events.")
    target = out / "extracted-memories.json"
    if not (out / "mem0-api-preview.json").exists():
        target.rename(out / "mem0-api-preview.json")
    target.write_text(json.dumps({"results": memories,
        "export_method": "Complete Qdrant scroll with conversation filter",
        "add_events_cross_checked": len(additions)}, indent=2, ensure_ascii=False) + "\n")
    print(f"Complete store export verified: {len(memories)} memories")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lab", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    export(args.lab, args.out)
