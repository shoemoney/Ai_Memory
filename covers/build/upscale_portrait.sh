#!/usr/bin/env bash
set -euo pipefail
cover_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$cover_dir/../.." && pwd)
cover_scratch=/var/tmp/membench-covers
mkdir -p "$cover_scratch"
# No containers or hosted image processing. The model is local, without face enhancement.
nvidia-smi --query-gpu=name,utilization.gpu,memory.free --format=csv
trap 'rm -rf -- "$cover_scratch/upscaler" "$cover_scratch/upscaler.zip" "$cover_scratch/upscaled.png"' EXIT
curl --fail -L https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip -o "$cover_scratch/upscaler.zip"
unzip -q "$cover_scratch/upscaler.zip" -d "$cover_scratch/upscaler"
chmod +x "$cover_scratch/upscaler/realesrgan-ncnn-vulkan"
# Select the NVIDIA GPU index from the device list (1 on the machine used for the build).
"$cover_scratch/upscaler/realesrgan-ncnn-vulkan" -i "$repo_dir/build/cover-art/cover-b-20261120-095134.png" -o "$cover_scratch/upscaled.png" -s 4 -n realesrgan-x4plus -m "$cover_scratch/upscaler/models" -g "${COVER_GPU_INDEX:-1}" -t 128
python3 - "$cover_scratch/upscaled.png" "$cover_dir/assets/portrait-4x.jpg" <<'PY'
from PIL import Image
import sys
Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2],quality=97,subsampling=0)
PY
