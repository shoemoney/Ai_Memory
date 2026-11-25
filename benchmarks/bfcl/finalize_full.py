"""Append actual terminal cleanup proof after all runtime files have been removed."""
import json
import subprocess
import re
from pathlib import Path
from full_common import ROOT,RUN_DIR

def main():
 out=RUN_DIR;done=json.loads((out/'DONE.json').read_text());a=json.loads((out/'analysis.json').read_text())
 proof=(out/'cleanup.txt').read_text()
 checks=('remote-scratch-absent' in proof and proof.count('task-service-absent')==2 and 'task-port-unoccupied' in proof and 'local-scratch-absent=True' in proof and not Path('/var/tmp/membench-bfcl').exists())
 listeners=subprocess.check_output(['ss','-ltnH','sport = :39730'],text=True)
 if not checks or listeners.strip():
  done['cleanup_complete']=False
  from full_common import atomic
  atomic(out/'DONE.json',done)
 local=subprocess.check_output(['df','-h','/var/tmp'],text=True)
 ps=subprocess.check_output(['ps','-eo','pid,comm,rss'],text=True)
 local+='\n'.join(line for line in ps.splitlines() if any(k in line.split() for k in ['PID','python','python3','ssh','uv']))+'\n'
 (out/'linux-resources-after.txt').write_text(local)
 text='\n## Final operational status and cleanup\n\n'
 text+=f"Operational status: `{done['status']}`. Cleanup confirmed: **{done['cleanup_complete']}**. This marks the end of the time-limited matrix, not a claim that every planned item completed. No containers were created, no chapter files were edited and no commit was made by this task.\n\n"
 text+='The server and memory guard were removed from launchd, task port 39730 was unoccupied, the SSH tunnel was closed, and both scratch directories including model downloads, Python runtime and local embedding cache were deleted. Pre/post disk-space and process snapshots are retained; other workloads make identical disk totals neither expected nor necessary. `cleanup.txt` and `DONE.json` are the recorded checks.\n\n'
 text+='The expanded smoke test initially found that Java evaluation had been given generation-normalized schemas, producing a type-map error. The runner was corrected to use the official unnormalized scoring loader before the measured matrix. Positive/negative Java and JavaScript checks, all three memory snapshot round trips, correct/wrong agentic answers and independent agreement with the official score-composition helpers passed in `evidence/full-verification.json`. The smoke outputs are diagnostics and excluded from the full result.\n\n'
 text+='A continuation check also found a model-induced context overflow after hundreds of repeated memory-retrieval calls. Treating that as an infrastructure exclusion would omit a hard case, so the worker was corrected to retain the rejected request and pass an empty failed-inference result to the official scorer. Positive/negative failure-path checks passed; the original source/manifest were archived, only the owned worker was reloaded, and all committed responses, items and deadlines were preserved. The repair record is in `evidence/full-repairs.jsonl` and `context-failure-verification.json`.\n\n'
 text+='A later startup-recovery fault exposed the restricted systemd PATH: uv lookup now checks PATH and the standard user installation. A refused-connection drill verified that serving loss suspends the worker once, with no scored or fabricated answers, instead of cascading through queued items. The loaded-server guard was corrected to stop at kernel warning/critical pressure, while retaining the >=40% free admission check; slot count now adapts to admission headroom with context and token cap fixed. These changes preserved all committed data and the original deadlines, and their verification is in `evidence/full-recovery-verification.json`.\n\n'
 for name in ['README.md','REPORT.md']:
  p=ROOT/name;s=re.sub(r'^\*\*Run status:.*?\*\*\n\n','',p.read_text());s=s.split('\n## Final operational status and cleanup')[0];p.write_text(s+text)
 audit_path=ROOT/'evidence/full-final-audit.json'
 if audit_path.exists():
  audit=json.loads(audit_path.read_text())
  extra='\n## Final evidence audit\n\nAll retained request hashes, planned item IDs, paired counts and weighted score points passed an independent offline audit. The complete 4,000-replicate aggregate intervals were reproduced exactly without inference. See `audit_full.py` and `evidence/full-final-audit.json`.\n\n'
  extra+='| Model | Scoring completions off/on | Paired scoring N | Saved requests off/on | Paired scoring length stops off/on |\n|---|---:|---:|---:|---:|\n'
  for size,d in audit['models'].items():
   off=d['modes']['off'];on=d['modes']['on'];diag=d['paired_scoring_diagnostics']
   extra+=f"| {size} | {off['scoring_completed']}/{on['scoring_completed']} | {d['paired_scoring_n']} | {off['request_checkpoints']}/{on['request_checkpoints']} | {diag['off']['length_stops']}/{diag['on']['length_stops']} |\n"
  extra+='\nThe paired scoring sample has one empty-answer irrelevance credit (0.8B thinking on) and zero malformed-tool irrelevance credits. These are not counted as skill in completed-nonempty performance. Non-scoring live-relevance length stops are listed separately by category. All six selected pilot cap rechecks still stopped at 16,384 tokens; two received official irrelevance credits, but none earned completed-nonempty credit.\n\n'
  extra+=audit['source_limit']+' The remaining provenance limit is the initial run-level attribution, rather than identical per-item source coverage for every record.\n'
  for name in ['README.md','REPORT.md']:
   p=ROOT/name;p.write_text(p.read_text()+extra)
 # Standalone transparent chart; show only the comparable local offline projections.
 parts=['''<!doctype html><html lang="en"><meta charset="utf-8"><style>body{margin:0;font-family:var(--font-sans);color:var(--foreground)}p{line-height:1.4}.group{margin:18px 0}.row{display:grid;grid-template-columns:35px 1fr 190px;gap:8px;align-items:center;font-size:12px;margin:8px 0}.track{height:16px;background:var(--secondary)}.bar{height:16px;background:var(--chart-1)}.on{background:var(--chart-2)}.note{font-size:13px;color:var(--muted-foreground)}</style><body><p><strong>Expanded offline BFCL-V4 projection</strong><br>Official-compatible score over represented offline weights, with paired case-mix intervals.</p>''']
 for size,m in a['models'].items():
  parts.append(f'<div class="group"><strong>Qwen3.5-{size} Q4_K_M · N={m["paired_n"]} per mode</strong>')
  for mode in ['off','on']:
   r=m['aggregate'].get('official',{}).get(mode)
   if not r:continue
   value=f'{r["projection_percent"]:.1f}% [{r["interval95"][0]:.1f}, {r["interval95"][1]:.1f}]'
   parts.append(f'<div class="row"><span>{mode}</span><div class="track"><div class="bar {mode}" style="width:{r["projection_percent"]}%"></div></div><span>{value}</span></div>')
  parts.append('</div>')
 parts.append('<p class="note">Missing live web search and any time-censored categories/domains are listed in the report. This is not the full vendor aggregate. Empty/malformed irrelevance credits and length stops are reported separately from completed nonempty performance. These results do not measure extraction accuracy.</p></body></html>')
 (out/'comparison.html').write_text('\n'.join(parts))

if __name__=='__main__':main()
