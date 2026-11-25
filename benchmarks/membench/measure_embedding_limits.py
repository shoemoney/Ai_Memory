"""Count encoder truncation exposure without running a hosted model."""
import collections
from common import *
def main():
 env();data=read(LAB/'prepared.json')
 from transformers import AutoTokenizer
 tokenizer=AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,cache_dir=os.environ['HF_HOME'])
 # SentenceTransformer's pinned sentence_bert_config sets max_seq_length=256,
 # regardless of the tokenizer's larger standalone model_max_length.
 limit=256;report={'encoder_limit_including_special_tokens':limit,'queries':{},'chunks':{}}
 for bench in ['mab','halu']:
  qs=[x['question'] for x in data['items'] if x['benchmark']==bench]
  lengths=[len(x) for x in tokenizer(qs,truncation=False)['input_ids']]
  report['queries'][bench]={'n':len(lengths),'over_limit':sum(v>limit for v in lengths),'maximum_wordpieces':max(lengths)}
 for bench in ['mab','halu']:
  lengths=[]
  for cid in data['contexts']:
   if not cid.startswith(bench+'-'):continue
   chunks=read(LAB/'indexes'/f'{cid}.json')
   lengths.extend(len(x) for x in tokenizer(chunks,truncation=False)['input_ids'])
  report['chunks'][bench]={'n':len(lengths),'over_limit':sum(v>limit for v in lengths),'maximum_wordpieces':max(lengths)}
 report['interpretation']='The encoder truncates over-limit inputs; the shared reader receives the full question and complete selected chunks. This is an encoder representation limit, not reader context truncation.'
 atomic(OUT/'embedding-limits.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
