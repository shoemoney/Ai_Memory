set -e
mkdir /var/tmp/memlab-11
cd /var/tmp/memlab-11
export OMP_NUM_THREADS=2 RAYON_NUM_THREADS=2
python3.14 -m venv venv
venv/bin/pip install qdrant-client==1.20.0 chromadb==1.5.9 \
  lancedb==0.41.0 tantivy==0.27.0
docker run -d --cpus=2 --name memlab-11-qdrant -p 127.0.0.1:39110:6333 \
  qdrant/qdrant:v1.20.2
