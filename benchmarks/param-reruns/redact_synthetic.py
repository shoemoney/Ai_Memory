"""Keep benchmark-derived training text in scratch; export hashes for auditing."""
import hashlib,json,os,shutil
from common import ROOT,SCRATCH,rows


def main():
    for scope in ['cartridges','cartridges-smoke']:
        directory=ROOT/'results'/scope;source=directory/'synthetic.jsonl'
        if not source.exists():continue
        data=rows(source);destination=SCRATCH/scope/'synthetic-text.jsonl'
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
        records=[]
        for row in data:
            out={k:v for k,v in row.items() if k not in ['question','answer','output']}
            for key in ['question','answer','output']:
                out[key+'_sha256']=hashlib.sha256(row[key].encode()).hexdigest()
            records.append(out)
        index=directory/'synthetic-index.jsonl';temporary=index.with_suffix('.tmp')
        if index.exists():
            prior={r['index']:tuple(r[key+'_sha256'] for key in ['question','answer','output']) for r in rows(index)}
            assert prior=={r['index']:tuple(r[key+'_sha256'] for key in ['question','answer','output']) for r in records},'Regenerated training text changed; start a fresh cell instead of mixing trials'
        with temporary.open('w') as f:
            for row in records:f.write(json.dumps(row)+'\n')
            f.flush();os.fsync(f.fileno())
        os.replace(temporary,index)
        assert len(rows(index))==len(data)
        source.unlink()
    print('Training text retained only in owned scratch; hashes exported.')

if __name__=='__main__':main()
