"""Read-only snapshot of the book's current BFCL statements for the editor."""
import datetime
import hashlib
import re
from html.parser import HTMLParser
from full_common import ROOT,atomic

class Plain(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)

def collect():
 repo=ROOT.parent.parent;rows=[];hashes={}
 for p in sorted((repo/'build/chapters').glob('*.html')):
  for n,line in enumerate(p.read_text().splitlines(),1):
   if not re.search(r'BFCL|Berkeley.function.call',line,re.I):continue
   parser=Plain();parser.feed(line);text=''.join(parser.parts).strip()
   kind='model_card' if '25.3' in text else 'prior_local' if 'paired questions' in text else 'qualitative'
   rows.append({'file':str(p.relative_to(repo)),'line':n,'statement':text,'kind':kind})
   hashes[str(p.relative_to(repo))]=hashlib.sha256(p.read_bytes()).hexdigest()
 snapshot={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files_sha256':hashes,'statements':rows,'note':'Book files are read only. Current statements may include prior incomplete results; this report supplies a separate uniformly paired continuation.'}
 atomic(ROOT/'evidence/wave2-book-citations.json',snapshot)
 return snapshot

if __name__=='__main__':collect()
