#!/usr/bin/env python3
"""Generate an editorial report from actual completed outputs and the chapter inventory."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TASKS=['SciFact','NFCorpus','ArguAna']

def results(model,dim=None):
    slug=model.replace('/','__')+(f'__{dim}d' if dim else '')
    out=[]
    for task in TASKS:
        p=ROOT/'results'/'local'/slug/(task+'.json')
        if p.exists():out.append(json.loads(p.read_text()))
    return out

def mean(model,dim=None):
    rows=results(model,dim)
    return f"{sum(r['ndcg_at_10'] for r in rows)/3*100:.2f}" if len(rows)==3 else 'not measured'

def local_sentence(model,dim=None):
    rows=results(model,dim)
    return ', '.join(f"{r['task']} {100*r['ndcg_at_10']:.2f} (N={r['n_queries']})" for r in rows) or 'No local measurement.'

def dimension_changes():
    path=ROOT/'results/dimensions.json'
    if not path.exists(): return ''
    rows=json.loads(path.read_text())
    return ' '.join(f"At {r['dimension']} dimensions the paired three-task change is {r['delta_vs_768']*100:+.2f} points, with a 95% interval [{r['paired_task_stratified_bootstrap_95_ci'][0]*100:+.2f}, {r['paired_task_stratified_bootstrap_95_ci'][1]*100:+.2f}]." for r in rows if 'delta_vs_768' in r)

claims=json.loads((ROOT/'claims.json').read_text())
text=['# Editorial report: MTEB/MMTEB',
      '', 'Status: partial reproduction. The evaluated models use local open weights and the official MTEB scorer, with full test splits on three English retrieval tasks. The full multilingual or English benchmark aggregates in the chapters were not reproduced, and larger model coverage remains incomplete.',
      '', '## Source claims and replacements',
      '', 'Original wording below comes from the chapter HTML; exact source citations and chapter hashes are in `claims.json`. Each suggested replacement is at most two sentences. Local task means give equal weight to SciFact, NFCorpus, and ArguAna, not to individual queries and not to the full MTEB suite. Chapter 05 has no MTEB/MMTEB score; its toy-corpus recall and MRR are outside this benchmark. Chapter 04 MMEB-V2 and ViDoRe figures are different benchmarks and are outside this run.']
for claim in claims:
    orig=claim['sentence_or_table_row']
    text += ['', f"### {claim['chapter']}: {orig.split(' ')[0]}", '', 'Original: '+orig]
    sources=[url for refs in claim['sources'].values() for url in refs]
    if sources:text+=['', 'Source: '+', '.join(f'[source citation]({u})' for u in sources)]
    if orig.startswith('Qwen3-Embedding') and '64.33, 69.45' in orig:
        local=local_sentence('Qwen/Qwen3-Embedding-0.6B')+'; 4B and 8B untested.'
        replacement=f"The model card reports multilingual MTEB scores of 64.33, 69.45, and 70.58 for the 0.6B, 4B, and 8B variants. Our 0.6B model averaged {mean('Qwen/Qwen3-Embedding-0.6B')} nDCG@10 across three English retrieval tasks, which cannot verify those full-suite averages or the historical number-one rank."
    elif orig.startswith('jina'):
        local=local_sentence('jinaai/jina-embeddings-v5-text-small')
        replacement=f"Jina reports 71.7 on English MTEB v2 and 67.7 on MMTEB for its v5 text small model. Our three English retrieval tasks averaged {mean('jinaai/jina-embeddings-v5-text-small')} nDCG@10, a different task set that cannot verify either aggregate."
    elif orig.startswith('Harrier'):
        local='270M: '+local_sentence('microsoft/harrier-oss-v1-270m')+'; 0.6B: '+local_sentence('microsoft/harrier-oss-v1-0.6b')+'; 27B untested.'
        replacement=f"Microsoft reports multilingual MTEB v2 scores of 66.5, 69.0, and 74.3 for Harrier 270M, 0.6B, and 27B. Our three English retrieval tasks averaged {mean('microsoft/harrier-oss-v1-270m')} and {mean('microsoft/harrier-oss-v1-0.6b')} nDCG@10 for the two smaller models; the 27B model was not run."
    elif orig.startswith('EmbeddingGemma'):
        local=local_sentence('google/embeddinggemma-2')
        replacement=f"The EmbeddingGemma 2 card reports 61.36 on multilingual MTEB v2 at 768 dimensions. Our text-only run averaged {mean('google/embeddinggemma-2')} nDCG@10 on three English retrieval tasks, which cannot verify that multilingual mean."
    elif orig.startswith('BGE-M3'):
        local=local_sentence('BAAI/bge-m3')
        replacement=f"The cited secondary guide reports 59.56 on multilingual MTEB for BGE-M3. Our dense-vector run averaged {mean('BAAI/bge-m3')} nDCG@10 on three English retrieval tasks, so it does not reproduce that multilingual score."
    elif orig.startswith('bge-small'):
        local=local_sentence('BAAI/bge-small-en-v1.5')
        replacement=f"The bge-small-en-v1.5 card reports a 62.17 mean across its English MTEB tasks. Our three-task English retrieval mean was {mean('BAAI/bge-small-en-v1.5')} nDCG@10, with task scores reported separately because the aggregates cover different tasks."
    elif orig.startswith('all-MiniLM'):
        local='No printed benchmark score and no local run in this reproduction.'
        replacement='The MiniLM card is used here to describe a small baseline, without a cited MTEB score.'
    elif '68.46' in orig:
        local='Three-task retrieval means at 768, 256, and 128 dimensions: '+', '.join(mean('google/embeddinggemma-2',d) for d in [None,256,128])+'. '+dimension_changes()
        replacement=f"The EmbeddingGemma 2 card reports English MTEB scores of 68.46, 67.78, and 65.68 at 768, 256, and 128 dimensions, including a 0.68-point drop from 768 to 256. Our three English retrieval tasks averaged {mean('google/embeddinggemma-2')}, {mean('google/embeddinggemma-2',256)}, and {mean('google/embeddinggemma-2',128)} nDCG@10 at those dimensions; these task means cannot verify the full-suite loss."
    elif '1 to 5 points' in orig:
        local='No instruction/no-instruction ablation was run; all runs used the official instructed wrapper.'
        replacement='The Qwen3 model card reports that query instructions typically add 1 to 5 points. Our evaluation used the official task instructions and did not measure that gain.'
    elif orig.startswith('67.88'):
        local='VL 2B: '+local_sentence('Qwen/Qwen3-VL-Embedding-2B')+'; text 0.6B: '+local_sentence('Qwen/Qwen3-Embedding-0.6B')+'; both 8B models untested.'
        replacement=f"Qwen reports text-only MMTEB means of 67.88 versus 70.58 for the two 8B models, a 2.70-point gap, and 63.87 versus 64.33 for the VL 2B and text 0.6B models. Our three-task English retrieval means were {mean('Qwen/Qwen3-VL-Embedding-2B')} for VL 2B and {mean('Qwen/Qwen3-Embedding-0.6B')} for text 0.6B, which cannot verify the multilingual means."
    else:raise ValueError(orig)
    assert '\u2014' not in replacement
    text+=['', 'Corresponding local evidence: '+local, '', '**Suggested replacement:** '+replacement]
text+=['', '## Per-task results', '', (ROOT/'results'/'TABLE.md').read_text(),
       '', '## Differences and interpretation', '',
       'The local run uses MTEB 2.27.20 and the dataset revisions in README.md, unquantized bfloat16 embeddings, exact cosine search, official model-specific task wrappers, and a common 512-token cap. The published JSON files identify their own MTEB and dataset versions in `results/comparison.json`; several differ from the local versions. The Jina revision is explicitly set to the revision with published English results rather than the newer registry default. There is no generated output, temperature setting, or LLM judge. GPU sharing affects timing, and no speed claim is made.', '',
       'The results demonstrate retrieval behavior on these test sets. They cannot support or contradict the full-suite aggregate claims, multilingual coverage, or historical leaderboard ranks. Differences against per-task published scores are not isolated effects of model quality, given the input cap, arithmetic, instruction implementation, and dataset/software revisions. Missing published task records are availability limits at the pinned results commit, not zero scores. The bootstrap intervals describe test-query variability rather than historical reproducibility or a paired significance test. The registry lists SciFact and NFCorpus among Harrier training datasets, so this run does not establish zero-shot performance; training/test overlap was not audited. See results/training_overlap.json.',
       '', '## Coverage and failures', '', '\n'.join('- '+model+': '+reason for model,reason in json.loads((ROOT/'results/scope.json').read_text())['not_run'].items()),
       '', 'NFCorpus is publicly downloadable, but its dataset license is unspecified in the MTEB task metadata and no dataset license was established from the project page. No website theme license has been substituted for a data license.',
       '', 'Process failures and diagnostic tails: `results/suite.json`, `results/suite-extra.json`, and `results/suite-jina.json`. Early setup correction: the generic SentenceTransformer wrapper does not accept `max_seq_length` in its constructor; the harness sets the loaded model length instead. That failed setup produced no retained score. The raw result download initially searched the newer Jina revision and found no English task files; the published-revision manifest fixes this explicitly. Jina initially failed because its historical custom module and sentence-transformers 6.3.0 both supplied cache_dir; compat.py removes duplicate cache arguments and routes nested weight, adapter, and tokenizer loads to a complete local snapshot of the published revision, without changing forward computation, pooling, adapter selection, or prompts. A first retry was stopped before its first task completed after discovering that the historical nested loaders ignore revision; its incomplete outputs were removed. Gemma initially failed the official dependency check for audio/video packages even with text towers only; the required packages were installed in the isolated environment and pinned. Initial failed attempts produced no scores and remain recorded in suite.json; retry outcomes are in suite-extra.json and suite-jina.json.',
       '', '## Raw evidence', '',
       '- `claims.json`: chapter wording, figure inventory, citation URLs, chapter hashes.\n- `published.json` and `results/published/*.json`: pinned leaderboard record paths and original task outputs.\n- `results/local/<model>/<task>.jsonl.gz`: per-query IDs, relevance labels, ranked document scores, nDCG@10 and hit flags.\n- Neighboring `<task>.json` and `config.json`: sample/corpus counts, confidence intervals, settings, model and data revisions.\n- `results/comparison.json` and `results/verification.json`: matched source/local versions and independently checked scores and hashes.\n- `results/sources.json`: primary-source availability and content hashes.']
if (ROOT/'results/DIMENSIONS.md').exists():
    text += ['', '## EmbeddingGemma dimension check', '', (ROOT/'results/DIMENSIONS.md').read_text(), '', 'Changes are paired by query and use equal weighting across the three tasks. Their 95% intervals use 10,000 query bootstrap samples within each task, seed 20261121; these are retrieval-subset changes, separate from the full English MTEB changes reported by the card.']
after=ROOT/'results'/'resources-after.json'
text+=['', '## Cleanup proof', '']
if after.exists():
    d=json.loads(after.read_text())
    text+=['The documented wrapper passed a fresh-environment BGE-small run with exit code 0, then independently verified all 30 retained outputs and removed its environment and caches. See `results/command-proof.json`; the existing-directory refusal is recorded in `results/guard-proof.json`.', '', 'Scratch directory removed: '+str(not d['scratch_exists'])+'. No model servers, tunnels, or containers were started. Model processes exited before cache removal; existing unrelated processes were left running. The first pre-model snapshot is in `results/resources-initial.json`; before/after disk, process, GPU, and container listings for the final clean-command validation are in `results/resources-before.json` and `results/resources-after.json`. The task used this Linux machine only and created no Mac resources.', '', 'Final disk listing:', '', '```text', d['df'], '```', '', 'Final GPU listing:', '', '```text',d['gpu'],'```']
else:text+=['Cleanup is still pending; no completion claim is made.']
(ROOT/'REPORT.md').write_text('\n'.join(text)+'\n')
# Replace only the generated section, preserving the authored method text.
p=ROOT/'README.md';s=p.read_text()
table=(ROOT/'results'/'TABLE.md').read_text()
if (ROOT/'results/DIMENSIONS.md').exists():
    table += '\n### EmbeddingGemma dimensions on the same retrieval subset\n\n'+(ROOT/'results/DIMENSIONS.md').read_text()+'\nChanges are paired within tasks and macro-averaged across tasks; the card\'s full English MTEB scores are separate figures in REPORT.md.\n'
start='<!-- RESULTS -->';end='<!-- /RESULTS -->'
if end in s:s=s[:s.index(start)]+start+'\n\n'+table+'\n'+s[s.index(end):]
else:s=s.replace(start,start+'\n\n'+table+'\n'+end)
p.write_text(s)
print('Updated README.md and REPORT.md from retained evidence')
