import json
from pathlib import Path
p=Path('/var/tmp/memlab-20')
s=[]
def add(day,text,facts=(),forget=None):
 s.append(dict(id=f's{len(s)+1:02}',date='2026-'+day,text=text,
               facts=[dict(key=k,text=t) for k,t in facts],forget=forget,
               forget_source="s04" if forget else None))
add('09-01','I am Ivo, an invented person. I prefer a window seat, quiet hotels, '
    'oatmeal for breakfast, and email reminders.',[
 ('seat','I prefer a window seat.'),('hotel','I prefer quiet hotels.'),
 ('breakfast','I prefer oatmeal for breakfast.'),('reminder','I prefer email reminders.')])
add('09-03','I live in Alder Quay. I work at Paper Lantern Studio. '
    'My usual drink is coffee. My remote work day is Monday.',[
 ('city','I live in Alder Quay.'),('job','I work at Paper Lantern Studio.'),
 ('drink','My usual drink is coffee.'),('remote','My remote work day is Monday.')])
add('09-07','I booked a pottery class today, September 7. The class is on October 19. '
    'I bought a green bicycle today.',[
 ('class','I booked a pottery class on September 7; the class is on October 19.'),
 ('bicycle','I bought a green bicycle on September 7.')])
add('09-10','My temporary locker is 47, its code is 6829, its color is violet, '
    'and it holds a brass compass.', [('locker','My temporary locker is 47; its code '
    'is 6829; its color is violet; it holds a brass compass.')])
add('09-14','The pottery class requires an apron. The bicycle needs a rear light.',[
 ('class-kit','The pottery class requires an apron.'),
 ('bicycle-kit','The bicycle needs a rear light.')])
add('09-18','I enrolled in a first-aid course today, September 18. '
    'I reserved the Otter Room today for my talk on October 22.',[
 ('course','I enrolled in a first-aid course on September 18.'),
 ('talk','I reserved the Otter Room on September 18 for my talk on October 22.')])
add('09-22','I moved today, September 22, to Mallow Bay. I started at Copper Kite '
    'Workshop today. I now drink mint tea instead of coffee. '
    'My remote work day is now Thursday instead of Monday.',[
 ('city','I moved to Mallow Bay on September 22; I live there now.'),
 ('job','I started at Copper Kite Workshop on September 22; I work there now.'),
 ('drink','My usual drink is now mint tea.'),
 ('remote','My remote work day is now Thursday.')])
add('09-26','The first-aid course requires a notebook. My talk needs a projector.',[
 ('course-kit','The first-aid course requires a notebook.'),
 ('talk-kit','My talk needs a projector.')])
add('10-01','Forget everything about my temporary locker, including its number, '
    'code, color, and contents. Do not reveal those details again.',forget='locker')
for day in ['10-05','10-09','10-13']:
 add(day,'Today I sorted paper scraps and watched the rain. '+
     'The paper had rough edges. I counted puddles and reorganized an empty shelf. '*12)
(p/'sessions.json').write_text(json.dumps(s,indent=2))
qs=[]
def q(cat,ask,gold,req=(),bad=(),asof=None):
 qs.append(dict(id=f'q{len(qs)+1:02}',category=cat,question=ask,gold=gold,
 required=list(req),forbidden=list(bad),abstain=cat in ['unknown','forgotten'],as_of=asof))
for (ask, word) in [
    ('Which seat do I prefer?', 'window'),
    ('What kind of hotels do I prefer?', 'quiet'),
    ('What do I prefer for breakfast?', 'oatmeal'),
    ('How do I prefer to receive reminders?', 'email'),
]:
    q('stable', ask, word, [word])
for (ask, new, old) in [
    ('Where do I live now?', 'mallow bay', 'alder quay'),
    ('Where do I work now?', 'copper kite workshop', 'paper lantern'),
    ('What is my usual drink now?', 'mint tea', 'coffee'),
    ('Which day do I work remotely now?', 'thursday', 'monday'),
]:
    q('updated', ask, new, [new], [old])
q('temporal','When did I move to Mallow Bay?','September 22',['september','22'])
q(
    'temporal',
    'Where did I live before moving, as of September 21?',
    'Alder Quay',
    ['alder quay'],
    ['mallow bay'],
    '2026-09-21',
)
q('temporal','When did I book the pottery class?','September 7',['september','7'])
q('temporal','When did I enroll in the first-aid course?','September 18',['september','18'])
q('multi','What should I bring to the class on October 19?','An apron',['apron'])
q('multi','What does the item I bought on September 7 need?','A rear light',['rear light'])
q(
    'multi',
    'What should I bring to the course I enrolled in on September 18?',
    'A notebook',
    ['notebook'],
)
q(
    'multi',
    'What equipment is needed in the Otter Room for my October 22 talk?',
    'A projector',
    ['projector'],
)
for ask in [
    'What is my blood type?',
    'What is my passport number?',
    'What is my favorite song?',
    'What is my shoe size?',
]:
    q('unknown', ask, 'I do not know')
for ask in [
    'What was my temporary locker number?',
    'What was my temporary locker code?',
    'What color was my temporary locker?',
    'What did my temporary locker contain?',
]:
    q('forgotten', ask, 'I do not know', bad=['47', '6829', 'violet', 'brass compass'])
(p/'questions.json').write_text(json.dumps(qs,indent=2))
