# Serving Inkling 2 Mini on a Mac Studio

How the stock model was built and served for the measurements in this folder. Everything ran on one Mac Studio (M3 Ultra, 96 GB) in an isolated directory, with the server bound to the loopback interface and reached through an SSH tunnel from the workstation.

## Software

- oMLX 0.8.3 (tag `v0.8.3`, commit `e72868dac12df4be4ced2dc8355f031686283974`) in its own virtual environment; installed versions in `omlx-freeze.txt`.
- mlx-lm from the Inkling pull request ml-explore/mlx-lm#2086 (commit `e2b5bbd3bd9d186dea895e60802aa765e70b9d93`), transformers 5.23.0, in a second environment; installed versions in `mlxlm-freeze.txt`.
- Python 3.13, MLX 0.32.4.
- The pull request text implementation does not need mlx-vlm. Its comments describe a transformers 5.24 validation failure for a community 4-bit conversion whose `vision_config` lacked `model_type: inkling2_vision` and `text_hidden_size: 2304`; the original source has both, so keep them.

The scripts name the Mac Studio as `<mac-studio>` (an SSH host alias) and its address as `<lan-address>`; replace both with your own host before running anything.

## Source and the oQ4e build

`download-source.py` snapshots the model repository at its manifest commit and checks every file: size and LFS SHA-256, or Git blob SHA-1 for non-LFS files. `hf-source-manifest.json` is the public metadata. The source payload is 20,191,645,654 bytes, revision `c9d028302cd0f035fdf8e7e91f089a4ce94d2195`; all 15 files verified.

`build-stock.py` calls oMLX's `omlx.oq.quantize_oq_streaming` with `oq_level=4`, `enhanced=True`, `group_size=64`, `dtype=bfloat16`, `preserve_mtp=True` and the default 128 calibration samples at sequence length 512. The importance-matrix cache stays beside the source. No community checkpoint and no calibration override is used. The oMLX documentation says Inkling skips the output-error refit and keeps plain oQe values; the conversion report (`oq_imatrix_report.json`) records the actual behaviour.

The published community build is expected to retain layers 0-19 expert weights as NVFP4 (group 16), layers 20-23 experts as affine 4-bit (group 64), attention, embeddings and head as affine 8-bit, vision and draft in BF16, and routers and loop controllers in FP32: 4.915 bits per weight excluding the draft, 5.047 including it. `tensor-breakdown.py` compares our build with that layout (`tensor-comparison.md`, `tensor-breakdown.json`).

## Serving

`serve.sh <model-dir> [restart|stop]` starts the server with `--no-hf-cache --no-cache --max-concurrent-requests 1 --memory-guard-gb 60 --headless`, an isolated base path and home directory, and a directory that exposes exactly one model. It listens on loopback port 39850; no API key is needed on that endpoint. `launch-server.py` wraps the command line to retain memory high-water marks and installs its own SIGTERM handler, because Uvicorn restores and re-raises SIGTERM after graceful shutdown and a Python `finally` block would otherwise not run. `smoke.py` sends one chat request and records the answer, usage and timing; `sample-memory.py` samples process memory every 30 seconds; `run-stock.sh` and `summarize-stock.py` drive and summarise the stock measurements.

Chat requests use both `"thinking_budget": 0` and `"chat_template_kwargs": {"enable_thinking": false}`; `enable_thinking=false` alone can leave an empty visible answer.

## Known upstream issues at the time

- Sustained multi-turn traffic leaks memory (oMLX #5539). Restart between batches, serialise requests and keep batches short; this setup is not a soak-test fix.
- Thinking-off needs the top-level `thinking_budget: 0` as well (oMLX #5556).
- A threadgroup-size failure in generation and quantisation on M1 Max (oMLX #5570); the Mac Studio is an M3 Ultra, but a real generation and build smoke test is the only proof it is unaffected.

## Results

- oQ4e build finished in 204.41 s. Peak resident set 20,299,677,696 bytes; macOS peak footprint 67,403,868,576 bytes. Main model plus vision 4.914710 bits per weight, with the draft 5.046662.
- Smoke request through the tunnel: model `Inkling-2-Mini-oQ4e-stock` answered "Jane Austen wrote *Pride and Prejudice*." in 26 prompt tokens and 15 completion tokens, 0 reasoning tokens, 25.85 generation tokens/s, 2.398 s for the full request including a cold model load. This sample is not benchmark throughput.
- Smoke server maximum resident set 17,598,185,472 bytes (16.39 GiB); MLX peak allocated memory 17,962,168,132 bytes (16.73 GiB).
- Mounted network filesystems made `df -h` and ordinary `lsof` stall on this machine; bounded probes with a 20-second limit and `lsof -b -w` fixed that.
