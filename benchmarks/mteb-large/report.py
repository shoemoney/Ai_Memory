#!/usr/bin/env python3
"""One account of retained evidence; missing cells never become inferred scores."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TASKS=['SciFact','NFCorpus','ArguAna']
TEXT={'Qwen/Qwen3-Embedding-4B','Qwen/Qwen3-Embedding-8B','Qwen/Qwen3-VL-Embedding-8B','microsoft/harrier-oss-v1-27b'}

def read(p,default=None):return json.loads(p.read_text()) if p.exists() else default

def pct(x):return f'{x*100:.2f}'
def ci(s,key='ndcg_at_10'):
    if key=='ndcg_at_10':return f"{pct(s[key])} [{pct(s['bootstrap_95_ci'][0])}, {pct(s['bootstrap_95_ci'][1])}]"
    s=s[key];return f"{pct(s['mean'])} [{pct(s['bootstrap_95_ci'][0])}, {pct(s['bootstrap_95_ci'][1])}]"

def precision(ex):
    bits=ex.get('bits')
    return f"{ex.get('engine','PyTorch')}; "+(f'{bits}-bit weights, BF16 compute' if bits else 'BF16 weights/compute')

def published_label(spec):
    if isinstance(spec['published'],list):
        return '; '.join(f'{score} on {name}' for score,name in zip(spec['published'],spec['benchmark']))
    return f"{spec['published']} on {spec['benchmark']}"

def main():
    inv=read(ROOT/'inventory.json');session=read(ROOT/'results/followup-session.json',{})
    inherited=read(ROOT.parent/'mteb/results/comparison.json');comparison=[];new_count=0
    rows=[]
    for old in inherited:
        row=dict(old);model=row['model'];task=row['task'];slug=model.replace('/','__')
        p=ROOT/'results/local'/slug/(task+'.json');local=read(p,old.get('local'))
        cfg=read(p.parent/'config.json',{}) if p.exists() else {}
        if p.exists():
            new_count+=1;setting='Apple M3 Ultra, 96 GB; '+precision(cfg.get('execution',{}));evidence=str(p.relative_to(ROOT))
        else:setting='Earlier 8 GB NVIDIA GPU; BF16';evidence=f'../mteb/results/local/{slug}/{task}.json'
        pub=row.get('published_ndcg_at_10');published=pct(pub) if pub is not None else 'Unavailable'
        if local:
            val=ci(local);n=local['n_queries'];decision='No matching published task score'
            if pub is not None:decision='Within local CI' if local['bootstrap_95_ci'][0]<=pub<=local['bootstrap_95_ci'][1] else 'Outside local CI'
        else:
            val='Not evaluated';n=0;evidence='results/followup-events.jsonl'
            if model=='microsoft/harrier-oss-v1-27b':setting='Deferred (timing estimate)';decision='Cannot assess; first-task forecast exceeded the remaining session time'
            elif (ROOT/'results/local'/slug/'deferred.json').exists():setting='Deferred (timing estimate)';decision='Cannot assess; deferred on elapsed-time forecast only, no score used';evidence=f'results/local/{slug}/deferred.json'
            else:setting='Pending/unrun';evidence='results/coverage.json';decision='Cannot assess'
        row.update(local=local,local_execution=cfg.get('execution'),local_hardware=setting,interpretation=decision);comparison.append(row)
        rows.append(f'| {model} | {task} | {published} | {val} | {n} | {setting} | {decision}; `{evidence}` |')
    (ROOT/'results/comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    visuals=[];vrows=[]
    for spec in inv['visual_score_models']:
        p=ROOT/'results/vidore'/spec['model'].replace('/','__')/'summary.json';s=read(p)
        if s:
            visuals.append(s);a,b,n=ci(s,'ndcg_cut_5'),ci(s,'ndcg_cut_10'),s['n_queries']
            setting=s['hardware']+'; '+precision(s.get('execution',{}))
        else:a=b='Not evaluated';n=0;setting='Pending/unrun'
        vrows.append(f"| {spec['model']} | {spec['published']}; {spec['benchmark']} | {a} | {b} | {n} | {setting} |")
    complete=new_count==12 and len(visuals)==3
    cleaned=read(ROOT/'results/cleanup.json')
    state='Complete' if complete else ('Partial, run finished' if cleaned else 'In progress')
    lines=['# Embedding follow-up report','',f'{state}: {new_count}/12 new text-task cells and {len(visuals)}/3 visual-subset cells are retained. The 2B visual result belongs to the initial GPU phase. Missing cells have no local score. Qwen3-VL-Embedding-8B text NFCorpus and ArguAna, and all three Harrier-27B text tasks, were deferred on elapsed-time forecasts alone (never on scores) so that the visual models could finish; every retained cell keeps its full query split and corpus.','',
      'The run stopped mid-way and was resumed: the live Qwen3-VL-Embedding-8B text run was kept, the dropped SSH tunnel was recreated (the worker on the Mac had stayed healthy; one text invocation had died with a connection error and the controller retried it from checkpoints), and after the first session deadline the run resumed with a new deadline and the `--visual-first` option so the Nomic and Qwen3-VL-8B visual cells ran before any more text work. No finished cell, prompt, model, sample or scoring rule was changed.','',
      'The initial assigned Mac entered warning pressure and was not used after reassignment. The replacement machine is the same hardware class, Apple M3 Ultra with 96 GB memory, shared with other benchmark servers. The follow-up uses no dev GPU. Earlier small-model rows and the initial 2B visual row remain explicitly identified reused evidence.','',
      '## Published text-task scores against local scores','',
      'Scores are percentage points, with 95% query-bootstrap intervals. Every completed cell uses its full test split and full corpus: SciFact N=300/5,183 documents, NFCorpus N=323/3,633, ArguAna N=1,406/8,674. “Within CI” describes consistency on that task, not verification of a full-suite average or proof that quantization, backend and version changes have no effect.','',
      '| Model | Task | Published | Local [95% CI] | N | Hardware and precision | Interpretation / evidence |','|---|---|---:|---|---:|---|---|',*rows,'',
      '## Published visual figures against the local subset','',
      'The local subset is ViDoRe V3 HR English, all 318 queries against all 1,110 pages. All models use the same items and graded qrels. This is different from MMEB-V2’s 78-task mean and the ViDoRe-v2 multi-dataset mean; these local results cannot support or contradict either published aggregate.','',
      '| Model | Published figure and benchmark | Local HR nDCG@5 [95% CI] | Local HR nDCG@10 [95% CI] | N | Hardware and precision |','|---|---|---|---|---:|---|',*vrows,'',
      'Raw visual evidence: `results/vidore/<model>/queries.jsonl.gz` and `summary.json`. Dataset revision `bc7d43d64815ed30f664168c8052106484aba7fd`, CC BY 4.0, is recorded in `results/vidore-data.json`. The qrels configuration contains 8,655 rows for query IDs outside the English query file; only judgments for the provided English IDs are used, and all 318 English queries retain judgments.','',
      '## Printed figures and editor replacements','',
      'Exact chapter sentences, source citations and chapter content hashes are in `claims.json`. `inventory.json` lists every printed embedding quality score in chapters 03, 04 and 18. Hosted models have dimensions/prices but no printed quality score there; MiniLM, Jina v4, ColQwen2, ColPali and ImageBind have no printed numeric quality score.','']
    for spec in inv['text_score_models']:
        cells=[r['local'] for r in comparison if r['model']==spec['model'] and r.get('local')]
        lines += [f"### {spec['model']}",'',f"Published: {published_label(spec)}. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.",'',
          'Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.','']
        replacement=f"The card reports {published_label(spec)}."
        if cells:
            values=', '.join(f"{pct(c['ndcg_at_10'])} on {c['task']} (N={c['n_queries']})" for c in cells)
            cfg=read(ROOT/'results/local'/spec['model'].replace('/','__')/'config.json',{})
            bits=cfg.get('execution',{}).get('bits')
            qualifier=f' with {bits}-bit weights' if bits else ''
            replacement+=f" This book scored {values}{qualifier}, a narrower test that cannot verify the full-suite average."
        else:replacement+=' The figure cannot be reproduced locally in this session under the available capacity and time constraints, so this book reports no local score.'
        lines+=['**Suggested replacement:** '+replacement,'']
    q2=read(ROOT/'results/vidore/Qwen__Qwen3-VL-Embedding-2B/summary.json')
    lines += ['### Chapter 04: Qwen MMEB-V2 77.8 and 73.2','',
      'Published: 77.8 and 73.2 for the 8B and 2B models over 78 MMEB-V2 tasks. Local: the HR table above; this subset cannot verify that mean or the 8B versus 2B full-suite gap.','',
      '**Suggested replacement:** Qwen reports MMEB-V2 means of 77.8 and 73.2 for its 8B and 2B models. '+(f"This book’s 2B model scored {pct(q2['ndcg_cut_10']['mean'])} nDCG@10 on 318 English ViDoRe V3 HR queries, a different benchmark." if q2 else 'This book’s HR subset is a different benchmark.'),'',
      '### Chapter 04: Nomic 58.8 nDCG@5','',
      'The pinned 7B card is internally inconsistent: its introduction states 58.8, while its table gives 59.7 for 7B and 58.8 for 3B. Content hashes and source URLs are in `results/sources.json`. A V3 HR subset cannot resolve a V2 multi-dataset average.','',
      '**Suggested replacement:** Nomic’s 7B card says 58.8 nDCG@5 in its introduction but 59.7 in its table. This book treats the source figure as unresolved and reports its local ViDoRe V3 HR test separately.','',
      '### Other printed behavior figures','',
      'EmbeddingGemma’s published 768/256/128-dimensional English-suite scores, 68.46/67.78/65.68, are separate from the earlier local retrieval cuts retained in `../mteb/REPORT.md`. The published Qwen instruction gain of 1 to 5 points is an ablation not established by these instructed-only runs. No OCR control or agent screenshot-task evaluation was run, so this test cannot establish visual-over-OCR superiority or screenshot-agent usefulness.','',
      '**Suggested replacement:** The cards report full-suite dimension and instruction results, while this book’s earlier dimension tests cover three English retrieval tasks. This follow-up uses the official instructions and does not measure the gain from adding them.','',
      '## Setup differences and limits','',
      'The data/scoring harness uses MTEB 2.27.20, pinned original model/dataset revisions, the 512-token text cap, exact cosine search, pytrec_eval, and 10,000 query-bootstrap samples with seed 20261121. Transport batches sort by character length and restore the original order. The VL worker omits the unused language-model output head absent from its embedding checkpoint, strictly loads every backbone parameter, and resets position state for each independent request. Six synthetic embeddings passed its padding/order/repeated-request check with minimum cosine 0.99858 (results/vl-batch-invariance.json); this is not a full-precision backend check. Native Qwen text cells use batch size 32; all actual execution settings are in neighboring model config/worker-identity files. A paired 32-input, label-free numerical check gave a minimum full-precision embedding cosine of 0.99977 between the original 4B PyTorch wrapper and MLX; see `results/backend-equivalence.json`. It validates the adapter before quantization, not retrieval accuracy after quantization.','',
      'Configuration descriptions for unrun workers describe the shipped harness, not completed measurements. Full-precision 4B trials crossed the reserve; the measured 4B configuration therefore uses 8-bit MLX affine weights, group size 64. Larger Qwen models use 4-bit MLX affine weights with bfloat16 compute and an unquantized VL vision tower. Harrier uses its native causal Gemma3 text backbone, strict weight loading without a language-model output head, original local/global attention settings, right padding, last-nonpadding-token pooling including the instruction, and L2 normalization. Its linear and embedding modules use 4-bit MLX affine weights. Conversion streams one matrix at a time on the CPU, without calibration.','',
      'Nomic uses the official ColPali fork at the pinned archive commit with Transformers 4.49.0 and PEFT 0.14.0. Its large linear matrices use symmetric round-to-nearest 4-bit weights, group size 64; embeddings, normalization, biases and smaller matrices keep their original precision. Active LoRA deltas are merged per matrix before quantization. Its base and adapter revisions are pinned separately. The Nomic worker includes a CPU-product check for its MPS 3D attention path; if native 3D SDPA fails, the worker promotes it to an equivalent 4D batch and records that path, following the [upstream shape issue](https://github.com/huggingface/transformers/issues/36413). Its official processor defaults and cosine output are retained. Qwen VL image processing uses at most 1,800 image tokens and an 8,192-token image sequence cap; its text/query cap is 512. Different processor policies remain a model-specific difference.','',
      'Quantization, native inference, input caps and the source/local software or dataset versions prevent an exact full-precision reproduction claim. Hardware and resource sharing prevent timing comparisons. Cache-only/resumed elapsed times are not end-to-end inference timings. The intervals describe test-query variability, not historical reproducibility. SciFact/NFCorpus are registered among Harrier training datasets; no training/test overlap audit was performed. NFCorpus’s data license is unspecified, and no dataset copy is committed.','',
      '## Failures, validation, and cleanup','',
      'Historical failures are retained, not converted into scores: the initial Mac’s warning-pressure stop, the early GPU worker’s exit code 120 during disk pressure (exact cause unproven), the qrels-ID loader correction, and package compatibility corrections. After reassignment, full-precision 4B workers also reached the reserve and were stopped before a task score completed. Quantized cells use a fresh precision-specific cache namespace. The numerical backend and quantizer checks are separate from the retrieval-quality data. A small synthetic Q4 matrix probe did not show a float16 speed advantage, so bfloat16 compute was retained; this was not a model benchmark and used no quality data (results/dtype-performance-probe.json).','',
      'The first quantized conversion encountered a read-only copied tokenizer file; writable permissions on only the task-owned converted metadata fixed serialization. The VL load also required the missing mlx-lm dependency, an explicit repository argument in the streaming loader, and omission of an unused output head absent from the embedding checkpoint. An independent-request position-cache bug failed before a task score completed; the worker now resets that cache and passed the synthetic batch check. These failed attempts are archived as VL load/position logs. No existing service or its files were changed. Admission, retry, configuration, deadline and completion events are in `results/followup-events.jsonl`; worker logs retain other failed attempts. The initial cleanup is preserved as `results/initial-cleanup.json`. Later text cells are deferred when a timing-only forecast exceeds the session time remaining; the same-host 8B task durations are the reference, scaled by completed current-model wall times when available and a 15% contingency, with a stated 3.6 starting parameter-scale factor for Harrier. The budget wall clocks include resumption and pauses and are not inference measurements. No quality score enters that choice, and retained cells use complete datasets. Per-model deferred files and the event log preserve the estimates and reasons.','',
      'Validation evidence: `results/verification.json`, `results/visual-verification.json`, `results/earlier-verification.json`, the two quantizer check files, and the numerical backend check. A verifier can pass only when its complete raw outputs exist. The earlier source hashes remain in `results/inherited-hashes.json`.','']
    if cleaned:lines+=['Final cleanup: `results/cleanup.json`; disk/process evidence: `results/resources-before-cleanup.json` and `results/resources-after.json`.','', '```json',json.dumps(cleaned,indent=2),'```','']
    else:lines+=['The follow-up is active; final cleanup has not been claimed.','']
    (ROOT/'REPORT.md').write_text('\n'.join(lines))
    readme=ROOT/'README.md';intro=readme.read_text().split('<!-- GENERATED RESULTS -->')[0].rstrip()
    end=lines.index('## Printed figures and editor replacements');start=lines.index('## Published text-task scores against local scores')
    readme.write_text(intro+'\n\n<!-- GENERATED RESULTS -->\n'+'\n'.join(lines[start:end])+'\n')
    coverage=[]
    for spec in read(ROOT/'models.json'):
        model=spec['model'];slug=model.replace('/','__');text=[read(ROOT/'results/local'/slug/(t+'.json')) for t in TASKS] if model in TEXT else []
        v=read(ROOT/'results/vidore'/slug/'summary.json')
        coverage.append({**spec,'text_completed_tasks':[x['task'] for x in text if x],
            'text_evaluated_queries':sum(x['n_queries'] for x in text if x),'visual_evaluated_queries':v['n_queries'] if v else 0,
            'status':'retained complete cells shown; missing cells deferred on elapsed-time forecasts or unresolved, never scored as zero'})
    (ROOT/'results/coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
if __name__=='__main__':main()
