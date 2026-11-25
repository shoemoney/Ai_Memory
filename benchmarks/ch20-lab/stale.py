import json
import time
from lab import ROOT, SESSIONS, QUESTIONS, CACHE, bound, chat

rows = []
for rep in range(1, 4):
    CACHE.flush_all()
    question = QUESTIONS[6]['question']
    old = bound([s['date']+'\n'+s['text'] for s in SESSIONS[:2][::-1]])
    new = bound([s['date']+'\n'+s['text'] for s in SESSIONS[6:7]])
    # Deliberately incomplete key: no data version.
    key = 'ivo:qwen38:t0:s7:drink-now'
    started = time.perf_counter()
    answer, nt, response = chat(question, old)
    CACHE.set(key, answer.encode(), expire=3600)
    cold = time.perf_counter()-started
    started = time.perf_counter()
    stale = CACHE.get(key).decode()
    hit = time.perf_counter()-started
    fixed, nfixed, fixed_response = chat(question, new)
    assert 'coffee' in answer.lower() and stale == answer
    assert 'mint tea' in fixed.lower() and 'coffee' not in fixed.lower()
    CACHE.set(key+':version7', fixed.encode(), expire=3600)
    started = time.perf_counter()
    versioned = CACHE.get(key+':version7').decode()
    versioned_hit = time.perf_counter()-started
    assert versioned == fixed
    rows.append(dict(rep=rep,old=answer,stale=stale,fixed=fixed,
                     cold_s=cold,hit_s=hit,versioned=versioned,
                     versioned_hit_s=versioned_hit,prompt_tokens=nt,
                     fixed_tokens=nfixed,response=response,fixed_response=fixed_response))
    print(rep, 'before:', answer, 'stale:', stale, 'version7 hit:', versioned,
          'cold/stale/versioned_s:', round(cold,4), round(hit,6), round(versioned_hit,6))
(ROOT / 'stale.json').write_text(json.dumps(rows,indent=2))
