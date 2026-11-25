"""Chapter 11 filtered retrieval control. Run against fresh, task-owned servers.

Requires numpy==2.5.5 qdrant-client==1.20.0 psycopg[binary]==3.3.9.
Ports: Qdrant 39110, PostgreSQL 39111. Writes JSONL to stdout.
Same fixture as worker.py; no model downloads. One graph build per store.
"""
import ast
import json
import pathlib
import time

import numpy as np
import psycopg
from qdrant_client import QdrantClient, models

N, D, Q, SEED = 100_000, 384, 200, 20261122
# Reuse the original generator verbatim without running worker.py's CLI.
source = pathlib.Path(__file__).with_name('worker.py').read_text()
node = next(n for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == 'dataset')
exec(compile(ast.Module(body=[node], type_ignores=[]), str(__file__), 'exec'))
x, queries = dataset()
filters = {'tenpct': 10, 'tiny': 5000}
truth = {}
for label, modulus in filters.items():
    eligible = np.arange(0, N, modulus)
    truth[label] = [eligible[np.argsort(-(x[eligible] @ q), kind='stable')[:10]]
                    for q in queries]

def emit(**row):
    print(json.dumps(row), flush=True)

def measure(store, mode, label, search):
    counts, recalls = [], []
    for i, q in enumerate(queries):
        start = time.perf_counter()
        ids = search(q)
        counts.append(len(ids))
        recalls.append(len(set(ids) & set(truth[label][i])) / 10)
        emit(kind='query', store=store, mode=mode, filter=label, query=i,
             ids=ids, count=len(ids), recall=recalls[-1],
             ms=(time.perf_counter() - start) * 1000)
    emit(kind='summary', store=store, mode=mode, filter=label,
         mean_rows=float(np.mean(counts)), recall_pct=float(np.mean(recalls)*100))

c = QdrantClient(url='http://127.0.0.1:39110', timeout=300)
c.create_collection('filter_control',
    vectors_config=models.VectorParams(size=D, distance=models.Distance.COSINE),
    hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100),
    optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1000))
for label in filters:
    c.create_payload_index('filter_control', label,
        field_schema=models.KeywordIndexParams(type='keyword', is_tenant=True),
        wait=True)
for start in range(0, N, 500):
    c.upsert('filter_control', wait=True, points=models.Batch(
        ids=list(range(start, start+500)), vectors=x[start:start+500].tolist(),
        payloads=[{k: str(i % modulus) for k, modulus in filters.items()}
                  for i in range(start, start+500)]))
for attempt in range(1800):
    info = c.get_collection('filter_control')
    if info.status == models.CollectionStatus.GREEN and info.indexed_vectors_count >= N:
        break
    time.sleep(1)
else:
    raise RuntimeError('Qdrant index did not finish')
emit(kind='index', store='qdrant', indexed_vectors=info.indexed_vectors_count,
     points=info.points_count, config=info.config.model_dump(mode='json'))
for label in filters:
    only = models.Filter(must=[models.FieldCondition(
        key=label, match=models.MatchValue(value='0'))])
    for mode, params in [('ef100', models.SearchParams(hnsw_ef=100)),
                         ('exact', models.SearchParams(exact=True))]:
        measure('qdrant', mode, label, lambda q: [p.id for p in c.query_points(
            'filter_control', query=q.tolist(), query_filter=only,
            search_params=params, limit=10).points])
c.close()

with psycopg.connect('host=127.0.0.1 port=39111 user=postgres dbname=postgres',
                     autocommit=True) as db:
    db.execute('CREATE EXTENSION vector')
    db.execute('CREATE TABLE vectors(id int PRIMARY KEY, v vector(384))')
    with db.cursor().copy('COPY vectors(id,v) FROM STDIN') as cp:
        for i, v in enumerate(x):
            cp.write_row((i, '[' + ','.join(map(str, v)) + ']'))
    db.execute('ANALYZE vectors')
    db.execute('CREATE INDEX ann ON vectors USING hnsw(v vector_cosine_ops) '
               'WITH(m=16,ef_construction=64)')
    db.execute('SET enable_seqscan=off')
    db.execute('SET hnsw.ef_search=40')
    def run(label, mode):
        modulus = filters[label]
        sql = f'SELECT id FROM vectors WHERE id %% {modulus}=0 '
        sql += 'ORDER BY v <=> %s::vector LIMIT 10'
        plan = db.execute('EXPLAIN (FORMAT JSON) '+sql,
                          ('['+','.join(map(str, queries[0]))+']',)).fetchone()[0]
        emit(kind='plan', store='postgres', mode=mode, filter=label, plan=plan)
        measure('postgres', mode, label, lambda q: [r[0] for r in db.execute(
            sql, ('['+','.join(map(str, q))+']',)).fetchall()])
    for mode in ['default', 'iterative', 'tuned_cap']:
        db.execute("SET hnsw.iterative_scan="+
                   ('off' if mode == 'default' else 'strict_order'))
        db.execute('SET hnsw.max_scan_tuples='+('100000' if mode == 'tuned_cap' else '20000'))
        db.execute('SET hnsw.scan_mem_multiplier='+('16' if mode == 'tuned_cap' else '1'))
        for label in filters:
            run(label, mode)
    db.execute('DROP INDEX ann')
    for label, modulus in filters.items():
        db.execute(f'CREATE INDEX partial_{label} ON vectors USING hnsw '
                   f'(v vector_cosine_ops) WHERE id % {modulus}=0')
    db.execute('SET hnsw.max_scan_tuples=20000')
    db.execute('SET hnsw.scan_mem_multiplier=1')
    for label in filters:
        run(label, 'partial_index')
emit(kind='complete')
