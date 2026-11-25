# Chapter 11 walkthrough and filtered-search control

The six scripts in this folder are exact decoded copies of Chapter 11's listings
(the installation block is saved as `install-stores.sh`). Start with no
`/var/tmp/memlab-11` directory or `memlab-11-qdrant` container, run
`bash benchmarks/stores/ch11/install-stores.sh`, copy the four Python scripts and
`run-stores.sh` into the new directory, then run `bash run-stores.sh` there.
The final script removes its container and the entire lab directory.

The separate `../ch11-filter.py` reuses the synthetic fixture in `../worker.py`:
100,000 normalized 384-dimensional vectors, seed 20261122, 200 independent
queries, LIMIT 10, filters `id % 10 = 0` and `id % 5000 = 0`. No model is used.
Run against fresh servers only. Example setup, from the repository root:

```bash
mkdir /var/tmp/memlab-11
python3.14 -m venv /var/tmp/memlab-11/venv
/var/tmp/memlab-11/venv/bin/pip install numpy==2.5.5 \
  qdrant-client==1.20.0 'psycopg[binary]==3.3.9'
docker run -d --cpus=2 --memory=3g --name memlab-11-qdrant \
  -p 127.0.0.1:39110:6333 qdrant/qdrant:v1.20.2
docker run -d --cpus=2 --memory=3g --name memlab-11-postgres \
  -v memlab-11-pgdata:/var/lib/postgresql \
  -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1:39111:5432 \
  pgvector/pgvector:pg18 -c max_parallel_maintenance_workers=0
# Wait for both servers to accept connections before starting.
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RAYON_NUM_THREADS=2 \
  /var/tmp/memlab-11/venv/bin/python benchmarks/stores/ch11-filter.py \
  > /var/tmp/memlab-11/filter.jsonl
# Preserve output before cleanup.
docker rm -fv memlab-11-qdrant memlab-11-postgres
docker volume rm memlab-11-pgdata
rm -rf /var/tmp/memlab-11
```

The lab waits for all Qdrant vectors to be indexed. Qdrant uses keyword tenant
indexes created before ingest, m=16, ef_construct=100 and hnsw_ef=100. Its normal
filtered planner can choose an exact scan for a small eligible set; this is not
an isolated measurement of graph traversal. An explicit exact-query control is
also measured. PostgreSQL uses m=16, ef_construction=64, ef_search=40, then
strict_order iteration with its default limits, raised max_scan_tuples=100000
and scan_mem_multiplier=16, and finally filter-specific partial HNSW indexes.
EXPLAIN plans and per-query ids, count, recall and wall time are retained in
`../results/ch11-filter.jsonl`. These are one-build correctness/recall controls
on shared CPU hardware, not equally tuned search budgets or throughput tests.

The recorded run experienced shared memory and disk pressure during the raised-limit
selective cell. Its package installation was paused, and pg_prewarm read mode read
the vectors and ann relation files into the filesystem cache during that cell.
This affects timing interpretation; only row counts and recall are used in the
chapter. The 400 exact Qdrant result sets also matched the original PostgreSQL
exact results in results/postgres.jsonl.
