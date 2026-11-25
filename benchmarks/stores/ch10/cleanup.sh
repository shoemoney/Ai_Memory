#!/usr/bin/env bash
set -euo pipefail
LAB=/var/tmp/memlab-10/run
if [ -L "$LAB" ] || [ ! -f "$LAB/.owner" ] || [ -L "$LAB/.owner" ] ||
   [ ! -f "$LAB/.path" ] || [ -L "$LAB/.path" ]; then
  echo "STOP: lab ownership check failed" >&2
  exit 1
fi
LAB_TOKEN=$(cat "$LAB/.owner")
LAB_REAL=$(cat "$LAB/.path")
if [ -z "$LAB_TOKEN" ] || [ "$LAB_REAL" != "$LAB" ] ||
   [ "$(realpath -e -- "$LAB")" != "$LAB" ]; then
  echo "STOP: lab ownership check failed" >&2
  exit 1
fi
names=$(docker container ls -a --format '{{.Names}}')
present=()
for name in memlab-10-default memlab-10-large; do
  if ! grep -Fxq -- "$name" <<< "$names"; then
    continue
  fi
  owner=$(docker inspect -f '{{ index .Config.Labels "memfix.owner" }}' "$name")
  if [ "$owner" != "$LAB_TOKEN" ]; then
    echo "STOP: container ownership check failed" >&2
    exit 1
  fi
  present+=("$name")
done
if [ "${#present[@]}" -gt 0 ]; then docker rm -f "${present[@]}"; fi
cd /var/tmp
rm -rf -- "$LAB"
test ! -e "$LAB" && test ! -L "$LAB"
echo "Cleanup verified: lab and containers removed"
