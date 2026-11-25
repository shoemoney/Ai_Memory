"""Draw the final 40-item blinded audit from the completed matched subset."""
import random,shutil
from full_common import *
from matched_summary import summarize_matched

def main():
    matched=summarize_matched();assert matched['n'], 'No matched conversations completed'
    selected=[q for q in read(OUT/'selection.json') if q['item_id'] in set(matched['item_ids'])]
    rng=random.Random(20261123);items=[]
    for backend in ['full-context','rag','mem0','graphiti','cognee']:
        for category in range(1,5):
            candidates=sorted((q for q in selected if q['category']==category),key=lambda q:q['item_id'])
            for q in rng.sample(candidates,2):items.append(dict(backend=backend,item_id=q['item_id'],category=category))
    old_plan=read(OUT/'manual-audit-plan.json')
    if old_plan.get('scope')=='final_matched_subset':
        assert old_plan['matched_item_ids']==matched['item_ids'], 'Audit already drawn for a different subset'
        if not (OUT/'manual-audit-blind-presentation.json').exists():
            presentation=list(old_plan['items']);random.Random(20261124).shuffle(presentation)
            atomic(OUT/'manual-audit-blind-presentation.json',dict(seed=20261124,rule='Shuffled presentation with system identities and votes hidden.',items=[dict(audit_id=f'audit_{i+1:03d}',**item) for i,item in enumerate(presentation)]))
        return
    shutil.copyfile(OUT/'manual-audit-plan.json',OUT/'manual-audit-wide-plan.json')
    old=read(OUT/'manual-audit.json');shutil.copyfile(OUT/'manual-audit.json',OUT/'manual-audit-wide.json')
    desired={(x['backend'],x['item_id']) for x in items}
    reviewed=[]  # Fresh final reading with both system identity and votes hidden.
    assert not any('majority_label' in x for x in reviewed)
    atomic(OUT/'manual-audit-plan.json',dict(scope='final_matched_subset',seed=20261123,rule='Two items per system/category, uniformly without replacement within the final matched subset. Selected without reading votes; manual review remains blinded.',matched_item_ids=matched['item_ids'],matched_conversations=matched['represented_conversations'],items=items))
    atomic(OUT/'manual-audit.json',dict(reviewer=old['reviewer'],blinded_to_majority_during_review=True,items=reviewed))
    presentation=list(items);random.Random(20261124).shuffle(presentation)
    atomic(OUT/'manual-audit-blind-presentation.json',dict(seed=20261124,rule='Shuffle the fixed 40-item plan; show opaque IDs, questions, references, answers and source evidence, hiding system identities and votes.',items=[dict(audit_id=f'audit_{i+1:03d}',**item) for i,item in enumerate(presentation)]))
    print(dict(planned=40,already_reviewed=len(reviewed),matched_n=matched['n'],presentation='System identities and votes hidden'))
if __name__=='__main__':main()
