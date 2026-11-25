"""Join the preselected blinded manual labels with the saved judge majority."""
from full_common import OUT, read, atomic
from run import wilson

def main():
    plan = read(OUT / 'manual-audit-plan.json')['items']
    audit = read(OUT / 'manual-audit.json')
    expected = {(x['backend'], x['item_id']) for x in plan}
    reviewed = {(x['backend'], x['item_id']) for x in audit['items']}
    assert len(reviewed) == len(audit['items']), 'Duplicate manual review'
    assert reviewed == expected, 'Finish the preselected 40 reviews before revealing agreement'
    groups = {}
    for item in audit['items']:
        assert item['manual_label'] in ('CORRECT', 'WRONG')
        row = read(OUT / 'items' / item['backend'] / (item['item_id'] + '.json'))
        assert row.get('complete') and len(row['votes']) == 3
        item['majority_label'] = 'CORRECT' if row['correct'] else 'WRONG'
        item['agrees'] = item['manual_label'] == item['majority_label']
        groups.setdefault(item['backend'], []).append(item['agrees'])
    k = sum(x['agrees'] for x in audit['items'])
    audit['summary'] = dict(agreed=k, n=40, agreement=k/40, wilson_95=wilson(k,40),
        by_system={b:dict(agreed=sum(v),n=len(v)) for b,v in groups.items()},
        interpretation='Implementation-agent manual audit, not independent human validation; main scores unchanged.')
    atomic(OUT / 'manual-audit.json', audit)
    print(audit['summary'])

if __name__ == '__main__':
    main()
