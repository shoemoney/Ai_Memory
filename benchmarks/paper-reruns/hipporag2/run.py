"""Paired, checkpointed evaluation using the pinned authors' implementation."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--endpoint', default='http://localhost:39950/v1')
    p.add_argument('--n', type=int, default=150)
    p.add_argument('--seed', type=int, default=20261122)
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--extraction-cache',type=Path)
    a = p.parse_args()
    sys.path.insert(0, str(a.source / 'src'))
    sys.path.insert(0, str(a.source))
    out = Path(__file__).parent / 'results'
    out.mkdir(exist_ok=True)
    data = json.loads((a.source / 'reproduce/dataset/2wikimultihopqa.json').read_text())
    selected = sorted(random.Random(a.seed).sample(range(len(data)), a.n))
    samples = [data[i] for i in selected]
    # Use every supplied context, including distractors, without inspecting answers.
    docs = list(dict.fromkeys(title + '\n' + ' '.join(sentences)
                             for s in samples for title, sentences in s['context']))
    manifest = {'seed': a.seed, 'n': a.n, 'dataset': '2wikimultihopqa',
                'corpus_size': len(docs), 'sampling': 'seeded sample without replacement, sorted source order',
                'corpus': 'union of all supplied contexts, including distractors, for selected questions',
                'item_ids': [s['_id'] for s in samples],
                'document_sha256': [hashlib.sha256(d.encode()).hexdigest() for d in docs]}
    (out / 'cohort.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if a.prepare_only:
        print(json.dumps({'n': a.n, 'corpus_size': len(docs)})); return
    import torch
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    from main import get_gold_docs, get_gold_answers
    from hipporag.HippoRAG import HippoRAG
    from hipporag.llm.openai_gpt import CacheOpenAI
    from format_guard import NativeFormatGuard
    from hipporag.StandardRAG import StandardRAG
    from hipporag.utils.config_utils import BaseConfig
    from hipporag.evaluation.retrieval_eval import RetrievalRecall
    from hipporag.evaluation.qa_eval import QAExactMatch, QAF1Score
    gold_docs = get_gold_docs(samples, '2wikimultihopqa')
    assert all(set(g).issubset(docs) for g in gold_docs)
    gold_answers = get_gold_answers(samples)
    for method, cls in [('hipporag2', HippoRAG), ('dense', StandardRAG)]:
        config = BaseConfig(save_dir=str(a.scratch / method), dataset='2wikimultihopqa',
            llm_name='local-qwen2.5-3b-q4', llm_base_url=a.endpoint,
            embedding_model_name='Transformers/' + str(a.scratch / 'embedding'),
            embedding_provider='transformers', embedding_batch_size=32,
            retrieval_top_k=20, linking_top_k=5, qa_top_k=5, temperature=0, seed=a.seed,
            force_index_from_scratch=True,
            openie_max_workers=2, max_new_tokens=1024, response_format={'type':'json_object'},
            openie_ner_max_tokens=1024, openie_triple_max_tokens=2048,
            rerank_dspy_file_path=str(a.source / 'src/hipporag/prompts/dspy_prompts/filter_llama3.3-70B-Instruct.json'))
        result_path = out / (method + '.jsonl')
        complete = {r['id'] for r in map(json.loads, result_path.read_text().splitlines())} if result_path.exists() else set()
        with ExitStack() as resources:
            if method=='hipporag2':
                cache_dir=a.extraction_cache or (Path(config.save_dir)/'llm_cache')
                base=CacheOpenAI(cache_dir=str(cache_dir),global_config=config,max_retries=config.max_retry_attempts)
                resources.callback(base.close)
                guarded=NativeFormatGuard(base,out/'format-guard-events.jsonl')
                rag=resources.enter_context(cls(global_config=config,extraction_llm=guarded,qa_llm=base,index_identity='native-format-retry-v1'))
            else:
                rag=resources.enter_context(cls(global_config=config))
            start = time.monotonic()
            rag.index(docs)
            (out / (method + '-index.json')).write_text(json.dumps({'seconds': time.monotonic()-start, 'documents': len(docs)}) + '\n')
            for s, gold, answers in zip(samples, gold_docs, gold_answers):
                if s['_id'] in complete: continue
                start = time.monotonic()
                solutions, responses, metadata, _, _ = rag.rag_qa([s['question']], [gold], [answers])
                solution = solutions[0]
                _, recall = RetrievalRecall().calculate_metric_scores([gold], [solution.docs], [1,5,10,20])
                _, em = QAExactMatch().calculate_metric_scores([answers], [solution.answer])
                _, f1 = QAF1Score().calculate_metric_scores([answers], [solution.answer])
                row = {'id': s['_id'], 'method': method, 'answer': solution.answer,
                       'gold_answers': answers, 'raw_response': responses[0],
                       'retrieved_sha256': [hashlib.sha256(d.encode()).hexdigest() for d in solution.docs],
                       'gold_sha256': [hashlib.sha256(d.encode()).hexdigest() for d in gold],
                       'scores': {**recall[0], **em[0], **f1[0]}, 'seconds': time.monotonic()-start}
                with result_path.open('a') as f:
                    f.write(json.dumps(row) + '\n'); f.flush(); os.fsync(f.fileno())
                print(method, s['_id'], row['scores'], flush=True)


if __name__ == '__main__':
    main()
