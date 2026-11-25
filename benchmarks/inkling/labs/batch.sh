#!/usr/bin/env bash
# The hook is one shell command; it must restart only the owned reader and wait until ready.
set -euo pipefail
if (( $# < 3 )); then
  echo 'Usage: batch.sh <stock|edited|edited+lora> --restart-hook <command> [shared lab flags...]' >&2
  exit 2
fi
variant=$1
shift
if [[ $1 != --restart-hook ]]; then
  echo 'Second argument must be --restart-hook' >&2
  exit 2
fi
hook=$2
shift 2
case "$variant" in stock|edited|edited+lora|smoke) ;; *) echo 'Invalid variant' >&2; exit 2 ;; esac
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec "${PYTHON:-python3}" "$here/batch.py" --variant "$variant" --restart-hook "$hook" "$@"
