# Rank 128 capability result

2026-11-25T10:46Z: the requested all-layers rank-128 cell failed before initial evaluation or training. Server response: `HTTP 400: lora_config.rank 128 exceeds max LoRA rank 64 for model thinkingmachines/Inkling-2-Mini`. Full evidence: `runs/lora-all-r128-s0/service.log`.

The frozen PREREG-lora.md is unchanged. Mark rank 128 unavailable, leave the remaining four cells unchanged, and do not substitute rank 64 or retry a permanent capability rejection. No training/sampling was submitted by this failed cell; provider-reported billing is not yet available. One seed per supported cell remains the registered plan.
