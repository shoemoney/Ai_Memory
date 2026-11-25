"""Public deterministic synthetic fixture recipe and tokenizer-only scoring."""
import collections,hashlib,pathlib,random,re,urllib.request
SEED=20261122
TOKENIZER_URL='https://huggingface.co/google-t5/t5-base/resolve/a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1/tokenizer.json'
def fixture(scratch,n=150):
 from tokenizers import Tokenizer
 path=pathlib.Path(scratch)/'t5-tokenizer.json'
 if not path.exists():path.write_bytes(urllib.request.urlopen(TOKENIZER_URL,timeout=120).read())
 tokenizer=Tokenizer.from_file(str(path));tokenizer.enable_truncation(max_length=32)
 adjectives=['small','quiet','green','narrow','rocky','sandy','open','shaded','bright','windy']
 places=['garden','forest','valley','riverbank','coast','meadow','village','orchard','desert','mountain']
 objects=['path','bridge','pond','stream','field','road','shelter','fence','hill','trail']
 combos=[(x,y,z) for x in adjectives for y in places for z in objects];random.Random(SEED).shuffle(combos)
 rows=[]
 for i,(x,y,z) in enumerate(combos[:n]):
  text=f'The {x} {y} contains a {z} beside several trees and an open area. During the spring the weather is usually mild, and steady rainfall keeps the ground moist for many weeks.'
  encoded=tokenizer.encode(text);assert len(encoded.ids)==32
  text=tokenizer.decode(encoded.ids,skip_special_tokens=True)
  rows.append({'trial':i,'source':text,'source_token_count':32,'attributes':[x,y,z],'source_sha256':hashlib.sha256(text.encode()).hexdigest()})
 assert len({r['source'] for r in rows})==n
 return rows

def attributes_recovered(answer,attributes):return sum(bool(re.search(r'\b'+re.escape(w)+r'\b',answer.lower())) for w in attributes)
