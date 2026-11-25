# Where the refusal direction sits, per layer and per loop pass

A measurement note on Inkling 2 Mini (three passes through its loop core). It records where a refusal-related direction in the residual stream is separable, and the one behavioural test we ran on it. No weights are released and no procedure for changing a model's refusals is described here.

## Finding

The direction separating harmful from benign prompts is clearest on the first pass through the loop core and in the later layers of the core (12-17); on passes 2 and 3 it is weaker in layers 6-11 and catches up in layers 15-17. Removing the component along this direction from the attention output projection, at one layer and at 6, 12 and 24 layers, left refusals unchanged: 10 of 10 held-out harmful prompts were still refused in every case. Separability in the residual stream is an association, not evidence that refusal is mediated by that direction in the attention outputs.

## Setup

- Model: Inkling 2 Mini, packed BF16/NVFP4 source weights (the 4-bit oQ4e build cannot be loaded by the mlx-lm pull request used here). Zero-based layers; the loop core is layers 6-17 (one-based 7-18).
- Prompts: 50 harmful (HarmBench, standard behaviours) and 50 benign (XSTest, safe prompts). Both sets are third-party and are not redistributed; `refusal/README.md` lists the sources, licences and pinned revisions. Split 30 train, 10 validation, 10 held-out evaluation per class, seed 42, reasoning effort `none`.
- Measurement: the residual-stream activation at the last instruction token, at every layer visit, for each pass. The direction is the normalised difference of class means on the training split. Validation separation = mean projection gap / pooled standard deviation.
- Selection was restricted to the loop core. Unrestricted selection picks layer 0, pass 1 (score 12.7), which is an early-layer scale effect and not a loop-pass question.

## Validation separation by layer and pass (loop core)

| Layer | Pass 1 | Pass 2 | Pass 3 |
|---:|---:|---:|---:|
| 6 | 4.50 | 2.12 | 1.38 |
| 7 | 4.37 | 2.12 | 1.57 |
| 8 | 3.84 | 2.08 | 1.66 |
| 9 | 3.30 | 2.29 | 1.96 |
| 10 | 3.14 | 2.02 | 2.13 |
| 11 | 3.16 | 2.19 | 2.61 |
| 12 | 6.33 | 4.79 | 3.69 |
| 13 | 6.09 | 5.40 | 3.97 |
| 14 | 6.37 | 4.41 | 3.96 |
| 15 | 5.15 | 4.23 | 4.23 |
| 16 | 6.25 | 5.33 | 5.40 |
| 17 | 5.37 | 5.14 | 5.09 |

Best layer per pass: pass 1 layer 14 (6.37), pass 2 layer 13 (5.40), pass 3 layer 16 (5.40); AUC 1.00 on validation in all three. On the held-out evaluation split the pass-1 winner (layer 14) scores 3.95, AUC 1.00. Pass 1 separates best in most layers; passes 2 and 3 catch up in layers 15-17.

## Behavioural test

Held-out prompts: 10 harmful and 10 benign, greedy decoding, reasoning effort `none`. That setting still emits a short thinking block, so refusal is judged on the answer after it (a regex on its first 400 characters; no answer was unfinished). Stock model: 10 of 10 harmful refused, 1 of 10 benign. After removing the direction's component from the attention output projection:

| Layers changed | Tensors changed | Harmful refused | Benign refused | Output |
|---|---:|---:|---:|---|
| 14 | 1 | 10/10 | 0/10 | coherent |
| 12-17 | 6 | 10/10 | 0/10 | coherent |
| 6-17 (loop core) | 12 | 10/10 | 0/10 | coherent |
| 0-23 | 24 | 10/10 | 0/10 | coherent |
| 0-23, each layer's own pass-1 direction | 24 | 10/10 | 0/10 | coherent |

In every case all 176 expert tensors and every non-attention tensor were byte-identical to the source. The behaviour is not simply unchanged text: only 1 of 20 responses in the first three multi-layer cases matches the stock response verbatim, and none does in the last. The refusal signal is probably also written through paths this change does not touch (expert and MLP outputs, convolution, the block bank, embeddings). We did not test those paths.

## Limits

- Ten prompts per class in the behavioural test; refusal is a regex on the first 400 characters of the answer.
- One direction, fitted on 30 + 30 prompts from one pair of public prompt sets.
- Separation scores are measured on single prompts at the last instruction token; they say nothing about generation-time behaviour.
- Related aggregate refusal rates against pass count are in [RESULTS.md](RESULTS.md).
