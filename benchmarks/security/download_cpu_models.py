"""Fetch pinned CPU study weights; never store them in the companion repository."""
import argparse,json,pathlib,shutil
from huggingface_hub import HfApi,snapshot_download
SPECS={
 'cpu-weights':('Qwen/Qwen2.5-3B-Instruct-GGUF','7dabda4d13d513e3e842b20f0d435c732f172cbe',['qwen2.5-3b-instruct-q4_k_m.gguf']),
 'inversion-models/gtr':('sentence-transformers/gtr-t5-base','9801579ce813fb37541e6098dffd17959fffcd6e',None),
 'inversion-models/hypothesizer':('jxm/gtr__nq__32','50ec60382fe46fde9eb4fba60b1b4c6ff2c0c9e7',None),
 'inversion-models/corrector':('jxm/gtr__nq__32__correct','f3592b1f0dc6b84a3f1524f80259ebda958b6487',None),
 'inversion-models/t5':('google-t5/t5-base','a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1',['config.json','tokenizer.json','tokenizer_config.json','spiece.model','special_tokens_map.json']),
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--scratch',required=True);a=p.parse_args();root=pathlib.Path(a.scratch);manifest={}
 for directory,(repo,revision,patterns) in SPECS.items():
  if shutil.disk_usage('/').free<20*1024**3 or shutil.disk_usage(root).free<20*1024**3:raise RuntimeError('disk gate refused a large download')
  if patterns is None:patterns=['config.json','pytorch_model*','model.safetensors','generation_config.json','tokenizer.json','tokenizer_config.json','spiece.model','special_tokens_map.json','modules.json']
  snapshot_download(repo,revision=revision,allow_patterns=patterns,local_dir=root/directory)
  info=HfApi().model_info(repo,revision=revision);manifest[repo]={'revision':revision,'license':(info.card_data or {}).get('license','not specified in model card')}
 (root/'model-revisions-cpu.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
