"""Combine validated storage and model cells without claiming benchmark equivalence."""
import hashlib,html,json,pathlib
from model_summary import summarize as model_summary
from summarize import summarize as storage_summary
ROOT=pathlib.Path(__file__).parent

def main():
 storage=storage_summary(ROOT/'results');models=model_summary(ROOT/'results/model');cells=models['cells']
 refs=[('MINJA','final targeted search',70,'70% attack, secondary restatement'),('AgentPoison','triggered targeted answer',80,'>80% attack'),('InjecMEM','target joint targeted answer',35.6,'35.6% joint in the paper; no chapter ASR'),('Embedding inversion','exact recovery step 5',92,'92% GTR/Natural Questions')]
 headline=[]
 def pick(family,measure,arm):return next(r for r in cells if r['family']==family and r['measure']==measure and r['arm']==arm)
 for family,measure,published,label in refs:
  headline.append({'family':family,'measure':measure,'published_reference_pct':published,'published_label':label,'undefended':pick(family,measure,'undefended'),'defended':pick(family,measure,'defended')})
 study={'study_kind':'Pinned storage conformance plus local toy-model attack transfers and learned inversion','model_headlines':headline,'storage':{'native_accepted':sum(r['attack_successes'] for r in storage if not r['defended']),'native_n':sum(r['n'] for r in storage if not r['defended']),'wrapper_accepted':sum(r['attack_successes'] for r in storage if r['defended']),'wrapper_n':sum(r['n'] for r in storage if r['defended']),'cells':len(storage)},'benign_write_review':models['benign_write_review'],'review_audit_n':models['review_audit']['n'],'raw_file_sha256':models['raw_file_sha256']}
 (ROOT/'results/study-summary.json').write_text(json.dumps(study,indent=2)+'\n')
 comparison=(ROOT/'results/model/summary.md').read_text()
 mn_u=pick('MINJA','final targeted search','undefended');mn_d=pick('MINJA','final targeted search','defended')
 comparison+=f"\nMINJA ordinary search utility: {mn_u['task_successes']}/{mn_u['n']} undefended versus {mn_d['task_successes']}/{mn_d['n']} defended. Both arms had zero target redirections, so this cell shows a utility cost without demonstrated ASR benefit.\n"
 s=study['storage'];comparison+=f"\nStorage: native accepted {s['native_accepted']}/{s['native_n']}; external-chain wrapper accepted {s['wrapper_accepted']}/{s['wrapper_n']}, across 15 edits and 100 repetitions per cell.\n"
 comparison+='\nAll model comparisons use different local setups from the published references. Detailed counts, controls and limits are in README.md, REPORT.md and STUDY_PROTOCOL.md.\n'
 (ROOT/'results/study-summary.md').write_text(comparison)
 claims=json.loads((ROOT/'results/claims.json').read_text())
 for claim in claims:
  if claim['topic'] in ['MINJA','AgentPoison','InjecMEM','embedding inversion']:
   family='Embedding inversion' if claim['topic']=='embedding inversion' else claim['topic'];h=next(x for x in headline if x['family']==family)
   claim['local_n']=h['undefended']['n'];claim['local_undefended']=h['undefended'];claim['local_defended']=h['defended'];claim['local']='model/summary.json'
 (ROOT/'results/claims.json').write_text(json.dumps(claims,indent=2)+'\n')
 fragments=[]
 for i,h in enumerate(headline):
  y=38+i*100
  fragments.append(f'<text x="0" y="{y+23}">{html.escape(h["family"])}</text>')
  values=[(h['published_reference_pct'],'var(--muted-foreground)',h['published_label'],None)]
  for arm,color in [('undefended','var(--chart-1)'),('defended','var(--chart-2)')]:
   c=h[arm];values.append((c['rate_pct'],color,f"{c['successes']}/{c['n']} ({c['rate_pct']:.1f}%; 95% {c['wilson_95_pct'][0]:.2f}–{c['wilson_95_pct'][1]:.2f}%)",c['wilson_95_pct']))
  for offset,(value,color,label,interval) in enumerate(values):
   yy=y+offset*21;fragments.append(f'<rect x="170" y="{yy}" width="{value*3.1}" height="13" fill="{color}"/><text x="490" y="{yy+11}" font-size="11">{html.escape(label)}</text>')
   if interval:
    lo,hi=(170+x*3.1 for x in interval);fragments.append(f'<path d="M {lo:.1f} {yy+6} H {hi:.1f} M {lo:.1f} {yy+2} V {yy+11} M {hi:.1f} {yy+2} V {yy+11}" fill="none" stroke="var(--foreground)" stroke-width="1"/>')
  if h['family']=='AgentPoison':fragments.append(f'<line x1="418" x2="480" y1="{y+6}" y2="{y+6}" stroke="var(--muted-foreground)" stroke-dasharray="3 3"/>')
 chart='<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:var(--font-sans);color:var(--foreground);min-height:0;margin:0}p{font-size:13px;color:var(--muted-foreground)}svg{width:100%;height:455px}text{fill:var(--foreground);font-family:var(--font-sans);font-size:12px}.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px}</style></head><body><p>Published references and completed local toy experiments. The model, dataset and attack-budget differences prevent direct replication claims.</p><div class="legend"><span style="color:var(--muted-foreground)">Published reference</span><span style="color:var(--chart-1)">Local undefended</span><span style="color:var(--chart-2)">Local defended</span></div><svg role="img" aria-label="Four attack-family comparisons; published figures have different experimental setups from local results." viewBox="0 0 720 455">'+''.join(fragments)+'<text x="170" y="450">0%</text><text x="450" y="450">100%</text></svg><p>Local headline sample sizes are printed on each bar. Local whiskers show Wilson 95% intervals; benign controls are in the report. Storage tests: '+f"{s['native_accepted']}/{s['native_n']} native edits accepted; {s['wrapper_accepted']}/{s['wrapper_n']} accepted by the external-chain wrapper. Each storage cell has N=100: native 100% (95% 96.3–100%), wrapper 0% (0–3.7%)."+f" MINJA ordinary-search utility: {mn_u['task_successes']}/{mn_u['n']} undefended, {mn_d['task_successes']}/{mn_d['n']} defended."+'</p></body></html>'
 review=models['benign_write_review'];chart=chart.replace('<div class="legend">',f"<p style=\"color:var(--warning,#a16207)\"><strong>Prompt-defense utility failure:</strong> write review accepted {review['accepted']}/{review['n']} benign factual proposals. Zero defended ASR does not demonstrate a useful selective write policy here.</p><div class=\"legend\">")
 inv_u=pick('Embedding inversion','exact recovery step 5','undefended');inv_d=pick('Embedding inversion','exact recovery step 5','defended');chart=chart.replace('</body>',f"<p>Inversion partial reconstruction: mean word F1 {inv_u['mean_word_f1']:.3f} undefended versus {inv_d['mean_word_f1']:.3f} with source exclusion. This is supplementary word overlap, not exact recovery or a semantic-search utility test.</p></body>")
 im_u=pick('InjecMEM','target joint targeted answer','undefended');im_d=pick('InjecMEM','target joint targeted answer','defended')
 chart=chart.replace('</body>',f"<p>InjecMEM poison recall: {im_u['retrieval_successes']}/{im_u['n']} undefended, {im_d['retrieval_successes']}/{im_d['n']} defended. A zero-exposure cell cannot estimate conditional payload success.</p></body>")
 for name,color in [('foreground','#111827'),('muted-foreground','#6b7280'),('chart-1','#2563eb'),('chart-2','#059669'),('font-sans','system-ui')]:chart=chart.replace('var(--'+name+')','var(--'+name+','+color+')')
 (ROOT/'results/study-comparison.html').write_text(chart)
 validation={'storage_cells':len(storage),'storage_valid_outcomes':sum(c['n'] for c in storage),'all_model_cells_complete':True,'model_headline_cells':8,'model_headline_outcomes':sum(h[a]['n'] for h in headline for a in ['undefended','defended']),'review_audit_n':models['review_audit']['n'],'write_review_benign_accepted':models['benign_write_review']['accepted'],'write_review_benign_n':models['benign_write_review']['n'],'write_review_rejected_all_tested_benign':models['benign_write_review']['accepted']==0,'model_file_sha256':models['raw_file_sha256'],'shipped_harness_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ['*.py','*.sh','*.lock'] for p in sorted(ROOT.glob(pattern))}}
 (ROOT/'results/study-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 print(comparison)
if __name__=='__main__':main()
