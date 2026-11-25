"""Matched scores on questions with complete answers and three votes in every system."""
from full_common import OUT, read, atomic, item_path
from run import wilson
import statistics
SYSTEMS = ['full-context','rag','mem0','graphiti','cognee']

def summarize_matched():
    selected = read(OUT/'selection.json')
    rows = {b:{q['item_id']:read(item_path(b,q)) for q in selected if item_path(b,q).exists()} for b in SYSTEMS}
    conversations = [ci for ci in range(10) if all(rows[b].get(q['item_id'],{}).get('complete') for b in SYSTEMS for q in selected if q['conversation']==ci)]
    questions = [q for q in selected if all(rows[b].get(q['item_id'],{}).get('complete') for b in SYSTEMS)]
    whole_questions = [q for q in selected if q['conversation'] in conversations]
    def score(items):
        n=len(items);k=sum(x['correct'] for x in items)
        return dict(correct=k,n=n,accuracy=k/n if n else None,wilson_95=wilson(k,n) if n else None)
    result = dict(rule='Intersection of preselected questions with a saved answer and all three judge votes in every system at the fixed stopping time. No outcome-based selection. Ingestion uses each complete conversation before answering.',conversation_order=list(range(10)),completed_conversations=conversations,represented_conversations=sorted({q['conversation'] for q in questions}),coverage={str(ci):dict(selected=sum(q['conversation']==ci for q in selected),matched=sum(q['conversation']==ci for q in questions)) for ci in range(10)},n=len(questions),item_ids=[q['item_id'] for q in questions],whole_conversation_n=len(whole_questions),whole_conversation_systems={},macro_sd_definition='Sample SD across represented conversations; undefined with fewer than two conversations.',systems={})
    for b in SYSTEMS:
        items=[rows[b][q['item_id']] for q in questions]
        result['systems'][b]=score(items)
        result['whole_conversation_systems'][b]=score([rows[b][q['item_id']] for q in whole_questions])
        result['systems'][b]['by_conversation']={str(ci):score([x for x in items if x['conversation']==ci]) for ci in result['represented_conversations']}
        rates=[v['accuracy'] for v in result['systems'][b]['by_conversation'].values()]
        result['systems'][b]['macro_conversation_accuracy']=statistics.mean(rates) if rates else None
        result['systems'][b]['macro_conversation_sd']=statistics.stdev(rates) if len(rates)>1 else None
        result['systems'][b]['by_category']= {str(c):score([x for x in items if x['category']==c]) for c in range(1,5)}
    atomic(OUT/'matched-summary.json',result)
    return result

if __name__ == '__main__':
    result=summarize_matched()
    print({k:result[k] for k in ['completed_conversations','n']})
