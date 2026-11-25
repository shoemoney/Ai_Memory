| Benchmark | Method | Published reference, different setup | Local correct / N | Local rate | 95% Wilson interval |
| --- | --- | --- | --- | --- | --- |
| MemoryAgentBench EventQA | full-context | 90.2% small-context GPT-4o-mini; 59.0% main table | 143/150 | 95.33% | 90.68% to 97.72% |
| MemoryAgentBench EventQA | rag | 63.0% Text-Embed-3-Small, main table | 115/150 | 76.67% | 69.28% to 82.72% |
| MemoryAgentBench EventQA | bm25 | 74.6%, main table | 129/150 | 86.00% | 79.54% to 90.66% |
| HaluMem QA | full-context | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 62/150 | 41.33% | 33.77% to 49.33% |
| HaluMem QA | rag | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 49/150 | 32.67% | 25.68% to 40.52% |
| HaluMem QA | bm25 | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 62/150 | 41.33% | 33.77% to 49.33% |
