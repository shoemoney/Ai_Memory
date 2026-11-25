"""Read-only local progress; use log path as the first argument."""
import json
from pathlib import Path
import re
import sys
p = Path(sys.argv[1])
s = p.read_text(errors='replace') if p.exists() else ''
progress = re.findall(r'(Batch Encoding|NER|Extracting triples):\s+(\d+)%[^\r\n]*', s)
print('Latest:', ' '.join(progress[-1]) if progress else s[-500:])
for f in (Path(__file__).parent/'hipporag2/results').glob('*.jsonl'):
    if f.stem not in ['hipporag2','dense']: continue
    print(f.stem, sum(1 for _ in f.open()), 'checkpointed questions')
if 'Traceback' in s:
    print(s[s.rfind('Traceback'):][-1200:])

issues=[line for line in s.splitlines() if any(term in line.lower() for term in ['openie response does not','exception for chunk','ner failed','triple extraction failed'])]
print('Extraction error messages:', len(issues))
for line in issues[-3:]: print(line[-400:])
