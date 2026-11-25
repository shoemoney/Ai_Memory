# Amendment 1 (2026-11-25, written and committed before the amended run)

Pre-registration: `README.md` (protocol flip17-v1). Everything not listed here is unchanged: probe family and features, the entropy and margin baselines, the rule that a probe must beat **both** entropy and margin, the clustered bootstrap, 1-pass vs 3-pass greedy comparison, layers 6, 11, 17, 32 new tokens, capped answers censored rather than counted.

(a) **Why.** With the registered settings (`reasoning_effort=none`, 32 new tokens, chat template) the 8-item pilot produced no final answer in any of 16 generations: every one was cut off inside the model's thinking block, so `answer_flip` was None for 8 of 8 items (`RESULTS.md` records the pilot, `PENDING.md` the question).

(b) **Change to what is measured.** The collector (`flips.py --no-thinking`) now appends `<|message_model|><|content_text|>` to the templated prompt, so the model's turn opens directly as a text message and the answer starts immediately. This is the form the checkpoint's chat template renders for an assistant turn with empty reasoning, i.e. an empty thinking block closed before it starts. The study therefore measures **the model's direct answer without visible reasoning**, not its answer after thinking; results do not transfer to reasoning-on use.

(c) **Item count.** 400 items cut to **160**, 40 per registered stratum (recall, two_hop, memory, code), sampled with the registered seed 1701 from each stratum's id-sorted pool (`--stratified 160`), emitted round-robin in the fixed strata order so any prefix is stratified. Reason: the full run would take about 8 hours. The reduced n widens every interval; a null at n = 160 is not evidence of no effect.

(d) **Pilot first.** An 8-item pilot (the first 8 of the same order, 2 per stratum) runs before the 160 to confirm final answers and flip labels exist and to report the base rate of answer flips. A base rate below about 10% or above about 90% is reported but does not stop the 160 run.

## Addendum, same day, before the amended pilot results were used
The first amended pilot showed a collector bug, not a design problem: the prefilled marker is outside the generated tokens, so the final-answer extractor found no text channel (`final_text` None although answers existed). Fixed by extracting the answer from prefill + generation, with a test. The 8-item pilot was rerun; its numbers are the ones reported. No full-run data existed before this fix.
