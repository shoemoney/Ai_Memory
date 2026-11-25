"""Download pinned public weights into the disposable model-service directory."""
import argparse,json,pathlib,shutil
from huggingface_hub import HfApi,snapshot_download
MODELS={
 'model':('mlx-community/Qwen2.5-3B-Instruct-4bit','4f83f8f146fdf28b512a06562b671d7af4fab457'),
 'gtr':('sentence-transformers/gtr-t5-base','9801579ce813fb37541e6098dffd17959fffcd6e'),
 'hypothesizer':('jxm/gtr__nq__32','50ec60382fe46fde9eb4fba60b1b4c6ff2c0c9e7'),
 'corrector':('jxm/gtr__nq__32__correct','f3592b1f0dc6b84a3f1524f80259ebda958b6487'),
 't5':('google-t5/t5-base','a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1'),
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();root=pathlib.Path(a.root);root.mkdir(parents=True,exist_ok=True);manifest={}
 for name,(repo,revision) in MODELS.items():
  if shutil.disk_usage(root).free<20*1024**3:raise RuntimeError('less than 20 GiB free before model download')
  patterns=None if name=='model' else (['config.json','tokenizer.json','tokenizer_config.json','spiece.model','special_tokens_map.json'] if name=='t5' else ['config.json','pytorch_model*','model.safetensors','generation_config.json','tokenizer.json','tokenizer_config.json','spiece.model','special_tokens_map.json','modules.json'])
  snapshot_download(repo,revision=revision,local_dir=root/name,allow_patterns=patterns)
  info=HfApi().model_info(repo,revision=revision);manifest[repo]={'revision':revision,'license':(info.card_data or {}).get('license','not specified in model card')}
 (root/'model-revisions.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
