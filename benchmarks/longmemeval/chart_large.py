"""Render the completed comparison as self-contained HTML, without a server."""
from pathlib import Path
import json

root = Path(__file__).resolve().parent
out = root / 'results/full'
data = json.loads((out / 'summary.json').read_text())
assert data['complete'], 'Do not present an incomplete run as the completed comparison'
systems = data['systems']
labels = [('bm25-standard', 'BM25'), ('dense-standard', 'Dense MiniLM'),
          ('mem0-raw-standard', 'Mem0 raw storage'), ('full-oracle', 'Oracle reference')]
rows = []
for index, (key, label) in enumerate(labels):
    item = systems[key]
    score = item['correct'] / item['n'] * 100
    low, high = [value * 100 for value in item['wilson95']]
    y = 45 + index * 65
    x = lambda value: 185 + value * 4.3
    rows.append(f'<text x="0" y="{y+5}" class="label">{label}</text>'
                f'<line x1="{x(low)}" x2="{x(high)}" y1="{y}" y2="{y}" class="interval"/>'
                f'<circle cx="{x(score)}" cy="{y}" r="5" class="point"/>'
                f'<text x="185" y="{y+23}" class="detail">{item["correct"]}/{item["n"]} · '
                f'{score:.1f}% · 95% Wilson {low:.1f}–{high:.1f}%</text>')
ticks = ''.join(f'<line x1="{185+t*4.3}" x2="{185+t*4.3}" y1="20" y2="265" class="grid"/>'
                f'<text x="{185+t*4.3}" y="290" text-anchor="middle" class="detail">{t}%</text>'
                for t in range(0, 101, 20))
audit = data['manual_audit']
html = '''<!doctype html><meta charset="utf-8"><style>
:root{font-family:var(--font-sans);color:var(--foreground)}
body{margin:0}svg{display:block;width:100%;height:320px;overflow:visible}
.grid{stroke:var(--border);stroke-width:1}.interval{stroke:var(--chart-1);stroke-width:3}
.point{fill:var(--chart-1)}text{fill:var(--foreground);font-family:var(--font-sans)}
.label{font-size:14px}.detail{font-size:12px;fill:var(--muted-foreground)}
p{font-size:14px;line-height:1.5;margin:12px 0}table{width:100%;border-collapse:collapse;font-size:13px}
td,th{text-align:left;vertical-align:top;padding:9px 5px;border-bottom:1px solid var(--border)}
th{font-weight:600}.note{color:var(--muted-foreground)}
</style>'''
html += '<p><strong>Local answer accuracy</strong> · Gemma 2 9B, 4-bit · Apple M1 Ultra, 64 GB</p>'
html += '<svg viewBox="0 0 650 310" role="img" aria-label="Local answer accuracy with 95 percent Wilson intervals">'
html += ticks + ''.join(rows) + '</svg>'
html += '''<p class="note">The three retrieval systems receive the same 300 full standard haystacks.
Oracle history is a separate, easier reference with its own official timestamps and only the cases
that fit the 8,192-token model window. Full standard-history reading fits 0/300 cases; accuracy is unavailable.</p>
<table><tr><th>Published anchor</th><th>Why it differs</th></tr>
<tr><td>Llama 3.1 8B: 45.4% standard; 71.0% Oracle, N=500</td>
<td>Different reader, context capacity, sample, prompts, and GPT-4o judge.</td></tr>
<tr><td>Mem0 managed: 94.4%, top-200 retrieval; headline N unstated</td>
<td>Local Mem0 is OSS raw storage with MiniLM, not the managed algorithm or fact extraction.</td></tr>
<tr><td>BM25: 71.0% session / 53.8% round Recall@10</td>
<td>Retrieval recall, not answer accuracy. No matched local QA comparator.</td></tr></table>'''
html += f'<p class="note">Direct agent review agreed with {audit["agree"]}/40 local judgments '
html += f'({audit["agreement"]*100:.1f}%). This is not independent human validation. '
html += f"Oracle judge scores include {systems['full-oracle'].get('empty_answer_positive', 0)} empty answers labeled positive; see the report sensitivity check. "
html += 'Three greedy local judge calls use the official prompts; repeated votes do not remove systematic errors.</p>'
(out / 'comparison.html').write_text(html)
print(out / 'comparison.html')
