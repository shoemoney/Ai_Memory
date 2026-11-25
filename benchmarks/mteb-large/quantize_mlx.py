"""Streaming use of MLX's own affine quantizer, without calibration or full-model copies."""
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten

def at_path(model,path):
    node=model
    for part in path.split('.'):
        node=node[int(part)] if isinstance(node,list) else node[part]
    return node

def stream_quantize(model,bits=4,group_size=64,skip_vision=False):
    paths=[]
    for path,module in model.named_modules():
        if not path or not hasattr(module,'to_quantized') or not hasattr(module,'weight'):continue
        if skip_vision and any(x in path for x in ['visual','vision_model','vision_tower']):continue
        if module.weight.ndim==2 and module.weight.shape[-1]%group_size==0:paths.append(path)
    del module
    stats={'method':'MLX affine, CPU stream, no calibration','bits':bits,'group_size':group_size,
           'modules':0,'original_matrix_bytes':0,'quantized_matrix_parameter_bytes':0,'skip_vision':skip_vision}
    with mx.stream(mx.cpu):
        for path in paths:
            old=at_path(model,path);stats['original_matrix_bytes']+=old.weight.nbytes
            nn.quantize(model,group_size=group_size,bits=bits,mode='affine',
                        class_predicate=lambda p,m,chosen=path:p==chosen)
            new=at_path(model,path)
            mx.eval(new.parameters())
            stats['quantized_matrix_parameter_bytes']+=sum(v.nbytes for _,v in tree_flatten(new.parameters()))
            stats['modules']+=1
            del old,new
    return stats

def sanity_check():
    mx.random.seed(20261122)
    checks=[]
    for bits,limit in [(8,.02),(4,.2)]:
        with mx.stream(mx.cpu):
            model=nn.Sequential(nn.Linear(128,64))
            x=mx.random.normal((8,128));reference=model(x);mx.eval(reference)
            stats=stream_quantize(model,bits)
            output=model(x);mx.eval(output)
            relative=float(mx.sqrt(mx.mean((output-reference)**2))/mx.sqrt(mx.mean(reference**2)))
            assert relative<limit,(bits,relative)
            assert stats['quantized_matrix_parameter_bytes']<stats['original_matrix_bytes']
            checks.append({'bits':bits,'relative_output_rmse':relative,'limit':limit,'status':'pass'})
    return checks
if __name__=='__main__':
    import json
    print(json.dumps(sanity_check(),indent=2))
