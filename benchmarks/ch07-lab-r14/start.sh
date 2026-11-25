set -euo pipefail
umask 077
export LAB=/var/tmp/memlab-07
if [ -e "$LAB" ] || [ -L "$LAB" ]; then
  echo "STOP: $LAB already exists" >&2
  exit 1
fi
for name in memlab-07-ollama memlab-07-cleanup; do
  if docker container inspect "$name" >/dev/null 2>&1; then
    echo "STOP: $name already exists" >&2
    exit 1
  fi
done
mkdir -- "$LAB"
export LAB_TOKEN=$(cat /proc/sys/kernel/random/uuid)
export LAB_REAL=$(realpath -e -- "$LAB")
printf '%s\n' "$LAB_TOKEN" > "$LAB/.owner"
printf '%s\n' "$LAB_REAL" > "$LAB/.path"
cd "$LAB"
export PIP_CACHE_DIR=/var/tmp/memlab-07/pip-cache
python3 -m venv venv
venv/bin/pip install jsonschema==4.25.1 attrs==26.1.0 \
  jsonschema-specifications==2025.9.1 referencing==0.37.0 rpds-py==2026.9.1
docker pull ollama/ollama:0.40.16
