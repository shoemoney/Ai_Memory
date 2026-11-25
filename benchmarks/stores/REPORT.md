# Editor handoff: externally sourced storage figures

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Each item below identifies the chapter sentence or table row, the published claim, its local disposition, evidence and a replacement of at most two sentences. Full numeric results and setup differences are in README.md and results/summary.json. The source chapter hashes in claims.json identify the exact reviewed build.

Do not silently turn a documentation limit, hosted price, one-run observation or an arithmetic extrapolation into a locally measured benchmark. Do not attach the local CPU timings to hosted-service claims.

## S01: Index cap: 200 lines or 25KB

Chapter: `build/chapters/01-flat-files.html:270`.

> 200 lines or 25KB Claude Code auto memory load cap for the MEMORY.md index. Content past it is not loaded at session start. 3 Official docs

**Disposition:** cannot be reproduced locally. The cap belongs to the closed Claude Code harness. Local filesystem writes beyond both sizes are measured only as a control, not an emulation of that harness.

**Evidence:** `results/sqlite.jsonl:flat_file`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S02: Longer than 200 lines reduces adherence

Chapter: `build/chapters/01-flat-files.html:271`.

> 200 lines Target length for one CLAUDE.md. Anthropic says longer files "reduce adherence". 3 Official docs

**Disposition:** cannot be reproduced locally. Closed-model adherence claim lacks public prompts, randomization and scoring; a different model would answer a different question.

**Evidence:** `results/sources.json:claude-memory`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S03: Cursor 500-line guidance

Chapter: `build/chapters/01-flat-files.html:272`.

> 500 lines Cursor guidance: "Keep rules under 500 lines". 5 Official docs

**Disposition:** cannot be reproduced locally. This is guidance from a closed harness, not a filesystem limit or a published effect size.

**Evidence:** `results/sources.json:cursor-rules`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S04: Pokemon: 10000 steps, 413/10 files, 1/4 badges

Chapter: `build/chapters/01-flat-files.html:273`.

> 413 files vs 10 files Memory folders of two Claude models about 10,000 steps into a Pokemon game. The 10-file folder earned 4 badges and the 413-file folder earned 1. One run each, and the notes were mostly redundant facts. 26 Vendor measurement

**Disposition:** cannot be reproduced locally. Closed models and no exact public run artifacts or paired sample. A one-run observation cannot supply a population interval.

**Evidence:** `results/sources.json:anthropic-memory-measurement`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S05: Copilot merge rate 83% to 90%, 7 points, 8.4% relative

Chapter: `build/chapters/01-flat-files.html:274`.

> 7 percentage points (83% to 90%, about 8.4% relative) Rise in pull request merge rate for Copilot's coding agent with memory on: the vendor's A/B result, reported by GitHub. 20 Vendor measurement

**Disposition:** cannot be reproduced locally. Private production A/B population, outcomes and closed service.

**Evidence:** `results/sources.json:copilot-measurement`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S06: Copilot default 90-day expiry, admin 7 to 180 days

Chapter: `build/chapters/01-flat-files.html:275`.

> 90 days Default expiry of a Copilot memory without reinforcement. Admins set 7 to 180 days for repository facts. 10 Official docs

**Disposition:** cannot be reproduced locally. Hosted retention policy, not a local database setting.

**Evidence:** `results/sources.json:copilot-memory`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S07: Claude database-task mean reward

Chapter: `build/chapters/01-flat-files.html:276`.

> 0.655 to 0.838 Mean reward of one Claude model on a database question task, without and with a memory directory. 26 Vendor measurement

**Disposition:** cannot be reproduced locally. The primary article identifies a CL-Bench 1.0 database task run in Claude Managed Agents, but does not provide the exact evaluated database snapshot, task instance sequence, prompts, model checkpoint or grader inputs for this reward. A generic local database task would not reproduce that reported experiment.

**Evidence:** `results/sources.json:anthropic-memory-measurement,cl-bench-release`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S08: Copilot validation latency

Chapter: `build/chapters/01-flat-files.html:142`.

> A note such as "send() never retries" is wrong the day someone adds retries, and the model will still trust it. The fix is to store, with each fact about code, the file, symbol and commit it was true at, and to check them before the note reaches the context. GitHub Copilot Memory does this: every fact cites code locations, and Copilot checks them against the current branch before using it. GitHub's engineers report that the check adds no significant latency in their testing, and GitHub's documentation says the check can be wrong. 10 , 20 Loom, an Apache-2.0 tool from ClickHouse announced on 13 November 2026, follows a renamed function and flags a note for review when the function is rewritten. Nothing is rewritten automatically. Both are vendor descriptions, not run. The Loom repository was created in October 2026. 21

**Disposition:** cannot be reproduced locally. No numeric latency bound, public workload or local implementation of the hosted check.

**Evidence:** `results/sources.json:copilot-measurement`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S09: Grep versus vector retrieval superiority

Chapter: `build/chapters/01-flat-files.html:126`.

> plain glob and grep driven by the model beat them

**Disposition:** cannot be reproduced locally. Interview anecdote supplies neither fixed corpus nor common queries and scoring; no reproducible benchmark is specified.

**Evidence:** `REPORT.md`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S10: AGENTS adoption count 60000+

Chapter: `build/chapters/01-flat-files.html:237`.

> AGENTS.md is an open format described as "a README for agents", and its site says 60k+ open-source projects use it. 4 Cursor rules add globs and four modes. 5

**Disposition:** cannot be reproduced locally. A website adoption count is not a performance measurement and the full counted population is unavailable.

**Evidence:** `REPORT.md`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S11: Concurrent file edits can lose updates

Chapter: `build/chapters/01-flat-files.html:471`.

> If two agents or people edit one file at the same time, one edit can overwrite the other. Git and worktrees reduce the risk, as Letta's repositories do, but plain shared files do not. 2 Beads' default embedded mode has a single writer. Server mode is the documented route for several. 8

**Disposition:** measured local. A deterministic two-reader, two-writer lost-update schedule; this is a possibility proof, not an incidence estimate.

**Evidence:** `results/sqlite.jsonl:lost_update`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book reproduced a lost update when two writers read the same old file and then replaced it without locking. This proves the failure is possible, not how often it occurs.

## S12: vector HNSW 2000-dimension cap

Chapter: `build/chapters/08-postgres.html:97`.

> vector The default dense embedding column. 2,000 dimensions

**Disposition:** measured local. Empty indexes test the validator at cap and cap+1; scale timings use 384 dimensions.

**Evidence:** `results/postgres.jsonl:index_boundary`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book created an HNSW index on vector(2000) and observed rejection at vector(2001). These are index limits, not the largest dimensions the column can store.

## S13: halfvec HNSW 4000-dimension cap

Chapter: `build/chapters/08-postgres.html:98`.

> halfvec Dense embeddings that need an index above 2,000 dimensions. 4,000 dimensions

**Disposition:** measured local. The column itself can hold larger vectors; the test concerns the HNSW index.

**Evidence:** `results/postgres.jsonl:index_boundary`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book created an HNSW index on halfvec(4000) and observed rejection at halfvec(4001). The larger indexable dimension limit does not establish recall for a particular embedding model.

## S14: bit HNSW 64000-dimension cap

Chapter: `build/chapters/08-postgres.html:99`.

> bit Binary vectors, for example from binary_quantize with Hamming distance. 64,000 dimensions

**Disposition:** measured local. Cap and cap+1 index creation.

**Evidence:** `results/postgres.jsonl:index_boundary`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book created an HNSW index on bit(64000) and observed rejection at bit(64001). This is an index-validator test, not a large-corpus timing result.

## S15: sparsevec HNSW 1000-nonzero cap

Chapter: `build/chapters/08-postgres.html:100`.

> sparsevec Sparse vectors that store only non-zero elements. 1,000 non-zero elements

**Disposition:** measured local. Insert succeeds; index build with cap+1 must reject the stored vector.

**Evidence:** `results/postgres.jsonl:index_boundary`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book indexed a sparse vector with 1,000 nonzero elements and observed rejection when the stored vector had 1,001. The column dimension and nonzero-element limit are different constraints.

## S16: IVFFlat faster and smaller than HNSW

Chapter: `build/chapters/08-postgres.html:112`.

> IVFFlat Lists: rows / 1000 up to 1M rows, then the square root of rows. Probes: about the square root of lists. ivfflat.probes defaults to 1. Builds faster and is smaller, but needs data in the table before the build.

**Disposition:** measured local. Same 100000 vectors, 384 dimensions; one index build per method, so no interval on build time or size.

**Evidence:** `results/postgres.jsonl:index`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** On this book's 100,000-vector, 384-dimension fixture, IVFFlat built in 2.725 seconds using 164,323,328 index bytes, versus HNSW's 202.359 seconds and 204,808,192 bytes. Each index was built once, so these observations have no between-build interval.

## S17: HNSW m16, construction64, search40 defaults and trade-off

Chapter: `build/chapters/08-postgres.html:111`.

> HNSW m 16, ef_construction 64, query setting hnsw.ef_search 40. Better speed and recall than IVFFlat, but slower to build and heavier on memory.

**Disposition:** measured local. 200 queries per cell. Explicit m16/construction64 for the build; ef_search is read from the running extension.

**Evidence:** `results/postgres.jsonl:default,query,index`.

**Interpretation:** Supports the measured subset of the claim; tuning rules, growth curves or out-of-core limits were not established.

**Suggested replacement:** This book confirmed hnsw.ef_search=40 and tested m=16 with ef_construction=64 on 100,000 vectors. Unfiltered recall@10 was 96.95% over 200 queries; see the companion benchmark for its interval and filtered results.

## S18: IVFFlat probes1; list/probe sizing recommendations

Chapter: `build/chapters/08-postgres.html:112`.

> IVFFlat Lists: rows / 1000 up to 1M rows, then the square root of rows. Probes: about the square root of lists. ivfflat.probes defaults to 1. Builds faster and is smaller, but needs data in the table before the build.

**Disposition:** measured local. 100 lists follows N/1000 at N=100000; probes 1 and 10 are compared. This does not optimize or validate a universal tuning rule.

**Evidence:** `results/postgres.jsonl:default,query,index`.

**Interpretation:** Supports the measured subset of the claim; tuning rules, growth curves or out-of-core limits were not established.

**Suggested replacement:** This book confirmed ivfflat.probes defaults to 1 and built 100 lists for 100,000 vectors. Increasing probes from 1 to 10 changed recall@10 from 38.90% to 67.10% on the same 200 queries, which does not establish a universal tuning rule.

## S19: Exact search perfect recall, latency grows with corpus

Chapter: `build/chapters/08-postgres.html:110`.

> None (exact) Every query computes the distance to every row and sorts. Perfect recall. Latency grows with table size.

**Disposition:** measured local. Exact top10 supplies ground truth at one scale. A single scale cannot establish a latency-growth curve.

**Evidence:** `results/postgres.jsonl:query`.

**Interpretation:** Supports the measured subset of the claim; tuning rules, growth curves or out-of-core limits were not established.

**Suggested replacement:** This book used exact top-10 results as ground truth for 200 queries over 100,000 vectors and measured a median read of 37.242 ms. It tested one corpus size, so it did not measure a latency-growth curve.

## S20: ef40 gives about2/20tenant, usually0/5000tenant

Chapter: `build/chapters/08-postgres.html:221`.

> What breaks first. Per-user recall usually fails before the disk fills. At the default ef_search of 40, an HNSW search returns 40 candidates, and the WHERE clause then discards the rows that belong to other users. If 20 users share the table evenly, about 2 of the 40 belong to the user you asked about. With 5,000 users, usually none do. This is an estimate from the README's arithmetic, not a recall guarantee. The fixes are in the filters gotcha below. 1 Concurrent load also competes for CPU and cache, so measure p95 and p99 at the agent count you expect. No universal row cutoff exists.

**Disposition:** measured local. Independent tenant labels at 5% and 0.02% selectivity; returned counts and recall measured over the same 200 queries. Arithmetic is an expectation, not a guarantee.

**Evidence:** `results/postgres.jsonl:query`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** With ef_search=40, this book measured mean result counts of 2.025 for 20 equal tenants and 0.005 for 5,000 tenants across 200 queries. These are observations for this fixture, not a per-query recall guarantee.

## S21: vector storage 4d+8; 1544 bytes, 1.54GB/1M and15.44GB/10M

Chapter: `build/chapters/08-postgres.html:222`.

> Storage. A vector(d) value takes 4d + 8 bytes (arithmetic in Chapter 00). 1 At 384 dimensions that is 1,544 bytes, so 1 million memories take 1.54 GB and 5,000 users with 2,000 memories each take 15.44 GB. These are decimal estimates for the vectors alone. Text, row overhead, indexes and replicas add more.

**Disposition:** measured local. pg_column_size and table bytes measured at100000x384. Larger counts remain arithmetic extrapolations.

**Evidence:** `results/postgres.jsonl:storage`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book measured 1,544 bytes for one 384-dimension vector and 163,905,536 table bytes for 100,000 rows. Million-row and ten-million-row sizes remain arithmetic extrapolations rather than loaded tests.

## S22: Post-filtering short results; iterative scans expand them

Chapter: `build/chapters/08-postgres.html:578`.

> The index scan runs first and the WHERE clause removes rows afterwards, so a per-user query can return fewer rows than LIMIT . Iterative scans fix this by continuing until enough rows pass or a work limit is reached. Other fixes are a higher ef_search , exact search over a selective user index, a partial index or partitions. 1

**Disposition:** measured local. Exact, HNSW default and strict_order iterative scans use identical filters and queries; finite scan budgets can still miss.

**Evidence:** `results/postgres.jsonl:query,plan`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book's default HNSW scan returned a mean 2.025 rows for a 5% filter, compared with 10.000 with iterative scanning. With a 0.02% filter, the iterative scan still averaged only 4.015 rows under its work limit.

## S23: Vector Set default8-bit codes about25% float32

Chapter: `build/chapters/09-redis.html:114`.

> Memory Measured about 16.1 KB per 1,536-dimension vector (hash plus index). 8-bit quantization by default, about 25% of float32 for the vector data. 3 Measured 2.3 KB per vector including the graph.

**Disposition:** measured local. A native one-element probe without quantization flags confirmed int8 as the default. Separate 100000 x 384 Q8, NOQUANT and BIN cells measure allocated server memory including graph and ids, not only vector-code bytes.

**Evidence:** `results/redis-default.json; results/redis.jsonl`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** For 100,000 vectors of 384 dimensions, this book measured 114,057,608 allocated bytes with default Q8 and 229,225,160 without quantization, a 2.010x total-memory reduction. Eight-bit code values take one quarter of float32 payload space, but graph and id overhead prevent treating that as a fourfold reduction in the whole set.

## S24: VSIM0..1 score; s=(1+cos)/2 and distance2(1-s)

Chapter: `build/chapters/09-redis.html:101`.

> VSIM ... WITHSCORES returns a score s from 0 to 1, where 1 is identical and 0 is opposite. The Redis module README says the interval is "rescaled from the -1, 1 original range to 0, 1". 4 FT.SEARCH and RedisVL return a distance instead, where lower is closer. Convert any threshold before moving it from one API to another:

**Disposition:** measured local. Three analytic vectors with NOQUANT, not embedding-model quality.

**Evidence:** `results/redis.jsonl:scores`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book tested unquantized identical, orthogonal and opposite vectors and received VSIM scores of 1, 0.5 and 0. These support s=(1+cosine)/2 for this API; distance thresholds use a different scale.

## S25: Vector Set attribute filtering

Chapter: `build/chapters/09-redis.html:113`.

> Filtering Tag, numeric and text fields in the same query. Tested with a tag filter. Filter expressions over element attributes, per the docs; not run here. 5

**Disposition:** measured local. One matching and two nonmatching elements. This verifies API behavior, not filtered ANN recall at scale.

**Evidence:** `results/redis.jsonl:filter`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book tested an attribute filter over three controlled elements and received only the matching element. It did not measure filtered Vector Set recall at scale.

## S26: AOF everysec crash loss about1second

Chapter: `build/chapters/09-redis.html:191`.

> About 1 second Writes lost after a crash with appendfsync everysec . 1 Official docs

**Disposition:** cannot be established by this local test. A process kill retains OS cache and cannot bound loss on power failure. No fabricated crash-loss measurement is provided.

**Evidence:** `REPORT.md`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S27: noeviction errors and allkeys-lru eviction

Chapter: `build/chapters/09-redis.html:516`.

> When maxmemory is reached, the default noeviction policy returns errors on writes, while policies such as allkeys-lru delete keys, including memory you wanted. 24 Release a lock only if its value is still yours: the lock guide uses DELEX key IFEQ value (Redis 8.4 or later) or a Lua script on older versions. Both come from the docs and were not run here. 22

**Disposition:** measured local. 4000 acknowledged writes per policy with a2MB budget above measured baseline.

**Evidence:** `results/redis.jsonl:eviction; results/valkey.jsonl:eviction`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book exhausted a small Redis and Valkey memory budget with 4,000 acknowledged writes per policy. noeviction produced write errors, while allkeys-lru accepted the writes and evicted earlier keys.

## S28: Ownership-checked lock release

Chapter: `build/chapters/09-redis.html:516`.

> When maxmemory is reached, the default noeviction policy returns errors on writes, while policies such as allkeys-lru delete keys, including memory you wanted. 24 Release a lock only if its value is still yours: the lock guide uses DELEX key IFEQ value (Redis 8.4 or later) or a Lua script on older versions. Both come from the docs and were not run here. 22

**Disposition:** measured local. Wrong owner then right owner. No failover or distributed-lock guarantee is inferred.

**Evidence:** `results/redis.jsonl:lease_release`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book tested DELEX IFEQ with a wrong owner and the correct owner: the first removed nothing and the second removed the lease. This is a single-instance behavior test, not a failover safety result.

## S29: RedisVL distance threshold default0.1

Chapter: `build/chapters/09-redis.html:171`.

> RedisVL's SemanticCache stores answers keyed by the question's embedding and returns one only when a new question is close enough. Its distance_threshold argument sets that limit and defaults to 0.1, a distance, so lower is stricter. 23

**Disposition:** verified published wheel. AST inspection of the pinned RedisVL 0.32.1 wheel confirms SemanticCache.__init__ has distance_threshold=0.1. The client was not instantiated and cache precision was not tested.

**Evidence:** `results/defaults.jsonl`.

**Interpretation:** Supports the constructor-default claim, not cache precision or runtime configuration.

**Suggested replacement:** This book checked the published RedisVL 0.32.1 wheel and confirmed a constructor default distance_threshold of 0.1. That configuration check does not establish a useful production threshold or semantic-cache precision.

## S30: Memcached max key250bytes; whitespace/control restriction

Chapter: `build/chapters/10-memcached-and-caches.html:238`.

> 250 bytes Longest key. 1 Official docs

**Disposition:** measured local. The 249/250/251-byte boundary is tested. Raw TCP requests with TAB and byte 0x01 were accepted and retrieved, while an embedded space was rejected; the documented format restriction is not uniformly enforced by the server.

**Evidence:** `results/memcached.jsonl:key_limit`.

**Interpretation:** Confirms the byte-length boundary, but shows that the server does not enforce all documented character restrictions.

**Suggested replacement:** This book confirmed the 250-byte limit, but its raw TCP probe stored and read back keys containing a tab or byte 0x01, despite the documented key-format restriction. Hash long prompts and validate keys in the client, rather than relying on every restriction being enforced by the server.

## S31: TTL30day boundary,31days immediate expiry,0 never expires by time

Chapter: `build/chapters/10-memcached-and-caches.html:140`.

> Expiry has one trap. Values up to 2,592,000 seconds (30 days) are lifetimes counted from now. Larger values are read as Unix timestamps, so 31 days in seconds points into 1970 and expires at once. Use the current Unix time plus the lifetime you want, as tested below. An expiry of 0 means no time expiry, but it does not protect against eviction. Eviction reclaims items at the least-recently-used end within slab classes, so monitor per-slab eviction counters instead of assuming every item lasts until its TTL. 1 2

**Disposition:** measured local. 0,30days,31days relative,31days absolute and1second TTL. Eviction is tested separately.

**Evidence:** `results/memcached.jsonl:ttl`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book retained values with zero expiry, a 30-day lifetime and an absolute timestamp 31 days ahead, but a relative 31-day value was immediately absent. A one-second value expired, and zero expiry did not prevent eviction in the capacity test.

## S32: Warm restart preserves planned restart, not crash safe

Chapter: `build/chapters/10-memcached-and-caches.html:138`.

> Warm restart writes an external mmap file and metadata during graceful shutdown, and can preserve items across a planned restart when configuration is compatible. It is not crash safe, misses updates made while the server is stopped, needs a stable clock, and cannot be combined with extstore. 3

**Disposition:** measured local. 100 values per mode, explicit SIGUSR1 graceful shutdown versus SIGKILL and ordinary shutdown. No power-cut claim.

**Evidence:** `results/features.jsonl:memcached_restart`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book retained all 100 values after the documented SIGUSR1 warm shutdown and none after SIGKILL. This process-restart test does not establish power-loss durability.

## S33: Extstore moves values to storage and loses index at restart

Chapter: `build/chapters/10-memcached-and-caches.html:137`.

> Extstore moves colder values to flash and keeps keys and the hash table in RAM. It trades disk I/O for capacity, and a lost process still loses the cache index. 19

**Disposition:** measured local. 10000x8KiB writes; require extstore_objects_written>0 before testing restart. This is local disk, not a flash performance comparison.

**Evidence:** `results/features.jsonl:extstore,extstore_restart`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book wrote 10,000 values of 8 KiB and confirmed extstore had written objects before restarting the process. Values visible before restart were absent afterward, so external storage did not preserve the cache index.

## S34: Warm restart incompatible with extstore

Chapter: `build/chapters/10-memcached-and-caches.html:138`.

> Warm restart writes an external mmap file and metadata during graceful shutdown, and can preserve items across a planned restart when configuration is compatible. It is not crash safe, misses updates made while the server is stopped, needs a stable clock, and cannot be combined with extstore. 3

**Disposition:** measured local. The documentation marks the combination unsupported, but the pinned server accepted both flags at startup. This probe does not establish correct recovery of a combined warm-restart/extstore deployment.

**Evidence:** `results/features.jsonl:incompatible_options`.

**Interpretation:** The flags were accepted; this cannot establish correctness or support of the combined configuration.

**Suggested replacement:** Memcached documents warm restart as unsupported with extstore; this book found that both flags were nevertheless accepted at startup. Startup acceptance does not establish correctness for the combined configuration.

## S35: Slab-class eviction beforeTTL

Chapter: `build/chapters/10-memcached-and-caches.html:140`.

> Expiry has one trap. Values up to 2,592,000 seconds (30 days) are lifetimes counted from now. Larger values are read as Unix timestamps, so 31 days in seconds points into 1970 and expires at once. Use the current Unix time plus the lifetime you want, as tested below. An expiry of 0 means no time expiry, but it does not protect against eviction. Eviction reclaims items at the least-recently-used end within slab classes, so monitor per-slab eviction counters instead of assuming every item lasts until its TTL. 1 2

**Disposition:** measured local. 64MiB cache loaded with20000x8KiB, no time expiry. Per-slab stats and total evictions retained.

**Evidence:** `results/memcached.jsonl:capacity`.

**Interpretation:** Confirms eviction before TTL in a bounded cache; this does not isolate every per-slab eviction scenario.

**Suggested replacement:** This book filled a 64 MiB Memcached cache with 20,000 values of 8 KiB and observed eviction despite zero time expiry. The companion results retain the server and slab counters.

## S36: Provider prompt default5min

Chapter: `build/chapters/10-memcached-and-caches.html:107`.

> Provider prompt cache The provider keeps the model state for a repeated prefix and bills the re-read at a lower rate. Provider-set. Anthropic's default is 5 minutes. 8

**Disposition:** cannot be reproduced locally. Hosted cache retention and billing control, not a Memcached policy.

**Evidence:** `results/sources.json:anthropic-cache`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S37: Anthropic512..4096prefix tokens; hit prices0.20/0.10/0.01; write1.25x/2x

Chapter: `build/chapters/10-memcached-and-caches.html:118`.

> Anthropic (named models only) 512 tokens: Fable/Mythos 5.2, Opus/Sonnet/Haiku 5.5. Opus $0.20; Sonnet $0.10; Haiku $0.01 (up to 100K). 1.25x base for 5m; 2x for 1h. Explicit or automatic cache control. 8 9

**Disposition:** cannot be reproduced locally. Paid closed-provider terms and model-specific counters; no API calls authorized by this local-only protocol.

**Evidence:** `results/sources.json:anthropic-cache,anthropic-pricing`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S38: OpenAI1024prefix,0.40/0.10hit,0.05x,1.25x30min/2.5x12hour

Chapter: `build/chapters/10-memcached-and-caches.html:119`.

> OpenAI 1,024 tokens for GPT-5.6 and later. GPT-6.2 Astra $0.40; Sol $0.10 (both 0.05x). 1.25x for 30m; 2.5x for 12h. Implicit or explicit breakpoints. 10 11

**Disposition:** cannot be reproduced locally. Hosted prices, models and retention rules. A local cache cannot establish them.

**Evidence:** `results/sources.json:openai-cache,openai-pricing`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S39: Gemini2048/4096prefix,prices0.10/0.20/0.03,0.05x/0.1x,storage1perM/hour

Chapter: `build/chapters/10-memcached-and-caches.html:120`.

> Gemini 2,048: 2.5 Pro/Flash. 4,096: listed 3.x and 4 models. 4 Carbon $0.10 (0.05x through Nov 30, then $0.20 on $4 input); 2.5 Flash $0.03 text (0.1x, routed to 3.5 Flash-Lite prices from Dec 1). 4: implicit only. Explicit storage for 2.5 Flash: $1/M tokens/hour. 12 13

**Disposition:** cannot be reproduced locally. Hosted prices and time-limited discount, not a local storage benchmark.

**Evidence:** `results/sources.json:gemini-cache,gemini-pricing`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S40: Gemini4 2050-token reprocessing boundary;Pro storage4.50perM/hour

Chapter: `build/chapters/10-memcached-and-caches.html:123`.

> Gemini 4 reuses the full previous request when the new turn adds at least 2,050 tokens. For smaller additions it reprocesses the last 2,050 prior tokens at standard input price. Explicit storage for Gemini 2.5 Pro costs $4.50/M tokens/hour, so storage has no universal rate. Read the model's price row and its cache usage counters. 12 13

**Disposition:** cannot be reproduced locally. Closed inference and billing policy; exact request processing and prices cannot be reproduced with a local model.

**Evidence:** `results/sources.json:gemini-cache,gemini-pricing`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S41: Anthropic0.05x/0.025x/0.1xhit and1.25xwrite

Chapter: `build/chapters/10-memcached-and-caches.html:205`.

> Provider prompt caching bills a re-read of the prefix at 0.05 times base input for Opus/Sonnet 5.5, 0.025 times for Fable/Mythos 5.2 and 0.1 times for Haiku 5.5, against 1.25 times for a 5-minute write. 8 Memcached is not involved.

**Disposition:** cannot be reproduced locally. Hosted policy; model prices are not storage measurements.

**Evidence:** `results/sources.json:anthropic-pricing`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S42: Prompt-cache cost break-even4/5/8/0.20,5.20/8.20/8.40versus8/12

Chapter: `build/chapters/10-memcached-and-caches.html:244`.

> On Opus 5.5 a five-minute cache pays off after one read, and the one-hour cache only wins when reads are more than five minutes apart and at least two of them arrive within the hour. A single read never recovers the one-hour write premium. Per million input tokens, Opus 5.5 costs $4 uncached, $5 for a 5m cache write, $8 for a 1h write and $0.20 for a read. 9 For a million-token prefix, a 5m write plus one read costs $5.20 versus $8 uncached. A 1h write plus one read costs $8.20, no better than uncached, and plus two reads costs $8.40 versus $12. Output and changing suffix tokens cost extra. 8 9

**Disposition:** arithmetic only. The cost arithmetic can be checked locally conditional on quoted rates, but cannot verify billed prices or retention.

**Evidence:** `results/cache-arithmetic.json`.

**Interpretation:** Supports the conditional arithmetic, not the quoted provider prices or billing behavior.

**Suggested replacement:** Using the stated prices, this book calculates $5.20 for a five-minute write plus one read and $8.20 for a one-hour write plus one read, compared with $8 uncached. These are conditional calculations, not a measured provider bill.

## S43: Cache-hit TTL refresh and0/1/10minute example5.20/8.20/10

Chapter: `build/chapters/10-memcached-and-caches.html:245`.

> Successful reads refresh the TTL, so the 1h option only helps when requests are spaced beyond five minutes. Opus 5.5, million-token prefix:

**Disposition:** cannot be reproduced locally. Provider-controlled sliding lifetime. Cost table can be checked conditional on the policy, not confirmed by a Memcached run.

**Evidence:** `results/sources.json:anthropic-cache`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S44: Under-length miss silent, cache unavailable until response starts

Chapter: `build/chapters/10-memcached-and-caches.html:470`.

> A prompt under the model's minimum length is processed without caching and returns no error, so check the usage counters. A cache entry becomes available only after the first response starts, so parallel requests on a cold prefix can all miss. Start one request first, then fan out. 8

**Disposition:** cannot be reproduced locally. Closed hosted timing/usage behavior. No local equivalent establishes this policy.

**Evidence:** `results/sources.json:anthropic-cache`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S45: llama.cpp slot state save/restore and prefixreuse

Chapter: `build/chapters/10-memcached-and-caches.html:127`.

> llama.cpp server: --slot-save-path plus POST /slots/{id}?action=save or restore saves or restores a slot’s prompt cache. 14 The files can be read back as prompts, so treat them as sensitive.

**Disposition:** measured local. One CPU-only Qwen2.5-0.5B slot save/erase/restore sequence; cached-token counters verify actual reuse. No production speedup or general retention guarantee is measured.

**Evidence:** an unpublished raw log.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book saved 889 llama.cpp prompt tokens to disk, restarted the server and restored the slot, then observed 888 cached tokens and one newly processed token. This was one CPU-only Qwen2.5-0.5B behavior test, not a speedup benchmark.

## S46: LMStudioMLX diskKV, oMLX SSDKV, vLLMprefix, LMCacheoffload

Chapter: `build/chapters/10-memcached-and-caches.html:128`.

> LM Studio MLX engine: loads KV cache from disk for prompt sections it has seen. 15

**Disposition:** documentation only, not run. No numerical comparison printed. The MLX routes need a Mac, prohibited for this task; vLLM/LMCache were not installed.

**Evidence:** `REPORT.md`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The documentation describes this behavior. This book did not run that implementation or establish its behavior on the target platform.

## S47: pgvector ef40,10%match yieldsabout4rows

Chapter: `build/chapters/11-vector-stores.html:103`.

> Post-filtering is why a selective filter can starve a result. With an HNSW index and the default hnsw.ef_search of 40, pgvector's documentation shows that a condition matching 10% of rows returns about 4 matching rows on average. Turn on hnsw.iterative_scan so the scan continues, use one partial index or namespace per tenant, or pick a store that filters before searching. 1 , 2 Qdrant filters support nested AND, OR and NOT clauses, and its documentation advises creating payload indexes before ingest. 2

**Disposition:** measured local. Exact per-query match counts, 200 queries; HNSW default and iterative on the same table.

**Evidence:** `results/postgres.jsonl:query`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** For a condition matching 10% of the rows and ef_search=40, this book measured a mean 3.920 returned rows across 200 queries. Iterative scanning returned ten in each of those queries, but not for every more-selective filter.

## S48: turbopuffer cold p50=874ms at1Mdocs

Chapter: `build/chapters/11-vector-stores.html:223`.

> 874 ms turbopuffer cold query, p50, at 1M documents. The first query to a namespace reads object storage, which suits batch agents better than an interactive turn. 3 Vendor claim

**Disposition:** cannot be reproduced locally. Proprietary managed service and unpublished namespace workload/hardware. Local PostgreSQL is not a surrogate for this latency.

**Evidence:** `results/sources.json:turbopuffer-architecture`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S49: turbopuffer cached p50=14ms at1Mdocs

Chapter: `build/chapters/11-vector-stores.html:224`.

> 14 ms turbopuffer cached query, p50, at 1M documents. 3 Vendor claim

**Disposition:** cannot be reproduced locally. Same managed-service restriction. No local number is placed next to it as if like-for-like.

**Evidence:** `results/sources.json:turbopuffer-architecture`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S50: turbopuffer write commits within200ms

Chapter: `build/chapters/11-vector-stores.html:225`.

> 200 ms Time within which turbopuffer says a write commits, so allow for it. 28 Vendor claim

**Disposition:** cannot be reproduced locally. Managed durability and object-store infrastructure cannot be recreated from a public local server.

**Evidence:** `results/sources.json:turbopuffer-tradeoffs`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S51: MongoDB scalar3.75x/binary24x vector-indexRAM

Chapter: `build/chapters/11-vector-stores.html:226`.

> 3.75x, 24x MongoDB RAM reduction for vectors with scalar and binary quantization. 6 Vendor claim

**Disposition:** local test, metric differs. Fresh local Atlas containers were tested for all three modes, with file-size proxies and process/mapped-memory snapshots. These quantities differ from the advertised Atlas per-index RAM metric, so they cannot directly validate its factors.

**Evidence:** `results/mongo_none.jsonl; results/mongo_scalar.jsonl; results/mongo_binary.jsonl`.

**Interpretation:** Supports a reduction in the local file proxy, but cannot verify the different advertised RAM metric.

**Suggested replacement:** Using vector-file snapshots and compound-file proportions, this book estimated 3.221x scalar and 15.680x binary reductions on 100,000 384-dimension vectors. These are file-based proxies, not Atlas Required Memory or peak RAM measurements, so they do not verify MongoDB's 3.75x and 24x RAM claims.

## S52: Vectorize dims1536,metadata10KiB,topK50/100,batch1000/5000

Chapter: `build/chapters/11-vector-stores.html:227`.

> 1536, 10 KiB, 50 Vectorize limits: float32 dimensions, metadata per vector, topK with values or metadata (100 without). Upserts take 1000 (Workers) or 5000 (HTTP). 16 Official docs

**Disposition:** cannot be reproduced locally. Managed Workers/HTTP quotas with no local open-source server implementation.

**Evidence:** `results/sources.json:vectorize-limits`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S53: S3Vectors previewingestion40billion

Chapter: `build/chapters/11-vector-stores.html:228`.

> 40 billion Vectors AWS says were ingested into S3 Vectors during preview. 25 Vendor claim

**Disposition:** cannot be reproduced locally. AWS private service-wide historical traffic, not a reproducible local dataset. No count interval can be derived.

**Evidence:** `results/sources.json:s3-vectors`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S54: Post-filtering can return fewer thanK

Chapter: `build/chapters/11-vector-stores.html:102`.

> Pre-filtering scopes search to allowed memories, such as one tenant. Post-filtering drops non-matching hits after search, which can leave fewer than k results for the prompt.

**Disposition:** measured local. One implementation tested; do not generalize behavior to all ANN products.

**Evidence:** `results/postgres.jsonl:query`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book observed result starvation when pgvector applied selective filters after its HNSW scan. This tests one implementation and does not establish every vector store's filtering behavior.

## S55: WALsame-host/sharedmemoryconstraint

Chapter: `build/chapters/12-sqlite-and-other-stores.html:115`.

> A shared WAL file on a network filesystem. WAL requires processes on the same host. 11

**Disposition:** documentation only, not run. Single-host concurrent behavior is tested; an unsafe multi-host network-filesystem stress test is not performed.

**Evidence:** `results/sources.json:sqlite-wal`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The documentation describes this behavior. This book did not run that implementation or establish its behavior on the target platform.

## S56: One writer, WALreaders continue

Chapter: `build/chapters/12-sqlite-and-other-stores.html:184`.

> Writers: concurrent agents share one SQLite writer. WAL readers continue, but queued writes or checkpoints can delay updates. 11

**Disposition:** measured local. Two connections on a local file; uncommitted row hidden, second writer waits50ms then locks. Not a rate estimate.

**Evidence:** `results/sqlite.jsonl:writer,wal_reader`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book held an uncommitted write in one SQLite connection: a second connection could read the committed snapshot, but its write waited about 50 ms and failed with database locked. This checks one local contention schedule, not concurrent throughput.

## S57: FTS5trigram substring matching

Chapter: `build/chapters/12-sqlite-and-other-stores.html:141`.

> FTS5 supports trigram substring search next to word search, so a fragment of an identifier can match. 1 Vector hits still catch paraphrases.

**Disposition:** measured local. One controlled identifier and substring. No retrieval-quality benchmark is inferred.

**Evidence:** `results/sqlite.jsonl:trigram`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book used an FTS5 trigram index to find an identifier through its substring. One controlled match does not establish retrieval quality over a real corpus.

## S58: FTS5MATCH parses expressions despiteSQLbinding

Chapter: `build/chapters/12-sqlite-and-other-stores.html:735`.

> MATCH has its own query grammar. SQL parameters prevent SQL injection but do not make user text literal. The printed quote() wraps words and doubles internal quotes (see Chapter 05). 1

**Disposition:** measured local. OR expression, quotedliteral and malformedquote, with SQLparameterbinding.

**Evidence:** `results/sqlite.jsonl:fts_grammar`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book passed OR syntax, a quoted literal and an unfinished quote through a parameterized FTS5 MATCH query and observed different results or a parse error. SQL parameter binding did not make the MATCH expression literal.

## S59: Base-rowdeletion doesnotcascade toFTS/vector

Chapter: `build/chapters/12-sqlite-and-other-stores.html:741`.

> Deleting only a memories row leaves its FTS5 and vector entries behind. The fixture avoids this by building all three tables in a fresh database from live state. An incremental materializer must update all three in one transaction.

**Disposition:** measured local. Verify orphanrowids in both virtualtables, not just the base table.

**Evidence:** `results/sqlite.jsonl:no_cascade`.

**Interpretation:** Supports the behavior in these controlled cases; this is not a universal performance bound.

**Suggested replacement:** This book deleted the base row and still found its row id in both the FTS5 and vec0 indexes. An incremental materializer must maintain all three structures together.

## S60: SQLiteWAL-resetrare-corruptionversionrange/fixes3.51.3,3.44.6,3.50.7

Chapter: `build/chapters/12-sqlite-and-other-stores.html:730`.

> SQLite documents a rare WAL-reset race that can corrupt a WAL-mode database when separate threads or processes write or checkpoint at once. It is likely present in SQLite 3.7.0 through 3.51.2. Use 3.51.3 or later, or the fixed backports 3.44.6 or 3.50.7, and check the library your app loads, not only the CLI. 11

**Disposition:** cannot be established by this local test. A passing concurrency smoke test cannot establish absence of a rare race; runtime SQLite version is reported without claiming the patch was validated.

**Evidence:** `results/sources.json:sqlite-wal`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## S61: DuckDB-vssHNSW must fitRAM

Chapter: `build/chapters/12-sqlite-and-other-stores.html:90`.

> DuckDB vss README You analyze archived episodes in batches, not live writes. Experimental extension; its index must fit in RAM. 5

**Disposition:** measured local memory probe. A separate 100000 x 384 uniform-random fixture (SQL seed 0.123) built a HNSW index with DuckDB buffer memory limited to 32 MiB. Whole-process RSS is measured before and after; it does not isolate index allocation or show out-of-core support.

**Evidence:** `results/duckdb.jsonl`.

**Interpretation:** Supports the measured subset of the claim; tuning rules, growth curves or out-of-core limits were not established.

**Suggested replacement:** This book built an HNSW index over 100,000 384-dimension vectors with a 32 MiB DuckDB buffer limit and observed process RSS grow from 144,932,864 to 220,106,752 bytes. This is whole-process memory, not isolated index bytes, and does not establish support for indexes larger than RAM.

## S62: wa-sqliteAccessHandlePoolVFSsingleinstance/noOPFSdirectimport-export

Chapter: `build/chapters/12-sqlite-and-other-stores.html:747`.

> For browser SQLite, start from wa-sqlite's demo/hello at revision 205eed5 , which registers IDBBatchAtomicVFS , a virtual filesystem that stores database pages in IndexedDB. 7 , 15 Choose the storage backend deliberately. The default demo keeps data in memory, and AccessHandlePoolVFS , for example, permits only one wa-sqlite instance and cannot directly import or export its OPFS (origin-private filesystem) files. 7 , 16 Adopt the route only after these checks pass in every supported browser:

**Disposition:** documentation only, not run. Browser-specific backend behavior is not established by desktop SQLite. No browser run performed.

**Evidence:** `results/sources.json:wa-sqlite-vfs`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The documentation describes this behavior. This book did not run that implementation or establish its behavior on the target platform.

## S63: Browserstorageeviction/refusedwrites/userdeletion

Chapter: `build/chapters/12-sqlite-and-other-stores.html:752`.

> Storage loss: handle refused writes and eviction. Browser storage is best-effort by default, and the user can delete even persistent storage. 17

**Disposition:** documentation only, not run. Browser-specific persistence/quotas vary by browser and platform; no browser matrix run.

**Evidence:** `results/sources.json:browser-storage`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The documentation describes this behavior. This book did not run that implementation or establish its behavior on the target platform.

## S64: Pinecone managed object-storage namespaces

Chapter: `build/chapters/11-vector-stores.html:118`.

> Pinecone Managed; proprietary. Serverless, object-storage backed, namespaces. Try first when you want no servers and a namespace per tenant. 14

**Disposition:** cannot be reproduced locally. Pinecone has no public local server implementing the hosted object-storage/namespace service; a different local store cannot establish this service behavior.

**Evidence:** `results/sources.json:pinecone-architecture`.

**Interpretation:** Cannot speak to the published result; it was not reproduced.

**Suggested replacement:** The source reports this figure or behavior. It cannot be reproduced locally under this book's test protocol, so it remains an externally reported claim.

## Cleanup evidence and what did not work

See README.md for corrected harness failures and results/resource-proof*.json for their cleanup records. No failed or partial attempt contributes to the headline statistics. Further corrected harness issues were Redis RESP3 reply shapes, an HNSW readiness timeout, the Docker top PID-column requirement, the unavailable DuckDB 1.4.1 extension and DuckDB 2.0 lambda syntax. MongoDB vector-file memory reads use SYS_PTRACE only inside the owned synthetic-data container; earlier permission refusal is retained as a measurement limitation. Final image/cache/scratch cleanup is documented in results/cleanup.json; a source-only documentation inventory is not a claim that its implementation ran.

The outstanding empirical gaps are the vendor's exact MongoDB per-index RAM metric, power-cut durability, closed/historical/production claims, browser persistence and unrun serving-engine offload implementations. These are named explicitly; none is replaced by a fabricated proxy number.
