#!/usr/bin/env python3
import os,logging,json
from pathlib import Path
lab=Path.home()/"inkling-lab"
os.environ.setdefault("HF_HOME",str(lab/'hf-cache'))
os.environ.setdefault("XDG_CACHE_HOME",str(lab/'cache'))
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
from omlx.oq import quantize_oq_streaming,estimate_bpw_and_size
src=lab/'models/Inkling-2-Mini'; dst=lab/'models/Inkling-2-Mini-oQ4e-stock'
print(json.dumps(estimate_bpw_and_size(str(src),4,preserve_mtp=True),indent=2),flush=True)
quantize_oq_streaming(str(src),str(dst),4,group_size=64,dtype='bfloat16',preserve_mtp=True,enhanced=True,imatrix_cache_path=str(src/'.oqe_imatrix'),progress_callback=lambda phase,pct:print(f"{phase}: {pct:.2f}",flush=True))
print('BUILD_COMPLETE',flush=True)
