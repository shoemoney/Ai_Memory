set -euo pipefail
if [ "${LAB:-}" != /var/tmp/memlab-07 ] || [ -L "$LAB" ] ||
   [ ! -f "$LAB/.owner" ] || [ -L "$LAB/.owner" ] ||
   [ ! -f "$LAB/.path" ] || [ -L "$LAB/.path" ] ||
   [ -z "${LAB_TOKEN:-}" ] || [ -z "${LAB_REAL:-}" ] ||
   [ "$(cat "$LAB/.owner")" != "$LAB_TOKEN" ] ||
   [ "$(cat "$LAB/.path")" != "$LAB_REAL" ] ||
   [ "$(realpath -e -- "$LAB")" != /var/tmp/memlab-07 ] ||
   [ "$LAB_REAL" != /var/tmp/memlab-07 ]; then
  echo "STOP: lab ownership check failed" >&2
  exit 1
fi
owner=$(docker inspect -f '{{ index .Config.Labels "memlab.owner" }}' \
  memlab-07-ollama)
if [ "$owner" != "$LAB_TOKEN" ]; then
  echo "STOP: container ownership check failed" >&2
  exit 1
fi
if docker container inspect memlab-07-cleanup >/dev/null 2>&1; then
  echo "STOP: memlab-07-cleanup already exists" >&2
  exit 1
fi
docker rm -fv memlab-07-ollama
docker run --rm --name memlab-07-cleanup \
  -v /var/tmp/memlab-07:/lab --entrypoint chown \
  ollama/ollama:0.40.16 -R "$(id -u):$(id -g)" /lab
cd /
rm -rf -- "$LAB"
test ! -e "$LAB" && test ! -L "$LAB"
test -z "$(docker ps -aq --filter name='^memlab-07-(ollama|cleanup)$')"
echo "Cleanup verified: lab and containers removed"
