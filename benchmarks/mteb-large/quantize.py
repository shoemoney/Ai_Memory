"""Auditable groupwise symmetric round-to-nearest weight-only quantization.

Linear matrices of at least one million weights are quantized. Embeddings,
normalization, biases and smaller matrices retain the original precision.
Dequantization and matrix products use the original compute dtype. No calibration.
"""
import math
import torch
from torch import nn
from torch.nn import functional as F

class QuantLinear(nn.Module):
    def __init__(self, weight, bias, bits, group_size=64, device='mps'):
        super().__init__()
        assert bits in (4,8)
        self.out_features,self.in_features=weight.shape
        self.bits=bits;self.group_size=group_size;self.compute_dtype=weight.dtype
        self.padded=math.ceil(self.in_features/group_size)*group_size
        with torch.no_grad():
            w=F.pad(weight.detach().float().cpu(),(0,self.padded-self.in_features)).reshape(self.out_features,-1,group_size)
            bound=2**(bits-1)-1
            scales=w.abs().amax(-1,keepdim=True).clamp_min(1e-12)/bound
            q=torch.round(w/scales).clamp(-bound,bound).to(torch.int8).reshape(self.out_features,self.padded)
            if bits==4:
                q=(q.to(torch.int16)+8).to(torch.uint8)
                q=q[:,::2] | (q[:,1::2]<<4)
            self.register_buffer('qweight',q.to(device))
            self.register_buffer('scales',scales.to(device=device,dtype=self.compute_dtype))
            self.bias=nn.Parameter(bias.detach().to(device),requires_grad=False) if bias is not None else None
        self.eval()
    def dequantize(self):
        q=self.qweight
        if self.bits==4:
            low=(q&15).to(self.compute_dtype)-8
            high=(q>>4).to(self.compute_dtype)-8
            q=torch.stack((low,high),dim=-1).reshape(self.out_features,self.padded)
        else:q=q.to(self.compute_dtype)
        w=(q.reshape(self.out_features,-1,self.group_size)*self.scales).reshape(self.out_features,self.padded)
        return w[:,:self.in_features]
    @property
    def weight(self):return self.dequantize()
    def forward(self,x):return F.linear(x,self.dequantize(),self.bias)


def convert_linears(model,bits,group_size=64,device='mps'):
    """Move each converted matrix immediately, avoiding a second model-sized copy."""
    stats={'bits':bits,'group_size':group_size,'method':'symmetric RTN, no calibration',
           'quantized_matrices':0,'quantized_weights':0,'merged_adapter_matrices':0,
           'excluded':'Embeddings, normalization, biases and matrices below 1000000 weights',
           'scale_dtype':'bfloat16','compute_dtype':'bfloat16'}
    def visit(parent):
        for name,child in list(parent.named_children()):
            # Merge an active LoRA delta for this matrix only, before RTN.
            is_adapter=hasattr(child,'get_base_layer') and hasattr(child,'get_delta_weight')
            if is_adapter and any(getattr(child,'use_dora',{}).values()):
                raise ValueError('DoRA adapters require a separate merge implementation')
            base=child.get_base_layer() if is_adapter else child
            if isinstance(base,nn.Linear) and base.weight.numel()>=1_000_000:
                weight=base.weight.detach()
                if is_adapter and not child.merged:
                    for adapter in child.active_adapters:
                        if adapter in child.lora_A:
                            weight=(weight+child.get_delta_weight(adapter).to(weight.dtype)).to(base.weight.dtype)
                    stats['merged_adapter_matrices']+=1
                replacement=QuantLinear(weight,base.bias,bits,group_size,device)
                setattr(parent,name,replacement)
                stats['quantized_matrices']+=1;stats['quantized_weights']+=base.weight.numel()
                del replacement,weight,base,child
            else:visit(child)
    visit(model)
    model.to(device);model.eval()
    return stats


def sanity_check(device='cpu'):
    torch.manual_seed(20261121)
    layer=nn.Linear(96,113,bias=True,dtype=torch.bfloat16)
    x=torch.randn(3,8,96,dtype=torch.bfloat16)
    reference=layer(x).float()
    result=[]
    for bits,limit in [(8,.02),(4,.20)]:
        q=QuantLinear(layer.weight,layer.bias,bits,64,device)
        output=q(x.to(device)).float().cpu().detach();reference=reference.detach();relative=float((output-reference).square().mean().sqrt()/reference.square().mean().sqrt())
        assert relative<limit,(bits,relative)
        assert q.dequantize().shape==layer.weight.shape
        assert q.qweight.numel()==113*(128 if bits==8 else 64)
        result.append({'bits':bits,'relative_output_rmse':relative,'limit':limit,'padding_test':True})
    return result
if __name__=='__main__':
    import json
    print(json.dumps(sanity_check(),indent=2))
