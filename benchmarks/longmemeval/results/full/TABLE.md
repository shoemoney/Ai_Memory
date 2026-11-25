| System | Local result | Checkpoints missing |
|---|---|---:|
| full-standard | unavailable, N=0; 300 context skips | 0 |
| bm25-standard | 191/300 (63.7%), 95% Wilson 58.1% to 68.9% | 0 |
| dense-standard | 165/300 (55.0%), 95% Wilson 49.3% to 60.5% | 0 |
| mem0-raw-standard | 165/300 (55.0%), 95% Wilson 49.3% to 60.5% | 0 |
| full-oracle | 127/212 (59.9%), 95% Wilson 53.2% to 66.3% | 0 |

| Official question type (abstentions included) | BM25 | Dense | Mem0 raw | Oracle full context |
|---|---:|---:|---:|---:|
| knowledge-update | 38/46 (69.3% to 90.9%) | 32/46 (55.2% to 80.9%) | 32/46 (55.2% to 80.9%) | 10/36 (15.8% to 44.0%) |
| multi-session | 38/81 (36.4% to 57.7%) | 32/81 (29.6% to 50.4%) | 32/81 (29.6% to 50.4%) | 15/36 (27.1% to 57.8%) |
| single-session-assistant | 30/34 (73.4% to 95.3%) | 32/34 (80.9% to 98.4%) | 32/34 (80.9% to 98.4%) | 34/34 (89.8% to 100.0%) |
| single-session-preference | 5/18 (12.5% to 50.9%) | 7/18 (20.3% to 61.4%) | 7/18 (20.3% to 61.4%) | 6/18 (16.3% to 56.3%) |
| single-session-user | 39/41 (83.9% to 98.7%) | 33/41 (66.0% to 89.8%) | 33/41 (66.0% to 89.8%) | 39/41 (83.9% to 98.7%) |
| temporal-reasoning | 41/80 (40.5% to 61.9%) | 29/80 (26.6% to 47.2%) | 29/80 (26.6% to 47.2%) | 23/47 (35.3% to 62.8%) |
| Abstention overlay | 17/18 (74.2% to 99.0%) | 16/18 (67.2% to 96.9%) | 16/18 (67.2% to 96.9%) | 14/15 (70.2% to 98.8%) |

Cells show correct/N and descriptive 95% Wilson intervals. The abstention row overlaps the official types; it is not added again to overall N. Disjoint sampling-stratum counts remain in the manifest and summary.

| Oracle-window matched subset | Result |
|---|---|
| bm25-standard | 156/212 (73.6%), 95% Wilson 67.3% to 79.1% |
| dense-standard | 135/212 (63.7%), 95% Wilson 57.0% to 69.9% |
| mem0-raw-standard | 135/212 (63.7%), 95% Wilson 57.0% to 69.9% |
| full-oracle | 127/212 (59.9%), 95% Wilson 53.2% to 66.3% |
