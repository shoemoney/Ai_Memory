set -e
venv/bin/python - <<'PYREADY'
import time
from qdrant_client import QdrantClient
c = QdrantClient(url="http://127.0.0.1:39110")
for attempt in range(60):
    try:
        c.get_collections()
        break
    except Exception:
        if attempt == 59:
            raise
        time.sleep(1)
c.close()
PYREADY
for file in qdrant_test.py chroma_test.py lance_test.py maxsim_test.py; do
  venv/bin/python "$file" write
  venv/bin/python "$file" read
done
docker rm -f memlab-11-qdrant
cd /var/tmp
rm -rf /var/tmp/memlab-11
