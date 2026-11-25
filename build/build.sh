#!/usr/bin/env bash
# Build guide.html and ai-memory-guide.pdf from chapters/*.html.
# Exits non-zero on lint errors, render failure or layout check failure.
set -euo pipefail
cd "$(dirname "$0")"
python3 make-cover.py >/dev/null
exec python3 build.py "$@"
