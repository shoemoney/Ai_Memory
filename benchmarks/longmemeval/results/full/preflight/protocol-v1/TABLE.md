| System | Local result | Checkpoints missing |
|---|---|---:|
| full-standard | unavailable, N=0; 16 context skips | 284 |
| bm25-standard | 11/16 (68.8%), 95% Wilson 44.4% to 85.8% | 284 |
| dense-standard | 8/16 (50.0%), 95% Wilson 28.0% to 72.0% | 284 |
| mem0-raw-standard | 8/16 (50.0%), 95% Wilson 28.0% to 72.0% | 284 |
| full-oracle | 8/14 (57.1%), 95% Wilson 32.6% to 78.6% | 285 |

| Official question type (abstentions included) | BM25 | Dense | Mem0 raw | Oracle full context |
|---|---:|---:|---:|---:|
| knowledge-update | 2/2 | 2/2 | 2/2 | 1/2 |
| multi-session | 2/4 | 1/4 | 1/4 | 2/3 |
| single-session-assistant | 4/4 | 4/4 | 4/4 | 4/4 |
| single-session-preference | 0/1 | 0/1 | 0/1 | 0/1 |
| single-session-user | 1/1 | 0/1 | 0/1 | 1/1 |
| temporal-reasoning | 2/4 | 1/4 | 1/4 | 0/3 |
| Abstention overlay | 0/0 | 0/0 | 0/0 | 0/0 |

The abstention row overlaps the official types; it is not added again to overall N. Disjoint sampling-stratum counts remain in the manifest and summary.

| Oracle-window matched subset | Result |
|---|---|
| bm25-standard | 11/15 (73.3%), 95% Wilson 48.0% to 89.1% |
| dense-standard | 8/15 (53.3%), 95% Wilson 30.1% to 75.2% |
| mem0-raw-standard | 8/15 (53.3%), 95% Wilson 30.1% to 75.2% |
| full-oracle | 8/14 (57.1%), 95% Wilson 32.6% to 78.6% |
