import hashlib,json
import lab
from pathlib import Path
# Exercise the exact identity expression used by stage(), against real Memcached.
def key(revision,settings):
 old_revision,old_settings=lab.EMBEDDING_REVISION,lab.RETRIEVAL
 lab.EMBEDDING_REVISION,lab.RETRIEVAL=revision,settings
 try:
  return lab.cache_key(4,12,lab.QUESTIONS[0])
 finally:
  lab.EMBEDDING_REVISION,lab.RETRIEVAL=old_revision,old_settings
lab.CACHE.flush_all()
k=key(lab.EMBEDDING_REVISION,lab.RETRIEVAL)
lab.CACHE.set(k,b'cached-answer')
assert lab.CACHE.get(key(lab.EMBEDDING_REVISION,lab.RETRIEVAL))==b'cached-answer'
assert lab.CACHE.get(key('changed-revision',lab.RETRIEVAL)) is None
assert lab.CACHE.get(key(lab.EMBEDDING_REVISION,dict(lab.RETRIEVAL,budget=599))) is None
print('Cache identity: unchanged hit; embedding revision miss; retrieval budget miss.',flush=True)
# Before and after deletion: same SQL filters and recall() as the chapter.
all_sessions=lab.SESSIONS
c=lab.database(4)
lab.SESSIONS=all_sessions[:4]
lab.load(c,4,1)
q=dict(lab.QUESTIONS[20],as_of='2026-09-10')
before=lab.recall(c,4,q)
assert '6829' in before
live_before=c.execute("SELECT count(*) FROM memories WHERE key='locker' AND NOT deleted").fetchone()[0]
lab.SESSIONS=all_sessions[4:]
lab.load(c,4,1)
lab.SESSIONS=all_sessions
current=lab.recall(c,4,dict(q,as_of=None))
past=lab.recall(c,4,q)
assert all(x not in current and x not in past for x in ['6829','violet','brass compass'])
assert c.execute("SELECT count(*) FROM memories WHERE key='locker' AND NOT deleted").fetchone()[0]==0
assert c.execute("SELECT body,embedding FROM memories WHERE key='locker'").fetchone()==('[forgotten]',None)
assert c.execute("SELECT body FROM sessions WHERE id='s04'").fetchone()[0]=='[forgotten]'
print(f'Locker: {live_before} eligible row before; 0 after; current/as-of excluded; source redacted.',flush=True)
Path('/var/tmp/memlab-20-source/checks.json').write_text(json.dumps(dict(before=before,current=current,asof=past),indent=2))
c.close()
