# Storage benchmark results

The vector query comparisons use 100,000 seeded synthetic unit vectors of 384 float32 dimensions and 200 independent query vectors per comparison cell. They measure storage behavior, algorithmic recall and client-observed latency, not embedding semantics. The paired query-level 95% intervals below are conditional on this corpus and one index build; they do not measure between-build, hardware or production uncertainty.

Hardware: 32-thread x86 AMD CPU host, about 28 GiB usable RAM, NVMe-backed ZFS for database data and scratch, CPU only. Each server and client is limited to 2 CPUs and 3 GiB RAM, run sequentially by store on a shared host. Numerical worker pools use one thread.

Observed stack: Python 3.12.12, NumPy 2.5.5, pgvector 0.8.7 on PostgreSQL 18.7, Redis 8.10.3, Valkey bundle 9.2.0 (Redis compatibility version 7.2.4), Memcached 1.6.45, SQLite 3.46.1 with sqlite-vec 0.1.9, local MongoDB 8.2.11, and DuckDB 2.0.1 with VSS revision 3685131eac for the separate memory probe. Exact runtime strings and dependency versions are retained in the raw files.

## Published claims against local observations

| Published claim | Local observation | N / uncertainty / interpretation |
|---|---|---|
| pgvector: IVFFlat builds faster and is smaller than HNSW | IVFFlat 2.725 s, 164,323,328 B; HNSW 202.359 s, 204,808,192 B | One build each, no interval; supports the trade-off on this fixture |
| pgvector: ef40 and 10% filter: about 4 matches | Default mean 3.920 [3.665, 4.160]; iterative 10.000 [9.812, 10.000] returned of 10 | 200 paired queries, 95% intervals; endpoint bounds use Wilson; tests this distribution only |
| pgvector: ef40 and 20 equal tenants: about 2 matches | Default mean 2.025 [1.850, 2.200]; iterative 10.000 [9.812, 10.000] returned of 10 | 200 paired queries, 95% intervals; endpoint bounds use Wilson; tests this distribution only |
| pgvector: ef40 and 5000 equal tenants: usually zero | Default mean 0.005 [0.000, 0.015]; iterative 4.015 [3.770, 4.255] returned of 10 | 200 paired queries, 95% intervals; endpoint bounds use Wilson; tests this distribution only |
| pgvector: vector(d) is 4d+8 B, so 1,544 B at d=384 | pg_column_size=1,544 B; table=163,905,536 B for 100,000 rows | Deterministic size, no sampling CI; 1M/10M extrapolations were not loaded |
| pgvector HNSW index caps: vector 2,000; halfvec 4,000; bit 64,000; sparsevec 1,000 nonzero | Each cap accepted, cap+1 rejected; sqlite-vec separately accepted 8,192 dimensions and rejected 8,193 | Two boundary cases per type; no sampling interval |
| Redis Vector Sets: default int8 vector codes are about 25% of float32 | Total allocated memory delta: Q8 114,057,608 B; NOQUANT 229,225,160 B, 2.010x reduction | 100,000 vectors, one graph build each; total includes graph and ids, so this is not a test of code bytes alone |
| MongoDB: scalar 3.75x and binary 24x vector-index RAM reduction | Independent vector-file proxies and Java RSS are listed below for fresh local containers | Different metrics; they cannot verify the advertised Atlas RAM factors |
| Raw quantization code widths | float32 153,600,000 B; float16 76,800,000 B; int8 38,400,000 B; packed bits 4,800,000 B | 100,000 x 384; exact payload allocations, 2x/4x/32x; no graph, database or allocator overhead |
| Memcached max key 250 B | 250 accepted; 251 and embedded space rejected; raw TAB and byte 0x01 accepted and read back | Boundary behavior tests, no population CI |
| Memcached 30-day relative-expiry boundary | 30 days and absolute 31-day timestamp retained; relative 31 days immediately absent; 1 second expired; zero retained | Five protocol cases, not a retention reliability estimate |
| Memcached warm restart preserves items; extstore is not durable | Graceful SIGUSR1 retained 100/100; SIGKILL retained 0/100; extstore had real external writes and lost its index on restart | One controlled run per mode; no power-failure guarantee |
| Claude Code 200 lines/25KB and Cursor 500-line guidance | A plain local file retained all 300 lines / 45,900 B; closed harness caps cannot be reproduced locally | Filesystem control only; no claim about Claude or Cursor adherence |
| turbopuffer 874 ms cold / 14 ms cached p50 at 1M documents; <=200 ms commit | Cannot be reproduced locally: proprietary managed backend and unspecified original workload/hardware | No substitute local latency presented as an equivalent |
| Cloudflare Vectorize 1536 dimensions, 10KiB metadata, topK50/100, batches1000/5000; AWS preview40B vectors | Cannot be reproduced locally: hosted quotas and private historical traffic | Not locally measurable |
| Provider prompt-cache thresholds, prices and lifetimes | Cannot be reproduced locally with open weights; quoted cost arithmetic checked separately | No hosted calls or billing verification |

## Measured local query cells

All vector cells have N=200 queries and k=10. Recall is the fraction of exact top-10 ids recovered. PostgreSQL exact results agree with all 200 SQLite and Redis/Valkey FLAT results. Median intervals use 2,000 bootstrap resamples with a fixed seed; recall intervals resample whole queries, keeping each query's ten neighbors together. All-perfect or all-zero samples use conservative bounded-mean intervals derived from Wilson event-rate bounds instead of zero-width bootstrap intervals. Exact PostgreSQL reference recall is 100% by definition. Full-list return rates have Wilson intervals in summary.json. p95/p99 are descriptive order statistics from 200 queries and are not production-tail guarantees.

| Store / method / filter | Recall@10, % (95% CI) | Median ms (95% CI) | p95 / p99 ms |
|---|---:|---:|---:|
| sqlite / vec0_l2 / all | 100.00 [98.115, 100.000] | 138.573 [137.169, 139.219] | 154.436 / 164.117 |
| postgres / exact / all | 100.00 [100.000, 100.000] | 37.242 [36.322, 38.856] | 95.223 / 150.901 |
| postgres / exact / tenpct | 100.00 [100.000, 100.000] | 13.106 [12.786, 14.151] | 64.195 / 349.352 |
| postgres / exact / fivepct | 100.00 [100.000, 100.000] | 11.715 [11.164, 12.653] | 37.651 / 100.325 |
| postgres / exact / tiny | 100.00 [100.000, 100.000] | 10.455 [9.981, 11.079] | 31.441 / 169.937 |
| postgres / ivfflat_default / all | 38.90 [33.500, 44.500] | 1.165 [1.105, 1.324] | 3.320 / 5.880 |
| postgres / ivfflat_probes10 / all | 67.10 [63.300, 70.700] | 4.010 [3.869, 4.305] | 7.979 / 132.311 |
| postgres / hnsw_default / all | 96.95 [94.350, 99.000] | 2.827 [2.709, 2.979] | 9.051 / 64.291 |
| postgres / hnsw_default / tenpct | 37.85 [35.250, 40.400] | 5.055 [4.686, 5.531] | 15.823 / 125.980 |
| postgres / hnsw_default / fivepct | 19.60 [17.850, 21.350] | 1.394 [1.229, 1.538] | 3.002 / 4.061 |
| postgres / hnsw_default / tiny | 0.05 [0.000, 0.150] | 1.175 [1.075, 1.284] | 2.800 / 4.856 |
| postgres / hnsw_iterative / all | 96.95 [94.350, 99.000] | 6.767 [6.279, 7.017] | 13.567 / 22.523 |
| postgres / hnsw_iterative / tenpct | 88.00 [84.900, 90.750] | 9.169 [8.534, 10.194] | 26.486 / 53.792 |
| postgres / hnsw_iterative / fivepct | 57.15 [54.200, 59.950] | 27.148 [23.219, 30.369] | 67.960 / 106.454 |
| postgres / hnsw_iterative / tiny | 27.85 [25.900, 29.800] | 276.335 [265.788, 289.569] | 399.194 / 436.026 |
| redis / FLAT / all | 100.00 [98.115, 100.000] | 14.272 [13.652, 15.019] | 27.742 / 36.907 |
| redis / HNSW / all | 73.20 [68.300, 77.950] | 0.384 [0.363, 0.413] | 88.255 / 93.683 |
| redis / VS_Q8 / all | 98.75 [98.250, 99.200] | 0.513 [0.488, 0.537] | 0.788 / 0.893 |
| redis / VS_NOQUANT / all | 100.00 [98.115, 100.000] | 1.329 [1.263, 1.406] | 2.703 / 3.700 |
| redis / VS_BIN / all | 37.85 [36.150, 39.650] | 0.586 [0.563, 0.604] | 0.968 / 1.129 |
| valkey / FLAT / all | 100.00 [98.115, 100.000] | 20.851 [20.380, 21.306] | 28.386 / 34.872 |
| valkey / HNSW / all | 29.20 [26.650, 31.800] | 6.965 [4.044, 7.666] | 87.884 / 93.599 |
| mongo / none / all | 92.00 [90.800, 93.100] | 49.072 [24.386, 61.572] | 168.057 / 203.076 |
| mongo / scalar / all | 88.30 [87.000, 89.500] | 17.891 [14.596, 32.640] | 112.549 / 205.732 |
| mongo / binary / all | 76.60 [74.650, 78.400] | 6.572 [6.291, 7.020] | 60.411 / 153.323 |

## MongoDB memory measurements

Published RAM reductions are scalar 3.75x and binary 24x. The local file-based working-set proxy gives 3.221x and 15.680x, respectively, at 100,000 x 384 dimensions. This is not a direct measurement of Atlas Required Memory or peak RAM.

| Quantization | Independent file proxy, B | Java process RSS, KiB | Container memory |
|---|---:|---:|---|
| none | 179,582,402 | 1795904 | 2.388GiB / 3GiB |
| scalar | 55,760,896 | 2019512 | 2.46GiB / 3GiB |
| binary | 11,453,110 | 2245476 | 2.72GiB / 3GiB |

Each mode has a fresh server and one index build; no statistical interval is justified for these memory snapshots. The file proxy sums .vex and .veq, includes .vec only without quantization, and estimates compound-file contribution from visible file proportions. Temporary files and background merges affect it. Zero named vector-file RSS means the data is in compound/temporary mappings, not that the index uses no RAM; per-extension mapped RSS/PSS is retained in the raw record.

The retrieved public mongot source contains an estimator fallback with the advertised 3.75x/24x constants. This experiment does not use that fallback, because it would be circular evidence for those ratios. That retrieved source is not asserted to be the bundled localDev build.


## Reproduce

From the repository root, run `bash benchmarks/stores/reproduce.sh`. It requires Docker with Buildx, a POSIX shell, host Python 3.10 or newer, internet access, and free loopback ports 39750 through 39757. It installs nothing globally. Re-running archives prior cell JSONL files before creating new ones, and replaces the summaries and source-retrieval manifest; the final step regenerates this report from the new summaries.

The Dockerfile pins the base image digest and requirements.txt pins all resolved Python packages. run.py pins PostgreSQL/pgvector, Redis, Valkey, Memcached and local Atlas images by digest; prefix.py pins llama.cpp and the model revision. Initial image versions are retained by each worker in its JSONL output.

Data: original synthetic fixture, generated by worker.py with NumPy default_rng seed 20261122. There are 1,000 unit-normalized Gaussian centers; each data/query vector chooses a center independently, adds Gaussian noise with standard deviation 0.08 and is normalized. Integer tenant labels are independent of the center and use row id modulo 10, 20 or 5000. No text dataset, embedding weights or model judge is involved in these vector tests. Code is MIT; the generated synthetic fixture is available under CC0-1.0. Each item is flushed and fsynced immediately; rerunning a cell archives its earlier raw output and rebuilds the index rather than mixing queries from different graph builds. Use run.py --cells to rerun only incomplete stores. No fixture vectors or model weights are retained.

The separate DuckDB memory probe uses 100,000 uniform-random FLOAT[384] arrays with SQL setseed(0.123), not the normalized query-comparison fixture. Its 32 MiB buffer setting is not a cap on whole-process or HNSW memory.

The prefix behavior probe uses Qwen2.5-0.5B-Instruct Q4_K_M, Apache-2.0, revision 9217f5db79a29953eb74d5343926648285ec7e67. It is one save/erase/restart/restore demonstration: the cold prompt processed 889 tokens, and the restored fresh process reused 888 tokens while processing one. It is not a generation-quality or speed benchmark, and no confidence interval is inferred.

Primary-source provenance is in results/sources.json with retrieval time, exact URL and SHA-256. Mutable documentation is identified by its fetched content hash, not silently treated as a release snapshot. Documentation pages are not redistributed. The MongoDB markdown pages are included because their HTML counterparts omit most body text. Software licenses include PostgreSQL/pgvector permissive licenses, Valkey BSD-3, Memcached BSD, sqlite-vec Apache-2.0/MIT, Redis 8 AGPL/RSAL/SSPL options, and MongoDB/mongot SSPL; this is not a relicensing of dependencies.

## Limits and scope

Controls: PostgreSQL HNSW m=16, ef_construction=64 and ef_search=40, with iterative scans off or strict_order; IVFFlat 100 lists and probes 1 or 10. ANN queries disable sequential scans and retain EXPLAIN output. Exact filtered baselines deliberately scan the table without an additional tenant index. Redis/Valkey Query Engine and Vector Set cells retain their engine defaults other than the selected index/quantization type; FT.INFO and VINFO are retained. MongoDB numCandidates=100 and limit=10 are explicit; each quantization mode has a fresh server, database and index to isolate retained JVM/index memory. These are different search-effort controls, not equally tuned products. Query Engine readiness requires num_docs=N and initial indexing completion where the engine exposes that field; tiered HNSW buffers/background work may still be present in FT.INFO during the first reads.

SQLite measures L2 and the other vector cells use cosine on the same unit-normalized inputs. Independent exact result sets are checked for agreement. Backend graph randomization is not exposed or seeded by this harness, so repeated ANN builds can return different neighbors even though the corpus and query seed is fixed.

These are one-build, serial, warm-client comparisons on shared hardware. There is no throughput saturation test, no multi-host replication/failover, no semantic task scoring, no production query distribution and no power cut. Server CPU/cache contention, build order, dimensions, corpus geometry and filters affect results. No universal corpus-size threshold follows. Binary codes are not rescored by the Redis Vector Set cell; local Atlas uses its own default quantized-search behavior.

SQLite here loads version 3.46.1 from the pinned Python image, with sqlite-vec 0.1.9. This is different from the book's patched SQLite 3.51.3. The single-threaded probes do not test or validate the rare WAL-reset corruption fix; use the patched library in production.

The inventory covers externally sourced numeric results, limits, prices and relevant measured storage behaviors in the six assigned chapters. Release/version dates, license terms, product lists, architectural descriptions without a measured claim, illustrative sizes and token estimates are not benchmarks. No externally sourced Memcached throughput number or pgvector quantization recall/speed number appears in these reviewed chapter snapshots; the Memcached batch-GET timings are new controls. Existing blocks marked Tested or Test run are the book's prior tests and are excluded, including the 10,000 x 1536 Redis timing/memory table, 20,000-vector PostgreSQL walkthrough, Memcached oversized-item fixture and toy store/MaxSim examples. The new local tests may overlap those features as controls.

Browser SQLite backend constraints and vLLM/LMCache offload behavior remain documentation only. RedisVL defaults were checked in the published wheel, while DuckDB-vss has a separate memory probe; neither is a semantic-quality benchmark. Warm-restart mmap and extstore backing files are on ZFS, not tmpfs or DAX. The extstore load pauses 50 ms after every 100 writes so the probe tests cold-value recovery, not peak ingestion throughput. The MLX engine routes require a Mac, which this task prohibits. REPORT.md lists each disposition explicitly rather than claiming these were measured.

## Cleanup and unsuccessful attempts

results/resource-proof*.json retain before/after df, process-name and container listings, owned-container labels, removed scratch status and completed-cell timings. Servers and workers have hard memory limits totaling 6 GiB; the separate prefix server has a 2 GiB cap. Database data, extension caches, generated data and model downloads use /data/scratch/membench/stores/ on ZFS; the runner stops before large writes if the shared system filesystem has under 20 GiB free. The corpus is small enough that data files plus the pinned images stay below the 20 GB task budget. Shared images/services are preserved. Final additional image/cache cleanup is recorded in results/cleanup.json.

Unsuccessful attempts are retained separately and are not included in the summary: a shared host-root filesystem filling during optional PostgreSQL postprocessing, unescaped SQL percent signs with Psycopg, a port precheck seeing TCP TIME_WAIT, a PostgreSQL parallel-index-build shared-memory limit, and readiness that accepted a Docker TCP proxy before PostgreSQL was serving SQL. The final harness escapes modulo operators, enables SO_REUSEADDR for the port reservation, disables parallel maintenance workers and retries a real SQL connection, and binds database files to a temporary directory on the ZFS scratch filesystem that cleanup removes.
