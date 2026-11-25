"""Render the editor report from preserved evidence, without inference calls."""
import json,statistics
from pathlib import Path
from bench import ROOT

def main():
    syntax=json.loads((ROOT/'results/summary.json').read_text())
    semantics=json.loads((ROOT/'results/semantic-summary.json').read_text()) if (ROOT/'results/semantic-summary.json').exists() else []
    bymodel={r['model']:r for r in semantics}
    validation=json.loads((ROOT/'results/judge-validation-summary.json').read_text()) if (ROOT/'results/judge-validation-summary.json').exists() else None
    cleanup=json.loads((ROOT/'results/cleanup.json').read_text()) if (ROOT/'results/cleanup.json').exists() else None
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    lines=['| Model, all Q4_K_M | Prior extraction evidence in book | Local valid JSON | Local schema accepted | Supported field claims | Covered reference units | Median / mean seconds |', '|---|---|---:|---:|---:|---:|---:|']
    old={'qwen3.5-2b-q4_k_m':'BFCL-V4 43.6; one direct schema fixture; Mem0 omitted a preference in two adds','qwen3.5-4b-q4_k_m':'None; BFCL-V4 50.3 is tool calling','qwen3.5-9b-q4_k_m':'None; BFCL-V4 66.1 is tool calling','gemma-4-e4b-q4_k_m':'None','coder-stock-q4_k_m':'0 errors in 10 responses / 13 propositions','coder-edited-q4_k_m':'2 reversals in 10 responses / 13 propositions'}
    for row in syntax:
        model=row['model']; sem=bymodel.get(model)
        if sem:
            groups=sem['per_seed']; nums={k:sum(g.get(k,0) for g in groups) for k in ('claim_count','supported','gold_count','covered')}
            precision=f"{nums['supported']}/{nums['claim_count']} ({nums['supported']/nums['claim_count']:.1%})" if nums['claim_count'] else 'No claims'
            recall=f"{nums['covered']}/{nums['gold_count']} ({nums['covered']/nums['gold_count']:.1%})"
        else: precision=recall='Not publishable: judge gate failed or not run'
        lines.append(f"| {model} | {old.get(model,'None')} | {row['valid_json']}/{row['requests']} | {row['accepted']}/{row['requests']} | {precision} | {recall} | {row['median_seconds']:.3f} / {row['mean_seconds']:.3f} |")
    table='\n'.join(lines)
    complete_models=sum(r['requests']==300 and r['items']==100 for r in syntax)
    status='Semantic scoring completed.' if semantics else ('Semantic scores withheld because the judge failed validation.' if validation and not validation['pass'] else 'Generation or semantic scoring is still in progress; read the actual counts below.')
    common=f'''Status: {status}

This is a new public-data stress test of the narrow Chapter 06 walkthrough, not a reproduction of a published extraction score. No published extraction precision or recall exists for this setup. The chapter's BFCL-V4 values measure tool calling; its prior extraction evidence is a one-input demonstration and a ten-case synthetic fixture.

{table}

Each complete model cell has 100 unique turns repeated at temperature zero for seeds 7, 19, and 43. The three repeats are not 300 independent examples. Model order was fixed rather than counterbalanced, and one interrupted source-correction pilot was resumed. Server slots can reuse common prompt prefixes even with RAM prompt caching disabled; observed cached prompt tokens and output-token counts are reported in `results/verification.json`. No speed ranking or causal throughput improvement is inferred. Counts above pool requests for transparency; per-seed counts are in `results/semantic-summary.json` and raw output files. No independent-sample confidence interval is claimed. Latency includes the HTTP round trip and generation, excludes model download and server/model startup, and includes failed/truncated requests where a response arrived. Existing workloads on the serving host were not controlled.
'''
    methods='''## What is measured

All calls use constrained decoding, so the JSON rate measures completed, parseable constrained outputs under the output cap, rather than unconstrained format following. The schema is exactly Chapter 06's three required string fields, `name`, `city`, and `likes`, with extra properties forbidden. No extra instructions define how the extractor should fill an unavailable field, so abstention wording is a prompt-design confound. The user prompt keeps its exact `Extract facts: ` prefix and replaces the original synthetic sentence with `SPEAKER says: TURN`. There is no added extraction system prompt. The literal original fixture cannot remain unchanged while testing 100 public turns. This input substitution, the speaker label, and pseudonymization are explicit differences. Thinking is disabled with `--chat-template-kwargs '{"enable_thinking":false}'` on the server and the same request-level setting. Output is capped at 512 tokens. The server context is 4,096 rather than the walkthrough's 16,384, because these are short direct prompts rather than Mem0's framework prompt.

The frozen data manifest pins the official LoCoMo repository and revision. Sampling seed 20261121 selects five turns with a case-insensitive love/like/enjoy/favorite marker and five other observation-bearing turns from each of ten conversations. Turns are at most 400 characters, and the sampled observation must cite a single source turn. This is a lexical stratum, not a certified preference category. Speaker names, short nickname prefixes, and camel-case personal names are consistently pseudonymized before inference. Artificial identifiers may change model behavior in the required name field. No images, URLs, timestamps, prior sessions, QA questions, or answer labels go to the extractor.

The official README says its observations were generated with a model. They are not human-annotated extraction gold. An agent inspected all 100 sampled source/reference pairs and recorded source-only corrections in `data/reference_audit.json`, removing unavailable context and fixing attribution or textual errors. The shipped sample contains 103 reference units; some are multi-clause observations, so these are not atomic fact counts. Reference coverage measures preservation of those units, not whether an application should retain every observation. No independent human review of these corrections is claimed. These limits prevent treating this as a definitive general extraction benchmark. The public dataset may have appeared in model training; no contamination audit was conducted.

## Matching rule

The `name` field is bookkeeping and is not credited as a remembered fact. Each non-abstaining `city` field becomes `NAME lives in VALUE`; each non-abstaining `likes` field becomes `NAME likes VALUE`. Empty strings and the predeclared case-insensitive placeholders in `judge.ABSTAIN` produce no claim. Other strings, including malformed-looking strings in otherwise valid JSON, remain claims. A wrong extracted name changes the attribution of both claims. A rejected response yields no accepted claims and receives zero reference coverage.

Supported field-claim precision is the fraction of these complete field claims supported by the source alone. One unsupported clause, wrong subject, polarity, amount, or time makes that whole field claim unsupported. Reference-unit recall is the fraction of full reference observations entailed by the union of accepted field claims. Partial overlap earns no coverage; a supported short claim can therefore earn precision but no recall. These two measures use different units and are not presented as a single atomic-fact F1 score. A city mention does not establish residence, and a goal or offer does not establish a preference.

Matching uses local Qwen3.5-9B Q4_K_M, temperature zero, seed 7, thinking off, with its exact prompt and JSON schema in `judge.py`. It differs from LoCoMo's published QA scoring, which uses normalized, stemmed token overlap and other QA metrics. LoCoMo does not publish this extraction scorer. This benchmark has no hosted generation or judge calls. An initial matcher interface attempt stopped on an out-of-range index before any semantic score was produced. The first repair supplied explicit zero-based index objects and restricted response indices in the schema, but the paired protocol then failed validation: 30/30 support decisions and only 11/30 coverage decisions matched. Those complete failed development results remain in `results/matching-development/`. No semantic scores from that protocol are used. The final protocol uses two separate premise-only entailment calls: source text to predicted field claims for support, then predicted field claims alone to reference units for coverage. The original source is absent from the coverage request, and its absence is checked by `verify_results.py`. The semantic inclusion rule did not change. All later raw judge attempts are saved before parsing. The initial failing second reply was not retained by the original parser, so that historical raw reply is unavailable; its exception and the first successful reply remain in `results/validation-pilot/`. The final gate is at least 27 exact entailment decisions on 30 fresh, hand-checkable cases from ten source turns distinct from the development set. The cases include 20 source-support checks and 10 incomplete-premise coverage checks. This is protocol validation after development, not an independently annotated judge-accuracy benchmark. Labels were authored by the implementing agent, not by an independent human annotator. Correct, incomplete, negated, wrong-quantity, and wrong-time examples are preserved with their exact premise, candidate hypothesis, expected label, full request, and raw judge response. The final validation set is small and shares source turns with the evaluated sample, although its ten turns differ from those used for matcher development. The judge is also one of the tested extractors, so shared-model bias is possible. Every semantic claim must be read with these limitations.

The three required fields cannot represent most events, dates, occupations, health statements, or temporal corrections in LoCoMo. Low recall here is heavily constrained by the chapter's schema. This experiment can expose unsupported fields and omissions in this exact walkthrough; it cannot establish which model is best with a general facts schema or isolate an abliteration effect. The edited and stock files also differ in parameter count, file size, and quantizer provenance. No explicit adult or refusal-oriented corpus is included, so this cannot measure the edit's intended refusal reduction.

## Reproduce

Prerequisites: Python 3.14.4 on the scoring machine; an Apple Silicon model-serving host with the preexisting `/opt/homebrew/bin/llama-server` at build 12359, commit b1b770d90; SSH access; enough disk for the six downloads; normal memory pressure and at least 40% system-wide free memory before loading a model. No global installs are performed. The harness uses only Python's standard library. Model revisions and hashes are pinned in `models.json` and `results/model-hashes.json`.

From this directory, after setting `SSH_TARGET` to your serving destination, run one command:

```sh
python3 run_all.py
```

The included `data/sample.json` is frozen; `python3 prepare.py` regenerates it from the pinned public source and records its SHA-256. `BASE_URL` defaults to `http://localhost:39740/v1` for direct `bench.py run --model MODEL_ID` use. The all-model driver creates a localhost-only SSH tunnel on 39741 to a localhost-only server on 39740, serves one model at a time, checks available memory before loading, and monitors the OS pressure level every five seconds. Warn or critical pressure terminates only the recorded benchmark server PID. All code, sampling, scoring, and results stay on the scoring machine. Model files and remote transient files stay under `~/membench-extraction-tmp`. The driver deletes its owned remote directory, stops its server and tunnel, and records before/after disk and process snapshots. It resumes completed model cells from preserved output files. To measure every request again, move the existing result JSONL files aside before running the command; the included frozen data files remain in place.

The exact extraction acceptance boundary is checked with `python3 check_harness.py`. The report is regenerated with `python3 write_report.py`. The driver also runs those reporting steps after scoring. No containers, hosted APIs, embeddings, or scoring-machine GPU are used.

## Data and licenses

Dataset: [official LoCoMo repository](https://github.com/snap-research/locomo), revision `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`. [Pinned README](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/README.MD), [data](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json), [license](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/LICENSE.txt), [published QA evaluation code](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py). The dataset license is CC BY-NC 4.0. The derived sample retains that license. The code here does not relicense the dataset. Gemma uses Q4_K_M here rather than the Q4_0 size estimate in the chapter table. All six quantizer cards declare Apache-2.0; pinned card URLs, metadata and hashes are recorded in `data/model-card-evidence.json`.

Hardware: Apple M1 Ultra with 64 GB unified memory for Metal model serving; a shared 32-thread x86 CPU machine for data, HTTP clients, and scoring orchestration. Existing voice services and a concurrent benchmark workload were left running. Their scheduling and memory use were not controlled. Timings are observations on this shared system, not production throughput guarantees.

## Raw evidence

`results/MODEL.jsonl` contains every extraction request, complete server response, seed, elapsed seconds, parse result and acceptance result. `results/judge-attempts.jsonl` captures every reply from the repaired matcher before parsing. `results/judge-cache.jsonl` contains each unique extraction-to-decision mapping, keyed by SHA-256 of its full input, and links to separate support and coverage raw attempts by immutable attempt IDs. Identical source/claim/reference triples reuse a deterministic judge decision across repeated seeds and models. Empty predictions need no judge call. `results/scored.json` maps every extraction to its judge evidence. `results/judge-validation.json` and its summary preserve the judge acceptance test. Model bytes are deleted after the run; immutable revisions and SHA-256 hashes remain. No original unmasked dataset is shipped here.
'''
    valtext='No judge validation completed.' if validation is None else f"Local judge validation: {validation['correct']}/{validation['N']} exact entailment decisions; gate {'passed' if validation['pass'] else 'FAILED'} at the fixed 27/30 threshold. Support and coverage case counts are in `results/judge-validation-summary.json`."
    cleanuptext='Cleanup evidence is incomplete.' if cleanup is None else 'Cleanup evidence: '+json.dumps(cleanup,sort_keys=True)+'. See sanitized disk and process snapshots in `results/preflight.json`, `results/before-driver.txt`, and `results/after-cleanup.txt`.'
    final_proof=ROOT/'results/final-cleanup.json'
    if final_proof.exists():
        f=json.loads(final_proof.read_text())
        cleanuptext+=f" Independent checks: observed server process absent={f['observed_server_process_absent']}, remote task port unused={f['remote_task_port_unused']}, local task listeners={f['local_task_ports_still_listening']}, local scratch absent={f['local_scratch_absent']}, voice listener PIDs unchanged={f['voice_listener_pids_unchanged']}. Full proof: `results/final-cleanup.json`."
    (ROOT/'README.md').write_text('# Narrow-schema extraction stress test\n\n'+common+'\n'+valtext+'\n\n'+methods+'\n## Cleanup\n\n'+cleanuptext+'\n')
    report='# Editor report: extraction evidence\n\n'+common+'\n'+valtext+'\n\n'
    report+='The strongest limitation is the fixed schema. The task asked for broad fact precision and recall while preserving a `name/city/likes` walkthrough. These requirements cannot yield a representative general-purpose fact extractor comparison. The results below are supported field claims and complete reference-unit coverage under that narrow schema. An independently annotated, unrestricted-facts benchmark remains unresolved.\n\n'
    inv=json.loads((ROOT/'editor_inventory.json').read_text())
    report+='## Inventory of existing numerical evidence\n\n'
    index_by_model={r['model']:r for r in syntax}
    def local_result(model):
        r=index_by_model.get(model)
        if not r: return 'Not run; no local figure.'
        answer=f"Valid JSON {r['valid_json']}/{r['requests']}; accepted schema {r['accepted']}/{r['requests']}; median {r['median_seconds']:.3f} seconds."
        if model in bymodel:
            groups=bymodel[model]['per_seed']; total={k:sum(g.get(k,0) for g in groups) for k in ('supported','claim_count','covered','gold_count')}
            answer+=f" Supported field claims {total['supported']}/{total['claim_count']}; covered complete reference units {total['covered']}/{total['gold_count']}."
        else: answer+=' No accepted semantic score.'
        return answer
    def validity(model):
        r=index_by_model.get(model)
        return f"{r['valid_json']} of {r['requests']}" if r else 'no measured'
    def latency(model):
        r=index_by_model.get(model)
        return f"{r['median_seconds']:.3f}" if r else 'unmeasured'
    two='qwen3.5-2b-q4_k_m'; stock='coder-stock-q4_k_m'; edited='coder-edited-q4_k_m'
    replacements=[
      'BFCL-V4 tests tool calling rather than memory extraction. Our separate test uses 100 public conversation turns and three seeds per extractor, with schema validity, supported field claims, and complete reference coverage reported separately.',
      f"On a shared Apple M1 Ultra with 64 GB, the 2B Q4_K_M extractor returned valid JSON in {validity(two)} requests, with a median of {latency(two)} seconds per call. These preloaded direct calls do not repeat the CPU Ollama test.",
      f"The pinned 2B Q4_K_M file was also tested on 100 public turns over three seeds, returning valid JSON in {validity(two)} requests with a median of {latency(two)} seconds. That run used Apple Metal and llama.cpp build 12359, so its timing is a different setup from the CPU example.",
      'The two Mem0 adds are a small demonstration rather than an extraction-accuracy measurement. The separate public-turn test measures direct extraction under the narrow walkthrough schema and does not test Mem0 storage behavior.',
      'The CPU Mem0 demonstration took 42.5 seconds for a complete add, including its framework prompt. The public-turn experiment times only direct extraction and does not reproduce that pipeline.',
      'The Inkling result is one failed schema check on the stated offload setup. Inkling was not included in the 100-turn small-model comparison.',
      'The approximate recall, retain, and cold-start times are private operating measurements. The public-turn test measures direct extraction and does not reproduce those memory-service timings.',
      'The vendor decision-model latency is not a memory-extraction latency. The public-turn experiment reports direct extraction timings on a shared Apple Silicon host.',
      f"In the public-turn test, the stock file returned valid JSON in {validity(stock)} requests and the edited file in {validity(edited)}, across 100 turns and three seeds each. The narrow schema, different parameter counts, and local judge prevent attributing a quality difference to abliteration.",
      f"The earlier 6.47-second extraction included model loading. With the files preloaded on a shared Apple M1 Ultra, the new direct calls had medians of {latency(stock)} seconds for stock and {latency(edited)} seconds for edited, under a different prompt and schema."
    ]
    relevant=[[two,'qwen3.5-4b-q4_k_m','qwen3.5-9b-q4_k_m'],[two],[two],[two],[two],[],['qwen3.5-9b-q4_k_m'],['qwen3.5-9b-q4_k_m'],[stock,edited],[stock,edited]]
    for item_index,item in enumerate(inv):
        source_links=' '.join('['+str(i+1)+']('+url+')' for i,url in enumerate(item.get('source_urls',[])))
        report+=f"### Chapter {item['chapter']}: {item['location']}\n\nBook sentence: {item['sentence']}\n\nPrinted figures: {item['figures']}. Source: {item['source']}. {source_links}\n\nLocal correspondence: {item['comparison']} The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.\n\n"
        for model in relevant[item_index]: report+=model+': '+local_result(model)+'\n\n'
        report+='Suggested replacement (at most two sentences): '+replacements[item_index]+'\n\n'
    report+='## Suggested replacement text\n\n'
    report+=f'Chapter 06: "We tested {complete_models} 4-bit extractors on 100 public conversation turns across three seeds, using the walkthrough\'s narrow schema and thinking switched off. Valid JSON did not guarantee supported facts, and this schema could not preserve most reference observations."\n\n'
    report+='Chapter 07: "The stock and edited files were also tested on 100 public turns across three seeds, but their different parameter counts and the narrow schema prevent attributing a quality difference to abliteration. The ten-case correction result remains a fixture result rather than a general ranking."\n\n'
    report+='Each suggested replacement is two sentences, uses plain American English, and contains no em dash. The detailed table should accompany the text. The result supports the chapter warning that schema validity does not establish factual accuracy, but cannot confirm the general recommendation of 4B or 9B memory writers.\n\n'
    report+='## Differences and unresolved work\n\n'+methods.split('## Reproduce')[0]+'\n'
    failures=json.loads((ROOT/'results/failures.json').read_text()) if (ROOT/'results/failures.json').exists() else []
    report+='Recorded execution failures: '+json.dumps(failures)+'. Raw truncated outputs remain in the per-model JSONL files. No bad response was retried or discarded to improve a score. Four source inputs changed after a nickname-mask bug was found; 16 affected earlier trials are retained in `results/pilot/obsolete-input-outputs.jsonl` and excluded by input ID, while unchanged completed trials were resumed. `results/pilot/exclusion.json` records the old and corrected sample hashes. The interrupted pilot run and its successful cleanup are retained under `results/pilot/`. Judge decisions have not received independent human adjudication. These results cannot establish a causal effect of weight editing or compare a general memory writer prompt with this narrow schema.\n\n'
    report+='Resolved setup issues: the first source fetch used lowercase filenames, which returned HTTP 404 before the official tree supplied `README.MD` and `LICENSE.txt`; an early readiness probe used the local extraction port instead of the tunnel port; and a draft formatter had a quoting error. The resumed driver uses the corrected readiness URL, and the formatter compiles and renders from the preserved results. The source-mask correction and excluded raw pilot rows are documented above.\n\n'
    report+='## Cleanup and scope\n\n'+cleanuptext+'\n\nOnly files under `benchmarks/extraction/` were written in the repository. No chapter was edited and no commit was made. The local scratch directory was used for primary-source inspection and is removed separately after report generation. Its removal and closure of the initial exploratory tunnel are recorded in `results/final-cleanup.json`. No wiki changes were made because this task explicitly limited writable territory and prohibited commits.\n'
    (ROOT/'REPORT.md').write_text(report)
    from chart import write_chart
    write_chart(syntax,semantics)
if __name__=='__main__': main()
