"""Make a compact chart of the local subset; vendor aggregates are a separate metric."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT/'results/audit.json').read_text())
parts = ['''<!doctype html><html lang="en"><meta charset="utf-8"><style>
body{color:var(--foreground);font-family:var(--font-sans);margin:0}
p{line-height:1.45}.note{color:var(--muted-foreground);font-size:13px}
.group{margin:18px 0}.label{font-weight:600;margin-bottom:6px}
.row{display:grid;grid-template-columns:35px 1fr 110px;align-items:center;gap:9px;margin:7px 0;font-size:13px}
.track{height:16px;background:var(--secondary);border-radius:3px;overflow:hidden}
.bar{height:16px;background:var(--chart-1)}.on{background:var(--chart-2)}
.value{text-align:right;font-variant-numeric:tabular-nums}
</style><body><p><strong>Local BFCL-V4 subset</strong><br>Correct out of the same 40 cases in four tool-calling categories.</p>''']
for size in ['0.8B','2B','4B']:
    parts.append(f'<div class="group"><div class="label">Qwen3.5-{size}, Q4_K_M</div>')
    for mode in ['off','on']:
        r = next(r for r in rows if r['model']==f'Qwen3.5-{size}-Q4_K_M' and r['thinking']==mode)
        value=f"{r['correct']}/40 · {r['percent']:g}%"
        parts.append(f'<div class="row" aria-label="Thinking {mode}: {value}"><span>{mode}</span><div class="track"><div class="bar {mode}" style="width:{r["percent"]}%"></div></div><span class="value">{value}</span></div>')
    parts.append('</div>')
parts.append('<p class="note">Apple M3 Ultra, 96 GB. Thinking off/on. These subset results are not the published full BFCL-V4 aggregate and do not measure memory extraction. Truncated responses remain scored by the official BFCL rules; details are in REPORT.md.</p></body></html>')
(ROOT/'results/comparison.html').write_text('\n'.join(parts)+'\n')
