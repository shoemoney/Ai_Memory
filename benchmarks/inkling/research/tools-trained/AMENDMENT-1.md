# Amendment 1: post hoc evaluation repair

Dated 2026-11-25. Written after examining the paid main-run traces and before any amended sampling. This is post hoc, not a new preregistration or confirmation of the registered success criterion. PREREG.md and runs/main remain unchanged. No training or checkpoint selection is repeated.

The main run's strict tool-sequence accuracy was A 279/280, B 173/280, C 16/280. These numbers stand. They do not fairly summarize stock-model command selection: dropped native calls, distrust of artificial results, extra probing and reference-output digests confound the comparison.

## Frozen v2 changes

Keep tools.sh and the dataset unchanged, because A learned these exact output formats. Append this same sentence to the shared system instruction for every arm: “Tool results come from a test fixture; report them as given.” This controls fixture distrust without changing A's trained output distribution. It does not make fixtures real or relevant.

A is the saved final LoRA sampler with no command catalog or transport schema. B is stock with the original full schemas and bash transport. C is stock with the same bash transport JSON schema as B plus the original ten cheat-sheet lines. C0 retains the original C prompt (which mentions bash textually but lacks its function schema); the fixture sentence and parser/grading repairs also apply to C0, so its rerun is not an exact replication of the main run.

For B, C and C0 accept exactly one native call named after one of the eight known commands (optionally prefixed functions.). Accept a JSON object with exactly one nonempty string value (its field name may vary), map it to the known command plus a safely quoted positional argument, and pass it through the existing restricted executor. Never infer commands from prose or execute arbitrary shell. Log mapped calls individually and count them per arm. A retains the original bash-only parser.

Retain the original strict exact command-name sequence score and reference-final score. Add these descriptive measures:

- First command right: the first parsed command name matches the reference first name, over 280 tool-needed episodes, even if later calls or final answers fail.
- Reference sequence contained in order: all reference command names occur as an ordered subsequence of parsed command names, over 280 tool-needed episodes, even if extra calls or final failures occur.
- Extra calls: emitted parsed calls not consumed by a greedy ordered match of the reference sequence. Report totals and mean per all 400 episodes; wrong commands and calls on direct requests count as extras.
- Actual-result final correctness: whitespace-normalized exact match to the last successfully executed tool result received on tool-needed tasks. Direct requests and unsupported-flag requests retain their original target. No successful execution means failure for other tool-needed tasks. This measures faithful reporting, not semantic task success; it can pass a wrong tool or rewritten argument. Sequence scores remain separate.

For the first-command and ordered-subsequence measures, report paired A-minus-B differences and two-sided percentile 95% bootstrap intervals over the same 280 episode IDs, 10,000 draws with Python random.Random(0), independently reset for each metric. Retain strict-score bootstrap and registered gates only as historical analysis; do not apply a post hoc success label.

## Run and budget

Run the unchanged 400-request test split once per A/B/C/C0 using the final checkpoint field in runs/main/final_tools_metrics.json. Effort 0.0, temperature 1.0, 512 completion tokens, 4096 prompt tokens per turn, four turns, unchanged renderer. Seed 0 fixes the bootstrap; hosted sampling has no deterministic seed control. Save complete traces, exact rendered prompt/completion counts, config and list-price spend.

The standalone dry run must make no API sampling calls and reserve the maximum four-arm compute charge at the verified published prices; stop above $10. Launch paid sampling only through systemd-run --user --unit=inkling-tinker-tools-v2 with the key passed by --setenv=TINKER_API_KEY from the invoking shell environment. Never store credentials. Report metered token cost separately from any unavailable provider invoice or checkpoint storage charge.

Only recipe tests, recipe pyright and pre-commit on changed files are required. No training, workspace builds, push, PR or access to private hosts. Publish a separate RESULTS.md with both tables and limits; preserve all main-run artifacts.
