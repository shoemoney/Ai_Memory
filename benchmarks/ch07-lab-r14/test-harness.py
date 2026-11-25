import importlib.util, json, subprocess, tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('lab', '/var/tmp/memlab-07/memtest.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
py='/var/tmp/memlab-07/venv/bin/python'; script='/var/tmp/memlab-07/memtest.py'
rows=[{'model': model,'case':n,'raw':json.dumps({'facts':[dict(zip(m.FIELDS,f)) for f in e]})} for model in ('stock','edited') for n,t,e in m.CASES]
with tempfile.TemporaryDirectory() as d:
 p=Path(d); (p/'responses.jsonl').write_text('\n'.join(map(json.dumps,rows)))
 (p/'memory.json').write_text('stale')
 # Invalid y/n and malformed tuple edits must re-prompt; reject plain note.
 answers='maybe\nn\n[42]\n\nx\nn\n'+ 'n\n\ny\n'*19
 result=subprocess.run([py,script,'review'],cwd=d,input=answers,text=True,capture_output=True)
 assert result.returncode==0,result.stderr
 assert not (p/'memory.json').exists()
 assert len((p/'reviewed.jsonl').read_text().splitlines())==20
 assert json.loads((p/'reviewed.json').read_text())[0]['disputed']
 assert "'disputed': 1" in result.stdout
 # Interrupted review retains completed rows and removes stale note.
 result=subprocess.run([py,script,'review'],cwd=d,input='n\n\ny\n',text=True,capture_output=True)
 assert result.returncode!=0
 assert len((p/'reviewed.jsonl').read_text().splitlines())==1
 # A wrong city is never written, including after an old note exists.
 rows[0]['raw']=rows[0]['raw'].replace('Denver','Boston')
 (p/'responses.jsonl').write_text('\n'.join(map(json.dumps,rows)))
 result=subprocess.run([py,script,'review'],cwd=d,input='n\n\ny\n'*20,text=True,capture_output=True)
 assert result.returncode==0,result.stderr
 assert not (p/'memory.json').exists()
print('PASS: retries, disputed totals, stale note, interrupted journal, wrong city')
