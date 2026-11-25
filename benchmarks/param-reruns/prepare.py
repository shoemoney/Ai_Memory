"""Fetch pinned primary sources, small model and evaluation data into owned scratch."""
import hashlib, json, os, subprocess
from pathlib import Path
from urllib.request import urlopen
ROOT = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get('PARAM_SCRATCH', '/data/scratch/membench/param-reruns'))
os.environ['HF_HOME'] = str(SCRATCH / 'hf')
REPOS = {'MemGen': ('KANABOON1/MemGen', '30a758eef848f15f9b30a8fa2747d9e66e7be5db'),
         'cartridges': ('HazyResearch/cartridges', 'ef34ba97a06049c34820506e2c283746284ae5f0')}

def fetch(url):
    return urlopen(url, timeout=120).read()

def main():
    from huggingface_hub import HfApi, snapshot_download
    from datasets import load_dataset
    SCRATCH.mkdir(parents=True, exist_ok=True)
    manifest = {'code': {}, 'models': {}, 'datasets': {}}
    pinned = json.loads((ROOT/'results'/'sources.json').read_text()) if (ROOT/'results'/'sources.json').exists() else {}
    for name, (repo, rev) in REPOS.items():
        dest = SCRATCH / name
        if not dest.exists():
            subprocess.run(['git', 'clone', 'https://github.com/' + repo, str(dest)], check=True)
        subprocess.run(['git', '-C', str(dest), 'checkout', rev], check=True, capture_output=True)
        manifest['code'][name] = {'url': 'https://github.com/' + repo, 'revision': rev}
    api = HfApi()
    for model, patterns in [('Qwen/Qwen2.5-1.5B-Instruct', ['*.json', '*.safetensors', '*.txt', '*.jinja']),
                            ('Kana-s/MemGen', ['Qwen2.5-1.5B-Instruct/gsm8k/weaver-grpo/**', 'Qwen2.5-1.5B-Instruct/triviaqa/weaver-sft/**'])]:
        info = api.model_info(model, revision=pinned.get('models', {}).get(model, {}).get('revision'))
        dest = SCRATCH / ('base' if model.startswith('Qwen/') else 'checkpoints')
        snapshot_download(model, revision=info.sha, allow_patterns=patterns, local_dir=dest)
        manifest['models'][model] = {'revision': info.sha, 'license': getattr(info.card_data, 'license', None)}
    for name, config, split in [('openai/gsm8k', 'main', 'test'), ('mandarjoshi/trivia_qa', 'rc.wikipedia.nocontext', 'validation')]:
        label = 'gsm8k' if 'gsm8k' in name else 'triviaqa'
        info = api.dataset_info(name, revision=pinned.get('datasets', {}).get(label, {}).get('revision'))
        data = load_dataset(name, config, split=split, revision=info.sha)
        # A fixed seeded sample without replacement. Sort sample indices to retain source order.
        import random
        indices = sorted(random.Random(42).sample(range(len(data)), 150))
        label = 'gsm8k' if 'gsm8k' in name else 'triviaqa'
        with (SCRATCH / (label + '.jsonl')).open('w') as f:
            for i in indices:
                row = data[i]
                row['source_index'] = i
                f.write(json.dumps(row) + '\n')
        manifest['datasets'][label] = {'id': name, 'revision': info.sha, 'config': config, 'split': split, 'population': len(data), 'n': 150, 'seed': 42, 'indices': indices, 'license': getattr(info.card_data, 'license', None)}
    info = json.loads(fetch('https://api.github.com/repos/kbressem/LongHealth/commits/main'))
    rev = pinned.get('datasets', {}).get('longhealth', {}).get('revision', info['sha'])
    raw = fetch(f'https://raw.githubusercontent.com/kbressem/LongHealth/{rev}/data/benchmark_v5.json')
    (SCRATCH / 'longhealth.json').write_bytes(raw)
    manifest['datasets']['longhealth'] = {'url': f'https://github.com/kbressem/LongHealth/blob/{rev}/data/benchmark_v5.json', 'revision': rev, 'sha256': hashlib.sha256(raw).hexdigest(), 'license': 'Apache-2.0 (repository LICENSE)', 'selection': 'patient_01, complete document set and all questions'}
    (ROOT / 'results' / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    main()
