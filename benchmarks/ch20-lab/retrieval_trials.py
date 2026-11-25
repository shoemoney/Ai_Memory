import json,shutil
from pathlib import Path
import lab
lab.RETRIEVAL.update(mode='all',key_bodies=False,sentences=False)
if (lab.ROOT/'stage-4.json').exists():
 shutil.copyfile(lab.ROOT/'stage-4.json',lab.ROOT/'stage-4-default.json')
c=lab.database(4)
lab.load(c,4,1)
rows=c.execute('SELECT body,since FROM memories WHERE NOT deleted AND until IS NULL ORDER BY id').fetchall()
text='\n'.join(f'{date}: {body}' for body,date in rows)
print('ALL_VALID_ROWS',len(rows),'TOKENS',lab.tokens(text),'BUDGET',lab.RETRIEVAL['budget'],flush=True)
c.close()
for name,settings in [('all',dict(mode='all')),('or',dict(mode='hybrid',keyword='english-websearch-OR'))]:
 lab.RETRIEVAL.update(settings)
 lab.stage(4)
 (lab.ROOT/f'stage-4-{name}.json').write_text((lab.ROOT/'stage-4.json').read_text())
