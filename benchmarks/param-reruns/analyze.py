"""Recompute all headline rates from paired, checkpointed raw answers."""
import json, re
from common import ROOT, rows, interval, paired

def compare(path, names, idkey):
    data=rows(path); cells={name:{} for name in names}
    for r in data:
        if r['system'] not in cells: raise ValueError('Unexpected system')
        if r[idkey] in cells[r['system']]: raise ValueError('Duplicate item')
        cells[r['system']][r[idkey]]=r
    ids=sorted(set.intersection(*(set(x) for x in cells.values())))
    if not ids: return {'n':0,'status':'no completed pairs'}
    if any(len(x)!=len(ids) for x in cells.values()): raise ValueError('Unpaired results')
    a,b=names
    result={'n':len(ids),'systems':{name:interval([cells[name][i]['score'] for i in ids]) for name in names},'paired':paired([cells[a][i]['score'] for i in ids],[cells[b][i]['score'] for i in ids]),'seconds':{name:sum(cells[name][i]['seconds'] for i in ids) for name in names}}
    if 'cache_bytes' in data[0]:
        result['cache_ratio_mean']=sum(cells[a][i]['cache_bytes']/cells[b][i]['cache_bytes'] for i in ids)/len(ids)
        result['cache_bytes_ranges']={name:[min(cells[name][i]['cache_bytes'] for i in ids),max(cells[name][i]['cache_bytes'] for i in ids)] for name in names}
        result['cache_bytes_means']={name:sum(cells[name][i]['cache_bytes'] for i in ids)/len(ids) for name in names}
        result['cache_ratio_of_means']=result['cache_bytes_means'][a]/result['cache_bytes_means'][b]
        result['cache_ratio_range']=[min(cells[a][i]['cache_bytes']/cells[b][i]['cache_bytes'] for i in ids),max(cells[a][i]['cache_bytes']/cells[b][i]['cache_bytes'] for i in ids)]
        result['document_tokens']=data[0]['document_tokens']; result['cartridge_tokens']=data[0]['cartridge_tokens']
        result['corpus_only_cache_ratio']=data[0]['document_tokens']/data[0]['cartridge_tokens']
    else:
        result['token_limit_counts']={name:sum(cells[name][i]['limit_reached'] for i in ids) for name in names}
        if data[0].get('protocol')=='closed-book-diagnostic':
            result['tagged_answer_counts']={name:sum(bool(re.search(r'<answer>(.*?)</answer>',cells[name][i]['output'],re.S)) for i in ids) for name in names}
    return result

if __name__=='__main__':
    result={name:compare(ROOT/'results'/(name+'.jsonl'),['base','memgen'],'source_index') for name in ['gsm8k','triviaqa']}
    result['cartridges']=compare(ROOT/'results'/'cartridges'/'answers.jsonl',['context','cartridge'],'id')
    (ROOT/'results'/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
