#!/usr/bin/env bash
set -euo pipefail
LAB=/var/tmp/memlab-10/run
if [ -e "$LAB" ] || [ -L "$LAB" ]; then
  echo "STOP: $LAB already exists" >&2
  exit 1
fi
for name in memlab-10-default memlab-10-large; do
  if docker container inspect "$name" >/dev/null 2>&1; then
    echo "STOP: $name already exists" >&2
    exit 1
  fi
done
python3 - <<'PYPORT'
import socket
sockets = []
for port in (39100, 39101):
    sock = socket.socket()
    sock.bind(("127.0.0.1", port))
    sockets.append(sock)
PYPORT
mkdir -p -- "$(dirname "$LAB")"
mkdir -- "$LAB" || { echo "STOP: lab creation failed" >&2; exit 1; }
LAB_TOKEN=$(cat /proc/sys/kernel/random/uuid)
LAB_REAL=$(realpath -e -- "$LAB")
printf '%s\n' "$LAB_TOKEN" > "$LAB/.owner"
printf '%s\n' "$LAB_REAL" > "$LAB/.path"
export PIP_CACHE_DIR="$LAB/pip-cache"
python3 -m venv "$LAB/venv"
"$LAB/venv/bin/pip" install pymemcache==4.0.0
docker run -d --name memlab-10-default --label "memfix.owner=$LAB_TOKEN" \
  --memory 256m --cpus 1 \
  -p 127.0.0.1:39100:11211 memcached:1.6.45
docker run -d --name memlab-10-large --label "memfix.owner=$LAB_TOKEN" \
  --memory 256m --cpus 1 \
  -p 127.0.0.1:39101:11211 memcached:1.6.45 memcached -I 2m
docker exec memlab-10-default memcached --version
"$LAB/venv/bin/python" --version
