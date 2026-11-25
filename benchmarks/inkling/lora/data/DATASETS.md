# Memory curriculum provenance

Training input: **Google Synthetic-Persona-Chat**, specifically
`data/New-Persona-New-Conversations.csv`, revision
`a520ad7f999ca7e6dfdc25fed9f5070bf6f87b42`.

- Source: https://huggingface.co/datasets/google/Synthetic-Persona-Chat/tree/a520ad7f999ca7e6dfdc25fed9f5070bf6f87b42
- Authors: Pegah Jandaghi, XiangHai Sheng, Xinyi Bai, Jay Pujara, Hakim Sidahmed.
- Work: *Faithful Persona-based Conversational Dataset Generation with Large Language Models* (2023), https://arxiv.org/abs/2312.10007.
- License: **CC BY 4.0**, checked in the dataset card's `license: cc-by-4.0` field. It permits sharing and adaptation, including commercial use, with attribution and an indication of changes. The card and full license are retained as `SOURCE-CARD.md` and `LICENSE-CC-BY-4.0.txt`.
- Source CSV SHA-256: `ac81a4db067ae15e9cfb82d32844d7941d7f12bff77e8b6482d40892f3c6614f`.
- Changes: take the first 1,000 distinct user-1 persona profiles; discard the original conversations; insert profile sentences as background in newly templated, dated dialogues. All names, addresses, events, garden notes, memory schemas and answers are new templates. The resulting curriculum is distributed under CC BY 4.0. Retain this notice when redistributing.

No benchmark evaluation content enters training. Neither LongMemEval nor LoCoMo supplies training rows. Their full arrays are read only by the overlap detector; they are not redistributed here. No refusal-set examples are used.

## Raw curriculum

| Skill | Training | Validation | Test |
|---|---:|---:|---:|
| Historical fact recall | 900 | 50 | 50 |
| Updating a changed fact | 900 | 50 | 50 |
| Abstaining on an unstated fact | 900 | 50 | 50 |
| Date arithmetic | 900 | 50 | 50 |
| Writing memory via `memory.put` | 900 | 50 | 50 |
| Looking up memory / using its result | 900 | 50 | 50 |
| **Total** | **5,400** | **300** | **300** |

Each row contains 18 sessions spanning 51 days. One half of lookup rows supervises `memory.get`; the other half supervises the final answer after a tool result. With prompt masking, this teaches both the call and its use. Tool arguments are parsed JSON objects, as required by the Inkling template. Persona groups do not cross splits. All six examples for a persona share context, so the 6,000 rows are not 6,000 independent conversations.

The corpus is a narrow, controlled curriculum: rendered examples are 1,421–2,107 tokens with the included template (see `token-lengths.json`), not 100K-token conversations. Dates, synthetic addresses and tool names follow a small template family. Success here does not establish general long-context performance. Benchmark scores and refusal behavior must be measured independently.

Completed audit: **6,000 input rows, 0 removed, 0 remaining overlaps**. Clean counts remain **5,400 train / 300 validation / 300 test**. Both LongMemEval arrays (500 standard + 500 oracle records) and all 10 LoCoMo conversations were scanned twice, for 1,010 evaluation records per pass. Post-filter row counts, removal reasons, full evaluation file hashes and the certified remaining-overlap count are in `clean/decontam-report.json`. The detector checks normalized 13-grams across questions, answers, sessions and other string fields, and conservative exact entity/fact co-occurrence within an evaluation item. It does not claim semantic paraphrase decontamination.
