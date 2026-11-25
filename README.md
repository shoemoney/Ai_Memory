# AI Memory: Building an LLM brain

By Jeremy Schoemaker. This is the companion repository for a book about storing,
retrieving, updating and evaluating memory for language model applications. It
covers files and wikis, embeddings, databases, memory frameworks, retrieval,
security and worked application examples. The labs include local experiments
and reduced-scale checks of published results; each report states its scope and
limits.

The book is available on Amazon in paperback, hardcover and Kindle editions.
Free PDF and EPUB distribution is planned.

## Repository layout

| Path | Contents |
| --- | --- |
| `build/chapters/` | Book chapter sources in HTML, including lab listings |
| `build/` | PDF/EPUB build scripts, styles, diagrams, fonts and edition outputs |
| `benchmarks/` | Lab harnesses, dependency pins, protocols, reports and retained results, grouped by experiment |
| `research/` | Topic notes and source references |
| `covers/` | Cover artwork, build scripts, assets and print proofs |
| `blog/` | Related articles |

Start with a lab's `README.md` and `REPORT.md`. Protocols and manifests give
sample selection, model revisions, dependency versions and differences from
published settings. A reported result applies to that configuration; it does
not establish a ranking across different datasets or model backends.

## Reproduce a lab

For a small local experiment, use the retained LongMemEval oracle-history pilot.
Read `benchmarks/longmemeval/README.pilot.md` for the pinned model, serving command
and dataset provenance. It uses a local Qwen3.5 9B model served through MLX-LM,
CPU embeddings, Python and `uv`. Serve the pinned model on your own Apple Silicon
machine and forward its endpoint to localhost port 39710 on the scoring machine.
The exact package and model revisions are in that pilot README and its manifest.

From the repository root, choose unused scratch and output directories:

```sh
LAB_DIR="$(mktemp -d /var/tmp/ai-memory-longmemeval.XXXXXX)" \
RESULTS_DIR="$PWD/benchmarks/longmemeval/rerun-$(date -u +%Y%m%dT%H%M%SZ)" \
BASE_URL="http://localhost:39710/v1" \
bash benchmarks/longmemeval/run.sh
```

The launcher installs the pinned requirements into its scratch environment,
downloads the pinned dataset and embedding model, generates answers and scores
them, and saves per-item evidence in the new output directory. It removes its
scratch directory on exit. Keep the model server running for the experiment and
stop your server afterwards. Existing scored item/method pairs are resumed if
an output directory is reused. This command reruns the pilot; the larger
standard-history experiment has a separate launcher described in
`benchmarks/longmemeval/README.md`.

Other labs have different prerequisites, including Docker, a model endpoint or
a GPU. Read their instructions and third-party data terms before downloading
inputs. Reproduction commands can take hours and substantial memory or disk.

## Which licence covers what

Copyright 2026 Jeremy Schoemaker for original material, except where another
copyright holder is identified.

| Material | Licence |
| --- | --- |
| Original code in `benchmarks/`, executable lab listings, scripts and build tooling in `build/` and `covers/` | MIT; see [LICENSE](LICENSE) |
| Original book text in `build/chapters/`, PDF/EPUB editions, figures, diagrams and cover artwork in `build/` and `covers/` | CC BY 4.0; see [LICENSE-TEXT](LICENSE-TEXT) |
| Original prose in `research/`, `blog/`, this README and benchmark reports | CC BY 4.0 |
| Third-party code, prompts, datasets, fonts and excerpts, including material inside the folders above | Their own licences; see [NOTICE](NOTICE) and retained upstream notices |

The MIT and CC BY 4.0 grants apply only to rights held by the author. They do
not relicense third-party material or override noncommercial, share-alike or
other source conditions. For CC BY 4.0 reuse, credit Jeremy Schoemaker, name the
book, identify the source and licence, and indicate changes. The full legal
code in `LICENSE-TEXT` was fetched from
[Creative Commons](https://creativecommons.org/licenses/by/4.0/legalcode.txt).

## Acknowledgements

[Thinking Machines Lab](https://thinkingmachines.ai) released
[Inkling 2 Mini](https://huggingface.co/thinkingmachines/Inkling-2-Mini) and the
[variable-loop research model](https://huggingface.co/thinkingmachines/TML-d24-varloop-research)
under Apache 2.0, and runs the [Tinker](https://thinkingmachines.ai/tinker/) fine-tuning service
used for the adapter experiments. The experiments in `benchmarks/inkling/` exist because those
weights are open.

The [Qwen team at Alibaba](https://huggingface.co/Qwen) released the base models
used in many labs. The `benchmarks/*/REPORT.md` files identify Qwen2.5 at 0.5B,
1.5B, 3B, 7B and 14B, and Qwen2.5-Coder at 1.5B; Qwen3-Embedding at 0.6B, 4B and
8B; Qwen3-VL-Embedding at 2B and 8B; and Qwen3.5 at 0.8B, 2B, 4B and 9B.
The reports also identify community Empero distill builds labelled Qwen3.8 at
2B, 4B and 9B, including an edited 9B refusal-test build. Those community labels
are not a claim that Alibaba released official Qwen3.8 checkpoints at those
sizes. Model licences vary: in particular, Qwen2.5 3B uses the Qwen Research
licence. Consult the exact model revision and its terms in each lab's protocol.

The benchmark and dataset authors are credited in [NOTICE](NOTICE) and the
individual lab records.

## Experiments on Inkling 2 Mini and the variable-loop research model

[benchmarks/inkling/REPORT.md](benchmarks/inkling/REPORT.md) reports a set of experiments on Thinking Machines Lab's
looped models, run on one Mac Studio and on the Tinker fine-tuning service:

- More loop passes help a memory reader only when the evidence is already in its context: about 9 points with the
  right sessions supplied, nothing with BM25 or dense retrieval.
- LoRA fine-tuning on short answers removes the model's reasoning (99.4% to about 54% on a hard memory test), and
  raising thinking effort does not bring it back. Training on the model's own verified reasoning keeps accuracy at
  the same token cost.
- Eight shell commands trained into the weights need about a tenth of the prompt and make far fewer extra calls, and
  trail native tool declaration by 7 to 10 points on unfamiliar phrasing.
- Refusal rate against pass count, a swap of the message passed between loop passes, one-pass drafting with
  three-pass verification and the bundled draft model's energy use showed no effect or a negative one.

Every study has its own write-up with sample sizes, intervals and limits; the full list is in
[benchmarks/inkling/research/LEDGER.md](benchmarks/inkling/research/LEDGER.md).

## Citation

Use [CITATION.cff](CITATION.cff) for the repository metadata and preferred book
citation. When referring to a lab result, also identify its report, configuration
and repository revision.
