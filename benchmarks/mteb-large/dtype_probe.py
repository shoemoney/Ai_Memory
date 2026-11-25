#!/usr/bin/env python3
"""Small synthetic Q4 matrix probe; no model, labels or quality scores used."""
import json,time,statistics
import mlx.core as mx
from memory_guard import admit

def main():
    free=admit();mx.set_memory_limit(1024**3);mx.set_cache_limit(32*1024**2)
    mx.random.seed(20261122)
    source=mx.random.normal((4096,4096))/64
    inputs=mx.random.normal((4096,4096))
    times={name:[] for name in ['bfloat16','float16']}
    for repeat in range(7):
        names=['bfloat16','float16'] if repeat%2==0 else ['float16','bfloat16']
        for name in names:
            dtype=getattr(mx,name);x=inputs.astype(dtype)
            w,s,b=mx.quantize(source.astype(dtype),group_size=64,bits=4)
            mx.eval(x,w,s,b)
            start=time.perf_counter();y=mx.quantized_matmul(x,w,s,b,group_size=64,bits=4);mx.eval(y);mx.synchronize()
            if repeat>1:times[name].append(time.perf_counter()-start)
            del x,w,s,b,y;mx.clear_cache()
    print(json.dumps({'hardware':'Apple M3 Ultra, 96 GB','shape_M_N_K':[4096,4096,4096],
        'quantization':'MLX affine Q4, group 64','shared_machine':True,'model_or_quality_data_used':False,
        'paired_alternating_order':True,'seconds':times,'median_seconds':{k:statistics.median(v) for k,v in times.items()}},indent=2),flush=True)
if __name__=='__main__':main()
