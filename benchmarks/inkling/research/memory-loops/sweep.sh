#!/usr/bin/env bash
# From the workstation. The model must already be provisioned on the Mac Studio.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec "${PYTHON:-python3}" "$here/sweep.py" "$@"
