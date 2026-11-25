# Actual oQ4e tensor breakdown

Measured from safetensors headers and the output per-module quantization map; no estimated parameter counts.

| Storage | Logical weights | Tensor bytes | GiB |
|---|---:|---:|---:|
| F32 | 35,637,248 | 142,548,992 | 0.132759 |
| nvfp4 4-bit g16 | 20,384,317,440 | 11,466,178,560 | 10.678711 |
| affine 8-bit g64 | 1,572,323,328 | 1,670,593,536 | 1.555861 |
| BF16 | 319,504,896 | 639,009,792 | 0.595124 |
| MTP BF16 | 317,897,872 | 635,795,744 | 0.592131 |
| affine 4-bit g64 | 4,076,863,488 | 2,293,235,712 | 2.135742 |

Main model+vision: 26,388,646,400 weights, 16,211,566,592 tensor bytes, **4.914710 bpw**.
Including draft: 26,706,544,272 weights, 16,847,362,336 tensor bytes, **5.046662 bpw**.

Published README rounds these to 4.915 and 5.047 bpw. All storage category counts and sizes agree at its published precision. The 20 early layers retain NVFP4; the final four expert layers are affine 4-bit; embeddings/head/attention are 8-bit. Vision and the separate draft remain BF16; router/loop state remains FP32.

The output retains `mtp.safetensors` and `mtp_config`. The build emitted a generic warning that no `mtp.*` tensors were in the main index; Inkling stores its draft separately, and the Inkling-specific sidecar-copy step preserved it. This warning did not mean the draft was lost.

Imatrix: 128 samples × 512 tokens; 65 entries; all 1,024 tracked experts active; p05 activation count 988.2; no mismatched entries; output-error refit skipped for inkling2_loop, as documented.

Build: 204.41 seconds; maximum RSS 20,299,677,696 bytes (18.91 GiB); macOS peak memory footprint 67,403,868,576 bytes (62.77 GiB). These are distinct OS metrics.
