"""Local direct and DC-Cumulative, all 100 public standard puzzles, no judge."""
import ast,collections,hashlib,json,os,re,resource,subprocess,sys,tempfile,urllib.request
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
HERE=Path(__file__).resolve().parent
REV='dfc146f81138b9bcd70069196545015e40be122b'
def dataset():
    import pyarrow.parquet as pq
    scratch=Path(os.environ.get('SCRATCH','/data/scratch/membench/small-reruns'));scratch.mkdir(parents=True,exist_ok=True)
    p=scratch/'game24.parquet'
    if not p.exists():urllib.request.urlretrieve(f'https://huggingface.co/datasets/turingmachine/meta-prompting/resolve/{REV}/data/GameOf24-00000-of-00001.parquet',p)
    assert hashlib.sha256(p.read_bytes()).hexdigest()=='047e74473a0a9b316072fe85bb837de6e5d8139e0178e9742a291d6a81d5de6b'
    return pq.read_table(p).to_pylist()
def score(numbers,answer):
    answer=answer.split('=')[0].strip().replace('×','*').replace('÷','/').replace('x','*')
    try:
        t=ast.parse(answer,mode='eval');nums=[]
        def ev(n):
            if isinstance(n,ast.Constant) and type(n.value)==int and n.value>=0:nums.append(n.value);return Fraction(n.value)
            if isinstance(n,ast.BinOp) and type(n.op) in (ast.Add,ast.Sub,ast.Mult,ast.Div):
                a,b=ev(n.left),ev(n.right)
                if isinstance(n.op,ast.Add):return a+b
                if isinstance(n.op,ast.Sub):return a-b
                if isinstance(n.op,ast.Mult):return a*b
                return a/b
            raise ValueError('unsupported arithmetic')
        val=ev(t.body)
        return val==24 and sorted(nums)==sorted(map(int,numbers.split()))
    except (Exception,):return False

def execute(text):
    blocks=re.findall(r'```python\s*\n(.*?)```',text,re.S)
    if not blocks:return 'No Python block found.'
    code=blocks[-1]
    try:
        t=ast.parse(code)
        for node in ast.walk(t):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module]
                if any(n not in {'itertools','fractions','math','functools','operator','collections'} for n in names):raise ValueError('import not allowed')
            if isinstance(node,ast.Attribute) and node.attr.startswith('_'):raise ValueError('private attribute')
            if isinstance(node,ast.Name) and (node.id.startswith('_') or node.id in {'open','exec','eval','compile','getattr','setattr','globals','locals','vars','input','breakpoint','help','exit','quit'}):raise ValueError('name not allowed')
        def limit():
            resource.setrlimit(resource.RLIMIT_CPU,(3,3));resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
        with tempfile.TemporaryDirectory(prefix='membench-small-reruns-',dir='/var/tmp') as d:
            p=subprocess.run([sys.executable,'-I','-c',code],cwd=d,text=True,capture_output=True,timeout=5,preexec_fn=limit)
        return (p.stdout+p.stderr)[-12000:]
    except Exception as e:return 'Execution error: '+str(e)
def answer(text):
    a=re.findall(r'<answer>(.*?)</answer>',text,re.S)
    return a[-1].strip() if a else text.strip()
def run():
    data=dataset();out=HERE/'results.jsonl';rows=[json.loads(x) for x in out.read_text().splitlines()] if out.exists() else []
    done={(r['id'],r['arm']):r for r in rows};memory='(empty)'
    generator=(HERE/'generator_prompt.txt').read_text();curator=(HERE/'curator_prompt_for_dc_cumulative.txt').read_text()
    for i,item in enumerate(data):
        question="Use each of these four integers exactly once with +, -, *, / and parentheses to make 24. Present a single expression: "+item['input']
        for arm in ['direct','dc_cumulative']:
            if (i,arm) in done:
                if arm=='dc_cumulative':memory=done[i,arm]['memory_after']
                continue
            prompt=question+'\nReturn only the expression, without explanation.' if arm=='direct' else generator.replace('[[QUESTION]]',question).replace('[[CHEATSHEET]]',memory)
            text,seconds,usage,finish=chat(prompt)
            trace=[text];executions=[]
            if arm!='direct' and 'EXECUTE CODE!' in text:
                codeout=execute(text);executions.append(codeout)
                messages=[{'role':'user','content':prompt},{'role':'assistant','content':text},{'role':'user','content':'Python execution output:\n'+codeout+'\nNow give the final answer in <answer> tags.'}]
                text,s,u,finish=chat('',messages=messages);seconds+=s;trace.append(text)
            a=answer(text);correct=score(item['input'],a)
            row={'id':i,'arm':arm,'answer':a,'correct':correct,'seconds':seconds,'finish_reason':finish,'trace':trace,'execution':executions,'usage_first_call':usage}
            if arm!='direct':
                # No score or gold answer enters the curator.
                cp=curator.replace('[[PREVIOUS_CHEATSHEET]]',memory).replace('[[QUESTION]]',question).replace('[[MODEL_ANSWER]]','\n'.join(trace))
                cur,cs,cu,cf=chat(cp+'\nKeep the updated cheatsheet under 200 words, including code, and close the cheatsheet tag.',max_tokens=512)
                parsed=re.findall(r'<cheatsheet>(.*?)</cheatsheet>',cur,re.S)
                memory=parsed[-1].strip() if parsed else memory
                row.update(memory_after=memory,curation=cur,curation_seconds=cs,curation_finish_reason=cf)
            append(out,row);done[i,arm]=row
            print(i,arm,correct,round(seconds,2),flush=True)
    a=[done[i,'direct']['correct'] for i in range(len(data))];b=[done[i,'dc_cumulative']['correct'] for i in range(len(data))]
    summary={'model':'Qwen2.5-3B-Instruct Q4_K_M','n':len(data),'dataset_revision':REV,'arms':{name:{'correct':sum(vals),'rate':sum(vals)/len(vals),'exact_95':interval(sum(vals),len(vals))} for name,vals in [('direct',a),('dc_cumulative',b)]},'paired':paired(a,b)}
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
if __name__=='__main__':run()
