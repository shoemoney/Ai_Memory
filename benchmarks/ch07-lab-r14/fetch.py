import hashlib
import urllib.request
from pathlib import Path

ROOT = Path('/var/tmp/memlab-07')
MODELS = [
    ('stock', 'Qwen2.5-Coder-1.5B-Instruct-GGUF',
     '1af47f78b1f9b0c242fabe43f7a365d5a67f3207',
     'Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf',
     'f530705d447660a4336c329981af164b471b60b974b1d808d57e8ec9fe23b239'),
    ('edited', 'Qwen2.5-Coder-1.5B-Instruct-abliterated-GGUF',
     '823ab8183896816dec7d29899310b556e655ad73',
     'Qwen2.5-Coder-1.5B-Instruct-abliterated-Q4_K_M.gguf',
     '389b8172028c874b79a11358d258222dbce272b56ab3512ccc743893a25e06b4'),
]
for name, repo, revision, filename, expected in MODELS:
    path = ROOT / (name + '.gguf')
    url = f'https://huggingface.co/bartowski/{repo}/resolve/{revision}/{filename}'
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    with path.open('rb') as file:
        assert hashlib.file_digest(file, 'sha256').hexdigest() == expected
    print(name, 'verified', path.stat().st_size)
