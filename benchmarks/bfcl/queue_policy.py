"""Coverage-first ordering using only checkpoint presence, never correctness."""

def question_ids(keys,mode,cat,selected):
 return {eid for m,c,eid in keys if m==mode and c==cat and eid in selected}

def mode_order(cat,completed,inflight,selected):
 keys=set(completed)|set(inflight)
 def key(mode):
  questions=len(question_ids(keys,mode,cat,selected))
  prereqs=sum(m==mode and c==cat and '_prereq_' in eid for m,c,eid in keys)
  return questions,prereqs
 return sorted(['off','on'],key=key)

def category_order(schedule,completed,inflight,selected,cursor):
 cats=list(dict.fromkeys(schedule));offset=cursor%len(cats);cats=cats[offset:]+cats[:offset]
 keys=set(completed)|set(inflight)
 def key(cat):
  effective=len(question_ids(keys,'off',cat,selected[cat])&question_ids(keys,'on',cat,selected[cat]))
  actual=len(question_ids(completed,'off',cat,selected[cat])&question_ids(completed,'on',cat,selected[cat]))
  return cat=='live_relevance',float('inf') if effective>=len(selected[cat]) else effective,actual
 return sorted(cats,key=key)
