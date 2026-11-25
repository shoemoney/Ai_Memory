"""Diagnostic: how often does the local indexer model answer a bare 'yes' to LIGHT's scratchpad chunk filter?
LIGHT keeps a chunk only when the reply, stripped and lower-cased, equals exactly 'yes'. Reports reply counts for 6 questions of one conversation."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.environ.get("BEAM_DIR", "/data/scratch/membench/gap-reruns/g10/BEAM"))
os.environ.setdefault("OPENAI_API_KEY", "local")
import sentence_transformers
from remote_st import RemoteST
sentence_transformers.SentenceTransformer = RemoteST
from langchain_openai import ChatOpenAI
from langchain_experimental.text_splitter import SemanticChunker
import src.answer_probing_questions.long_term_memory_methods as lm
from src.prompts import filter_chunk_context_prompt
lm._get_st_client = lambda name, device=None: RemoteST(name)
from concurrent.futures import ThreadPoolExecutor
conv = sys.argv[1] if len(sys.argv) > 1 else "2"; model = sys.argv[2] if len(sys.argv) > 2 else "gap-qwen2.5-3b"
W = os.environ.get("WORK_DIR", "/data/scratch/membench/gap-reruns/g10/work")
sp = open(f"{W}/{conv}/index/scrach_pad_new.txt").read()
qs = json.load(open(f"{os.environ.get('BEAM_DIR', '/data/scratch/membench/gap-reruns/g10/BEAM')}/chats/100K/{conv}/probing_questions/probing_questions.json"))
questions = [it["question"] for ab in qs for it in qs[ab][:1]][:6]
llm = ChatOpenAI(model=model, base_url="http://127.0.0.1:39980/v1", api_key="local", temperature=0, max_tokens=1200)
docs = SemanticChunker(embeddings=lm.CachedHFEmbeddings("BAAI/bge-large-en-v1.5"), buffer_size=1, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=80.0).create_documents([sp])
out = {"conversation": conv, "model": model, "chunks": len(docs), "questions": []}
for q in questions:
    def f(d): return llm.invoke(filter_chunk_context_prompt.replace("<query>", q).replace("<doc_text>", d.page_content)).content.strip().lower()
    with ThreadPoolExecutor(8) as ex: rep = list(ex.map(f, docs))
    c = collections.Counter(rep)
    out["questions"].append({"question": q[:80], "kept_exact_yes": c.get("yes", 0), "other_yes_like": sum(v for k, v in c.items() if k.startswith("yes") and k != "yes"), "top_replies": c.most_common(4)})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", f"diag-filter-{model}.json"), "w"), indent=1)
print(json.dumps(out, indent=1)[:1500])
