"""Render completed local cells beside clearly labeled published reference figures."""
import html
from common import *
def rate(v):return f"{100*v:.2f}%"
def interval(v):return f"{100*v[0]:.2f}% to {100*v[1]:.2f}%"
def main():
 s=read(OUT/'summary.json');rows=[]
 for b in ['mab','halu']:
  for m in ['full-context','rag','bm25']:
   c=s[b][m];assert c['n']==150
   ref={'mab':{'full-context':'90.2% small-context GPT-4o-mini; 59.0% main table','rag':'63.0% Text-Embed-3-Small, main table','bm25':'74.6%, main table'},'halu':{m:'No same-baseline score; MemOS 67.23%, Mem0 53.02%' for m in ['full-context','rag','bm25']}}[b][m]
   rows.append(f"| {'MemoryAgentBench EventQA' if b=='mab' else 'HaluMem QA'} | {m} | {ref} | {c['correct']}/{c['n']} | {rate(c['accuracy'])} | {interval(c['wilson95'])} |")
 table='| Benchmark | Method | Published reference, different setup | Local correct / N | Local rate | 95% Wilson interval |\n| --- | --- | --- | --- | --- | --- |\n'+'\n'.join(rows)
 (OUT/'results-table.md').write_text(table+'\n')
 for file in ['README.md','REPORT.md']:
  p=ROOT/file;text=p.read_text();marker='\n<!-- completed-local-results -->\n'
  if marker in text:text=text.split(marker)[0]
  text+=marker+'\n## Completed local results\n\n'+table+'\n\nThese are privacy-transformed inputs. Confirmed false name masking affects 12 HaluMem questions and one reference; other false detections may remain. MiniLM truncates the semantic query representation for 111/150 EventQA items. Published references use different readers, embeddings, histories and scoring distributions. The HaluMem references evaluate different memory systems. These local rates cannot establish a same-system replication, LIGHT gain, operation-level hallucination accumulation or action completion. Wilson intervals treat questions as independent; see the paired cluster-bootstrap estimates below.\n'
  for b in ['mab','halu']:
   text+='\n'+b+': '
   text+='; '.join(f"{m} minus full context {100*d['difference']:+.2f} percentage points (paired cluster-bootstrap 95% {100*d['cluster_bootstrap95'][0]:+.2f} to {100*d['cluster_bootstrap95'][1]:+.2f}; {d['clusters']} clusters)" for m,d in s[b]['paired_differences_vs_full'].items())+'.\n'
  text+='\nHaluMem local QA labels, N=150 per method:\n\n| Method | Correct | Hallucination | Omission |\n| --- | --- | --- | --- |\n'
  for method in ['full-context','rag','bm25']:
   labels=s['halu'][method]['label_rates'];text+='| '+method+' | '+' | '.join(rate(labels[label]['rate'])+' ('+interval(labels[label]['wilson95'])+')' for label in ['Correct','Hallucination','Omission'])+' |\n'
  if (OUT/'manual-audit.json').exists():
   a=read(OUT/'manual-audit.json');agree=sum(x['agree'] for x in a['items']);n=len(a['items']);text+=f'\nTester hand audit of the local HaluMem judge: {agree}/{n} agreement ({100*agree/n:.1f}%; Wilson 95% {interval(wilson(agree,n))}). This was performed by the tester, not an independent human. Main automated labels are retained, including disagreements.\n'
  if file=='REPORT.md':
   for b,label in [('mab','EventQA'),('halu','HaluMem QA')]:
    a=s[b]
    qualification="The RAG encoder represented only the starts of 111 of 150 queries, and different histories and models mean this does not replicate the authors' full benchmark." if b=='mab' else "These QA inputs were altered for privacy, with ordinary words incorrectly masked in 12 items, so this does not reproduce the published memory systems or measure extraction and updating."
    text+=f"\nSuggested two-sentence replacement for the {label} performance qualification: “On 150 paired {label} questions, this book measured {rate(a['full-context']['accuracy'])} with full context, {rate(a['rag']['accuracy'])} with plain RAG and {rate(a['bm25']['accuracy'])} with BM25 using a local Qwen2.5-14B reader. {qualification}”\n"
  p.write_text(text)
 # The inline chart shows local rates only; published figures remain in the adjacent table.
 charts=[]
 for b,title in [('mab','MemoryAgentBench: small EventQA subset'),('halu','HaluMem: earlier-history QA subset')]:
  bars=[]
  for i,m in enumerate(['full-context','rag','bm25']):
   c=s[b][m];lo,hi=c['wilson95'];y=25+i*65;v=c['accuracy']*450
   bars.append(f'<text x="0" y="{y+19}" fill="var(--foreground)" font-size="13">{html.escape(m)}</text><rect x="115" y="{y}" width="{v:.1f}" height="25" rx="3" fill="var(--chart-{i+1})"/><line x1="{115+lo*450:.1f}" x2="{115+hi*450:.1f}" y1="{y+12}" y2="{y+12}" stroke="var(--foreground)" stroke-width="2"/><text x="{125+hi*450:.1f}" y="{y+18}" fill="var(--foreground)" font-size="13">{100*c["accuracy"]:.1f}%</text>')
  charts.append(f'<section><h3>{title}</h3><svg viewBox="0 0 700 220" role="img" aria-label="Local accuracy with question-level 95 percent Wilson intervals">'+''.join(bars)+'</svg></section>')
 page='<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;font-family:var(--font-sans)}h3{font-size:16px;font-weight:600;margin:12px 0 0}p{color:var(--muted-foreground);font-size:13px;line-height:1.5}svg{display:block;width:100%;height:220px}section{margin-bottom:16px}</style></head><body>'+''.join(charts)+'<p>150 identical questions per method in each benchmark. Lines show question-level 95% Wilson intervals; shared histories limit independence. Reader: Qwen2.5-14B-Instruct Q4_K_M. Inputs are privacy transformed, including confirmed false name masking in 12 HaluMem items; MiniLM truncates 111 EventQA query representations. Published figures use different setups and appear in the report table.</p></body></html>'
 (ROOT/'results.html').write_text(page)
 print(table)
if __name__=='__main__':main()
