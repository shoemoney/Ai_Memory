venv/bin/python memtest.py run
venv/bin/python memtest.py review
venv/bin/python - <<'PY'
import json
from pathlib import Path
from time import perf_counter
from memtest import CASES, CHECK, FIELDS
start = perf_counter()
note = json.loads(Path('memory.json').read_text())
elapsed = perf_counter() - start
CHECK.validate(note)
facts = {tuple(f[k] for k in FIELDS) for f in note['facts']}
assert facts == set(CASES[0][2])
print(note)
print('Read ms:', round(elapsed * 1000, 3))
PY
