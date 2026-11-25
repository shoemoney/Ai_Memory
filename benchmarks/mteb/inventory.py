#!/usr/bin/env python3
"""Read chapter citations without modifying the book; retain benchmark claim inventory."""
from pathlib import Path
import hashlib
from html import unescape
import json
import re
ROOT = Path(__file__).resolve().parent

def plain(s):
    s = re.sub(r'<sup\b.*?</sup>', '', s, flags=re.S)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', s))).strip()

out = []
chapters = []
for chapter in ['03-text-embeddings', '04-multimodal-embeddings', '05-retrieval-techniques']:
    data = (ROOT.parents[1]/'build'/'chapters'/(chapter+'.html')).read_bytes()
    html = data.decode()
    chapters.append({'chapter': chapter+'.html', 'sha256': hashlib.sha256(data).hexdigest()})
    sources = {}
    for ident, fragment in re.findall(r'<li id="(s\d+-\d+)">(.*?)</li>', html, re.S):
        sources[ident] = re.findall(r'href="(https?[^\"]+)"', fragment)
    fragments = []
    if chapter.startswith('03'):
        table = html.split('Scores reported by each source (benchmark versions differ)', 1)[1].split('</table>', 1)[0]
        fragments += re.findall(r'<tr>(.*?)</tr>', table, re.S)[1:]
        fragments += [s for s in re.findall(r'<(?:p|li)>(.*?)</(?:p|li)>', html, re.S)
                      if ('68.46' in s or '1 to 5 points' in s)]
    elif chapter.startswith('04'):
        fragments += [s for s in re.findall(r'<tr>(.*?)</tr>', html, re.S) if '67.88 vs 70.58' in s]
    for fragment in fragments:
        refs = re.findall(r'href="#(s\d+-\d+)"', fragment)
        out.append({'chapter': chapter+'.html', 'chapter_sha256': hashlib.sha256(data).hexdigest(),
                    'sentence_or_table_row': plain(fragment),
                    'sources': {r: sources.get(r, []) for r in refs}})
(ROOT/'chapters.json').write_text(json.dumps(chapters,indent=2)+'\n')
(ROOT/'claims.json').write_text(json.dumps(out, indent=2)+'\n')
print('Recorded', len(out), 'benchmark claims; chapter 05 has no MTEB/MMTEB score.')
