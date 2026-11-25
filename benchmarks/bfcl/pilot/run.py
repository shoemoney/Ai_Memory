"""Fixed stratified BFCL-V4 subset, using upstream FC handler and scorers."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import random
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORIES = ['simple_python', 'multiple', 'parallel', 'irrelevance']
SEED = 20261121
PER_CATEGORY = 10

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--thinking', choices=['on', 'off'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--rescore', action='store_true')
    a = p.parse_args()
    os.environ['OPENAI_API_KEY'] = 'local'
    os.environ['OPENAI_BASE_URL'] = os.getenv('BASE_URL', 'http://localhost:39730/v1')
    import bfcl_eval
    from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
    from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry, _evaluate_single_relevance_entry
    from bfcl_eval.constants.enums import Language, ReturnFormat
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
    MODEL_CONFIG_MAPPING['local-subset-FC'] = replace(
        MODEL_CONFIG_MAPPING['gpt-4o-2024-11-20-FC'], model_name=a.model,
        display_name='Local subset', model_handler=OpenAICompletionsHandler,
        input_price=None, output_price=None)

    class LocalHandler(OpenAICompletionsHandler):
        def generate_with_backoff(self, **kwargs):
            # Only transport/generation controls differ from the upstream handler.
            kwargs.update(max_tokens=4096, seed=SEED,
                          extra_body={'chat_template_kwargs': {'enable_thinking': a.thinking == 'on'}})
            self.request = copy.deepcopy(kwargs)
            start = time.monotonic()
            response = self.client.chat.completions.create(**kwargs)
            self.response = response.model_dump()
            return response, time.monotonic() - start

    handler = LocalHandler(a.model, 0, 'local-subset-FC', True)
    handler.client = handler.client.with_options(timeout=600, max_retries=0)
    if importlib.metadata.version('bfcl-eval') != '2026.3.23':
        raise RuntimeError('Unexpected BFCL package version')
    data = Path(bfcl_eval.__file__).parent / 'data'
    expected_manifest = json.loads((ROOT/'evidence/sample-manifest.json').read_text())
    manifest = {'seed': SEED, 'per_category': PER_CATEGORY, 'categories': {},
                'bfcl_version': importlib.metadata.version('bfcl-eval'),
                'scorer_sha256': hashlib.sha256(Path(__import__('bfcl_eval.eval_checker.eval_runner', fromlist=['x']).__file__).read_bytes()).hexdigest()}
    a.output.mkdir(parents=True, exist_ok=True)
    summary = {'model': a.model, 'thinking': a.thinking, 'categories': {}}
    for cat in CATEGORIES:
        source = data / f'BFCL_v4_{cat}.json'
        entries = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
        selected = random.Random(f'{SEED}:{cat}').sample(entries, PER_CATEGORY)
        expected = expected_manifest['categories'][cat]
        if (hashlib.sha256(source.read_bytes()).hexdigest() != expected['sha256']
                or [e['id'] for e in selected] != expected['ids']):
            raise RuntimeError('Dataset or sample differs from frozen manifest')
        manifest['categories'][cat] = {'population': len(entries), 'ids': [e['id'] for e in selected],
                                     'data_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        answer_path = data / 'possible_answer' / f'BFCL_v4_{cat}.json'
        answers = {e['id']: e['ground_truth'] for e in map(json.loads, answer_path.read_text().splitlines())} if cat != 'irrelevance' else {}
        if cat != 'irrelevance':
            manifest['categories'][cat]['answer_sha256'] = hashlib.sha256(answer_path.read_bytes()).hexdigest()
        records = []
        for entry in selected:
            dest = a.output / cat / f"{entry['id']}.json"
            if a.rescore:
                row = json.loads(dest.read_text())
            elif dest.exists():
                raise RuntimeError(f'Refusing to overwrite {dest}; use a fresh output directory')
            else:
                start = time.monotonic()
                try:
                    result, metadata = handler.inference(copy.deepcopy(entry), True, False)
                    row = {'id': entry['id'], 'category': cat, 'result': result, 'metadata': metadata,
                           'request': handler.request, 'response': handler.response,
                           'elapsed_seconds': time.monotonic() - start}
                except Exception as exc:
                    raise RuntimeError(f'Inference failed for {entry["id"]}: {exc}') from exc
            if cat == 'irrelevance':
                score = _evaluate_single_relevance_entry(handler, entry['id'], row['result'], copy.deepcopy(entry), 'local-subset-FC', cat)
            else:
                score = _evaluate_single_ast_entry(handler, entry['id'], row['result'], answers[entry['id']], copy.deepcopy(entry), 'local-subset-FC', cat, Language.PYTHON, ReturnFormat.PYTHON)
            row['score'] = score
            dump(dest, row)
            records.append(row)
            print(f"{a.model} thinking={a.thinking} {entry['id']} correct={score['valid']}", flush=True)
        summary['categories'][cat] = {'correct': sum(r['score']['valid'] for r in records), 'n': len(records),
            'length_stopped': sum(r['response']['choices'][0]['finish_reason'] == 'length' for r in records),
            'reasoning_nonempty': sum(bool(r['response']['choices'][0]['message'].get('reasoning_content')) for r in records)}
    summary['correct'] = sum(c['correct'] for c in summary['categories'].values())
    summary['n'] = sum(c['n'] for c in summary['categories'].values())
    summary['accuracy_percent'] = 100 * summary['correct'] / summary['n']
    dump(a.output / 'summary.json', summary)
    dump(a.output / 'manifest.json', manifest)
    print(json.dumps(summary), flush=True)

if __name__ == '__main__':
    main()
